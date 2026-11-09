"""NEAR mainnet on-chain truth: supply, protocol parameters, stake, realized issuance, storage sinks.

Entry point: ``collect_near_rpc(ledger, *, use_archival=True) -> NearOnchainTruth`` (sync wrapper around
``collect_near_rpc_async``). Every number comes from JSON-RPC responses recorded in the ledger; nothing
is substituted when a call fails (the field is ``None`` and a warning is recorded on the ledger and in
the ``warnings`` extra field of the returned model).

Method (docs/LIVE_ENDPOINT_FACTS.md section 1, docs/MODEL_DESIGN.md section 4.1):

1. ``block`` (final) -> height, hash, timestamp (ns), ``total_supply`` (yoctoNEAR), ``gas_price``.
2. ``EXPERIMENTAL_protocol_config`` -> ``max_inflation_rate`` [num, den], ``protocol_reward_rate`` [num, den]
   (treasury share; live 0), ``runtime_config.storage_amount_per_byte`` (yocto/byte), ``num_blocks_per_year``,
   ``epoch_length`` (blocks), ``protocol_version``.
3. ``validators`` [null] -> active validator count, sum of ``stake``, ``epoch_start_height``, ``epoch_height``.
4. ``query`` view_account for each tracked sink. ``storage_locked_near = storage_usage * storage_amount_per_byte / 1e24``;
   ``has_contract = code_hash != "11111111111111111111111111111111"``. Missing accounts are skipped and listed.
5. Realized issuance. nearcore mints the epoch reward in the first block of each epoch, so
   ``minted_per_epoch = total_supply(epoch_start) - total_supply(epoch_start - 1)``. The previous epoch start
   is located at ``epoch_start_height - epoch_length`` (walking back along ``prev_hash`` if that height falls
   inside the previous epoch or was skipped) and confirmed by an ``epoch_id`` change versus its predecessor.
   ``epoch_duration_hours = (ts(epoch_start) - ts(prev_epoch_start)) / 3.6e12``;
   ``epochs_per_year = 365.25 * 24 / epoch_duration_hours``;
   ``net_burn_per_epoch = total_supply(epoch_start - 1) - total_supply(prev_epoch_start)`` (within-epoch drift,
   negative = gas burned); ``implied_annual_issuance = minted_per_epoch * epochs_per_year``;
   ``implied_annual_inflation_rate = implied_annual_issuance / total_supply``;
   ``nominal_annual_issuance = max_inflation_rate * total_supply``.
6. Storage growth (archival). For ``intents.near`` and ``aurora``: ``view_account`` at the blocks closest to
   now - 7 d and now - 30 d (heights estimated from the measured average block time, then the real block
   timestamps are fetched), OLS slope of bytes on days over the available points;
   ``growth_locked_near_per_day = growth_bytes_per_day * storage_amount_per_byte / 1e24``.
7. Derived: ``staked_supply_ratio = total_staked / total_supply``;
   ``nominal_staking_apr = inflation * (1 - protocol_reward_rate) / staked_supply_ratio`` at the live cap and at
   the SVRN target from ``valuo.assumptions``; ``gross_daily_issuance = total_supply * rate / 365.25``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import threading
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from valuo import assumptions, config
from valuo.provenance import FetchError, ProvenanceLedger, RawRecord, near_rpc_call
from valuo.schemas import (
    ContractSinkSnapshot,
    EpochIssuanceMeasurement,
    NearOnchainTruth,
)

__all__ = [
    "BlockHeader", "ProtocolParams", "ValidatorSet", "AccountState",
    "TRACKED_SINKS", "GROWTH_SINKS", "DEFAULT_LOOKBACK_DAYS", "NO_CONTRACT_CODE_HASH",
    "yocto_to_near", "ratio", "ns_to_iso", "parse_block", "parse_protocol_config", "parse_validators",
    "parse_view_account", "has_contract", "storage_locked_near", "storage_near_per_kb", "sink_snapshot",
    "epoch_jump_near", "is_epoch_first_block", "classify_candidate", "measure_epoch_issuance",
    "fit_growth_bytes_per_day", "apply_growth", "staking_apr", "daily_issuance_near", "assemble_truth",
    "collect_near_rpc", "collect_near_rpc_async",
]

YOCTO_PER_NEAR = 10**24
NO_CONTRACT_CODE_HASH = "11111111111111111111111111111111"
HOURS_PER_YEAR = 365.25 * 24.0
DAYS_PER_YEAR = 365.25
NS_PER_HOUR = 3_600_000_000_000
NS_PER_DAY = 86_400_000_000_000
# "1 NEAR per 100 KB" uses decimal kilobytes (1e5 bytes), matching the NEP storage-staking convention.
BYTES_PER_KB = 1000

# (account_id, label). Storage locks are state sinks for all of them; wrap.near's *balance* is user deposits.
TRACKED_SINKS: tuple[tuple[str, str], ...] = (
    ("intents.near", "NEAR Intents clearinghouse (Defuse verifier contract)"),
    ("aurora", "Aurora EVM engine"),
    ("wrap.near", "wNEAR wrapper (balance is user deposits; only the storage lock is a sink)"),
    ("v1.signer", "Chain Signatures MPC coordinator"),
    ("escrow.ai.near", "NEAR AI escrow (plain account; a caller of intents.near, not a contract sink)"),
    ("treasury.near", "Protocol treasury (receives protocol_reward_rate share of issuance)"),
    ("meme-cooking.near", "meme.cooking launchpad"),
    # QUANT_PIPELINE_SPEC lists ref-finance-101.near, which does not exist on mainnet (RPC UNKNOWN_ACCOUNT);
    # the live Ref Finance AMM contract is v2.ref-finance.near.
    ("v2.ref-finance.near", "Ref Finance AMM (v2)"),
)
# Sinks whose storage growth is measured from archival state (kept to two to bound archival calls).
GROWTH_SINKS: tuple[str, ...] = ("intents.near", "aurora")
# Measurement windows for the storage-growth fit (methodology parameter, not a model assumption).
DEFAULT_LOOKBACK_DAYS: tuple[float, ...] = (7.0, 30.0)
# Bounded searches: epoch boundary (heights can be skipped) and lookback blocks (skipped heights).
EPOCH_SEARCH_STEPS = 8
HEIGHT_SEARCH_RADIUS = 3
MAX_CONCURRENCY = 6


# ============================================================================ parsed RPC shapes
@dataclass(frozen=True)
class BlockHeader:
    height: int
    hash: str
    prev_hash: str
    epoch_id: str
    next_epoch_id: str
    timestamp_ns: int
    total_supply_yocto: int
    gas_price_yocto: int


@dataclass(frozen=True)
class ProtocolParams:
    max_inflation_rate: float
    protocol_reward_rate: float
    storage_amount_per_byte_yocto: int
    num_blocks_per_year: int
    epoch_length_blocks: int
    protocol_version: int
    protocol_treasury_account: str | None


@dataclass(frozen=True)
class ValidatorSet:
    active_validator_count: int
    total_staked_yocto: int
    epoch_start_height: int
    epoch_height: int | None


@dataclass(frozen=True)
class AccountState:
    account_id: str
    amount_yocto: int
    locked_yocto: int
    storage_usage: int
    code_hash: str
    block_height: int
    block_hash: str


# ============================================================================ pure conversions
def yocto_to_near(value: int | str) -> float:
    """``int(value) / 1e24`` with exact integer parsing (strings are yoctoNEAR decimals)."""
    return int(value) / YOCTO_PER_NEAR


def ratio(pair: Sequence[int]) -> float:
    """nearcore rational ``[numerator, denominator]`` -> float (``[1, 40]`` -> 0.025)."""
    num, den = int(pair[0]), int(pair[1])
    if den == 0:
        raise ValueError(f"rational with zero denominator: {list(pair)}")
    return num / den


def ns_to_iso(timestamp_ns: int) -> str:
    """Nanosecond unix timestamp -> ISO-8601 UTC with millisecond precision and Z suffix."""
    seconds, remainder_ns = divmod(int(timestamp_ns), 1_000_000_000)
    base = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return base.strftime("%Y-%m-%dT%H:%M:%S") + f".{remainder_ns // 1_000_000:03d}Z"


def parse_block(result: dict[str, Any]) -> BlockHeader:
    """``block`` result -> BlockHeader. ``timestamp_nanosec`` (string) is preferred over ``timestamp``."""
    header = result["header"]
    ts = header.get("timestamp_nanosec")
    return BlockHeader(
        height=int(header["height"]),
        hash=str(header["hash"]),
        prev_hash=str(header["prev_hash"]),
        epoch_id=str(header["epoch_id"]),
        next_epoch_id=str(header["next_epoch_id"]),
        timestamp_ns=int(ts) if ts is not None else int(header["timestamp"]),
        total_supply_yocto=int(header["total_supply"]),
        gas_price_yocto=int(header["gas_price"]),
    )


def parse_protocol_config(result: dict[str, Any]) -> ProtocolParams:
    """``EXPERIMENTAL_protocol_config`` result -> ProtocolParams (rationals converted to floats)."""
    runtime = result.get("runtime_config") or {}
    return ProtocolParams(
        max_inflation_rate=ratio(result["max_inflation_rate"]),
        protocol_reward_rate=ratio(result["protocol_reward_rate"]),
        storage_amount_per_byte_yocto=int(runtime["storage_amount_per_byte"]),
        num_blocks_per_year=int(result["num_blocks_per_year"]),
        epoch_length_blocks=int(result["epoch_length"]),
        protocol_version=int(result["protocol_version"]),
        protocol_treasury_account=result.get("protocol_treasury_account"),
    )


def parse_validators(result: dict[str, Any]) -> ValidatorSet:
    """``validators`` result -> count of ``current_validators``, their summed stake, and the epoch anchor."""
    current = result.get("current_validators") or []
    epoch_height = result.get("epoch_height")
    return ValidatorSet(
        active_validator_count=len(current),
        total_staked_yocto=sum(int(v["stake"]) for v in current),
        epoch_start_height=int(result["epoch_start_height"]),
        epoch_height=int(epoch_height) if epoch_height is not None else None,
    )


def parse_view_account(result: dict[str, Any], account_id: str) -> AccountState:
    """``query`` view_account result -> AccountState (``amount`` liquid, ``locked`` staked, bytes used)."""
    return AccountState(
        account_id=account_id,
        amount_yocto=int(result["amount"]),
        locked_yocto=int(result.get("locked") or 0),
        storage_usage=int(result["storage_usage"]),
        code_hash=str(result.get("code_hash") or NO_CONTRACT_CODE_HASH),
        block_height=int(result["block_height"]),
        block_hash=str(result.get("block_hash") or ""),
    )


def has_contract(code_hash: str) -> bool:
    """An account holds contract code unless its code hash is the all-ones (empty) hash."""
    return bool(code_hash) and code_hash != NO_CONTRACT_CODE_HASH


def storage_locked_near(storage_bytes: int, storage_amount_per_byte_yocto: int) -> float:
    """NEP storage staking: ``bytes * storage_amount_per_byte / 1e24`` NEAR (integer product, then scaled)."""
    return int(storage_bytes) * int(storage_amount_per_byte_yocto) / YOCTO_PER_NEAR


def storage_near_per_kb(storage_amount_per_byte_yocto: int) -> float:
    """NEAR locked per decimal kilobyte: ``storage_amount_per_byte * 1000 / 1e24`` (1e19 yocto/byte -> 0.01)."""
    return storage_locked_near(BYTES_PER_KB, storage_amount_per_byte_yocto)


def sink_snapshot(state: AccountState, storage_amount_per_byte_yocto: int, label: str) -> ContractSinkSnapshot:
    """Account state -> ContractSinkSnapshot.

    ``liquid_balance_near = amount/1e24 - storage_locked_near`` (what the account could actually spend);
    ``total_balance_near = (amount + locked)/1e24``; ``staked_near = locked/1e24``.
    """
    locked = storage_locked_near(state.storage_usage, storage_amount_per_byte_yocto)
    amount = yocto_to_near(state.amount_yocto)
    staked = yocto_to_near(state.locked_yocto)
    return ContractSinkSnapshot(
        account_id=state.account_id,
        label=label,
        has_contract=has_contract(state.code_hash),
        storage_bytes=state.storage_usage,
        storage_locked_near=locked,
        liquid_balance_near=amount - locked,
        total_balance_near=amount + staked,
        staked_near=staked,
        code_hash=state.code_hash,
        state_block_height=state.block_height,
    )


# ============================================================================ epoch issuance (pure)
def epoch_jump_near(first_block: BlockHeader, predecessor: BlockHeader) -> float:
    """Supply minted at an epoch boundary: ``total_supply(first) - total_supply(predecessor)`` in NEAR."""
    return yocto_to_near(first_block.total_supply_yocto - predecessor.total_supply_yocto)


def is_epoch_first_block(block: BlockHeader, predecessor: BlockHeader) -> bool:
    """True when ``predecessor`` is the parent of ``block`` and the epoch id changes between them."""
    return predecessor.hash == block.prev_hash and block.epoch_id != predecessor.epoch_id


def classify_candidate(candidate: BlockHeader, predecessor: BlockHeader, prev_epoch_id: str, current_epoch_id: str) -> str:
    """Where does ``candidate`` sit relative to the previous epoch's first block?

    Returns ``"found"`` (first block of the previous epoch), ``"too_late"`` (inside the previous or the
    current epoch: walk back) or ``"too_early"`` (in an older epoch: step forward).
    """
    if candidate.epoch_id == current_epoch_id:
        return "too_late"
    if candidate.epoch_id != prev_epoch_id:
        return "too_early"
    if is_epoch_first_block(candidate, predecessor):
        return "found"
    return "too_late"


def measure_epoch_issuance(
    *,
    cur_start: BlockHeader,
    cur_pred: BlockHeader | None,
    prev_start: BlockHeader | None,
    prev_pred: BlockHeader | None,
    total_supply_near: float,
    max_inflation_rate: float,
) -> EpochIssuanceMeasurement:
    """Realized issuance from epoch-boundary supply jumps (see module docstring, step 5).

    The reward minted in ``cur_start`` pays for the epoch that just ended, whose wall time is
    ``ts(cur_start) - ts(prev_start)``; the two are therefore paired for the annualization.
    ``prev_minted_per_epoch_near`` (extra) is the jump at ``prev_start`` for a second, independent reading.
    """
    nominal = max_inflation_rate * total_supply_near
    minted = epoch_jump_near(cur_start, cur_pred) if cur_pred is not None else None
    duration_h = epochs_per_year = net_burn = implied = implied_rate = avg_block_time_s = prev_minted = None
    if prev_start is not None:
        duration_ns = cur_start.timestamp_ns - prev_start.timestamp_ns
        if duration_ns > 0 and cur_start.height > prev_start.height:
            duration_h = duration_ns / NS_PER_HOUR
            epochs_per_year = HOURS_PER_YEAR / duration_h
            avg_block_time_s = duration_ns / 1e9 / (cur_start.height - prev_start.height)
        if cur_pred is not None:
            net_burn = yocto_to_near(cur_pred.total_supply_yocto - prev_start.total_supply_yocto)
        if prev_pred is not None:
            prev_minted = epoch_jump_near(prev_start, prev_pred)
    if minted is not None and epochs_per_year is not None:
        implied = minted * epochs_per_year
        implied_rate = implied / total_supply_near if total_supply_near > 0 else None
    jumps = [
        {"height": b.height, "hash": b.hash, "minted_near": m}
        for b, m in ((cur_start, minted), (prev_start, prev_minted))
        if b is not None and m is not None
    ]
    note = (
        "minted_per_epoch = total_supply(epoch_start) - total_supply(epoch_start - 1), read from block headers at "
        f"height {cur_start.height}; epoch_duration = ts(epoch_start) - ts(prev_epoch_start); "
        "epochs_per_year = 365.25*24 / epoch_duration_hours; implied_annual = minted * epochs_per_year; "
        "net_burn = total_supply(epoch_start - 1) - total_supply(prev_epoch_start) (within-epoch drift); "
        "nominal_annual = max_inflation_rate * total_supply. nearcore scales the epoch reward by elapsed time and "
        "pays nothing to validators below the uptime threshold, so measured can sit below nominal."
    )
    return EpochIssuanceMeasurement(
        epoch_start_height=cur_start.height,
        epoch_start_hash=cur_start.hash,
        prev_epoch_start_height=prev_start.height if prev_start is not None else None,
        minted_per_epoch_near=minted,
        epoch_duration_hours=duration_h,
        epochs_per_year=epochs_per_year,
        net_burn_per_epoch_near=net_burn,
        implied_annual_issuance_near=implied,
        implied_annual_inflation_rate=implied_rate,
        nominal_annual_issuance_near=nominal,
        method_note=note,
        prev_minted_per_epoch_near=prev_minted,
        avg_block_time_s=avg_block_time_s,
        measured_minus_nominal_annual_near=(implied - nominal) if implied is not None else None,
        epoch_start_timestamp_utc=ns_to_iso(cur_start.timestamp_ns),
        prev_epoch_start_timestamp_utc=ns_to_iso(prev_start.timestamp_ns) if prev_start is not None else None,
        jumps=jumps,
    )


# ============================================================================ storage growth (pure)
def fit_growth_bytes_per_day(points: Sequence[tuple[float, int]]) -> tuple[float | None, float | None]:
    """OLS slope of storage bytes on time.

    ``points`` are ``(t_days, bytes)``; returns ``(bytes_per_day, window_days)`` with
    ``slope = sum((t - t_mean)(b - b_mean)) / sum((t - t_mean)^2)``, or ``(None, None)`` with fewer than two
    distinct timestamps. Two points reduce to ``delta_bytes / delta_days``.
    """
    if len(points) < 2:
        return None, None
    ts = [float(t) for t, _ in points]
    bs = [float(b) for _, b in points]
    window = max(ts) - min(ts)
    if window <= 0:
        return None, None
    n = len(ts)
    t_mean = sum(ts) / n
    b_mean = sum(bs) / n
    sxx = sum((t - t_mean) ** 2 for t in ts)
    sxy = sum((t - t_mean) * (b - b_mean) for t, b in zip(ts, bs, strict=True))
    return sxy / sxx, window


def apply_growth(
    sink: ContractSinkSnapshot, history: list[dict[str, Any]], storage_amount_per_byte_yocto: int
) -> ContractSinkSnapshot:
    """Attach ``history`` (entries with ``days_before_now`` and ``storage_bytes``) and the fitted growth.

    ``growth_locked_near_per_day = growth_bytes_per_day * storage_amount_per_byte / 1e24``.
    """
    ordered = sorted(history, key=lambda h: int(h["block_height"]))
    slope, window = fit_growth_bytes_per_day([(-float(h["days_before_now"]), int(h["storage_bytes"])) for h in ordered])
    locked_per_day = storage_locked_near(1, storage_amount_per_byte_yocto) * slope if slope is not None else None
    return sink.model_copy(
        update={
            "history": ordered,
            "growth_bytes_per_day": slope,
            "growth_locked_near_per_day": locked_per_day,
            "growth_window_days": window,
        }
    )


# ============================================================================ derived (pure)
def staking_apr(inflation_rate: float, treasury_share: float, staked_supply_ratio: float) -> float:
    """Nominal staking APR: ``inflation * (1 - treasury_share) / staked_supply_ratio``."""
    if staked_supply_ratio <= 0:
        raise ValueError("staked_supply_ratio must be positive")
    return inflation_rate * (1.0 - treasury_share) / staked_supply_ratio


def daily_issuance_near(total_supply_near: float, annual_rate: float) -> float:
    """Gross daily issuance at an annual rate: ``total_supply * rate / 365.25``."""
    return total_supply_near * annual_rate / DAYS_PER_YEAR


def assemble_truth(
    *,
    head: BlockHeader,
    proto: ProtocolParams,
    validators: ValidatorSet,
    sinks: list[ContractSinkSnapshot],
    epoch_issuance: EpochIssuanceMeasurement,
    rpc_endpoint_used: str,
    archival_available: bool,
    archival_attempted: bool,
    warnings: list[str],
    missing_accounts: list[str],
    svrn_target_inflation: float,
) -> NearOnchainTruth:
    """Combine parsed RPC pieces into the NearOnchainTruth contract (all derivations in one place)."""
    total_supply = yocto_to_near(head.total_supply_yocto)
    total_staked = yocto_to_near(validators.total_staked_yocto)
    staked_ratio = total_staked / total_supply
    measured_daily = (
        epoch_issuance.implied_annual_issuance_near / DAYS_PER_YEAR
        if epoch_issuance.implied_annual_issuance_near is not None
        else None
    )
    growth_values = [s.growth_locked_near_per_day for s in sinks if s.growth_locked_near_per_day is not None]
    return NearOnchainTruth(
        block_height=head.height,
        block_hash=head.hash,
        timestamp_ns=head.timestamp_ns,
        timestamp_utc=ns_to_iso(head.timestamp_ns),
        total_supply_near=total_supply,
        gas_price_yocto=head.gas_price_yocto,
        max_inflation_rate=proto.max_inflation_rate,
        protocol_reward_rate=proto.protocol_reward_rate,
        storage_amount_per_byte_yocto=proto.storage_amount_per_byte_yocto,
        storage_near_per_kb=storage_near_per_kb(proto.storage_amount_per_byte_yocto),
        num_blocks_per_year=proto.num_blocks_per_year,
        epoch_length_blocks=proto.epoch_length_blocks,
        protocol_version=proto.protocol_version,
        active_validator_count=validators.active_validator_count,
        total_staked_near=total_staked,
        staked_supply_ratio=staked_ratio,
        nominal_staking_apr_current=staking_apr(proto.max_inflation_rate, proto.protocol_reward_rate, staked_ratio),
        nominal_staking_apr_svrn_1_6=staking_apr(svrn_target_inflation, proto.protocol_reward_rate, staked_ratio),
        gross_daily_issuance_near=daily_issuance_near(total_supply, proto.max_inflation_rate),
        gross_daily_issuance_svrn_near=daily_issuance_near(total_supply, svrn_target_inflation),
        epoch_issuance=epoch_issuance,
        tracked_sinks=sinks,
        total_state_locked_near=sum(s.storage_locked_near for s in sinks),
        measured_state_lock_growth_near_per_day=sum(growth_values) if growth_values else None,
        rpc_endpoint_used=rpc_endpoint_used,
        archival_available=archival_available,
        # --- extras (OpenModel): kept out of the fixed contract but useful downstream ---
        archival_attempted=archival_attempted,
        measured_daily_issuance_near=measured_daily,
        epoch_height=validators.epoch_height,
        epoch_id=head.epoch_id,
        protocol_treasury_account=proto.protocol_treasury_account,
        svrn_target_inflation_used=svrn_target_inflation,
        measured_state_lock_growth_sinks=[s.account_id for s in sinks if s.growth_locked_near_per_day is not None],
        missing_accounts=missing_accounts,
        warnings=list(warnings),
    )


# ============================================================================ async fetch layer
class _Rpc:
    """Bounded-concurrency wrapper around ``near_rpc_call`` that remembers the records it produced."""

    def __init__(self, client: httpx.AsyncClient, ledger: ProvenanceLedger, concurrency: int = MAX_CONCURRENCY) -> None:
        self.client = client
        self.ledger = ledger
        self.semaphore = asyncio.Semaphore(concurrency)
        self.records: list[RawRecord] = []

    async def call(self, method: str, params: Any, name: str) -> tuple[Any | None, RawRecord]:
        async with self.semaphore:
            result, record = await near_rpc_call(self.client, self.ledger, method, params, name)
        self.records.append(record)
        return result, record

    def archival_ok(self) -> bool:
        return any(r.ok and r.source == "near_rpc_archival" for r in self.records)


def _view_account_params(account_id: str, block_id: int | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"request_type": "view_account", "account_id": account_id}
    if block_id is None:
        params["finality"] = "final"
    else:
        params["block_id"] = block_id
    return params


async def _fetch_block(rpc: _Rpc, block_id: int | str, name: str) -> tuple[BlockHeader | None, RawRecord]:
    result, record = await rpc.call("block", {"block_id": block_id}, name)
    return (parse_block(result) if result else None), record


async def _fetch_account(
    rpc: _Rpc, account_id: str, block_id: int | None = None
) -> tuple[AccountState | None, RawRecord]:
    name = f"view_account:{account_id}" if block_id is None else f"view_account:{account_id}@{block_id}"
    result, record = await rpc.call("query", _view_account_params(account_id, block_id), name)
    return (parse_view_account(result, account_id) if result else None), record


async def _fetch_predecessor(rpc: _Rpc, block: BlockHeader) -> BlockHeader | None:
    """Parent block by ``prev_hash`` (exact even when heights were skipped)."""
    pred, _ = await _fetch_block(rpc, block.prev_hash, f"block:pred_of:{block.height}")
    return pred


async def _find_prev_epoch_start(
    rpc: _Rpc, cur_start: BlockHeader, cur_pred: BlockHeader, epoch_length: int, warnings: list[str]
) -> tuple[BlockHeader | None, BlockHeader | None]:
    """Locate the previous epoch's first block and its predecessor.

    Epoch E+1 starts at the first block with height >= start(E) + epoch_length, so start(E-1) <= start(E) -
    epoch_length. Begin there; a skipped height or a block inside the previous epoch means walking back
    (by height, then along ``prev_hash``), bounded by EPOCH_SEARCH_STEPS.
    """
    prev_epoch_id = cur_pred.epoch_id
    height = cur_start.height - epoch_length
    direction = -1  # skipped heights are stepped over in the current search direction
    candidate: BlockHeader | None = None
    for _ in range(EPOCH_SEARCH_STEPS):
        if candidate is None:
            candidate, _ = await _fetch_block(rpc, height, f"block:{height}")
            if candidate is None:
                height += direction
                continue
        predecessor = await _fetch_predecessor(rpc, candidate)
        if predecessor is None:
            warnings.append(f"near_rpc: predecessor of block {candidate.height} unavailable; epoch search aborted")
            return None, None
        verdict = classify_candidate(candidate, predecessor, prev_epoch_id, cur_start.epoch_id)
        if verdict == "found":
            return candidate, predecessor
        if verdict == "too_late":
            candidate = predecessor  # walk back along prev_hash; exact even across skipped heights
            direction = -1
        else:
            direction = 1
            height = candidate.height + 1
            candidate = None
    warnings.append(
        f"near_rpc: previous epoch start not found within {EPOCH_SEARCH_STEPS} steps of height "
        f"{cur_start.height - epoch_length}; epoch duration and implied issuance are null"
    )
    return None, None


async def _fetch_block_near_height(rpc: _Rpc, height: int) -> BlockHeader | None:
    """Block at ``height`` or the nearest produced height within HEIGHT_SEARCH_RADIUS (skipped heights)."""
    offsets = [0] + [o for k in range(1, HEIGHT_SEARCH_RADIUS + 1) for o in (-k, k)]
    for offset in offsets:
        block, _ = await _fetch_block(rpc, height + offset, f"block:{height + offset}")
        if block is not None:
            return block
    return None


async def _measure_storage_growth(
    rpc: _Rpc,
    head: BlockHeader,
    current: dict[str, AccountState],
    avg_block_time_s: float,
    lookback_days: Sequence[float],
    warnings: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Historical ``view_account`` points for GROWTH_SINKS at ~now - d days for each d in ``lookback_days``."""
    targets = [head.height - round(d * 86400.0 / avg_block_time_s) for d in lookback_days]
    blocks = await asyncio.gather(*(_fetch_block_near_height(rpc, h) for h in targets))
    found: list[BlockHeader] = []
    for d, h, b in zip(lookback_days, targets, blocks, strict=True):
        if b is None:
            warnings.append(f"near_rpc: no block found near height {h} (~{d:g} d ago); lookback point dropped")
        else:
            found.append(b)
    sinks = [a for a in GROWTH_SINKS if a in current]
    states = await asyncio.gather(*(_fetch_account(rpc, a, b.height) for a in sinks for b in found))
    history: dict[str, list[dict[str, Any]]] = {}
    for account in sinks:
        state = current[account]
        history[account] = [_history_point(state.block_height, head.timestamp_ns, head.timestamp_ns, state.storage_usage)]
    for (account, block), (state, record) in zip(((a, b) for a in sinks for b in found), states, strict=True):
        if state is None:
            warnings.append(f"near_rpc: archival view_account {account}@{block.height} failed ({record.error}); point dropped")
            continue
        history[account].append(_history_point(block.height, block.timestamp_ns, head.timestamp_ns, state.storage_usage))
    return history


def _history_point(block_height: int, timestamp_ns: int, now_ns: int, storage_bytes: int) -> dict[str, Any]:
    return {
        "block_height": block_height,
        "timestamp_utc": ns_to_iso(timestamp_ns),
        "storage_bytes": storage_bytes,
        "days_before_now": (now_ns - timestamp_ns) / NS_PER_DAY,
    }


def _require(result: Any, record: RawRecord, what: str) -> Any:
    if result is None:
        raise FetchError(f"near_rpc {what} failed: {record.error or 'no result'} ({record.url})")
    return result


def _is_unknown_account(record: RawRecord) -> bool:
    return bool(record.error) and "UNKNOWN_ACCOUNT" in (record.error or "")


async def collect_near_rpc_async(
    ledger: ProvenanceLedger,
    *,
    use_archival: bool = True,
    client: httpx.AsyncClient | None = None,
    lookback_days: Sequence[float] = DEFAULT_LOOKBACK_DAYS,
) -> NearOnchainTruth:
    """Async implementation of ``collect_near_rpc`` (see module docstring for the method)."""
    own_client = client is None
    client = client or httpx.AsyncClient(follow_redirects=True)
    warnings: list[str] = []
    try:
        rpc = _Rpc(client, ledger)
        (block_res, block_rec), (proto_res, proto_rec), (val_res, val_rec) = await asyncio.gather(
            rpc.call("block", {"finality": "final"}, "block_final"),
            rpc.call("EXPERIMENTAL_protocol_config", {"finality": "final"}, "protocol_config"),
            rpc.call("validators", [None], "validators"),
        )
        head = parse_block(_require(block_res, block_rec, "block(final)"))
        proto = parse_protocol_config(_require(proto_res, proto_rec, "EXPERIMENTAL_protocol_config"))
        validators = parse_validators(_require(val_res, val_rec, "validators"))

        account_results, (cur_start, cur_start_rec) = await asyncio.gather(
            asyncio.gather(*(_fetch_account(rpc, account) for account, _ in TRACKED_SINKS)),
            _fetch_block(rpc, validators.epoch_start_height, f"block:{validators.epoch_start_height}"),
        )
        current: dict[str, AccountState] = {}
        missing: list[str] = []
        sinks: list[ContractSinkSnapshot] = []
        for (account, label), (state, record) in zip(TRACKED_SINKS, account_results, strict=True):
            if state is None:
                missing.append(account)
                kind = "does not exist (UNKNOWN_ACCOUNT)" if _is_unknown_account(record) else f"unavailable ({record.error})"
                warnings.append(f"near_rpc: account {account} {kind}; excluded from tracked sinks")
                continue
            current[account] = state
            sinks.append(sink_snapshot(state, proto.storage_amount_per_byte_yocto, label))

        epoch_issuance, avg_block_time_s = await _measure_issuance(rpc, head, proto, validators, cur_start, cur_start_rec, warnings)

        archival_attempted = use_archival
        if use_archival:
            sinks = await _attach_growth(rpc, head, proto, current, sinks, avg_block_time_s, lookback_days, warnings)
        else:
            warnings.append("near_rpc: archival lookback disabled; storage growth (state-lock sink) is null")

        for message in warnings:
            ledger.warn(message)
        return assemble_truth(
            head=head,
            proto=proto,
            validators=validators,
            sinks=sinks,
            epoch_issuance=epoch_issuance,
            rpc_endpoint_used=block_rec.url,
            archival_available=rpc.archival_ok(),
            archival_attempted=archival_attempted,
            warnings=warnings,
            missing_accounts=missing,
            svrn_target_inflation=assumptions.value("svrn_target_inflation"),
        )
    finally:
        if own_client:
            await client.aclose()


async def _measure_issuance(
    rpc: _Rpc,
    head: BlockHeader,
    proto: ProtocolParams,
    validators: ValidatorSet,
    cur_start: BlockHeader | None,
    cur_start_rec: RawRecord,
    warnings: list[str],
) -> tuple[EpochIssuanceMeasurement, float]:
    """Step 5: fetch the boundary blocks and measure; returns the measurement and a measured avg block time (s)."""
    total_supply = yocto_to_near(head.total_supply_yocto)
    if cur_start is None:
        warnings.append(
            f"near_rpc: epoch start block {validators.epoch_start_height} unavailable ({cur_start_rec.error}); "
            "realized issuance not measured, nominal only"
        )
        placeholder = BlockHeader(validators.epoch_start_height, "", "", head.epoch_id, head.next_epoch_id, head.timestamp_ns, head.total_supply_yocto, head.gas_price_yocto)
        measurement = measure_epoch_issuance(cur_start=placeholder, cur_pred=None, prev_start=None, prev_pred=None, total_supply_near=total_supply, max_inflation_rate=proto.max_inflation_rate)
        return measurement, _fallback_block_time(head, None)
    cur_pred = await _fetch_predecessor(rpc, cur_start)
    prev_start = prev_pred = None
    if cur_pred is None:
        warnings.append(f"near_rpc: predecessor of epoch start {cur_start.height} unavailable; minted_per_epoch is null")
    else:
        prev_start, prev_pred = await _find_prev_epoch_start(rpc, cur_start, cur_pred, proto.epoch_length_blocks, warnings)
    measurement = measure_epoch_issuance(
        cur_start=cur_start, cur_pred=cur_pred, prev_start=prev_start, prev_pred=prev_pred,
        total_supply_near=total_supply, max_inflation_rate=proto.max_inflation_rate,
    )
    avg_bt = getattr(measurement, "avg_block_time_s", None)
    return measurement, (avg_bt if avg_bt else _fallback_block_time(head, cur_start))


def _fallback_block_time(head: BlockHeader, anchor: BlockHeader | None) -> float:
    """Measured average block time from two fetched headers; used only to aim lookback heights."""
    if anchor is not None and head.height > anchor.height and head.timestamp_ns > anchor.timestamp_ns:
        return (head.timestamp_ns - anchor.timestamp_ns) / 1e9 / (head.height - anchor.height)
    return 0.0


async def _attach_growth(
    rpc: _Rpc,
    head: BlockHeader,
    proto: ProtocolParams,
    current: dict[str, AccountState],
    sinks: list[ContractSinkSnapshot],
    avg_block_time_s: float,
    lookback_days: Sequence[float],
    warnings: list[str],
) -> list[ContractSinkSnapshot]:
    """Step 6: archival lookback for GROWTH_SINKS; sinks without >= 2 points keep growth null."""
    if avg_block_time_s <= 0:
        warnings.append("near_rpc: no measured block time available to aim archival lookback; storage growth is null")
        return sinks
    history = await _measure_storage_growth(rpc, head, current, avg_block_time_s, lookback_days, warnings)
    out: list[ContractSinkSnapshot] = []
    for sink in sinks:
        points = history.get(sink.account_id)
        if points is None:
            out.append(sink)
            continue
        updated = apply_growth(sink, points, proto.storage_amount_per_byte_yocto)
        if updated.growth_bytes_per_day is None:
            warnings.append(f"near_rpc: fewer than two archival points for {sink.account_id}; storage growth is null")
        out.append(updated)
    return out


def _run_blocking(factory: Callable[[], Awaitable[NearOnchainTruth]]) -> NearOnchainTruth:
    """Run a coroutine to completion whether or not an event loop is already running in this thread."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["value"] = asyncio.run(factory())
        except BaseException as exc:  # re-raised in the caller's thread
            box["error"] = exc

    thread = threading.Thread(target=runner, name="valuo-near-rpc")
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["value"]


def collect_near_rpc(
    ledger: ProvenanceLedger,
    *,
    use_archival: bool = True,
    lookback_days: Sequence[float] = DEFAULT_LOOKBACK_DAYS,
) -> NearOnchainTruth:
    """Fetch NEAR mainnet on-chain truth (sync). Raises FetchError if block/protocol_config/validators fail.

    ``use_archival=False`` skips the historical storage lookback (growth fields null, warning recorded).
    """
    return _run_blocking(lambda: collect_near_rpc_async(ledger, use_archival=use_archival, lookback_days=lookback_days))


# ============================================================================ CLI smoke
def _summary_lines(truth: NearOnchainTruth) -> list[str]:
    ei = truth.epoch_issuance
    intents = next((s for s in truth.tracked_sinks if s.account_id == "intents.near"), None)

    def fmt(v: float | None, spec: str) -> str:
        return "null" if v is None else format(v, spec)

    lines = [
        f"block            {truth.block_height} {truth.block_hash} {truth.timestamp_utc} via {truth.rpc_endpoint_used}",
        f"total_supply     {truth.total_supply_near:,.2f} NEAR   staked {truth.total_staked_near:,.0f} ({truth.staked_supply_ratio:.2%}, {truth.active_validator_count} validators)",
        f"inflation cap    {truth.max_inflation_rate:.4f}  treasury share {truth.protocol_reward_rate:.3f}  nominal/day {truth.gross_daily_issuance_near:,.0f} NEAR",
        f"epoch start      {ei.epoch_start_height} (prev {ei.prev_epoch_start_height})  minted/epoch {fmt(ei.minted_per_epoch_near, ',.2f')} NEAR  "
        f"prev jump {fmt(getattr(ei, 'prev_minted_per_epoch_near', None), ',.2f')}",
        f"epoch duration   {fmt(ei.epoch_duration_hours, '.3f')} h  epochs/yr {fmt(ei.epochs_per_year, '.1f')}  net burn/epoch {fmt(ei.net_burn_per_epoch_near, ',.2f')} NEAR",
        f"implied annual   {fmt(ei.implied_annual_issuance_near, ',.0f')} NEAR = {fmt((ei.implied_annual_inflation_rate or 0) * 100 if ei.implied_annual_inflation_rate is not None else None, '.4f')} %  "
        f"(nominal {ei.nominal_annual_issuance_near:,.0f})",
        f"state locked     {truth.total_state_locked_near:,.2f} NEAR over {len(truth.tracked_sinks)} sinks; growth/day {fmt(truth.measured_state_lock_growth_near_per_day, ',.2f')} NEAR  archival ok={truth.archival_available}",
    ]
    if intents is not None:
        lines.append(
            f"intents.near     {intents.storage_bytes:,} bytes = {intents.storage_locked_near:,.2f} NEAR locked; "
            f"growth {fmt(intents.growth_bytes_per_day, ',.0f')} B/day = {fmt(intents.growth_locked_near_per_day, ',.3f')} NEAR/day "
            f"over {fmt(intents.growth_window_days, '.2f')} d ({len(intents.history)} points)"
        )
    for w in getattr(truth, "warnings", []) or []:
        lines.append(f"warning          {w}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m valuo.collectors.near_rpc [--no-archival] [--json]``: one live run with a console summary."""
    parser = argparse.ArgumentParser(description="Valuo NEAR RPC collector smoke run")
    parser.add_argument("--no-archival", action="store_true", help="skip the archival storage-growth lookback")
    parser.add_argument("--json", action="store_true", help="print the full NearOnchainTruth JSON after the summary")
    args = parser.parse_args(argv)
    config.ensure_artifact_dirs()
    ledger = ProvenanceLedger()
    truth = collect_near_rpc(ledger, use_archival=not args.no_archival)
    print("\n".join(_summary_lines(truth)))
    summary = ledger.summary()
    print(f"records          {summary['records']} ok={summary['ok']} failures={summary['failures']} sources={summary['sources']}")
    if args.json:
        print(json.dumps(truth.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
