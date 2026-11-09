"""Peer comparables: live DefiLlama fee/revenue run-rates and CoinGecko valuations for SOL, ETH, HYPE, NEAR.

Formulas (all inputs live; nothing here is a model assumption):

    annualized_fees_usd     = fees.total30d    * 365 / 30
    annualized_revenue_usd  = revenue.total30d * 365 / 30
    fdv_to_fees             = fdv_usd / annualized_fees_usd        (None if either side missing or <= 0)
    fdv_to_revenue          = fdv_usd / annualized_revenue_usd     (None if either side missing or <= 0)
    median_*_ex_near        = statistics.median over peers with symbol != "NEAR" and a non-null multiple
    near_combined.fees      = fees(near L1 gas) + fees(near-intents); same for revenue; FDV/mcap = NEAR's

Why trailing-30d annualized rather than ``total1y``: the SOTP terminal multiple is applied to a
*forward* run-rate, so the comparable must be the peers' current run-rate, not a trailing-year sum
that mixes in a different fee regime (both windows are stored so the gap is visible). ``revenue`` is
DefiLlama's ``dataType=dailyRevenue`` series; what that word means differs per protocol (burn, buyback,
treasury), so the live ``methodology.Revenue`` text is carried into the snapshot next to every number.

Sources: ``api.llama.fi/summary/fees/<slug>[?dataType=dailyRevenue]`` (10 calls), ``coins.llama.fi``
prices (1 call), CoinGecko ``/coins/markets`` for FDV + market cap (1 call, retried four times on 429/5xx
with Retry-After honoured up to 60 s, once on a 403 challenge). If CoinGecko fails the FDV fields are null
and a warning is recorded; ``reproduce.py`` may backfill NEAR's FDV from the nearstats price facts collected
by ``intents_forensics``. This module never does.
"""
from __future__ import annotations

import asyncio
import statistics
import threading
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, TypeVar

import httpx

from valuo import config
from valuo.provenance import ProvenanceLedger, fetch_json, utc_now_iso
from valuo.schemas import PeerComp, PeerComps

__all__ = [
    "PeerSpec", "PEER_SPECS", "NEAR_COMPONENT_SPECS", "COINGECKO_IDS", "NEAR_COMBINED_SLUG",
    "annualize_30d", "multiple", "median_ex_near",
    "parse_fee_summary", "parse_prices", "parse_markets", "revenue_methodology_from", "fees_methodology_from",
    "build_peer", "build_near_combined", "assemble_peer_comps",
    "collect_comps_async", "collect_comps",
]

_T = TypeVar("_T")

DAYS_PER_YEAR = 365.0
WINDOW_DAYS = 30.0
ANNUALIZATION_NOTE = "annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)"
NEAR_COMBINED_SLUG = "near_combined"
COINGECKO_IDS: tuple[str, ...] = ("near", "solana", "ethereum", "hyperliquid")
_NO_REVENUE_TEXT = "no revenue"
# CoinGecko's key-free tier answers bursts with 429 (Retry-After up to a minute) and occasionally a Cloudflare 403
# challenge. One call per run, so it gets real patience: 4 retries at 2 s x 2**n (2 + 4 + 8 + 16 = 30 s) with
# Retry-After honoured up to 60 s, and a 403 retried exactly once. Failure still means null FDV + warning, and the
# SOTP then falls back to the labeled terminal_multiple_cap assumption instead of aborting the run.
_COINGECKO_RETRIES = 4
_COINGECKO_BACKOFF_S = 2.0
_COINGECKO_RETRY_AFTER_CAP_S = 60.0
_COINGECKO_RETRY_ONCE_ON = frozenset({403})
_LLAMA_CONCURRENCY = 4  # polite fan-out; api.llama.fi is key-free and shared with the other collectors


@dataclass(frozen=True)
class PeerSpec:
    """One DefiLlama slug and the CoinGecko id whose valuation prices it."""

    slug: str
    symbol: str
    coingecko_id: str
    label: str


PEER_SPECS: tuple[PeerSpec, ...] = (
    PeerSpec("solana", "SOL", "solana", "Solana L1"),
    PeerSpec("ethereum", "ETH", "ethereum", "Ethereum L1"),
    PeerSpec("hyperliquid", "HYPE", "hyperliquid", "Hyperliquid (parent: perps + spot + HLP + outcomes)"),
)
# Components of the NEAR row: L1 gas fees (chain slug) and the Intents clearinghouse (protocol slug).
NEAR_COMPONENT_SPECS: tuple[PeerSpec, ...] = (
    PeerSpec("near", "NEAR", "near", "NEAR L1 gas"),
    PeerSpec("near-intents", "NEAR", "near", "NEAR Intents"),
)
ALL_SPECS: tuple[PeerSpec, ...] = PEER_SPECS + NEAR_COMPONENT_SPECS


# ----------------------------------------------------------------------------- pure arithmetic
def _num(value: Any) -> float | None:
    """Coerce a DefiLlama/CoinGecko numeric (int, float or numeric string) to a finite float, else None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if isfinite(out) else None


def annualize_30d(total30d: float | None) -> float | None:
    """``total30d * 365 / 30``; None propagates."""
    if total30d is None:
        return None
    return total30d * DAYS_PER_YEAR / WINDOW_DAYS


def multiple(numerator: float | None, denominator: float | None) -> float | None:
    """``numerator / denominator`` for valuation multiples; None when either side is missing or denominator <= 0.

    A zero or negative run-rate has no meaningful multiple (it would be infinite or negative), so it is
    reported as null rather than clipped.
    """
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def median_ex_near(peers: Iterable[PeerComp], attr: str) -> float | None:
    """Median of ``attr`` over peers whose symbol is not NEAR and whose value is non-null; None if none qualify.

    ``statistics.median`` averages the two middle values for an even count, so a 2-peer median is their mean.
    """
    values = [
        v for p in peers
        if p.symbol.upper() != "NEAR" and (v := getattr(p, attr, None)) is not None and isfinite(v)
    ]
    return statistics.median(values) if values else None


def _sum_or_none(values: Iterable[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) if present else None


# ----------------------------------------------------------------------------- payload parsing
def revenue_methodology_from(summary: Mapping[str, Any] | None) -> str | None:
    """Live ``methodology.Revenue`` text; for parent slugs with ``methodology: null`` (Hyperliquid) the
    children's ``Revenue`` texts are joined as ``"<child>: <text>"``, skipping children that state no revenue.

    Returns None when DefiLlama publishes no methodology for the slug; the caller records a warning.
    """
    if not isinstance(summary, Mapping):
        return None
    method = summary.get("methodology")
    if isinstance(method, Mapping):
        text = method.get("Revenue")
        if isinstance(text, str) and text.strip():
            return text.strip()
    children = summary.get("childProtocols")
    if isinstance(children, list):
        parts: list[str] = []
        for child in children:
            if not isinstance(child, Mapping):
                continue
            cm = child.get("methodology")
            text = cm.get("Revenue") if isinstance(cm, Mapping) else None
            if not (isinstance(text, str) and text.strip()):
                continue
            if text.strip().lower().rstrip(".") == _NO_REVENUE_TEXT:
                continue
            name = child.get("displayName") or child.get("name") or "child"
            parts.append(f"{name}: {text.strip()}")
        if parts:
            return "Parent aggregates child protocols. " + " | ".join(parts)
    return None


def fees_methodology_from(summary: Mapping[str, Any] | None) -> str | None:
    """Live ``methodology.Fees`` text (parent or joined children), None when absent."""
    if not isinstance(summary, Mapping):
        return None
    method = summary.get("methodology")
    if isinstance(method, Mapping):
        text = method.get("Fees")
        if isinstance(text, str) and text.strip():
            return text.strip()
    children = summary.get("childProtocols")
    if isinstance(children, list):
        parts = []
        for child in children:
            if not isinstance(child, Mapping):
                continue
            cm = child.get("methodology")
            text = cm.get("Fees") if isinstance(cm, Mapping) else None
            if isinstance(text, str) and text.strip():
                parts.append(f"{child.get('displayName') or child.get('name') or 'child'}: {text.strip()}")
        if parts:
            return "Parent aggregates child protocols. " + " | ".join(parts)
    return None


def parse_fee_summary(parsed: Any) -> dict[str, Any] | None:
    """Reduce a ``/summary/fees/<slug>`` payload to the totals used here; None if the shape is not a summary.

    Keys: total24h, total7d, total30d, total1y (floats or None), methodology_revenue, methodology_fees.
    """
    if not isinstance(parsed, Mapping) or "total30d" not in parsed:
        return None
    return {
        "total24h": _num(parsed.get("total24h")),
        "total7d": _num(parsed.get("total7d")),
        "total30d": _num(parsed.get("total30d")),
        "total1y": _num(parsed.get("total1y")),
        "methodology_revenue": revenue_methodology_from(parsed),
        "methodology_fees": fees_methodology_from(parsed),
    }


def parse_prices(parsed: Any) -> dict[str, float]:
    """``coins.llama.fi/prices/current`` -> {coingecko_id: price_usd} for entries with a finite price."""
    out: dict[str, float] = {}
    coins = parsed.get("coins") if isinstance(parsed, Mapping) else None
    if not isinstance(coins, Mapping):
        return out
    for key, entry in coins.items():
        if not (isinstance(key, str) and key.startswith("coingecko:") and isinstance(entry, Mapping)):
            continue
        price = _num(entry.get("price"))
        if price is not None:
            out[key.split(":", 1)[1]] = price
    return out


def parse_markets(parsed: Any) -> dict[str, dict[str, float | None]]:
    """CoinGecko ``/coins/markets`` array -> {id: {fdv, market_cap, price}}; empty dict if not an array."""
    out: dict[str, dict[str, float | None]] = {}
    if not isinstance(parsed, list):
        return out
    for row in parsed:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            continue
        out[row["id"]] = {
            "fdv": _num(row.get("fully_diluted_valuation")),
            "market_cap": _num(row.get("market_cap")),
            "price": _num(row.get("current_price")),
        }
    return out


# ----------------------------------------------------------------------------- row construction
def _valuation_fields(
    coingecko_id: str,
    prices: Mapping[str, float],
    markets: Mapping[str, Mapping[str, float | None]],
) -> dict[str, Any]:
    """FDV / market cap from CoinGecko; price from coins.llama.fi, else CoinGecko's current_price (both live)."""
    market = markets.get(coingecko_id) or {}
    price_source: str | None = None
    price = prices.get(coingecko_id)
    if price is not None:
        price_source = "coins.llama.fi"
    elif market.get("price") is not None:
        price = market["price"]
        price_source = "coingecko"
    fdv = market.get("fdv")
    return {
        "fdv_usd": fdv,
        "market_cap_usd": market.get("market_cap"),
        "price_usd": price,
        "price_source": price_source,
        "fdv_source": "coingecko" if fdv is not None else None,
    }


def _multiples(fees_30d: float | None, rev_30d: float | None, fdv: float | None, mcap: float | None) -> dict[str, Any]:
    ann_fees = annualize_30d(fees_30d)
    ann_rev = annualize_30d(rev_30d)
    return {
        "annualized_fees_usd": ann_fees,
        "annualized_revenue_usd": ann_rev,
        "fdv_to_fees": multiple(fdv, ann_fees),
        "fdv_to_revenue": multiple(fdv, ann_rev),
        "mcap_to_fees": multiple(mcap, ann_fees),
        "mcap_to_revenue": multiple(mcap, ann_rev),
    }


def build_peer(
    spec: PeerSpec,
    fees: Mapping[str, Any] | None,
    revenue: Mapping[str, Any] | None,
    prices: Mapping[str, float],
    markets: Mapping[str, Mapping[str, float | None]],
) -> PeerComp:
    """One comparable row from parsed fee/revenue summaries and valuation maps; missing inputs stay null."""
    fees = fees or {}
    revenue = revenue or {}
    valuation = _valuation_fields(spec.coingecko_id, prices, markets)
    fees_30d, rev_30d = fees.get("total30d"), revenue.get("total30d")
    return PeerComp(
        slug=spec.slug,
        symbol=spec.symbol,
        label=spec.label,
        coingecko_id=spec.coingecko_id,
        fees_30d_usd=fees_30d,
        revenue_30d_usd=rev_30d,
        fees_1y_usd=fees.get("total1y"),
        revenue_1y_usd=revenue.get("total1y"),
        fees_24h_usd=fees.get("total24h"),
        revenue_24h_usd=revenue.get("total24h"),
        fees_7d_usd=fees.get("total7d"),
        revenue_7d_usd=revenue.get("total7d"),
        **valuation,
        **_multiples(fees_30d, rev_30d, valuation["fdv_usd"], valuation["market_cap_usd"]),
        # Revenue semantics come from the revenue payload when present (same text as the fees payload).
        revenue_methodology=revenue.get("methodology_revenue") or fees.get("methodology_revenue"),
        fees_methodology=fees.get("methodology_fees") or revenue.get("methodology_fees"),
    )


def build_near_combined(
    components: list[PeerComp],
    prices: Mapping[str, float],
    markets: Mapping[str, Mapping[str, float | None]],
) -> PeerComp:
    """NEAR row = sum of component fees/revenue (L1 gas + Intents) priced at NEAR's FDV / market cap.

    Sums run over the components that returned a value; ``components_included`` / ``components_missing``
    state exactly which slugs are inside each total so a partial sum is never mistaken for the full one.
    """
    valuation = _valuation_fields("near", prices, markets)

    def part(attr: str) -> tuple[float | None, list[str], list[str]]:
        included = [c.slug for c in components if getattr(c, attr) is not None]
        missing = [c.slug for c in components if getattr(c, attr) is None]
        return _sum_or_none(getattr(c, attr) for c in components), included, missing

    fees_30d, fees_in, fees_missing = part("fees_30d_usd")
    rev_30d, rev_in, rev_missing = part("revenue_30d_usd")
    methodology = " | ".join(f"{c.slug}: {c.revenue_methodology}" for c in components if c.revenue_methodology)
    fees_methodology = " | ".join(f"{c.slug}: {c.fees_methodology}" for c in components if getattr(c, "fees_methodology", None))
    return PeerComp(
        slug=NEAR_COMBINED_SLUG,
        symbol="NEAR",
        label="NEAR (L1 gas + Intents clearinghouse)",
        coingecko_id="near",
        components=[c.slug for c in components],
        components_included={"fees": fees_in, "revenue": rev_in},
        components_missing={"fees": fees_missing, "revenue": rev_missing},
        fees_30d_usd=fees_30d,
        revenue_30d_usd=rev_30d,
        fees_1y_usd=part("fees_1y_usd")[0],
        revenue_1y_usd=part("revenue_1y_usd")[0],
        fees_24h_usd=part("fees_24h_usd")[0],
        revenue_24h_usd=part("revenue_24h_usd")[0],
        fees_7d_usd=part("fees_7d_usd")[0],
        revenue_7d_usd=part("revenue_7d_usd")[0],
        **valuation,
        **_multiples(fees_30d, rev_30d, valuation["fdv_usd"], valuation["market_cap_usd"]),
        revenue_methodology=methodology or None,
        fees_methodology=fees_methodology or None,
    )


def _revenue_note(peer: PeerComp) -> str:
    if peer.revenue_methodology:
        return f"{peer.symbol} ({peer.slug}) revenue = {peer.revenue_methodology}"
    return f"{peer.symbol} ({peer.slug}) revenue: DefiLlama publishes no methodology text for this slug"


def assemble_peer_comps(
    fees_by_slug: Mapping[str, Mapping[str, Any] | None],
    revenue_by_slug: Mapping[str, Mapping[str, Any] | None],
    prices: Mapping[str, float],
    markets: Mapping[str, Mapping[str, float | None]],
    *,
    fetched_at_utc: str,
    ledger: ProvenanceLedger | None = None,
    fetch_status: Mapping[str, Any] | None = None,
) -> PeerComps:
    """Pure assembly from parsed payloads (no I/O): peers, NEAR components, NEAR combined, medians, notes.

    Every null that reaches the output is explained by a warning on ``ledger`` (when given).
    """
    warn = ledger.warn if ledger is not None else (lambda _msg: None)

    def row(spec: PeerSpec) -> PeerComp:
        fees, revenue = fees_by_slug.get(spec.slug), revenue_by_slug.get(spec.slug)
        if fees is None:
            warn(f"comps: DefiLlama fees summary for {spec.slug} unavailable; fees fields null")
        if revenue is None:
            warn(f"comps: DefiLlama dailyRevenue summary for {spec.slug} unavailable; revenue fields null")
        peer = build_peer(spec, fees, revenue, prices, markets)
        if peer.fdv_usd is None:
            warn(f"comps: CoinGecko FDV for {spec.coingecko_id} unavailable; {spec.slug} multiples null")
        if peer.price_usd is None:
            warn(f"comps: no live price for {spec.coingecko_id} from coins.llama.fi or CoinGecko")
        if peer.revenue_methodology is None and (fees is not None or revenue is not None):
            warn(f"comps: DefiLlama publishes no Revenue methodology text for {spec.slug}")
        return peer

    peers = [row(spec) for spec in PEER_SPECS]
    components = [row(spec) for spec in NEAR_COMPONENT_SPECS]
    near_combined = build_near_combined(components, prices, markets)
    for kind in ("fees", "revenue"):
        missing = near_combined.components_missing[kind]
        if missing and len(missing) < len(components):
            warn(f"comps: near_combined {kind} sum excludes {missing} (fetch failed); partial sum labeled in components_included")

    median_rev = median_ex_near(peers, "fdv_to_revenue")
    median_fees = median_ex_near(peers, "fdv_to_fees")
    if median_rev is None:
        warn("comps: no peer has both FDV and revenue run-rate; median_fdv_to_revenue_ex_near null")
    if median_fees is None:
        warn("comps: no peer has both FDV and fee run-rate; median_fdv_to_fees_ex_near null")

    all_rows = [*peers, *components, near_combined]
    return PeerComps(
        peers=peers,
        near_combined=near_combined,
        near_components=components,
        median_fdv_to_revenue_ex_near=median_rev,
        median_fdv_to_fees_ex_near=median_fees,
        n_peers_in_revenue_median=sum(1 for p in peers if p.fdv_to_revenue is not None),
        n_peers_in_fees_median=sum(1 for p in peers if p.fdv_to_fees is not None),
        notes={p.slug: _revenue_note(p) for p in all_rows},
        annualization=ANNUALIZATION_NOTE,
        fetch_status=dict(fetch_status or {}),
        fetched_at_utc=fetched_at_utc,
    )


# ----------------------------------------------------------------------------- live collection
async def _fetch_llama_summary(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, slug: str, data_type: str | None, sem: asyncio.Semaphore
) -> dict[str, Any] | None:
    """One ``/summary/fees/<slug>`` call (optionally ``?dataType=dailyRevenue``) reduced via parse_fee_summary."""
    name = f"fees:{slug}:{data_type or 'dailyFees'}"
    params = {"dataType": data_type} if data_type else None
    async with sem:
        parsed, record = await fetch_json(
            client, ledger, source="defillama", name=name, method="GET",
            url=f"{config.DEFILLAMA_API_BASE}/summary/fees/{slug}", params=params,
        )
    if not record.ok:
        return None
    summary = parse_fee_summary(parsed)
    if summary is None:
        ledger.warn(f"comps: {name} returned 2xx but not a fee summary payload")
    return summary


async def _fetch_prices(client: httpx.AsyncClient, ledger: ProvenanceLedger) -> tuple[dict[str, float], bool]:
    coins = ",".join(f"coingecko:{cid}" for cid in COINGECKO_IDS)
    parsed, record = await fetch_json(
        client, ledger, source="defillama", name="prices:current", method="GET",
        url=f"{config.COINS_LLAMA_BASE}/prices/current/{coins}",
    )
    prices = parse_prices(parsed) if record.ok else {}
    if not prices:
        ledger.warn("comps: coins.llama.fi current prices unavailable; falling back to CoinGecko current_price where present")
    return prices, record.ok


async def _fetch_markets(client: httpx.AsyncClient, ledger: ProvenanceLedger) -> tuple[dict[str, dict[str, float | None]], bool]:
    """Single CoinGecko call for all four ids; 429-patient retries (see constants) then null FDV with a warning."""
    parsed, record = await fetch_json(
        client, ledger, source="coingecko", name="coins_markets", method="GET",
        url=f"{config.COINGECKO_API_BASE}/coins/markets",
        params={"vs_currency": "usd", "ids": ",".join(COINGECKO_IDS)},
        retries=_COINGECKO_RETRIES, backoff=_COINGECKO_BACKOFF_S, transport_retries=1,
        retry_after_cap_s=_COINGECKO_RETRY_AFTER_CAP_S, retry_once_on=_COINGECKO_RETRY_ONCE_ON,
    )
    markets = parse_markets(parsed) if record.ok else {}
    if not markets:
        ledger.warn(
            f"comps: CoinGecko /coins/markets failed after {record.attempts} attempt(s) ({record.error}); "
            "FDV and market cap null for every peer, multiples null"
        )
    return markets, bool(markets)


async def collect_comps_async(ledger: ProvenanceLedger, client: httpx.AsyncClient | None = None) -> PeerComps:
    """Fetch everything concurrently on one httpx client and assemble the PeerComps snapshot section."""
    fetched_at = utc_now_iso()
    own_client = client is None
    client = client or httpx.AsyncClient(follow_redirects=True, timeout=config.HTTP_TIMEOUT_S)
    sem = asyncio.Semaphore(_LLAMA_CONCURRENCY)
    try:
        fee_tasks = [_fetch_llama_summary(client, ledger, s.slug, None, sem) for s in ALL_SPECS]
        rev_tasks = [_fetch_llama_summary(client, ledger, s.slug, "dailyRevenue", sem) for s in ALL_SPECS]
        results = await asyncio.gather(*fee_tasks, *rev_tasks, _fetch_prices(client, ledger), _fetch_markets(client, ledger))
    finally:
        if own_client:
            await client.aclose()

    n = len(ALL_SPECS)
    fees_by_slug = {spec.slug: results[i] for i, spec in enumerate(ALL_SPECS)}
    revenue_by_slug = {spec.slug: results[n + i] for i, spec in enumerate(ALL_SPECS)}
    prices, prices_ok = results[2 * n]
    markets, markets_ok = results[2 * n + 1]
    status = {
        "defillama_fees_ok": sorted(s for s, v in fees_by_slug.items() if v is not None),
        "defillama_revenue_ok": sorted(s for s, v in revenue_by_slug.items() if v is not None),
        "coins_llama_prices_ok": prices_ok,
        "coingecko_markets_ok": markets_ok,
    }
    return assemble_peer_comps(
        fees_by_slug, revenue_by_slug, prices, markets, fetched_at_utc=fetched_at, ledger=ledger, fetch_status=status,
    )


def _inside_running_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _run_on_private_loop(make_coro: Callable[[], Awaitable[_T]]) -> _T:
    """Run a coroutine to completion on a helper thread with its own event loop (caller's loop is busy)."""
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["value"] = asyncio.run(make_coro())  # type: ignore[arg-type]
        except BaseException as exc:  # propagate to the caller's thread
            box["error"] = exc

    thread = threading.Thread(target=runner, name="valuo-comps", daemon=True)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["value"]


def collect_comps(ledger: ProvenanceLedger, client: httpx.AsyncClient | None = None) -> PeerComps:
    """Synchronous entry point: ``collect_comps(ledger) -> PeerComps`` (see collect_comps_async).

    Works from plain code (``asyncio.run``) and from inside a running loop (private loop on a helper
    thread). A caller-supplied ``client`` is refused inside a running loop because an AsyncClient belongs
    to the loop that created it; ``await collect_comps_async(ledger, client)`` there instead.
    """
    if not _inside_running_loop():
        return asyncio.run(collect_comps_async(ledger, client))
    if client is not None:
        raise RuntimeError("collect_comps(client=...) called inside a running event loop; await collect_comps_async instead")
    return _run_on_private_loop(lambda: collect_comps_async(ledger, None))
