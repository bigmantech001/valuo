"""Tests for valuo.collectors.comps: multiples arithmetic, NEAR combination, null handling, provenance.

All offline tests route httpx through a MockTransport that serves the recorded DefiLlama / coins.llama /
CoinGecko fixtures (or injected failures). Expected values are recomputed from the fixture JSON inside
each test so the assertions track the recorded payloads exactly. The single live test re-runs the
collector against the real endpoints and is skipped unless VALUO_LIVE_TESTS=1.
"""
from __future__ import annotations

import asyncio
import json
import statistics
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from valuo.collectors import comps
from valuo.collectors.comps import (
    NEAR_COMBINED_SLUG,
    PEER_SPECS,
    PeerSpec,
    annualize_30d,
    collect_comps,
    collect_comps_async,
    median_ex_near,
    multiple,
    revenue_methodology_from,
)
from valuo.provenance import ProvenanceLedger
from valuo.schemas import PeerComp, PeerComps

_FIXTURE_STEM = {"solana": "solana", "ethereum": "ethereum", "hyperliquid": "hyperliquid", "near": "near", "near-intents": "near_intents"}
_ANNUALIZE = 365.0 / 30.0


def _llama_fixture(probes_dir: Path, kind: str, slug: str) -> bytes:
    return (probes_dir / f"llama_{kind}_{_FIXTURE_STEM[slug]}.json").read_bytes()


def make_handler(
    probes_dir: Path,
    *,
    llama_fail: set[tuple[str, str]] = frozenset(),
    coingecko_status: int = 200,
    prices_status: int = 200,
    calls: list[httpx.Request] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    """Serve fixtures by host/path; inject failures per (slug, "fees"|"rev"), for CoinGecko, or for prices."""

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        url = request.url
        if url.host == "api.coingecko.com":
            if coingecko_status != 200:
                return httpx.Response(coingecko_status, json={"status": {"error_message": "rate limited"}}, headers={"Retry-After": "0"})
            return httpx.Response(200, content=(probes_dir / "coingecko_markets.json").read_bytes())
        if url.host == "coins.llama.fi":
            if prices_status != 200:
                return httpx.Response(prices_status, text="<html>bad gateway</html>", headers={"Retry-After": "0"})
            return httpx.Response(200, content=(probes_dir / "llama_prices.json").read_bytes())
        if url.host == "api.llama.fi" and url.path.startswith("/summary/fees/"):
            slug = url.path.rsplit("/", 1)[1]
            kind = "rev" if url.params.get("dataType") == "dailyRevenue" else "fees"
            if (slug, kind) in llama_fail:
                return httpx.Response(500, json={"message": "injected failure"}, headers={"Retry-After": "0"})
            return httpx.Response(200, content=_llama_fixture(probes_dir, kind, slug))
        return httpx.Response(404, json={"message": f"unexpected url {url}"})

    return handler


def run_collector(handler: Callable[[httpx.Request], httpx.Response], ledger: ProvenanceLedger) -> PeerComps:
    async def go() -> PeerComps:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await collect_comps_async(ledger, client)

    return asyncio.run(go())


def _markets(load_fixture: Callable[[str], Any]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in load_fixture("coingecko_markets.json")}


def _totals(load_fixture: Callable[[str], Any], kind: str, slug: str) -> dict[str, Any]:
    return load_fixture(f"llama_{kind}_{_FIXTURE_STEM[slug]}.json")


# ----------------------------------------------------------------------------- pure helpers
def test_pure_helpers_annualize_multiple_and_median():
    assert annualize_30d(None) is None
    assert annualize_30d(30.0) == pytest.approx(365.0)
    assert multiple(None, 1.0) is None
    assert multiple(1.0, None) is None
    assert multiple(1.0, 0.0) is None  # zero run-rate: no meaningful multiple, reported null rather than inf
    assert multiple(1.0, -5.0) is None
    assert multiple(100.0, 25.0) == pytest.approx(4.0)

    def peer(symbol: str, value: float | None) -> PeerComp:
        return PeerComp(slug=symbol.lower(), symbol=symbol, fdv_to_revenue=value)

    assert median_ex_near([], "fdv_to_revenue") is None
    assert median_ex_near([peer("NEAR", 3.0)], "fdv_to_revenue") is None  # NEAR is excluded even when present
    assert median_ex_near([peer("A", 2.0), peer("B", None), peer("NEAR", 100.0)], "fdv_to_revenue") == pytest.approx(2.0)
    # even count -> mean of the two middle values
    assert median_ex_near([peer("A", 2.0), peer("B", 10.0), peer("C", 4.0), peer("D", 8.0)], "fdv_to_revenue") == pytest.approx(6.0)
    assert median_ex_near([peer("A", 2.0), peer("B", 10.0), peer("C", 4.0)], "fdv_to_revenue") == pytest.approx(4.0)


def test_revenue_methodology_from_parent_and_children(load_fixture):
    # Chain slug: direct methodology.Revenue text.
    near = load_fixture("llama_rev_near.json")
    assert revenue_methodology_from(near) == near["methodology"]["Revenue"]
    # Hyperliquid parent publishes methodology: null; text is composed from live childProtocols entries,
    # skipping the HLP child which states "No revenue.".
    hype = load_fixture("llama_rev_hyperliquid.json")
    assert hype["methodology"] is None
    text = revenue_methodology_from(hype)
    assert text is not None and text.startswith("Parent aggregates child protocols.")
    assert "Assistance Fund" in text
    assert "Hyperliquid Perps:" in text and "Hyperliquid HLP" not in text
    children_texts = [c["methodology"]["Revenue"] for c in hype["childProtocols"] if c["methodology"]["Revenue"] != "No revenue."]
    for child_text in children_texts:
        assert child_text in text
    assert revenue_methodology_from({"total30d": 1}) is None
    assert revenue_methodology_from(None) is None


# ----------------------------------------------------------------------------- happy path
def test_happy_path_multiples_match_fixture_arithmetic(probes_dir: Path, ledger: ProvenanceLedger, load_fixture):
    result = run_collector(make_handler(probes_dir), ledger)
    markets = _markets(load_fixture)
    prices = load_fixture("llama_prices.json")["coins"]

    assert [p.slug for p in result.peers] == [s.slug for s in PEER_SPECS]
    for peer in result.peers:
        spec = next(s for s in PEER_SPECS if s.slug == peer.slug)
        fees, rev = _totals(load_fixture, "fees", peer.slug), _totals(load_fixture, "rev", peer.slug)
        market = markets[spec.coingecko_id]
        assert peer.fees_30d_usd == pytest.approx(fees["total30d"])
        assert peer.revenue_30d_usd == pytest.approx(rev["total30d"])
        assert peer.fees_1y_usd == pytest.approx(fees["total1y"])
        assert peer.revenue_1y_usd == pytest.approx(rev["total1y"])
        assert peer.annualized_fees_usd == pytest.approx(fees["total30d"] * _ANNUALIZE, rel=1e-12)
        assert peer.annualized_revenue_usd == pytest.approx(rev["total30d"] * _ANNUALIZE, rel=1e-12)
        assert peer.fdv_usd == pytest.approx(market["fully_diluted_valuation"])
        assert peer.market_cap_usd == pytest.approx(market["market_cap"])
        assert peer.price_usd == pytest.approx(prices[f"coingecko:{spec.coingecko_id}"]["price"])
        assert peer.price_source == "coins.llama.fi"
        assert peer.fdv_to_fees == pytest.approx(market["fully_diluted_valuation"] / (fees["total30d"] * _ANNUALIZE), rel=1e-12)
        assert peer.fdv_to_revenue == pytest.approx(market["fully_diluted_valuation"] / (rev["total30d"] * _ANNUALIZE), rel=1e-12)
        assert peer.mcap_to_revenue == pytest.approx(market["market_cap"] / (rev["total30d"] * _ANNUALIZE), rel=1e-12)
        assert peer.revenue_methodology  # live text present for every peer (parent or children)

    expected_rev = statistics.median(p.fdv_to_revenue for p in result.peers)
    expected_fees = statistics.median(p.fdv_to_fees for p in result.peers)
    assert result.median_fdv_to_revenue_ex_near == pytest.approx(expected_rev)
    assert result.median_fdv_to_fees_ex_near == pytest.approx(expected_fees)
    assert result.n_peers_in_revenue_median == 3 and result.n_peers_in_fees_median == 3
    assert ledger.warnings == []

    # Notes carry the live methodology text, keyed by slug, for every row including NEAR components.
    assert set(result.notes) >= {"solana", "ethereum", "hyperliquid", "near", "near-intents", NEAR_COMBINED_SLUG}
    assert load_fixture("llama_rev_solana.json")["methodology"]["Revenue"] in result.notes["solana"]
    assert "Assistance Fund" in result.notes["hyperliquid"]
    assert "revenue wallets" in result.notes["near-intents"]  # DefiLlama: swept into NEAR revenue wallets (buyback)
    assert result.fetch_status["coingecko_markets_ok"] is True and result.fetch_status["coins_llama_prices_ok"] is True


def test_near_combined_sums_components_and_uses_near_fdv(probes_dir: Path, ledger: ProvenanceLedger, load_fixture):
    result = run_collector(make_handler(probes_dir), ledger)
    near = result.near_combined
    gas_fees, intents_fees = _totals(load_fixture, "fees", "near"), _totals(load_fixture, "fees", "near-intents")
    gas_rev, intents_rev = _totals(load_fixture, "rev", "near"), _totals(load_fixture, "rev", "near-intents")
    near_market = _markets(load_fixture)["near"]

    assert near.slug == NEAR_COMBINED_SLUG and near.symbol == "NEAR"
    assert near.components == ["near", "near-intents"]
    assert near.components_missing == {"fees": [], "revenue": []}
    assert near.fees_30d_usd == pytest.approx(gas_fees["total30d"] + intents_fees["total30d"])
    assert near.revenue_30d_usd == pytest.approx(gas_rev["total30d"] + intents_rev["total30d"])
    assert near.fees_1y_usd == pytest.approx(gas_fees["total1y"] + intents_fees["total1y"])
    assert near.revenue_1y_usd == pytest.approx(gas_rev["total1y"] + intents_rev["total1y"])
    assert near.fdv_usd == pytest.approx(near_market["fully_diluted_valuation"])
    assert near.market_cap_usd == pytest.approx(near_market["market_cap"])
    assert near.fdv_to_revenue == pytest.approx(near_market["fully_diluted_valuation"] / (near.revenue_30d_usd * _ANNUALIZE), rel=1e-12)
    assert near.fdv_to_fees == pytest.approx(near_market["fully_diluted_valuation"] / (near.fees_30d_usd * _ANNUALIZE), rel=1e-12)
    # Both component methodologies are carried, labeled by slug.
    assert near.revenue_methodology.startswith("near: ") and "| near-intents: " in near.revenue_methodology
    assert "burned" in near.revenue_methodology and "revenue wallets" in near.revenue_methodology

    # Components are exposed individually (extra field) and the Intents component dominates NEAR fees.
    by_slug = {c.slug: c for c in result.near_components}
    assert set(by_slug) == {"near", "near-intents"}
    assert by_slug["near-intents"].fees_30d_usd > by_slug["near"].fees_30d_usd
    assert by_slug["near-intents"].fdv_usd == pytest.approx(near_market["fully_diluted_valuation"])
    # NEAR rows never enter the ex-NEAR medians.
    assert result.median_fdv_to_revenue_ex_near == pytest.approx(statistics.median(p.fdv_to_revenue for p in result.peers))


def test_provenance_records_cover_every_call_and_persist_raw(probes_dir: Path, ledger: ProvenanceLedger):
    calls: list[httpx.Request] = []
    run_collector(make_handler(probes_dir, calls=calls), ledger)
    assert len(calls) == 12  # 5 slugs x (fees + dailyRevenue) + prices + coingecko
    assert len(ledger.records) == 12 and ledger.failures() == []
    assert ledger.sources() == {"coingecko": 1, "defillama": 11}
    names = {r.name for r in ledger.records}
    assert "fees:near-intents:dailyRevenue" in names and "fees:hyperliquid:dailyFees" in names
    assert "prices:current" in names and "coins_markets" in names
    rev = ledger.get("defillama", "fees:solana:dailyRevenue")
    assert rev is not None and "dataType=dailyRevenue" in rev.url and rev.method == "GET"
    assert all(len(r.sha256) == 64 and r.raw_path for r in ledger.records)
    cg = ledger.get("coingecko", "coins_markets")
    assert cg is not None and "ids=near%2Csolana%2Cethereum%2Chyperliquid" in cg.url and cg.attempts == 1


def test_snapshot_section_roundtrips_with_extra_fields(probes_dir: Path, ledger: ProvenanceLedger):
    result = run_collector(make_handler(probes_dir), ledger)
    restored = PeerComps.model_validate_json(result.model_dump_json())
    assert restored.near_combined.fdv_to_revenue == pytest.approx(result.near_combined.fdv_to_revenue)
    # near_components is a typed PeerComps field (schemas.py), so it reads back as PeerComp instances.
    assert [c.slug for c in restored.near_components] == ["near", "near-intents"]
    assert all(isinstance(c, PeerComp) for c in restored.near_components)
    assert [c.fdv_usd for c in restored.near_components] == [c.fdv_usd for c in result.near_components]
    assert restored.notes == result.notes and restored.annualization == comps.ANNUALIZATION_NOTE
    as_json = json.loads(result.model_dump_json())
    assert as_json["peers"][0]["price_source"] == "coins.llama.fi"
    assert as_json["near_combined"]["components_included"] == {"fees": ["near", "near-intents"], "revenue": ["near", "near-intents"]}


# ----------------------------------------------------------------------------- failure handling
def test_coingecko_429_is_retried_four_times_then_fdv_null_with_warning(probes_dir: Path, ledger: ProvenanceLedger, load_fixture):
    calls: list[httpx.Request] = []
    result = run_collector(make_handler(probes_dir, coingecko_status=429, calls=calls), ledger)
    assert sum(1 for c in calls if c.url.host == "api.coingecko.com") == 5  # first try + four retries (429 patience)
    record = ledger.get("coingecko", "coins_markets")
    assert record is not None and record.ok is False and record.attempts == 5 and record.http_status == 429

    for peer in [*result.peers, *result.near_components, result.near_combined]:
        assert peer.fdv_usd is None and peer.market_cap_usd is None
        assert peer.fdv_to_fees is None and peer.fdv_to_revenue is None
        assert peer.fdv_source is None
        # Fee/revenue run-rates still come through: the DefiLlama side did not fail.
        assert peer.fees_30d_usd is not None and peer.annualized_revenue_usd is not None
        # Price still comes from coins.llama.fi.
        assert peer.price_source == "coins.llama.fi"
    assert result.near_combined.fees_30d_usd == pytest.approx(
        _totals(load_fixture, "fees", "near")["total30d"] + _totals(load_fixture, "fees", "near-intents")["total30d"]
    )
    assert result.median_fdv_to_revenue_ex_near is None and result.median_fdv_to_fees_ex_near is None
    assert result.n_peers_in_revenue_median == 0
    assert result.fetch_status["coingecko_markets_ok"] is False
    assert any("CoinGecko /coins/markets failed after 5 attempt(s)" in w for w in ledger.warnings)
    assert any("median_fdv_to_revenue_ex_near null" in w for w in ledger.warnings)


def test_coingecko_403_challenge_is_retried_exactly_once(probes_dir: Path, ledger: ProvenanceLedger):
    calls: list[httpx.Request] = []
    run_collector(make_handler(probes_dir, coingecko_status=403, calls=calls), ledger)
    assert sum(1 for c in calls if c.url.host == "api.coingecko.com") == 2  # a Cloudflare 403 is not a rate-limit ladder
    record = ledger.get("coingecko", "coins_markets")
    assert record is not None and record.ok is False and record.attempts == 2 and record.http_status == 403


def test_single_defillama_failure_nulls_only_that_field_and_labels_partial_sum(probes_dir: Path, ledger: ProvenanceLedger, load_fixture):
    # NEAR L1 gas fees fail; Ethereum dailyRevenue fails. Everything else is served.
    handler = make_handler(probes_dir, llama_fail={("near", "fees"), ("ethereum", "rev")})
    result = run_collector(handler, ledger)
    markets = _markets(load_fixture)

    eth = next(p for p in result.peers if p.slug == "ethereum")
    assert eth.revenue_30d_usd is None and eth.annualized_revenue_usd is None and eth.fdv_to_revenue is None
    assert eth.fees_30d_usd is not None and eth.fdv_to_fees is not None  # fees side intact
    assert eth.revenue_methodology is not None  # methodology text still available from the fees payload
    # Revenue median now runs over SOL and HYPE only (even count -> mean); fees median still over all three.
    sol, hype = (next(p for p in result.peers if p.slug == s) for s in ("solana", "hyperliquid"))
    assert result.median_fdv_to_revenue_ex_near == pytest.approx((sol.fdv_to_revenue + hype.fdv_to_revenue) / 2)
    assert result.n_peers_in_revenue_median == 2 and result.n_peers_in_fees_median == 3

    near = result.near_combined
    intents_fees = _totals(load_fixture, "fees", "near-intents")["total30d"]
    assert near.fees_30d_usd == pytest.approx(intents_fees)  # partial sum, explicitly labeled
    assert near.components_included["fees"] == ["near-intents"] and near.components_missing["fees"] == ["near"]
    assert near.components_missing["revenue"] == []  # revenue side complete
    assert near.fdv_usd == pytest.approx(markets["near"]["fully_diluted_valuation"])
    gas = next(c for c in result.near_components if c.slug == "near")
    assert gas.fees_30d_usd is None and gas.fdv_to_fees is None and gas.revenue_30d_usd is not None

    failed = {(r.name, r.http_status) for r in ledger.failures()}
    assert failed == {("fees:near:dailyFees", 500), ("fees:ethereum:dailyRevenue", 500)}
    assert any("fees summary for near unavailable" in w for w in ledger.warnings)
    assert any("dailyRevenue summary for ethereum unavailable" in w for w in ledger.warnings)
    assert any("near_combined fees sum excludes ['near']" in w for w in ledger.warnings)


def test_price_falls_back_to_coingecko_current_price_when_coins_llama_fails(probes_dir: Path, ledger: ProvenanceLedger, load_fixture):
    result = run_collector(make_handler(probes_dir, prices_status=502), ledger)
    markets = _markets(load_fixture)
    for peer in result.peers:
        spec = next(s for s in PEER_SPECS if s.slug == peer.slug)
        assert peer.price_source == "coingecko"
        assert peer.price_usd == pytest.approx(markets[spec.coingecko_id]["current_price"])
        assert peer.fdv_to_revenue is not None
    assert result.near_combined.price_usd == pytest.approx(markets["near"]["current_price"])
    assert result.fetch_status["coins_llama_prices_ok"] is False
    assert any("coins.llama.fi current prices unavailable" in w for w in ledger.warnings)
    prices_record = ledger.get("defillama", "prices:current")
    assert prices_record is not None and prices_record.ok is False and "non-JSON" in (prices_record.error or "")


def test_everything_down_yields_all_null_rows_not_exceptions(ledger: ProvenanceLedger, monkeypatch: pytest.MonkeyPatch):
    # Transport errors carry no Retry-After, so zero the exponential backoff to keep the test fast;
    # the retry *count* is still exercised (attempts recorded on each failed record).
    monkeypatch.setattr("valuo.provenance._backoff_delay", lambda *_args, **_kwargs: 0.0)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    result = run_collector(handler, ledger)
    assert {r.attempts for r in ledger.by_source("defillama")} == {4}  # default retries=3 -> 4 requests each
    assert ledger.get("coingecko", "coins_markets").attempts == 2  # transport_retries=1: a dead host is not a 429 ladder
    for peer in [*result.peers, *result.near_components, result.near_combined]:
        for field in ("fees_30d_usd", "revenue_30d_usd", "fdv_usd", "price_usd", "fdv_to_fees", "fdv_to_revenue", "revenue_methodology"):
            assert getattr(peer, field) is None, field
    assert result.median_fdv_to_revenue_ex_near is None and result.median_fdv_to_fees_ex_near is None
    assert len(ledger.failures()) == 12
    assert "methodology" not in " ".join(w for w in ledger.warnings if "publishes no Revenue methodology" in w)  # no methodology warning without a payload
    assert any("no live price" in w for w in ledger.warnings)


def test_sync_entry_point_runs_outside_an_event_loop(probes_dir: Path, ledger: ProvenanceLedger):
    with_client = httpx.AsyncClient(transport=httpx.MockTransport(make_handler(probes_dir)))
    result = collect_comps(ledger, with_client)
    assert isinstance(result, PeerComps) and len(result.peers) == 3
    assert result.near_combined.fdv_to_revenue is not None


def test_sync_entry_point_rejects_foreign_client_inside_running_loop(probes_dir: Path, ledger: ProvenanceLedger):
    async def go() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(make_handler(probes_dir))) as client:
            with pytest.raises(RuntimeError, match="collect_comps_async"):
                collect_comps(ledger, client)

    asyncio.run(go())


def test_peer_spec_table_is_the_contracted_universe():
    assert [(s.slug, s.symbol, s.coingecko_id) for s in PEER_SPECS] == [
        ("solana", "SOL", "solana"), ("ethereum", "ETH", "ethereum"), ("hyperliquid", "HYPE", "hyperliquid"),
    ]
    assert [(s.slug, s.symbol) for s in comps.NEAR_COMPONENT_SPECS] == [("near", "NEAR"), ("near-intents", "NEAR")]
    assert comps.COINGECKO_IDS == ("near", "solana", "ethereum", "hyperliquid")
    assert isinstance(PEER_SPECS[0], PeerSpec)


# ----------------------------------------------------------------------------- live
@pytest.mark.live
def test_live_comps_table(ledger: ProvenanceLedger):
    result = collect_comps(ledger)
    assert result.fetched_at_utc.endswith("Z")
    assert [p.slug for p in result.peers] == ["solana", "ethereum", "hyperliquid"]
    near = result.near_combined
    assert near.fees_30d_usd is not None and near.fees_30d_usd > 1e5
    assert near.revenue_30d_usd is not None and 0 < near.revenue_30d_usd <= near.fees_30d_usd
    assert "revenue wallets" in (near.revenue_methodology or "") or "burned" in (near.revenue_methodology or "")
    with_rev_multiple = [p for p in result.peers if p.fdv_to_revenue is not None]
    if result.fetch_status["coingecko_markets_ok"]:
        assert len(with_rev_multiple) >= 2
        assert result.median_fdv_to_revenue_ex_near is not None and result.median_fdv_to_revenue_ex_near > 0
        assert near.fdv_usd is not None and near.fdv_usd > 1e9
    else:
        assert near.fdv_usd is None and any("CoinGecko" in w for w in ledger.warnings)
    assert all(r.sha256 and len(r.sha256) == 64 for r in ledger.records)
    assert ledger.sources().get("defillama", 0) == 11
