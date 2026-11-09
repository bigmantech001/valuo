"""relative_value: peer multiples recomputed, rank/percentile, implied band, staking lens, real-snapshot checks."""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pytest

from valuo.models import relative_value as RV
from tests.test_market_implied import SNAPSHOT_PATH, synthetic_snapshot


def test_rank_against_peers() -> None:
    r = RV.rank_against_peers(50.0, [10.0, 100.0, 200.0])
    assert r["rank"] == 2 and r["n"] == 4
    assert r["percentile"] == pytest.approx(1 / 3)
    assert r["peer_median"] == 100.0 and r["position"] == "inside the peer range"
    assert RV.rank_against_peers(5.0, [10.0, 20.0])["position"] == "below every peer"
    assert RV.rank_against_peers(25.0, [10.0, 20.0])["position"] == "above every peer"
    assert RV.rank_against_peers(None, [10.0])["rank"] is None


def test_synthetic_coverage_and_band() -> None:
    res = RV.run_relative_value(synthetic_snapshot(current_fdv=2.0e9))
    # peer FDV/fees: 100, 200, 500; NEAR: 2e9 / 40e6 = 50
    cf = res["coverage"]["fdv_to_fees_run_rate"]
    assert cf["value"] == pytest.approx(50.0)
    assert cf["rank"] == 1 and cf["position"] == "below every peer"
    assert cf["peer_median"] == pytest.approx(200.0)
    band = res["implied_fdv_band"]["fees"]
    assert band["median_fdv_usd"] == pytest.approx(40e6 * 200.0)
    assert band["p25_fdv_usd"] == pytest.approx(40e6 * np.percentile([100, 200, 500], 25))
    assert band["p25_fdv_usd"] <= band["median_fdv_usd"] <= band["p75_fdv_usd"]
    # model terminal multiple 60x; peer FDV/revenue 200, 500, 1000 -> none at or below
    assert res["n_peers_at_or_below_model_multiple"] == 0
    assert res["findings"] and all(f.endswith(".") for f in res["findings"])


def test_staking_lens_arithmetic() -> None:
    snap = synthetic_snapshot()
    st = RV.run_relative_value(snap)["staking"]
    annual = 1.3e9 * 0.025
    assert st["annual_issuance_near"] == pytest.approx(annual)
    assert st["security_budget_usd_per_year"] == pytest.approx(annual * 1.5)
    assert st["revenue_to_security_budget"] == pytest.approx(15e6 / (annual * 1.5))
    assert st["net_dilution_usd_per_year"] == pytest.approx(annual * 1.5 - 15e6)


def test_missing_comps_degrade_to_null() -> None:
    snap = synthetic_snapshot()
    snap["comps"] = {}
    res = RV.run_relative_value(snap)
    assert res["peers"] == [] and res["implied_fdv_band"]["fees"] is None
    assert res["coverage"]["fdv_to_fees_run_rate"]["rank"] is None


@pytest.fixture(scope="module")
def real_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        pytest.skip("artifacts/latest_snapshot.json not present")
    return json.loads(SNAPSHOT_PATH.read_text())


def test_real_snapshot_multiples_match_comps(real_snapshot: dict[str, Any]) -> None:
    res = RV.run_relative_value(real_snapshot)
    by = {p["slug"]: p for p in real_snapshot["comps"]["peers"]}
    for row in res["peers"]:
        src = by[row["slug"]]
        if src.get("fdv_to_fees") is not None:
            assert row["fdv_to_fees_run_rate"] == pytest.approx(src["fdv_to_fees"], rel=1e-9)
        if src.get("fdv_to_revenue") is not None:
            assert row["fdv_to_revenue_run_rate"] == pytest.approx(src["fdv_to_revenue"], rel=1e-9)
    near = real_snapshot["comps"]["near_combined"]
    assert res["near"]["fdv_to_fees_run_rate"] == pytest.approx(near["fdv_to_fees"], rel=1e-9)
    med = res["coverage"]["fdv_to_revenue_run_rate"]["peer_median"]
    assert med == pytest.approx(real_snapshot["comps"]["median_fdv_to_revenue_ex_near"], rel=1e-9)
    assert 1 <= res["coverage"]["fdv_to_fees_run_rate"]["rank"] <= len(res["peers"]) + 1
