"""Liquidity cliff ladder: the largest clip each router will quote on each benchmarked corridor.

Question
    The execution benchmark stops at $250K. An allocator sizing a position needs to know where each
    router stops quoting at all, and what the all-in cost does on the way there.

Method
    For every corridor of ``execution_bench.CORRIDORS`` and every venue that corridor attempts, request a
    dry (non-binding) quote at $1K, $10K, $50K, $250K, $500K, $1M, $2.5M and $5M. The request bodies and
    response parsers are the bench's own (``oneclick_payload`` / ``parse_oneclick`` and the Relay, LI.FI
    and Across equivalents), so a ladder cell and a bench cell are the same measurement at a different
    size. 1Click is always called with ``"dry": true``: no deposit address is ever requested. Every
    response goes through the ``ProvenanceLedger`` under ``ladder:<venue>:<corridor>:<size>`` (raw payload
    saved and SHA-256 hashed); the reference prices come from one 1Click token-list fetch recorded as
    ``oneclick/ladder:tokens``.

    Sizes run in ascending order inside one (corridor, venue) chain; chains run concurrently under the
    bench's concurrency limit and per-request timeout, inside a wall-clock budget (``VALUO_LADDER_BUDGET_S``,
    default 75 s). The collector waits for ``events["bench_done"]`` so it never competes with the quote race
    for venue rate limits.

Cell outcomes
    quoted        the venue returned an executable quote. ``cost_bps`` is the bench's friction on the bench's
                  basis: (in - out) / in x 1e4 on raw units when both legs are the same stablecoin, else on
                  USD legs valued at one common price (1Click token-list oracle, else the median of the
                  venues' own implied prices, exactly as ``execution_bench.common_price_basis``).
    no_liquidity  the venue's explicit refusal for that size (its message is kept verbatim). The bench's parsers
                  decide this; in addition a venue error code in ``SIZE_REFUSAL_CODES`` (Relay's AMOUNT_TOO_HIGH,
                  "Quote amount exceeds the maximum for this pair") is a size refusal here, not a generic error.
    unsupported   the venue does not route the corridor at all (declared, or refused at the smallest size;
                  after such a refusal the larger sizes are not called).
    error         transport failure, HTTP error or a body the parser does not recognise (short reason kept).
    not_attempted the request did not complete inside the budget. Never reported as "no liquidity".

Limits
    A dry "no liquidity" is the solver set's quoting policy at that moment, not proven hard depth, and a
    dry quote is not a fill. One run is one observation. Sizes between two rungs are not observed. All
    fields say "largest size quoted", never "depth". A refusal below a size the venue did quote is flagged
    ``non_monotone`` and the ladder is not reported as clean.
"""
from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from valuo import config
from valuo.collectors import execution_bench as eb
from valuo.provenance import ProvenanceLedger, fetch_json, utc_now_iso
from valuo.schemas import Corridor, RawRecord, VenueQuote

__all__ = [
    "SIZES_USD", "INSTITUTIONAL_SIZE_USD", "DEFAULT_BUDGET_S", "BUDGET_ENV", "CAVEATS", "CLAIM_TEXT",
    "collect_liquidity_ladder", "run_ladder", "summarize_venue", "summarize_corridor", "build_headline",
    "scorecard_claim", "memo_markdown", "record_name", "fmt_size",
]

SIZES_USD: tuple[float, ...] = (1_000.0, 10_000.0, 50_000.0, 250_000.0, 500_000.0, 1_000_000.0, 2_500_000.0, 5_000_000.0)
INSTITUTIONAL_SIZE_USD = 1_000_000.0
REFERENCE_SIZE_USD = 250_000.0  # the bench's largest clip; the memo table prints the cost here next to the cost at the top
DEFAULT_BUDGET_S = 75.0
BUDGET_ENV = "VALUO_LADDER_BUDGET_S"

QUOTED, NO_LIQUIDITY, UNSUPPORTED, ERROR, NOT_ATTEMPTED = "quoted", "no_liquidity", "unsupported", "error", "not_attempted"
OUTCOMES: tuple[str, ...] = (QUOTED, NO_LIQUIDITY, UNSUPPORTED, ERROR, NOT_ATTEMPTED)
_STATUS_OUTCOME: dict[str, str] = {
    "ok": QUOTED, "no_liquidity": NO_LIQUIDITY, "unsupported_route": UNSUPPORTED, "error": ERROR, "skipped": NOT_ATTEMPTED,
}
# Venue error codes that refuse the SIZE of a request. The bench files Relay's AMOUNT_TOO_HIGH under "error" (it never
# sees it at $250K); on a ladder it is the venue's explicit size cap.
SIZE_REFUSAL_CODES: frozenset[str] = frozenset({"AMOUNT_TOO_HIGH"})
VENUE_LABEL: dict[str, str] = {"1click": "1Click", "relay": "Relay", "lifi": "LI.FI", "across": "Across"}

CAVEATS: tuple[str, ...] = (
    "A dry 'no liquidity' reflects the solvers' quoting policy at that moment. It is not proven hard depth, and a dry quote is not a fill.",
    "One run is one observation. Solver inventory and venue limits move within minutes; re-run before relying on a rung.",
    "Every figure is the largest size quoted on an eight-rung ladder ($1K to $5M), not depth. Sizes between two rungs were not observed.",
    "Cells marked not attempted did not complete inside the time budget. They carry no information about liquidity.",
)
CLAIM_TEXT = "1Click quotes institutional size: at least $1M on every benchmarked corridor"


# ----------------------------------------------------------------------------- formatting
def fmt_size(size_usd: float | None) -> str:
    """$1K, $250K, $2.5M (ladder rungs); "none" for a missing size."""
    if size_usd is None:
        return "none"
    if size_usd >= 1e6:
        return f"${size_usd / 1e6:g}M"
    if size_usd >= 1e3:
        return f"${size_usd / 1e3:g}K"
    return f"${size_usd:g}"


def _fmt_bps(value: Any) -> str:
    return f"{float(value):.2f} bps" if isinstance(value, (int, float)) and not isinstance(value, bool) else "n/a"


def venue_label(venue: str | None) -> str:
    return VENUE_LABEL.get(venue or "", venue or "n/a")


def record_name(venue: str, corridor_id: str, size_usd: float) -> str:
    """Ledger record name of one ladder quote: ``ladder:<venue>:<corridor>:<size>``."""
    size = int(size_usd) if float(size_usd).is_integer() else size_usd
    return f"ladder:{venue}:{corridor_id}:{size}"


def _budget_from_env() -> float:
    raw = os.environ.get(BUDGET_ENV, "").strip()
    try:
        value = float(raw) if raw else DEFAULT_BUDGET_S
    except ValueError:
        return DEFAULT_BUDGET_S
    return value if value > 0 else DEFAULT_BUDGET_S


# ----------------------------------------------------------------------------- one quote
def _context(corridor: Corridor, size_usd: float, tokens: eb.TokenUniverse | None) -> eb.QuoteContext:
    return eb.QuoteContext(
        corridor=corridor, clip_usd=float(size_usd), amount_in_raw=eb.amount_in_raw_for(corridor, size_usd),
        dest_price_usd=tokens.price(corridor.destination["oneclick_asset_id"]) if tokens else None,
        origin_price_usd=tokens.price(corridor.origin["oneclick_asset_id"]) if tokens else None,
    )


def _routes_across(corridor: Corridor) -> bool:
    return corridor.origin.get("across_chain_id") is not None and corridor.destination.get("across_chain_id") is not None


def _declared_reason(corridor: Corridor, venue: str) -> str | None:
    """Structural reason a venue is not called on a corridor (the bench's declaration), else None."""
    declared = corridor.venues_declared_unsupported if isinstance(corridor.venues_declared_unsupported, Mapping) else {}
    if venue in declared:
        return str(declared[venue])
    if venue == "across" and not _routes_across(corridor):
        return f"Across is EVM-only; no {corridor.destination.get('chain')} route"
    return None


async def ladder_quote(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, corridor: Corridor, size_usd: float, venue: str, *,
    tokens: eb.TokenUniverse | None, timeout_s: float, deadline: str,
) -> tuple[VenueQuote, RawRecord]:
    """One dry quote for (corridor, size, venue) with the bench's payload and parser, recorded as ``ladder:...``."""
    if venue not in eb.VENUE_SOURCE:
        raise ValueError(f"unknown venue {venue!r}; known: {eb.VENUES}")
    ctx = _context(corridor, size_usd, tokens)
    name, source = record_name(venue, corridor.corridor_id, size_usd), eb.VENUE_SOURCE[venue]
    if venue == eb.ONECLICK:
        body = eb.oneclick_payload(corridor, ctx.amount_in_raw, deadline)
        if body.get("dry") is not True:  # a non-dry quote would mint a deposit address; never send one
            raise RuntimeError("1Click ladder quote must be dry")
        parsed, record = await fetch_json(
            client, ledger, source=source, name=name, method="POST", url=f"{config.ONECLICK_API_BASE}/v0/quote",
            json=body, headers=config.oneclick_headers(), timeout=timeout_s, retries=eb.QUOTE_RETRIES,
        )
        return eb.parse_oneclick(parsed, record, ctx), record
    if venue == "relay":
        parsed, record = await fetch_json(
            client, ledger, source=source, name=name, method="POST", url=f"{config.RELAY_API_BASE}/quote",
            json=eb.relay_payload(corridor, ctx.amount_in_raw), headers={"Content-Type": "application/json"},
            timeout=timeout_s, retries=eb.QUOTE_RETRIES,
        )
        return eb.parse_relay(parsed, record, ctx), record
    if venue == "lifi":
        parsed, record = await fetch_json(
            client, ledger, source=source, name=name, method="GET", url=f"{config.LIFI_API_BASE}/quote",
            params=eb.lifi_params(corridor, ctx.amount_in_raw), timeout=timeout_s, retries=eb.QUOTE_RETRIES,
        )
        return eb.parse_lifi(parsed, record, ctx), record
    parsed, record = await fetch_json(
        client, ledger, source=source, name=name, method="GET", url=f"{config.ACROSS_API_BASE}/suggested-fees",
        params=eb.across_params(corridor, ctx.amount_in_raw), timeout=timeout_s, retries=eb.QUOTE_RETRIES,
    )
    return eb.parse_across(parsed, record, ctx), record


# ----------------------------------------------------------------------------- cells
def _empty_cell(size_usd: float, outcome: str, message: str | None, *, called: bool = False) -> dict[str, Any]:
    return {
        "size_usd": float(size_usd), "outcome": outcome, "cost_bps": None, "cost_basis": None, "amount_out": None,
        "amount_out_raw": None, "time_estimate_s": None, "message": message, "route_tool": None, "via_near_intents": False,
        "called": called, "record_source": None, "record_name": None, "sha256": None, "http_status": None, "latency_ms": None,
        "fetched_at_utc": None,
    }


def _cell(corridor: Corridor, venue: str, size_usd: float, quote: VenueQuote, record: RawRecord | None) -> dict[str, Any]:
    """Ladder cell from a parsed bench ``VenueQuote`` (already valued at the cell's common price)."""
    outcome = _STATUS_OUTCOME.get(quote.status, ERROR)
    if outcome == ERROR and getattr(quote, "error_code", None) in SIZE_REFUSAL_CODES:
        outcome = NO_LIQUIDITY
    cell = _empty_cell(size_usd, outcome, None, called=record is not None)
    if record is not None:
        cell.update(
            record_source=record.source, record_name=record.name, sha256=record.sha256, http_status=record.http_status,
            latency_ms=record.latency_ms, fetched_at_utc=record.fetched_at_utc,
        )
    if outcome != QUOTED:
        cell["message"] = (quote.error_message or "no message")[:240]
        return cell
    raw_cost, usd_cost = quote.friction_bps_raw, quote.friction_bps_usd
    cost = raw_cost if raw_cost is not None else usd_cost
    if cost is None:  # an "ok" quote without a computable cost is not a usable rung
        cell.update(outcome=ERROR, message="quote returned without a computable cost (no output amount or no reference price)")
        return cell
    out_raw = quote.amount_out_raw
    amount_out = quote.amount_out_formatted
    if isinstance(out_raw, str) and out_raw.isdigit():
        amount_out = int(out_raw) / 10 ** int(corridor.destination["decimals"])
    cell.update(
        cost_bps=float(cost), cost_basis="raw" if raw_cost is not None else "usd", amount_out=amount_out, amount_out_raw=out_raw,
        time_estimate_s=quote.time_estimate_s, route_tool=quote.route_tool,
        via_near_intents=bool(getattr(quote, "routes_via_near_intents", False)),
    )
    return cell


# ----------------------------------------------------------------------------- summaries (pure)
def summarize_venue(venue: str, cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Largest size quoted, first size refused and the cost curve of one venue on one corridor.

    A refusal is an explicit ``no_liquidity``, or an ``unsupported`` answer from a venue that did quote
    another size. ``non_monotone`` is true when a refused size lies below a quoted one; ``clean_ladder``
    requires every rung up to the largest size quoted to be quoted. ``ceiling_observed`` says whether the
    stop is known: the venue either quoted the top rung or explicitly refused a larger size.
    """
    ordered = sorted(cells, key=lambda c: float(c["size_usd"]))
    quoted = [c for c in ordered if c["outcome"] == QUOTED]
    refused = [c for c in ordered if c["outcome"] == NO_LIQUIDITY or (c["outcome"] == UNSUPPORTED and quoted and c.get("called"))]
    largest = float(quoted[-1]["size_usd"]) if quoted else None
    first_refused = refused[0] if refused else None
    contiguous: float | None = None
    for c in ordered:
        if c["outcome"] != QUOTED:
            break
        contiguous = float(c["size_usd"])
    top = float(ordered[-1]["size_usd"]) if ordered else None
    unresolved = [float(c["size_usd"]) for c in ordered if c["outcome"] in (ERROR, NOT_ATTEMPTED) and (largest is None or float(c["size_usd"]) < largest)]
    non_monotone = largest is not None and any(float(c["size_usd"]) < largest for c in refused)
    by_size = {float(c["size_usd"]): c for c in ordered}
    at_largest = by_size.get(largest) if largest is not None else None
    at_ref = by_size.get(REFERENCE_SIZE_USD)
    return {
        "venue": venue,
        "routes": bool(quoted) or any(c["outcome"] == NO_LIQUIDITY for c in ordered) or not any(c["outcome"] == UNSUPPORTED for c in ordered),
        "largest_size_quoted_usd": largest,
        "first_size_refused_usd": float(first_refused["size_usd"]) if first_refused else None,
        "first_refusal_message": first_refused.get("message") if first_refused else None,
        "contiguous_to_usd": contiguous,
        "non_monotone": bool(non_monotone),
        "clean_ladder": largest is not None and contiguous == largest,
        "ceiling_observed": largest is not None and (largest == top or any(float(c["size_usd"]) > largest for c in refused)),
        "unresolved_below_largest_usd": unresolved if largest is not None else [],
        "cost_bps_at_largest": at_largest.get("cost_bps") if at_largest else None,
        "cost_bps_at_250k": at_ref.get("cost_bps") if at_ref and at_ref["outcome"] == QUOTED else None,
        "via_near_intents_at_largest": bool(at_largest.get("via_near_intents")) if at_largest else False,
        # Largest size quoted on a route that is not NEAR Intents resold (LI.FI's tool "near" is 1Click execution).
        "largest_size_quoted_independent_usd": max((float(c["size_usd"]) for c in quoted if not c.get("via_near_intents")), default=None),
        "n_quoted": len(quoted),
        "n_attempted": sum(1 for c in ordered if c["outcome"] in (QUOTED, NO_LIQUIDITY, ERROR) or (c["outcome"] == UNSUPPORTED and c.get("called"))),
        "cost_curve": [{"size_usd": float(c["size_usd"]), "cost_bps": c["cost_bps"]} for c in quoted],
        "cells": [dict(c) for c in ordered],
    }


def summarize_corridor(corridor: Mapping[str, Any], venues: Sequence[Mapping[str, Any]], sizes_usd: Sequence[float]) -> dict[str, Any]:
    """Which venue quotes the largest size, the cheapest venue at each size, and 1Click against its best competitor."""
    largest_by_venue = {v["venue"]: v["largest_size_quoted_usd"] for v in venues}
    quoted_sizes = [s for s in largest_by_venue.values() if s is not None]
    corridor_largest = max(quoted_sizes) if quoted_sizes else None
    cheapest: list[dict[str, Any]] = []
    for size in sizes_usd:
        offers = []
        for v in venues:
            cell = next((c for c in v["cells"] if float(c["size_usd"]) == float(size)), None)
            if cell is not None and cell["outcome"] == QUOTED and cell["cost_bps"] is not None:
                offers.append((float(cell["cost_bps"]), v["venue"]))
        best = min(offers) if offers else None
        cheapest.append({
            "size_usd": float(size), "venue": best[1] if best else None, "cost_bps": best[0] if best else None,
            "n_quoted": len(offers), "venues_quoted": [name for _, name in sorted(offers, key=lambda o: eb.VENUES.index(o[1]) if o[1] in eb.VENUES else 99)],
        })
    one = next((v for v in venues if v["venue"] == eb.ONECLICK), None)
    competitors = [v for v in venues if v["venue"] != eb.ONECLICK and v["largest_size_quoted_usd"] is not None]
    # Best competitor = the one quoting the largest size; ties go to the lower cost at that size.
    best_comp = min(competitors, key=lambda v: (-v["largest_size_quoted_usd"], v["cost_bps_at_largest"] if v["cost_bps_at_largest"] is not None else float("inf"))) if competitors else None
    one_largest = one["largest_size_quoted_usd"] if one else None
    comp_largest = best_comp["largest_size_quoted_usd"] if best_comp else None
    independent = [v for v in venues if v["venue"] != eb.ONECLICK and v.get("largest_size_quoted_independent_usd") is not None]
    best_indep = max(independent, key=lambda v: v["largest_size_quoted_independent_usd"]) if independent else None
    if one is None or one["n_attempted"] == 0:
        relation = "not_measured"
    elif comp_largest is None:
        relation = "larger" if one_largest is not None else "not_measured"
    elif one_largest is not None and one_largest > comp_largest:
        relation = "larger"
    elif one_largest is not None and one_largest == comp_largest:
        relation = "equal"
    elif one_largest is not None and not one["ceiling_observed"]:
        relation = "inconclusive"  # 1Click's larger rungs errored or were not reached: no refusal was observed
    elif one_largest is None and not any(c["outcome"] == NO_LIQUIDITY for c in one["cells"]):
        relation = "inconclusive"
    else:
        relation = "smaller"
    return {
        "corridor_id": corridor["corridor_id"], "label": corridor["label"], "archetype": corridor.get("archetype"),
        "cost_basis": corridor.get("cost_basis"), "price_basis": corridor.get("price_basis"),
        "largest_size_quoted_usd": corridor_largest,
        "largest_size_venues": [v for v, s in largest_by_venue.items() if s is not None and s == corridor_largest],
        "oneclick_largest_size_quoted_usd": one_largest,
        "best_competitor": best_comp["venue"] if best_comp else None,
        "best_competitor_largest_size_quoted_usd": comp_largest,
        "best_competitor_via_near_intents": bool(best_comp["via_near_intents_at_largest"]) if best_comp else False,
        "best_independent_competitor": best_indep["venue"] if best_indep else None,
        "best_independent_competitor_largest_size_quoted_usd": best_indep["largest_size_quoted_independent_usd"] if best_indep else None,
        "oneclick_vs_best_competitor": relation,
        "any_non_monotone": any(v["non_monotone"] for v in venues),
        "cheapest_by_size": cheapest,
        "venues": [dict(v) for v in venues],
    }


def _comp_text(c: Mapping[str, Any]) -> str:
    if c.get("best_competitor") is None:
        return "no competitor quoted"
    via = " (routed through NEAR Intents)" if c.get("best_competitor_via_near_intents") else ""
    return f"{venue_label(c['best_competitor'])} {fmt_size(c['best_competitor_largest_size_quoted_usd'])}{via}"


def build_headline(corridors: Sequence[Mapping[str, Any]]) -> str:
    """One sentence that states the result either way, in "largest size quoted" terms."""
    n = len(corridors)
    if n == 0:
        return "No corridor was measured in this run"
    smaller = [c for c in corridors if c["oneclick_vs_best_competitor"] == "smaller"]
    unknown = [c for c in corridors if c["oneclick_vs_best_competitor"] in ("inconclusive", "not_measured")]
    if smaller:
        detail = "; ".join(
            f"{c['label']}, {fmt_size(c['oneclick_largest_size_quoted_usd']) if c['oneclick_largest_size_quoted_usd'] is not None else 'no size quoted'} against {_comp_text(c)}"
            for c in smaller
        )
        tail = f"; {len(unknown)} of {n} not conclusive" if unknown else ""
        return f"1Click stops quoting at a smaller size than a competitor on {len(smaller)} of {n} corridors: {detail}{tail}"
    measured = [c for c in corridors if c not in unknown]
    if not measured:
        return f"The ladder did not reach a conclusive comparison on any of the {n} corridors in this run"
    detail = "; ".join(f"{c['label']} {fmt_size(c['oneclick_largest_size_quoted_usd'])} (best competitor: {_comp_text(c)})" for c in measured)
    scope = f"all {n} corridors" if not unknown else f"{len(measured)} of {n} corridors ({len(unknown)} not conclusive)"
    return f"1Click's largest size quoted matches or exceeds every competitor on {scope}: {detail}"


def _takeaway(corridors: Sequence[Mapping[str, Any]]) -> str:
    """The sentence a reader can act on: what the ladder says about the long-term case and what overturns it."""
    n = len(corridors)
    at_inst = [c for c in corridors if (c["oneclick_largest_size_quoted_usd"] or 0) >= INSTITUTIONAL_SIZE_USD]
    smaller = [c for c in corridors if c["oneclick_vs_best_competitor"] == "smaller"]
    lead = f"On this run 1Click quoted at least {fmt_size(INSTITUTIONAL_SIZE_USD)} on {len(at_inst)} of {n} corridors"
    resold = [c for c in corridors if c.get("best_competitor_via_near_intents") and c["oneclick_largest_size_quoted_usd"] is not None]
    resold_note = "".join(
        f" On {c['label']} the largest competitor quote ({venue_label(c['best_competitor'])} {fmt_size(c['best_competitor_largest_size_quoted_usd'])}) "
        "is 1Click execution resold; the largest quote on an independent route was "
        + (f"{fmt_size(c['best_independent_competitor_largest_size_quoted_usd'])} ({venue_label(c['best_independent_competitor'])})." if c.get("best_independent_competitor") else "none.")
        for c in resold
    )
    if smaller:
        return (
            f"{lead} and stopped below a competitor on {len(smaller)}. That cuts against the case that the solver network already carries "
            "institutional clips on those routes: fee growth there has to come from retail-size flow until solver inventory deepens."
            f"{resold_note} Repeated runs in which 1Click quotes the same rungs its competitors do would overturn this reading."
        )
    if len(at_inst) == n and n:
        return (
            f"{lead}, so quoted size is not the constraint on fee growth at this moment.{resold_note} "
            "Repeated runs in which 1Click refuses a size that a competitor quotes on the same corridor would overturn this reading."
        )
    return (
        f"{lead}; where it stopped lower, no competitor quoted more. Quoted size limits the fee base on those routes for every router, "
        f"not for NEAR Intents alone.{resold_note} Repeated runs in which a competitor quotes sizes 1Click refuses would turn this into a relative weakness."
    )


# ----------------------------------------------------------------------------- orchestration
async def run_ladder(
    client: httpx.AsyncClient,
    ledger: ProvenanceLedger,
    *,
    sizes_usd: Sequence[float] = SIZES_USD,
    corridors: Sequence[Corridor] | None = None,
    budget_s: float = DEFAULT_BUDGET_S,
    concurrency: int = eb.DEFAULT_CONCURRENCY,
    request_timeout_s: float = eb.DEFAULT_REQUEST_TIMEOUT_S,
) -> dict[str, Any] | None:
    """Run the ladder and return the snapshot dict; None (with a ledger warning) when no venue answered at all."""
    started = time.perf_counter()
    ran_at = utc_now_iso()
    sizes = sorted({float(s) for s in sizes_usd})
    if not sizes or sizes[0] <= 0:
        raise ValueError(f"sizes_usd must be positive, got {list(sizes_usd)}")
    corridor_list = list(corridors) if corridors is not None else list(eb.CORRIDORS)

    parsed_tokens, token_record = await fetch_json(
        client, ledger, source="oneclick", name="ladder:tokens", method="GET", url=f"{config.ONECLICK_API_BASE}/v0/tokens",
        headers=config.oneclick_headers(), timeout=request_timeout_s, retries=eb.QUOTE_RETRIES,
    )
    tokens = eb.parse_oneclick_tokens(parsed_tokens if token_record.ok else None, token_record.sha256)
    if not tokens.ok:
        ledger.warn(
            f"liquidity_ladder: 1Click /v0/tokens unavailable ({token_record.error}); cross-asset costs are valued at the median of the "
            "venues' own implied prices"
        )

    semaphore = asyncio.Semaphore(max(1, int(concurrency)))
    deadline = eb.deadline_iso()
    quotes: dict[tuple[str, str, float], tuple[VenueQuote, RawRecord | None]] = {}
    preset: dict[tuple[str, str, float], dict[str, Any]] = {}

    async def chain(corridor: Corridor, venue: str) -> None:
        """Ascending sizes for one (corridor, venue). Stops calling once the venue says it does not route the corridor."""
        any_quoted = False
        for i, size in enumerate(sizes):
            key = (corridor.corridor_id, venue, size)
            try:
                async with semaphore:
                    quote, record = await ladder_quote(
                        client, ledger, corridor, size, venue, tokens=tokens if tokens.ok else None, timeout_s=request_timeout_s, deadline=deadline,
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - one failed rung must not lose the chain
                preset[key] = _empty_cell(size, ERROR, f"{type(exc).__name__}: {exc}"[:240], called=True)
                continue
            quotes[key] = (quote, record)
            any_quoted = any_quoted or quote.status == "ok"
            if quote.status == "unsupported_route" and not any_quoted and i == 0:
                reason = f"not called: {venue_label(venue)} refused the route at {fmt_size(size)} ({(quote.error_message or 'unsupported route')[:120]})"
                for later in sizes[1:]:
                    preset[(corridor.corridor_id, venue, later)] = _empty_cell(later, UNSUPPORTED, reason)
                return

    tasks: list[asyncio.Task[None]] = []
    for corridor in corridor_list:
        for venue in corridor.venues_attempted:
            reason = _declared_reason(corridor, venue)
            if reason is not None:
                for size in sizes:
                    preset[(corridor.corridor_id, venue, size)] = _empty_cell(size, UNSUPPORTED, reason)
                continue
            tasks.append(asyncio.ensure_future(chain(corridor, venue)))
    if tasks:
        remaining = max(0.05, budget_s - (time.perf_counter() - started))
        _done, pending = await asyncio.wait(set(tasks), timeout=remaining)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    out_corridors: list[dict[str, Any]] = []
    counts = dict.fromkeys(OUTCOMES, 0)
    for corridor in corridor_list:
        venue_cells: dict[str, list[dict[str, Any]]] = {v: [] for v in corridor.venues_attempted}
        price_basis: dict[str, Any] | None = None
        for size in sizes:
            keys = [(corridor.corridor_id, v, size) for v in corridor.venues_attempted]
            live = [(k, quotes[k]) for k in keys if k in quotes]
            # One common price for every venue in the (corridor, size) cell, exactly as the bench scores a cell.
            valued, basis = eb.common_price_basis(corridor, eb.amount_in_raw_for(corridor, size), [q for _, (q, _r) in live])
            if basis.get("source") and price_basis is None:
                price_basis = dict(basis)
            valued_by_key = {k: (q, rec) for (k, (_q, rec)), q in zip(live, valued)}
            for key in keys:
                venue = key[1]
                if key in valued_by_key:
                    quote, record = valued_by_key[key]
                    cell = _cell(corridor, venue, size, quote, record)
                elif key in preset:
                    cell = preset[key]
                else:
                    cell = _empty_cell(size, NOT_ATTEMPTED, f"not completed within the {budget_s:.0f} s ladder budget")
                counts[cell["outcome"]] += 1
                venue_cells[venue].append(cell)
        same_asset = corridor.origin.get("symbol") == corridor.destination.get("symbol") and corridor.origin.get("decimals") == corridor.destination.get("decimals")
        venues = [summarize_venue(v, venue_cells[v]) for v in sorted(venue_cells, key=lambda v: eb.VENUES.index(v) if v in eb.VENUES else 99)]
        out_corridors.append(summarize_corridor(
            {
                "corridor_id": corridor.corridor_id, "label": corridor.label, "archetype": corridor.archetype,
                "cost_basis": "raw_units" if same_asset else ((price_basis or {}).get("source") or "usd_legs"),
                "price_basis": price_basis,
            },
            venues, sizes,
        ))

    n_cells = sum(counts.values())
    if counts[NOT_ATTEMPTED]:
        ledger.warn(
            f"liquidity_ladder: {counts[NOT_ATTEMPTED]} of {n_cells} ladder cells were not completed within the {budget_s:.0f} s budget; "
            "they are recorded as not_attempted, not as no liquidity"
        )
    if counts[QUOTED] + counts[NO_LIQUIDITY] == 0:
        ledger.warn("liquidity_ladder: no venue returned a quote or an explicit refusal; snapshot.liquidity_ladder is null")
        return None
    for c in out_corridors:
        for v in c["venues"]:
            if v["non_monotone"]:
                ledger.warn(
                    f"liquidity_ladder: {c['corridor_id']} {v['venue']} refused {fmt_size(v['first_size_refused_usd'])} but quoted "
                    f"{fmt_size(v['largest_size_quoted_usd'])}; the ladder is not monotone, so the largest size quoted is not a clean limit"
                )
    return {
        "ran_at_utc": ran_at,
        "sizes_usd": sizes,
        "institutional_size_usd": INSTITUTIONAL_SIZE_USD,
        "venues": list(eb.VENUES),
        "headline": build_headline(out_corridors),
        "takeaway": _takeaway(out_corridors),
        "caveats": list(CAVEATS),
        "corridors": out_corridors,
        "outcome_counts": counts,
        "n_cells": n_cells,
        "n_http_records": sum(1 for r in ledger.records if r.name.startswith("ladder:") and r.name != "ladder:tokens"),
        "cost_definition": (
            "(amount in - amount out) / amount in x 1e4: on raw units where both legs are the same stablecoin, else on USD legs valued at one "
            "common price per cell (1Click token-list oracle, else the median of the venues' implied prices), as in execution_bench"
        ),
        "record_name_pattern": "ladder:<venue>:<corridor_id>:<size_usd>",
        "token_list_ok": tokens.ok, "token_list_sha256": tokens.record_sha256,
        "all_quotes_dry": True,
        "budget_s": float(budget_s), "concurrency": int(concurrency), "request_timeout_s": float(request_timeout_s),
        "elapsed_s": round(time.perf_counter() - started, 3),
    }


async def collect_liquidity_ladder(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, args: Any, log: Any, events: Mapping[str, asyncio.Event],
) -> dict[str, Any] | None:
    """``EXTRA_COLLECTORS`` entry point: waits for the quote race, then runs the ladder inside its own budget."""
    bench_done = events.get("bench_done") if isinstance(events, Mapping) else None
    if bench_done is not None:
        await bench_done.wait()  # never compete with the main race for venue rate limits
    if getattr(args, "skip_bench", False):
        ledger.warn("liquidity_ladder: skipped (--skip-bench); snapshot.liquidity_ladder is null")
        return None
    budget = _budget_from_env()
    data = await run_ladder(client, ledger, budget_s=budget)
    if data is not None and callable(log):
        c = data["outcome_counts"]
        log(
            f"liquidity_ladder: {c[QUOTED]} quoted, {c[NO_LIQUIDITY]} refused, {c[ERROR]} errors, {c[NOT_ATTEMPTED]} not attempted "
            f"of {data['n_cells']} cells in {data['elapsed_s']:.1f}s"
        )
    return data


# ----------------------------------------------------------------------------- scorecard + memo
def _oneclick(corridor: Mapping[str, Any]) -> Mapping[str, Any] | None:
    return next((v for v in corridor.get("venues") or [] if isinstance(v, Mapping) and v.get("venue") == eb.ONECLICK), None)


def scorecard_claim(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Graded claim: VERIFIED_LIVE_API only if 1Click quoted >= $1M on every corridor where a 1Click rung at or
    above $1M was attempted (quoted, refused or errored); NOT_SUPPORTED otherwise, including when none was attempted."""
    if not isinstance(data, Mapping) or not isinstance(data.get("corridors"), list) or not data["corridors"]:
        return None
    threshold = float(data.get("institutional_size_usd") or INSTITUTIONAL_SIZE_USD)
    parts: list[str] = []
    eligible = passed = 0
    not_reached: list[str] = []
    gaps: list[str] = []
    for c in data["corridors"]:
        one = _oneclick(c)
        label = str(c.get("label") or c.get("corridor_id"))
        one_largest = c.get("oneclick_largest_size_quoted_usd")
        comp = _comp_text(c)
        parts.append(f"{label}: 1Click {fmt_size(one_largest) if one_largest is not None else 'no size quoted'}, best competitor {comp}")
        top_cells = [x for x in (one or {}).get("cells") or [] if float(x.get("size_usd") or 0) >= threshold]
        if not any(x.get("outcome") in (QUOTED, NO_LIQUIDITY, ERROR) for x in top_cells):
            not_reached.append(label)
            continue
        eligible += 1
        if one_largest is not None and float(one_largest) >= threshold:
            passed += 1
        if one and one.get("non_monotone"):
            gaps.append(label)
    ok = eligible > 0 and passed == eligible
    note = (
        "Largest size quoted on an eight-rung ladder of dry quotes, one run. A dry 'no liquidity' is solver quoting policy at that moment, "
        "not proven depth, and a dry quote is not a fill."
    )
    if not_reached:
        note += f" No 1Click rung at or above {fmt_size(threshold)} was attempted on: {', '.join(not_reached)}."
    if gaps:
        note += f" Not a clean ladder (a smaller size was refused) on: {', '.join(gaps)}."
    value = "; ".join(parts) + f" ({passed} of {eligible} corridors with an attempted 1Click rung at or above {fmt_size(threshold)})"
    return {
        "claim": CLAIM_TEXT,
        "status": "VERIFIED_LIVE_API" if ok else "NOT_SUPPORTED",
        "value": value if eligible else value + "; not measured this run",
        "source": f"1Click, Relay, LI.FI, Across dry quotes; ledger records {data.get('record_name_pattern', 'ladder:<venue>:<corridor_id>:<size_usd>')} ({data.get('n_http_records', 'n/a')} responses), run {data.get('ran_at_utc')}",
        "confidence": "medium" if ok and not gaps and not not_reached else "low",
        "note": note,
    }


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], align: Sequence[str]) -> str:
    sep = ["---:" if a == "r" else ":---" for a in align]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    lines.append("")
    return "\n".join(lines)


def memo_markdown(data: Mapping[str, Any], snap_dict: Mapping[str, Any] | None = None) -> str:
    """Memo sub-section: headline, corridor x venue table (largest size quoted, cost at $250K and at that size), caveats."""
    rows: list[list[str]] = []
    for c in data.get("corridors") or []:
        for v in c.get("venues") or []:
            largest = v.get("largest_size_quoted_usd")
            if not v.get("routes"):
                rows.append([str(c.get("label")), venue_label(v.get("venue")), "does not route", "n/a", "n/a", "n/a"])
                continue
            flag = " (not monotone)" if v.get("non_monotone") else ""
            via = " via NEAR Intents" if v.get("via_near_intents_at_largest") else ""
            refused = v.get("first_size_refused_usd")
            rows.append([
                str(c.get("label")), venue_label(v.get("venue")),
                (fmt_size(largest) if largest is not None else "none") + flag,
                _fmt_bps(v.get("cost_bps_at_250k")),
                (_fmt_bps(v.get("cost_bps_at_largest")) + via) if largest is not None else "n/a",
                fmt_size(refused) if refused is not None else ("none on the ladder" if v.get("n_attempted") else "not attempted"),
            ])
    counts = data.get("outcome_counts") or {}
    sizes = ", ".join(fmt_size(float(s)) for s in data.get("sizes_usd") or [])
    parts = [
        f"**{data.get('headline')}.**",
        (
            f"Dry quotes at {sizes} on each benchmarked corridor, run {data.get('ran_at_utc')}: {counts.get(QUOTED, 0)} quoted, "
            f"{counts.get(NO_LIQUIDITY, 0)} refused, {counts.get(ERROR, 0)} errors, {counts.get(NOT_ATTEMPTED, 0)} not attempted, "
            f"{counts.get(UNSUPPORTED, 0)} on routes the venue does not serve ({data.get('n_cells', 0)} cells, "
            f"{data.get('elapsed_s', 'n/a')} s against a {data.get('budget_s', 'n/a')} s budget)."
        ),
        _md_table(
            ["Corridor", "Venue", "Largest size quoted", "Cost at $250K", "Cost at largest size", "First size refused"],
            rows, ["l", "l", "r", "r", "r", "r"],
        ),
        f"Cost: {data.get('cost_definition')}.",
        str(data.get("takeaway") or ""),
        "Limits:\n" + "\n".join(f"- {c}" for c in data.get("caveats") or []),
        f"Raw responses: ledger records `{data.get('record_name_pattern')}`; data in `snapshot.liquidity_ladder`.",
    ]
    return "\n\n".join(p for p in parts if p)
