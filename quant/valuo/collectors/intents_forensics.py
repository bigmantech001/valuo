"""intents.near forensics: volume split, fee capture, price/volume volatility and caller concentration.

Sources (docs/LIVE_ENDPOINT_FACTS.md sections 4-6), all key-free:

- nearstats ``/summary``: public vs confidential volume split, records, week-over-week days,
  protocol metrics (cumulative fees, confidential TVL and its verification flag, 7d unique users),
  CoinGecko-sourced price facts, the ten largest recent swaps.
- nearstats ``/price-history?window=1y``: daily closes -> log returns -> realized volatility.
- DefiLlama ``summary/fees/near-intents`` (gross fees), ``?dataType=dailyRevenue`` (NEAR's captured
  revenue swept to revenue wallets, i.e. the buyback-directed flow), ``?dataType=dailyHoldersRevenue``,
  and ``summary/dexs/near-intents`` (volume). Take rates are computed over ONE calendar window: the last
  30 complete UTC days present in all of the daily charts (DefiLlama's ``total30d`` fields are not
  aligned across adapters: the fees total can include a partial current day the dexs chart lacks, and
  the dexs ``total30d`` has been observed to be a 29-day sum). The raw ``total30d`` values are kept as
  cross-checks.
- NearBlocks ``/account/intents.near/txns`` pages (cursor pagination, spaced) for the caller audit and
  the solver audit, ``/txns/count`` for lifetime receipts, ``/stats`` for the NearBlocks supply figures.
- coins.llama.fi ``/chart/coingecko:near?span=365&period=1d`` is the key-free fallback price series when
  nearstats' price history is unavailable (same log-return sigma method).

Formulas
--------
- gross_take_bps = sum(fees over window) / sum(volume over window) * 1e4; net likewise with revenue;
  capture_ratio = sum(revenue) / sum(fees); window = last 30 common complete UTC days.
- Volatility: r_t = ln(x_t / x_{t-1}); sigma_daily = sample std (ddof=1); sigma_annual = sigma_daily * sqrt(365)
  (crypto trades every calendar day; the price series spacing is measured, not assumed).
- Volume monthly sigma: 30-day rolling sums S_k anchored at the latest day and stepped back 30 days at a
  time (non-overlapping), r_k = ln(S_k / S_{k+1}), sigma = sample std of r_k. The returns themselves and
  the sigma excluding the three earliest returns are published so the SOTP can show how much of the
  dispersion comes from the oldest window.
- Deposit-source concentration over EXTERNAL predecessors (excluding ``system`` and ``intents.near``):
  s_i = receipts_i / sum receipts; HHI = sum (100 * s_i)^2 in (0, 10000]; N_eff = 10000 / HHI.
  ``hhi_all`` repeats the sum over every predecessor including system refunds and self receipts.
  This is NOT solver concentration: ``execute_intents`` fills are submitted by the intents.near relayer
  (predecessor == intents.near), so the external population is bridge token-contract deposit callbacks
  plus direct callers such as escrow.ai.near.
- Solver concentration: every ``execute_intents`` receipt (any predecessor) is decoded
  (``args.signed[].payload.message``, NEP-413 JSON) into signer payloads. A fill is a receipt with at
  least two signers carrying ``token_diff`` legs. The solver side is the signer whose payload is a pure
  ``token_diff`` while the counterparty bundles a withdrawal (``transfer`` / ``ft_withdraw`` /
  ``mt_withdraw``), or whose account name says so (``*solver*``, ``*-liq*``, market maker), or the named
  account when the counterparty is an implicit 64-hex 1Click deposit address. HHI_solver is over fills
  per solver account. Receipts whose signers only ``transfer`` (solver inventory moves) are not fills.

Nothing is invented: a value that cannot be fetched is ``None`` and a warning is recorded both on the
ledger and in the model's ``warnings`` extra. The collector raises ``IntentsForensicsError`` only when
the schema cannot hold the result (no receipts sampled -> HHI undefined; no 30d volume from any source).
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timezone
from statistics import NormalDist
from typing import Any

import httpx
import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationError

from valuo import assumptions as A
from valuo import config
from valuo.collectors.confidential_boundary import collect_confidential_boundary
from valuo.provenance import ProvenanceLedger, fetch_json, utc_now_iso
from valuo.schemas import CallerClass, CallerShare, IntentsForensics

__all__ = [
    "IntentsForensicsError",
    "SELF_ACCOUNT",
    "DEFILLAMA_SLUG",
    "TAKE_RATE_WINDOW_DAYS",
    "NEARBLOCKS_TRANSPORT_BACKOFF_S",
    "collect_intents_forensics",
    "collect_intents_forensics_async",
    "classify_account",
    "classify_caller",
    "hhi_from_counts",
    "caller_concentration",
    "decode_nested_json",
    "parse_execute_intents",
    "classify_fill_signers",
    "solver_concentration",
    "bootstrap_hhi_ci",
    "detect_settlement_hub",
    "confidential_split_guard",
    "SPLIT_STATUS_MEASURED",
    "SPLIT_STATUS_IMPLAUSIBLE",
    "SPLIT_STATUS_UNAVAILABLE",
    "SOLVER_AUDIT_PAGES",
    "SOLVER_SAMPLE_TARGET_SPAN_S",
    "plan_stratum_offsets",
    "estimate_id_rate",
    "cursor_for_offset",
    "SOLVER_AUDIT_PER_PAGE",
    "SOLVER_MIN_PARTICIPATIONS",
    "BOOTSTRAP_DRAWS",
    "BOOTSTRAP_SEED",
    "price_volatility",
    "volume_volatility",
    "fee_metrics",
    "align_daily_series",
    "aligned_window_sums",
    "extract_volume",
    "extract_price",
    "extract_protocol_metrics",
    "extract_top_swaps",
]

SELF_ACCOUNT = "intents.near"
DEFILLAMA_SLUG = "near-intents"
EXPLORER_BASE = "https://nearblocks.io"
TAKE_RATE_WINDOW_DAYS = 30
# NearBlocks answers an exhausted unauthenticated quota with HTTP 429 and no Retry-After, and the window resets within
# about a minute. provenance.fetch_json waits backoff x 2**attempt between tries, so 4 retries at 3 s give
# 3 + 6 + 12 + 24 = 45 s of patience before a page is declared failed. That ladder is only for HTTP 429/5xx: a
# refused connection or a hang is retried once after a flat 2 s and the rest of the NearBlocks chain is skipped
# (``_fetch_nearblocks`` marks the host unavailable), so an unreachable host costs seconds, not minutes.
NEARBLOCKS_RETRIES = 4
NEARBLOCKS_BACKOFF_S = 3.0
NEARBLOCKS_TRANSPORT_RETRIES = 1
NEARBLOCKS_TRANSPORT_BACKOFF_S = 2.0
_NEARBLOCKS_RETRY_KW: dict[str, Any] = {
    "retries": NEARBLOCKS_RETRIES, "backoff": NEARBLOCKS_BACKOFF_S,
    "transport_retries": NEARBLOCKS_TRANSPORT_RETRIES, "transport_backoff": NEARBLOCKS_TRANSPORT_BACKOFF_S,
}
DAYS_PER_YEAR = 365.0
_MS_PER_DAY = 86_400_000.0
_YOCTO = 10**24
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_EVM_IMPLICIT = re.compile(r"^0x[0-9a-f]{40}$")
_BRIDGE_SUFFIXES = (".omft.near", ".omni.hot.tg")
_BRIDGE_EXACT = frozenset({"omni.bridge.near"})
_AI_SUFFIXES = (".ai.near", ".agent.near")
_TOKEN_CONTRACT_METHODS = frozenset({"ft_on_transfer", "mt_on_transfer", "nft_on_transfer"})
# Solver-side heuristics for execute_intents fills (see module docstring). Names are a weak signal and are
# only consulted when the payload structure (pure token_diff vs bundled withdrawal) does not decide.
_SOLVER_NAME = re.compile(r"solver|market|maker|-liq|liquidity|\bmm\b", re.I)
_WITHDRAWAL_INTENTS = frozenset({"transfer", "ft_withdraw", "mt_withdraw", "nft_withdraw", "native_withdraw", "storage_deposit"})
_EXECUTE_INTENTS = "execute_intents"
# Solver audit sample: besides the generic caller pages, the collector reads NearBlocks' method-filtered receipt list
# (``?method=execute_intents``), which returns only fills/settlements. 50 rows per page is accepted unauthenticated
# (100 answered HTTP 520 on 2026-11-08). One page covers ~45 s of settlement, so 4 consecutive pages spanned ~3 minutes
# and could never reach solver_sample_min_span_s. The sample is therefore STRATIFIED IN TIME: page 1 is the newest page
# (page=1); the other pages are reached by jumping the id cursor (NearBlocks' cursor is a receipt id and the list returns
# rows with id < cursor; a synthetic cursor is accepted, verified live 2026-11-08) to even time offsets back to
# SOLVER_SAMPLE_TARGET_SPAN_S. page=N without a cursor is not usable for depth (page 2 answered HTTP 520 after 50 s).
# Page count and target depth are registry assumptions (solver_sample_pages, solver_sample_target_span_s);
# VALUO_NEARBLOCKS_SOLVER_PAGES overrides the page count (0 disables the method-filtered walk).
SOLVER_AUDIT_PAGES = max(0, int(os.environ.get("VALUO_NEARBLOCKS_SOLVER_PAGES", "") or A.value("solver_sample_pages")))
SOLVER_SAMPLE_TARGET_SPAN_S = A.value("solver_sample_target_span_s")
SAMPLE_DESIGN_STRATIFIED = "stratified_time_sample"
SAMPLE_DESIGN_CONTIGUOUS = "contiguous_cursor_walk"
SOLVER_AUDIT_PER_PAGE = 50
NEARBLOCKS_FREE_CALLS_PER_WINDOW = 10
NEARBLOCKS_RATE_WINDOW_S = 62.0
# The stratified solver walk runs in chunks of at most this many calls, each chunk starting a full rate window after the
# previous NearBlocks call. Measured 2026-11-08: 6 caller-walk calls, a 57 s wait, then 5 solver calls were served and the
# 6th answered HTTP 429 through the whole 45 s retry ladder, so the safe unauthenticated burst is 5, not 10.
NEARBLOCKS_SOLVER_CALLS_PER_CHUNK = 5
# Below this many fill participations HHI_solver is "thin": one solver taking four fills crosses 3,500 by chance.
# Kept equal to bear_case.MIN_SOLVER_FILLS_FOR_TRIGGER.
SOLVER_MIN_PARTICIPATIONS = 10
# Hub detection (detect_settlement_hub) and the hub-leg solver rule.
HUB_MIN_COUNTERPARTIES = 10
HUB_DOMINANCE_RATIO = 2.0
HUB_SOLVER_MIN_LEGS = 2
# Bootstrap CI for HHI: 2,000 draws, numpy default_rng([20261114, stream]) with one stream per statistic.
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 20261114
BOOTSTRAP_STREAM_SOLVER = 1
BOOTSTRAP_STREAM_EXTERNAL = 2
BOOTSTRAP_STREAM_EXTERNAL_EX_AI = 3
BOOTSTRAP_STREAM_SOLVER_UNIT = 4  # unit-level solver bootstrap kept for comparison with the page-block bootstrap
# confidential_split_guard outcomes (intents_forensics.volume.confidential_share_status).
SPLIT_STATUS_MEASURED = "measured"
SPLIT_STATUS_IMPLAUSIBLE = "implausible_fallback"
SPLIT_STATUS_UNAVAILABLE = "unavailable"


class IntentsForensicsError(RuntimeError):
    """Raised when the result cannot be represented truthfully (no receipts, or no 30d volume at all)."""


# ----------------------------------------------------------------------------- lenient payload shapes
class _TxnRow(BaseModel):
    """The NearBlocks receipt fields the audit reads; unknown fields are ignored, missing ones are None."""

    model_config = ConfigDict(extra="ignore")

    predecessor_account_id: str
    receiver_account_id: str | None = None
    receipt_id: str | None = None
    id: str | None = None
    transaction_hash: str | None = None
    receipt_block: dict[str, Any] | None = None
    block: dict[str, Any] | None = None
    actions: list[dict[str, Any]] | None = None
    receipt_outcome: dict[str, Any] | None = None
    # Added by the collector (never by NearBlocks): the solver-sample page the row came from, e.g. "p3".
    valuo_stratum: str | None = None


class _PricePoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    t: float
    c: float


class _LlamaSummary(BaseModel):
    """Totals and the daily chart of a DefiLlama fees/dexs summary (numbers may arrive as int or float)."""

    model_config = ConfigDict(extra="ignore")

    total24h: float | None = None
    total7d: float | None = None
    total30d: float | None = None
    total1y: float | None = None
    totalAllTime: float | None = None
    totalDataChart: list[list[Any]] | None = None
    methodology: dict[str, Any] | None = None


# ----------------------------------------------------------------------------- small helpers
def _num(value: Any) -> float | None:
    """float(value) when it is a finite number or numeric string, else None (bools are not numbers)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _get(obj: Any, *path: str) -> Any:
    """Nested dict lookup returning None on any miss or non-dict intermediate."""
    cur = obj
    for key in path:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(key)
    return cur


def _yocto_to_near(value: Any) -> float | None:
    """yoctoNEAR integer string -> NEAR (10^24 yocto per NEAR)."""
    raw = _int(value)
    return None if raw is None else raw / _YOCTO


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _bps(numerator: float | None, denominator: float | None) -> float | None:
    r = _ratio(numerator, denominator)
    return None if r is None else r * 1e4


def _sample_std(xs: Sequence[float]) -> float | None:
    """Sample standard deviation (ddof=1); None below two observations."""
    n = len(xs)
    if n < 2:
        return None
    mean = sum(xs) / n
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1))


def _log_returns(values: Sequence[float]) -> list[float]:
    """ln(x_t / x_{t-1}) over consecutive strictly positive values; non-positive pairs are skipped."""
    out: list[float] = []
    for prev, cur in zip(values, values[1:], strict=False):  # offset pairing: lengths differ by one on purpose
        if prev > 0 and cur > 0:
            out.append(math.log(cur / prev))
    return out


def _ns_to_iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _ms_to_iso(ms: float) -> str:
    return datetime.fromtimestamp(ms / 1e3, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _chart_points(chart: Any) -> list[tuple[int, float]]:
    """DefiLlama ``totalDataChart`` [[unix_s, usd], ...] -> sorted numeric pairs, malformed rows dropped."""
    points: list[tuple[int, float]] = []
    if not isinstance(chart, list):
        return points
    for row in chart:
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            ts, val = _int(row[0]), _num(row[1])
            if ts is not None and val is not None:
                points.append((ts, val))
    points.sort(key=lambda p: p[0])
    return points


# ----------------------------------------------------------------------------- caller classification
def classify_account(account_id: str, self_account: str = SELF_ACCOUNT) -> CallerClass:
    """Name-only classification of a predecessor account (FACTS section 5 rules).

    system -> system; the clearinghouse itself -> self_internal; ``*.omft.near`` / ``*.omni.hot.tg`` /
    ``omni.bridge.near`` -> bridge_relayer; ``*.ai.near`` / ``*.agent.near`` -> ai_agent; 64-hex or
    ``0x``+40-hex implicit accounts -> implicit_account; anything else -> named_account.
    """
    acct = account_id.strip()
    lowered = acct.lower()
    if lowered == "system":
        return CallerClass.system
    if lowered == self_account:
        return CallerClass.self_internal
    if lowered in _BRIDGE_EXACT or lowered.endswith(_BRIDGE_SUFFIXES):
        return CallerClass.bridge_relayer
    if lowered.endswith(_AI_SUFFIXES):
        return CallerClass.ai_agent
    if _HEX64.match(lowered) or _EVM_IMPLICIT.match(lowered):
        return CallerClass.implicit_account
    return CallerClass.named_account


def classify_caller(account_id: str, methods: Iterable[str | None] = (), self_account: str = SELF_ACCOUNT) -> CallerClass:
    """Method-aware classification.

    NEP-141 ``ft_transfer_call`` makes the *token contract* call ``ft_on_transfer`` on the receiver, so a
    predecessor whose receipt is ``ft_on_transfer`` is a token contract depositing assets (bridged omft
    assets or a NEAR-native FT such as the 64-hex USDC contract), not a user wallet. Such implicit/named
    predecessors are therefore reported as ``bridge_relayer`` (token-contract inflow). Every other case
    falls back to ``classify_account``.
    """
    base = classify_account(account_id, self_account)
    if base in (CallerClass.implicit_account, CallerClass.named_account):
        if any(m in _TOKEN_CONTRACT_METHODS for m in methods if isinstance(m, str)):
            return CallerClass.bridge_relayer
    return base


def hhi_from_counts(counts: Mapping[str, int]) -> tuple[float | None, dict[str, float]]:
    """(HHI, shares) for a receipts-per-account mapping; HHI = sum (100 * s_i)^2, None for an empty map."""
    total = sum(v for v in counts.values() if v > 0)
    if total <= 0:
        return None, {}
    shares = {k: v / total for k, v in counts.items() if v > 0}
    return sum((100.0 * s) ** 2 for s in shares.values()), shares


def _row_methods(row: _TxnRow) -> list[str]:
    """Action labels of a receipt: the function-call method, else the action kind (e.g. TRANSFER)."""
    labels: list[str] = []
    for action in row.actions or []:
        if not isinstance(action, Mapping):
            continue
        method = action.get("method")
        kind = action.get("action")
        if isinstance(method, str) and method:
            labels.append(method)
        elif isinstance(kind, str) and kind:
            labels.append(kind)
    return labels


def _row_height(row: _TxnRow) -> int | None:
    return _int(_get(row.receipt_block, "block_height")) or _int(_get(row.block, "block_height"))


def _parse_rows(txns: Iterable[Any], warnings: list[str]) -> list[_TxnRow]:
    """Validate NearBlocks rows and de-duplicate by receipt id across pages (cursor pages can overlap)."""
    rows: list[_TxnRow] = []
    seen: set[str] = set()
    bad = dupes = 0
    for raw in txns:
        try:
            row = _TxnRow.model_validate(raw)
        except ValidationError:
            bad += 1
            continue
        key = row.receipt_id or row.id or f"{row.transaction_hash}:{row.predecessor_account_id}:{_row_height(row)}"
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        rows.append(row)
    if bad:
        warnings.append(f"nearblocks: {bad} receipt row(s) failed shape validation and were skipped")
    if dupes:
        # NearBlocks cursors are id-based while rows are block-time ordered and ids are not monotonic in
        # time, so consecutive cursor pages legitimately overlap by a few receipts; each is counted once.
        warnings.append(
            f"nearblocks: {dupes} duplicate receipt(s) seen on overlapping pages were counted once "
            f"(id-based cursor vs time-ordered rows); unique receipts sampled = {len(rows)}"
        )
    return rows


def caller_concentration(txns: Iterable[Any], self_account: str = SELF_ACCOUNT, warnings: list[str] | None = None) -> dict[str, Any]:
    """Caller shares, HHI/N_eff over external callers, HHI over all predecessors, class shares, method mix.

    External = predecessor not in {system, self_account}. Each NearBlocks row is one receipt; the per-page
    endpoint only returns receipts where intents.near is predecessor or receiver, so an external
    predecessor is by construction a caller *into* the clearinghouse.
    """
    warnings = warnings if warnings is not None else []
    rows = _parse_rows(txns, warnings)
    all_counts: Counter[str] = Counter()
    ext_counts: Counter[str] = Counter()
    ext_methods: dict[str, list[str]] = {}
    example_tx: dict[str, str] = {}
    method_mix: Counter[str] = Counter()
    heights: list[int] = []
    timestamps: list[int] = []
    for row in rows:
        acct = row.predecessor_account_id
        methods = _row_methods(row)
        all_counts[acct] += 1
        method_mix.update(methods or ["<no action>"])
        height = _row_height(row)
        if height is not None:
            heights.append(height)
        ts = _int(_get(row.receipt_block, "block_timestamp"))
        if ts is not None:
            timestamps.append(ts)
        if classify_account(acct, self_account) in (CallerClass.system, CallerClass.self_internal):
            continue
        ext_counts[acct] += 1
        ext_methods.setdefault(acct, []).extend(methods)
        if row.transaction_hash and acct not in example_tx:
            example_tx[acct] = row.transaction_hash

    hhi_ext, shares = hhi_from_counts(ext_counts)
    hhi_all, _ = hhi_from_counts(all_counts)
    # execute_intents by predecessor: shows that the fills themselves are relayer self-receipts, which is
    # why the external HHI measures deposit sources, not solvers.
    exec_by_pred: Counter[str] = Counter()
    for row in rows:
        if _EXECUTE_INTENTS in _row_methods(row):
            exec_by_pred[classify_account(row.predecessor_account_id, self_account).value] += 1
    callers = [
        CallerShare(
            account_id=acct,
            cls=classify_caller(acct, ext_methods.get(acct, ()), self_account),
            receipts=ext_counts[acct],
            share=shares[acct],
            example_tx_hash=example_tx.get(acct),
        )
        for acct in sorted(ext_counts, key=lambda a: (-ext_counts[a], a))
    ]
    class_share: dict[str, float] = {}
    class_counts: dict[str, int] = {}
    for c in callers:
        class_share[c.cls.value] = class_share.get(c.cls.value, 0.0) + c.share
        class_counts[c.cls.value] = class_counts.get(c.cls.value, 0) + c.receipts
    class_counts["system"] = sum(v for a, v in all_counts.items() if classify_account(a, self_account) is CallerClass.system)
    class_counts["self_internal"] = sum(v for a, v in all_counts.items() if classify_account(a, self_account) is CallerClass.self_internal)
    # AI escrow callers can dominate a 100-receipt window; the "solver cartelization" bear trigger needs the
    # concentration of everyone else, so report the external HHI with the ai_agent class removed as well.
    hhi_ex_ai, _ = hhi_from_counts({c.account_id: c.receipts for c in callers if c.cls is not CallerClass.ai_agent})
    # Bootstrap CIs: one unit per external receipt (each carries one predecessor).
    ext_units = [[acct] for acct, n in ext_counts.items() for _ in range(n)]
    ai_accounts = {c.account_id for c in callers if c.cls is CallerClass.ai_agent}
    boot_ext = bootstrap_hhi_ci(ext_units, stream=BOOTSTRAP_STREAM_EXTERNAL)
    boot_ex_ai = bootstrap_hhi_ci([u for u in ext_units if u[0] not in ai_accounts], stream=BOOTSTRAP_STREAM_EXTERNAL_EX_AI)
    return {
        "hhi_external_ci90": boot_ext["hhi_ci90"],
        "n_eff_external_ci90": boot_ext["n_eff_ci90"],
        "hhi_external_ex_ai_agent_ci90": boot_ex_ai["hhi_ci90"],
        "bootstrap_draws": boot_ext["draws"],
        "bootstrap_method": boot_ext["method"],
        "hhi_external_ex_ai_agent": hhi_ex_ai,
        "n_eff_external_ex_ai_agent": None if hhi_ex_ai is None else 10_000.0 / hhi_ex_ai,
        "callers": callers,
        "hhi_external": hhi_ext,
        "n_eff_external": None if hhi_ext is None else 10_000.0 / hhi_ext,
        "hhi_all": hhi_all,
        "ai_agent_share": class_share.get(CallerClass.ai_agent.value, 0.0),
        "bridge_share": class_share.get(CallerClass.bridge_relayer.value, 0.0),
        "class_share_external": class_share,
        "class_counts": class_counts,
        "method_mix": dict(method_mix.most_common()),
        "execute_intents_by_predecessor_class": dict(exec_by_pred.most_common()),
        "receipts_sampled": len(rows),
        "external_receipts_sampled": sum(ext_counts.values()),
        "unique_external_callers": len(ext_counts),
        "sample_block_range": [min(heights), max(heights)] if heights else [],
        "sample_time_range_utc": [_ns_to_iso(min(timestamps)), _ns_to_iso(max(timestamps))] if timestamps else [],
        "sample_span_s": (max(timestamps) - min(timestamps)) / 1e9 if timestamps else None,
    }


# ----------------------------------------------------------------------------- solver forensics (execute_intents payloads)
def decode_nested_json(value: Any, max_layers: int = 6) -> Any:
    """Decode a value NearBlocks has JSON-string-encoded one or more times (``args`` -> ``signed[].payload.message``).

    Each layer is either a JSON document or a JSON string literal whose quotes were stripped (so the text
    reads ``{\\"deadline\\":...}``); the latter is undone by re-quoting. Returns the first non-string value
    reached, or None when a layer cannot be decoded.
    """
    current = value
    for _ in range(max_layers):
        if not isinstance(current, str):
            return current
        try:
            current = json.loads(current)
            continue
        except ValueError:
            pass
        try:
            current = json.loads('"' + current + '"')
        except ValueError:
            return None
    return None if isinstance(current, str) else current


def _signed_payload(entry: Any) -> dict[str, Any] | None:
    """signer_id, intent names and token_diff legs of one ``signed[]`` entry; None when the message is unreadable."""
    if not isinstance(entry, Mapping):
        return None
    payload = entry.get("payload")
    message = decode_nested_json(payload.get("message") if isinstance(payload, Mapping) else payload)
    if not isinstance(message, Mapping) or not isinstance(message.get("signer_id"), str):
        return None
    intents = [i for i in (message.get("intents") or []) if isinstance(i, Mapping)]
    return {
        "signer_id": message["signer_id"],
        "intents": [str(i.get("intent")) for i in intents if i.get("intent") is not None],
        "token_diffs": [dict(i.get("diff")) for i in intents if i.get("intent") == "token_diff" and isinstance(i.get("diff"), Mapping)],
        # ``transfer`` intents (receiver + token amounts): the hub-settled flow pays solvers and is paid by them this way.
        "transfers": [
            {"receiver_id": i["receiver_id"], "tokens": dict(i.get("tokens")) if isinstance(i.get("tokens"), Mapping) else {}}
            for i in intents if i.get("intent") == "transfer" and isinstance(i.get("receiver_id"), str)
        ],
        "standard": entry.get("standard"),
    }


def parse_execute_intents(row: Any) -> list[dict[str, Any]]:
    """Signer payloads of every ``execute_intents`` action in a NearBlocks receipt row (empty when none / undecodable).

    Each item: ``{signer_id, intents, token_diffs, standard}``; an unreadable payload yields
    ``{"signer_id": None, "undecodable": True}`` so callers can count them.
    """
    actions = row.get("actions") if isinstance(row, Mapping) else getattr(row, "actions", None)
    out: list[dict[str, Any]] = []
    for action in actions or []:
        if not isinstance(action, Mapping) or action.get("method") != _EXECUTE_INTENTS:
            continue
        args = decode_nested_json(action.get("args"))
        signed = args.get("signed") if isinstance(args, Mapping) else None
        for entry in signed if isinstance(signed, list) else []:
            parsed = _signed_payload(entry)
            out.append(parsed if parsed is not None else {"signer_id": None, "intents": [], "token_diffs": [], "transfers": [], "undecodable": True})
    return out


def classify_fill_signers(
    payloads: Sequence[Mapping[str, Any]], known_solvers: frozenset[str] = frozenset()
) -> tuple[list[str], list[str], str]:
    """Split one receipt's signers into (solvers, takers, rule) when it is a fill; ([], [], reason) otherwise.

    A fill needs >= 2 distinct signers with token_diff legs. Rules, in order:
      ``structure``: signers whose every intent is token_diff are solvers when at least one counterparty
                     bundles a withdrawal/transfer (users withdraw what they bought; market makers do not);
      ``name_or_known``: otherwise, the signers whose name matches the solver pattern or that the
                     structure rule already identified as solvers elsewhere in the sample
                     (``known_solvers``), provided that leaves a counterparty;
      ``implicit``:  otherwise, named accounts are solvers when every counterparty is an implicit account
                     (1Click deposit addresses are per-swap 64-hex accounts);
      ``unresolved`` when none of these separates the two sides.
    """
    by_signer: dict[str, dict[str, Any]] = {}
    for p in payloads:
        sid = p.get("signer_id")
        if not isinstance(sid, str) or not p.get("token_diffs"):
            continue
        slot = by_signer.setdefault(sid, {"intents": set(), "pure": True})
        slot["intents"].update(p.get("intents") or [])
        slot["pure"] = slot["pure"] and all(i == "token_diff" for i in (p.get("intents") or []))
    if len(by_signer) < 2:
        return [], [], "not_a_fill"
    signers = list(by_signer)
    pure = [s for s in signers if by_signer[s]["pure"]]
    withdrawing = [s for s in signers if by_signer[s]["intents"] & _WITHDRAWAL_INTENTS]
    if pure and withdrawing and len(pure) < len(signers):
        return pure, [s for s in signers if s not in pure], "structure"
    flagged = [s for s in signers if _SOLVER_NAME.search(s) or s in known_solvers]
    if flagged and len(flagged) < len(signers):
        return flagged, [s for s in signers if s not in flagged], "name_or_known"
    implicit = [s for s in signers if classify_account(s) is CallerClass.implicit_account]
    named = [s for s in signers if s not in implicit]
    if implicit and named:
        return named, implicit, "implicit"
    return [], signers, "unresolved"


def bootstrap_hhi_ci(
    events: Sequence[Sequence[str]],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    stream: int = 0,
    level: float = 0.90,
    strata: Sequence[str | None] | None = None,
) -> dict[str, Any]:
    """Bias-corrected (BC) percentile bootstrap CI for HHI and N_eff over resampled settlement units.

    ``events`` is one list of participating accounts per sampled unit (an atomic fill receipt lists every solver
    side; a hub leg or a deposit receipt lists one account). Without ``strata`` each draw resamples the units with
    replacement (multinomial weights, n units), recomputes participation counts per account and HHI = sum (100 s_i)^2.

    With ``strata`` (one label per event, e.g. the NearBlocks page "p3" the unit came from) and at least two distinct
    labels, the draw is a BLOCK (cluster) bootstrap: the K page blocks are resampled with replacement (multinomial over
    K) and every unit of a drawn block enters together. Fills inside one ~45 s page are serially correlated (the same
    solvers quote consecutive blocks), so treating them as independent units understates the uncertainty; resampling
    whole pages keeps that within-page dependence and lets the interval reflect how concentration varies between
    pages hours apart. With few blocks the interval is wide by construction, which is the honest answer.

    HHI is a sum of squared shares, so resampling noise pushes the bootstrap distribution ABOVE the point
    estimate (E[s_hat^2] = s^2 + var); the plain percentile interval then sits almost entirely above the point.
    The BC correction (Efron 1987) shifts the quantiles: z0 = Phi^-1(P(HHI* < HHI_hat)), bounds at
    Phi(2 z0 -/+ z_{1-a/2}), and the interval is widened to contain the point estimate (BC cannot reach below a point
    that sits at the minimum of the bootstrap support). The plain percentile interval is kept as ``hhi_ci90_percentile``.
    The generator is ``numpy.random.default_rng([BOOTSTRAP_SEED, stream])`` (BOOTSTRAP_SEED = 20261114), so the
    interval is reproducible. N_eff bounds are 10,000 / HHI bounds (order reversed). None fields when there are no units.
    """
    if strata is not None and len(strata) != len(events):
        raise ValueError(f"strata has {len(strata)} labels for {len(events)} events")
    pairs = [(list(e), (strata[i] if strata is not None else None)) for i, e in enumerate(events) if e]
    labels = sorted({str(lab) for _, lab in pairs}) if strata is not None else []
    block = len(labels) >= 2
    if block:
        method = (
            f"bias-corrected percentile block bootstrap by page: resample the {len(labels)} page strata ({', '.join(labels)}) with "
            f"replacement, every unit of a drawn page enters together ({len(pairs)} units), {draws} draws, numpy default_rng("
            f"[{BOOTSTRAP_SEED}, {stream}]); keeps within-page serial correlation, so the interval reflects between-page variation"
        )
    else:
        method = (
            f"bias-corrected percentile bootstrap: resample the {len(events)} sampled units with replacement, {draws} draws, "
            f"numpy default_rng([{BOOTSTRAP_SEED}, {stream}]); within-sample noise only (serial correlation of one short window not modelled)"
        )
    out: dict[str, Any] = {
        "hhi_ci90": None, "n_eff_ci90": None, "hhi_ci90_percentile": None, "draws": draws, "units": len(events), "level": level,
        "seed": [BOOTSTRAP_SEED, stream], "method": method, "resampling": "block_by_page" if block else "unit",
        "blocks": len(labels) if block else None,
    }
    if not pairs or draws <= 0:
        return out
    units = [e for e, _ in pairs]
    accounts = sorted({a for e in units for a in e})
    index = {a: i for i, a in enumerate(accounts)}
    m = np.zeros((len(units), len(accounts)))
    for r, e in enumerate(units):
        for a in e:
            m[r, index[a]] += 1.0
    n = len(units)
    rng = np.random.default_rng([BOOTSTRAP_SEED, stream])
    if block:
        lab_index = {lab: i for i, lab in enumerate(labels)}
        mb = np.zeros((len(labels), len(accounts)))
        for r, (_, lab) in enumerate(pairs):
            mb[lab_index[str(lab)]] += m[r]
        k = len(labels)
        weights = rng.multinomial(k, np.full(k, 1.0 / k), size=draws)
        counts = weights @ mb
    else:
        weights = rng.multinomial(n, np.full(n, 1.0 / n), size=draws)
        counts = weights @ m
    totals = counts.sum(axis=1)
    shares = counts / totals[:, None]
    hhi = (shares**2).sum(axis=1) * 1e4
    tail = (1.0 - level) / 2.0
    point_counts = m.sum(axis=0)
    point = float(((point_counts / point_counts.sum()) ** 2).sum() * 1e4)
    below = (float((hhi < point - 1e-9).sum()) + 0.5 * float((np.abs(hhi - point) <= 1e-9).sum())) / draws
    below = min(max(below, 0.5 / draws), 1.0 - 0.5 / draws)
    nd = NormalDist()
    z0 = nd.inv_cdf(below)
    z = nd.inv_cdf(1.0 - tail)
    q_lo, q_hi = nd.cdf(2 * z0 - z), nd.cdf(2 * z0 + z)
    lo, hi = (float(x) for x in np.quantile(hhi, [q_lo, q_hi]))
    # At a boundary (equal shares: HHI_hat is the smallest value any resample can take) every draw sits at or above the
    # point and BC cannot reach below it; the interval is widened to include the point estimate.
    lo, hi = min(lo, point), max(hi, point)
    p_lo, p_hi = (float(x) for x in np.quantile(hhi, [tail, 1.0 - tail]))
    out.update({
        "hhi_ci90": [lo, hi], "n_eff_ci90": [10_000.0 / hi, 10_000.0 / lo], "hhi_ci90_percentile": [p_lo, p_hi],
        "hhi_point": point, "bias_z0": z0, "units": n,
    })
    return out


def detect_settlement_hub(
    edges: Sequence[tuple[str, str]], *, min_counterparties: int = HUB_MIN_COUNTERPARTIES, dominance: float = HUB_DOMINANCE_RATIO,
) -> dict[str, Any] | None:
    """The account most transfer intents run through, when one clearly dominates; None otherwise.

    ``edges`` are (signer, receiver) pairs of ``transfer`` intents inside execute_intents. Degree = number of
    distinct counterparties (either direction). The hub is the top-degree account when its degree is at least
    ``min_counterparties`` and ``dominance`` x the runner-up's. Nothing is hard-coded: on 2026-11-08 the live
    sample's hub was a 64-hex account with 74 counterparties vs 17 for the next account.
    """
    neighbours: dict[str, set[str]] = {}
    for s, r in edges:
        if s == r:
            continue
        neighbours.setdefault(s, set()).add(r)
        neighbours.setdefault(r, set()).add(s)
    if not neighbours:
        return None
    ranked = sorted(neighbours, key=lambda a: (-len(neighbours[a]), a))
    top = ranked[0]
    deg = len(neighbours[top])
    runner = len(neighbours[ranked[1]]) if len(ranked) > 1 else 0
    if deg < min_counterparties or deg < dominance * runner:
        return None
    return {
        "account_id": top, "distinct_counterparties": deg, "runner_up_counterparties": runner,
        "transfers_in": sum(1 for s, r in edges if r == top and s != r), "transfers_out": sum(1 for s, r in edges if s == top and s != r),
        "account_class": classify_account(top).value,
    }


def solver_concentration(txns: Iterable[Any], warnings: list[str] | None = None) -> dict[str, Any]:
    """HHI over solver fill participations parsed from execute_intents payloads (see module docstring).

    Two settlement modes are decoded from the same NEP-413 payloads:
      ``atomic_token_diff``: one receipt with >= 2 token_diff signers (classify_fill_signers);
      ``hub_transfer``: a solver's ``transfer`` intent to the settlement hub (detect_settlement_hub), i.e. the
          solver delivering the output leg of a swap the hub routes. Solvers are hub counterparties that the
          atomic structure rule already identified, whose name matches the solver pattern, or that both pay and
          are paid by the hub at least twice in the sample without ever signing a withdrawal (one-shot 1Click
          deposit addresses pay the hub once and withdraw).
    Each atomic fill and each hub leg is one sampled unit for the bootstrap; HHI_solver is over participations
    per solver account across both modes, with per-mode HHIs alongside. ``measurement_status`` is "measured",
    "thin" (< SOLVER_MIN_PARTICIPATIONS participations) or "not_measured".

    Rows carrying ``valuo_stratum`` (the solver-sample page, set by the collector) make the headline CI a block
    bootstrap by page (``bootstrap_hhi_ci(strata=...)``); the unit-level bootstrap is kept alongside as
    ``hhi_solver_ci90_unit_bootstrap`` and ``hhi_solver_by_stratum`` lists the HHI of each page on its own.
    """
    warnings = warnings if warnings is not None else []
    rows = _parse_rows(txns, [])  # dedup already reported by caller_concentration
    fills_by_solver: Counter[str] = Counter()
    atomic_by_solver: Counter[str] = Counter()
    hub_by_solver: Counter[str] = Counter()
    example_tx: dict[str, str] = {}
    taker_classes: Counter[str] = Counter()
    rules: Counter[str] = Counter()
    n_exec = n_fills = n_unresolved = n_undecodable = n_payloads = 0
    signer_payloads: Counter[str] = Counter()
    decoded: list[tuple[Any, list[dict[str, Any]]]] = []
    timestamps: list[int] = []
    for row in rows:
        payloads = parse_execute_intents(row.model_dump())
        if payloads:
            decoded.append((row, payloads))
            ts = _int(_get(row.receipt_block, "block_timestamp"))
            if ts is not None:
                timestamps.append(ts)
    # Pass 1: solver identities fixed by payload structure alone; pass 2 reuses them where every signer is a
    # pure token_diff (a solver's name does not have to say "solver").
    known: set[str] = set()
    for _row, payloads in decoded:
        solvers, _takers, rule = classify_fill_signers(payloads)
        if rule == "structure":
            known.update(solvers)
    known_solvers = frozenset(known)
    events: list[list[str]] = []
    atomic_events: list[list[str]] = []
    edges: list[tuple[str, str, str | None, str | None]] = []
    event_strata: list[str | None] = []
    withdrawing: set[str] = set()
    for row, payloads in decoded:
        n_exec += 1
        n_payloads += len(payloads)
        n_undecodable += sum(1 for p in payloads if p.get("undecodable"))
        for p in payloads:
            sid = p.get("signer_id")
            if not isinstance(sid, str):
                continue
            signer_payloads[sid] += 1
            if set(p.get("intents") or []) & (_WITHDRAWAL_INTENTS - {"transfer"}):
                withdrawing.add(sid)
            for t in p.get("transfers") or []:
                edges.append((sid, t["receiver_id"], row.transaction_hash, row.valuo_stratum))
        solvers, takers, rule = classify_fill_signers(payloads, known_solvers)
        rules[rule] += 1
        if rule == "not_a_fill":
            continue
        n_fills += 1
        if not solvers:
            n_unresolved += 1
            continue
        events.append(list(solvers))
        event_strata.append(row.valuo_stratum)
        atomic_events.append(list(solvers))
        for s in solvers:
            fills_by_solver[s] += 1
            atomic_by_solver[s] += 1
            if row.transaction_hash and s not in example_tx:
                example_tx[s] = row.transaction_hash
        for t in takers:
            taker_classes[classify_account(t).value] += 1

    # Hub-settled legs.
    hub = detect_settlement_hub([(s, r) for s, r, _, _ in edges])
    hub_events: list[list[str]] = []
    hub_solver_rules: dict[str, str] = {}
    if hub is not None:
        h = hub["account_id"]
        to_hub: Counter[str] = Counter(s for s, r, _, _ in edges if r == h and s != h)
        from_hub: Counter[str] = Counter(r for s, r, _, _ in edges if s == h and r != h)
        for acct in sorted(to_hub):
            if acct in known_solvers:
                hub_solver_rules[acct] = "known_from_atomic_structure"
            elif _SOLVER_NAME.search(acct):
                hub_solver_rules[acct] = "name"
            elif to_hub[acct] >= HUB_SOLVER_MIN_LEGS and from_hub[acct] >= HUB_SOLVER_MIN_LEGS and acct not in withdrawing:
                hub_solver_rules[acct] = "repeat_two_way_counterparty"
        for s, r, tx, stratum in edges:
            if r == h and s in hub_solver_rules:
                hub_events.append([s])
                event_strata.append(stratum)
                fills_by_solver[s] += 1
                hub_by_solver[s] += 1
                if tx and s not in example_tx:
                    example_tx[s] = tx
        rules["hub_transfer_leg"] = len(hub_events)
        events.extend(hub_events)
        hub.update({
            "solver_counterparties": {a: {"legs_to_hub": to_hub[a], "legs_from_hub": from_hub[a], "rule": hub_solver_rules[a]} for a in sorted(hub_solver_rules)},
            "non_solver_counterparties_paying_hub": sum(1 for a in to_hub if a not in hub_solver_rules),
            "legs_counted": len(hub_events),
            "rule": (
                f"hub = account with the most distinct transfer counterparties (>= {HUB_MIN_COUNTERPARTIES} and >= {HUB_DOMINANCE_RATIO:g}x the runner-up); "
                f"a hub leg = one transfer intent from a solver to the hub; solver = known from the atomic structure rule, name pattern, "
                f"or >= {HUB_SOLVER_MIN_LEGS} legs each way with the hub and no withdrawal intent"
            ),
        })
    hhi, shares = hhi_from_counts(fills_by_solver)
    hhi_atomic, _ = hhi_from_counts(atomic_by_solver)
    hhi_hub, _ = hhi_from_counts(hub_by_solver)
    participations = sum(fills_by_solver.values())
    if hhi is None:
        status = "not_measured"
    elif participations < SOLVER_MIN_PARTICIPATIONS:
        status = "thin"
    else:
        status = "measured"
    stratified = any(st is not None for st in event_strata)
    boot = bootstrap_hhi_ci(events, stream=BOOTSTRAP_STREAM_SOLVER, strata=event_strata if stratified else None)
    boot_unit = bootstrap_hhi_ci(events, stream=BOOTSTRAP_STREAM_SOLVER_UNIT) if boot["resampling"] == "block_by_page" else boot
    by_stratum: list[dict[str, Any]] = []
    if stratified:
        per: dict[str, Counter[str]] = {}
        for ev, st in zip(events, event_strata):
            c = per.setdefault(str(st), Counter())
            for acct in ev:
                c[acct] += 1
        for st in sorted(per, key=lambda x: (len(x), x)):
            h_st, sh_st = hhi_from_counts(per[st])
            top = max(sh_st, key=lambda a: (sh_st[a], a)) if sh_st else None
            by_stratum.append({
                "stratum": st, "participations": sum(per[st].values()), "unique_solvers": len(per[st]), "hhi_solver": h_st,
                "top_solver": top, "top_share": sh_st.get(top) if top else None,
            })
    if n_exec and hhi is None:
        warnings.append(
            f"solver audit: {n_exec} execute_intents receipts decoded but no atomic fill or hub leg with an attributable solver; "
            "hhi_solver null (not measured)"
        )
    elif status == "thin":
        warnings.append(f"solver audit: only {participations} solver fill participations; HHI_solver {hhi:,.0f} is thin (< {SOLVER_MIN_PARTICIPATIONS})")
    if n_undecodable:
        warnings.append(f"solver audit: {n_undecodable} of {n_payloads} signed payloads could not be decoded (non-NEP-413 standards are skipped)")
    solvers_table = [
        {"account_id": s, "fills": fills_by_solver[s], "share": shares[s], "fills_atomic": atomic_by_solver.get(s, 0), "fills_hub": hub_by_solver.get(s, 0),
         "example_tx_hash": example_tx.get(s), "payloads_signed": signer_payloads.get(s, 0), "name_matches_solver_pattern": bool(_SOLVER_NAME.search(s))}
        for s in sorted(fills_by_solver, key=lambda a: (-fills_by_solver[a], a))
    ]
    return {
        "hhi_solver": hhi,
        "n_eff_solver": None if hhi is None else 10_000.0 / hhi,
        "hhi_solver_ci90": boot["hhi_ci90"],
        "n_eff_solver_ci90": boot["n_eff_ci90"],
        "bootstrap_draws": boot["draws"],
        "bootstrap_units": boot["units"],
        "bootstrap_seed": boot["seed"],
        "bootstrap_method": boot["method"],
        "hhi_solver_ci90_percentile": boot["hhi_ci90_percentile"],
        "bootstrap_resampling": boot["resampling"],
        "bootstrap_blocks": boot["blocks"],
        "hhi_solver_ci90_unit_bootstrap": boot_unit["hhi_ci90"],
        "hhi_solver_by_stratum": by_stratum,
        "measurement_status": status,
        "min_participations_for_measured": SOLVER_MIN_PARTICIPATIONS,
        "n_fills": n_fills + len(hub_events),
        "n_fills_atomic": n_fills,
        "n_fills_hub_legs": len(hub_events),
        "n_fills_attributed": participations,
        "n_fills_unresolved": n_unresolved,
        "hhi_solver_atomic": hhi_atomic,
        "hhi_solver_hub": hhi_hub,
        "n_execute_intents_receipts": n_exec,
        "n_signed_payloads": n_payloads,
        "n_payloads_undecodable": n_undecodable,
        "n_transfer_intents": len(edges),
        "unique_solvers": len(fills_by_solver),
        "solvers": solvers_table,
        "settlement_hub": hub,
        "taker_class_mix": dict(taker_classes.most_common()),
        "attribution_rules": dict(rules.most_common()),
        "top_signers_by_payloads": dict(signer_payloads.most_common(10)),
        "known_solvers_from_structure": sorted(known_solvers),
        "sample_time_range_utc": [_ns_to_iso(min(timestamps)), _ns_to_iso(max(timestamps))] if timestamps else [],
        "sample_span_s": (max(timestamps) - min(timestamps)) / 1e9 if timestamps else None,
        "method": (
            "fill participation = (a) the solver side of an atomic execute_intents fill (>= 2 token_diff signers; solver = pure "
            "token_diff signer when the counterparty bundles a withdrawal, else a signer whose name matches (*solver*, *-liq*, market "
            "maker) or that the structure rule identified elsewhere in the sample, else the named account facing an implicit 1Click "
            "deposit address), or (b) a transfer intent from a solver to the settlement hub (see settlement_hub.rule); HHI over "
            "participations per solver account; transfers that are not solver-to-hub legs are inventory or user moves, not fills. "
            "hhi_solver_ci90 is a bias-corrected bootstrap (bootstrap_method): a block bootstrap by NearBlocks page when the sample "
            "is stratified in time (bootstrap_resampling = block_by_page), else over sampled units"
        ),
    }


# ----------------------------------------------------------------------------- volatility
def price_volatility(points: Iterable[Any], warnings: list[str] | None = None, *, source: str = "nearstats:price-history") -> dict[str, Any]:
    """Realized volatility from OHLC points ``{t: ms, c: close}``.

    Point spacing is measured (median delta t) so sigma annualizes correctly even if the provider changes
    the granularity; for the 1y window it is one day -> periods_per_year = 365. ``source`` names the
    series (nearstats, or the coins.llama.fi fallback).
    """
    warnings = warnings if warnings is not None else []
    parsed: list[_PricePoint] = []
    for raw in points:
        try:
            parsed.append(_PricePoint.model_validate(raw))
        except ValidationError:
            continue
    parsed.sort(key=lambda p: p.t)
    closes = [p.c for p in parsed if p.c > 0]
    out: dict[str, Any] = {
        "window": "1y", "source": source, "n_points": len(closes), "n_obs": 0,
        "first_t_utc": _ms_to_iso(parsed[0].t) if parsed else None, "last_t_utc": _ms_to_iso(parsed[-1].t) if parsed else None,
        "price_first_usd": closes[0] if closes else None, "price_last_usd": closes[-1] if closes else None,
        "periods_per_year": None, "daily_sigma": None, "annualized_sigma": None, "mean_daily_log_return": None,
        "sigma_30d_annualized": None, "sigma_90d_annualized": None,
    }
    if len(closes) < 3:
        warnings.append(f"price volatility: only {len(closes)} usable closes; sigma null")
        return out
    gaps = sorted(b.t - a.t for a, b in zip(parsed, parsed[1:], strict=False) if b.t > a.t)
    median_gap_days = gaps[len(gaps) // 2] / _MS_PER_DAY if gaps else 1.0
    periods_per_year = DAYS_PER_YEAR / median_gap_days if median_gap_days > 0 else DAYS_PER_YEAR
    rets = _log_returns(closes)
    sigma = _sample_std(rets)
    out.update({
        "n_obs": len(rets), "periods_per_year": periods_per_year, "daily_sigma": sigma,
        "annualized_sigma": None if sigma is None else sigma * math.sqrt(periods_per_year),
        "mean_daily_log_return": sum(rets) / len(rets) if rets else None,
    })
    for label, n in (("sigma_30d_annualized", 30), ("sigma_90d_annualized", 90)):
        if len(rets) >= n:
            s = _sample_std(rets[-n:])
            out[label] = None if s is None else s * math.sqrt(periods_per_year)
    return out


def volume_volatility(chart: Any, days: int = 365, warnings: list[str] | None = None) -> dict[str, Any]:
    """Daily and monthly volatility of a daily USD volume chart (DefiLlama ``totalDataChart``).

    Daily: sigma of ln(V_t / V_{t-1}) over the last ``days`` points (zero-volume pairs skipped).
    Monthly: non-overlapping 30-day sums anchored at the latest day, ln(S_k / S_{k+1}) between consecutive
    sums, sample std. Monthly needs at least 90 days (two returns); otherwise None with a warning.
    """
    warnings = warnings if warnings is not None else []
    points = _chart_points(chart)[-days:]
    values = [v for _, v in points]
    out: dict[str, Any] = {
        "volume_series_days": len(values), "volume_source": f"defillama:dexs/{DEFILLAMA_SLUG}",
        "volume_daily_sigma": None, "volume_annualized_sigma": None, "volume_daily_n_obs": 0,
        "volume_monthly_sigma": None, "volume_monthly_n_obs": 0, "volume_monthly_mean_log_return": None,
        "volume_monthly_log_returns": [], "volume_monthly_sigma_ex_first_3": None,
        "volume_first_t_utc": _ms_to_iso(points[0][0] * 1e3) if points else None,
        "volume_last_t_utc": _ms_to_iso(points[-1][0] * 1e3) if points else None,
    }
    daily = _log_returns(values)
    sigma_d = _sample_std(daily)
    out.update({
        "volume_daily_n_obs": len(daily), "volume_daily_sigma": sigma_d,
        "volume_annualized_sigma": None if sigma_d is None else sigma_d * math.sqrt(DAYS_PER_YEAR),
    })
    if sigma_d is None:
        warnings.append(f"volume volatility: {len(values)} daily points are too few for a daily sigma")
    sums: list[float] = []
    end = len(values)
    while end - 30 >= 0:
        sums.append(sum(values[end - 30:end]))
        end -= 30
    monthly = _log_returns(list(reversed(sums)))  # chronological order
    sigma_m = _sample_std(monthly)
    out.update({
        "volume_monthly_n_obs": len(monthly), "volume_monthly_sigma": sigma_m,
        "volume_monthly_mean_log_return": sum(monthly) / len(monthly) if monthly else None,
        "volume_monthly_log_returns": monthly,
        # Sensitivity of sigma to the oldest window (incentive-program months dominate the early returns).
        "volume_monthly_sigma_ex_first_3": _sample_std(monthly[3:]) if len(monthly) > 4 else None,
    })
    if sigma_m is None:
        warnings.append(f"volume volatility: {len(values)} daily points yield {len(monthly)} monthly return(s); monthly sigma null")
    return out


# ----------------------------------------------------------------------------- fees
def align_daily_series(fees_chart: Any, revenue_chart: Any, volume_chart: Any, days: int = 365) -> list[list[float]]:
    """Inner join of the three daily charts on unix timestamp -> [[ts, fees, revenue, volume]] (last ``days``)."""
    fees = dict(_chart_points(fees_chart))
    rev = dict(_chart_points(revenue_chart))
    vol = dict(_chart_points(volume_chart))
    common = sorted(set(fees) & set(rev) & set(vol))[-days:]
    return [[ts, fees[ts], rev[ts], vol[ts]] for ts in common]


def _llama(payload: Any) -> _LlamaSummary | None:
    if not isinstance(payload, Mapping):
        return None
    try:
        return _LlamaSummary.model_validate(payload)
    except ValidationError:
        return None


def _ts_date(ts: int) -> date:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def aligned_window_sums(
    fees_chart: Any,
    revenue_chart: Any,
    holders_chart: Any,
    volume_chart: Any,
    *,
    days: int = TAKE_RATE_WINDOW_DAYS,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Sums of fees / revenue / holders revenue / volume over the last ``days`` COMPLETE UTC days common to the charts.

    The join is on unix day timestamps across fees, revenue and volume (holders revenue joins when present,
    else its sum is None). A trailing point dated ``as_of`` (today, UTC) is a partial day and is dropped.
    Returns ``window_days = 0`` when the join is empty.
    """
    fees, rev, vol = dict(_chart_points(fees_chart)), dict(_chart_points(revenue_chart)), dict(_chart_points(volume_chart))
    hrev = dict(_chart_points(holders_chart))
    common = set(fees) & set(rev) & set(vol)
    if hrev:
        common &= set(hrev)
    today = as_of or datetime.now(timezone.utc).date()
    ordered = sorted(ts for ts in common if _ts_date(ts) < today)
    window = ordered[-days:]
    out: dict[str, Any] = {
        "window_days": len(window), "window_requested_days": days,
        "window_start_utc": _ts_date(window[0]).isoformat() if window else None,
        "window_end_utc": _ts_date(window[-1]).isoformat() if window else None,
        "fees": None, "revenue": None, "holders": None, "volume": None,
    }
    if window:
        out.update({
            "fees": sum(fees[t] for t in window), "revenue": sum(rev[t] for t in window), "volume": sum(vol[t] for t in window),
            "holders": sum(hrev[t] for t in window) if hrev else None,
        })
    return out


def fee_metrics(
    fees_payload: Any,
    revenue_payload: Any,
    holders_payload: Any,
    dexs_payload: Any,
    *,
    nearstats_volume_30d: float | None = None,
    nearstats_public_30d: float | None = None,
    warnings: list[str] | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Fee capture metrics from the four DefiLlama summaries over ONE aligned calendar window.

    ``gross_fees_30d_usd`` / ``net_revenue_30d_usd`` / ``holders_revenue_30d_usd`` / ``volume_30d_usd`` are
    sums over the same last-30-complete-days window of the daily charts (``take_rate_window``), so
    gross_take_bps, net_take_bps and capture_ratio share a denominator and a numerator window. DefiLlama's
    own ``total30d`` fields are published under ``defillama_total30d`` as cross-checks (they mix a partial
    current day and, for dexs, a 29-day sum). When the daily charts are unavailable the totals fall back to
    ``total30d`` over DefiLlama's dexs volume, then nearstats' 30d volume, and the window is labelled
    unaligned with a warning. ``gross_take_bps_on_public_volume`` divides by the nearstats *public* 30d
    volume as an upper bound in case confidential volume carries no DefiLlama-tracked fees.
    """
    warnings = warnings if warnings is not None else []
    fees, rev, hrev, dexs = _llama(fees_payload), _llama(revenue_payload), _llama(holders_payload), _llama(dexs_payload)
    for label, obj in (("fees", fees), ("dailyRevenue", rev), ("dailyHoldersRevenue", hrev), ("dexs volume", dexs)):
        if obj is None:
            warnings.append(f"defillama {DEFILLAMA_SLUG} {label} unavailable; dependent fee fields null")
    win = aligned_window_sums(
        fees.totalDataChart if fees else None, rev.totalDataChart if rev else None,
        hrev.totalDataChart if hrev else None, dexs.totalDataChart if dexs else None, as_of=as_of,
    )
    llama_totals = {
        "fees": fees.total30d if fees else None, "revenue": rev.total30d if rev else None,
        "holders": hrev.total30d if hrev else None, "volume": dexs.total30d if dexs else None,
    }
    if win["window_days"] > 0 and win["volume"]:
        f30, r30, h30, vol30 = win["fees"], win["revenue"], win["holders"], win["volume"]
        window_days = win["window_days"]
        vol_src = f"defillama:dexs/{DEFILLAMA_SLUG} daily chart summed over the aligned window"
        take_window = f"aligned daily charts, {window_days} complete UTC days {win['window_start_utc']}..{win['window_end_utc']}"
        if window_days < TAKE_RATE_WINDOW_DAYS:
            warnings.append(f"take-rate window has only {window_days} common complete days (requested {TAKE_RATE_WINDOW_DAYS})")
        if h30 is None:
            h30 = r30
            warnings.append("dailyHoldersRevenue chart unavailable; holders revenue window sum set to the dailyRevenue sum (same series live)")
    else:
        f30, r30, h30 = llama_totals["fees"], llama_totals["revenue"], llama_totals["holders"]
        window_days = TAKE_RATE_WINDOW_DAYS
        vol30, vol_src = (dexs.total30d, f"defillama:dexs/{DEFILLAMA_SLUG} total30d") if dexs and dexs.total30d else (None, None)
        if vol30 is None and nearstats_volume_30d:
            vol30, vol_src = nearstats_volume_30d, "nearstats:intents.totals.volume30dUsd"
            warnings.append("take-rate denominator fell back to nearstats 30d volume (DefiLlama dexs unavailable)")
        take_window = "UNALIGNED: DefiLlama total30d fields (daily charts unavailable); numerator and denominator windows may differ by a day"
        if f30 is not None and vol30 is not None:
            warnings.append("take rates computed from unaligned DefiLlama total30d fields (daily charts unavailable)")
    series = align_daily_series(
        fees.totalDataChart if fees else None, rev.totalDataChart if rev else None, dexs.totalDataChart if dexs else None,
    )
    return {
        "gross_fees_30d_usd": f30, "net_revenue_30d_usd": r30, "holders_revenue_30d_usd": h30,
        "gross_fees_24h_usd": fees.total24h if fees else None, "net_revenue_24h_usd": rev.total24h if rev else None,
        "gross_fees_7d_usd": fees.total7d if fees else None, "net_revenue_7d_usd": rev.total7d if rev else None,
        "fees_1y_usd": fees.total1y if fees else None, "revenue_1y_usd": rev.total1y if rev else None,
        "holders_revenue_1y_usd": hrev.total1y if hrev else None,
        "cumulative_fees_usd": fees.totalAllTime if fees else None,
        "cumulative_revenue_usd": rev.totalAllTime if rev else None,
        "cumulative_holders_revenue_usd": hrev.totalAllTime if hrev else None,
        "volume_30d_usd": vol30, "volume_30d_source": vol_src,
        "volume_30d_nearstats_usd": nearstats_volume_30d,
        "take_rate_window": take_window, "take_rate_window_days": window_days,
        "take_rate_window_start_utc": win["window_start_utc"], "take_rate_window_end_utc": win["window_end_utc"],
        "defillama_total30d": llama_totals,
        "gross_take_bps": _bps(f30, vol30), "net_take_bps": _bps(r30, vol30), "holders_take_bps": _bps(h30, vol30),
        "gross_take_bps_on_public_volume": _bps(f30, nearstats_public_30d),
        "capture_ratio": _ratio(r30, f30), "holders_capture_ratio": _ratio(h30, f30),
        "annualized_gross_fees_30d_usd": None if f30 is None else f30 * DAYS_PER_YEAR / window_days,
        "annualized_net_revenue_30d_usd": None if r30 is None else r30 * DAYS_PER_YEAR / window_days,
        "methodology": {
            "fees": _get(fees.methodology if fees else None, "Fees"),
            "revenue": _get(rev.methodology if rev else None, "Revenue"),
            "holders_revenue": _get(hrev.methodology if hrev else None, "HoldersRevenue"),
        },
        "daily_series_columns": ["ts_unix_s", "fees_usd", "revenue_usd", "volume_usd"],
        "daily_series_days": len(series),
        "daily_series": series,
    }


# ----------------------------------------------------------------------------- nearstats extraction
def extract_volume(summary: Any, dexs_payload: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    """Volume totals and the public/confidential split from nearstats, with DefiLlama totals alongside.

    confidential_share_30d = confidential30d / total30d (nearstats derives confidential as NEAR-reported
    total minus explorer public volume). When nearstats is down the headline totals come from DefiLlama
    and the split is null.
    """
    warnings = warnings if warnings is not None else []
    intents = _get(summary, "intents")
    totals = _get(intents, "totals")
    split = _get(intents, "totalsBreakdown")
    dexs = _llama(dexs_payload)
    out: dict[str, Any] = {
        "source": None, "allTimeUsd": None, "24h": None, "7d": None, "30d": None,
        "public30d": None, "confidential30d": None, "confidential_share_30d": None,
        "public7d": None, "confidential7d": None, "confidential_share_7d": None,
        "public24h": None, "confidential24h": None, "public_allTimeUsd": None, "confidential_allTimeUsd": None,
        "split_as_of_date": _get(split, "asOfDate"), "split_basis": _get(split, "basis"), "split_sources": _get(split, "sources"),
        "split_alignment": _get(split, "alignment"), "split_stale": _get(split, "stale"),
        "confidential_stream_status": _get(summary, "sourceHealth", "confidentialStream", "status"),
        "split_checks": [
            {"id": c.get("id"), "status": c.get("status"), "detail": c.get("detail")} for c in (_get(split, "checks") or []) if isinstance(c, Mapping)
        ],
        "weekOverWeek": _get(split, "weekOverWeek"), "records": _get(split, "records"),
        "vs_30d_record_ratio": None, "drawdown_from_30d_record": None,
        "defillama": {
            "24h": dexs.total24h if dexs else None, "7d": dexs.total7d if dexs else None, "30d": dexs.total30d if dexs else None,
            "1y": dexs.total1y if dexs else None, "allTimeUsd": dexs.totalAllTime if dexs else None,
        },
    }
    if isinstance(totals, Mapping):
        out.update({
            "source": "nearstats:intents.totals", "allTimeUsd": _num(totals.get("allTimeUsd")),
            "24h": _num(totals.get("volume24hUsd")), "7d": _num(totals.get("volume7dUsd")), "30d": _num(totals.get("volume30dUsd")),
        })
    elif dexs is not None:
        out.update({"source": f"defillama:dexs/{DEFILLAMA_SLUG}", "allTimeUsd": dexs.totalAllTime, "24h": dexs.total24h, "7d": dexs.total7d, "30d": dexs.total30d})
        warnings.append("nearstats totals unavailable; headline volume taken from DefiLlama, public/confidential split null")
    else:
        warnings.append("volume totals unavailable from both nearstats and DefiLlama")
    pub, conf = _get(split, "public"), _get(split, "confidential")
    if isinstance(pub, Mapping) and isinstance(conf, Mapping):
        out.update({
            "public30d": _num(pub.get("volume30dUsd")), "confidential30d": _num(conf.get("volume30dUsd")),
            "public7d": _num(pub.get("volume7dUsd")), "confidential7d": _num(conf.get("volume7dUsd")),
            "public24h": _num(pub.get("volume24hUsd")), "confidential24h": _num(conf.get("volume24hUsd")),
            "public_allTimeUsd": _num(pub.get("allTimeUsd")), "confidential_allTimeUsd": _num(conf.get("allTimeUsd")),
        })
        out["confidential_share_30d"] = _ratio(out["confidential30d"], out["30d"] or _sum_opt(out["public30d"], out["confidential30d"]))
        out["confidential_share_7d"] = _ratio(out["confidential7d"], out["7d"] or _sum_opt(out["public7d"], out["confidential7d"]))
    else:
        warnings.append("nearstats totalsBreakdown missing; confidential share null")
    max30 = _num(_get(split, "records", "max30dUsd"))
    ratio = _ratio(out["30d"], max30)
    if ratio is not None:
        out["vs_30d_record_ratio"] = ratio
        out["drawdown_from_30d_record"] = 1.0 - ratio
    return out


_SPLIT_FIELDS = (
    "public30d", "confidential30d", "public7d", "confidential7d", "public24h", "confidential24h",
    "public_allTimeUsd", "confidential_allTimeUsd", "confidential_share_30d", "confidential_share_7d",
)


def confidential_split_guard(
    volume: dict[str, Any],
    summary: Any,
    metrics: Mapping[str, Any] | None,
    warnings: list[str] | None = None,
    *,
    floor: float | None = None,
    fallback_share: float | None = None,
    boundary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide whether nearstats' public/confidential split is a measurement; fall back through a labelled chain if not.

    Writes into ``volume`` (and returns it):
      ``confidential_share_status``  "measured" | "implausible_fallback" | "unavailable"
      ``confidential_share_measured`` True only for "measured"
      ``confidential_share_source``  where ``confidential_share_30d`` now comes from
      ``confidential_share_reason``  why (list of labelled signals)
      ``confidential_share_30d_reported`` the share nearstats reported (kept for audit)
      ``confidential_share_fallback_chain`` the steps tried, in order
      ``split_reported``             the raw public/confidential fields, when they were withdrawn

    Implausible = reported 30d share < ``floor`` (registry ``confidential_share_plausibility_floor``) AND at least
    one contradiction inside the same nearstats payload:
      ``tvl_without_volume``  confidential TVL > 0 while all-time confidential volume <= floor x all-time total
                              (a cumulative series cannot hold ~$0 against a funded shard);
      ``stream_ok``           sourceHealth.confidentialStream.status == "ok" (the upstream stream is live);
      ``split_withheld``      a totalsBreakdown check whose detail says the split is withheld.
    A share below the floor with no contradiction is kept as measured (a genuine collapse) with a warning.
    Fallback chain when implausible: (1) a cross-check volume split in the fetched payloads - none exists today
    (DefiLlama dexs and nearstats totals both carry the NEAR total; privacyRoutes is a 100-row route sample, not a
    volume share); (2) registry assumption ``confidential_share`` (source=assumption). The public/confidential
    fields are then set to None (they are not measurements) and preserved under ``split_reported``. When the split
    is missing altogether the status is "unavailable" and the share stays None (sotp credits 0 and reports Engine 2
    as not measured, its existing branch).
    """
    warnings = warnings if warnings is not None else []
    floor = A.value("confidential_share_plausibility_floor") if floor is None else floor
    share = volume.get("confidential_share_30d")
    volume["confidential_share_30d_reported"] = share
    proxy = boundary_inflow_ratio(boundary, volume)
    volume.update(proxy)
    proxy_step = {
        "step": "onchain: confidential treasury inflow / (24h volume + inflow)", "value": proxy.get("confidential_boundary_inflow_ratio_24h"),
        "result": ("cross-check only, not used as the share: hourly treasury snapshots undercount gross flow (same-hour shields and "
                   "unshields net out) and overcount swap volume (solver inventory crosses the boundary too)"),
        "source": "intents_forensics.confidential_boundary",
    }
    chain: list[dict[str, Any]] = [{"step": "nearstats intents.totalsBreakdown", "value": share}]
    if share is None:
        volume.update({
            "confidential_share_status": SPLIT_STATUS_UNAVAILABLE, "confidential_share_measured": False,
            "confidential_share_source": "unavailable: nearstats public/confidential split missing",
            "confidential_share_reason": ["split_missing"], "confidential_share_fallback_chain": chain + [
                {"step": "fallback", "value": None, "result": "none applied: no evidence about the split this run; sotp credits 0 (Engine 2 not measured)"}],
        })
        return volume
    total_all = _num(volume.get("allTimeUsd"))
    conf_all = _num(volume.get("confidential_allTimeUsd"))
    tvl = _num((metrics or {}).get("confidential_tvl_usd"))
    stream = _get(summary, "sourceHealth", "confidentialStream", "status")
    checks = _get(summary, "intents", "totalsBreakdown", "checks") or []
    signals: list[str] = []
    if tvl is not None and tvl > 0 and conf_all is not None and total_all and conf_all <= floor * total_all:
        signals.append(f"tvl_without_volume: confidential TVL {_usd_txt(tvl)} but all-time confidential volume {_usd_txt(conf_all)} of {_usd_txt(total_all)}")
    if isinstance(stream, str) and stream.lower() == "ok":
        signals.append("stream_ok: nearstats sourceHealth.confidentialStream.status = ok")
    for c in checks if isinstance(checks, list) else []:
        detail = c.get("detail") if isinstance(c, Mapping) else None
        if isinstance(detail, str) and "withheld" in detail.lower():
            signals.append(f"split_withheld: check {c.get('id')!s} ({c.get('status')!s}) says '{detail}'")
    below = share < floor
    if not below or not signals:
        if below:
            warnings.append(
                f"confidential split: reported share {share:.4%} is below the {floor:.0%} plausibility floor but nothing in the nearstats "
                "payload contradicts it; kept as measured (a genuine collapse)"
            )
        volume.update({
            "confidential_share_status": SPLIT_STATUS_MEASURED, "confidential_share_measured": True,
            "confidential_share_source": "measured: nearstats intents.totalsBreakdown confidential / total 30d",
            "confidential_share_reason": ["below_floor_uncorroborated"] if below else [],
            "confidential_share_fallback_chain": chain + [proxy_step],
        })
        return volume
    fallback = A.get("confidential_share")
    value = fallback.value if fallback_share is None else fallback_share
    volume["split_reported"] = {k: volume.get(k) for k in _SPLIT_FIELDS}
    for k in _SPLIT_FIELDS:
        volume[k] = None
    volume.update({
        "confidential_share_30d": value,
        "confidential_share_status": SPLIT_STATUS_IMPLAUSIBLE, "confidential_share_measured": False,
        "confidential_share_source": f"assumption: registry confidential_share = {value:.0%} (nearstats split implausible; not a measurement)",
        "confidential_share_reason": [f"share_below_floor: reported {share:.4%} < {floor:.0%}", *signals],
        "confidential_share_fallback_chain": chain + [
            {"step": "cross-check in fetched payloads", "value": None,
             "result": "none: DefiLlama dexs and nearstats totals both report the NEAR total; privacyRoutes is a 100-row route sample, not a volume share"},
            proxy_step,
            {"step": "assumption:confidential_share", "value": value, "low": fallback.low, "high": fallback.high, "source": "assumption"},
        ],
    })
    warnings.append(
        f"CONFIDENTIAL SPLIT IMPLAUSIBLE - NOT MEASURED: nearstats reports confidential 30d {_usd_txt(volume['split_reported']['confidential30d'])} "
        f"({share:.4%} of 30d volume) while {'; '.join(signals)}. The public tile appears to include confidential flow (source change). "
        f"public/confidential fields set to null (raw kept in volume.split_reported); confidential_share_30d = {value:.0%} from the "
        "registry assumption confidential_share (source=assumption)"
    )
    r = proxy.get("confidential_boundary_inflow_ratio_24h")
    if r is not None:
        rel = "below" if r < fallback.low else ("above" if r > fallback.high else "inside")
        warnings.append(
            f"confidential share cross-check: on-chain treasury inflow over 24h was {_usd_txt(proxy.get('confidential_boundary_inflow_24h_usd'))}, "
            f"{r:.1%} of 24h volume + inflow, {rel} the assumption's {fallback.low:.0%}-{fallback.high:.0%} range (assumed {value:.0%}). "
            "A proxy, not a measurement of the share: hourly snapshots undercount gross flow and solver inventory inflates it"
        )
    return volume


def boundary_inflow_ratio(boundary: Mapping[str, Any] | None, volume: Mapping[str, Any]) -> dict[str, Any]:
    """On-chain proxy for the confidential share: treasury inflow over 24h / (24h volume + that inflow).

    The denominator adds the inflow so the ratio stays below 1 whether or not the 24h total already includes
    confidential flow. Null when the boundary audit or the 24h volume is missing."""
    b = boundary or {}
    inflow, total = _num(b.get("flow_24h_in_lower_bound_usd")), _num(volume.get("24h"))
    ratio = inflow / (total + inflow) if inflow is not None and total and total > 0 else None
    return {"confidential_boundary_inflow_24h_usd": inflow, "confidential_boundary_inflow_ratio_24h": ratio}


def _usd_txt(x: float | None) -> str:
    if x is None:
        return "n/a"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            return f"${x / div:,.2f}{suf}"
    return f"${x:,.2f}"


def _sum_opt(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a + b


def extract_protocol_metrics(summary: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    """Cumulative fees, confidential TVL (+ nearstats' own verification status) and 7d unique users."""
    warnings = warnings if warnings is not None else []
    pm = _get(summary, "intents", "protocolMetrics")
    if not isinstance(pm, Mapping):
        warnings.append("nearstats protocolMetrics missing; confidential TVL / unique users / cumulative fees null")
        return {
            "confidential_tvl_usd": None, "confidential_tvl_verified": False, "confidential_tvl_source_status": None,
            "unique_users_7d": None, "cumulative_fees_nearstats_usd": None, "confidential_tvl_warnings": [],
        }
    status = _get(pm, "confidentialTvlObservation", "sourceStatus")
    tvl_warnings = _get(pm, "confidentialTvlObservation", "warnings")
    return {
        "confidential_tvl_usd": _num(pm.get("confidentialTvlUsd")),
        "confidential_tvl_verified": status == "verified",
        "confidential_tvl_source_status": status if isinstance(status, str) else None,
        "confidential_tvl_warnings": [w for w in tvl_warnings if isinstance(w, str)] if isinstance(tvl_warnings, list) else [],
        "unique_users_7d": _int(pm.get("uniqueUsers7d")),
        "cumulative_fees_nearstats_usd": _num(pm.get("totalGeneratedFeesUsd")),
    }


def apply_onchain_tvl(metrics: dict[str, Any], boundary: Mapping[str, Any] | None) -> dict[str, Any]:
    """Prefer the treasury TVL read on-chain over the nearstats-reported figure; keep the reported one for audit."""
    tvl = _num((boundary or {}).get("tvl_usd"))
    out = dict(metrics)
    out["confidential_tvl_reported_usd"] = metrics.get("confidential_tvl_usd")
    out["confidential_tvl_reported_status"] = metrics.get("confidential_tvl_source_status")
    if tvl is not None and tvl > 0:
        out.update({"confidential_tvl_usd": tvl, "confidential_tvl_verified": True, "confidential_tvl_source_status": "onchain_measured"})
    return out


def extract_price(summary: Any, nearblocks_stats: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    """NEAR price facts (CoinGecko via nearstats) plus NearBlocks' independent supply/price figures."""
    warnings = warnings if warnings is not None else []
    price = _get(summary, "price")
    facts = _get(price, "facts")
    out: dict[str, Any] = {
        "current_usd": None, "change_24h_pct": None, "fdv_usd": None, "market_cap_usd": None, "circulating_supply": None,
        "total_supply": None, "perf": None, "price_change_pct": None, "ath_usd": None, "ath_date": None,
        "source": None, "fetched_at": None,
        "circulating_supply_nearblocks": None, "total_supply_nearblocks": None, "price_nearblocks_usd": None, "market_cap_nearblocks_usd": None,
    }
    if isinstance(price, Mapping):
        current = _num(price.get("currentUsd"))
        out["current_usd"] = current if current is not None else _num(_get(facts, "currentPriceUsd"))
        out["change_24h_pct"] = _num(price.get("change24hPct"))
        out["perf"] = price.get("performance") if isinstance(price.get("performance"), Mapping) else None
    else:
        warnings.append("nearstats price block missing; price facts null")
    if isinstance(facts, Mapping):
        out.update({
            "fdv_usd": _num(facts.get("fdvUsd")), "market_cap_usd": _num(facts.get("marketCapUsd")),
            "circulating_supply": _num(facts.get("circulatingSupply")), "total_supply": _num(facts.get("totalSupply")),
            "price_change_pct": facts.get("priceChangePct") if isinstance(facts.get("priceChangePct"), Mapping) else None,
            "ath_usd": _num(facts.get("athUsd")), "ath_date": facts.get("athDate") if isinstance(facts.get("athDate"), str) else None,
            "source": facts.get("source") if isinstance(facts.get("source"), str) else None,
            "fetched_at": facts.get("fetchedAt") if isinstance(facts.get("fetchedAt"), str) else None,
        })
    stats_rows = _get(nearblocks_stats, "stats")
    row = stats_rows[0] if isinstance(stats_rows, list) and stats_rows and isinstance(stats_rows[0], Mapping) else None
    if row is None:
        warnings.append("nearblocks /stats unavailable; circulating_supply_nearblocks null")
    else:
        out.update({
            "circulating_supply_nearblocks": _yocto_to_near(row.get("circulating_supply")),
            "total_supply_nearblocks": _yocto_to_near(row.get("total_supply")),
            "price_nearblocks_usd": _num(row.get("near_price")),
            "market_cap_nearblocks_usd": _num(row.get("market_cap")),
        })
    return out


def extract_top_swaps(summary: Any, n: int = 10) -> list[dict[str, Any]]:
    """The ``n`` largest recent swaps by USD volume with explorer links (nearstats topSwaps)."""
    swaps = _get(summary, "intents", "topSwaps")
    if not isinstance(swaps, list):
        return []
    rows = [s for s in swaps if isinstance(s, Mapping) and _num(s.get("volumeUsd")) is not None]
    rows.sort(key=lambda s: -(_num(s.get("volumeUsd")) or 0.0))
    out: list[dict[str, Any]] = []
    for s in rows[:n]:
        tx = s.get("txHash") if isinstance(s.get("txHash"), str) else None
        out.append({
            "tx_hash": tx,
            "origin_symbol": s.get("originSymbol"), "origin_chain": s.get("originChain"),
            "destination_symbol": s.get("destinationSymbol"), "destination_chain": s.get("destinationChain"),
            "volume_usd": _num(s.get("volumeUsd")), "amount_in_usd": _num(s.get("amountInUsd")), "amount_out_usd": _num(s.get("amountOutUsd")),
            "referral": s.get("referral"), "affiliates": [a for a in (s.get("affiliates") or []) if isinstance(a, str)],
            "status": s.get("status"), "created_at": s.get("createdAt"),
            "explorer_url": f"{EXPLORER_BASE}/txns/{tx}" if tx and s.get("hasNearSwapTransaction") else None,
        })
    return out


# ----------------------------------------------------------------------------- fetch groups
def _llama_chart_points(parsed: Any) -> list[dict[str, float]]:
    """coins.llama.fi ``/chart`` -> [{t: ms, c: price}] in the shape price_volatility reads."""
    prices = _get(parsed, "coins", "coingecko:near", "prices")
    out: list[dict[str, float]] = []
    for row in prices if isinstance(prices, list) else []:
        ts, price = (_num(row.get("timestamp")), _num(row.get("price"))) if isinstance(row, Mapping) else (None, None)
        if ts is not None and price is not None:
            out.append({"t": ts * 1e3, "c": price})
    return out


async def _fetch_confidential_boundary(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str], *, enabled: bool = True,
) -> dict[str, Any] | None:
    """Confidential treasury audit on NEAR mainnet (collectors.confidential_boundary); a failure is a warning, never fatal."""
    if not enabled:
        return None
    try:
        return await collect_confidential_boundary(client, ledger, warnings)
    except Exception as e:  # noqa: BLE001 - one optional source must not abort the forensics collector
        warnings.append(f"confidential boundary audit failed: {type(e).__name__}: {e}")
        return None


async def _fetch_nearstats(client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str]) -> tuple[Any, Any, str]:
    """(summary_or_None, price_points_or_None, price_source).

    The price series falls back to coins.llama.fi's key-free daily chart when nearstats' history is down
    (nearstats returned HTTP 500 for some windows while probing), so the SOTP's price sigma does not
    depend on a single host.
    """
    summary_task = fetch_json(client, ledger, source="nearstats", name="summary", method="GET", url=f"{config.NEARSTATS_API_BASE}/summary")
    price_task = fetch_json(
        client, ledger, source="nearstats", name="price_history:1y", method="GET",
        url=f"{config.NEARSTATS_API_BASE}/price-history", params={"window": "1y"},
    )
    (summary, s_rec), (price, p_rec) = await asyncio.gather(summary_task, price_task)
    if not s_rec.ok or not isinstance(summary, Mapping):
        warnings.append(f"nearstats summary unavailable ({s_rec.error}); volume split, price facts, TVL and top swaps null")
        summary = None
    points = _get(price, "points") if p_rec.ok else None
    source = "nearstats:price-history"
    if not isinstance(points, list) or not points:
        warnings.append(f"nearstats price-history 1y unavailable ({p_rec.error or 'no points'}); trying coins.llama.fi daily chart")
        chart, c_rec = await fetch_json(
            client, ledger, source="defillama", name="price_chart:near:365d", method="GET",
            url=f"{config.COINS_LLAMA_BASE}/chart/coingecko:near", params={"span": "365", "period": "1d"},
        )
        points = _llama_chart_points(chart) if c_rec.ok else []
        source = "coins.llama.fi:chart/coingecko:near (fallback)"
        if not points:
            warnings.append(f"coins.llama.fi price chart unavailable ({c_rec.error or 'no points'}); price volatility null")
            points = None
    return summary, points, source


async def _fetch_defillama(client: httpx.AsyncClient, ledger: ProvenanceLedger) -> dict[str, Any]:
    """The four near-intents summaries keyed fees / revenue / holders / dexs (None where the fetch failed)."""
    fees_url = f"{config.DEFILLAMA_API_BASE}/summary/fees/{DEFILLAMA_SLUG}"
    specs = {
        "fees": (f"fees:{DEFILLAMA_SLUG}", fees_url, None),
        "revenue": (f"fees:{DEFILLAMA_SLUG}:dailyRevenue", fees_url, {"dataType": "dailyRevenue"}),
        "holders": (f"fees:{DEFILLAMA_SLUG}:dailyHoldersRevenue", fees_url, {"dataType": "dailyHoldersRevenue"}),
        "dexs": (f"dexs:{DEFILLAMA_SLUG}", f"{config.DEFILLAMA_API_BASE}/summary/dexs/{DEFILLAMA_SLUG}", None),
    }
    results = await asyncio.gather(*(
        fetch_json(client, ledger, source="defillama", name=name, method="GET", url=url, params=params)
        for name, url, params in specs.values()
    ))
    return {
        key: (parsed if rec.ok and isinstance(parsed, Mapping) else None)
        for key, (parsed, rec) in zip(specs, results, strict=True)
    }


async def _fetch_nearblocks_pages(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str], *, pages: int, per_page: int, delay: float,
    errors: list[str] | None = None, method: str | None = None,
) -> tuple[list[Any], int]:
    """Receipt rows across up to ``pages`` pages; cursor pagination when offered, page=N otherwise.

    ``method`` filters NearBlocks' list to one contract method (``execute_intents`` for the solver audit); those
    pages are recorded as ``txns:intents.near:<method>:pN``.
    """
    errors = errors if errors is not None else []
    url = f"{config.NEARBLOCKS_API_BASE}/account/{SELF_ACCOUNT}/txns"
    rows: list[Any] = []
    pages_ok = 0
    cursor: str | None = None
    noted_fallback = False
    label = f"{method} " if method else ""
    for page in range(1, pages + 1):
        if page > 1:
            await asyncio.sleep(delay)
        params: dict[str, Any] = {"per_page": per_page}
        if method:
            params["method"] = method
        if cursor:
            params["cursor"] = cursor
        else:
            params["page"] = page
        name = f"txns:{SELF_ACCOUNT}:{method}:p{page}" if method else f"txns:{SELF_ACCOUNT}:p{page}"
        parsed, rec = await fetch_json(
            client, ledger, source="nearblocks", name=name, method="GET", url=url,
            params=params, headers=config.nearblocks_headers(), **_NEARBLOCKS_RETRY_KW,
        )
        txns = _get(parsed, "txns") if rec.ok else None
        if not isinstance(txns, list) or not txns:
            reason = f"failed ({rec.error})" if not rec.ok else "returned no receipts"
            if rec.http_status is None:
                reason += "; NearBlocks unreachable, remaining pages skipped"
            sample = "solver sample" if method else "caller sample"
            warnings.append(f"nearblocks {label}txns page {page} {reason}; {sample} has {pages_ok} page(s)")
            errors.append(rec.error or "no receipts")
            break
        rows.extend(txns)
        pages_ok += 1
        nxt = parsed.get("cursor") if isinstance(parsed, Mapping) else None
        cursor = str(nxt) if isinstance(nxt, (str, int)) and str(nxt) else None
        if cursor is None and page < pages and not noted_fallback:
            warnings.append("nearblocks response carried no cursor; using page=N pagination (pages may overlap if new receipts land)")
            noted_fallback = True
    return rows, pages_ok


# ----------------------------------------------------------------------------- stratified solver sample
def _raw_ts_ns(raw: Any) -> int | None:
    return _int(_get(raw, "receipt_block", "block_timestamp")) or _int(_get(raw, "block_timestamp"))


def _raw_id(raw: Any) -> int | None:
    return _int(_get(raw, "id"))


def plan_stratum_offsets(pages: int, target_span_s: float) -> list[float]:
    """Time offsets (seconds before the newest receipt) of the newest row of each solver-sample page.

    Page 1 sits at 0; pages 2..K are evenly spaced so page K starts ``target_span_s`` back:
    offset_k = target_span_s * (k - 1) / (K - 1). One page -> [0.0]; zero pages -> [].
    """
    if pages <= 0:
        return []
    if pages == 1:
        return [0.0]
    return [float(target_span_s) * k / (pages - 1) for k in range(pages)]


def estimate_id_rate(points: Iterable[tuple[int, int]]) -> float | None:
    """NearBlocks receipt ids per second from (id, block_timestamp_ns) pairs: least-squares slope of id on time.

    NearBlocks ids are a global sequence (all accounts) that grows roughly linearly in time (~45 ids/s on 2026-11-08),
    though not strictly monotonic within a block. None when fewer than two distinct timestamps or a non-positive slope.
    """
    pts = [(float(i), float(t) / 1e9) for i, t in points]
    if len({t for _, t in pts}) < 2:
        return None
    ids = np.array([i for i, _ in pts])
    ts = np.array([t for _, t in pts])
    slope = float(np.polyfit(ts - ts.mean(), ids - ids.mean(), 1)[0])
    return slope if math.isfinite(slope) and slope > 0 else None


def cursor_for_offset(top_id: int, ids_per_s: float, offset_s: float) -> int:
    """Id cursor expected to sit ``offset_s`` seconds before the receipt ``top_id`` (NearBlocks returns ids < cursor)."""
    return max(1, int(round(top_id - ids_per_s * offset_s)))


def _stratum_meta(k: int, name: str, txns: Sequence[Any], request: Mapping[str, Any], target_offset_s: float | None, top_ts: int | None) -> dict[str, Any]:
    ts = [t for t in (_raw_ts_ns(r) for r in txns) if t is not None]
    ids = [i for i in (_raw_id(r) for r in txns) if i is not None]
    return {
        "page": k, "name": name, "request": dict(request), "receipts": len(txns),
        "target_offset_s": target_offset_s,
        "offset_from_newest_s": (top_ts - max(ts)) / 1e9 if ts and top_ts is not None else None,
        "newest_utc": _ns_to_iso(max(ts)) if ts else None, "oldest_utc": _ns_to_iso(min(ts)) if ts else None,
        "span_s": (max(ts) - min(ts)) / 1e9 if ts else None,
        "id_range": [min(ids), max(ids)] if ids else None,
    }


async def _fetch_solver_strata(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str], *, pages: int, per_page: int, delay: float,
    target_span_s: float = SOLVER_SAMPLE_TARGET_SPAN_S, chunk: int = 0, window_s: float = NEARBLOCKS_RATE_WINDOW_S,
) -> dict[str, Any]:
    """Stratified-in-time execute_intents sample: page 1 (newest) plus pages at even time offsets back to ``target_span_s``.

    Order of calls: p1 (``page=1``); pK at the target depth via an id cursor aimed with the id/time slope of p1
    (``estimate_id_rate``); then the id/time slope is re-measured on the long p1..pK baseline and p2..p(K-1) are aimed
    at even offsets between p1 and the depth pK actually reached. Each page is recorded raw as
    ``txns:intents.near:execute_intents:pN`` and its rows are tagged ``valuo_stratum = "pN"`` (copies; the raw record is
    untouched). A failed deep page costs that stratum only; an unreachable host stops the walk. When p1 carries no usable
    ids/timestamps the walk falls back to NearBlocks' own cursor (contiguous pages) and says so.
    ``chunk`` > 0 paces the walk: after every ``chunk`` calls it waits until ``window_s`` has passed since the last call
    (NearBlocks' unauthenticated rate window); the waits are summed into ``pacing_wait_s``.
    Returns ``{"rows", "pages_ok", "strata", "design", "target_span_s", "ids_per_s", "pacing_wait_s"}``.
    """
    url = f"{config.NEARBLOCKS_API_BASE}/account/{SELF_ACCOUNT}/txns"
    out: dict[str, Any] = {"rows": [], "pages_ok": 0, "strata": [], "design": SAMPLE_DESIGN_STRATIFIED, "target_span_s": float(target_span_s),
                           "ids_per_s": None, "pacing_wait_s": 0.0}
    got: dict[int, list[Any]] = {}
    stop = False
    calls = 0
    last_call = time.monotonic()

    async def fetch(k: int, request: dict[str, Any], target_offset: float | None, top_ts: int | None) -> tuple[list[Any] | None, Any]:
        nonlocal stop, calls, last_call
        if chunk > 0 and calls and calls % chunk == 0:
            wait = max(0.0, last_call + window_s - time.monotonic())
            out["pacing_wait_s"] += wait
            await asyncio.sleep(wait)
        calls += 1
        name = f"txns:{SELF_ACCOUNT}:{_EXECUTE_INTENTS}:p{k}"
        parsed, rec = await fetch_json(
            client, ledger, source="nearblocks", name=name, method="GET", url=url,
            params={"per_page": per_page, "method": _EXECUTE_INTENTS, **request}, headers=config.nearblocks_headers(), **_NEARBLOCKS_RETRY_KW,
        )
        last_call = time.monotonic()
        txns = _get(parsed, "txns") if rec.ok else None
        if not isinstance(txns, list) or not txns:
            reason = f"failed ({rec.error})" if not rec.ok else "returned no receipts"
            if rec.http_status is None:
                reason += "; NearBlocks unreachable, remaining pages skipped"
                stop = True
            warnings.append(f"nearblocks {_EXECUTE_INTENTS} txns page {k} {reason}; solver sample continues without this stratum")
            return None, parsed
        got[k] = [{**r, "valuo_stratum": f"p{k}"} if isinstance(r, Mapping) else r for r in txns]
        out["strata"].append(_stratum_meta(k, name, txns, request, target_offset, top_ts))
        return txns, parsed

    if pages <= 0:
        return out
    p1, parsed1 = await fetch(1, {"page": 1}, 0.0, None)
    if p1 is None:
        return out
    pts = [(i, t) for i, t in ((_raw_id(r), _raw_ts_ns(r)) for r in p1) if i is not None and t is not None]
    rate = estimate_id_rate(pts)
    top_id = max((i for i, _ in pts), default=None)
    top_ts = max((t for _, t in pts), default=None)
    out["strata"][0]["offset_from_newest_s"] = 0.0
    if pages > 1 and (rate is None or top_id is None or top_ts is None):
        # No id/time anchor: walk NearBlocks' own cursor (contiguous newest pages), as before the stratified design.
        out["design"] = SAMPLE_DESIGN_CONTIGUOUS
        warnings.append("nearblocks execute_intents page 1 carried no usable id/timestamp pairs; solver sample falls back to contiguous cursor pages")
        nxt = parsed1.get("cursor") if isinstance(parsed1, Mapping) else None
        for k in range(2, pages + 1):
            if stop or not isinstance(nxt, (str, int)) or not str(nxt):
                break
            await asyncio.sleep(delay)
            txns, parsed = await fetch(k, {"cursor": str(nxt)}, None, top_ts)
            if txns is None:
                break
            nxt = parsed.get("cursor") if isinstance(parsed, Mapping) else None
    elif pages > 1:
        offsets = plan_stratum_offsets(pages, target_span_s)
        floor_id = min(i for i, _ in pts)  # every deeper cursor stays below page 1, so strata never overlap it
        await asyncio.sleep(delay)
        deep_cursor = min(cursor_for_offset(top_id, rate, offsets[-1]), floor_id)
        deep, _ = await fetch(pages, {"cursor": str(deep_cursor)}, offsets[-1], top_ts)
        deep_pts = [(i, t) for i, t in ((_raw_id(r), _raw_ts_ns(r)) for r in deep or []) if i is not None and t is not None]
        if deep_pts:
            d_id, d_ts = max(deep_pts, key=lambda p: p[1])
            if top_ts > d_ts and top_id > d_id:
                rate = (top_id - d_id) / ((top_ts - d_ts) / 1e9)  # secant over hours: far less noisy than one page
                reached = (top_ts - d_ts) / 1e9
                offsets = [reached * k / (pages - 1) for k in range(pages)]
        for k in range(2, pages):
            if stop:
                break
            await asyncio.sleep(delay)
            await fetch(k, {"cursor": str(min(cursor_for_offset(top_id, rate, offsets[k - 1]), floor_id))}, offsets[k - 1], top_ts)
    out["ids_per_s"] = rate
    out["strata"].sort(key=lambda m: m["page"])
    out["rows"] = [r for k in sorted(got) for r in got[k]]
    out["pages_ok"] = len(got)
    return out


async def _fetch_nearblocks(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str], *, pages: int, per_page: int, delay: float,
    solver_pages: int = 0, solver_per_page: int = SOLVER_AUDIT_PER_PAGE, solver_out: dict[str, Any] | None = None,
    solver_target_span_s: float = SOLVER_SAMPLE_TARGET_SPAN_S,
) -> tuple[list[Any], int, int | None, Any, str | None]:
    """(rows, pages_ok, lifetime_receipts, stats_payload, last_error) with polite spacing between NearBlocks calls.

    The two single calls (lifetime count, network stats) go first: the paginated receipt walk is what
    exhausts the unauthenticated quota, and a 429 there should cost pages, not the singletons. A transport
    failure (``http_status`` None: refused connection, DNS, timeout) on the first call means the host is
    unreachable; the remaining calls are skipped so the fatal exit arrives in seconds. After the caller pages,
    ``solver_pages`` method-filtered pages (``?method=execute_intents``), stratified in time by ``_fetch_solver_strata``,
    feed the solver audit only; their rows, page count and per-page time ranges land in ``solver_out``. They are skipped when the caller walk already
    failed on an HTTP error (the quota is spent; the solver audit then uses the execute_intents in the caller pages).
    """
    errors: list[str] = []
    count_parsed, count_rec = await fetch_json(
        client, ledger, source="nearblocks", name=f"txns_count:{SELF_ACCOUNT}", method="GET",
        url=f"{config.NEARBLOCKS_API_BASE}/account/{SELF_ACCOUNT}/txns/count", headers=config.nearblocks_headers(),
        **_NEARBLOCKS_RETRY_KW,
    )
    count_rows = _get(count_parsed, "txns") if count_rec.ok else None
    first_row = count_rows[0] if isinstance(count_rows, list) and count_rows and isinstance(count_rows[0], Mapping) else None
    lifetime = _int(first_row.get("count")) if first_row is not None else None
    if lifetime is None:
        warnings.append(f"nearblocks txns/count unavailable ({count_rec.error or 'unexpected shape'}); lifetime_receipts null")
        errors.append(count_rec.error or "unexpected shape")
    if count_rec.http_status is None:
        warnings.append(f"nearblocks unreachable ({count_rec.error}); /stats and receipt pages skipped")
        return [], 0, lifetime, None, errors[-1] if errors else None
    await asyncio.sleep(delay)
    stats, stats_rec = await fetch_json(
        client, ledger, source="nearblocks", name="stats", method="GET",
        url=f"{config.NEARBLOCKS_API_BASE}/stats", headers=config.nearblocks_headers(),
        **_NEARBLOCKS_RETRY_KW,
    )
    if not stats_rec.ok:
        errors.append(stats_rec.error or "stats failed")
    if stats_rec.http_status is None:
        warnings.append(f"nearblocks unreachable ({stats_rec.error}); receipt pages skipped")
        return [], 0, lifetime, None, errors[-1]
    await asyncio.sleep(delay)
    n_err = len(errors)
    rows, pages_ok = await _fetch_nearblocks_pages(client, ledger, warnings, pages=pages, per_page=per_page, delay=delay, errors=errors)
    t_last = time.monotonic()
    if solver_out is not None:
        solver_out.update({"rows": [], "pages_ok": 0, "pages_requested": solver_pages, "per_page": solver_per_page, "skipped_reason": None})
        if solver_pages > 0 and len(errors) > n_err and pages_ok < pages:
            solver_out["skipped_reason"] = f"caller page walk failed ({errors[-1]}); method-filtered execute_intents pages skipped"
            warnings.append(f"nearblocks: {solver_out['skipped_reason']}; solver audit uses the execute_intents receipts in the caller pages only")
        elif solver_pages > 0:
            # Unauthenticated NearBlocks allows ~NEARBLOCKS_FREE_CALLS_PER_WINDOW calls per rolling minute (2026-11-08: 10 calls
            # in 9 s were served, the 11th answered 429 for the next 45 s). When the caller walk already used the budget, wait
            # for the window to roll past the LAST caller call instead of burning the retry ladder, then walk the solver
            # pages in chunks of NEARBLOCKS_SOLVER_CALLS_PER_CHUNK. Skipped with an API key or when pacing is off (delay 0).
            used = 2 + pages_ok + (1 if pages_ok < pages else 0)
            paced = delay > 0 and not config.NEARBLOCKS_API_KEY
            wait = 0.0
            if paced and used + solver_pages > NEARBLOCKS_FREE_CALLS_PER_WINDOW:
                wait = max(0.0, t_last + NEARBLOCKS_RATE_WINDOW_S - time.monotonic())
            await asyncio.sleep(max(delay, wait))
            # Solver-page failures are not fatal and do not set last_error (the caller sample is what the HHI_external needs).
            strata = await _fetch_solver_strata(
                client, ledger, warnings, pages=solver_pages, per_page=solver_per_page, delay=delay, target_span_s=solver_target_span_s,
                chunk=NEARBLOCKS_SOLVER_CALLS_PER_CHUNK if paced else 0,
            )
            solver_out.update(strata)
            solver_out["rate_window_wait_s"] = round(wait + strata["pacing_wait_s"], 1)
    return rows, pages_ok, lifetime, (stats if stats_rec.ok else None), (errors[-1] if errors else None)


# ----------------------------------------------------------------------------- assembly
def _assemble(
    *,
    summary: Any,
    price_points: Any,
    llama: Mapping[str, Any],
    rows: list[Any],
    pages_ok: int,
    pages_requested: int,
    per_page: int,
    lifetime: int | None,
    stats: Any,
    warnings: list[str],
    fetched_at: str,
    price_source: str = "nearstats:price-history",
    nearblocks_error: str | None = None,
    solver_sample: Mapping[str, Any] | None = None,
    boundary: Mapping[str, Any] | None = None,
) -> IntentsForensics:
    volume = extract_volume(summary, llama.get("dexs"), warnings)
    metrics = extract_protocol_metrics(summary, warnings)
    metrics = apply_onchain_tvl(metrics, boundary)
    volume = confidential_split_guard(volume, summary, metrics, warnings, boundary=boundary)
    price = extract_price(summary, stats, warnings)
    fees = fee_metrics(
        llama.get("fees"), llama.get("revenue"), llama.get("holders"), llama.get("dexs"),
        nearstats_volume_30d=volume["30d"], nearstats_public_30d=volume["public30d"], warnings=warnings,
    )
    fees["cumulative_fees_nearstats_usd"] = metrics["cumulative_fees_nearstats_usd"]
    # The fetch step already warned when the price series is missing; pass a throwaway list to avoid a duplicate.
    volatility = price_volatility(price_points, warnings, source=price_source) if price_points else price_volatility([], [], source=price_source)
    dexs = llama.get("dexs")
    volatility.update(volume_volatility(_get(dexs, "totalDataChart") if dexs else None, warnings=warnings))
    conc = caller_concentration(rows, SELF_ACCOUNT, warnings)
    if conc["hhi_external"] is None:
        detail = f"; last NearBlocks error: {nearblocks_error}" if nearblocks_error else ""
        raise IntentsForensicsError(
            f"no external intents.near callers sampled ({conc['receipts_sampled']} receipts over {pages_ok} page(s)); HHI undefined{detail}"
        )
    if volume["30d"] is None:
        raise IntentsForensicsError("30d intents volume unavailable from nearstats and DefiLlama")
    solver_sample = dict(solver_sample or {})
    solver_rows = list(solver_sample.get("rows") or [])
    strata_meta = list(solver_sample.get("strata") or [])
    # The caller pages are the newest receipts, fetched a minute before solver page 1: they belong to the newest stratum.
    caller_rows = [{**r, "valuo_stratum": "p1"} if isinstance(r, Mapping) else r for r in rows] if strata_meta else rows
    solvers = solver_concentration(caller_rows + solver_rows, warnings)
    offsets = [m["offset_from_newest_s"] for m in strata_meta if m.get("offset_from_newest_s") is not None]
    gaps = [b - a for a, b in zip(sorted(offsets), sorted(offsets)[1:])]
    covered = sum(m["span_s"] or 0.0 for m in strata_meta)
    span = solvers.get("sample_span_s")
    solvers["sample"] = {
        "design": solver_sample.get("design") if strata_meta else None,
        "caller_page_receipts": len(rows),
        "execute_intents_pages_requested": solver_sample.get("pages_requested", 0),
        "execute_intents_pages_ok": solver_sample.get("pages_ok", 0),
        "execute_intents_per_page": solver_sample.get("per_page"),
        "execute_intents_page_receipts": len(solver_rows),
        "execute_intents_pages_skipped_reason": solver_sample.get("skipped_reason"),
        "rate_window_wait_s": solver_sample.get("rate_window_wait_s"),
        "pages_fetched": [m["page"] for m in strata_meta],
        "target_span_s": solver_sample.get("target_span_s"),
        "time_range_utc": solvers.get("sample_time_range_utc"),
        "span_s": span,
        "stride_s_median": float(np.median(gaps)) if gaps else None,
        "covered_s": covered if strata_meta else None,
        "coverage_share": (covered / span) if strata_meta and span else None,
        "ids_per_s": solver_sample.get("ids_per_s"),
        "strata": strata_meta,
        "note": (
            "solver audit = execute_intents receipts from the caller pages plus NearBlocks' method-filtered list "
            "(?method=execute_intents), de-duplicated by receipt id. design stratified_time_sample: page 1 is the newest page; "
            "pages 2..K are reached by jumping NearBlocks' id cursor to even time offsets back to target_span_s (cursor aimed "
            "with the measured ids-per-second slope), so the sample is K short windows (~45 s each) spread over hours, not one "
            "contiguous window; coverage_share = summed page windows / total span. Caller-page receipts are assigned to "
            "stratum p1 (same newest window). hhi_solver_ci90 resamples whole pages (block bootstrap)"
        ),
    }
    return IntentsForensics(
        volume=volume,
        fees=fees,
        confidential_tvl_usd=metrics["confidential_tvl_usd"],
        confidential_tvl_verified=metrics["confidential_tvl_verified"],
        unique_users_7d=metrics["unique_users_7d"],
        price=price,
        volatility=volatility,
        callers=conc["callers"],
        hhi_external=conc["hhi_external"],
        n_eff_external=conc["n_eff_external"],
        hhi_all=conc["hhi_all"],
        ai_agent_share=conc["ai_agent_share"],
        bridge_share=conc["bridge_share"],
        method_mix=conc["method_mix"],
        receipts_sampled=conc["receipts_sampled"],
        pages_fetched=pages_ok,
        lifetime_receipts=lifetime,
        sample_block_range=conc["sample_block_range"],
        explorer_base=EXPLORER_BASE,
        # extras (OpenModel keeps them)
        fetched_at_utc=fetched_at,
        nearstats_generated_at=_get(summary, "generatedAt"),
        confidential_tvl_source_status=metrics["confidential_tvl_source_status"],
        confidential_tvl_warnings=metrics["confidential_tvl_warnings"],
        confidential_tvl_reported_usd=metrics.get("confidential_tvl_reported_usd"),
        confidential_tvl_reported_status=metrics.get("confidential_tvl_reported_status"),
        confidential_boundary=dict(boundary) if boundary else None,
        top_swaps=extract_top_swaps(summary),
        solver_concentration=solvers,
        caller_sample={
            "account": SELF_ACCOUNT, "pages_requested": pages_requested, "per_page": per_page,
            "external_receipts_sampled": conc["external_receipts_sampled"], "unique_external_callers": conc["unique_external_callers"],
            "hhi_external_ex_ai_agent": conc["hhi_external_ex_ai_agent"], "n_eff_external_ex_ai_agent": conc["n_eff_external_ex_ai_agent"],
            "hhi_external_ci90": conc["hhi_external_ci90"], "n_eff_external_ci90": conc["n_eff_external_ci90"],
            "hhi_external_ex_ai_agent_ci90": conc["hhi_external_ex_ai_agent_ci90"],
            "bootstrap_draws": conc["bootstrap_draws"], "bootstrap_method": conc["bootstrap_method"],
            "hhi_external_meaning": "deposit-source concentration (external predecessors: bridge token-contract callbacks, direct callers); not solver concentration",
            "execute_intents_by_predecessor_class": conc["execute_intents_by_predecessor_class"],
            "class_counts": conc["class_counts"], "class_share_external": conc["class_share_external"],
            "sample_time_range_utc": conc["sample_time_range_utc"], "sample_span_s": conc["sample_span_s"],
            "classification_note": (
                "system and intents.near self-receipts excluded from external shares; *.omft.near / *.omni.hot.tg = bridge "
                "token contracts; *.ai.near / *.agent.near = AI agents BY NAME SUFFIX ONLY (escrow.ai.near is a plain account "
                "with no contract; the label is a heuristic, not a verified classification); 64-hex / 0x40-hex = implicit "
                "accounts; a predecessor whose receipt is ft_on_transfer is a NEP-141 token contract and is reported as "
                "bridge_relayer. execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter "
                "the external HHI; solver concentration is in solver_concentration"
            ),
        },
        source_status={
            "nearstats_summary": summary is not None,
            "nearstats_price_history": bool(price_points) and price_source.startswith("nearstats"),
            "price_series_source": price_source if price_points else None,
            "defillama_fees": llama.get("fees") is not None, "defillama_revenue": llama.get("revenue") is not None,
            "defillama_holders_revenue": llama.get("holders") is not None, "defillama_dexs": llama.get("dexs") is not None,
            "nearblocks_pages_ok": pages_ok, "nearblocks_count": lifetime is not None, "nearblocks_stats": stats is not None,
            "nearblocks_execute_intents_pages_ok": solver_sample.get("pages_ok", 0),
        },
        warnings=list(warnings),
    )


async def collect_intents_forensics_async(
    ledger: ProvenanceLedger,
    *,
    client: httpx.AsyncClient | None = None,
    nearblocks_pages: int = 4,
    per_page: int = 25,
    page_delay_s: float | None = None,
    solver_pages: int | None = None,
    solver_target_span_s: float | None = None,
    confidential_boundary: bool = True,
) -> IntentsForensics:
    """Fetch nearstats, DefiLlama, NearBlocks and the confidential treasury (NEAR RPC) concurrently (NearBlocks pages sequential, spaced) and assemble.

    ``solver_pages`` (default ``SOLVER_AUDIT_PAGES``: registry solver_sample_pages, env VALUO_NEARBLOCKS_SOLVER_PAGES)
    method-filtered execute_intents pages of ``SOLVER_AUDIT_PER_PAGE`` rows are fetched after the caller pages for the
    solver audit, stratified in time back to ``solver_target_span_s`` (default registry solver_sample_target_span_s).

    ``page_delay_s`` defaults to ``config.NEARBLOCKS_PAGE_DELAY_S`` (VALUO_NEARBLOCKS_PAGE_DELAY_S, 0.8 s);
    tests pass 0. Every warning is also pushed to ``ledger.warn`` prefixed with ``intents_forensics:`` so it
    reaches ``Snapshot.warnings``.
    """
    delay = config.NEARBLOCKS_PAGE_DELAY_S if page_delay_s is None else max(0.0, page_delay_s)
    n_solver_pages = SOLVER_AUDIT_PAGES if solver_pages is None else max(0, int(solver_pages))
    solver_sample: dict[str, Any] = {}
    warnings: list[str] = []
    fetched_at = utc_now_iso()
    own_client = client is None
    client = client or httpx.AsyncClient(follow_redirects=True, timeout=config.HTTP_TIMEOUT_S)
    try:
        (summary, points, price_source), llama, (rows, pages_ok, lifetime, stats, nb_error), boundary = await asyncio.gather(
            _fetch_nearstats(client, ledger, warnings),
            _fetch_defillama(client, ledger),
            _fetch_nearblocks(
                client, ledger, warnings, pages=nearblocks_pages, per_page=per_page, delay=delay,
                solver_pages=n_solver_pages, solver_out=solver_sample,
                solver_target_span_s=SOLVER_SAMPLE_TARGET_SPAN_S if solver_target_span_s is None else float(solver_target_span_s),
            ),
            _fetch_confidential_boundary(client, ledger, warnings, enabled=confidential_boundary),
        )
    finally:
        if own_client:
            await client.aclose()
    try:
        result = _assemble(
            summary=summary, price_points=points, llama=llama, rows=rows, pages_ok=pages_ok, pages_requested=nearblocks_pages,
            per_page=per_page, lifetime=lifetime, stats=stats, warnings=warnings, fetched_at=fetched_at,
            price_source=price_source, nearblocks_error=nb_error, solver_sample=solver_sample, boundary=boundary,
        )
    finally:
        # Flushed even when assembly raises, so a fatal exit still carries the collector's diagnostics.
        for message in warnings:
            ledger.warn(f"intents_forensics: {message}")
    return result


def collect_intents_forensics(
    ledger: ProvenanceLedger,
    *,
    nearblocks_pages: int = 4,
    per_page: int = 25,
    page_delay_s: float | None = None,
    solver_pages: int | None = None,
    solver_target_span_s: float | None = None,
) -> IntentsForensics:
    """Synchronous entrypoint (runs the async collector in a fresh event loop).

    Use ``collect_intents_forensics_async`` from inside an already-running loop (``reproduce.py`` runs the
    three API collectors concurrently).
    """
    return asyncio.run(
        collect_intents_forensics_async(
            ledger, nearblocks_pages=nearblocks_pages, per_page=per_page, page_delay_s=page_delay_s, solver_pages=solver_pages,
            solver_target_span_s=solver_target_span_s,
        )
    )
