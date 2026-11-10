"""Execution benchmark tests: pure venue parsers against recorded fixtures, friction identity, headroom
sign, aggregates/summary, payload shapes, and the concurrent orchestration over a mock transport.
Only the ``@pytest.mark.live`` test touches the network."""
from __future__ import annotations

import asyncio
import json
import re

import httpx
import pytest

from valuo import config
from valuo.collectors import execution_bench as eb
from valuo.provenance import EMPTY_SHA256, ProvenanceLedger
from valuo.schemas import CorridorClipResult, ExecutionBenchmark, RawRecord, VenueQuote

SHA = "ab" * 32
ETH_SOL = eb.corridor_by_id("eth_usdc_sol_usdc")
ETH_BTC = eb.corridor_by_id("eth_usdc_btc")
BASE_ARB = eb.corridor_by_id("base_usdc_arb_usdc")
USDC_PRICE = 0.999808
BTC_PRICE = 77238.0


def _rec(ok: bool = True, status: int | None = 200, error: str | None = None, source: str = "oneclick") -> RawRecord:
    return RawRecord(
        source=source, name="quote:test", url="https://example.invalid", method="POST", ok=ok, http_status=status, error=error,
        fetched_at_utc="2026-10-30T23:52:16.000Z", latency_ms=12.0, bytes=1, sha256=SHA,
    )


def _ctx(corridor, clip_usd: float, dest_price: float | None = USDC_PRICE, origin_price: float | None = USDC_PRICE) -> eb.QuoteContext:
    return eb.QuoteContext(
        corridor=corridor, clip_usd=clip_usd, amount_in_raw=eb.amount_in_raw_for(corridor, clip_usd),
        dest_price_usd=dest_price, origin_price_usd=origin_price,
    )


def _out_bps(one: VenueQuote, other: VenueQuote) -> float:
    """Output-unit headroom: (out_1click - out_other) / out_other x 1e4."""
    a, b = int(one.amount_out_raw), int(other.amount_out_raw)
    return (a - b) / b * 1e4


def _assert_friction_identity(quote: VenueQuote) -> None:
    assert quote.status == "ok"
    assert quote.amount_in_usd is not None and quote.amount_out_usd is not None
    assert quote.friction_bps_usd == pytest.approx((quote.amount_in_usd - quote.amount_out_usd) / quote.amount_in_usd * 1e4, abs=1e-9)
    if quote.friction_bps_raw is not None:
        in_raw, out_raw = int(quote.amount_in_raw), int(quote.amount_out_raw)
        assert quote.friction_bps_raw == pytest.approx((in_raw - out_raw) / in_raw * 1e4, abs=1e-9)


# ----------------------------------------------------------------------------- corridor definitions
def test_corridor_ids_archetypes_and_venues():
    assert [c.corridor_id for c in eb.CORRIDORS] == ["eth_usdc_sol_usdc", "eth_usdc_btc", "base_usdc_arb_usdc"]
    assert {c.corridor_id: c.archetype for c in eb.CORRIDORS} == {
        "eth_usdc_sol_usdc": "cross_vm", "eth_usdc_btc": "native_btc", "base_usdc_arb_usdc": "evm_l2",
    }
    assert ETH_SOL.venues_attempted == ["1click", "relay", "lifi", "across"]
    assert ETH_BTC.venues_attempted == ["1click", "lifi", "relay"]
    assert getattr(ETH_BTC, "venues_declared_unsupported") == {"across": "Across is EVM-only; no Bitcoin route"}
    assert BASE_ARB.venues_attempted == ["1click", "across", "relay", "lifi"]
    assert eb.amount_in_raw_for(ETH_SOL, 500) == "500000000"
    assert eb.amount_in_raw_for(ETH_SOL, 250_000) == "250000000000"
    with pytest.raises(ValueError):
        eb.corridor_by_id("nope")


def test_corridor_asset_ids_exist_in_recorded_token_list(load_fixture):
    universe = eb.parse_oneclick_tokens(load_fixture("oneclick_tokens.json"), SHA)
    assert universe.ok and universe.count == 210 and "btc" in universe.blockchains and "sol" in universe.blockchains
    for corridor in eb.CORRIDORS:
        assert universe.has(corridor.origin["oneclick_asset_id"]), corridor.corridor_id
        assert universe.has(corridor.destination["oneclick_asset_id"]), corridor.corridor_id
    assert universe.price("nep141:btc.omft.near") == pytest.approx(BTC_PRICE)
    assert eb.parse_oneclick_tokens(None).ok is False
    assert eb.parse_oneclick_tokens({"message": "nope"}).count is None


# ----------------------------------------------------------------------------- payloads (FACTS 2-3)
def test_payloads_follow_live_endpoint_facts():
    deadline = eb.deadline_iso()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z", deadline)
    body = eb.oneclick_payload(ETH_SOL, "50000000000", deadline)
    assert body == {
        "dry": True, "swapType": "EXACT_INPUT", "slippageTolerance": 100,
        "originAsset": "nep141:eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near", "depositType": "ORIGIN_CHAIN",
        "destinationAsset": "nep141:sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near", "amount": "50000000000",
        "refundTo": config.EVM_ADDRESS, "refundType": "ORIGIN_CHAIN", "recipient": config.SOL_ADDRESS,
        "recipientType": "DESTINATION_CHAIN", "deadline": deadline,
    }
    assert eb.oneclick_payload(ETH_BTC, "1", deadline)["recipient"] == config.BTC_ADDRESS
    relay = eb.relay_payload(ETH_SOL, "50000000000")
    assert relay == {
        "user": config.EVM_ADDRESS, "originChainId": 1, "destinationChainId": 792703809,
        "originCurrency": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "destinationCurrency": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "recipient": config.SOL_ADDRESS, "tradeType": "EXACT_INPUT", "amount": "50000000000",
    }
    assert eb.relay_payload(BASE_ARB, "1")["originChainId"] == 8453 and eb.relay_payload(BASE_ARB, "1")["destinationChainId"] == 42161
    assert eb.lifi_params(ETH_SOL, "50000000000") == {
        "fromChain": "ETH", "toChain": "SOL", "fromToken": "USDC", "toToken": "USDC", "fromAmount": "50000000000",
        "fromAddress": config.EVM_ADDRESS, "toAddress": config.SOL_ADDRESS,
    }
    assert eb.lifi_params(BASE_ARB, "1")["fromChain"] == "BAS" and eb.lifi_params(ETH_BTC, "1")["toToken"] == "BTC"
    assert eb.across_params(BASE_ARB, "50000000000") == {
        "inputToken": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "outputToken": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "originChainId": "8453", "destinationChainId": "42161", "amount": "50000000000",
    }


# ----------------------------------------------------------------------------- 1Click parser
def test_parse_oneclick_ok_eth_sol_50k(load_fixture):
    quote = eb.parse_oneclick(load_fixture("oneclick_quote.json"), _rec(), _ctx(ETH_SOL, 50_000))
    assert quote.venue == "1click" and quote.status == "ok" and quote.supported
    assert quote.amount_in_raw == "50000000000" and quote.amount_out_raw == "49989890495"
    assert quote.amount_in_usd == pytest.approx(49990.4) and quote.amount_out_usd == pytest.approx(49980.29243602496)
    assert quote.amount_out_formatted == pytest.approx(49989.890495)
    assert quote.friction_bps_raw == pytest.approx(10109505 / 5e10 * 1e4)
    assert quote.friction_bps_usd == pytest.approx(2.0219, abs=1e-3)
    assert quote.time_estimate_s == 42 and quote.route_tool == "1click-solver-network"
    assert quote.fee_breakdown_usd["withdrawFee"] == pytest.approx(10026 / 1e6 * USDC_PRICE)
    assert quote.fee_breakdown_usd["appFee"] == pytest.approx(49990.4 * 1 / 1e4)
    assert getattr(quote, "app_fee_bps") == 1.0 and quote.raw_record_sha256 == SHA
    # 1Click's own USD legs use the same token-list oracle, so venue and common legs coincide here.
    assert getattr(quote, "usd_basis") == eb.USD_BASIS_ORACLE
    assert getattr(quote, "venue_amount_in_usd") == pytest.approx(49990.4) and getattr(quote, "venue_friction_bps_usd") == pytest.approx(quote.friction_bps_usd, abs=1e-6)
    _assert_friction_identity(quote)


def test_parse_oneclick_no_liquidity_250k(load_fixture):
    quote = eb.parse_oneclick(load_fixture("oneclick_250k.json"), _rec(ok=False, status=400, error="HTTP 400: No liquidity available"), _ctx(ETH_SOL, 250_000))
    assert quote.status == "no_liquidity" and quote.supported is True
    assert quote.error_message == "No liquidity available"
    assert quote.amount_out_raw is None and quote.friction_bps_usd is None and quote.friction_bps_raw is None
    assert quote.amount_in_raw == "250000000000"


def test_parse_oneclick_native_btc_is_usd_normalized_on_the_common_oracle(load_fixture):
    quote = eb.parse_oneclick(load_fixture("oneclick_eth_btc.json"), _rec(), _ctx(ETH_BTC, 50_000, dest_price=BTC_PRICE))
    assert quote.status == "ok" and quote.friction_bps_raw is None  # cross-asset: raw friction is meaningless
    assert quote.amount_out_formatted == pytest.approx(0.64637909)
    # Common oracle: in = 50,000 USDC x token-list USDC price, out = 0.64637909 BTC x token-list BTC price.
    in_usd, out_usd = 50_000 * USDC_PRICE, 0.64637909 * BTC_PRICE
    assert quote.amount_in_usd == pytest.approx(in_usd) and quote.amount_out_usd == pytest.approx(out_usd)
    assert quote.friction_bps_usd == pytest.approx((in_usd - out_usd) / in_usd * 1e4)
    # The venue's own legs survive as venue_* fields with the BTC price they imply.
    assert getattr(quote, "venue_amount_out_usd") == pytest.approx(49922.442637060005)
    assert getattr(quote, "venue_friction_bps_usd") == pytest.approx((49990.3 - 49922.442637060005) / 49990.3 * 1e4)
    assert getattr(quote, "venue_implied_dest_price_usd") == pytest.approx(49922.442637060005 / 0.64637909)
    assert abs(getattr(quote, "venue_oracle_gap_bps")) < 1.0  # 1Click prices BTC off the same list
    assert quote.fee_breakdown_usd["withdrawFee"] == pytest.approx(3400 / 1e8 * BTC_PRICE)
    assert getattr(quote, "app_fee_bps") == 20.0 and quote.time_estimate_s == 490
    _assert_friction_identity(quote)
    # Without the token list the venue legs are the only basis, and the quote says so.
    own = eb.parse_oneclick(load_fixture("oneclick_eth_btc.json"), _rec(), _ctx(ETH_BTC, 50_000, dest_price=None, origin_price=None))
    assert getattr(own, "usd_basis") == eb.USD_BASIS_VENUE and own.amount_in_usd == pytest.approx(49990.3)


def test_echo_mismatch_guard_refuses_to_score_wrong_input(load_fixture):
    # The $50K fixtures echo amountIn 50000000000; asking them to price a $500 request must not yield an "ok" quote.
    ctx = _ctx(ETH_SOL, 500)
    for quote in (
        eb.parse_oneclick(load_fixture("oneclick_quote.json"), _rec(), ctx),
        eb.parse_relay(load_fixture("relay_quote.json"), _rec(source="relay"), ctx),
        eb.parse_lifi(load_fixture("lifi_quote.json"), _rec(source="lifi"), ctx),
    ):
        assert quote.status == "error" and getattr(quote, "error_code") == "AMOUNT_ECHO_MISMATCH"
        assert "50000000000" in quote.error_message and "500000000" in quote.error_message
        assert quote.friction_bps_usd is None and quote.amount_out_raw is None


def test_parse_oneclick_other_failures_are_errors_with_message():
    quote = eb.parse_oneclick({"message": "recipient is not valid"}, _rec(ok=False, status=400), _ctx(ETH_SOL, 500))
    assert quote.status == "error" and quote.error_message == "recipient is not valid"
    transport = eb.parse_oneclick(None, _rec(ok=False, status=None, error="ConnectTimeout: x"), _ctx(ETH_SOL, 500))
    assert transport.status == "error" and transport.error_message == "ConnectTimeout: x"
    none = eb.parse_oneclick(None, None, _ctx(ETH_SOL, 500))
    assert none.status == "error" and none.raw_record_sha256 == EMPTY_SHA256


# ----------------------------------------------------------------------------- Relay parser
def test_parse_relay_ok_eth_sol_50k(load_fixture):
    quote = eb.parse_relay(load_fixture("relay_quote.json"), _rec(source="relay"), _ctx(ETH_SOL, 50_000))
    assert quote.status == "ok" and quote.route_tool == "relay"
    assert quote.amount_out_raw == "49984979876" and quote.amount_out_formatted == pytest.approx(49984.979876)
    # Relay prices USDC 0.04% richer than the 1Click token list; those legs are kept as venue_*, the published legs use one oracle.
    assert getattr(quote, "venue_amount_in_usd") == pytest.approx(50008.95) and getattr(quote, "venue_amount_out_usd") == pytest.approx(49993.927187)
    assert quote.amount_in_usd == pytest.approx(50_000 * USDC_PRICE) and quote.amount_out_usd == pytest.approx(49984.979876 * USDC_PRICE)
    assert quote.friction_bps_usd == pytest.approx(quote.friction_bps_raw, abs=1e-9)  # same oracle on both legs -> usd == raw
    assert quote.friction_bps_raw == pytest.approx(15020124 / 5e10 * 1e4)
    assert quote.time_estimate_s == 24
    assert set(quote.fee_breakdown_usd) == {"gas", "relayer", "relayerGas", "relayerService", "app", "subsidized"}
    assert quote.fee_breakdown_usd["relayer"] == pytest.approx(15.022813)
    assert getattr(quote, "price_impact_pct") == pytest.approx(-0.03)
    _assert_friction_identity(quote)


def test_parse_relay_invalid_currency_is_unsupported_route(load_fixture):
    quote = eb.parse_relay(load_fixture("relay_eth_btc.json"), _rec(ok=False, status=400, source="relay"), _ctx(ETH_BTC, 50_000, BTC_PRICE))
    assert quote.status == "unsupported_route" and quote.supported is False
    assert quote.error_message == "INVALID_INPUT_CURRENCY: Invalid input or output currency"
    assert getattr(quote, "error_code") == "INVALID_INPUT_CURRENCY"
    other = eb.parse_relay({"message": "This address is blocked", "errorCode": "BLOCKED_WALLET_ADDRESS"}, _rec(ok=False, status=400, source="relay"), _ctx(ETH_SOL, 500))
    assert other.status == "error" and other.supported is True


# ----------------------------------------------------------------------------- LI.FI parser
def test_parse_lifi_ok_eth_sol_50k(load_fixture):
    quote = eb.parse_lifi(load_fixture("lifi_quote.json"), _rec(source="lifi"), _ctx(ETH_SOL, 50_000))
    assert quote.status == "ok" and quote.route_tool == "polymerStandard"
    assert quote.amount_out_raw == "49875000000" and quote.amount_out_formatted == pytest.approx(49875.0)
    assert quote.friction_bps_raw == pytest.approx(25.0)
    assert getattr(quote, "venue_amount_in_usd") == pytest.approx(49978.8001) and getattr(quote, "venue_amount_out_usd") == pytest.approx(49748.2681)
    assert quote.amount_in_usd == pytest.approx(50_000 * USDC_PRICE) and quote.amount_out_usd == pytest.approx(49875.0 * USDC_PRICE)
    assert quote.time_estimate_s == 1080
    assert quote.fee_breakdown_usd["LIFI Fixed Fee"] == pytest.approx(124.947) and quote.fee_breakdown_usd["gas"] == pytest.approx(0.0295)
    assert getattr(quote, "tool_name") == "Polymer (Standard)"
    _assert_friction_identity(quote)


def test_parse_lifi_native_btc_routes_through_near_intents(load_fixture):
    quote = eb.parse_lifi(load_fixture("lifi_eth_btc.json"), _rec(source="lifi"), _ctx(ETH_BTC, 50_000, BTC_PRICE))
    assert quote.status == "ok" and quote.route_tool == "near" and getattr(quote, "tool_name") == "NearIntents"
    assert quote.amount_out_formatted == pytest.approx(0.64540895) and quote.friction_bps_raw is None
    in_usd, out_usd = 50_000 * USDC_PRICE, 0.64540895 * BTC_PRICE
    assert quote.friction_bps_usd == pytest.approx((in_usd - out_usd) / in_usd * 1e4)
    assert getattr(quote, "venue_friction_bps_usd") == pytest.approx((49978.8001 - 49624.3534) / 49978.8001 * 1e4)
    # LI.FI's own BTC mark sits ~45 bps under the token list: that gap is what used to be read as 1Click "headroom".
    assert getattr(quote, "venue_oracle_gap_bps") == pytest.approx((49624.3534 / 0.64540895 - BTC_PRICE) / BTC_PRICE * 1e4)
    assert getattr(quote, "venue_oracle_gap_bps") < -30
    assert quote.fee_breakdown_usd["NearIntents Protocol Fee"] == pytest.approx(4.9854)
    assert quote.fee_breakdown_usd["NearIntents App Fee"] == pytest.approx(49.8539)
    assert quote.time_estimate_s == 1390
    _assert_friction_identity(quote)


def test_parse_lifi_failures():
    unsupported = eb.parse_lifi({"message": "Chain ZEC is not supported"}, _rec(ok=False, status=400, source="lifi"), _ctx(ETH_SOL, 500))
    assert unsupported.status == "unsupported_route" and unsupported.supported is False
    empty = eb.parse_lifi({"message": "No available quotes for the requested transfer"}, _rec(ok=False, status=404, source="lifi"), _ctx(ETH_SOL, 500))
    assert empty.status == "no_liquidity" and empty.supported is True
    other = eb.parse_lifi({"message": "Internal error"}, _rec(ok=False, status=500, source="lifi"), _ctx(ETH_SOL, 500))
    assert other.status == "error" and other.error_message == "Internal error"


# ----------------------------------------------------------------------------- Across parser
def test_parse_across_ok_base_arb_50k(load_fixture):
    quote = eb.parse_across(load_fixture("across_quote.json"), _rec(source="across"), _ctx(BASE_ARB, 50_000))
    assert quote.status == "ok" and quote.route_tool == "across"
    assert quote.amount_out_raw == "49994992014" and quote.amount_out_formatted == pytest.approx(49994.992014)
    # Across publishes no USD legs: venue_* are null and the common oracle values both legs (no "USDC = 1.00" invention).
    assert getattr(quote, "venue_amount_in_usd") is None and getattr(quote, "venue_amount_out_usd") is None
    assert quote.amount_in_usd == pytest.approx(50_000 * USDC_PRICE) and quote.amount_out_usd == pytest.approx(49994.992014 * USDC_PRICE)
    assert quote.friction_bps_raw == pytest.approx(5007986 / 5e10 * 1e4)
    assert quote.time_estimate_s == 1
    assert quote.fee_breakdown_usd["totalRelayFee"] == pytest.approx(5.007986)
    assert quote.fee_breakdown_usd["relayerCapitalFee"] == pytest.approx(5.0) and quote.fee_breakdown_usd["lpFee"] == 0.0
    assert getattr(quote, "relay_fee_bps") == pytest.approx(1.0015972)
    assert "token-list oracle" in getattr(quote, "usd_basis_note")
    _assert_friction_identity(quote)
    no_oracle = eb.parse_across(load_fixture("across_quote.json"), _rec(source="across"), _ctx(BASE_ARB, 50_000, dest_price=None, origin_price=None))
    assert no_oracle.status == "ok" and no_oracle.friction_bps_usd is None and no_oracle.friction_bps_raw is not None


def test_parse_across_500_and_route_not_enabled(load_fixture):
    small = eb.parse_across(load_fixture("across_500.json"), _rec(source="across"), _ctx(BASE_ARB, 500))
    assert small.status == "ok" and small.amount_out_formatted == pytest.approx(499.942025)
    assert small.friction_bps_raw == pytest.approx(57975 / 5e8 * 1e4)
    blocked = eb.parse_across(load_fixture("across_eth_sol.json"), _rec(ok=False, status=400, source="across"), _ctx(ETH_SOL, 50_000))
    assert blocked.status == "unsupported_route" and blocked.supported is False
    assert blocked.error_message == "ROUTE_NOT_ENABLED: Route is not enabled." and getattr(blocked, "error_code") == "ROUTE_NOT_ENABLED"
    too_low = eb.parse_across({"outputAmount": "0", "isAmountTooLow": True}, _rec(source="across"), _ctx(BASE_ARB, 1))
    assert too_low.status == "error" and "AMOUNT_TOO_LOW" == getattr(too_low, "error_code")


# ----------------------------------------------------------------------------- friction identity & headroom sign
def test_friction_identity_holds_for_every_recorded_ok_quote(load_fixture):
    quotes = [
        eb.parse_oneclick(load_fixture("oneclick_quote.json"), _rec(), _ctx(ETH_SOL, 50_000)),
        eb.parse_oneclick(load_fixture("oneclick_500.json"), _rec(), _ctx(ETH_SOL, 500)),
        eb.parse_oneclick(load_fixture("oneclick_base_arb.json"), _rec(), _ctx(BASE_ARB, 50_000)),
        eb.parse_relay(load_fixture("relay_quote.json"), _rec(source="relay"), _ctx(ETH_SOL, 50_000)),
        eb.parse_relay(load_fixture("relay_base_arb.json"), _rec(source="relay"), _ctx(BASE_ARB, 50_000)),
        eb.parse_lifi(load_fixture("lifi_quote.json"), _rec(source="lifi"), _ctx(ETH_SOL, 50_000)),
        eb.parse_lifi(load_fixture("lifi_base_arb.json"), _rec(source="lifi"), _ctx(BASE_ARB, 50_000)),
        eb.parse_across(load_fixture("across_quote.json"), _rec(source="across"), _ctx(BASE_ARB, 50_000)),
    ]
    for quote in quotes:
        _assert_friction_identity(quote)
        assert quote.friction_bps_raw is not None  # all USDC -> USDC
    assert eb.friction_bps(100.0, 99.0) == pytest.approx(100.0)
    assert eb.friction_bps(0, 1) is None and eb.friction_bps(None, 1) is None and eb.friction_bps(1, None) is None


def test_headroom_sign_positive_when_1click_pays_out_more(load_fixture):
    quotes = [
        eb.parse_oneclick(load_fixture("oneclick_quote.json"), _rec(), _ctx(ETH_SOL, 50_000)),
        eb.parse_relay(load_fixture("relay_quote.json"), _rec(source="relay"), _ctx(ETH_SOL, 50_000)),
        eb.parse_lifi(load_fixture("lifi_quote.json"), _rec(source="lifi"), _ctx(ETH_SOL, 50_000)),
        eb.parse_across(load_fixture("across_eth_sol.json"), _rec(ok=False, status=400, source="across"), _ctx(ETH_SOL, 50_000)),
    ]
    cell = eb.score_cell(ETH_SOL, 50_000, quotes)
    assert cell.headroom_bps == pytest.approx(_out_bps(quotes[0], quotes[1])) and cell.headroom_bps > 0
    assert cell.best_competitor == "relay" and cell.oneclick_rank == 1 and cell.n_venues_ok == 3
    assert cell.headroom_basis == eb.HEADROOM_BASIS_DEST_UNITS == "dest_units" == eb.HEADROOM_BASIS_OUT_UNITS
    assert cell.price_basis["source"] == eb.USD_BASIS_ORACLE and cell.price_basis["dest_price_usd"] == pytest.approx(USDC_PRICE)
    assert getattr(cell, "oneclick_amount_out_raw") == quotes[0].amount_out_raw and getattr(cell, "best_competitor_amount_out_raw") == quotes[1].amount_out_raw
    assert [q.venue for q in cell.quotes] == ["1click", "relay", "lifi", "across"]


def test_common_price_basis_falls_back_to_median_venue_oracle_when_token_list_failed(load_fixture):
    # No token-list prices: every ok quote starts on its own venue legs (not comparable). score_cell must re-value all of
    # them at ONE price (median of the venues' implied BTC prices) and say so in price_basis.
    quotes = [
        eb.parse_oneclick(load_fixture("oneclick_eth_btc.json"), _rec(), _ctx(ETH_BTC, 50_000, None, None)),
        eb.parse_lifi(load_fixture("lifi_eth_btc.json"), _rec(source="lifi"), _ctx(ETH_BTC, 50_000, None, None)),
    ]
    assert all(getattr(q, "usd_basis") == eb.USD_BASIS_VENUE for q in quotes)
    cell = eb.score_cell(ETH_BTC, 50_000, quotes)
    pb = cell.price_basis
    implied = sorted(getattr(q, "venue_implied_dest_price_usd") for q in quotes)
    assert pb["source"] == eb.USD_BASIS_MEDIAN_VENUE and pb["n_venue_oracles"] == 2
    assert pb["dest_price_usd"] == pytest.approx((implied[0] + implied[1]) / 2)
    for q in cell.quotes:
        assert getattr(q, "usd_basis") == eb.USD_BASIS_MEDIAN_VENUE and getattr(q, "oracle_dest_price_usd") == pytest.approx(pb["dest_price_usd"])
        _assert_friction_identity(q)
        assert q.amount_out_usd == pytest.approx(int(q.amount_out_raw) / 1e8 * pb["dest_price_usd"])
    # With one common price the USD friction ranking agrees with the destination-unit ranking.
    one, lifi = cell.quotes
    assert (one.friction_bps_usd < lifi.friction_bps_usd) == (int(one.amount_out_raw) > int(lifi.amount_out_raw))
    assert cell.headroom_basis == "dest_units" and cell.headroom_bps == pytest.approx(_out_bps(one, lifi))
    # Venue legs survive untouched for the record.
    assert getattr(one, "venue_amount_out_usd") == pytest.approx(float(load_fixture("oneclick_eth_btc.json")["quote"]["amountOutUsd"]))


def test_headroom_sign_negative_when_evm_bridges_beat_1click(load_fixture):
    quotes = [
        eb.parse_oneclick(load_fixture("oneclick_base_arb.json"), _rec(), _ctx(BASE_ARB, 50_000)),
        eb.parse_across(load_fixture("across_quote.json"), _rec(source="across"), _ctx(BASE_ARB, 50_000)),
        eb.parse_relay(load_fixture("relay_base_arb.json"), _rec(source="relay"), _ctx(BASE_ARB, 50_000)),
        eb.parse_lifi(load_fixture("lifi_base_arb.json"), _rec(source="lifi"), _ctx(BASE_ARB, 50_000)),
    ]
    cell = eb.score_cell(BASE_ARB, 50_000, quotes)
    assert cell.headroom_bps < 0 and cell.best_competitor == "across" and cell.oneclick_rank == 3 and cell.n_venues_ok == 4
    assert cell.headroom_bps == pytest.approx(_out_bps(quotes[0], quotes[1]))


def test_headroom_on_output_units_ignores_venue_oracles_and_nulls_without_1click(load_fixture):
    quotes = [
        eb.parse_oneclick(load_fixture("oneclick_eth_btc.json"), _rec(), _ctx(ETH_BTC, 50_000, BTC_PRICE)),
        eb.parse_lifi(load_fixture("lifi_eth_btc.json"), _rec(source="lifi"), _ctx(ETH_BTC, 50_000, BTC_PRICE)),
        eb.parse_relay(load_fixture("relay_eth_btc.json"), _rec(ok=False, status=400, source="relay"), _ctx(ETH_BTC, 50_000, BTC_PRICE)),
        eb.declared_unsupported_quote(_ctx(ETH_BTC, 50_000, BTC_PRICE), "across", "Across is EVM-only; no Bitcoin route"),
    ]
    cell = eb.score_cell(ETH_BTC, 50_000, quotes)
    # 0.64637909 BTC vs 0.64540895 BTC: the physical output decides, not each venue's USD mark of BTC.
    assert getattr(cell, "headroom_basis") == eb.HEADROOM_BASIS_OUT_UNITS
    assert cell.headroom_bps == pytest.approx((64637909 - 64540895) / 64540895 * 1e4) and cell.headroom_bps > 0
    assert cell.best_competitor == "lifi" and cell.n_venues_ok == 2 and cell.oneclick_rank == 1
    # LI.FI's BTC oracle gap (~-45 bps) exceeds the 15 bps headroom: the USD-leg comparison would have been oracle-driven.
    assert getattr(cell, "oracle_gap_exceeds_headroom") is True and "lifi" in getattr(cell, "venue_oracle_gap_bps")
    # The inverse case from the review: a competitor delivering MORE BTC must rank above 1Click even if its own USD legs look worse.
    more_btc = load_fixture("lifi_eth_btc.json")
    more_btc = json.loads(json.dumps(more_btc).replace('"toAmount": "64540895"', '"toAmount": "64700000"'))
    assert more_btc["estimate"]["toAmount"] == "64700000"
    flipped = eb.score_cell(ETH_BTC, 50_000, [quotes[0], eb.parse_lifi(more_btc, _rec(source="lifi"), _ctx(ETH_BTC, 50_000, BTC_PRICE))])
    assert flipped.headroom_bps < 0 and flipped.oneclick_rank == 2 and flipped.best_competitor == "lifi"
    no_1click = eb.score_cell(ETH_SOL, 50_000, [
        eb.parse_oneclick(load_fixture("oneclick_250k.json"), _rec(ok=False, status=400), _ctx(ETH_SOL, 50_000)),
        eb.parse_relay(load_fixture("relay_quote.json"), _rec(source="relay"), _ctx(ETH_SOL, 50_000)),
    ])
    assert no_1click.headroom_bps is None and no_1click.oneclick_rank is None and no_1click.best_competitor == "relay"


# ----------------------------------------------------------------------------- aggregates & summary
def _fixture_results(load_fixture) -> list[CorridorClipResult]:
    return [
        eb.score_cell(ETH_SOL, 50_000, [
            eb.parse_oneclick(load_fixture("oneclick_quote.json"), _rec(), _ctx(ETH_SOL, 50_000)),
            eb.parse_relay(load_fixture("relay_quote.json"), _rec(source="relay"), _ctx(ETH_SOL, 50_000)),
            eb.parse_lifi(load_fixture("lifi_quote.json"), _rec(source="lifi"), _ctx(ETH_SOL, 50_000)),
            eb.parse_across(load_fixture("across_eth_sol.json"), _rec(ok=False, status=400, source="across"), _ctx(ETH_SOL, 50_000)),
        ]),
        eb.score_cell(ETH_SOL, 250_000, [
            eb.parse_oneclick(load_fixture("oneclick_250k.json"), _rec(ok=False, status=400), _ctx(ETH_SOL, 250_000)),
        ]),
        eb.score_cell(ETH_BTC, 50_000, [
            eb.parse_oneclick(load_fixture("oneclick_eth_btc.json"), _rec(), _ctx(ETH_BTC, 50_000, BTC_PRICE)),
            eb.parse_lifi(load_fixture("lifi_eth_btc.json"), _rec(source="lifi"), _ctx(ETH_BTC, 50_000, BTC_PRICE)),
            eb.parse_relay(load_fixture("relay_eth_btc.json"), _rec(ok=False, status=400, source="relay"), _ctx(ETH_BTC, 50_000, BTC_PRICE)),
            eb.declared_unsupported_quote(_ctx(ETH_BTC, 50_000, BTC_PRICE), "across", "Across is EVM-only; no Bitcoin route"),
        ]),
        eb.score_cell(BASE_ARB, 50_000, [
            eb.parse_oneclick(load_fixture("oneclick_base_arb.json"), _rec(), _ctx(BASE_ARB, 50_000)),
            eb.parse_across(load_fixture("across_quote.json"), _rec(source="across"), _ctx(BASE_ARB, 50_000)),
            eb.parse_relay(load_fixture("relay_base_arb.json"), _rec(source="relay"), _ctx(BASE_ARB, 50_000)),
            eb.parse_lifi(load_fixture("lifi_base_arb.json"), _rec(source="lifi"), _ctx(BASE_ARB, 50_000)),
        ]),
    ]


def test_aggregate_medians_and_fee_ceiling(load_fixture):
    results = _fixture_results(load_fixture)
    agg = eb.aggregate(eb.CORRIDORS, results)
    headroom = agg["headroom_by_archetype_bps"]
    assert set(headroom) == {"cross_vm", "native_btc", "evm_l2"}
    assert headroom["cross_vm"] == pytest.approx(results[0].headroom_bps) and headroom["cross_vm"] > 0
    assert headroom["native_btc"] > 0 and headroom["evm_l2"] < 0
    assert agg["headroom_n_by_archetype"] == {"cross_vm": 1, "native_btc": 1, "evm_l2": 1}
    relay, lifi = 15020124 / 5e10 * 1e4, 25.0
    # Ceiling = best competitor per cross_vm cell (Relay here), not the midpoint of two venues' fee schedules.
    assert agg["competitive_fee_ceiling_bps"] == pytest.approx(relay) and agg["competitive_fee_ceiling_n"] == 1
    by_venue = agg["competitor_friction_by_venue_bps"]
    assert by_venue["relay"]["median"] == pytest.approx(relay) and by_venue["lifi"]["median"] == pytest.approx(lifi)
    assert by_venue["relay"]["n"] == by_venue["lifi"]["n"] == 1 and "across" not in by_venue
    empty = eb.aggregate(eb.CORRIDORS, [])
    assert empty["competitive_fee_ceiling_bps"] is None and all(v is None for v in empty["headroom_by_archetype_bps"].values())


def test_summary_note_is_factual_per_archetype(load_fixture):
    note = eb.summarize(eb.CORRIDORS, _fixture_results(load_fixture))
    sentences = [s for s in note.split(". ") if s]
    assert len(sentences) == 3
    assert sentences[0].startswith("cross_vm (ETH USDC -> SOL USDC): $50,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units)")
    assert "$250,000: 1Click no liquidity" in sentences[0] and "across (ROUTE_NOT_ENABLED)" in sentences[0]
    assert sentences[1].startswith("native_btc (ETH USDC -> native BTC): $50,000: 1Click delivers 15.03 bps more than lifi") and "relay (INVALID_INPUT_CURRENCY)" in sentences[1]
    assert "across (Across is EVM-only; no Bitcoin route)" in sentences[1]
    assert "evm_l2 (Base USDC -> Arbitrum USDC): $50,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units)" in sentences[2]
    for word in ("revolutionize", "seamless", "unlock", "delve"):
        assert word not in note.lower()


# ----------------------------------------------------------------------------- orchestration over a mock transport
def _fixture_bytes(probes_dir, name: str) -> bytes:
    return (probes_dir / name).read_bytes()


def _mock_handler(probes_dir, calls: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        calls.append(f"{host}{path}")
        if host == "1click.chaindefuser.com" and path == "/v0/tokens":
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "oneclick_tokens.json"))
        if host == "1click.chaindefuser.com" and path == "/v0/quote":
            body = json.loads(request.content)
            assert body["dry"] is True and body["deadline"].endswith("Z")
            if body["amount"] == "250000000000":
                return httpx.Response(400, content=_fixture_bytes(probes_dir, "oneclick_250k.json"))
            if "btc" in body["destinationAsset"]:
                return httpx.Response(200, content=_fixture_bytes(probes_dir, "oneclick_eth_btc.json"))
            if "arb-" in body["destinationAsset"]:
                return httpx.Response(200, content=_fixture_bytes(probes_dir, "oneclick_base_arb.json"))
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "oneclick_quote.json"))
        if host == "api.relay.link":
            body = json.loads(request.content)
            if body["destinationChainId"] == eb.RELAY_CHAIN_BITCOIN:
                return httpx.Response(400, content=_fixture_bytes(probes_dir, "relay_eth_btc.json"))
            if body["destinationChainId"] == eb.RELAY_CHAIN_ARBITRUM:
                return httpx.Response(200, content=_fixture_bytes(probes_dir, "relay_base_arb.json"))
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "relay_quote.json"))
        if host == "li.quest":
            to_chain = request.url.params["toChain"]
            name = {"SOL": "lifi_quote.json", "BTC": "lifi_eth_btc.json", "ARB": "lifi_base_arb.json"}[to_chain]
            return httpx.Response(200, content=_fixture_bytes(probes_dir, name))
        if host == "app.across.to":
            if request.url.params["destinationChainId"] == str(eb.ACROSS_CHAIN_SOLANA):
                return httpx.Response(400, content=_fixture_bytes(probes_dir, "across_eth_sol.json"))
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "across_quote.json"))
        return httpx.Response(500, json={"message": f"unexpected {host}{path}"})

    return handler


def test_collect_execution_bench_over_mock_transport(ledger: ProvenanceLedger, probes_dir):
    calls: list[str] = []

    async def run() -> ExecutionBenchmark:
        async with httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler(probes_dir, calls))) as client:
            return await eb.collect_execution_bench(ledger, clips_usd=(50_000, 250_000), client=client, budget_s=20)

    bench = asyncio.run(run())
    assert isinstance(bench, ExecutionBenchmark) and bench.clips_usd == [50_000.0, 250_000.0]
    assert [c.corridor_id for c in bench.corridors] == ["eth_usdc_sol_usdc", "eth_usdc_btc", "base_usdc_arb_usdc"]
    assert len(bench.results) == 6 and bench.oneclick_1y_token_universe == 210 and "btc" in bench.oneclick_blockchains
    assert calls.count("1click.chaindefuser.com/v0/tokens") == 1
    # 3 corridors x 2 clips: 4 + 3 + 4 = 11 HTTP quotes per clip; Across is never called for the BTC corridor.
    assert len(calls) == 1 + 2 * 11
    by_cell = {(r.corridor_id, r.clip_usd): r for r in bench.results}
    cross = by_cell[("eth_usdc_sol_usdc", 50_000.0)]
    assert {q.venue: q.status for q in cross.quotes} == {"1click": "ok", "relay": "ok", "lifi": "ok", "across": "unsupported_route"}
    assert cross.headroom_bps > 0 and cross.best_competitor == "relay" and cross.oneclick_rank == 1
    btc = by_cell[("eth_usdc_btc", 50_000.0)]
    assert {q.venue: q.status for q in btc.quotes} == {"1click": "ok", "lifi": "ok", "relay": "unsupported_route", "across": "unsupported_route"}
    across_btc = next(q for q in btc.quotes if q.venue == "across")
    assert across_btc.error_message == "Across is EVM-only; no Bitcoin route" and across_btc.raw_record_sha256 == EMPTY_SHA256
    assert btc.headroom_bps > 0 and getattr(btc, "headroom_basis") == eb.HEADROOM_BASIS_OUT_UNITS
    assert getattr(bench, "usd_friction_basis") == eb.USD_BASIS_ORACLE and getattr(bench, "headroom_basis") == eb.HEADROOM_BASIS_OUT_UNITS
    evm = by_cell[("base_usdc_arb_usdc", 50_000.0)]
    assert evm.n_venues_ok == 4 and evm.headroom_bps < 0 and evm.best_competitor == "across"
    big = by_cell[("eth_usdc_sol_usdc", 250_000.0)]
    assert next(q for q in big.quotes if q.venue == "1click").status == "no_liquidity" and big.headroom_bps is None
    # The mock echoes the $50K fixture for the $250K request: the integrity guard must refuse to score it.
    for venue in ("relay", "lifi"):
        echoed = next(q for q in big.quotes if q.venue == venue)
        assert echoed.status == "error" and getattr(echoed, "error_code") == "AMOUNT_ECHO_MISMATCH"
    assert bench.headroom_by_archetype_bps["cross_vm"] > 0 and bench.headroom_by_archetype_bps["evm_l2"] < 0
    assert bench.competitive_fee_ceiling_bps == pytest.approx(15020124 / 5e10 * 1e4)  # best competitor (Relay) on the one comparable cross_vm cell
    assert getattr(bench, "competitor_friction_by_venue_bps")["lifi"]["median"] == pytest.approx(25.0)
    # LI.FI's BTC oracle gap exceeds the BTC headroom: the collector must say so instead of letting oracles grade execution.
    assert any("oracles disagree" in w for w in ledger.warnings)
    assert "cross_vm" in bench.summary_note and "native_btc" in bench.summary_note and "evm_l2" in bench.summary_note
    records = [r for r in ledger.records if r.name.startswith("quote:")]
    assert len(records) == 22 and all(len(r.sha256) == 64 for r in records)
    assert ledger.get("across", "quote:eth_usdc_btc:50000") is None
    assert ledger.get("oneclick", "quote:eth_usdc_sol_usdc:250000").ok is False
    for result in bench.results:
        for quote in result.quotes:
            if quote.status == "ok":
                _assert_friction_identity(quote)
                assert quote.raw_record_sha256 != EMPTY_SHA256
    # Snapshot-ready: round-trips through JSON with extras intact.
    rebuilt = ExecutionBenchmark.model_validate_json(bench.model_dump_json())
    assert rebuilt.results[0].quotes[0].friction_bps_raw == bench.results[0].quotes[0].friction_bps_raw
    table = eb.format_table(bench)
    assert "eth_usdc_sol_usdc" in table and "headroom" in table


def test_quote_venue_rejects_unknown_venue(ledger: ProvenanceLedger):
    with pytest.raises(ValueError):
        asyncio.run(eb.quote_venue(None, ledger, ETH_SOL, 500, "uniswap"))


def test_budget_exhaustion_marks_pending_quotes_skipped(ledger: ProvenanceLedger, probes_dir):
    async def slow_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v0/tokens":
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "oneclick_tokens.json"))
        await asyncio.sleep(30)
        return httpx.Response(200, json={})

    async def run() -> ExecutionBenchmark:
        async with httpx.AsyncClient(transport=httpx.MockTransport(slow_handler)) as client:
            return await eb.collect_execution_bench(ledger, clips_usd=(500,), corridor_ids=["eth_usdc_sol_usdc"], client=client, budget_s=1.0)

    bench = asyncio.run(run())
    statuses = {q.venue: q.status for q in bench.results[0].quotes}
    assert statuses == {"1click": "skipped", "relay": "skipped", "lifi": "skipped", "across": "skipped"}
    assert bench.headroom_by_archetype_bps == {"cross_vm": None} and bench.competitive_fee_ceiling_bps is None
    assert any("budget" in w for w in ledger.warnings) and any("no venue returned an ok quote" in w for w in ledger.warnings)
    assert getattr(bench, "elapsed_s") < 10


def test_token_list_failure_is_null_not_invented(ledger: ProvenanceLedger, probes_dir):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v0/tokens":
            return httpx.Response(503, json={"message": "down"})
        if request.url.host == "1click.chaindefuser.com":
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "oneclick_quote.json"))
        if request.url.host == "api.relay.link":
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "relay_quote.json"))
        if request.url.host == "li.quest":
            return httpx.Response(200, content=_fixture_bytes(probes_dir, "lifi_quote.json"))
        return httpx.Response(400, content=_fixture_bytes(probes_dir, "across_eth_sol.json"))

    async def run() -> ExecutionBenchmark:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await eb.collect_execution_bench(ledger, clips_usd=(50_000,), corridor_ids=["eth_usdc_sol_usdc"], client=client, budget_s=20)

    bench = asyncio.run(run())
    assert bench.oneclick_1y_token_universe is None and bench.oneclick_blockchains == [] and getattr(bench, "token_list_ok") is False
    oneclick = next(q for q in bench.results[0].quotes if q.venue == "1click")
    assert oneclick.status == "ok" and "withdrawFee" not in oneclick.fee_breakdown_usd  # no live price -> no converted fee
    # Without the token list the cell is re-valued at the median of the venues' own oracles: one common price, never per-venue legs.
    assert getattr(oneclick, "usd_basis") == eb.USD_BASIS_MEDIAN_VENUE and getattr(bench, "usd_friction_basis") == eb.USD_BASIS_MEDIAN_VENUE
    assert bench.results[0].price_basis["source"] == eb.USD_BASIS_MEDIAN_VENUE and bench.results[0].price_basis["n_venue_oracles"] == 3
    assert any("/v0/tokens unavailable" in w for w in ledger.warnings) and any("token-list oracle unavailable" in w for w in ledger.warnings)
    assert bench.results[0].headroom_bps is not None and bench.results[0].headroom_basis == "dest_units"  # unit headroom needs no oracle


# ----------------------------------------------------------------------------- live
@pytest.mark.live
def test_live_cross_vm_500_returns_executable_quotes(ledger: ProvenanceLedger):
    bench = asyncio.run(eb.collect_execution_bench(ledger, clips_usd=(500,), corridor_ids=["eth_usdc_sol_usdc"]))
    cell = bench.results[0]
    ok = [q for q in cell.quotes if q.status == "ok"]
    assert ok, [(q.venue, q.status, q.error_message) for q in cell.quotes]
    for quote in ok:
        _assert_friction_identity(quote)
        assert quote.amount_out_formatted is not None and quote.amount_out_formatted > 0
        assert -50 < (quote.friction_bps_raw if quote.friction_bps_raw is not None else quote.friction_bps_usd) < 500
    assert bench.oneclick_1y_token_universe is None or bench.oneclick_1y_token_universe > 50
    assert ledger.get("oneclick", "tokens") is not None


# ---------------------------------------------------------------------- confidential premium (optional, needs ONECLICK_JWT)
def test_premium_bps_math():
    from valuo.collectors.execution_bench import premium_bps
    assert premium_bps("1000000", "998000") == pytest.approx(20.0)
    assert premium_bps("0", "1") is None and premium_bps(None, "1") is None


def test_confidential_premium_skips_without_key(monkeypatch):
    import asyncio
    from valuo import config as cfg
    from valuo.collectors import execution_bench as eb
    monkeypatch.setattr(cfg, "ONECLICK_JWT", None)
    out = asyncio.run(eb.confidential_premium(None, None, list(eb.CORRIDORS.values()) if isinstance(eb.CORRIDORS, dict) else eb.CORRIDORS, timeout_s=1))
    assert out["status"] == "skipped_no_key" and out["premium_bps"] is None
