"""Wider peer set for relative value: FDV / annualised chain revenue across the top revenue chains.

Question: where does NEAR's FDV-to-revenue multiple sit in a peer distribution wide enough to have a meaningful
median, and does the model's terminal multiple cap hold up against it? The valuation's own peer set
(``comps.peers``) is three names; this view is ADDITIVE and feeds nothing into the valuation.

Method (two key-free calls, both persisted and hashed through the ProvenanceLedger):

1. Revenue: DefiLlama ``/overview/fees?dataType=dailyRevenue``. The rows with ``category == "Chain"`` and
   ``total30d > 0`` are ranked by 30-day revenue, highest first.
2. FDV: ONE CoinGecko ``/coins/markets`` call for every token id in ``COINGECKO_ID_BY_SLUG`` plus NEAR
   (``fully_diluted_valuation``).
3. Inclusion, fixed before looking at any multiple (``INCLUSION_RULES``): walk the ranking and take the first
   ``N_PEERS_TARGET`` chains that have their own token with an FDV. Chains without a token, chains whose token
   has no FDV, chains missing from the mapping table and second rows for a token already counted are listed in
   ``excluded`` with the reason. NEAR is the subject: it is positioned against the set, not counted in it.
4. Per peer: ``annualized_revenue = total30d x 365 / 30`` and ``fdv_to_revenue = FDV / annualized_revenue``
   (the same formulas as ``valuo.collectors.comps``).
5. Distribution of ``fdv_to_revenue``: median, quartiles (linear interpolation), IQR, min, max and a bootstrap 90%
   interval for the median (10,000 resamples with replacement, seed 20261114, 5th and 95th percentiles).
6. Position of a value v against the set: ``percentile = (peers with multiple <= v) / n_peers``. Reported for NEAR
   (L1 gas revenue only, from the same two payloads, so like for like) and for the model's
   ``terminal_multiple_cap`` / ``terminal_multiple_floor`` (read from the assumptions registry the run uses).

Limits: 30 days annualised is a noisy run-rate; "revenue" means what each chain's DefiLlama adapter says it means
(carried per row as ``revenue_methodology``); an L2 token or an exchange-linked token does not accrue chain
revenue the way an L1 gas token does (such rows are flagged, kept in the set, and a sensitivity excluding them is
reported); the chain -> token mapping is configuration; one snapshot, no history. NEAR's multiple here is L1-only
and is NOT the model's combined (L1 + Intents) figure in ``comps.near_combined``.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from typing import Any

import httpx
import numpy as np

from valuo import assumptions, config
from valuo.collectors.comps import annualize_30d, multiple
from valuo.provenance import ProvenanceLedger, fetch_json, utc_now_iso

__all__ = [
    "COINGECKO_ID_BY_SLUG", "NO_TOKEN_REASON_BY_SLUG", "FLAG_BY_SLUG", "INCLUSION_RULES", "CAVEATS",
    "N_PEERS_TARGET", "MIN_PEERS_FOR_CLAIM", "BOOTSTRAP_SEED", "BOOTSTRAP_RESAMPLES",
    "parse_chain_rows", "parse_market_rows", "percentile_at_or_below", "distribution",
    "build_wide_peers", "collect_wide_peers", "scorecard_claim", "memo_markdown",
]

SNAPSHOT_KEY = "wide_peers"
SUBJECT_SLUG = "near"
SUBJECT_COINGECKO_ID = "near"
N_PEERS_TARGET = 15
MIN_PEERS_FOR_CLAIM = 8
BOOTSTRAP_SEED = 20261114
BOOTSTRAP_RESAMPLES = 10_000
OVERVIEW_PARAMS: dict[str, str] = {
    "excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true", "dataType": "dailyRevenue",
}
OVERVIEW_RECORD = ("defillama", "overview:fees:dailyRevenue")
MARKETS_RECORD = ("coingecko", "coins_markets_wide")
# CoinGecko's key-free tier answers bursts with 429. One batched call, retried with backoff (Retry-After honoured up
# to 30 s); a 403 challenge is retried once. Failure -> warning + null key, never an aborted run.
_COINGECKO_RETRIES = 2
_COINGECKO_BACKOFF_S = 3.0
_COINGECKO_RETRY_AFTER_CAP_S = 30.0

# ----------------------------------------------------------------------------- configuration (not data)
# DefiLlama chain slug -> CoinGecko id of the chain's own token. Covers the ~30 highest-revenue chain rows
# (ids cross-checked against DefiLlama /v2/chains ``gecko_id``, November 2026). A chain that ranks inside the cut
# and is in neither table is listed in ``excluded`` as unmapped and raises a warning; it is never dropped silently.
COINGECKO_ID_BY_SLUG: dict[str, str] = {
    "tron": "tron",
    "ethereum": "ethereum",
    "solana": "solana",
    "polygon": "polygon-ecosystem-token",
    "bsc": "binancecoin",
    "hyperliquid-l1": "hyperliquid",
    "arbitrum": "arbitrum",
    "avalanche": "avalanche-2",
    "monad": "monad",
    "quai": "quai-network",
    "icp": "internet-computer",
    "injective": "injective-protocol",
    "aptos": "aptos",
    "starknet": "starknet",
    "filecoin": "filecoin",
    "dexalot": "dexalot",
    "linea": "linea",
    "op-mainnet": "optimism",
    "megaeth": "megaeth",
    "pulsechain": "pulsechain",
    "xrpl": "ripple",
    "x-layer": "okb",
    "ton": "the-open-network",
    "stellar": "stellar",
    "thorchain": "thorchain",
    "celo": "celo",
    "cardano": "cardano",
    "zksync-era": "zksync",
    "berachain-incentive-buys": "berachain-bera",
    "mantle": "mantle",
}
# Chains with revenue but no token of their own to put an FDV on.
NO_TOKEN_REASON_BY_SLUG: dict[str, str] = {
    "base": "no native token: Coinbase-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue",
    "robinhood-chain": "no native token: Robinhood-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue",
    "abstract": "no native token listed: DefiLlama's chain list carries no CoinGecko id for it",
    "ink": "no native token listed: DefiLlama's chain list carries no CoinGecko id for it",
    "soneium": "no native token listed: DefiLlama's chain list carries no CoinGecko id for it",
}
# Rows kept in the set but flagged: the token's FDV is not priced on this chain-revenue row alone.
FLAG_BY_SLUG: dict[str, str] = {
    "hyperliquid-l1": "chain row covers HyperEVM gas only; HYPE's FDV is priced mostly on the HyperCore exchange, whose "
                      "revenue DefiLlama books under separate Hyperliquid protocols (the model's three-peer set uses that parent)",
    "quai": "revenue is merged-mining block rewards earned on other chains and spent on QUAI buyback and burn (the adapter's own Fees "
            "text), not gas paid on Quai",
    "bsc": "exchange-linked token: BNB's FDV also prices Binance exchange utility, not only BNB Chain's fee burn",
    "x-layer": "exchange-linked token: OKB is OKX's exchange token, not a pure X Layer gas token",
    "arbitrum": "L2 governance token: sequencer revenue accrues to the DAO treasury, not to ARB by protocol rule",
    "starknet": "L2 token: sequencer revenue accrues to the operator and foundation, not to STRK by protocol rule",
    "op-mainnet": "L2 governance token: sequencer revenue accrues to the Optimism Collective, not to OP by protocol rule",
    "linea": "L2 token: sequencer revenue accrues to the operator; the LINEA burn covers only part of it",
    "zksync-era": "L2 governance token: sequencer revenue accrues to the operator, not to ZK by protocol rule",
    "megaeth": "L2 token: sequencer revenue accrues to the operator, not to the token by protocol rule",
    "mantle": "L2 token: sequencer revenue accrues to the Mantle treasury, not to MNT by protocol rule",
    "celo": "L2 token since 2025: net sequencer revenue goes to the Celo Community Fund, not to CELO holders directly",
}
# The model's own three-peer set (comps.PEER_SPECS), rebuilt here from the same two payloads for contrast only:
# (label, CoinGecko id, chain slug in the overview or None, DefiLlama parentProtocol id whose child rows are summed or None).
_MODEL_THREE: tuple[tuple[str, str, str | None, str | None], ...] = (
    ("Solana", "solana", "solana", None),
    ("Ethereum", "ethereum", "ethereum", None),
    ("Hyperliquid (parent: perps + spot + HLP + outcomes)", "hyperliquid", None, "parent#hyperliquid"),
)

INCLUSION_RULES: tuple[str, ...] = (
    "Universe: every DefiLlama fees-overview row with category 'Chain' and 30-day revenue (dataType=dailyRevenue) above zero.",
    "Ranking: by 30-day revenue, highest first. No chain is added or removed by hand after seeing its multiple.",
    f"Peers: the first {N_PEERS_TARGET} chains in that ranking that have their own token with a CoinGecko fully diluted valuation.",
    "Excluded, each listed with its reason: chains with no native token; chains whose token has no FDV on CoinGecko; chains not "
    "in the chain-to-token mapping table (configuration in wide_peers.py); a second row for a token already counted.",
    "Flagged, not dropped: L2 tokens, exchange-linked tokens, rows whose adapter books something other than chain gas revenue and "
    "rows whose DefiLlama adapter is not typed 'chain'. They stay in the distribution; a sensitivity without them is reported next to it.",
    "NEAR is the subject. It is positioned against the set on the same basis (its own chain row and CoinGecko FDV) and is not counted in it.",
    "Multiple: FDV / (30-day revenue x 365 / 30). Percentile of a value: share of peers with a multiple at or below it.",
)
CAVEATS: tuple[str, ...] = (
    "FDV to revenue on 30 days annualised is noisy: one busy or quiet month moves a chain's multiple by a large factor.",
    "Revenue definitions differ by chain adapter (burned base fees, sequencer profit, treasury share, buyback and burn); the adapter's own text is carried per row.",
    "Token FDV for an L2 or an exchange-linked token does not accrue chain revenue the way an L1 gas token does; those rows are flagged and a sensitivity without them is shown.",
    "Selection: ranking by revenue picks the chains with the most revenue, which pulls their multiples down relative to the long tail of low-revenue chains.",
    "NEAR's multiple here uses L1 gas revenue only. The model values NEAR on L1 plus Intents revenue (comps.near_combined), which no peer row here has an equivalent of.",
    "One snapshot. Nothing here is a time series, and the cap's position will move with token prices and monthly fee volume.",
)


# ----------------------------------------------------------------------------- small helpers
def _num(value: Any) -> float | None:
    """Finite float from an int, float or numeric string; None otherwise (bool is not a number here)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if isfinite(out) else None


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _x(value: Any, decimals: int | None = None) -> str:
    """``1,234x`` / ``60x`` / ``8.4x``: no decimals from 100x up or for whole numbers, one below."""
    v = _num(value)
    if v is None:
        return "n/a"
    if decimals is None:
        decimals = 0 if v >= 100 or float(v).is_integer() else 1
    return f"{v:,.{decimals}f}x"


def _usd(value: Any) -> str:
    v = _num(value)
    if v is None:
        return "n/a"
    a = abs(v)
    if a >= 1e9:
        return f"${v / 1e9:,.2f}B"
    if a >= 1e6:
        return f"${v / 1e6:,.1f}M"
    return f"${v:,.0f}"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _pctile(p: Any) -> str:
    """0.47 -> '47th percentile'."""
    v = _num(p)
    return "n/a" if v is None else f"{_ordinal(int(round(v * 100)))} percentile"


# ----------------------------------------------------------------------------- payload parsing
def parse_chain_rows(overview_payload: Any) -> tuple[list[dict[str, Any]], int]:
    """Chain rows of a DefiLlama fees overview, ranked by 30-day revenue (highest first; slug breaks ties).

    Returns ``(rows, n_malformed)``. A row needs ``category == "Chain"``, a slug, a name and a finite
    ``total30d > 0``; chain rows failing that are counted in ``n_malformed`` when the fault is a missing or
    non-numeric field (a zero or negative total is simply not ranked). ``rank_by_revenue`` starts at 1.
    """
    protocols = overview_payload.get("protocols") if isinstance(overview_payload, Mapping) else None
    if not isinstance(protocols, list):
        return [], 0
    rows: list[dict[str, Any]] = []
    malformed = 0
    for entry in protocols:
        if not isinstance(entry, Mapping) or entry.get("category") != "Chain":
            continue
        slug, name = _text(entry.get("slug")), _text(entry.get("displayName")) or _text(entry.get("name"))
        raw30 = entry.get("total30d")
        rev30 = _num(raw30)
        if slug is None or name is None or (raw30 is not None and rev30 is None):
            malformed += 1
            continue
        if rev30 is None or rev30 <= 0:
            continue
        method = entry.get("methodology")
        rows.append({
            "chain": name,
            "slug": slug,
            "revenue_30d_usd": rev30,
            "revenue_1y_usd": _num(entry.get("total1y")),
            "protocol_type": _text(entry.get("protocolType")),
            "revenue_methodology": _text(method.get("Revenue")) if isinstance(method, Mapping) else None,
        })
    rows.sort(key=lambda r: (-r["revenue_30d_usd"], r["slug"]))
    for i, row in enumerate(rows, start=1):
        row["rank_by_revenue"] = i
    return rows, malformed


def parse_market_rows(markets_payload: Any) -> dict[str, dict[str, Any]]:
    """CoinGecko ``/coins/markets`` array -> {id: {symbol, fdv_usd, market_cap_usd, price_usd}}; {} if not an array.

    ``fdv_usd`` is kept only when finite and positive (CoinGecko returns null for some tokens).
    """
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(markets_payload, list):
        return out
    for row in markets_payload:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            continue
        fdv = _num(row.get("fully_diluted_valuation"))
        symbol = _text(row.get("symbol"))
        out[row["id"]] = {
            "symbol": symbol.upper() if symbol else None,
            "fdv_usd": fdv if fdv is not None and fdv > 0 else None,
            "market_cap_usd": _num(row.get("market_cap")),
            "price_usd": _num(row.get("current_price")),
        }
    return out


# ----------------------------------------------------------------------------- statistics
def percentile_at_or_below(value: float | None, values: Sequence[float]) -> float | None:
    """Share of ``values`` at or below ``value`` (empirical CDF, 0..1); None when either side is missing."""
    if value is None or not values:
        return None
    return sum(1 for v in values if v <= value) / len(values)


def distribution(values: Sequence[float], *, seed: int = BOOTSTRAP_SEED, n_resamples: int = BOOTSTRAP_RESAMPLES) -> dict[str, Any]:
    """Median, quartiles (numpy linear interpolation), IQR, min, max and a seeded bootstrap 90% interval for the median.

    The bootstrap resamples the n multiples with replacement ``n_resamples`` times and takes the 5th and 95th
    percentiles of the resampled medians. With one value the interval collapses to it; with none every field is null.
    """
    vals = np.asarray([v for v in values if v is not None and isfinite(v)], dtype=float)
    n = int(vals.size)
    boot = {"seed": seed, "n_resamples": n_resamples, "method": "percentile bootstrap of the median, resampling peers with replacement; 5th and 95th percentiles"}
    if n == 0:
        return {"n": 0, "median": None, "p25": None, "p75": None, "iqr": None, "min": None, "max": None, "median_ci90": None, "bootstrap": boot}
    p25, med, p75 = (float(x) for x in np.percentile(vals, [25, 50, 75]))
    rng = np.random.default_rng(seed)
    medians = np.median(vals[rng.integers(0, n, size=(n_resamples, n))], axis=1)
    lo, hi = (float(x) for x in np.percentile(medians, [5, 95]))
    return {
        "n": n, "median": med, "p25": p25, "p75": p75, "iqr": p75 - p25, "min": float(vals.min()), "max": float(vals.max()),
        "median_ci90": [lo, hi], "bootstrap": boot,
    }


# ----------------------------------------------------------------------------- pure assembly
def _model_three_peer(
    chain_by_slug: Mapping[str, Mapping[str, Any]], overview_payload: Any, markets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """The model's three-peer set rebuilt from this module's payloads (contrast only; the valuation reads comps)."""
    protocols = overview_payload.get("protocols") if isinstance(overview_payload, Mapping) else None
    members: list[dict[str, Any]] = []
    for label, cg_id, chain_slug, parent_id in _MODEL_THREE:
        rev30: float | None = None
        if chain_slug is not None:
            rev30 = _num((chain_by_slug.get(chain_slug) or {}).get("revenue_30d_usd"))
        elif isinstance(protocols, list):
            parts = [
                v for p in protocols
                if isinstance(p, Mapping) and p.get("parentProtocol") == parent_id and (v := _num(p.get("total30d"))) is not None
            ]
            rev30 = sum(parts) if parts else None
        fdv = (markets.get(cg_id) or {}).get("fdv_usd")
        ann = annualize_30d(rev30)
        members.append({"label": label, "coingecko_id": cg_id, "revenue_30d_usd": rev30, "annualized_revenue_usd": ann, "fdv_usd": fdv,
                        "fdv_to_revenue": multiple(fdv, ann)})
    vals = [m["fdv_to_revenue"] for m in members if m["fdv_to_revenue"] is not None]
    return {
        "label": "the three-peer median the model uses (Solana, Ethereum, Hyperliquid), for contrast",
        "members": members,
        "n": len(vals),
        "median_fdv_to_revenue": float(np.median(vals)) if vals else None,
        "basis": "recomputed here from the same DefiLlama overview and CoinGecko call as the wide set (Hyperliquid = sum of the rows "
                 "whose parentProtocol is parent#hyperliquid). The valuation itself reads comps.median_fdv_to_revenue_ex_near, fetched "
                 "seconds apart, and clips it to the floor and cap.",
    }


def _excluded(chain: Mapping[str, Any], code: str, reason: str, cg_id: str | None = None) -> dict[str, Any]:
    return {
        "chain": chain["chain"], "slug": chain["slug"], "rank_by_revenue": chain["rank_by_revenue"],
        "revenue_30d_usd": chain["revenue_30d_usd"], "coingecko_id": cg_id, "reason_code": code, "reason": reason,
    }


def _position_phrase(label: str, value: float, n_at_or_below: int, n: int, dist: Mapping[str, Any]) -> str:
    if n_at_or_below == 0:
        return f"{label} is below all {n} peers (lowest {_x(dist.get('min'))})"
    if n_at_or_below == n:
        return f"{label} is above all {n} peers (highest {_x(dist.get('max'))})"
    return f"{label} sits at the {_pctile(n_at_or_below / n)} of {n} peers ({n_at_or_below} of {n} trade at or below it)"


def build_wide_peers(
    overview_payload: Any,
    markets_payload: Any,
    near_row: Mapping[str, Any] | None = None,
    cap: float | None = None,
    floor: float | None = None,
    *,
    n_target: int = N_PEERS_TARGET,
    warn: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Pure assembly of the wide peer view from the two parsed payloads (no I/O, deterministic).

    ``near_row`` overrides NEAR's inputs (keys ``revenue_30d_usd``, ``fdv_usd``); None, the default and the
    like-for-like choice, reads NEAR's chain row and CoinGecko FDV from the same two payloads as the peers.
    ``cap`` / ``floor`` default to the registry's ``terminal_multiple_cap`` / ``terminal_multiple_floor``.
    Raises ValueError when the overview has no ranked chain rows or no peer qualifies.
    """
    warn = warn or (lambda _msg: None)
    cap = float(assumptions.value("terminal_multiple_cap")) if cap is None else float(cap)
    floor = float(assumptions.value("terminal_multiple_floor")) if floor is None else float(floor)
    chains, malformed = parse_chain_rows(overview_payload)
    if malformed:
        warn(f"wide_peers: {malformed} DefiLlama chain row(s) skipped (missing slug/name or non-numeric total30d)")
    if not chains:
        raise ValueError("DefiLlama fees overview holds no chain row with 30-day revenue above zero")
    markets = parse_market_rows(markets_payload)
    chain_by_slug = {c["slug"]: c for c in chains}

    peers: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    token_owner: dict[str, str] = {}
    n_below_cut = 0
    for chain in chains:
        slug = chain["slug"]
        if slug == SUBJECT_SLUG:
            continue
        if len(peers) >= n_target:
            n_below_cut += 1
            continue

        if slug in NO_TOKEN_REASON_BY_SLUG:
            excluded.append(_excluded(chain, "no_native_token", NO_TOKEN_REASON_BY_SLUG[slug]))
            continue
        cg_id = COINGECKO_ID_BY_SLUG.get(slug)
        if cg_id is None:
            excluded.append(_excluded(chain, "unmapped", "not in the chain-to-token mapping table (wide_peers.COINGECKO_ID_BY_SLUG); not evaluated"))
            warn(f"wide_peers: chain '{slug}' ranks {chain['rank_by_revenue']} by 30-day revenue but has no entry in the mapping table; listed as excluded")
            continue
        if cg_id in token_owner:
            excluded.append(_excluded(chain, "token_already_counted", f"its token ({cg_id}) is already counted through the higher-revenue row '{token_owner[cg_id]}'", cg_id))
            continue
        market = markets.get(cg_id) or {}
        fdv = market.get("fdv_usd")
        if fdv is None:
            excluded.append(_excluded(chain, "no_coingecko_fdv", f"CoinGecko returned no fully diluted valuation for id '{cg_id}' in this call", cg_id))
            warn(f"wide_peers: CoinGecko FDV for '{cg_id}' ({slug}) missing; chain excluded and the next ranked chain takes its place")
            continue
        token_owner[cg_id] = chain["chain"]
        flags: list[str] = []
        if slug in FLAG_BY_SLUG:
            flags.append(FLAG_BY_SLUG[slug])
        if chain["protocol_type"] not in (None, "chain"):
            flags.append(f"DefiLlama types this adapter '{chain['protocol_type']}', not 'chain': its revenue is not plain chain gas revenue")
        ann = annualize_30d(chain["revenue_30d_usd"])
        peers.append({
            "chain": chain["chain"], "slug": slug, "coingecko_id": cg_id, "symbol": market.get("symbol"),
            "rank_by_revenue": chain["rank_by_revenue"],
            "revenue_30d_usd": chain["revenue_30d_usd"], "annualized_revenue_usd": ann, "revenue_1y_usd": chain["revenue_1y_usd"],
            "fdv_usd": fdv, "market_cap_usd": market.get("market_cap_usd"),
            "fdv_to_revenue": multiple(fdv, ann),
            "flags": flags, "revenue_methodology": chain["revenue_methodology"],
        })
    if not peers:
        raise ValueError("no chain qualified as a peer (no mapped token with a CoinGecko FDV)")
    if len(peers) < n_target:
        warn(f"wide_peers: only {len(peers)} of the {n_target} target peers qualified")

    mults = [p["fdv_to_revenue"] for p in peers]
    dist = distribution(mults)
    n = len(mults)

    # NEAR on the same basis ----------------------------------------------------------------------------------
    near_chain = chain_by_slug.get(SUBJECT_SLUG) or {}
    near_market = markets.get(SUBJECT_COINGECKO_ID) or {}
    near_rev30 = _num((near_row or {}).get("revenue_30d_usd")) if near_row is not None else near_chain.get("revenue_30d_usd")
    near_fdv = _num((near_row or {}).get("fdv_usd")) if near_row is not None else near_market.get("fdv_usd")
    near_ann = annualize_30d(near_rev30)
    near_mult = multiple(near_fdv, near_ann)
    if near_mult is None:
        warn("wide_peers: NEAR's chain revenue row or CoinGecko FDV missing; NEAR's position against the wide set is null")
    near = {
        "chain": near_chain.get("chain") or "Near", "slug": SUBJECT_SLUG, "coingecko_id": SUBJECT_COINGECKO_ID,
        "rank_by_revenue": near_chain.get("rank_by_revenue"), "n_chains_ranked": len(chains),
        "revenue_30d_usd": near_rev30, "annualized_revenue_usd": near_ann, "fdv_usd": near_fdv, "fdv_to_revenue": near_mult,
        "percentile": percentile_at_or_below(near_mult, mults),
        "n_peers_at_or_below": sum(1 for v in mults if v <= near_mult) if near_mult is not None else None,
        "revenue_methodology": near_chain.get("revenue_methodology"),
        "basis": "L1-only: NEAR's own chain row in the same DefiLlama overview (gas revenue) over NEAR's FDV from the same CoinGecko call"
                 + (" (inputs overridden by the caller)" if near_row is not None else "")
                 + ". This is not the model's combined L1 + Intents multiple, which is comps.near_combined.fdv_to_revenue.",
    }

    n_cap = sum(1 for v in mults if v <= cap)
    n_floor = sum(1 for v in mults if v <= floor)
    clean = [p["fdv_to_revenue"] for p in peers if not p["flags"]]
    clean_dist = distribution(clean)
    ex_flagged = {
        "label": "sensitivity: the same set without the flagged rows (L2, exchange-linked, non-gas revenue and non-chain adapters)",
        "n_peers": len(clean), "n_flagged_removed": n - len(clean),
        "median": clean_dist["median"], "p25": clean_dist["p25"], "p75": clean_dist["p75"], "min": clean_dist["min"], "max": clean_dist["max"],
        "median_ci90": clean_dist["median_ci90"],
        "cap_percentile": percentile_at_or_below(cap, clean), "n_peers_at_or_below_cap": sum(1 for v in clean if v <= cap),
        "near_percentile": percentile_at_or_below(near_mult, clean),
    }

    ci = dist["median_ci90"] or [None, None]
    headline = (
        f"{_position_phrase(f'The {_x(cap)} terminal multiple cap', cap, n_cap, n, dist)} on FDV to annualised 30-day revenue; "
        f"the wide median is {_x(dist['median'])} (bootstrap 90% interval {_x(ci[0])} to {_x(ci[1])})"
        + (f", and NEAR on L1 gas revenue alone trades at {_x(near_mult)}, the {_pctile(near['percentile'])}." if near_mult is not None
           else "; NEAR's own multiple could not be computed this run.")
    )
    p75 = dist["p75"]
    if p75 is not None and cap <= p75:
        cap_read = (f"The cap is at or below the upper quartile of the set ({_x(p75)}), so the model's terminal value does not rest on a "
                    "multiple richer than what the market pays for chain revenue today")
        if n_cap == 0:
            cap_read += "; it is in fact below every peer, which also shows that chain tokens are not priced on burn revenue alone"
    else:
        cap_read = (f"The cap is above the upper quartile of the set ({_x(p75)}): against this evidence it is an aggressive multiple, "
                    "which cuts against the base case")
    if near_mult is None or dist["median"] is None:
        near_read = "NEAR's own position is not available"
    elif near_mult > dist["median"]:
        near_read = (f"On L1 gas revenue alone NEAR ({_x(near_mult)}) is priced above the wide median ({_x(dist['median'])}), so NEAR is not cheap on "
                     "chain revenue; the long-term case has to be carried by Intents revenue, not by the L1 multiple")
    else:
        near_read = (f"On L1 gas revenue alone NEAR ({_x(near_mult)}) is priced at or below the wide median ({_x(dist['median'])}), before counting "
                     "any Intents revenue")
    reading = (
        f"{cap_read}. {near_read}. This reading is overturned if a re-run puts the cap above the 75th percentile of the set "
        f"(peer multiples compressing toward {_x(cap)}) or if the set shrinks below {MIN_PEERS_FOR_CLAIM} peers."
    )

    return {
        "status": "ok",
        "basis": "FDV (CoinGecko fully_diluted_valuation) / annualised chain revenue (DefiLlama overview, dataType=dailyRevenue, total30d x 365/30)",
        "annualization": "annualized_revenue_usd = revenue_30d_usd x 365 / 30 (30-day run-rate, the same convention as comps)",
        "n_peers": n,
        "n_peers_target": n_target,
        "n_chains_ranked": len(chains),
        "n_chains_below_cut": n_below_cut,
        "peers": peers,
        "distribution": dist,
        "near": near,
        "terminal_multiple_cap": cap,
        "cap_percentile": n_cap / n,
        "n_peers_at_or_below_cap": n_cap,
        "terminal_multiple_floor": floor,
        "floor_percentile": n_floor / n,
        "n_peers_at_or_below_floor": n_floor,
        "percentile_definition": "share of peers with FDV/revenue at or below the value",
        "model_three_peer": _model_three_peer(chain_by_slug, overview_payload, markets),
        "ex_flagged": ex_flagged,
        "headline": headline,
        "reading": reading,
        "inclusion_rules": list(INCLUSION_RULES),
        "excluded": excluded,
        "caveats": list(CAVEATS),
    }


# ----------------------------------------------------------------------------- live collection
def _registry_bounds(args: Any) -> tuple[float, float, str]:
    """(cap, floor, source) from the registry the run uses (``assumptions.preset(args.preset)``), else the defaults."""
    preset = getattr(args, "preset", None)
    if isinstance(preset, str) and preset:
        try:
            registry = assumptions.preset(preset)
            return (float(assumptions.value("terminal_multiple_cap", registry)), float(assumptions.value("terminal_multiple_floor", registry)),
                    f"assumptions registry, preset '{preset}'")
        except KeyError:
            pass
    return (float(assumptions.value("terminal_multiple_cap")), float(assumptions.value("terminal_multiple_floor")),
            "assumptions registry defaults")


async def collect_wide_peers(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, args: Any, log: Callable[[str], None] | None = None,
    events: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """EXTRA_COLLECTORS entry: one DefiLlama overview call, one batched CoinGecko call, then ``build_wide_peers``.

    Returns None (with a ledger warning) when either payload is unavailable or no peer qualifies; never raises
    for a data fault. ``events`` is unused: neither call touches the quote venues or NearBlocks.
    """
    fetched_at = utc_now_iso()
    overview, rec_o = await fetch_json(
        client, ledger, source=OVERVIEW_RECORD[0], name=OVERVIEW_RECORD[1], method="GET",
        url=f"{config.DEFILLAMA_API_BASE}/overview/fees", params=OVERVIEW_PARAMS,
        timeout=max(config.HTTP_TIMEOUT_S, 45.0), retries=2,
    )
    if not rec_o.ok or not isinstance(overview, Mapping):
        ledger.warn(f"wide_peers: DefiLlama fees overview unavailable ({rec_o.error or 'HTTP ' + str(rec_o.http_status)}); snapshot.wide_peers is null")
        return None
    ids = sorted({*COINGECKO_ID_BY_SLUG.values(), SUBJECT_COINGECKO_ID, *(m[1] for m in _MODEL_THREE)})
    markets, rec_m = await fetch_json(
        client, ledger, source=MARKETS_RECORD[0], name=MARKETS_RECORD[1], method="GET",
        url=f"{config.COINGECKO_API_BASE}/coins/markets",
        params={"vs_currency": "usd", "ids": ",".join(ids), "per_page": 250, "page": 1},
        retries=_COINGECKO_RETRIES, backoff=_COINGECKO_BACKOFF_S, transport_retries=1,
        retry_after_cap_s=_COINGECKO_RETRY_AFTER_CAP_S, retry_once_on=frozenset({403}),
    )
    if not rec_m.ok or not isinstance(markets, list) or not markets:
        ledger.warn(
            f"wide_peers: CoinGecko /coins/markets (wide set) failed after {rec_m.attempts} attempt(s) "
            f"({rec_m.error or 'HTTP ' + str(rec_m.http_status)}); snapshot.wide_peers is null"
        )
        return None
    cap, floor, cap_source = _registry_bounds(args)
    try:
        out = build_wide_peers(overview, markets, None, cap, floor, warn=ledger.warn)
    except ValueError as exc:
        ledger.warn(f"wide_peers: {exc}; snapshot.wide_peers is null")
        return None
    out["cap_source"] = cap_source
    out["fetched_at_utc"] = fetched_at
    out["sources"] = {
        "revenue": {"source": rec_o.source, "name": rec_o.name, "url": rec_o.url, "sha256": rec_o.sha256, "raw_path": rec_o.raw_path,
                    "fetched_at_utc": rec_o.fetched_at_utc},
        "fdv": {"source": rec_m.source, "name": rec_m.name, "url": rec_m.url, "sha256": rec_m.sha256, "raw_path": rec_m.raw_path,
                "fetched_at_utc": rec_m.fetched_at_utc, "attempts": rec_m.attempts},
    }
    if log is not None:
        d = out["distribution"]
        log(f"wide_peers: {out['n_peers']} peers, median FDV/revenue {_x(d['median'])}, cap at the {_pctile(out['cap_percentile'])}, "
            f"{len(out['excluded'])} excluded")
    return out


# ----------------------------------------------------------------------------- scorecard + memo
def scorecard_claim(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Graded claim for the evidence scorecard (fields claim/status/value/source/confidence/note); None without data.

    DERIVED when the cap is at or below the 75th percentile of the wide set and the set has at least
    ``MIN_PEERS_FOR_CLAIM`` peers; NOT_SUPPORTED otherwise (cap above the upper quartile, or too few peers).
    """
    if not isinstance(data, Mapping):
        return None
    dist = data.get("distribution") or {}
    cap, p75, n = _num(data.get("terminal_multiple_cap")), _num(dist.get("p75")), int(_num(data.get("n_peers")) or 0)
    if cap is None or p75 is None or n == 0:
        return None
    n_cap = int(_num(data.get("n_peers_at_or_below_cap")) or 0)
    enough = n >= MIN_PEERS_FOR_CLAIM
    ok = enough and cap <= p75
    ci = dist.get("median_ci90") or [None, None]
    near = data.get("near") or {}
    exf = data.get("ex_flagged") or {}
    value = (
        f"cap {_x(cap)} vs {n} chain tokens: {n_cap} of {n} trade at or below it ({_pctile(data.get('cap_percentile'))}); "
        f"P25 {_x(dist.get('p25'))}, median {_x(dist.get('median'))} [bootstrap 90% {_x(ci[0])} to {_x(ci[1])}], P75 {_x(p75)}, "
        f"range {_x(dist.get('min'))} to {_x(dist.get('max'))}; NEAR L1-only {_x(near.get('fdv_to_revenue'))} ({_pctile(near.get('percentile'))}); "
        f"without flagged rows: median {_x(exf.get('median'))}, n {exf.get('n_peers')}"
    )
    if not enough:
        position = f"only {n} peers qualified (minimum {MIN_PEERS_FOR_CLAIM}), so the claim is not graded as supported"
    elif n_cap == 0:
        position = ("the cap is BELOW the whole observed range, not inside it: the claim holds only in the weaker sense that the cap is "
                    "not above what peers trade at")
    elif ok:
        position = "the cap is inside the observed range and at or below its upper quartile"
    else:
        position = "the cap is above the upper quartile of the observed range"
    src = data.get("sources") or {}
    sha_r, sha_f = (src.get("revenue") or {}).get("sha256"), (src.get("fdv") or {}).get("sha256")
    source = ("defillama/overview:fees:dailyRevenue" + (f" sha256 {str(sha_r)[:12]}..." if sha_r else "")
              + " + coingecko/coins_markets_wide" + (f" sha256 {str(sha_f)[:12]}..." if sha_f else ""))
    return {
        "claim": "The model's terminal multiple cap sits inside the observed peer range of FDV/revenue",
        "status": "DERIVED" if ok else "NOT_SUPPORTED",
        "value": value,
        "source": source,
        "confidence": "medium" if ok else "low",
        "note": f"Rule: DERIVED when the cap is at or below the 75th percentile of the wide set and n_peers >= {MIN_PEERS_FOR_CLAIM}. Here {position}. "
                "FDV/revenue on 30 days annualised, one snapshot; revenue definitions differ by chain adapter; peers ranked by revenue and "
                "fixed before any multiple was computed (inclusion_rules, excluded).",
    }


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], align: Sequence[str]) -> str:
    """GitHub-flavoured Markdown table in the memo's style ('l' / 'r' per column, trailing blank line)."""
    sep = ["---:" if a == "r" else ":---" for a in align]
    lines = ["| " + " | ".join(str(h) for h in headers) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    lines.append("")
    return "\n".join(lines)


def memo_markdown(data: Mapping[str, Any], snap_dict: Mapping[str, Any] | None = None) -> str:
    """Memo sub-section: headline, reading, peer table sorted by FDV/revenue with NEAR and the cap marked in place,
    distribution line, inclusion rules, excluded list, caveats. ``snap_dict`` supplies the model's own combined
    NEAR multiple and three-peer median (``comps``) when present.
    """
    dist = data.get("distribution") or {}
    near = data.get("near") or {}
    cap, floor = _num(data.get("terminal_multiple_cap")), _num(data.get("terminal_multiple_floor"))
    comps = (snap_dict or {}).get("comps") or {}
    combined = _num((comps.get("near_combined") or {}).get("fdv_to_revenue"))
    model_median = _num(comps.get("median_fdv_to_revenue_ex_near"))
    peers = [p for p in data.get("peers") or [] if _num(p.get("fdv_to_revenue")) is not None]
    mults = [float(p["fdv_to_revenue"]) for p in peers]

    # (sort key, tie order, cells) so the reference rows land in place among the peers
    marked: list[tuple[float, int, list[str]]] = []
    for p in peers:
        flag = "; ".join(p.get("flags") or [])
        marked.append((float(p["fdv_to_revenue"]), 1, [
            str(p.get("chain")), str(p.get("symbol") or p.get("coingecko_id") or ""), _usd(p.get("revenue_30d_usd")),
            _usd(p.get("annualized_revenue_usd")), _usd(p.get("fdv_usd")), _x(p.get("fdv_to_revenue")), flag or "",
        ]))
    if floor is not None:
        marked.append((floor, 0, ["**Model floor**", "", "", "", "", f"**{_x(floor)}**", "terminal_multiple_floor (assumption)"]))
    if cap is not None:
        marked.append((cap, 0, ["**Model cap**", "", "", "", "", f"**{_x(cap)}**", "terminal_multiple_cap (assumption); the multiple the model uses"]))
    if _num(near.get("fdv_to_revenue")) is not None:
        marked.append((float(near["fdv_to_revenue"]), 2, [
            "**NEAR (L1 gas revenue only)**", "NEAR", _usd(near.get("revenue_30d_usd")), _usd(near.get("annualized_revenue_usd")),
            _usd(near.get("fdv_usd")), f"**{_x(near.get('fdv_to_revenue'))}**", "subject, not counted in the set",
        ]))
    if combined is not None:
        nc = comps.get("near_combined") or {}
        marked.append((combined, 2, [
            "**NEAR (L1 + Intents, the model's basis)**", "NEAR", _usd(nc.get("revenue_30d_usd")), _usd(nc.get("annualized_revenue_usd")),
            _usd(nc.get("fdv_usd")), f"**{_x(combined)}**", "comps.near_combined; not like for like (no peer row includes app revenue)",
        ]))
    marked.sort(key=lambda t: (t[0], t[1]))
    table = _md_table(
        ["Chain", "Token", "Revenue, 30d", "Revenue, annualised", "FDV", "FDV / revenue", "Note"],
        [cells for _k, _o, cells in marked], ["l", "l", "r", "r", "r", "r", "l"],
    )

    ci = dist.get("median_ci90") or [None, None]
    boot = dist.get("bootstrap") or {}
    exf = data.get("ex_flagged") or {}
    three = data.get("model_three_peer") or {}
    dist_line = (
        f"Distribution of FDV / revenue across {data.get('n_peers')} peers: median {_x(dist.get('median'))} "
        f"(bootstrap 90% interval {_x(ci[0])} to {_x(ci[1])}; {boot.get('n_resamples', BOOTSTRAP_RESAMPLES):,} resamples, seed {boot.get('seed', BOOTSTRAP_SEED)}), "
        f"P25 {_x(dist.get('p25'))}, P75 {_x(dist.get('p75'))}, IQR {_x(dist.get('iqr'))}, range {_x(dist.get('min'))} to {_x(dist.get('max'))}. "
        f"The {_x(cap)} cap: {data.get('n_peers_at_or_below_cap')} of {data.get('n_peers')} peers at or below it ({_pctile(data.get('cap_percentile'))}). "
        f"The {_x(floor)} floor: {data.get('n_peers_at_or_below_floor')} of {data.get('n_peers')} ({_pctile(data.get('floor_percentile'))}). "
        f"NEAR on L1 gas revenue only: {_x(near.get('fdv_to_revenue'))}, the {_pctile(near.get('percentile'))}"
        + (f"; on the model's combined L1 + Intents basis {_x(combined)}, which would be the {_pctile(percentile_at_or_below(combined, mults))} "
           "(not like for like)." if combined is not None else ".")
    )
    contrast = (
        f"Without the {exf.get('n_flagged_removed')} flagged rows ({exf.get('n_peers')} peers): median {_x(exf.get('median'))}, "
        f"P25 {_x(exf.get('p25'))}, P75 {_x(exf.get('p75'))}; {exf.get('n_peers_at_or_below_cap')} at or below the cap. "
        f"For contrast, the three-peer median the model uses (Solana, Ethereum, Hyperliquid) is "
        + (f"{_x(model_median)} (comps.median_fdv_to_revenue_ex_near)" if model_median is not None
           else f"{_x(three.get('median_fdv_to_revenue'))} (recomputed from this view's payloads)")
        + f", which the model clips to the {_x(cap)} cap."
    )
    excluded = data.get("excluded") or []
    excl_lines = [
        f"- {e.get('chain')} (rank {e.get('rank_by_revenue')} by revenue, {_usd(e.get('revenue_30d_usd'))} in 30 days): {e.get('reason')}." for e in excluded
    ] or ["- none inside the cut."]
    src = data.get("sources") or {}
    rev_src, fdv_src = src.get("revenue") or {}, src.get("fdv") or {}
    parts = [
        f"**{data.get('headline')}**",
        "",
        str(data.get("reading") or ""),
        "",
        table,
        dist_line,
        "",
        contrast,
        "",
        "Inclusion rules (fixed before any multiple was computed):",
        "\n".join(f"- {r}" for r in data.get("inclusion_rules") or []),
        "",
        f"Excluded inside the cut ({len(excluded)}); {data.get('n_chains_below_cut')} further chains rank below the last peer and were not evaluated:",
        "\n".join(excl_lines),
        "",
        "Caveats:",
        "\n".join(f"- {c}" for c in data.get("caveats") or []),
        "",
        f"Sources: `{rev_src.get('source')}/{rev_src.get('name')}` sha256 `{str(rev_src.get('sha256') or 'n/a')[:16]}`, "
        f"`{fdv_src.get('source')}/{fdv_src.get('name')}` sha256 `{str(fdv_src.get('sha256') or 'n/a')[:16]}`; "
        f"fetched {data.get('fetched_at_utc') or 'n/a'}. Field: `snapshot.wide_peers`.",
    ]
    return "\n".join(parts)
