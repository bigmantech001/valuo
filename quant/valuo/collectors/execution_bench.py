"""Live cross-venue execution benchmark: NEAR Intents 1Click vs Relay, LI.FI and Across.

Why this collector exists (docs/MODEL_DESIGN.md section 4.2, QUANT_PIPELINE_SPEC section 3): the public
take-rate a router can sustain is bounded by what competing routers deliver *net of all fees* on the
same corridor and clip. That bound is measured here from executable quotes (1Click ``"dry": true``
quotes, Relay / LI.FI / Across quote endpoints) rather than from published fee schedules. Every
response is hashed and recorded through ``valuo.provenance``; nothing is retried into a guess.

Definitions
    friction_bps_usd = (amount_in_usd - amount_out_usd) / amount_in_usd * 1e4 where BOTH legs of EVERY
                       venue in a cell are valued with ONE common price, recorded in the cell as
                       ``price_basis``: the live 1Click token-list prices of the origin and destination
                       assets (``usd_basis = "oneclick_token_list_oracle"``), or, when that list failed,
                       the median of the venues' own implied prices (``"median_venue_oracle"``). Each
                       venue's own USD legs are kept as ``venue_amount_in_usd`` / ``venue_amount_out_usd`` /
                       ``venue_friction_bps_usd`` with the implied destination price, because venues price
                       the same BTC 20-30 bps apart and that gap would otherwise masquerade as execution
                       quality (the review case: Relay delivered more BTC than 1Click on every native_btc
                       cell while its own USD mark made it look worse).
    friction_bps_raw = (amount_in_raw - amount_out_raw) / amount_in_raw * 1e4
                       only when origin and destination are the same 6-dp stablecoin (USDC -> USDC).
    headroom_bps     = (out_1click - out_best_competitor) / out_best_competitor * 1e4 on the PHYSICAL
                       destination units (amount_out_raw) per unit of the identical raw input: every venue
                       in a cell delivers the same asset for the same raw input, so the ranking needs no
                       oracle at all (``headroom_basis = "dest_units"``; positive: 1Click pays out more).
    oneclick_rank    = 1 + number of ok competitors that delivered strictly more destination units.
    competitive_fee_ceiling_bps = median over cross_vm cells of the BEST competitor's friction
                       (raw where present, else usd) - the level a public take-rate cannot exceed long-run.
                       Per-venue medians are published alongside; the statistic no longer depends on how
                       many venues or clips were polled the way a pooled median did.
    headroom_by_archetype_bps   = median cell headroom per archetype over cells with 1Click ok and
                                  at least one competitor ok.

Status mapping (``VenueQuote.status``)
    1Click  2xx with ``quote``                      -> ok
            4xx "No liquidity available"            -> no_liquidity   (supported=True: route exists, no fill)
    Relay   ``errorCode`` in RELAY_ROUTE_ERROR_CODES -> unsupported_route
            ``errorCode`` in RELAY_NO_LIQUIDITY_CODES -> no_liquidity
    LI.FI   message matching "not supported" etc.   -> unsupported_route
            "No available quotes ..."               -> no_liquidity
    Across  ``code`` ROUTE_NOT_ENABLED / UNSUPPORTED -> unsupported_route
            ``code`` AMOUNT_TOO_HIGH                 -> no_liquidity
            never called for non-EVM destinations  -> unsupported_route (declared, no HTTP)
    anything else (transport error, unknown body)   -> error, with the verbatim message
    cancelled by the wall-clock budget              -> skipped

Request payloads follow docs/LIVE_ENDPOINT_FACTS.md sections 2-3 exactly.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

import httpx

from valuo import config
from valuo.provenance import EMPTY_SHA256, ProvenanceLedger, fetch_json, utc_now_iso
from valuo.schemas import (
    Corridor,
    CorridorClipResult,
    ExecutionBenchmark,
    RawRecord,
    VenueQuote,
)

__all__ = [
    "CORRIDORS", "VENUES", "ONECLICK", "VENUE_SOURCE", "DEFAULT_CLIPS_USD",
    "USD_BASIS_ORACLE", "USD_BASIS_VENUE", "USD_BASIS_MEDIAN_VENUE", "HEADROOM_BASIS_DEST_UNITS", "HEADROOM_BASIS_OUT_UNITS",
    "QuoteContext", "TokenUniverse",
    "collect_execution_bench", "quote_venue", "fetch_oneclick_tokens",
    "corridor_by_id", "amount_in_raw_for", "deadline_iso",
    "oneclick_payload", "relay_payload", "lifi_params", "across_params",
    "parse_oneclick_tokens", "parse_oneclick", "parse_relay", "parse_lifi", "parse_across",
    "friction_bps", "common_price_basis", "score_cell", "aggregate", "summarize",
]

# ----------------------------------------------------------------------------- constants
ONECLICK = "1click"
VENUES: tuple[str, ...] = ("1click", "relay", "lifi", "across")
VENUE_SOURCE: dict[str, str] = {"1click": "oneclick", "relay": "relay", "lifi": "lifi", "across": "across"}
DEFAULT_CLIPS_USD: tuple[float, ...] = (500.0, 50_000.0, 250_000.0)
DEFAULT_BUDGET_S = 45.0
DEFAULT_CONCURRENCY = 8
DEFAULT_REQUEST_TIMEOUT_S = 25.0
# Quote endpoints are latency-sensitive and the whole matrix shares a 45 s budget: one retry on 429/5xx.
QUOTE_RETRIES = 1

RELAY_ROUTE_ERROR_CODES = frozenset({
    "INVALID_INPUT_CURRENCY", "INVALID_OUTPUT_CURRENCY", "UNSUPPORTED_CHAIN", "UNSUPPORTED_CURRENCY",
    "UNSUPPORTED_ROUTE", "NO_SWAP_ROUTES_FOUND", "NO_INTERNAL_SWAP_ROUTES_FOUND", "ROUTE_TEMPORARILY_RESTRICTED",
})
RELAY_NO_LIQUIDITY_CODES = frozenset({"INSUFFICIENT_LIQUIDITY", "SWAP_IMPACT_TOO_HIGH", "NO_QUOTES"})
ACROSS_ROUTE_ERROR_CODES = frozenset({"ROUTE_NOT_ENABLED", "UNSUPPORTED_CHAIN", "UNSUPPORTED_TOKEN"})
ACROSS_NO_LIQUIDITY_CODES = frozenset({"AMOUNT_TOO_HIGH"})
_LIFI_UNSUPPORTED = re.compile(r"not supported|unsupported|invalid chain|unknown chain|invalid token|unknown token", re.I)
_LIFI_NO_QUOTES = re.compile(r"no available quotes|no quotes|no routes? (?:found|available)", re.I)
_ONECLICK_NO_LIQUIDITY = re.compile(r"no liquidity", re.I)

ROUTE_TOOL: dict[str, str] = {"1click": "1click-solver-network", "relay": "relay", "across": "across"}
_ACROSS_USD_NOTE = "Across returns no USD legs; amount_in_usd / amount_out_usd are valued at the cell's common price (1Click token-list oracle, else the median of venue oracles; null if neither exists); raw USDC friction is exact"
USD_BASIS_ORACLE = "oneclick_token_list_oracle"
USD_BASIS_VENUE = "venue_oracle"  # transient: a quote's own legs before score_cell applies the cell's common price
USD_BASIS_MEDIAN_VENUE = "median_venue_oracle"
HEADROOM_BASIS_DEST_UNITS = "dest_units"
HEADROOM_BASIS_OUT_UNITS = HEADROOM_BASIS_DEST_UNITS  # former name; same value

# Asset identifiers verified in docs/LIVE_ENDPOINT_FACTS.md section 2-3 and re-verified against the live
# 1Click token list on every run (missing ids raise a ledger warning, never a silent substitution).
_ETH_USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
_BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
_ARB_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_SOL_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
RELAY_CHAIN_ETHEREUM, RELAY_CHAIN_BASE, RELAY_CHAIN_ARBITRUM = 1, 8453, 42161
RELAY_CHAIN_SOLANA = 792703809
RELAY_CHAIN_BITCOIN = 8253038
# Relay's native-BTC currency id as published by GET https://api.relay.link/chains (chain 8253038, vm "bvm");
# any other placeholder returns INVALID_INPUT_CURRENCY (docs/LIVE_ENDPOINT_FACTS.md section 3 misattributed that
# error to the route). Verified live 2026-10-31 together with web/src/lib/corridors.ts.
RELAY_NATIVE_BTC = "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqmql8k8"
ACROSS_CHAIN_SOLANA = 34268394551451


def _leg(
    *, chain: str, symbol: str, decimals: int, oneclick_asset_id: str, address: str,
    relay_chain_id: int | None, relay_currency: str | None, lifi_chain: str, lifi_token: str,
    across_chain_id: int | None, across_token: str | None,
) -> dict[str, Any]:
    return {
        "chain": chain, "symbol": symbol, "decimals": decimals, "oneclick_asset_id": oneclick_asset_id,
        "address": address, "relay_chain_id": relay_chain_id, "relay_currency": relay_currency,
        "lifi_chain": lifi_chain, "lifi_token": lifi_token, "across_chain_id": across_chain_id, "across_token": across_token,
    }


_ETH_USDC_LEG = _leg(
    chain="eth", symbol="USDC", decimals=6, oneclick_asset_id=f"nep141:eth-{_ETH_USDC}.omft.near",
    address=config.EVM_ADDRESS, relay_chain_id=RELAY_CHAIN_ETHEREUM, relay_currency=_ETH_USDC,
    lifi_chain="ETH", lifi_token="USDC", across_chain_id=RELAY_CHAIN_ETHEREUM, across_token=_ETH_USDC,
)

CORRIDORS: list[Corridor] = [
    Corridor(
        corridor_id="eth_usdc_sol_usdc", label="ETH USDC -> SOL USDC", archetype="cross_vm",
        origin=_ETH_USDC_LEG,
        destination=_leg(
            chain="sol", symbol="USDC", decimals=6, oneclick_asset_id="nep141:sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near",
            address=config.SOL_ADDRESS, relay_chain_id=RELAY_CHAIN_SOLANA, relay_currency=_SOL_USDC_MINT,
            lifi_chain="SOL", lifi_token="USDC", across_chain_id=ACROSS_CHAIN_SOLANA, across_token=_SOL_USDC_MINT,
        ),
        venues_attempted=["1click", "relay", "lifi", "across"],
        venues_declared_unsupported={},
    ),
    Corridor(
        corridor_id="eth_usdc_btc", label="ETH USDC -> native BTC", archetype="native_btc",
        origin=_ETH_USDC_LEG,
        destination=_leg(
            chain="btc", symbol="BTC", decimals=8, oneclick_asset_id="nep141:btc.omft.near",
            address=config.BTC_ADDRESS, relay_chain_id=RELAY_CHAIN_BITCOIN, relay_currency=RELAY_NATIVE_BTC,
            lifi_chain="BTC", lifi_token="BTC", across_chain_id=None, across_token=None,
        ),
        venues_attempted=["1click", "lifi", "relay"],
        venues_declared_unsupported={"across": "Across is EVM-only; no Bitcoin route"},
    ),
    Corridor(
        corridor_id="base_usdc_arb_usdc", label="Base USDC -> Arbitrum USDC", archetype="evm_l2",
        origin=_leg(
            chain="base", symbol="USDC", decimals=6, oneclick_asset_id=f"nep141:base-{_BASE_USDC.lower()}.omft.near",
            address=config.EVM_ADDRESS, relay_chain_id=RELAY_CHAIN_BASE, relay_currency=_BASE_USDC,
            lifi_chain="BAS", lifi_token="USDC", across_chain_id=RELAY_CHAIN_BASE, across_token=_BASE_USDC,
        ),
        destination=_leg(
            chain="arb", symbol="USDC", decimals=6, oneclick_asset_id=f"nep141:arb-{_ARB_USDC.lower()}.omft.near",
            address=config.EVM_ADDRESS, relay_chain_id=RELAY_CHAIN_ARBITRUM, relay_currency=_ARB_USDC,
            lifi_chain="ARB", lifi_token="USDC", across_chain_id=RELAY_CHAIN_ARBITRUM, across_token=_ARB_USDC,
        ),
        venues_attempted=["1click", "across", "relay", "lifi"],
        venues_declared_unsupported={},
    ),
]
_CORRIDOR_INDEX: dict[str, Corridor] = {c.corridor_id: c for c in CORRIDORS}


def corridor_by_id(corridor_id: str) -> Corridor:
    """Corridor definition for ``corridor_id`` (ValueError listing the known ids when unknown)."""
    try:
        return _CORRIDOR_INDEX[corridor_id]
    except KeyError as exc:
        raise ValueError(f"unknown corridor {corridor_id!r}; known: {sorted(_CORRIDOR_INDEX)}") from exc


def _declared_unsupported(corridor: Corridor) -> dict[str, str]:
    value = getattr(corridor, "venues_declared_unsupported", None)
    return dict(value) if isinstance(value, Mapping) else {}


def _same_asset(corridor: Corridor) -> bool:
    """True for USDC -> USDC style corridors where raw-unit friction is meaningful."""
    o, d = corridor.origin, corridor.destination
    return o.get("symbol") == d.get("symbol") and o.get("decimals") == d.get("decimals")


# ----------------------------------------------------------------------------- small helpers
def _f(value: Any) -> float | None:
    """Float from a str/number API field; None for missing, empty or non-numeric."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def _int_str(value: Any) -> int | None:
    """Integer from a raw-unit string field (digits only), else None."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def friction_bps(amount_in: float | int | None, amount_out: float | int | None) -> float | None:
    """(amount_in - amount_out) / amount_in * 1e4; None when either leg is missing or amount_in <= 0."""
    if amount_in is None or amount_out is None or amount_in <= 0:
        return None
    return (float(amount_in) - float(amount_out)) / float(amount_in) * 1e4


def amount_in_raw_for(corridor: Corridor, clip_usd: float) -> str:
    """Raw origin units for a USD clip: clip x 10^origin_decimals (all corridors originate in USDC ~ 1 USD)."""
    if clip_usd <= 0:
        raise ValueError(f"clip_usd must be positive, got {clip_usd}")
    return str(int(round(clip_usd * 10 ** int(corridor.origin["decimals"]))))


def deadline_iso(now: datetime | None = None, hours: float = 2.0) -> str:
    """1Click quote deadline: now + ``hours`` as ISO-8601 UTC with millisecond precision and Z suffix."""
    base = now or datetime.now(timezone.utc)
    return (base + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


@dataclass(frozen=True)
class QuoteContext:
    """Everything a venue parser needs besides the response: the cell and live destination price."""

    corridor: Corridor
    clip_usd: float
    amount_in_raw: str
    dest_price_usd: float | None = None  # live 1Click token price of the destination asset (USD per unit)
    origin_price_usd: float | None = None

    @property
    def same_asset(self) -> bool:
        return _same_asset(self.corridor)

    @property
    def dest_decimals(self) -> int:
        return int(self.corridor.destination["decimals"])

    @property
    def oracle_origin_price_usd(self) -> float | None:
        """Origin-asset USD price for the common oracle; a same-asset corridor may reuse the destination price."""
        if self.origin_price_usd is not None:
            return self.origin_price_usd
        return self.dest_price_usd if self.same_asset else None


def _record_fields(record: RawRecord | None) -> dict[str, Any]:
    if record is None:
        return {"latency_ms": 0.0, "fetched_at_utc": utc_now_iso(), "raw_record_sha256": EMPTY_SHA256}
    return {"latency_ms": record.latency_ms, "fetched_at_utc": record.fetched_at_utc, "raw_record_sha256": record.sha256}


def _failure(ctx: QuoteContext, venue: str, record: RawRecord | None, *, status: str, supported: bool, message: str | None, **extra: Any) -> VenueQuote:
    return VenueQuote(
        venue=venue, supported=supported, status=status, error_message=(message or "no response")[:300],
        amount_in_raw=ctx.amount_in_raw, **_record_fields(record), **extra,
    )


def _success(
    ctx: QuoteContext, venue: str, record: RawRecord | None, *, amount_in_usd: float | None, amount_out_raw: str | None,
    amount_out_formatted: float | None, amount_out_usd: float | None, time_estimate_s: float | None, route_tool: str | None,
    fee_breakdown_usd: dict[str, float], **extra: Any,
) -> VenueQuote:
    """Assemble an ok quote; friction is computed here so every venue shares one identity.

    ``amount_in_usd`` / ``amount_out_usd`` passed in are the VENUE's own USD legs (None for Across). The
    published legs are re-valued with the 1Click token-list oracle when both prices are known, so a
    30 bps gap between venue oracles cannot pose as execution quality; the venue legs survive as
    ``venue_*`` fields together with the destination price they imply.
    """
    in_raw = _int_str(ctx.amount_in_raw)
    out_raw = _int_str(amount_out_raw)
    out_units = (out_raw / 10**ctx.dest_decimals) if out_raw is not None else amount_out_formatted
    venue_in_usd, venue_out_usd = amount_in_usd, amount_out_usd
    venue_implied_price = (venue_out_usd / out_units) if (venue_out_usd is not None and out_units) else None
    origin_price = ctx.oracle_origin_price_usd
    if origin_price is not None and ctx.dest_price_usd is not None and in_raw is not None and out_units is not None:
        in_usd = in_raw / 10 ** int(ctx.corridor.origin["decimals"]) * origin_price
        out_usd = out_units * ctx.dest_price_usd
        usd_basis = USD_BASIS_ORACLE
    else:
        in_usd, out_usd, usd_basis = venue_in_usd, venue_out_usd, USD_BASIS_VENUE
    oracle_gap_bps = (
        (venue_implied_price - ctx.dest_price_usd) / ctx.dest_price_usd * 1e4
        if venue_implied_price is not None and ctx.dest_price_usd else None
    )
    return VenueQuote(
        venue=venue, supported=True, status="ok", error_message=None, amount_in_raw=ctx.amount_in_raw,
        amount_in_usd=in_usd, amount_out_raw=str(out_raw) if out_raw is not None else None,
        amount_out_formatted=amount_out_formatted, amount_out_usd=out_usd,
        friction_bps_usd=friction_bps(in_usd, out_usd),
        friction_bps_raw=friction_bps(in_raw, out_raw) if ctx.same_asset else None,
        time_estimate_s=time_estimate_s, route_tool=route_tool, fee_breakdown_usd=fee_breakdown_usd,
        usd_basis=usd_basis, oracle_dest_price_usd=ctx.dest_price_usd, oracle_origin_price_usd=origin_price,
        venue_amount_in_usd=venue_in_usd, venue_amount_out_usd=venue_out_usd,
        venue_friction_bps_usd=friction_bps(venue_in_usd, venue_out_usd),
        venue_implied_dest_price_usd=venue_implied_price, venue_oracle_gap_bps=oracle_gap_bps,
        **_record_fields(record), **extra,
    )


def _message(parsed: Any, record: RawRecord | None, *keys: str) -> str | None:
    if isinstance(parsed, dict):
        for key in keys:
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return record.error if record is not None else None


def _echo_mismatch(ctx: QuoteContext, venue: str, record: RawRecord | None, echoed_amount_in: Any) -> VenueQuote | None:
    """Integrity guard: a quote priced for a different input than we sent must not be scored as ok."""
    echoed = _int_str(echoed_amount_in)
    requested = _int_str(ctx.amount_in_raw)
    if echoed is None or requested is None or echoed == requested:
        return None
    return _failure(
        ctx, venue, record, status="error", supported=True,
        message=f"venue echoed amountIn {echoed} != requested {requested}", error_code="AMOUNT_ECHO_MISMATCH",
    )


# ----------------------------------------------------------------------------- 1Click token universe
@dataclass
class TokenUniverse:
    """The live 1Click asset list: existence check for corridor asset ids plus USD prices for fee conversion."""

    ok: bool
    by_asset_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    count: int | None = None
    blockchains: list[str] = field(default_factory=list)
    record_sha256: str | None = None

    def price(self, asset_id: str) -> float | None:
        token = self.by_asset_id.get(asset_id)
        return _f(token.get("price")) if token else None

    def has(self, asset_id: str) -> bool:
        return asset_id in self.by_asset_id


def parse_oneclick_tokens(parsed: Any, record_sha256: str | None = None) -> TokenUniverse:
    """Pure parser for GET /v0/tokens (a JSON array of {assetId, decimals, blockchain, symbol, price, ...})."""
    if not isinstance(parsed, list):
        return TokenUniverse(ok=False, record_sha256=record_sha256)
    by_id: dict[str, dict[str, Any]] = {}
    chains: set[str] = set()
    for token in parsed:
        if not isinstance(token, dict) or not isinstance(token.get("assetId"), str):
            continue
        by_id[token["assetId"]] = token
        chain = token.get("blockchain")
        if isinstance(chain, str) and chain:
            chains.add(chain)
    return TokenUniverse(ok=True, by_asset_id=by_id, count=len(by_id), blockchains=sorted(chains), record_sha256=record_sha256)


async def fetch_oneclick_tokens(client: httpx.AsyncClient | None, ledger: ProvenanceLedger, *, timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S) -> TokenUniverse:
    """GET 1Click /v0/tokens once per run; failure yields ok=False and a ledger warning (never a cached list)."""
    parsed, record = await fetch_json(
        client, ledger, source="oneclick", name="tokens", method="GET", url=f"{config.ONECLICK_API_BASE}/v0/tokens",
        headers=config.oneclick_headers(), timeout=timeout_s, retries=QUOTE_RETRIES,
    )
    universe = parse_oneclick_tokens(parsed if record.ok else None, record.sha256)
    if not universe.ok:
        ledger.warn(f"execution_bench: 1Click /v0/tokens unavailable ({record.error}); token universe and fee USD conversion are null")
    return universe


# ----------------------------------------------------------------------------- payload builders (FACTS 2-3)
def oneclick_payload(corridor: Corridor, amount_in_raw: str, deadline: str) -> dict[str, Any]:
    """1Click dry quote body, field-for-field as docs/LIVE_ENDPOINT_FACTS.md section 2."""
    return {
        "dry": True, "swapType": "EXACT_INPUT", "slippageTolerance": 100,
        "originAsset": corridor.origin["oneclick_asset_id"], "depositType": "ORIGIN_CHAIN",
        "destinationAsset": corridor.destination["oneclick_asset_id"], "amount": amount_in_raw,
        "refundTo": corridor.origin["address"], "refundType": "ORIGIN_CHAIN",
        "recipient": corridor.destination["address"], "recipientType": "DESTINATION_CHAIN", "deadline": deadline,
    }


def relay_payload(corridor: Corridor, amount_in_raw: str) -> dict[str, Any]:
    """Relay POST /quote body (FACTS section 3)."""
    return {
        "user": corridor.origin["address"], "originChainId": corridor.origin["relay_chain_id"],
        "destinationChainId": corridor.destination["relay_chain_id"], "originCurrency": corridor.origin["relay_currency"],
        "destinationCurrency": corridor.destination["relay_currency"], "recipient": corridor.destination["address"],
        "tradeType": "EXACT_INPUT", "amount": amount_in_raw,
    }


def lifi_params(corridor: Corridor, amount_in_raw: str) -> dict[str, str]:
    """LI.FI GET /v1/quote query (FACTS section 3)."""
    return {
        "fromChain": corridor.origin["lifi_chain"], "toChain": corridor.destination["lifi_chain"],
        "fromToken": corridor.origin["lifi_token"], "toToken": corridor.destination["lifi_token"], "fromAmount": amount_in_raw,
        "fromAddress": corridor.origin["address"], "toAddress": corridor.destination["address"],
    }


def across_params(corridor: Corridor, amount_in_raw: str) -> dict[str, str]:
    """Across GET /suggested-fees query (FACTS section 3); caller must check the destination is reachable."""
    return {
        "inputToken": str(corridor.origin["across_token"]), "outputToken": str(corridor.destination["across_token"]),
        "originChainId": str(corridor.origin["across_chain_id"]), "destinationChainId": str(corridor.destination["across_chain_id"]),
        "amount": amount_in_raw,
    }


# ----------------------------------------------------------------------------- pure parsers
def parse_oneclick(parsed: Any, record: RawRecord | None, ctx: QuoteContext) -> VenueQuote:
    """1Click dry quote -> VenueQuote.

    amount_in_usd / amount_out_usd come from the quote's own USD legs; ``withdrawFee`` (raw destination
    units) is converted with the live token-list price; ``appFees[].fee`` is in bps of the input.
    """
    quote = parsed.get("quote") if isinstance(parsed, dict) else None
    if record is not None and record.ok and isinstance(quote, dict) and quote.get("amountOut") is not None:
        mismatch = _echo_mismatch(ctx, ONECLICK, record, quote.get("amountIn"))
        if mismatch is not None:
            return mismatch
        in_usd = _f(quote.get("amountInUsd"))
        fees: dict[str, float] = {}
        withdraw_fee = _f(quote.get("withdrawFee"))
        if withdraw_fee is not None and ctx.dest_price_usd is not None:
            fees["withdrawFee"] = withdraw_fee / 10**ctx.dest_decimals * ctx.dest_price_usd
        app_fee_bps = 0.0
        request = parsed.get("quoteRequest") if isinstance(parsed.get("quoteRequest"), dict) else {}
        for item in request.get("appFees") or []:
            fee = _f(item.get("fee")) if isinstance(item, dict) else None
            app_fee_bps += fee or 0.0
        if in_usd is not None and app_fee_bps:
            fees["appFee"] = in_usd * app_fee_bps / 1e4
        return _success(
            ctx, ONECLICK, record, amount_in_usd=in_usd, amount_out_raw=quote.get("amountOut"),
            amount_out_formatted=_f(quote.get("amountOutFormatted")), amount_out_usd=_f(quote.get("amountOutUsd")),
            time_estimate_s=_f(quote.get("timeEstimate")), route_tool=ROUTE_TOOL[ONECLICK], fee_breakdown_usd=fees,
            app_fee_bps=app_fee_bps, min_amount_out_raw=quote.get("minAmountOut"), refund_fee_raw=quote.get("refundFee"),
            confidentiality=request.get("confidentiality"),
        )
    message = _message(parsed, record, "message")
    if message and _ONECLICK_NO_LIQUIDITY.search(message):
        return _failure(ctx, ONECLICK, record, status="no_liquidity", supported=True, message=message)
    return _failure(ctx, ONECLICK, record, status="error", supported=True, message=message)


def parse_relay(parsed: Any, record: RawRecord | None, ctx: QuoteContext) -> VenueQuote:
    """Relay /quote -> VenueQuote. USD legs: details.currencyIn/currencyOut.amountUsd; fees.*.amountUsd."""
    details = parsed.get("details") if isinstance(parsed, dict) else None
    currency_out = details.get("currencyOut") if isinstance(details, dict) else None
    if record is not None and record.ok and isinstance(currency_out, dict) and currency_out.get("amount") is not None:
        currency_in = details.get("currencyIn") if isinstance(details.get("currencyIn"), dict) else {}
        mismatch = _echo_mismatch(ctx, "relay", record, currency_in.get("amount"))
        if mismatch is not None:
            return mismatch
        fees: dict[str, float] = {}
        for key, value in (parsed.get("fees") or {}).items():
            usd = _f(value.get("amountUsd")) if isinstance(value, dict) else None
            if usd is not None:
                fees[key] = usd
        impact = details.get("totalImpact") if isinstance(details.get("totalImpact"), dict) else {}
        return _success(
            ctx, "relay", record, amount_in_usd=_f(currency_in.get("amountUsd")), amount_out_raw=currency_out.get("amount"),
            amount_out_formatted=_f(currency_out.get("amountFormatted")), amount_out_usd=_f(currency_out.get("amountUsd")),
            time_estimate_s=_f(details.get("timeEstimate")), route_tool=ROUTE_TOOL["relay"], fee_breakdown_usd=fees,
            price_impact_pct=_f(impact.get("percent")), min_amount_out_raw=currency_out.get("minimumAmount"),
        )
    code = parsed.get("errorCode") if isinstance(parsed, dict) else None
    message = _message(parsed, record, "message")
    text = f"{code}: {message}" if isinstance(code, str) and message and code not in message else (message or code)
    if isinstance(code, str) and code in RELAY_ROUTE_ERROR_CODES:
        return _failure(ctx, "relay", record, status="unsupported_route", supported=False, message=text, error_code=code)
    if isinstance(code, str) and code in RELAY_NO_LIQUIDITY_CODES:
        return _failure(ctx, "relay", record, status="no_liquidity", supported=True, message=text, error_code=code)
    return _failure(ctx, "relay", record, status="error", supported=True, message=text, error_code=code if isinstance(code, str) else None)


def parse_lifi(parsed: Any, record: RawRecord | None, ctx: QuoteContext) -> VenueQuote:
    """LI.FI /v1/quote -> VenueQuote. ``tool`` names the bridge LI.FI chose (``"near"`` = NEAR Intents)."""
    estimate = parsed.get("estimate") if isinstance(parsed, dict) else None
    if record is not None and record.ok and isinstance(estimate, dict) and estimate.get("toAmount") is not None:
        mismatch = _echo_mismatch(ctx, "lifi", record, estimate.get("fromAmount"))
        if mismatch is not None:
            return mismatch
        action = parsed.get("action") if isinstance(parsed.get("action"), dict) else {}
        to_token = action.get("toToken") if isinstance(action.get("toToken"), dict) else {}
        decimals = to_token.get("decimals") if isinstance(to_token.get("decimals"), int) else ctx.dest_decimals
        out_raw = _int_str(estimate.get("toAmount"))
        fees: dict[str, float] = {}
        for cost in estimate.get("feeCosts") or []:
            if not isinstance(cost, dict):
                continue
            usd = _f(cost.get("amountUSD"))
            if usd is not None:
                name = str(cost.get("name") or "fee")
                fees[name] = fees.get(name, 0.0) + usd
        gas_usd = [u for u in (_f(c.get("amountUSD")) for c in estimate.get("gasCosts") or [] if isinstance(c, dict)) if u is not None]
        if gas_usd:
            fees["gas"] = sum(gas_usd)
        tool_details = parsed.get("toolDetails") if isinstance(parsed.get("toolDetails"), dict) else {}
        tool = str(parsed.get("tool") or estimate.get("tool") or "lifi")
        # LI.FI's bridge key "near" is NEAR Intents itself: the quote is 1Click execution resold with LI.FI's fee on top,
        # not an independent competitor price. It still counts for headroom (it is what a LI.FI user receives).
        return _success(
            ctx, "lifi", record, amount_in_usd=_f(estimate.get("fromAmountUSD")), amount_out_raw=estimate.get("toAmount"),
            amount_out_formatted=(out_raw / 10**decimals) if out_raw is not None else None, amount_out_usd=_f(estimate.get("toAmountUSD")),
            time_estimate_s=_f(estimate.get("executionDuration")), route_tool=tool,
            fee_breakdown_usd=fees, tool_name=tool_details.get("name"), min_amount_out_raw=estimate.get("toAmountMin"),
            routes_via_near_intents=(tool.lower() == "near"),
        )
    message = _message(parsed, record, "message")
    if message and _LIFI_UNSUPPORTED.search(message):
        return _failure(ctx, "lifi", record, status="unsupported_route", supported=False, message=message)
    if message and _LIFI_NO_QUOTES.search(message):
        return _failure(ctx, "lifi", record, status="no_liquidity", supported=True, message=message)
    return _failure(ctx, "lifi", record, status="error", supported=True, message=message)


def parse_across(parsed: Any, record: RawRecord | None, ctx: QuoteContext) -> VenueQuote:
    """Across /suggested-fees -> VenueQuote.

    Across quotes carry no USD legs, so ``venue_*`` USD fields are null and the published USD legs come
    from the common token-list oracle like every other venue (null if that list failed; the raw
    USDC -> USDC friction is always available). ``pct`` fields are 1e18-scaled ratios.
    """
    if record is not None and record.ok and isinstance(parsed, dict) and parsed.get("outputAmount") is not None:
        if parsed.get("isAmountTooLow") is True:
            return _failure(ctx, "across", record, status="error", supported=True, message="isAmountTooLow: amount below Across minimum deposit", error_code="AMOUNT_TOO_LOW")
        scale = 10**ctx.dest_decimals
        out_raw = _int_str(parsed.get("outputAmount"))
        fees: dict[str, float] = {}
        for key in ("totalRelayFee", "relayerCapitalFee", "relayerGasFee", "lpFee"):
            block = parsed.get(key)
            total = _f(block.get("total")) if isinstance(block, dict) else None
            if total is not None:
                fees[key] = total / scale
        total_pct = _f(parsed["totalRelayFee"].get("pct")) if isinstance(parsed.get("totalRelayFee"), dict) else None
        limits = parsed.get("limits") if isinstance(parsed.get("limits"), dict) else {}
        return _success(
            ctx, "across", record, amount_in_usd=None, amount_out_raw=parsed.get("outputAmount"),
            amount_out_formatted=(out_raw / scale) if out_raw is not None else None, amount_out_usd=None,
            time_estimate_s=_f(parsed.get("estimatedFillTimeSec")), route_tool=ROUTE_TOOL["across"], fee_breakdown_usd=fees,
            relay_fee_bps=(total_pct / 1e18 * 1e4) if total_pct is not None else None,
            usd_basis_note=_ACROSS_USD_NOTE, note=_ACROSS_USD_NOTE,
            max_deposit_raw=limits.get("maxDeposit"), exclusive_relayer=parsed.get("exclusiveRelayer"),
        )
    code = parsed.get("code") if isinstance(parsed, dict) else None
    message = _message(parsed, record, "message")
    text = f"{code}: {message}" if isinstance(code, str) and message and code not in message else (message or code)
    if isinstance(code, str) and code in ACROSS_ROUTE_ERROR_CODES:
        return _failure(ctx, "across", record, status="unsupported_route", supported=False, message=text, error_code=code)
    if isinstance(code, str) and code in ACROSS_NO_LIQUIDITY_CODES:
        return _failure(ctx, "across", record, status="no_liquidity", supported=True, message=text, error_code=code)
    return _failure(ctx, "across", record, status="error", supported=True, message=text, error_code=code if isinstance(code, str) else None)


def declared_unsupported_quote(ctx: QuoteContext, venue: str, reason: str) -> VenueQuote:
    """A venue we do not call because it structurally cannot reach the destination chain (no HTTP)."""
    return VenueQuote(
        venue=venue, supported=False, status="unsupported_route", error_message=reason, amount_in_raw=ctx.amount_in_raw,
        latency_ms=0.0, fetched_at_utc=utc_now_iso(), raw_record_sha256=EMPTY_SHA256, declared=True,
    )


# ----------------------------------------------------------------------------- live quoting
def _context(corridor: Corridor, clip_usd: float, tokens: TokenUniverse | None) -> QuoteContext:
    return QuoteContext(
        corridor=corridor, clip_usd=float(clip_usd), amount_in_raw=amount_in_raw_for(corridor, clip_usd),
        dest_price_usd=tokens.price(corridor.destination["oneclick_asset_id"]) if tokens else None,
        origin_price_usd=tokens.price(corridor.origin["oneclick_asset_id"]) if tokens else None,
    )


def _record_name(corridor: Corridor, clip_usd: float) -> str:
    return f"quote:{corridor.corridor_id}:{int(clip_usd) if float(clip_usd).is_integer() else clip_usd}"


async def quote_venue(
    client: httpx.AsyncClient | None,
    ledger: ProvenanceLedger,
    corridor: Corridor,
    clip_usd: float,
    venue: str,
    *,
    tokens: TokenUniverse | None = None,
    timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
    deadline: str | None = None,
) -> VenueQuote:
    """Fetch one live quote for (corridor, clip, venue) and parse it into a VenueQuote.

    Venues the corridor declares structurally unsupported (``venues_declared_unsupported``) are not called.
    Across is only called when both legs carry an ``across_chain_id``.
    """
    if venue not in VENUE_SOURCE:
        raise ValueError(f"unknown venue {venue!r}; known: {VENUES}")
    ctx = _context(corridor, clip_usd, tokens)
    declared = _declared_unsupported(corridor)
    if venue in declared:
        return declared_unsupported_quote(ctx, venue, declared[venue])
    name = _record_name(corridor, clip_usd)
    source = VENUE_SOURCE[venue]
    if venue == ONECLICK:
        parsed, record = await fetch_json(
            client, ledger, source=source, name=name, method="POST", url=f"{config.ONECLICK_API_BASE}/v0/quote",
            json=oneclick_payload(corridor, ctx.amount_in_raw, deadline or deadline_iso()), headers=config.oneclick_headers(),
            timeout=timeout_s, retries=QUOTE_RETRIES,
        )
        return parse_oneclick(parsed, record, ctx)
    if venue == "relay":
        parsed, record = await fetch_json(
            client, ledger, source=source, name=name, method="POST", url=f"{config.RELAY_API_BASE}/quote",
            json=relay_payload(corridor, ctx.amount_in_raw), headers={"Content-Type": "application/json"},
            timeout=timeout_s, retries=QUOTE_RETRIES,
        )
        return parse_relay(parsed, record, ctx)
    if venue == "lifi":
        parsed, record = await fetch_json(
            client, ledger, source=source, name=name, method="GET", url=f"{config.LIFI_API_BASE}/quote",
            params=lifi_params(corridor, ctx.amount_in_raw), timeout=timeout_s, retries=QUOTE_RETRIES,
        )
        return parse_lifi(parsed, record, ctx)
    if corridor.origin.get("across_chain_id") is None or corridor.destination.get("across_chain_id") is None:
        return declared_unsupported_quote(ctx, "across", f"Across is EVM-only; no {corridor.destination['chain']} route")
    parsed, record = await fetch_json(
        client, ledger, source=source, name=name, method="GET", url=f"{config.ACROSS_API_BASE}/suggested-fees",
        params=across_params(corridor, ctx.amount_in_raw), timeout=timeout_s, retries=QUOTE_RETRIES,
    )
    return parse_across(parsed, record, ctx)


# ----------------------------------------------------------------------------- cell scoring & aggregates
def _preferred_friction(quote: VenueQuote) -> float | None:
    return quote.friction_bps_raw if quote.friction_bps_raw is not None else quote.friction_bps_usd


def _out_units(quote: VenueQuote) -> int | None:
    return _int_str(quote.amount_out_raw)


def common_price_basis(corridor: Corridor, amount_in_raw: str, quotes: Sequence[VenueQuote]) -> tuple[list[VenueQuote], dict[str, Any]]:
    """Value every ok quote's USD legs in a cell at ONE price; returns (quotes, price_basis).

    Preferred: the 1Click token-list oracle, already applied by ``_success`` (``usd_basis ==
    "oneclick_token_list_oracle"``). When the token list failed every ok quote carries its own venue legs,
    which are not comparable across venues; the fallback takes the MEDIAN of the venues' implied
    destination prices (venue_amount_out_usd / destination units) and origin prices (venue_amount_in_usd /
    origin units) and re-values all legs with it (``usd_basis = "median_venue_oracle"``). The venue legs
    survive in the ``venue_*`` fields. ``price_basis`` = {source, dest_price_usd, origin_price_usd,
    n_venue_oracles}; ``source`` is null when no USD valuation is possible (frictions stay as they are).
    """
    ok = [q for q in quotes if q.status == "ok"]
    oracle = [q for q in ok if getattr(q, "usd_basis", None) == USD_BASIS_ORACLE]
    if oracle or not ok:
        q0 = oracle[0] if oracle else None
        return list(quotes), {
            "source": USD_BASIS_ORACLE if q0 is not None else None,
            "dest_price_usd": getattr(q0, "oracle_dest_price_usd", None) if q0 is not None else None,
            "origin_price_usd": getattr(q0, "oracle_origin_price_usd", None) if q0 is not None else None,
            "n_venue_oracles": 0,
        }
    in_raw = _int_str(amount_in_raw)
    in_units = in_raw / 10 ** int(corridor.origin["decimals"]) if in_raw else None
    dest_decimals = int(corridor.destination["decimals"])
    dest_prices = [p for p in (getattr(q, "venue_implied_dest_price_usd", None) for q in ok) if p is not None and p > 0]
    origin_prices = [
        v / in_units for v in (getattr(q, "venue_amount_in_usd", None) for q in ok) if v is not None and in_units
    ]
    if not dest_prices or not origin_prices:
        return list(quotes), {"source": None, "dest_price_usd": None, "origin_price_usd": None, "n_venue_oracles": 0}
    dest_p, origin_p = float(median(dest_prices)), float(median(origin_prices))
    out: list[VenueQuote] = []
    for q in quotes:
        if q.status != "ok":
            out.append(q)
            continue
        out_raw = _int_str(q.amount_out_raw)
        out_units = out_raw / 10**dest_decimals if out_raw is not None else q.amount_out_formatted
        in_usd = in_units * origin_p if in_units else None
        out_usd = out_units * dest_p if out_units is not None else None
        out.append(q.model_copy(update={
            "amount_in_usd": in_usd, "amount_out_usd": out_usd, "friction_bps_usd": friction_bps(in_usd, out_usd),
            "usd_basis": USD_BASIS_MEDIAN_VENUE, "oracle_dest_price_usd": dest_p, "oracle_origin_price_usd": origin_p,
        }))
    return out, {"source": USD_BASIS_MEDIAN_VENUE, "dest_price_usd": dest_p, "origin_price_usd": origin_p, "n_venue_oracles": len(dest_prices)}


def score_cell(corridor: Corridor, clip_usd: float, quotes: Sequence[VenueQuote]) -> CorridorClipResult:
    """Headroom, best competitor and 1Click rank for one (corridor, clip) cell, on destination units.

    Every venue in a cell delivers the same destination asset for the same raw input, so
    headroom_bps = (out_1click - out_best_competitor) / out_best_competitor * 1e4 needs no oracle
    (``headroom_basis = "dest_units"``); best competitor = the one delivering the most units;
    oneclick_rank = 1 + number of ok competitors delivering strictly more. USD frictions are carried for
    information, every venue valued at the cell's ONE common price (``price_basis``, see
    ``common_price_basis``); raw friction is preferred where the corridor is same-asset. Cells without an
    ok 1Click quote carry null headroom. ``venue_oracle_gap_bps`` records how far each venue's own USD
    pricing of the destination asset sits from the common price; when that gap exceeds the headroom a
    USD-leg comparison would have been decided by oracles, which is why it is not used for ranking.
    """
    ordered = sorted(quotes, key=lambda q: VENUES.index(q.venue) if q.venue in VENUES else len(VENUES))
    ordered, price_basis = common_price_basis(corridor, ordered[0].amount_in_raw if ordered else amount_in_raw_for(corridor, clip_usd), ordered)
    ok = [q for q in ordered if q.status == "ok" and _out_units(q) is not None]
    oneclick = next((q for q in ok if q.venue == ONECLICK), None)
    one_out = _out_units(oneclick) if oneclick else None
    competitors = [(q, _out_units(q)) for q in ok if q.venue != ONECLICK]
    best = max(competitors, key=lambda pair: pair[1]) if competitors else None
    headroom = (one_out - best[1]) / best[1] * 1e4 if best is not None and one_out is not None and best[1] > 0 else None
    rank = 1 + sum(1 for _, out in competitors if out > one_out) if one_out is not None else None
    common_dest = price_basis.get("dest_price_usd")
    gaps: dict[str, float] = {}
    for q in ok:
        implied = getattr(q, "venue_implied_dest_price_usd", None)
        if implied is not None and common_dest:
            gaps[q.venue] = (implied - common_dest) / common_dest * 1e4
    max_gap = max((abs(g) for g in gaps.values()), default=None)
    return CorridorClipResult(
        corridor_id=corridor.corridor_id, clip_usd=float(clip_usd), quotes=list(ordered),
        best_competitor=best[0].venue if best is not None else None, headroom_bps=headroom, oneclick_rank=rank,
        n_venues_ok=sum(1 for q in ordered if q.status == "ok"),
        headroom_basis=HEADROOM_BASIS_DEST_UNITS if headroom is not None else None, archetype=corridor.archetype,
        oneclick_friction_bps=_preferred_friction(oneclick) if oneclick else None,
        best_competitor_friction_bps=_preferred_friction(best[0]) if best is not None else None,
        n_competitors_ok=len(competitors),
        price_basis=price_basis,
        oneclick_amount_out_raw=str(one_out) if one_out is not None else None,
        best_competitor_amount_out_raw=str(best[1]) if best is not None else None,
        venue_oracle_gap_bps=gaps,
        oracle_gap_exceeds_headroom=(max_gap is not None and headroom is not None and max_gap > abs(headroom)),
    )


def aggregate(corridors: Sequence[Corridor], results: Sequence[CorridorClipResult]) -> dict[str, Any]:
    """Archetype medians of cell headroom and the cross_vm competitor fee ceiling.

    headroom_by_archetype_bps[a] = median(headroom_bps over cells of archetype a with headroom != null)
    competitive_fee_ceiling_bps  = median over cross_vm cells of the best competitor's friction (raw where
                                   present else usd): what a user forgoes by routing to the next-best venue.
    competitor_friction_by_venue_bps = per-venue {median, n, values} over the same cells, so the ceiling
                                   can be read next to each schedule instead of a pooled midpoint.
    """
    archetype_of = {c.corridor_id: c.archetype for c in corridors}
    headroom_lists: dict[str, list[float]] = {c.archetype: [] for c in corridors}
    ceiling_samples: list[float] = []
    by_venue: dict[str, list[float]] = {}
    for result in results:
        archetype = archetype_of.get(result.corridor_id)
        if archetype is None:
            continue
        if result.headroom_bps is not None:
            headroom_lists[archetype].append(result.headroom_bps)
        if archetype == "cross_vm":
            cell_best: float | None = None
            for quote in result.quotes:
                friction = _preferred_friction(quote)
                if quote.status == "ok" and quote.venue != ONECLICK and friction is not None:
                    by_venue.setdefault(quote.venue, []).append(friction)
                    cell_best = friction if cell_best is None else min(cell_best, friction)
            if cell_best is not None:
                ceiling_samples.append(cell_best)
    return {
        "headroom_by_archetype_bps": {a: (median(v) if v else None) for a, v in headroom_lists.items()},
        "headroom_n_by_archetype": {a: len(v) for a, v in headroom_lists.items()},
        "competitive_fee_ceiling_bps": median(ceiling_samples) if ceiling_samples else None,
        "competitive_fee_ceiling_n": len(ceiling_samples),
        "competitive_fee_ceiling_basis": "median over cross_vm cells of the best competitor's friction (raw where available else usd)",
        "competitor_friction_by_venue_bps": {
            v: {"median": median(vals), "n": len(vals), "values": vals} for v, vals in sorted(by_venue.items())
        },
    }


def _fmt_clip(clip_usd: float) -> str:
    return f"${clip_usd:,.0f}" if float(clip_usd).is_integer() else f"${clip_usd:,.2f}"


def _corridor_sentence(corridor: Corridor, results: Sequence[CorridorClipResult]) -> str:
    """One factual sentence: where 1Click wins/loses and by how much, and which venues were unsupported."""
    parts: list[str] = []
    unsupported: dict[str, str] = {}
    other_failures: list[str] = []
    for result in sorted(results, key=lambda r: r.clip_usd):
        clip = _fmt_clip(result.clip_usd)
        oneclick = next((q for q in result.quotes if q.venue == ONECLICK), None)
        if result.headroom_bps is not None and result.best_competitor:
            verb = "delivers" if result.headroom_bps >= 0 else "trails"
            n_ranked = int(getattr(result, "n_competitors_ok", 0) or 0) + 1
            parts.append(
                f"{clip}: 1Click {verb} {abs(result.headroom_bps):.2f} bps {'more than' if result.headroom_bps >= 0 else 'behind'} "
                f"{result.best_competitor} (rank {result.oneclick_rank}/{n_ranked}, destination units)"
            )
        elif oneclick is not None and oneclick.status == "no_liquidity":
            parts.append(f"{clip}: 1Click no liquidity")
        elif oneclick is not None and oneclick.status in ("error", "skipped"):
            parts.append(f"{clip}: 1Click {oneclick.status}")
        elif oneclick is not None and result.n_venues_ok == 1:
            parts.append(f"{clip}: 1Click ok, no competitor quote to compare")
        for quote in result.quotes:
            if quote.venue == ONECLICK:
                continue
            if quote.status == "unsupported_route":
                code = getattr(quote, "error_code", None)
                unsupported.setdefault(quote.venue, code or (quote.error_message or "unsupported"))
            elif quote.status in ("error", "skipped", "no_liquidity"):
                other_failures.append(f"{quote.venue} {quote.status} at {clip}")
    if unsupported:
        parts.append("unsupported: " + ", ".join(f"{venue} ({reason})" for venue, reason in unsupported.items()))
    if other_failures:
        parts.append("; ".join(other_failures))
    body = "; ".join(parts) if parts else "no quotes returned"
    return f"{corridor.archetype} ({corridor.label}): {body}."


def summarize(corridors: Sequence[Corridor], results: Sequence[CorridorClipResult]) -> str:
    """One sentence per corridor/archetype, in corridor order."""
    by_corridor: dict[str, list[CorridorClipResult]] = {c.corridor_id: [] for c in corridors}
    for result in results:
        by_corridor.setdefault(result.corridor_id, []).append(result)
    return " ".join(_corridor_sentence(c, by_corridor[c.corridor_id]) for c in corridors)


# ----------------------------------------------------------------------------- orchestration
def _resolve_corridors(corridor_ids: Iterable[str] | None) -> list[Corridor]:
    if corridor_ids is None:
        return list(CORRIDORS)
    return [corridor_by_id(cid) for cid in corridor_ids]


def _skipped_quote(ctx: QuoteContext, venue: str, reason: str) -> VenueQuote:
    return VenueQuote(
        venue=venue, supported=True, status="skipped", error_message=reason, amount_in_raw=ctx.amount_in_raw,
        latency_ms=0.0, fetched_at_utc=utc_now_iso(), raw_record_sha256=EMPTY_SHA256,
    )


def _error_quote(ctx: QuoteContext, venue: str, exc: BaseException) -> VenueQuote:
    return VenueQuote(
        venue=venue, supported=True, status="error", error_message=f"{type(exc).__name__}: {exc}"[:300],
        amount_in_raw=ctx.amount_in_raw, latency_ms=0.0, fetched_at_utc=utc_now_iso(), raw_record_sha256=EMPTY_SHA256,
    )


async def _quote_matrix(
    client: httpx.AsyncClient,
    ledger: ProvenanceLedger,
    corridors: Sequence[Corridor],
    clips_usd: Sequence[float],
    tokens: TokenUniverse,
    *,
    budget_s: float,
    concurrency: int,
    request_timeout_s: float,
) -> dict[tuple[str, float, str], VenueQuote]:
    """All (corridor x clip x venue) quotes concurrently under a semaphore and a wall-clock budget."""
    semaphore = asyncio.Semaphore(concurrency)
    deadline = deadline_iso()

    async def worker(corridor: Corridor, clip: float, venue: str) -> VenueQuote:
        async with semaphore:
            return await quote_venue(client, ledger, corridor, clip, venue, tokens=tokens, timeout_s=request_timeout_s, deadline=deadline)

    tasks: dict[asyncio.Task[VenueQuote], tuple[Corridor, float, str]] = {}
    for corridor in corridors:
        for clip in clips_usd:
            for venue in corridor.venues_attempted:
                tasks[asyncio.ensure_future(worker(corridor, clip, venue))] = (corridor, clip, venue)
    quotes: dict[tuple[str, float, str], VenueQuote] = {}
    if not tasks:
        return quotes
    done, pending = await asyncio.wait(set(tasks), timeout=budget_s)
    for task in done:
        corridor, clip, venue = tasks[task]
        exc = task.exception()
        quotes[(corridor.corridor_id, clip, venue)] = task.result() if exc is None else _error_quote(_context(corridor, clip, tokens), venue, exc)
    if pending:
        for task in pending:
            task.cancel()
            corridor, clip, venue = tasks[task]
            quotes[(corridor.corridor_id, clip, venue)] = _skipped_quote(
                _context(corridor, clip, tokens), venue, f"not completed within the {budget_s:.0f} s benchmark budget"
            )
        await asyncio.gather(*pending, return_exceptions=True)
        ledger.warn(f"execution_bench: {len(pending)} of {len(tasks)} quote requests exceeded the {budget_s:.0f} s budget and were skipped")
    return quotes


async def collect_execution_bench(
    ledger: ProvenanceLedger,
    *,
    clips_usd: Sequence[float] = DEFAULT_CLIPS_USD,
    corridor_ids: Iterable[str] | None = None,
    client: httpx.AsyncClient | None = None,
    budget_s: float = DEFAULT_BUDGET_S,
    concurrency: int = DEFAULT_CONCURRENCY,
    request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
) -> ExecutionBenchmark:
    """Run the live 1Click vs Relay vs LI.FI vs Across quote matrix and score it.

    Steps: GET the 1Click token list once (asset-id existence check, USD prices, token universe), then
    fire every (corridor x clip x venue) request concurrently (semaphore ``concurrency``, per-request
    timeout ``request_timeout_s``, total budget ``budget_s``), score each cell and aggregate. Venues
    that fail stay in the output with their verbatim status; nothing is substituted.
    """
    started = time.perf_counter()
    ran_at = utc_now_iso()
    corridors = _resolve_corridors(corridor_ids)
    clips = [float(c) for c in clips_usd]
    for clip in clips:
        if clip <= 0:
            raise ValueError(f"clips_usd must be positive, got {clip}")
    own_client = client is None
    client = client or httpx.AsyncClient(follow_redirects=True, timeout=request_timeout_s)
    try:
        tokens = await fetch_oneclick_tokens(client, ledger, timeout_s=request_timeout_s)
        if tokens.ok:
            for corridor in corridors:
                for leg in (corridor.origin, corridor.destination):
                    asset_id = leg["oneclick_asset_id"]
                    if not tokens.has(asset_id):
                        ledger.warn(f"execution_bench: {asset_id} ({corridor.corridor_id}) is absent from the live 1Click token list; quote attempted anyway")
        remaining = max(1.0, budget_s - (time.perf_counter() - started))
        quotes = await _quote_matrix(
            client, ledger, corridors, clips, tokens, budget_s=remaining, concurrency=concurrency, request_timeout_s=request_timeout_s
        )
    finally:
        if own_client:
            await client.aclose()

    results: list[CorridorClipResult] = []
    for corridor in corridors:
        declared = _declared_unsupported(corridor)
        for clip in clips:
            ctx = _context(corridor, clip, tokens)
            cell = [quotes[(corridor.corridor_id, clip, v)] for v in corridor.venues_attempted if (corridor.corridor_id, clip, v) in quotes]
            cell.extend(declared_unsupported_quote(ctx, venue, reason) for venue, reason in declared.items())
            results.append(score_cell(corridor, clip, cell))
    aggregates = aggregate(corridors, results)
    n_ok = sum(1 for r in results for q in r.quotes if q.status == "ok")
    if n_ok == 0:
        ledger.warn("execution_bench: no venue returned an ok quote; headroom and fee ceiling are null")
    if not tokens.ok and n_ok:
        ledger.warn(
            "execution_bench: token-list oracle unavailable; each cell's USD frictions are valued at the median of the venues' own "
            "implied prices (price_basis.source = median_venue_oracle); headroom is on destination units and unaffected"
        )
    for result in results:
        if getattr(result, "oracle_gap_exceeds_headroom", False):
            gaps = ", ".join(f"{v} {g:+.1f} bps" for v, g in (result.venue_oracle_gap_bps or {}).items())
            ledger.warn(
                f"execution_bench: {result.corridor_id} ${result.clip_usd:,.0f}: venue USD oracles disagree with the cell's common price by more "
                f"than the {result.headroom_bps:+.2f} bps headroom ({gaps}); headroom is measured on destination units, not USD legs"
            )
    return ExecutionBenchmark(
        ran_at_utc=ran_at, clips_usd=clips, corridors=corridors, results=results,
        headroom_by_archetype_bps=aggregates["headroom_by_archetype_bps"],
        competitive_fee_ceiling_bps=aggregates["competitive_fee_ceiling_bps"],
        oneclick_1y_token_universe=tokens.count, oneclick_blockchains=tokens.blockchains,
        summary_note=summarize(corridors, results),
        headroom_n_by_archetype=aggregates["headroom_n_by_archetype"],
        competitive_fee_ceiling_n=aggregates["competitive_fee_ceiling_n"],
        competitive_fee_ceiling_basis=aggregates["competitive_fee_ceiling_basis"],
        competitor_friction_by_venue_bps=aggregates["competitor_friction_by_venue_bps"],
        headroom_basis=HEADROOM_BASIS_DEST_UNITS,
        headroom_definition="(out_1click - out_best_competitor) / out_best_competitor x 1e4 on destination units for the same raw input; no oracle",
        usd_friction_basis=USD_BASIS_ORACLE if tokens.ok else USD_BASIS_MEDIAN_VENUE,
        token_list_ok=tokens.ok, token_list_sha256=tokens.record_sha256,
        budget_s=budget_s, concurrency=concurrency, request_timeout_s=request_timeout_s,
        elapsed_s=round(time.perf_counter() - started, 3), n_quotes_ok=n_ok,
    )


# ----------------------------------------------------------------------------- CLI
def _fmt(value: float | None, spec: str, dash: str = "-") -> str:
    return dash if value is None else format(value, spec)


def format_table(bench: ExecutionBenchmark) -> str:
    """Plain-text table of every quote plus the aggregates (used by ``python -m`` and smoke runs)."""
    header = f"{'corridor':<20}{'clip':>10}  {'venue':<7}{'status':<18}{'out':>18}{'fric_bps':>10}{'secs':>7}  {'tool':<22}{'note'}"
    lines = [header, "-" * len(header)]
    for result in bench.results:
        for quote in result.quotes:
            friction = quote.friction_bps_raw if quote.friction_bps_raw is not None else quote.friction_bps_usd
            note = "" if quote.status == "ok" else (quote.error_message or "")[:60]
            lines.append(
                f"{result.corridor_id:<20}{_fmt_clip(result.clip_usd):>10}  {quote.venue:<7}{quote.status:<18}"
                f"{_fmt(quote.amount_out_formatted, ',.6f'):>18}{_fmt(friction, '.2f'):>10}{_fmt(quote.time_estimate_s, '.0f'):>7}  "
                f"{(quote.route_tool or '-'):<22}{note}"
            )
        lines.append(
            f"{'':<20}{'':>10}  -> headroom {_fmt(result.headroom_bps, '+.2f')} bps "
            f"[{getattr(result, 'headroom_basis', None) or '-'}] best competitor {result.best_competitor or '-'} "
            f"rank {result.oneclick_rank if result.oneclick_rank is not None else '-'} ok {result.n_venues_ok}"
        )
    lines.append("")
    lines.append(f"headroom_by_archetype_bps (destination units): {bench.headroom_by_archetype_bps}")
    lines.append(f"competitive_fee_ceiling_bps (best competitor per cross_vm cell): {bench.competitive_fee_ceiling_bps}")
    lines.append(f"competitor_friction_by_venue_bps: {getattr(bench, 'competitor_friction_by_venue_bps', {})}")
    lines.append(f"oneclick_1y_token_universe: {bench.oneclick_1y_token_universe} across {len(bench.oneclick_blockchains)} blockchains")
    lines.append(f"summary_note: {bench.summary_note}")
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live 1Click vs Relay vs LI.FI vs Across quote benchmark")
    parser.add_argument("--clips", default=",".join(str(int(c)) for c in DEFAULT_CLIPS_USD), help="comma-separated USD clips")
    parser.add_argument("--corridors", default=None, help="comma-separated corridor ids (default: all)")
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET_S, help="total wall-clock budget in seconds")
    parser.add_argument("--no-persist", action="store_true", help="do not write raw payloads under artifacts/raw")
    parser.add_argument("--json", action="store_true", help="print the ExecutionBenchmark JSON instead of the table")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    clips = [float(c) for c in args.clips.split(",") if c.strip()]
    corridor_ids = [c.strip() for c in args.corridors.split(",") if c.strip()] if args.corridors else None
    if not args.no_persist:
        config.ensure_artifact_dirs()
    ledger = ProvenanceLedger(persist_raw=not args.no_persist)
    bench = asyncio.run(collect_execution_bench(ledger, clips_usd=clips, corridor_ids=corridor_ids, budget_s=args.budget))
    if args.json:
        print(bench.model_dump_json(indent=2))
    else:
        print(format_table(bench))
        print(f"elapsed_s: {getattr(bench, 'elapsed_s', None)}  records: {len(ledger.records)}  failures: {len(ledger.failures())}")
        for warning in ledger.warnings:
            print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
