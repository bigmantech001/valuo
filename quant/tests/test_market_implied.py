"""market_implied: snapshot -> inputs reconstruction, bracketed solves, unreachable -> null, real-snapshot invariants."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import pytest

from valuo.models import market_implied as MI
from valuo.models.sotp_valuation import deterministic_sotp

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "latest_snapshot.json"


def synthetic_snapshot(*, current_fdv: float = 2.0e9, horizon: int = 36) -> dict[str, Any]:
    """A small, self-consistent synthetic snapshot (round numbers, not live data)."""
    days = 400
    t0 = 1_700_000_000
    # volume grows 50% over the year; fees 15 bps; revenue/fees 0.3
    series = []
    for d in range(days):
        v = 50e6 * (1.5 ** (d / 365.0))
        series.append([t0 + 86400 * d, v * 15e-4, v * 15e-4 * 0.3, v])
    flat = [0.025] * horizon
    glide = [0.025 + (0.016 - 0.025) * min(m, 24) / 24 for m in range(horizon)]
    return {
        "near_rpc": {"total_supply_near": 1.3e9, "staked_supply_ratio": 0.45, "nominal_staking_apr_current": 0.055},
        "execution_bench": {"competitive_fee_ceiling_bps": 3.0, "competitive_fee_ceiling_basis": "synthetic"},
        "intents_forensics": {
            "volume": {"confidential_share_30d": 0.4, "confidential_share_7d": 0.45},
            "fees": {"daily_series_columns": ["ts_unix_s", "fees_usd", "revenue_usd", "volume_usd"], "daily_series": series,
                     "take_rate_window_days": 30},
        },
        "comps": {
            "peers": [
                {"slug": "a", "symbol": "AAA", "fdv_usd": 100e9, "annualized_fees_usd": 1e9, "annualized_revenue_usd": 0.5e9,
                 "fees_1y_usd": 0.8e9, "revenue_1y_usd": 0.4e9},
                {"slug": "b", "symbol": "BBB", "fdv_usd": 50e9, "annualized_fees_usd": 0.25e9, "annualized_revenue_usd": 0.1e9,
                 "fees_1y_usd": 0.2e9, "revenue_1y_usd": 0.1e9},
                {"slug": "c", "symbol": "CCC", "fdv_usd": 10e9, "annualized_fees_usd": 0.02e9, "annualized_revenue_usd": 0.01e9,
                 "fees_1y_usd": 0.02e9, "revenue_1y_usd": 0.01e9},
            ],
            "near_combined": {"slug": "near_combined", "symbol": "NEAR", "fdv_usd": current_fdv, "annualized_fees_usd": 40e6,
                              "annualized_revenue_usd": 15e6, "fees_1y_usd": 30e6, "revenue_1y_usd": 10e6, "price_usd": 1.5},
            "median_fdv_to_revenue_ex_near": 500.0,
        },
        "supply_physics": {
            "current_daily_issuance_near": 1.3e9 * 0.025 / 365.25,
            "staking_yield_table": [
                {"regime": "status_quo", "inflation_rate": 0.025, "nominal_staking_apr": 0.055, "real_staking_apr": 0.03,
                 "real_staking_apr_with_buyback": 0.033, "real_non_staker_apr": -0.022},
            ],
        },
        "assumptions": [],
        "sotp": {
            "horizon_months": horizon, "discount_rate": 0.25, "current_fdv_usd": current_fdv,
            "fdv_percentiles": {"p50": 3.0e8},
            "inputs": {"confidential_multiple_haircut": {"value": 0.7}, "public_volume_growth_yoy": {"value": 0.3},
                       "confidential_compression_divisor": {"value": 3.0}, "near_price_drift_annual": {"value": 0.0}},
            "calibration": {
                "take_rate_window_days": 30.0,
                "v_pub_30d_usd": 1.2e9, "v_conf_30d_usd": 0.8e9, "gross_fees_30d_usd": 3.0e6,
                "alpha_capture": 0.3, "tau_conf_start_bps": 20.0, "public_take_floor_bps": 0.5, "headroom_cross_vm_bps": 1.0,
                "terminal_multiple_used": 60.0, "terminal_multiple_raw": 500.0,
                "gas_burn_near_day": 400.0, "state_lock_near_day": 300.0, "price_usd": 1.5,
                "regime_inflation_paths_annual": {"status_quo": flat, "svrn_glidepath": glide},
                "issuance_scale_measured_over_path": 1.0,
                "supply_at_horizon_by_regime": {"status_quo": 1.39e9, "svrn_glidepath": 1.37e9},
                "confidential_share_target": 0.4, "lambda_pub_monthly": 0.03,
                "sigma_volume_monthly": 0.3, "sigma_price_monthly": 0.3,
            },
        },
    }


def _row(res: dict[str, Any], param: str) -> dict[str, Any]:
    return next(r for r in res["solves"] if r["param"] == param)


# ------------------------------------------------------------------ reconstruction
def test_compose_inputs_reconciles_public_take_to_live_fees() -> None:
    p = MI.primitives_from_snapshot(synthetic_snapshot())
    inp = MI.compose_inputs(p)
    # month-0 modelled gross fees == measured 30d fees
    fees = (inp["v_pub_usd_day"] * inp["tau_pub_bps"] + inp["v_conf_usd_day"] * inp["tau_conf_bps"]) / 1e4 * 30.0
    assert fees == pytest.approx(3.0e6, rel=1e-12)
    assert inp["tau_floor_bps"] == pytest.approx(1.0)  # max(0.5, min(tau_pub, headroom 1.0))
    assert inp["growth_monthly_pub"] == pytest.approx(1.3 ** (1 / 12) - 1)
    assert inp["lambda_conf"] == pytest.approx(0.01)


def test_missing_field_raises() -> None:
    snap = synthetic_snapshot()
    del snap["sotp"]["calibration"]["alpha_capture"]
    with pytest.raises(ValueError, match="alpha_capture"):
        MI.primitives_from_snapshot(snap)


# ------------------------------------------------------------------ monotonicity
@pytest.mark.parametrize("key,lo,hi,increasing", [
    ("public_volume_growth_yoy", 0.0, 1.0, True),
    ("terminal_multiple", 10.0, 200.0, True),
    ("tau_pub_bps", 5.0, 50.0, True),
    ("discount_rate", 0.05, 0.6, False),
    ("volume_scale", 0.5, 3.0, True),
])
def test_fdv_monotone(key: str, lo: float, hi: float, increasing: bool) -> None:
    p = MI.primitives_from_snapshot(synthetic_snapshot())
    a, b = MI.fdv_at(p, **{key: lo}), MI.fdv_at(p, **{key: hi})
    assert (b > a) if increasing else (b < a)


# ------------------------------------------------------------------ solves
def test_root_found_where_expected() -> None:
    snap = synthetic_snapshot()
    p = MI.primitives_from_snapshot(snap)
    known = {"public_volume_growth_yoy": 0.8, "terminal_multiple": 140.0, "discount_rate": 0.12}
    for key, val in known.items():
        target = MI.fdv_at(p, **{key: val})
        res = MI.run_market_implied(snap, current_fdv_usd=target)
        row = _row(res, key)
        assert row["reachable"] and row["reason"] is None
        assert row["required_value"] == pytest.approx(val, rel=1e-7)
        assert row["check_rel_error"] < 1e-9


def test_holder_revenue_solve_is_linear_scale() -> None:
    snap = synthetic_snapshot()
    p = MI.primitives_from_snapshot(snap)
    target = MI.fdv_at(p, volume_scale=2.5)
    row = _row(MI.run_market_implied(snap, current_fdv_usd=target), "holder_revenue_scale")
    assert row["required_volume_scale"] == pytest.approx(2.5, rel=1e-8)
    assert row["required_value"] == pytest.approx(2.5 * row["base_value"], rel=1e-8)


def test_unreachable_returns_null_with_reason() -> None:
    snap = synthetic_snapshot(current_fdv=1e15)
    res = MI.run_market_implied(snap)
    g = _row(res, "public_volume_growth_yoy")
    assert g["required_value"] is None and not g["reachable"]
    assert "not reachable below 1,000%" in g["reason"]
    d = _row(res, "discount_rate")
    assert d["required_value"] is None and "0%" in d["reason"]
    assert res["n_reachable"] == 0
    assert "no single input" in res["headline"]


def test_target_below_base_moves_inputs_down() -> None:
    snap = synthetic_snapshot()
    p = MI.primitives_from_snapshot(snap)
    base = MI.fdv_at(p)
    res = MI.run_market_implied(snap, current_fdv_usd=base * 0.8)
    assert _row(res, "public_volume_growth_yoy")["required_value"] < 0.3
    assert _row(res, "discount_rate")["required_value"] > 0.25
    assert res["gap_multiple"] == pytest.approx(0.8)


def test_evidence_and_verdict_are_computed() -> None:
    res = MI.run_market_implied(synthetic_snapshot())
    g = _row(res, "public_volume_growth_yoy")
    assert g["evidence"]["value"] == pytest.approx(1.5 ** (335 / 365) - 1, rel=1e-2)  # synthetic series: +50%/yr
    assert "trailing-12-month" in g["verdict"]
    t = _row(res, "tau_pub_bps")
    assert t["evidence"]["value"] == 3.0
    m = _row(res, "terminal_multiple")
    assert m["evidence"]["value"] == 500.0
    for r in res["solves"]:
        assert isinstance(r["verdict"], str) and r["verdict"].endswith(".")


def test_trailing_growth_falls_back_to_log_returns() -> None:
    snap = synthetic_snapshot()
    snap["intents_forensics"]["fees"]["daily_series"] = []
    snap["sotp"]["calibration"]["sigma_volume_monthly_log_returns"] = [0.1] * 12
    tg = MI.trailing_volume_growth(snap)
    assert tg is not None and tg["value"] == pytest.approx(math.exp(1.2) - 1)


def test_input_snapshot_not_mutated() -> None:
    snap = synthetic_snapshot()
    before = copy.deepcopy(snap)
    MI.run_market_implied(snap)
    assert snap == before


def test_cli_prints_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "snap.json"
    f.write_text(json.dumps(synthetic_snapshot()))
    assert MI.main([str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert {"current_fdv_usd", "base_fdv_usd", "gap_multiple", "solves", "headline"} <= set(out)
    assert MI.main([]) == 2


# ------------------------------------------------------------------ real snapshot (read-only)
@pytest.fixture(scope="module")
def real_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        pytest.skip("artifacts/latest_snapshot.json not present")
    return json.loads(SNAPSHOT_PATH.read_text())


def test_real_snapshot_reconstruction_matches_deterministic_base(real_snapshot: dict[str, Any]) -> None:
    res = deterministic_sotp(MI.inputs_from_snapshot(real_snapshot))
    base = real_snapshot["sotp"]["calibration"]["deterministic_base"]
    for k in ("fdv_total", "engine_clearinghouse", "engine_confidential", "engine_monetary", "implied_price", "cum_holder_revenue_usd"):
        assert res[k] == pytest.approx(base[k], rel=1e-9), k


def test_real_snapshot_required_values_reproduce_market_fdv(real_snapshot: dict[str, Any]) -> None:
    res = MI.run_market_implied(real_snapshot)
    p = MI.primitives_from_snapshot(real_snapshot)
    target = res["current_fdv_usd"]
    assert target == pytest.approx(real_snapshot["sotp"]["current_fdv_usd"])
    assert res["base_fdv_usd"] == pytest.approx(real_snapshot["sotp"]["calibration"]["deterministic_base"]["fdv_total"], rel=1e-9)
    for r in res["solves"]:
        if not r["reachable"]:
            assert r["required_value"] is None and r["reason"]
            continue
        key = {"tau_pub_bps": "tau_pub_bps", "holder_revenue_scale": "volume_scale"}.get(r["param"], r["param"])
        val = r["required_volume_scale"] if r["param"] == "holder_revenue_scale" else r["required_value"]
        assert MI.fdv_at(p, **{key: val}) == pytest.approx(target, rel=1e-3), r["param"]
        lo, hi = MI.SEARCH_BOUNDS[r["param"]]
        if r["param"] != "holder_revenue_scale":
            assert lo <= r["required_value"] <= hi


def test_confidential_share_evidence_is_labelled_assumption_under_fallback() -> None:
    snap = synthetic_snapshot()
    measured = _row(MI.run_market_implied(snap), "confidential_share_target")
    assert measured["evidence"]["status"] == "measured" and "measured share" in measured["verdict"]
    snap["intents_forensics"]["volume"].update({
        "confidential_share_status": "implausible_fallback", "confidential_share_7d": None,
        "confidential_share_source": "assumption: registry confidential_share = 40% (nearstats split implausible; not a measurement)",
    })
    snap["sotp"]["calibration"]["confidential_engine_measured"] = False
    row = _row(MI.run_market_implied(snap), "confidential_share_target")
    assert row["evidence"]["assumption"] is True and row["evidence"]["status"] == "implausible_fallback"
    assert row["evidence"]["label"].startswith("ASSUMED") and "NOT MEASURED" in row["verdict"] and "measured share" not in row["verdict"]
