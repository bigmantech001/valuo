"""Confidential treasury audit: pricing, step flows, the on-chain TVL override and the share proxy (offline)."""
from __future__ import annotations

import pytest

from valuo.collectors import confidential_boundary as cb
from valuo.collectors import intents_forensics as f

PRICES = cb.price_table([
    {"assetId": "nep141:wrap.near", "price": 2.0, "decimals": 24, "symbol": "wNEAR"},
    {"assetId": "nep141:usdc", "price": 1.0, "decimals": 6, "symbol": "USDC"},
    {"assetId": "nep141:noprice", "price": None, "decimals": 6, "symbol": "X"},
])


def test_price_table_skips_unpriced():
    assert set(PRICES) == {"nep141:wrap.near", "nep141:usdc"}


def test_value_and_flows():
    n = 10 ** 24
    s0 = {"nep141:wrap.near": 10 * n, "nep141:usdc": 5_000_000}
    s1 = {"nep141:wrap.near": 12 * n, "nep141:usdc": 1_000_000, "nep141:noprice": 99}
    s2 = {"nep141:wrap.near": 11 * n, "nep141:usdc": 1_000_000}
    assert cb.value_usd(s0, PRICES) == pytest.approx(25.0)
    gin, gout = cb.step_flows([s0, s1, s2], PRICES)
    # in: +2 wNEAR ($4); out: -4 USDC ($4) then -1 wNEAR ($2); unpriced tokens ignored
    assert gin == pytest.approx(4.0) and gout == pytest.approx(6.0)
    # coarser snapshots net out: the same window seen as one step shows less gross flow (lower bound)
    gin2, gout2 = cb.step_flows([s0, s2], PRICES)
    assert gin2 + gout2 < gin + gout


def test_onchain_tvl_overrides_reported_and_keeps_it():
    m = {"confidential_tvl_usd": 139.6e6, "confidential_tvl_verified": True, "confidential_tvl_source_status": "verified"}
    out = f.apply_onchain_tvl(m, {"tvl_usd": 142.3e6})
    assert out["confidential_tvl_usd"] == 142.3e6 and out["confidential_tvl_source_status"] == "onchain_measured"
    assert out["confidential_tvl_reported_usd"] == 139.6e6 and out["confidential_tvl_reported_status"] == "verified"
    same = f.apply_onchain_tvl(m, None)
    assert same["confidential_tvl_usd"] == 139.6e6 and same["confidential_tvl_source_status"] == "verified"


def test_inflow_ratio_bounded_and_null_safe():
    r = f.boundary_inflow_ratio({"flow_24h_in_lower_bound_usd": 19e6}, {"24h": 166e6})
    assert r["confidential_boundary_inflow_ratio_24h"] == pytest.approx(19 / 185)
    assert f.boundary_inflow_ratio(None, {"24h": 1e6})["confidential_boundary_inflow_ratio_24h"] is None
    assert f.boundary_inflow_ratio({"flow_24h_in_lower_bound_usd": 1.0}, {"24h": None})["confidential_boundary_inflow_ratio_24h"] is None
