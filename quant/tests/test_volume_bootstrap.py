"""Block-bootstrap volume engine (valuo/models/volume_bootstrap.py) and its place in the backtest: resampling math,
determinism, no look-ahead, the GBM result left untouched, and the like-for-like Monte Carlo swap. Synthetic inputs only."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from valuo import config
from valuo.models import backtest as bt
from valuo.models import volume_bootstrap as vb
from valuo.models.sotp_valuation import simulate_paths

SEED = 20261114
DAY = 86400
T0 = 1_700_000_000 // DAY * DAY


def _ar1(n: int, phi: float, sigma: float, seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n) * sigma
    x = np.empty(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def _daily_chart(n_days: int, *, sigma: float = 0.25, drift: float = 0.004, seed: int = SEED, v0: float = 1e7) -> list[list[float]]:
    """Daily volume whose log-changes are iid Normal(drift, sigma): the bootstrap's own data-generating process."""
    rng = np.random.default_rng(seed)
    logs = math.log(v0) + np.cumsum(drift + sigma * rng.standard_normal(n_days))
    return [[T0 + i * DAY, float(math.exp(lv))] for i, lv in enumerate(logs)]


@pytest.fixture(scope="module")
def chart() -> list[list[float]]:
    return _daily_chart(330)


@pytest.fixture(scope="module")
def with_engines(chart: list[list[float]]) -> dict:
    return bt.run_backtest(chart, growth_yoy=0.30, with_engines=True)


# ---------------------------------------------------------------------------- resampling
def test_indices_are_circular_blocks_with_the_requested_mean_length() -> None:
    n, b = 50, 8.0
    idx = vb.stationary_bootstrap_indices(n, 400, 300, b, np.random.default_rng(SEED))
    assert idx.shape == (400, 300) and idx.min() >= 0 and idx.max() < n
    step = (idx[:, 1:] - idx[:, :-1]) % n
    continued = step == 1
    # a new block lands on the successor by chance 1/n of the time, so P(step == 1) = (1 - 1/b) + (1/b)(1/n)
    assert continued.mean() == pytest.approx((1 - 1 / b) + (1 / b) / n, abs=0.01)
    assert ((idx == n - 1)[:, :-1] & (idx[:, 1:] == 0)).any()  # wraps around the end of the series
    assert np.bincount(idx.ravel(), minlength=n).min() > 0     # every day can be drawn


def test_bootstrap_recovers_mean_and_variance_of_an_iid_series() -> None:
    rng = np.random.default_rng(SEED)
    x = 0.002 + 0.05 * rng.standard_normal(364)
    b = vb.optimal_block_length(x)
    assert 1.0 <= b <= math.ceil(min(3 * math.sqrt(364), 364 / 3))
    idx = vb.stationary_bootstrap_indices(x.size, 20_000, 30, b, np.random.default_rng(SEED))
    draws = x[idx]
    assert draws.mean() == pytest.approx(x.mean(), abs=4 * 0.05 / math.sqrt(draws.size) + 1e-4)
    assert draws.var() == pytest.approx(x.var(), rel=0.03)
    sums = vb.bootstrap_log_paths(x, 30, mean_block=b, n_paths=20_000, rng=np.random.default_rng(SEED))[:, -1]
    assert sums.mean() == pytest.approx(30 * x.mean(), abs=0.01)
    # iid: the variance of a 30-day sum is 30 x the daily variance (sampling error of the lookback's own autocovariances allowed)
    assert sums.var() == pytest.approx(30 * x.var(), rel=0.25)


def test_block_length_selector_separates_iid_from_persistent_series() -> None:
    iid = _ar1(364, 0.0, 1.0)
    persistent = _ar1(364, 0.8, 1.0)
    b_iid, b_pers = vb.optimal_block_length(iid), vb.optimal_block_length(persistent)
    assert b_iid < b_pers <= 58.0
    assert b_iid < 8.0 < b_pers
    assert vb.optimal_block_length(np.ones(100)) == 1.0 and vb.optimal_block_length([0.1, 0.2]) == 1.0
    assert vb.rule_of_thumb_block_length(343) == pytest.approx(7.0)
    with pytest.raises(ValueError):
        vb.mean_block_length(iid, "tuned")


def test_blocks_keep_autocorrelation_that_an_iid_draw_drops() -> None:
    x = _ar1(364, 0.6, 0.05)
    b = vb.optimal_block_length(x)
    blocked = vb.bootstrap_log_paths(x, 30, mean_block=b, n_paths=8_000, rng=np.random.default_rng(SEED))[:, -1].var()
    shuffled = vb.bootstrap_log_paths(x, 30, mean_block=1.0, n_paths=8_000, rng=np.random.default_rng(SEED))[:, -1].var()
    assert shuffled == pytest.approx(30 * x.var(), rel=0.15)
    assert blocked > 1.8 * shuffled  # positive autocorrelation widens the horizon distribution; block length 1 loses it


def test_daily_log_changes_skips_bad_pairs_and_respects_the_lookback() -> None:
    v = [1.0, 2.0, 0.0, 4.0, 8.0, float("nan"), 16.0, 32.0]
    np.testing.assert_allclose(vb.daily_log_changes(v), [math.log(2.0)] * 3)
    assert vb.daily_log_changes(v, lookback_days=2).tolist() == [pytest.approx(math.log(2.0))]
    assert vb.daily_log_changes([5.0]).size == 0


# ---------------------------------------------------------------------------- forecast at one origin
def test_forecast_is_reproducible_and_keyed_by_origin(chart: list[list[float]]) -> None:
    values = [v for _, v in chart[:200]]
    a = vb.forecast_at_origin(values, origin_ts=T0, horizon_days=[30, 91], growth_yoy=0.3, n_paths=500)
    b = vb.forecast_at_origin(values, origin_ts=T0, horizon_days=[30, 91], growth_yoy=0.3, n_paths=500)
    c = vb.forecast_at_origin(values, origin_ts=T0 + DAY, horizon_days=[30, 91], growth_yoy=0.3, n_paths=500)
    assert a is not None and b is not None and c is not None
    for h in (30, 91):
        for mode in ("resampled", "registry"):
            np.testing.assert_array_equal(a["horizons"][h][mode], b["horizons"][h][mode])
        assert not np.array_equal(a["horizons"][h]["resampled"], c["horizons"][h]["resampled"])
        # registry form: demeaned and rescaled to the GBM's expected path, V_0 (1+g)^(days/365.25) x 30
        assert a["horizons"][h]["registry"].mean() == pytest.approx(a["v0_30d_usd"] * 1.3 ** (h / 365.25), rel=1e-9)
    assert a["v0_30d_usd"] == pytest.approx(sum(values[-30:])) and a["last_day_usd"] == values[-1]
    assert a["n_changes"] == 199 and a["n_paths"] == 500
    # too little history, or a dead last day: no forecast, no exception
    assert vb.forecast_at_origin(values[:20], origin_ts=T0, horizon_days=[30]) is None
    assert vb.forecast_at_origin([*values[:100], 0.0], origin_ts=T0, horizon_days=[30]) is None
    assert vb.forecast_at_origin(values, origin_ts=T0, horizon_days=[30], n_paths=200)["horizons"][30]["registry"] is None


def test_forecast_covers_its_own_data_generating_process() -> None:
    """Walk-forward on iid log-changes (what the bootstrap assumes): P10-P90 should hold about 80% of outcomes."""
    values = np.array([v for _, v in _daily_chart(365 + 30 * 81, sigma=0.2, drift=0.0)])
    inside = n = 0
    for k in range(80):
        i = 364 + 30 * k
        fc = vb.forecast_at_origin(values[: i + 1], origin_ts=T0 + i * DAY, horizon_days=[30], n_paths=1_500)
        assert fc is not None
        smp = fc["horizons"][30]["resampled"]
        realized = values[i + 1: i + 31].sum()
        inside += int(np.quantile(smp, 0.10) <= realized <= np.quantile(smp, 0.90))
        n += 1
    assert 0.65 <= inside / n <= 0.92, inside / n


# ---------------------------------------------------------------------------- inside the backtest
def test_engines_block_leaves_every_existing_key_unchanged(chart: list[list[float]], with_engines: dict) -> None:
    base = bt.run_backtest(chart, growth_yoy=0.30)
    assert "engines" not in base and "comparison" not in base  # default call: the GBM backtest exactly as before
    for key, val in base.items():
        assert with_engines[key] == val, key
    assert with_engines["engines_error"] is None
    eng = with_engines["engines"]
    assert eng["gbm"]["by_horizon"] == base["by_horizon"] and eng["gbm"]["calibrated"] == base["calibrated"]
    assert eng["gbm"]["used_by_valuation"] is True and eng["block_bootstrap"]["used_by_valuation"] is False
    assert with_engines["valuation_effect"]["engine_used_by_valuation"] == "gbm"


def test_bootstrap_is_scored_on_the_gbm_sample_with_consistent_stats(with_engines: dict) -> None:
    boot = with_engines["engines"]["block_bootstrap"]
    assert boot["seed"] == SEED and boot["n_paths"] == 10_000 and boot["block_length_rule"] == "politis_white"
    assert with_engines["comparison"]["same_sample"] is True
    gbm_rows = {(r["origin_date"], r["h"]): r for r in with_engines["rows"]}
    assert len(boot["rows"]) == len(gbm_rows) > 10
    for r in boot["rows"]:
        g = gbm_rows[(r["origin_date"], r["h"])]
        assert r["realized_30d_usd"] == g["realized_30d_usd"] and r["target_date"] == g["target_date"]
        assert r["v0_30d_usd"] == pytest.approx(g["v0_30d_usd"], rel=1e-12)  # same 30 days, summed by numpy instead of math.fsum
        assert 0 < r["p10"] < r["p50"] < r["p90"] and 0.0 < r["pit"] < 1.0
        assert r["inside"] == (r["p10"] <= r["realized_30d_usd"] <= r["p90"])
    for name in ("block_bootstrap",):
        for h, s in with_engines["engines"][name]["by_horizon"].items():
            rows = [r for r in boot["rows"] if str(r["h"]) == h]
            assert s["n"] == len(rows) and s["inside"] == sum(r["inside"] for r in rows) and sum(s["pit_hist"]) == s["n"]
            assert s["binom_p_vs_80"] == pytest.approx(bt._binom_two_sided_p(s["inside"], s["n"], 0.8))
            flag = boot["calibrated"]["per_horizon"][h]
            assert flag == (s["binom_p_vs_80"] >= 0.10)
            cmp_h = with_engines["comparison"]["per_horizon"][h]
            assert cmp_h["block_bootstrap"]["inside"] == s["inside"] and cmp_h["gbm"]["n"] == with_engines["by_horizon"][h]["n"]
            assert cmp_h["band_width_ratio_bootstrap_to_gbm"] > 0
    for variant in ("registry_drift", "rule_of_thumb_blocks"):
        v = boot["variants"][variant]
        assert set(v["by_horizon"]) == set(boot["by_horizon"]) and "per_horizon" in v["calibrated"]
    assert isinstance(with_engines["comparison"]["headline"], str) and with_engines["comparison"]["headline"].endswith(".")
    assert with_engines["comparison"]["outcome"] in {"bootstrap_passes_low_power", "bootstrap_fails", "bootstrap_mixed"}


def test_bootstrap_has_no_look_ahead(chart: list[list[float]], with_engines: dict) -> None:
    cut_ts = chart[200][0]
    mutated = bt.run_backtest([[t, v * (1000.0 if t > cut_ts else 1.0)] for t, v in chart], growth_yoy=0.30, with_engines=True)
    a = {(r["origin_date"], r["h"]): r for r in with_engines["engines"]["block_bootstrap"]["rows"]}
    b = {(r["origin_date"], r["h"]): r for r in mutated["engines"]["block_bootstrap"]["rows"]}
    checked = changed = 0
    for key, r in a.items():
        origin_ts = int(np.datetime64(r["origin_date"]).astype("datetime64[s]").astype(int))
        if origin_ts <= cut_ts:
            for f in ("p10", "p50", "p90", "mean", "mean_block_days", "n_changes", "v0_30d_usd"):
                assert b[key][f] == r[f], (key, f)
            checked += 1
        else:
            changed += int(b[key]["p50"] != r["p50"])
    assert checked >= 4 and changed >= 1


def test_power_and_forward_effect_fields(with_engines: dict) -> None:
    power = bt._test_power(20)
    assert (power["accept_min"], power["accept_max"]) == (14, 19)
    assert power["reject_prob_if_true_80"] < 0.10 < power["reject_prob_if_true_70"] < power["reject_prob_if_true_60"] < 1.0
    vol = with_engines["valuation_effect"]["volume_12m"]
    assert vol["horizon_months"] == 12 and vol["horizon_days"] == 365
    for key in ("gbm", "block_bootstrap_registry_drift", "block_bootstrap_resampled_drift"):
        assert 0 < vol[key]["p10"] < vol[key]["p50"] < vol[key]["p90"]
    # same expected path: the shape-only bootstrap and the GBM agree on the mean multiple, (1+g) to within the day-count rounding
    assert vol["block_bootstrap_registry_drift"]["mean"] == pytest.approx(vol["gbm"]["mean"], rel=2e-3)
    assert vol["gbm"]["mean"] == pytest.approx(1.30, rel=1e-9)
    assert with_engines["valuation_effect"]["fdv"]["computed"] is False  # needs a snapshot; run_backtest alone has none


def test_engine_fault_never_costs_the_base_backtest(chart: list[list[float]], monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("resampler down")

    monkeypatch.setattr(vb, "forecast_at_origin", boom)
    res = bt.run_backtest(chart, growth_yoy=0.30, with_engines=True)
    assert res["engines"] is None and res["comparison"] is None and res["valuation_effect"] is None
    assert "resampler down" in res["engines_error"]
    assert res["by_horizon"] == bt.run_backtest(chart, growth_yoy=0.30)["by_horizon"]
    assert bt.bootstrap_claim(res) is None
    assert "not computed" in vb.memo_markdown(res, {})


# ---------------------------------------------------------------------------- claim and memo
def _fake_bt(inside: dict[str, tuple[int, int]]) -> dict:
    by_h = {h: {"n": n, "inside": k, "coverage_p10_p90": k / n, "binom_p_vs_80": bt._binom_two_sided_p(k, n, 0.8)} for h, (k, n) in inside.items()}
    gbm = {"1": {"n": 20, "inside": 12, "coverage_p10_p90": 0.6, "binom_p_vs_80": bt._binom_two_sided_p(12, 20, 0.8)}}
    return {
        "source": "synthetic", "source_sha256": "ab" * 32, "n_origins": 20, "first_origin": "2025-01-01", "last_origin": "2026-08-01",
        "engines": {"gbm": {"by_horizon": gbm}, "block_bootstrap": {"by_horizon": by_h, "calibrated": bt._verdict(by_h), "seed": SEED, "n_paths": 10_000}},
        "comparison": {"per_horizon": {"1": {"band_width_ratio_bootstrap_to_gbm": 1.5}}, "power_1m": bt._test_power(20)},
    }


def test_bootstrap_claim_grades_on_every_scored_horizon(with_engines: dict) -> None:
    passing = bt.bootstrap_claim(_fake_bt({"1": (16, 20), "3": (14, 17)}))
    assert passing is not None and passing["status"] == "DERIVED" and passing["confidence"] == "low"
    one_fails = bt.bootstrap_claim(_fake_bt({"1": (16, 20), "3": (8, 17)}))
    assert one_fails["status"] == "NOT_SUPPORTED"
    too_wide = bt.bootstrap_claim(_fake_bt({"1": (20, 20)}))  # 20 of 20 is over-coverage and is rejected like under-coverage
    assert too_wide["status"] == "NOT_SUPPORTED"
    assert bt.bootstrap_claim({"by_horizon": {}}) is None
    live = bt.bootstrap_claim(with_engines)
    assert set(live) == {"claim", "status", "value", "source", "confidence", "note"}
    assert live["status"] == ("DERIVED" if with_engines["engines"]["block_bootstrap"]["calibrated"]["all"] else "NOT_SUPPORTED")
    assert "GBM" in live["value"] and "block bootstrap" in live["value"] and "ab" not in live["source"]


def test_memo_renders_both_engines_and_states_which_one_the_valuation_uses(with_engines: dict) -> None:
    md = vb.memo_markdown(with_engines, {})
    assert with_engines["comparison"]["headline"] in md
    assert "| GBM, registry drift (valuation engine) | 1m |" in md and "| Block bootstrap, resampled drift | 1m |" in md
    assert "The valuation uses the GBM" in md and "Caveats:" in md and "overfitting" in md
    assert "FDV: not computed" in md
    for banned in ("—", "seamless", "unlock", "revolutioni", "delve"):
        assert banned not in md
    assert vb.memo_markdown({"rows": []}, {}).startswith("The block-bootstrap engine was not computed")


# ---------------------------------------------------------------------------- the Monte Carlo swap
def test_monthly_relative_paths_are_mean_one() -> None:
    x = _ar1(364, 0.2, 0.3)
    rel = vb._monthly_relative_paths(x, 6, mean_block=10.0, n_paths=2_500, rng=np.random.default_rng(SEED))
    assert rel.shape == (2_500, 6) and (rel > 0).all()
    np.testing.assert_allclose(rel.mean(axis=0), 1.0, rtol=1e-12)
    wide = vb._monthly_relative_paths(x, 6, mean_block=10.0, n_paths=2_500, rng=np.random.default_rng(SEED), scale=1.5)
    assert np.log(wide[:, -1]).std() > np.log(rel[:, -1]).std()


def test_fdv_swap_is_like_for_like_and_leaves_the_base_run_alone() -> None:
    """With the base run's own volume paths the swap returns the base FDV bit for bit; the base equals sotp.fdv_percentiles."""
    snap_path = config.ARTIFACTS_DIR / "latest_snapshot.json"
    if not snap_path.is_file():
        pytest.skip("no canonical snapshot to rebuild the base Monte Carlo from")
    from valuo.models.market_implied import inputs_from_snapshot

    snap = json.loads(Path(snap_path).read_text())
    before = json.dumps(snap["sotp"], sort_keys=True)
    cal = snap["sotp"]["calibration"]
    inputs = inputs_from_snapshot(snap)
    inputs.update({
        "sigma_volume_monthly": cal["sigma_volume_monthly"], "sigma_price_monthly": cal["sigma_price_monthly"],
        "confidential_sigma_multiplier": cal.get("confidential_sigma_multiplier") or 1.0,
    })
    sim = simulate_paths(inputs, seed=snap["sotp"]["seed"], n_paths=2_000)
    again = vb._revalue(inputs, sim, sim["v_pub"], sim["v_conf"])
    for key in ("fdv", "e1", "e2", "e3"):
        np.testing.assert_array_equal(again[key], sim[key])

    chart, _, _ = bt.load_dexs_chart(None, snap)
    values = [float(r[1]) for r in chart]
    out = vb.fdv_effect(snap, values, origin_ts=int(chart[-1][0]))
    assert out["computed"] is True and out["revalue_identity_holds"] is True and out["base_reproduces_snapshot"] is True
    for k in ("p10", "p50", "p90"):
        assert out["gbm"][k] == pytest.approx(snap["sotp"]["fdv_percentiles"][k], rel=1e-9)
        assert out["block_bootstrap"][k] > 0 and out["ratio_to_gbm"][k] == pytest.approx(out["block_bootstrap"][k] / out["gbm"][k])
    assert out == vb.fdv_effect(snap, values, origin_ts=int(chart[-1][0]))  # deterministic
    assert json.dumps(snap["sotp"], sort_keys=True) == before              # the snapshot's sotp block is read, never written
    assert vb.fdv_effect({}, values, origin_ts=0) == {"computed": False, "reason": "snapshot.sotp is absent"}
