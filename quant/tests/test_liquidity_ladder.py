"""Offline tests for the liquidity cliff ladder (synthetic venue responses through httpx.MockTransport).

The mock answers each venue in the venue's own wire shape and echoes the requested amount, so every cell
goes through the bench parsers the live run uses. A ``policy(venue, corridor_id, size_usd)`` callback
decides the outcome of each rung: a float (cost in bps), "no_liq", "unsupported", "error" or "slow".
"""
from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from valuo.collectors import execution_bench as eb
from valuo.collectors import liquidity_ladder as ll
from valuo.provenance import ProvenanceLedger

Policy = Callable[[str, str, float], Any]
BY_ID = {c.corridor_id: c for c in eb.CORRIDORS}
ETH_SOL, ETH_BTC, BASE_ARB = BY_ID["eth_usdc_sol_usdc"], BY_ID["eth_usdc_btc"], BY_ID["base_usdc_arb_usdc"]


def _corridor_for(venue: str, request: httpx.Request, body: dict[str, Any]) -> tuple[eb.Corridor, str]:
    params = dict(request.url.params)
    for c in eb.CORRIDORS:
        if venue == "1click" and body.get("originAsset") == c.origin["oneclick_asset_id"] and body.get("destinationAsset") == c.destination["oneclick_asset_id"]:
            return c, str(body["amount"])
        if venue == "relay" and body == eb.relay_payload(c, str(body.get("amount"))):
            return c, str(body["amount"])
        if venue == "lifi" and params == eb.lifi_params(c, params.get("fromAmount", "")):
            return c, params["fromAmount"]
        if venue == "across" and c.origin.get("across_chain_id") is not None and c.destination.get("across_chain_id") is not None \
                and params == eb.across_params(c, params.get("amount", "")):
            return c, params["amount"]
    raise AssertionError(f"unrecognised {venue} request {request.url} {body}")


def make_handler(policy: Policy, tokens: Any, calls: list[tuple[str, str, float]], *, tokens_status: int = 200):
    prices = {t["assetId"]: float(t["price"]) for t in tokens if isinstance(t, dict) and t.get("price") is not None}

    async def handler(request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        if host == "1click.chaindefuser.com" and path == "/v0/tokens":
            return httpx.Response(tokens_status, json=tokens if tokens_status == 200 else {"message": "unavailable"})
        venue = {"1click.chaindefuser.com": "1click", "api.relay.link": "relay", "li.quest": "lifi", "app.across.to": "across"}[host]
        body = json.loads(request.content) if request.content else {}
        if venue == "1click":
            assert body.get("dry") is True, "ladder must never send a non-dry 1Click quote"
        corridor, amount = _corridor_for(venue, request, body)
        size = int(amount) / 10 ** corridor.origin["decimals"]
        calls.append((venue, corridor.corridor_id, size))
        verdict = policy(venue, corridor.corridor_id, size)
        if verdict == "slow":
            await asyncio.sleep(30)
            verdict = 1.0
        if verdict == "error":
            return httpx.Response(500, json={"message": "internal error"})
        if verdict == "no_liq":
            return {
                "1click": httpx.Response(400, json={"message": "No liquidity available"}),
                "relay": httpx.Response(400, json={"errorCode": "INSUFFICIENT_LIQUIDITY", "message": "Amount is higher than the available liquidity. Max amount is $152,923 USD"}),
                "lifi": httpx.Response(404, json={"message": "No available quotes for the requested transfer"}),
                "across": httpx.Response(400, json={"code": "AMOUNT_TOO_HIGH", "message": "Amount exceeds max. deposit limit"}),
            }[venue]
        if verdict == "too_high":  # Relay's size cap: the bench parser files it under "error"; the ladder reads it as a refusal
            return httpx.Response(400, json={"errorCode": "AMOUNT_TOO_HIGH", "message": "Quote amount exceeds the maximum for this pair"})
        if verdict == "unsupported":
            return {
                "1click": httpx.Response(400, json={"message": "tokenIn is not valid"}),
                "relay": httpx.Response(400, json={"errorCode": "UNSUPPORTED_ROUTE", "message": "route not supported"}),
                "lifi": httpx.Response(400, json={"message": "The requested chain is not supported"}),
                "across": httpx.Response(400, json={"code": "ROUTE_NOT_ENABLED", "message": "Route is not enabled."}),
            }[venue]
        bps = float(verdict)
        # Same-stablecoin corridors are scored on raw units, so the synthetic output is sized 1:1 there.
        same_asset = corridor.origin["symbol"] == corridor.destination["symbol"]
        dest_price = 1.0 if same_asset else prices[corridor.destination["oneclick_asset_id"]]
        out_units = size * (1 - bps / 1e4) / dest_price
        out_raw = str(int(round(out_units * 10 ** corridor.destination["decimals"])))
        out_usd = str(out_units * dest_price)
        if venue == "1click":
            return httpx.Response(200, json={"quote": {"amountIn": amount, "amountOut": out_raw, "amountInUsd": str(size), "amountOutUsd": out_usd, "timeEstimate": 20}, "quoteRequest": {}})
        if venue == "relay":
            return httpx.Response(200, json={"details": {"currencyIn": {"amount": amount, "amountUsd": str(size)}, "currencyOut": {"amount": out_raw, "amountFormatted": str(out_units), "amountUsd": out_usd}, "timeEstimate": 5}, "fees": {}})
        if venue == "lifi":
            return httpx.Response(200, json={
                "estimate": {"fromAmount": amount, "toAmount": out_raw, "fromAmountUSD": str(size), "toAmountUSD": out_usd, "executionDuration": 60},
                "action": {"toToken": {"decimals": corridor.destination["decimals"]}}, "tool": "near" if size >= 250_000 else "mayan",
            })
        return httpx.Response(200, json={"outputAmount": out_raw, "totalRelayFee": {"total": str(int(amount) - int(out_raw)), "pct": str(int(bps * 1e14))}, "estimatedFillTimeSec": 2})

    return handler


def run(policy: Policy, tokens: Any, ledger: ProvenanceLedger, **kwargs: Any) -> tuple[dict[str, Any] | None, list[tuple[str, str, float]]]:
    calls: list[tuple[str, str, float]] = []
    tokens_status = kwargs.pop("tokens_status", 200)

    async def go() -> dict[str, Any] | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(make_handler(policy, tokens, calls, tokens_status=tokens_status))) as client:
            return await ll.run_ladder(client, ledger, **kwargs)

    return asyncio.run(go()), calls


def venue_of(data: dict[str, Any], corridor_id: str, venue: str) -> dict[str, Any]:
    corridor = next(c for c in data["corridors"] if c["corridor_id"] == corridor_id)
    return next(v for v in corridor["venues"] if v["venue"] == venue)


def corridor_of(data: dict[str, Any], corridor_id: str) -> dict[str, Any]:
    return next(c for c in data["corridors"] if c["corridor_id"] == corridor_id)


def base_policy(venue: str, corridor_id: str, size: float) -> Any:
    """1Click quotes to $500K, Relay to $250K on BTC and $5M elsewhere, LI.FI to $1M, Across to $2.5M (not on ETH->SOL)."""
    if venue == "1click":
        return 2.0 if size <= 500_000 else "no_liq"
    if venue == "relay":
        if corridor_id == "eth_usdc_btc":
            return 17.0 if size <= 250_000 else "no_liq"
        return 3.0
    if venue == "lifi":
        return 25.0 if size <= 1_000_000 else "no_liq"
    if corridor_id == "eth_usdc_sol_usdc":
        return "unsupported"
    return 1.0 if size <= 2_500_000 else "no_liq"


# ----------------------------------------------------------------------------- formatting and names
def test_fmt_size_and_record_name() -> None:
    assert [ll.fmt_size(s) for s in ll.SIZES_USD] == ["$1K", "$10K", "$50K", "$250K", "$500K", "$1M", "$2.5M", "$5M"]
    assert ll.fmt_size(None) == "none"
    assert ll.record_name("1click", "eth_usdc_btc", 2_500_000.0) == "ladder:1click:eth_usdc_btc:2500000"
    assert len(ll.SIZES_USD) == 8 and list(ll.SIZES_USD) == sorted(ll.SIZES_USD)


# ----------------------------------------------------------------------------- outcome classification
def test_outcomes_are_classified_per_cell(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    data, calls = run(base_policy, load_fixture("oneclick_tokens.json"), ledger)
    assert data is not None
    assert data["sizes_usd"] == list(ll.SIZES_USD) and data["all_quotes_dry"] is True

    one = venue_of(data, "eth_usdc_sol_usdc", "1click")
    assert [c["outcome"] for c in one["cells"]] == ["quoted"] * 5 + ["no_liquidity"] * 3
    assert one["largest_size_quoted_usd"] == 500_000 and one["first_size_refused_usd"] == 1_000_000
    assert one["first_refusal_message"] == "No liquidity available"
    assert one["clean_ladder"] and one["ceiling_observed"] and not one["non_monotone"]
    assert one["cost_bps_at_250k"] == pytest.approx(2.0, abs=0.01) and one["cost_bps_at_largest"] == pytest.approx(2.0, abs=0.01)
    assert one["cells"][0]["cost_basis"] == "raw" and one["cells"][0]["time_estimate_s"] == 20
    assert one["cells"][0]["record_name"] == "ladder:1click:eth_usdc_sol_usdc:1000" and len(one["cells"][0]["sha256"]) == 64
    assert [p["size_usd"] for p in one["cost_curve"]] == [1_000, 10_000, 50_000, 250_000, 500_000]

    # Across refuses the ETH -> SOL route at the first rung: marked as not routing, larger sizes never called.
    across_sol = venue_of(data, "eth_usdc_sol_usdc", "across")
    assert across_sol["routes"] is False and across_sol["largest_size_quoted_usd"] is None
    assert {c["outcome"] for c in across_sol["cells"]} == {"unsupported"}
    assert sum(1 for v, cid, _ in calls if v == "across" and cid == "eth_usdc_sol_usdc") == 1
    # Across is declared unsupported on the BTC corridor by the bench: no HTTP call at all, no venue row invented.
    assert not any(v == "across" and cid == "eth_usdc_btc" for v, cid, _ in calls)
    assert "across" not in [v["venue"] for v in corridor_of(data, "eth_usdc_btc")["venues"]]

    # Cross-asset corridor: cost on USD legs at the 1Click token-list oracle.
    btc = venue_of(data, "eth_usdc_btc", "relay")
    assert btc["largest_size_quoted_usd"] == 250_000 and btc["first_size_refused_usd"] == 500_000
    assert btc["cells"][0]["cost_basis"] == "usd" and btc["cells"][0]["cost_bps"] == pytest.approx(17.0, abs=2.5)  # origin USDC is valued at the list price, not 1.0
    assert "INSUFFICIENT_LIQUIDITY" in btc["first_refusal_message"]
    assert corridor_of(data, "eth_usdc_btc")["cost_basis"] == eb.USD_BASIS_ORACLE
    assert corridor_of(data, "eth_usdc_sol_usdc")["cost_basis"] == "raw_units"

    lifi = venue_of(data, "eth_usdc_btc", "lifi")
    assert lifi["largest_size_quoted_usd"] == 1_000_000 and lifi["via_near_intents_at_largest"] is True

    counts = data["outcome_counts"]
    assert sum(counts.values()) == data["n_cells"] == 8 * (4 + 3 + 4)
    assert counts["not_attempted"] == 0 and counts["error"] == 0
    # Every HTTP response is in the ledger under a ladder:* name, and the bench's own record names are untouched.
    names = {r.name for r in ledger.records}
    assert "ladder:tokens" in names and "tokens" not in names
    assert not any(n.startswith("quote:") for n in names)
    assert data["n_http_records"] == len(calls) == sum(1 for n in names if n.startswith("ladder:")) - 1


def test_corridor_summary_and_headline_when_oneclick_stops_first(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    data, _ = run(base_policy, load_fixture("oneclick_tokens.json"), ledger)
    assert data is not None
    sol = corridor_of(data, "eth_usdc_sol_usdc")
    assert sol["largest_size_quoted_usd"] == 5_000_000 and sol["largest_size_venues"] == ["relay"]
    assert sol["oneclick_largest_size_quoted_usd"] == 500_000 and sol["best_competitor"] == "relay"
    assert sol["oneclick_vs_best_competitor"] == "smaller"
    by_size = {row["size_usd"]: row for row in sol["cheapest_by_size"]}
    assert by_size[250_000]["venue"] == "1click" and by_size[250_000]["n_quoted"] == 3
    assert by_size[1_000_000]["venue"] == "relay" and by_size[1_000_000]["venues_quoted"] == ["relay", "lifi"]
    assert by_size[5_000_000]["venue"] == "relay" and by_size[5_000_000]["n_quoted"] == 1
    arb = corridor_of(data, "base_usdc_arb_usdc")
    assert {row["size_usd"]: row["venue"] for row in arb["cheapest_by_size"]}[2_500_000] == "across"
    btc = corridor_of(data, "eth_usdc_btc")
    assert btc["best_competitor"] == "lifi" and btc["best_competitor_via_near_intents"] is True
    assert data["headline"].startswith("1Click stops quoting at a smaller size than a competitor on 3 of 3 corridors")
    assert "$500K against Relay $5M" in data["headline"] and "depth" not in data["headline"].lower()
    assert "cuts against" in data["takeaway"]
    assert any("not proven hard depth" in c for c in data["caveats"]) and any("one observation" in c for c in data["caveats"])


def test_headline_when_oneclick_matches_or_exceeds(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    def policy(venue: str, corridor_id: str, size: float) -> Any:
        if venue == "1click":
            return 2.0
        return 3.0 if size <= 1_000_000 else "no_liq"

    data, _ = run(policy, load_fixture("oneclick_tokens.json"), ledger, corridors=[ETH_SOL, BASE_ARB])
    assert data is not None
    assert all(c["oneclick_vs_best_competitor"] == "larger" for c in data["corridors"])
    assert data["headline"].startswith("1Click's largest size quoted matches or exceeds every competitor on all 2 corridors")
    claim = ll.scorecard_claim(data)
    assert claim is not None and claim["status"] == "VERIFIED_LIVE_API" and claim["confidence"] == "medium"
    assert "1Click $5M" in claim["value"] and "2 of 2 corridors" in claim["value"]


# ----------------------------------------------------------------------------- budget
def test_budget_exhaustion_yields_not_attempted_never_no_liquidity(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    def policy(venue: str, corridor_id: str, size: float) -> Any:
        if venue == "1click":
            return 2.0 if size <= 10_000 else "slow"
        return "slow"

    data, _ = run(policy, load_fixture("oneclick_tokens.json"), ledger, corridors=[BASE_ARB], budget_s=0.6)
    assert data is not None
    one = venue_of(data, "base_usdc_arb_usdc", "1click")
    assert [c["outcome"] for c in one["cells"]] == ["quoted", "quoted"] + ["not_attempted"] * 6
    assert one["largest_size_quoted_usd"] == 10_000 and one["first_size_refused_usd"] is None
    assert one["ceiling_observed"] is False
    relay = venue_of(data, "base_usdc_arb_usdc", "relay")
    assert {c["outcome"] for c in relay["cells"]} == {"not_attempted"} and relay["n_attempted"] == 0
    assert data["outcome_counts"]["no_liquidity"] == 0 and data["outcome_counts"]["not_attempted"] == 6 + 3 * 8
    assert data["elapsed_s"] < 5
    assert any("not_attempted, not as no liquidity" in w for w in ledger.warnings)
    # 1Click's stop is not observed, so it is not reported as stopping below anyone, and the claim is not graded as verified.
    assert corridor_of(data, "base_usdc_arb_usdc")["oneclick_vs_best_competitor"] != "smaller"
    claim = ll.scorecard_claim(data)
    assert claim is not None and claim["status"] == "NOT_SUPPORTED" and "not measured this run" in claim["value"]
    assert "No 1Click rung at or above $1M was attempted" in claim["note"]


def test_returns_none_when_no_venue_answers(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    data, _ = run(lambda v, c, s: "error", load_fixture("oneclick_tokens.json"), ledger, corridors=[BASE_ARB])
    assert data is None
    assert any("snapshot.liquidity_ladder is null" in w for w in ledger.warnings)


# ----------------------------------------------------------------------------- gaps
def test_gap_in_the_ladder_is_flagged_non_monotone(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    def policy(venue: str, corridor_id: str, size: float) -> Any:
        if venue == "1click":
            if size == 500_000:
                return "no_liq"
            return 2.0 if size <= 1_000_000 else "no_liq"
        return 3.0 if size <= 250_000 else "no_liq"

    data, _ = run(policy, load_fixture("oneclick_tokens.json"), ledger, corridors=[ETH_SOL])
    assert data is not None
    one = venue_of(data, "eth_usdc_sol_usdc", "1click")
    assert one["largest_size_quoted_usd"] == 1_000_000
    assert one["first_size_refused_usd"] == 500_000
    assert one["non_monotone"] is True and one["clean_ladder"] is False
    assert one["contiguous_to_usd"] == 250_000
    assert corridor_of(data, "eth_usdc_sol_usdc")["any_non_monotone"] is True
    assert any("not monotone" in w for w in ledger.warnings)
    claim = ll.scorecard_claim(data)
    assert claim is not None and claim["status"] == "VERIFIED_LIVE_API" and claim["confidence"] == "low"
    assert "Not a clean ladder" in claim["note"]
    assert "(not monotone)" in ll.memo_markdown(data, {})


def test_summarize_venue_pure_cases() -> None:
    def cell(size: float, outcome: str, cost: float | None = None, called: bool = True) -> dict[str, Any]:
        return {"size_usd": size, "outcome": outcome, "cost_bps": cost, "message": "m", "via_near_intents": False, "called": called}

    clean = ll.summarize_venue("relay", [cell(1e3, "quoted", 3.0), cell(1e4, "quoted", 3.0), cell(5e4, "no_liquidity")])
    assert clean["largest_size_quoted_usd"] == 1e4 and clean["first_size_refused_usd"] == 5e4 and clean["clean_ladder"] and not clean["non_monotone"]
    # An error below the largest size quoted is not a refusal (not non-monotone) but the ladder is not clean either.
    holed = ll.summarize_venue("relay", [cell(1e3, "quoted", 3.0), cell(1e4, "error"), cell(5e4, "quoted", 4.0)])
    assert holed["largest_size_quoted_usd"] == 5e4 and not holed["non_monotone"] and not holed["clean_ladder"]
    assert holed["unresolved_below_largest_usd"] == [1e4] and holed["first_size_refused_usd"] is None
    nothing = ll.summarize_venue("lifi", [cell(1e3, "no_liquidity"), cell(1e4, "no_liquidity")])
    assert nothing["largest_size_quoted_usd"] is None and nothing["first_size_refused_usd"] == 1e3 and nothing["routes"] is True
    declared = ll.summarize_venue("across", [cell(1e3, "unsupported", called=False)])
    assert declared["routes"] is False and declared["n_attempted"] == 0 and declared["first_size_refused_usd"] is None


# ----------------------------------------------------------------------------- price basis fallback
def test_token_list_failure_falls_back_to_median_venue_prices(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    data, _ = run(base_policy, load_fixture("oneclick_tokens.json"), ledger, corridors=[ETH_BTC], tokens_status=503, sizes_usd=[1_000, 10_000])
    assert data is not None and data["token_list_ok"] is False
    assert any("/v0/tokens unavailable" in w for w in ledger.warnings)
    btc = corridor_of(data, "eth_usdc_btc")
    assert btc["cost_basis"] == eb.USD_BASIS_MEDIAN_VENUE
    assert venue_of(data, "eth_usdc_btc", "1click")["cells"][0]["cost_bps"] is not None


# ----------------------------------------------------------------------------- collector entry point
def test_skip_bench_returns_none_with_warning_and_no_http(ledger: ProvenanceLedger) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call is allowed when --skip-bench is set")

    async def go() -> Any:
        events = {"bench_done": asyncio.Event(), "forensics_done": asyncio.Event()}
        events["bench_done"].set()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await ll.collect_liquidity_ladder(client, ledger, argparse.Namespace(skip_bench=True), lambda _m: None, events)

    assert asyncio.run(go()) is None
    assert any("liquidity_ladder: skipped" in w for w in ledger.warnings)
    assert ledger.records == []


def test_collector_waits_for_bench_done_and_reads_budget_env(
    ledger: ProvenanceLedger, load_fixture: Callable[[str], Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, float]] = []
    logs: list[str] = []
    monkeypatch.setenv(ll.BUDGET_ENV, "9")
    monkeypatch.setattr(eb, "CORRIDORS", [BASE_ARB])

    async def go() -> Any:
        events = {"bench_done": asyncio.Event(), "forensics_done": asyncio.Event()}
        handler = make_handler(base_policy, load_fixture("oneclick_tokens.json"), calls)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            task = asyncio.ensure_future(ll.collect_liquidity_ladder(client, ledger, argparse.Namespace(skip_bench=False), logs.append, events))
            await asyncio.sleep(0.05)
            assert not task.done() and calls == [] and ledger.records == []  # blocked on the quote race
            events["bench_done"].set()
            return await task

    data = asyncio.run(go())
    assert data is not None and data["budget_s"] == 9.0
    assert data["concurrency"] == eb.DEFAULT_CONCURRENCY and data["request_timeout_s"] == eb.DEFAULT_REQUEST_TIMEOUT_S
    assert logs and logs[0].startswith("liquidity_ladder: ")
    json.dumps(data)  # snapshot-serialisable


def test_budget_env_rejects_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    for raw in ("abc", "-5", "0", ""):
        monkeypatch.setenv(ll.BUDGET_ENV, raw)
        assert ll._budget_from_env() == ll.DEFAULT_BUDGET_S
    monkeypatch.setenv(ll.BUDGET_ENV, "30")
    assert ll._budget_from_env() == 30.0


# ----------------------------------------------------------------------------- claim + memo
def test_scorecard_claim_not_supported_when_oneclick_stops_below_1m(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    data, _ = run(base_policy, load_fixture("oneclick_tokens.json"), ledger)
    claim = ll.scorecard_claim(data)
    assert claim is not None
    assert set(claim) == {"claim", "status", "value", "source", "confidence", "note"}
    assert claim["claim"] == ll.CLAIM_TEXT and claim["status"] == "NOT_SUPPORTED" and claim["confidence"] == "low"
    assert "ETH USDC -> SOL USDC: 1Click $500K, best competitor Relay $5M" in claim["value"]
    assert "LI.FI $1M (routed through NEAR Intents)" in claim["value"]
    assert "0 of 3 corridors" in claim["value"]
    assert ll.scorecard_claim(None) is None and ll.scorecard_claim({"corridors": []}) is None


def test_scorecard_claim_needs_every_corridor(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    def policy(venue: str, corridor_id: str, size: float) -> Any:
        if venue == "1click" and corridor_id == "eth_usdc_sol_usdc":
            return 2.0 if size <= 500_000 else "no_liq"
        return 2.0

    data, _ = run(policy, load_fixture("oneclick_tokens.json"), ledger, corridors=[ETH_SOL, BASE_ARB])
    claim = ll.scorecard_claim(data)
    assert claim is not None and claim["status"] == "NOT_SUPPORTED" and "1 of 2 corridors" in claim["value"]


def test_memo_markdown_table_and_caveats(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    data, _ = run(base_policy, load_fixture("oneclick_tokens.json"), ledger)
    assert data is not None
    md = ll.memo_markdown(data, {})
    assert md.startswith("**1Click stops quoting at a smaller size than a competitor")
    assert "| Corridor | Venue | Largest size quoted | Cost at $250K | Cost at largest size | First size refused |" in md
    assert "| ETH USDC -> SOL USDC | 1Click | $500K | 2.00 bps | 2.00 bps | $1M |" in md
    assert "| ETH USDC -> SOL USDC | Across | does not route | n/a | n/a | n/a |" in md
    assert "via NEAR Intents" in md and "not proven hard depth" in md
    assert "—" not in md and "depth" not in md.split("Limits:")[0].lower()


def test_relay_size_cap_is_a_refusal_not_an_error(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    def policy(venue: str, corridor_id: str, size: float) -> Any:
        if venue == "relay":
            return 1.0 if size <= 2_500_000 else "too_high"
        return 2.0 if size <= 500_000 else "no_liq"

    data, _ = run(policy, load_fixture("oneclick_tokens.json"), ledger, corridors=[BASE_ARB])
    assert data is not None
    relay = venue_of(data, "base_usdc_arb_usdc", "relay")
    assert relay["cells"][-1]["outcome"] == "no_liquidity" and "exceeds the maximum" in relay["cells"][-1]["message"]
    assert relay["largest_size_quoted_usd"] == 2_500_000 and relay["first_size_refused_usd"] == 5_000_000
    assert data["outcome_counts"]["error"] == 0


def test_independent_competitor_excludes_near_intents_resold_quotes(ledger: ProvenanceLedger, load_fixture: Callable[[str], Any]) -> None:
    data, _ = run(base_policy, load_fixture("oneclick_tokens.json"), ledger, corridors=[ETH_BTC])
    assert data is not None
    btc = corridor_of(data, "eth_usdc_btc")
    # LI.FI quotes $1M but from $250K up its tool is "near" (1Click resold); Relay's own route stops at $250K.
    assert btc["best_competitor"] == "lifi" and btc["best_competitor_largest_size_quoted_usd"] == 1_000_000
    assert btc["best_independent_competitor"] == "relay" and btc["best_independent_competitor_largest_size_quoted_usd"] == 250_000
    assert venue_of(data, "eth_usdc_btc", "lifi")["largest_size_quoted_independent_usd"] == 50_000
    assert "1Click execution resold" in data["takeaway"]
