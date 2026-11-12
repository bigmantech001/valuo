"""Tests for valuo.collectors.wide_peers: ranking, inclusion and exclusion, distribution arithmetic, bootstrap
determinism, a missing CoinGecko row, 429 handling, the scorecard claim and the memo rendering.

Offline. Every payload here is synthetic (round numbers chosen so the expected multiples can be checked by hand);
the collector tests route httpx through a MockTransport.
"""
from __future__ import annotations

import argparse
import asyncio
from typing import Any

import httpx
import numpy as np
import pytest

from valuo import assumptions
from valuo.collectors import wide_peers as wp
from valuo.collectors.wide_peers import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    COINGECKO_ID_BY_SLUG,
    NO_TOKEN_REASON_BY_SLUG,
    build_wide_peers,
    collect_wide_peers,
    distribution,
    memo_markdown,
    parse_chain_rows,
    parse_market_rows,
    percentile_at_or_below,
    scorecard_claim,
)
from valuo.provenance import ProvenanceLedger

ANN = 365.0 / 30.0


def chain(slug: str, rev30: Any, *, name: str | None = None, category: str = "Chain", protocol_type: str = "chain", **extra: Any) -> dict[str, Any]:
    return {
        "slug": slug, "name": name or slug.title(), "displayName": name or slug.title(), "category": category,
        "protocolType": protocol_type, "total30d": rev30, "total1y": None if not isinstance(rev30, (int, float)) else rev30 * 12,
        "methodology": {"Revenue": f"{slug} burn"}, **extra,
    }


def market(cg_id: str, fdv: float | None, symbol: str | None = None) -> dict[str, Any]:
    return {"id": cg_id, "symbol": (symbol or cg_id[:4]), "fully_diluted_valuation": fdv, "market_cap": fdv, "current_price": 1.0}


def overview(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"protocols": list(rows)}


# A small universe: revenue chosen so annualised revenue = rev30 x 365/30 and the multiples are easy to state.
OVERVIEW = overview(
    chain("tron", 3000.0),
    chain("ethereum", 2000.0),
    chain("base", 1500.0),                       # no native token -> excluded
    chain("solana", 1000.0),
    chain("mysterychain", 900.0),                # not in the mapping table -> excluded, warned
    chain("arbitrum", 800.0),                    # flagged L2, kept
    chain("near", 700.0),                        # subject, never a peer
    chain("dexalot", 600.0, protocol_type="protocol"),  # adapter not typed chain -> flagged, kept
    chain("aptos", 500.0),
    chain("uniswap", 99999.0, category="Dexs"),  # not a chain row
    chain("zerochain", 0.0),                     # no revenue -> not ranked
    chain("brokenchain", "not-a-number"),        # malformed -> skipped and counted
    {"slug": "hl-perps", "name": "HL Perps", "category": "Derivatives", "total30d": 4000.0, "parentProtocol": "parent#hyperliquid"},
    {"slug": "hl-spot", "name": "HL Spot", "category": "Dexs", "total30d": 1000.0, "parentProtocol": "parent#hyperliquid"},
)
MARKETS = [
    market("tron", 3000.0 * ANN * 100),      # 100x
    market("ethereum", 2000.0 * ANN * 400),  # 400x
    market("solana", 1000.0 * ANN * 300),    # 300x
    market("arbitrum", 800.0 * ANN * 50),    # 50x
    market("dexalot", 600.0 * ANN * 10),     # 10x
    market("aptos", 500.0 * ANN * 200),      # 200x
    market("near", 700.0 * ANN * 250, "near"),  # 250x
    market("hyperliquid", 5000.0 * ANN * 80),   # 80x on the summed parent revenue
]


def mult_by_slug(out: dict[str, Any]) -> dict[str, float]:
    return {p["slug"]: p["fdv_to_revenue"] for p in out["peers"]}


# ----------------------------------------------------------------------------- parsing and ranking
def test_parse_chain_rows_ranks_by_revenue_and_skips_non_chain_zero_and_malformed() -> None:
    rows, malformed = parse_chain_rows(OVERVIEW)
    assert [r["slug"] for r in rows] == ["tron", "ethereum", "base", "solana", "mysterychain", "arbitrum", "near", "dexalot", "aptos"]
    assert [r["rank_by_revenue"] for r in rows] == list(range(1, 10))
    assert malformed == 1
    assert rows[0]["revenue_methodology"] == "tron burn"
    assert parse_chain_rows({"protocols": "nope"}) == ([], 0)
    assert parse_chain_rows(None) == ([], 0)


def test_parse_market_rows_keeps_only_positive_finite_fdv() -> None:
    parsed = parse_market_rows([market("a", 10.0), market("b", None), market("c", 0.0), {"no_id": 1}, "junk"])
    assert parsed["a"]["fdv_usd"] == 10.0
    assert parsed["b"]["fdv_usd"] is None and parsed["c"]["fdv_usd"] is None
    assert set(parsed) == {"a", "b", "c"}
    assert parse_market_rows({"error": "rate limited"}) == {}


def test_inclusion_exclusion_and_flags() -> None:
    warnings: list[str] = []
    out = build_wide_peers(OVERVIEW, MARKETS, None, 60.0, 8.0, warn=warnings.append)
    assert [p["slug"] for p in out["peers"]] == ["tron", "ethereum", "solana", "arbitrum", "dexalot", "aptos"]
    assert out["n_peers"] == 6 and out["n_chains_ranked"] == 9
    assert "near" not in mult_by_slug(out)  # the subject is positioned, not counted
    got = mult_by_slug(out)
    for slug, expected in {"tron": 100, "ethereum": 400, "solana": 300, "arbitrum": 50, "dexalot": 10, "aptos": 200}.items():
        assert got[slug] == pytest.approx(expected)
    tron = out["peers"][0]
    assert tron["annualized_revenue_usd"] == pytest.approx(3000.0 * 365 / 30)
    assert tron["coingecko_id"] == COINGECKO_ID_BY_SLUG["tron"]

    reasons = {e["slug"]: e["reason_code"] for e in out["excluded"]}
    assert reasons == {"base": "no_native_token", "mysterychain": "unmapped"}
    base = next(e for e in out["excluded"] if e["slug"] == "base")
    assert base["reason"] == NO_TOKEN_REASON_BY_SLUG["base"] and base["rank_by_revenue"] == 3 and base["revenue_30d_usd"] == 1500.0
    assert any("mysterychain" in w for w in warnings)
    assert any("skipped" in w for w in warnings)  # the malformed chain row
    assert any("only 6 of the 15" in w for w in warnings)

    flags = {p["slug"]: p["flags"] for p in out["peers"]}
    assert flags["tron"] == [] and flags["aptos"] == []
    assert len(flags["arbitrum"]) == 1 and "L2" in flags["arbitrum"][0]
    assert any("'protocol'" in f for f in flags["dexalot"])
    # sensitivity drops exactly the flagged rows: 100, 400, 300, 200 -> median 250
    exf = out["ex_flagged"]
    assert exf["n_peers"] == 4 and exf["n_flagged_removed"] == 2 and exf["median"] == pytest.approx(250.0)
    assert out["inclusion_rules"] and out["caveats"]


def test_cut_takes_the_top_n_with_a_token_and_counts_the_rest() -> None:
    out = build_wide_peers(OVERVIEW, MARKETS, None, 60.0, 8.0, n_target=3)
    assert [p["slug"] for p in out["peers"]] == ["tron", "ethereum", "solana"]
    assert [e["slug"] for e in out["excluded"]] == ["base"]  # only what ranks inside the cut is listed
    assert out["n_chains_below_cut"] == 4  # mysterychain, arbitrum, dexalot, aptos (near is the subject)


def test_missing_coingecko_row_is_excluded_and_next_chain_takes_the_place() -> None:
    markets = [m for m in MARKETS if m["id"] != "ethereum"] + [market("ethereum", None)]
    warnings: list[str] = []
    out = build_wide_peers(OVERVIEW, markets, None, 60.0, 8.0, n_target=3, warn=warnings.append)
    assert [p["slug"] for p in out["peers"]] == ["tron", "solana", "arbitrum"]
    eth = next(e for e in out["excluded"] if e["slug"] == "ethereum")
    assert eth["reason_code"] == "no_coingecko_fdv" and eth["coingecko_id"] == "ethereum"
    assert any("ethereum" in w and "FDV" in w for w in warnings)
    # an id absent from the array altogether behaves the same
    out2 = build_wide_peers(OVERVIEW, [m for m in MARKETS if m["id"] != "tron"], None, 60.0, 8.0, n_target=3)
    assert [p["slug"] for p in out2["peers"]] == ["ethereum", "solana", "arbitrum"]


def test_second_row_for_the_same_token_is_excluded() -> None:
    ov = overview(chain("berachain-incentive-buys", 500.0), chain("tron", 400.0))
    twin = dict(COINGECKO_ID_BY_SLUG)
    twin["bera-twin"] = "berachain-bera"
    ov["protocols"].insert(1, chain("bera-twin", 450.0))
    orig = wp.COINGECKO_ID_BY_SLUG
    wp.COINGECKO_ID_BY_SLUG = twin
    try:
        out = build_wide_peers(ov, [market("berachain-bera", 1e9), market("tron", 1e9)], None, 60.0, 8.0)
    finally:
        wp.COINGECKO_ID_BY_SLUG = orig
    assert [p["slug"] for p in out["peers"]] == ["berachain-incentive-buys", "tron"]
    assert [(e["slug"], e["reason_code"]) for e in out["excluded"]] == [("bera-twin", "token_already_counted")]


def test_no_chain_rows_or_no_peers_raise() -> None:
    with pytest.raises(ValueError, match="no chain row"):
        build_wide_peers({"protocols": []}, MARKETS)
    with pytest.raises(ValueError, match="no chain qualified"):
        build_wide_peers(OVERVIEW, [])


# ----------------------------------------------------------------------------- arithmetic
def test_distribution_quartiles_match_hand_values() -> None:
    d = distribution([10.0, 20.0, 30.0, 40.0, 50.0])
    assert (d["n"], d["median"], d["p25"], d["p75"], d["iqr"], d["min"], d["max"]) == (5, 30.0, 20.0, 40.0, 20.0, 10.0, 50.0)
    even = distribution([1.0, 2.0, 3.0, 4.0])
    assert even["median"] == pytest.approx(2.5) and even["p25"] == pytest.approx(1.75) and even["p75"] == pytest.approx(3.25)
    empty = distribution([])
    assert empty["n"] == 0 and empty["median"] is None and empty["median_ci90"] is None
    one = distribution([7.0])
    assert one["median"] == 7.0 and one["median_ci90"] == [7.0, 7.0]


def test_percentile_is_share_at_or_below() -> None:
    vals = [10.0, 20.0, 30.0, 40.0]
    assert percentile_at_or_below(5.0, vals) == 0.0
    assert percentile_at_or_below(20.0, vals) == 0.5  # ties count as at or below
    assert percentile_at_or_below(25.0, vals) == 0.5
    assert percentile_at_or_below(99.0, vals) == 1.0
    assert percentile_at_or_below(None, vals) is None and percentile_at_or_below(1.0, []) is None


def test_distribution_and_positions_in_the_built_view() -> None:
    out = build_wide_peers(OVERVIEW, MARKETS, None, 60.0, 8.0)
    d = out["distribution"]  # multiples: 10, 50, 100, 200, 300, 400
    assert d["median"] == pytest.approx(150.0) and d["min"] == pytest.approx(10.0) and d["max"] == pytest.approx(400.0)
    assert d["p25"] == pytest.approx(62.5) and d["p75"] == pytest.approx(275.0) and d["iqr"] == pytest.approx(212.5)
    assert out["terminal_multiple_cap"] == 60.0 and out["n_peers_at_or_below_cap"] == 2 and out["cap_percentile"] == pytest.approx(2 / 6)
    assert out["terminal_multiple_floor"] == 8.0 and out["n_peers_at_or_below_floor"] == 0 and out["floor_percentile"] == 0.0
    near = out["near"]
    assert near["fdv_to_revenue"] == pytest.approx(250.0) and near["n_peers_at_or_below"] == 4 and near["percentile"] == pytest.approx(4 / 6)
    assert near["rank_by_revenue"] == 7 and "L1-only" in near["basis"]
    three = out["model_three_peer"]  # SOL 300x, ETH 400x, Hyperliquid parent (4000 + 1000 revenue) 80x -> median 300x
    assert three["n"] == 3 and three["median_fdv_to_revenue"] == pytest.approx(300.0)
    assert three["members"][2]["revenue_30d_usd"] == 5000.0
    assert "60x" in out["headline"] and "33rd percentile" in out["headline"] and "150x" in out["headline"] and "250x" in out["headline"]
    assert "overturned" in out["reading"]


def test_near_row_override_and_registry_defaults() -> None:
    out = build_wide_peers(OVERVIEW, MARKETS, {"revenue_30d_usd": 30.0, "fdv_usd": 365.0 * 1000})
    assert out["near"]["fdv_to_revenue"] == pytest.approx(1000.0) and out["near"]["percentile"] == 1.0
    assert "overridden" in out["near"]["basis"]
    assert out["terminal_multiple_cap"] == assumptions.value("terminal_multiple_cap")
    assert out["terminal_multiple_floor"] == assumptions.value("terminal_multiple_floor")
    missing = build_wide_peers(OVERVIEW, [m for m in MARKETS if m["id"] != "near"])
    assert missing["near"]["fdv_to_revenue"] is None and missing["near"]["percentile"] is None
    assert "could not be computed" in missing["headline"]


def test_bootstrap_is_deterministic_and_seeded() -> None:
    vals = [3.0, 45.0, 100.0, 230.0, 248.0, 398.0, 444.0, 538.0, 665.0, 985.0, 1032.0, 2511.0, 3299.0, 6169.0, 6653.0]
    a, b = distribution(vals), distribution(list(reversed(vals)))
    assert a["median_ci90"] == distribution(vals)["median_ci90"]
    assert a["bootstrap"] == {"seed": BOOTSTRAP_SEED, "n_resamples": BOOTSTRAP_RESAMPLES, "method": a["bootstrap"]["method"]}
    assert BOOTSTRAP_SEED == 20261114 and BOOTSTRAP_RESAMPLES == 10_000
    lo, hi = a["median_ci90"]
    assert a["min"] <= lo <= a["median"] <= hi <= a["max"]
    # independent recomputation of the same procedure
    arr = np.asarray(vals)
    rng = np.random.default_rng(20261114)
    med = np.median(arr[rng.integers(0, arr.size, size=(10_000, arr.size))], axis=1)
    assert [lo, hi] == [float(x) for x in np.percentile(med, [5, 95])]
    assert b["median"] == a["median"]  # order of the peers does not move the point estimates
    # the interval endpoints are order statistics of the sample, so a different seed may land on the same pair;
    # what must hold is that the recorded seed is the one that was used
    assert distribution(vals, seed=7)["bootstrap"]["seed"] == 7


# ----------------------------------------------------------------------------- collector (MockTransport)
def make_client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


def run_collect(handler: Any, ledger: ProvenanceLedger, args: Any = None) -> dict[str, Any] | None:
    async def go() -> dict[str, Any] | None:
        async with make_client(handler) as client:
            return await collect_wide_peers(client, ledger, args or argparse.Namespace(preset="base"), None, {})

    return asyncio.run(go())


def handler_factory(calls: list[httpx.Request], *, coingecko_statuses: list[int] | None = None, overview_status: int = 200) -> Any:
    statuses = list(coingecko_statuses or [200])

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == "api.coingecko.com":
            status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
            if status != 200:
                return httpx.Response(status, json={"status": {"error_message": "rate limited"}}, headers={"Retry-After": "0"})
            return httpx.Response(200, json=MARKETS)
        if request.url.path == "/overview/fees":
            return httpx.Response(overview_status, json=OVERVIEW if overview_status == 200 else {"message": "down"})
        return httpx.Response(404, json={})

    return handler


def test_collect_makes_one_batched_coingecko_call_and_records_provenance(ledger: ProvenanceLedger) -> None:
    calls: list[httpx.Request] = []
    out = run_collect(handler_factory(calls), ledger)
    assert out is not None and out["status"] == "ok" and out["n_peers"] == 6
    cg = [c for c in calls if c.url.host == "api.coingecko.com"]
    assert len(cg) == 1  # one batched call, never one per coin
    ids = cg[0].url.params["ids"].split(",")
    assert set(COINGECKO_ID_BY_SLUG.values()) <= set(ids) and "near" in ids and cg[0].url.params["vs_currency"] == "usd"
    ov = [c for c in calls if c.url.path == "/overview/fees"]
    assert len(ov) == 1 and ov[0].url.params["dataType"] == "dailyRevenue" and ov[0].url.params["excludeTotalDataChart"] == "true"
    assert out["cap_source"] == "assumptions registry, preset 'base'"
    assert out["terminal_multiple_cap"] == assumptions.value("terminal_multiple_cap", assumptions.preset("base"))
    rec_o, rec_m = ledger.get("defillama", "overview:fees:dailyRevenue"), ledger.get("coingecko", "coins_markets_wide")
    assert rec_o is not None and rec_m is not None and rec_o.ok and rec_m.ok
    assert out["sources"]["revenue"]["sha256"] == rec_o.sha256 and out["sources"]["fdv"]["sha256"] == rec_m.sha256
    assert out["fetched_at_utc"].endswith("Z")


def test_collect_retries_coingecko_429_then_succeeds(ledger: ProvenanceLedger) -> None:
    calls: list[httpx.Request] = []
    out = run_collect(handler_factory(calls, coingecko_statuses=[429, 200]), ledger)
    assert out is not None and out["n_peers"] == 6
    cg = [c for c in calls if c.url.host == "api.coingecko.com"]
    assert len(cg) == 2 and cg[0].url == cg[1].url  # the same batched request, retried once
    assert out["sources"]["fdv"]["attempts"] == 2


def test_collect_returns_none_with_warning_when_coingecko_stays_429(ledger: ProvenanceLedger) -> None:
    calls: list[httpx.Request] = []
    out = run_collect(handler_factory(calls, coingecko_statuses=[429]), ledger)
    assert out is None
    assert len([c for c in calls if c.url.host == "api.coingecko.com"]) == wp._COINGECKO_RETRIES + 1  # bounded, no hammering
    assert any("wide_peers" in w and "CoinGecko" in w and "null" in w for w in ledger.warnings)


def test_collect_returns_none_when_overview_fails_and_skips_coingecko(ledger: ProvenanceLedger) -> None:
    calls: list[httpx.Request] = []
    out = run_collect(handler_factory(calls, overview_status=404), ledger)
    assert out is None
    assert not [c for c in calls if c.url.host == "api.coingecko.com"]
    assert any("wide_peers" in w and "overview" in w for w in ledger.warnings)


def test_collect_falls_back_to_registry_defaults_without_a_preset(ledger: ProvenanceLedger) -> None:
    out = run_collect(handler_factory([]), ledger, argparse.Namespace())
    assert out is not None and out["cap_source"] == "assumptions registry defaults"
    assert out["terminal_multiple_cap"] == assumptions.value("terminal_multiple_cap")


# ----------------------------------------------------------------------------- scorecard claim
def _view(mults: list[float], cap: float) -> dict[str, Any]:
    """A built view whose peers have exactly these multiples (mapped slugs, descending revenue)."""
    slugs = [s for s in COINGECKO_ID_BY_SLUG if s not in wp.FLAG_BY_SLUG][: len(mults)]
    assert len(slugs) == len(mults)
    rows = [chain(s, 1000.0 - i) for i, s in enumerate(slugs)] + [chain("near", 1.0)]
    markets = [market(COINGECKO_ID_BY_SLUG[s], (1000.0 - i) * ANN * m) for i, (s, m) in enumerate(zip(slugs, mults))] + [market("near", 1.0 * ANN * 500)]
    return build_wide_peers(overview(*rows), markets, None, cap, 8.0)


def test_claim_derived_when_cap_at_or_below_p75_with_enough_peers() -> None:
    view = _view([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], cap=60.0)  # P75 = 77.5
    claim = scorecard_claim(view)
    assert claim is not None and set(claim) == {"claim", "status", "value", "source", "confidence", "note"}
    assert claim["status"] == "DERIVED" and claim["confidence"] == "medium"
    assert claim["claim"] == "The model's terminal multiple cap sits inside the observed peer range of FDV/revenue"
    assert "6 of 10" in claim["value"] and "60x" in claim["value"] and "inside the observed range" in claim["note"]


def test_claim_not_supported_when_cap_above_p75_or_too_few_peers() -> None:
    high = scorecard_claim(_view([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], cap=90.0))
    assert high is not None and high["status"] == "NOT_SUPPORTED" and high["confidence"] == "low" and "above the upper quartile" in high["note"]
    few = scorecard_claim(_view([100, 200, 300, 400, 500, 600, 700], cap=60.0))  # 7 peers < 8
    assert few is not None and few["status"] == "NOT_SUPPORTED" and "only 7 peers" in few["note"]


def test_claim_says_so_when_cap_is_below_the_whole_range() -> None:
    below = scorecard_claim(_view([100, 200, 300, 400, 500, 600, 700, 800], cap=60.0))
    assert below is not None and below["status"] == "DERIVED"
    assert "BELOW the whole observed range" in below["note"] and "0 of 8" in below["value"]


def test_claim_none_without_data() -> None:
    assert scorecard_claim(None) is None
    assert scorecard_claim({"n_peers": 0, "distribution": {}}) is None


# ----------------------------------------------------------------------------- memo
def test_memo_markdown_marks_near_and_cap_in_place() -> None:
    out = build_wide_peers(OVERVIEW, MARKETS, None, 60.0, 8.0)
    snap = {"comps": {"median_fdv_to_revenue_ex_near": 2512.3, "near_combined": {"fdv_to_revenue": 120.0, "revenue_30d_usd": 1.0, "fdv_usd": 2.0}}}
    md = memo_markdown(out, snap)
    assert md.startswith(f"**{out['headline']}**")
    lines = md.splitlines()

    def row_index(label: str) -> int:
        return next(i for i, line in enumerate(lines) if line.startswith(f"| {label}"))

    # ascending by multiple: floor 8x, Dexalot 10x, Arbitrum 50x, cap 60x, Tron 100x, NEAR combined 120x, Aptos 200x, NEAR L1 250x, Solana 300x
    order = ["**Model floor**", "Dexalot", "Arbitrum", "**Model cap**", "Tron", "**NEAR (L1 + Intents", "Aptos", "**NEAR (L1 gas revenue only)**", "Solana", "Ethereum"]
    idx = [row_index(label) for label in order]
    assert idx == sorted(idx)
    assert "2,512x (comps.median_fdv_to_revenue_ex_near)" in md
    assert "Base (rank 3 by revenue" in md and "no native token" in md
    assert "Inclusion rules" in md and "Caveats:" in md and "bootstrap 90% interval" in md
    assert "—" not in md  # no em dashes in memo copy
    # without the snapshot the contrast falls back to the recomputed three-peer median and still renders
    assert "recomputed from this view's payloads" in memo_markdown(out, None)
