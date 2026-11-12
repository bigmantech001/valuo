"""sensitivity: tornado ranking, variance-proxy shares, ranges by source, speed, real-snapshot invariants."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from valuo import assumptions as A
from valuo.models import market_implied as MI
from valuo.models import sensitivity as S
from valuo.models.sotp_valuation import deterministic_sotp
from tests.test_market_implied import SNAPSHOT_PATH, synthetic_snapshot


def test_rows_ranked_by_swing_and_shares_sum_to_one() -> None:
    res = S.run_sensitivity(synthetic_snapshot())
    swings = [r["swing_usd"] for r in res["rows"]]
    assert swings == sorted(swings, reverse=True)
    assert [r["rank"] for r in res["rows"]] == list(range(1, len(swings) + 1))
    assert sum(r["variance_share"] for r in res["rows"]) == pytest.approx(1.0)
    assert res["top3_share"] == pytest.approx(sum(r["variance_share"] for r in res["rows"][:3]))
    for r in res["rows"]:
        assert r["swing_usd"] == pytest.approx(abs(r["fdv_high"] - r["fdv_low"]))
        assert r["source"] in {"measured", "assumption", "derived"}
        assert r["low"] <= r["high"]


def test_assumption_rows_use_registry_ranges() -> None:
    res = S.run_sensitivity(synthetic_snapshot())
    by = {r["param"]: r for r in res["rows"]}
    for key in S.ASSUMPTION_PARAMS:
        a = A.get(key)
        assert (by[key]["low"], by[key]["high"]) == (a.low, a.high)
        assert by[key]["source"] == "assumption"
    assert by["terminal_multiple"]["source"] == "derived"
    assert by["starting_volume"]["source"] == "measured"
    # A registry entry the run replaced by a measurement is labelled measured, with its interval as the range.
    snap = synthetic_snapshot()
    snap["assumptions"] = [{"key": "public_volume_growth_yoy", "value": 0.5, "low": 0.1, "high": 1.2, "source": "measured"}]
    g = {r["param"]: r for r in S.run_sensitivity(snap)["rows"]}["public_volume_growth_yoy"]
    assert g["source"] == "measured" and (g["low"], g["high"]) == (0.1, 1.2) and g["range_basis"].startswith("measured 90% interval")


def test_rows_match_direct_evaluation() -> None:
    snap = synthetic_snapshot()
    p = MI.primitives_from_snapshot(snap)
    res = S.run_sensitivity(snap)
    by = {r["param"]: r for r in res["rows"]}
    assert by["discount_rate"]["fdv_low"] == pytest.approx(MI.fdv_at(p, discount_rate=A.get("discount_rate").low))
    assert by["public_volume_growth_yoy"]["fdv_high"] > by["public_volume_growth_yoy"]["fdv_low"]
    assert by["discount_rate"]["fdv_high"] < by["discount_rate"]["fdv_low"]
    assert res["base_fdv_usd"] == pytest.approx(MI.fdv_at(p))


def test_measured_windows_from_daily_series() -> None:
    win = S.measured_windows(synthetic_snapshot(), 6)
    assert win is not None and win["n_windows"] == 6
    assert all(t == pytest.approx(15.0) for t in win["gross_take_bps"])
    assert all(c == pytest.approx(0.3) for c in win["capture_ratio"])


def test_band_fallback_when_no_series() -> None:
    snap = synthetic_snapshot()
    snap["intents_forensics"]["fees"]["daily_series"] = []
    res = S.run_sensitivity(snap)
    by = {r["param"]: r for r in res["rows"]}
    band = A.value("sensitivity_unmeasured_band")
    assert by["alpha_capture"]["source"] == "assumption"
    assert by["alpha_capture"]["low"] == pytest.approx(0.3 * (1 - band))
    assert res["notes"]


def test_deterministic_and_fast() -> None:
    snap = synthetic_snapshot()
    t0 = time.perf_counter()
    a = S.run_sensitivity(snap)
    assert time.perf_counter() - t0 < 2.0
    assert json.dumps(a, sort_keys=True) == json.dumps(S.run_sensitivity(snap), sort_keys=True)


@pytest.fixture(scope="module")
def real_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        pytest.skip("artifacts/latest_snapshot.json not present")
    return json.loads(SNAPSHOT_PATH.read_text())


def test_real_snapshot_tornado(real_snapshot: dict[str, Any]) -> None:
    t0 = time.perf_counter()
    res = S.run_sensitivity(real_snapshot)
    assert time.perf_counter() - t0 < 2.0
    base = real_snapshot["sotp"]["calibration"]["deterministic_base"]["fdv_total"]
    assert res["base_fdv_usd"] == pytest.approx(base, rel=1e-9)
    assert deterministic_sotp(MI.inputs_from_snapshot(real_snapshot))["fdv_total"] == pytest.approx(base, rel=1e-9)
    assert len(res["rows"]) >= 12
    for r in res["rows"]:
        assert r["fdv_low"] > 0 and r["fdv_high"] > 0
    assert 0.0 < res["top3_share"] <= 1.0
