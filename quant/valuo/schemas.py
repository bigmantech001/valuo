"""Snapshot schema: every pydantic model named in docs/MODEL_DESIGN.md section 2-3.

Field names are the contract shared by the Python collectors/models, the JSON artifacts and the
web terminal's TypeScript mirror (web/src/lib/types.ts). Add fields freely; never rename or
remove one. Collector/model outputs carry ``extra="allow"`` so implementers can attach
module-specific fields without editing this file. This module holds no logic (no hashing, no
fetching): it is pure shape.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"
PERCENTILE_KEYS: tuple[str, ...] = ("p10", "p25", "p50", "p75", "p90")

# Literal aliases (importable so collectors/models type their own helpers consistently).
AssumptionSource = Literal["assumption", "derived", "measured"]
VenueName = Literal["1click", "relay", "lifi", "across"]
QuoteStatus = Literal["ok", "no_liquidity", "unsupported_route", "error", "skipped"]
CorridorArchetype = Literal["cross_vm", "native_btc", "evm_l2", "native_zec"]
EngineKey = Literal["clearinghouse", "confidential", "monetary"]
EvidenceStatus = Literal["VERIFIED_ON_CHAIN", "VERIFIED_LIVE_API", "DERIVED", "ASSUMPTION", "NOT_SUPPORTED"]
RawSource = Literal[
    "near_rpc", "near_rpc_archival", "oneclick", "relay", "lifi", "across",
    "nearstats", "nearblocks", "defillama", "coingecko",
]


class OpenModel(BaseModel):
    """Base for collector/model outputs: unknown fields are kept, not dropped."""

    model_config = ConfigDict(extra="allow")


# ============================================================================ section 2: provenance
class RawRecord(BaseModel):
    """One HTTP/RPC exchange: what was asked, what came back, and the SHA-256 of the raw bytes."""

    source: str  # "near_rpc" | "near_rpc_archival" | "oneclick" | "relay" | "lifi" | "across" | "nearstats" | "nearblocks" | "defillama" | "coingecko"
    name: str  # e.g. "block_final", "quote:eth_usdc->sol_usdc:50000", "fees:near-intents:dailyRevenue"
    url: str
    method: str
    request_body_sha256: str | None = None
    http_status: int | None = None
    ok: bool
    error: str | None = None
    fetched_at_utc: str  # ISO-8601 Z
    latency_ms: float
    bytes: int
    sha256: str  # sha256 of the exact raw response bytes (sha256(b"") when nothing was received)
    raw_path: str | None = None  # artifacts/raw/... relative to repo root
    attempts: int = 1
    note: str | None = None  # e.g. "primary GARBAGE_COLLECTED_BLOCK; retried on archival"


# ============================================================================ section 3: contract
class Assumption(BaseModel):
    """A labeled input: the value, its plausible range, and why. Never presented as measured."""

    key: str
    value: float
    unit: str
    low: float
    high: float
    source: AssumptionSource
    justification: str


class EpochIssuanceMeasurement(OpenModel):
    epoch_start_height: int
    epoch_start_hash: str
    prev_epoch_start_height: int | None = None
    minted_per_epoch_near: float | None = None  # supply jump at epoch boundary
    epoch_duration_hours: float | None = None
    epochs_per_year: float | None = None
    net_burn_per_epoch_near: float | None = None  # within-epoch supply drift (negative = burn)
    implied_annual_issuance_near: float | None = None
    implied_annual_inflation_rate: float | None = None
    nominal_annual_issuance_near: float  # max_inflation_rate x total_supply
    method_note: str
    # Promoted collector extras (near_rpc): second independent boundary reading and timing detail.
    prev_minted_per_epoch_near: float | None = None
    avg_block_time_s: float | None = None
    measured_minus_nominal_annual_near: float | None = None
    epoch_start_timestamp_utc: str | None = None
    prev_epoch_start_timestamp_utc: str | None = None
    jumps: list[dict[str, Any]] = Field(default_factory=list)  # [{height, hash, minted_near}]


class ContractSinkSnapshot(OpenModel):
    account_id: str
    label: str
    has_contract: bool
    storage_bytes: int
    storage_locked_near: float
    liquid_balance_near: float
    total_balance_near: float
    staked_near: float
    history: list[dict[str, Any]] = Field(default_factory=list)  # [{block_height, timestamp_utc, storage_bytes, days_before_now}]
    growth_bytes_per_day: float | None = None
    growth_locked_near_per_day: float | None = None
    growth_window_days: float | None = None
    code_hash: str | None = None
    state_block_height: int | None = None


class NearOnchainTruth(OpenModel):
    block_height: int
    block_hash: str
    timestamp_ns: int
    timestamp_utc: str
    total_supply_near: float
    gas_price_yocto: int
    max_inflation_rate: float
    protocol_reward_rate: float
    storage_amount_per_byte_yocto: int
    storage_near_per_kb: float
    num_blocks_per_year: int
    epoch_length_blocks: int
    protocol_version: int
    active_validator_count: int
    total_staked_near: float
    staked_supply_ratio: float
    nominal_staking_apr_current: float  # max_inflation_rate x (1 - protocol_reward_rate) / staked_ratio
    nominal_staking_apr_svrn_1_6: float
    gross_daily_issuance_near: float
    gross_daily_issuance_svrn_near: float
    epoch_issuance: EpochIssuanceMeasurement
    tracked_sinks: list[ContractSinkSnapshot] = Field(default_factory=list)
    total_state_locked_near: float
    measured_state_lock_growth_near_per_day: float | None = None
    rpc_endpoint_used: str
    archival_available: bool
    # Promoted collector extras (near_rpc).
    warnings: list[str] = Field(default_factory=list)
    archival_attempted: bool = False
    measured_daily_issuance_near: float | None = None  # implied_annual_issuance_near / 365.25
    missing_accounts: list[str] = Field(default_factory=list)
    measured_state_lock_growth_sinks: list[str] = Field(default_factory=list)
    epoch_height: int | None = None
    epoch_id: str | None = None
    protocol_treasury_account: str | None = None
    svrn_target_inflation_used: float | None = None


class VenueQuote(OpenModel):
    venue: VenueName
    supported: bool
    status: QuoteStatus
    error_message: str | None = None
    amount_in_raw: str
    amount_in_usd: float | None = None
    amount_out_raw: str | None = None
    amount_out_formatted: float | None = None
    amount_out_usd: float | None = None
    friction_bps_usd: float | None = None  # (in_usd - out_usd) / in_usd x 1e4
    friction_bps_raw: float | None = None  # same-asset corridors only
    time_estimate_s: float | None = None
    route_tool: str | None = None
    fee_breakdown_usd: dict[str, float] = Field(default_factory=dict)
    latency_ms: float
    fetched_at_utc: str
    raw_record_sha256: str
    # Promoted collector extras (execution_bench): venue error code and a basis note (e.g. Across USD legs).
    error_code: str | None = None
    note: str | None = None
    routes_via_near_intents: bool = False  # LI.FI tool "near" resells NEAR Intents; not an independent price


class CorridorClipResult(OpenModel):
    corridor_id: str
    clip_usd: float
    quotes: list[VenueQuote] = Field(default_factory=list)
    best_competitor: str | None = None
    headroom_bps: float | None = None  # min competitor friction - 1click friction (positive = 1Click delivers more)
    oneclick_rank: int | None = None
    n_venues_ok: int = 0
    # Promoted collector extras (execution_bench).
    headroom_basis: str | None = None  # "dest_units": destination units out per unit in, no oracle (null when not comparable)
    archetype: str | None = None
    oneclick_friction_bps: float | None = None
    best_competitor_friction_bps: float | None = None
    n_competitors_ok: int = 0
    # The ONE price every venue's USD friction in this cell is valued at: {source, dest_price_usd, origin_price_usd, n_venue_oracles}
    # source = "oneclick_token_list_oracle" | "median_venue_oracle" | null (no USD valuation possible).
    price_basis: dict[str, Any] = Field(default_factory=dict)
    oneclick_amount_out_raw: str | None = None
    best_competitor_amount_out_raw: str | None = None
    venue_oracle_gap_bps: dict[str, float] = Field(default_factory=dict)
    oracle_gap_exceeds_headroom: bool | None = None


class Corridor(OpenModel):
    corridor_id: str
    label: str
    archetype: CorridorArchetype
    origin: dict[str, Any]
    destination: dict[str, Any]
    venues_attempted: list[str] = Field(default_factory=list)
    venues_declared_unsupported: dict[str, str] = Field(default_factory=dict)  # venue -> structural reason (not called)


class ExecutionBenchmark(OpenModel):
    ran_at_utc: str
    clips_usd: list[float]
    corridors: list[Corridor]
    results: list[CorridorClipResult]
    headroom_by_archetype_bps: dict[str, float | None] = Field(default_factory=dict)  # median headroom per archetype
    competitive_fee_ceiling_bps: float | None = None  # median competitor friction on cross_vm
    oneclick_1y_token_universe: int | None = None  # size of the live 1Click token list (null if the fetch failed)
    oneclick_blockchains: list[str] = Field(default_factory=list)
    summary_note: str = ""
    # Promoted collector extras (execution_bench).
    headroom_n_by_archetype: dict[str, int] = Field(default_factory=dict)
    competitive_fee_ceiling_n: int | None = None
    competitive_fee_ceiling_basis: str | None = None
    token_list_ok: bool | None = None
    token_list_sha256: str | None = None
    budget_s: float | None = None
    concurrency: int | None = None
    request_timeout_s: float | None = None
    elapsed_s: float | None = None
    n_quotes_ok: int | None = None


class CallerClass(str, Enum):
    ai_agent = "ai_agent"
    bridge_relayer = "bridge_relayer"
    implicit_account = "implicit_account"
    named_account = "named_account"
    self_internal = "self_internal"
    system = "system"


class CallerShare(OpenModel):
    account_id: str
    cls: CallerClass
    receipts: int
    share: float
    example_tx_hash: str | None = None


class IntentsForensics(OpenModel):
    volume: dict[str, Any]  # {allTimeUsd, 24h, 7d, 30d, public30d, confidential30d, confidential_share_30d, weekOverWeek, records}
    fees: dict[str, Any]  # {gross_fees_30d_usd, net_revenue_30d_usd, holders_revenue_30d_usd, gross_take_bps, net_take_bps, capture_ratio, cumulative_fees_usd, daily_series}
    confidential_tvl_usd: float | None = None
    confidential_tvl_verified: bool = False
    unique_users_7d: int | None = None
    price: dict[str, Any]  # {current_usd, fdv_usd, market_cap_usd, circulating_supply, total_supply, perf, ath_usd}
    volatility: dict[str, Any]  # {window, n_obs, daily_sigma, annualized_sigma, volume_daily_sigma, volume_annualized_sigma}
    callers: list[CallerShare] = Field(default_factory=list)
    hhi_external: float
    n_eff_external: float
    hhi_all: float
    ai_agent_share: float
    bridge_share: float
    method_mix: dict[str, int] = Field(default_factory=dict)
    receipts_sampled: int
    pages_fetched: int
    lifetime_receipts: int | None = None
    sample_block_range: list[int] = Field(default_factory=list)
    explorer_base: str = "https://nearblocks.io"
    # Promoted collector extras (intents_forensics).
    warnings: list[str] = Field(default_factory=list)
    fetched_at_utc: str | None = None
    nearstats_generated_at: str | None = None
    confidential_tvl_source_status: str | None = None
    confidential_tvl_warnings: list[str] = Field(default_factory=list)
    top_swaps: list[dict[str, Any]] = Field(default_factory=list)
    caller_sample: dict[str, Any] = Field(default_factory=dict)  # incl. hhi_external_ex_ai_agent, class_counts, sample span
    source_status: dict[str, Any] = Field(default_factory=dict)
    # Solver population (execute_intents NEP-413 signer payloads): {hhi_solver, n_eff_solver, n_fills, n_fills_attributed,
    # solvers: [{account_id, fills, share, example_tx_hash}], taker_class_mix, attribution_rules, method}. hhi_solver is
    # null when no fill could be attributed. hhi_external above is DEPOSIT/CALLER concentration, not solver concentration.
    solver_concentration: dict[str, Any] = Field(default_factory=dict)


class PeerComp(OpenModel):
    slug: str
    symbol: str
    fees_30d_usd: float | None = None
    revenue_30d_usd: float | None = None
    fees_1y_usd: float | None = None
    revenue_1y_usd: float | None = None
    fdv_usd: float | None = None
    market_cap_usd: float | None = None
    price_usd: float | None = None
    annualized_fees_usd: float | None = None
    annualized_revenue_usd: float | None = None
    fdv_to_fees: float | None = None
    fdv_to_revenue: float | None = None
    revenue_methodology: str | None = None
    # Promoted collector extras (comps).
    label: str | None = None
    coingecko_id: str | None = None
    fees_24h_usd: float | None = None
    revenue_24h_usd: float | None = None
    fees_7d_usd: float | None = None
    revenue_7d_usd: float | None = None
    price_source: str | None = None  # "coins.llama.fi" | "coingecko"
    fdv_source: str | None = None  # "coingecko" | None (and "nearstats" when reproduce.py backfills NEAR)
    mcap_to_fees: float | None = None
    mcap_to_revenue: float | None = None
    fees_methodology: str | None = None


class PeerComps(OpenModel):
    peers: list[PeerComp]
    near_combined: PeerComp
    median_fdv_to_revenue_ex_near: float | None = None
    median_fdv_to_fees_ex_near: float | None = None
    fetched_at_utc: str
    # Promoted collector extras (comps): NEAR rows kept out of ``peers`` so ex-NEAR medians stay unambiguous.
    near_components: list[PeerComp] = Field(default_factory=list)
    n_peers_in_revenue_median: int | None = None
    n_peers_in_fees_median: int | None = None
    notes: dict[str, str] = Field(default_factory=dict)
    annualization: str | None = None
    fetch_status: dict[str, Any] = Field(default_factory=dict)


class Regime(OpenModel):
    key: str
    label: str
    inflation_path_annual: list[float]  # HORIZON_MONTHS monthly values


class SupplyTrajectory(OpenModel):
    regime: str
    months: list[int]
    gross_issuance_cum: list[float]
    buyback_cum: list[float]
    gas_burn_cum: list[float]
    state_lock_cum: list[float]
    net_float_change_cum: list[float]
    crossover_month: int | None = None
    daily_issuance_start: float
    daily_issuance_end: float
    # Promoted model extras (supply_physics).
    monthly_net_float_change: list[float] = Field(default_factory=list)
    cumulative_crossover_month: int | None = None
    supply_end_near: float | None = None
    volume_growth_yoy: float | None = None
    daily_volume_usd_start: float | None = None
    daily_volume_usd_end: float | None = None
    realization_factor: float | None = None


class SupplyPhysics(OpenModel):
    inputs: dict[str, Assumption]
    regimes: list[Regime]
    trajectories: list[SupplyTrajectory]
    breakeven_daily_volume_usd: dict[str, float]  # per regime: V* where dS <= 0 at current price & take & alpha
    current_daily_sinks_near: dict[str, float]  # {buyback, gas_burn, state_lock, total}
    current_daily_issuance_near: float
    sink_coverage_ratio: float  # sinks / issuance
    staking_yield_table: list[dict[str, Any]] = Field(default_factory=list)
    agent_scale_table: list[dict[str, Any]] = Field(default_factory=list)  # [{agents, kb_per_agent, locked_near}]
    # Promoted model extras (supply_physics).
    warnings: list[str] = Field(default_factory=list)
    breakeven_daily_volume_usd_at_ceiling: dict[str, float] = Field(default_factory=dict)
    growth_trajectories: list[SupplyTrajectory] = Field(default_factory=list)
    current_net_float_change_near_day: float | None = None
    cross_checks: dict[str, float | None] = Field(default_factory=dict)
    horizon_months: int | None = None
    days_per_month: float | None = None


class EngineValue(OpenModel):
    key: EngineKey
    label: str
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    method: str
    assumption_heavy: bool


class SotpValuation(OpenModel):
    seed: int
    n_paths: int
    horizon_months: int
    discount_rate: float
    inputs: dict[str, Assumption]
    engines: list[EngineValue]
    fdv_percentiles: dict[str, float]  # {"p10","p25","p50","p75","p90"} horizon FDV discounted to today
    price_percentiles: dict[str, float]  # FDV / projected total supply
    fdv_ex_monetary_percentiles: dict[str, float]
    current_fdv_usd: float
    upside_p50_pct: float
    fan_chart: dict[str, list[float]]  # monthly p10..p90 paths, length horizon_months
    crossover_month_distribution: dict[str, Any]  # {"p_crossover_within_36m", "p10_month", "p50_month", "p90_month"} per regime
    sensitivity_heatmap: dict[str, Any]  # {"x": [...], "y": [...], "fdv_p50": [[...]], "net_deflation": [[bool]]}
    calibration: dict[str, Any] = Field(default_factory=dict)


class BearScenario(OpenModel):
    key: str
    title: str
    narrative: str
    perturbations: dict[str, float]
    sotp_fdv_p50: float
    drawdown_pct: float
    price_p50: float
    crossover_month: int | None = None
    early_warning_metric: str
    current_value: float | None = None
    trigger_threshold: float
    trigger_breached: bool | None = None  # null = metric not measured this run (never reported as "not breached")
    monitor_source: str
    # Promoted model extras (bear_case).
    trigger_evaluated: bool | None = None  # False when current_value is null or the sample is too thin to grade
    monitor_field: str | None = None
    trigger_comparator: str | None = None
    trigger_note: str | None = None
    fdv_basis: str | None = None  # "deterministic (median-input) SOTP at perturbed inputs; not the Monte Carlo P50"
    mc_fdv_p50: float | None = None
    mc_drawdown_pct: float | None = None
    price_drawdown_pct: float | None = None  # per-token drawdown; differs from drawdown_pct when horizon supply changes
    fdv_ex_monetary: float | None = None
    supply_at_horizon_near: float | None = None
    crossover_source: str | None = None
    perturbations_applied: dict[str, str] = Field(default_factory=dict)
    perturbations_unapplied: list[str] = Field(default_factory=list)
    secondary_metric: str | None = None
    secondary_value: float | None = None
    secondary_threshold: float | None = None
    secondary_comparator: str | None = None
    secondary_breached: bool | None = None  # null = secondary metric not measured
    secondary_evaluated: bool | None = None


class BearCase(OpenModel):
    base_fdv_p50: float
    scenarios: list[BearScenario]
    combined_worst_fdv: float
    combined_drawdown_pct: float
    falsification_summary: str
    # Promoted model extras (bear_case).
    # base_fdv_p50 / sotp_fdv_p50 / combined_worst_fdv keep their names for compatibility but are DETERMINISTIC values at
    # median inputs, not Monte Carlo percentiles; value_basis says so and the memo prints it.
    value_basis: str | None = None
    basis: str | None = None
    base_mc_fdv_p50: float | None = None
    combined_mc_fdv_p50: float | None = None
    combined_mc_drawdown_pct: float | None = None
    triggers_evaluated: int | None = None
    triggers_unevaluated: list[str] = Field(default_factory=list)
    base_price_p50: float | None = None
    base_crossover_month: int | None = None
    combined_worst_price: float | None = None
    combined_price_drawdown_pct: float | None = None
    combined_crossover_month: int | None = None
    combined_perturbations: dict[str, float] = Field(default_factory=dict)
    combined_perturbations_applied: dict[str, str] = Field(default_factory=dict)
    combined_perturbations_unapplied: list[str] = Field(default_factory=list)
    triggers_breached: int | None = None
    live_metrics: dict[str, Any] = Field(default_factory=dict)
    stress_parameters: list[dict[str, Any]] = Field(default_factory=list)
    drawdown_definition: str | None = None


class EvidenceClaim(OpenModel):
    claim: str
    status: EvidenceStatus
    value: str
    source: str
    confidence: str
    note: str = ""


class Snapshot(OpenModel):
    schema_version: str = SCHEMA_VERSION
    generated_at_utc: str
    seed: int
    runtime_s: float
    valuo_version: str
    near_rpc: NearOnchainTruth
    execution_bench: ExecutionBenchmark | None = None
    intents_forensics: IntentsForensics
    comps: PeerComps
    supply_physics: SupplyPhysics
    sotp: SotpValuation
    bear_case: BearCase
    evidence_scorecard: list[EvidenceClaim] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance_summary: dict[str, Any] = Field(default_factory=dict)
    # Integration extras (reproduce.py): what was run and how long each stage took.
    run_config: dict[str, Any] = Field(default_factory=dict)
    timings_s: dict[str, float] = Field(default_factory=dict)
    # Reverse valuation / tornado / peer coverage over the snapshot itself (models/market_implied.py, sensitivity.py,
    # relative_value.py). Null when the model raised; reproduce records a warning instead of aborting.
    market_implied: dict[str, Any] | None = None
    sensitivity: dict[str, Any] | None = None
    relative_value: dict[str, Any] | None = None


class Manifest(OpenModel):
    generated_at_utc: str
    block_height: int
    block_hash: str
    snapshot_sha256: str
    snapshot_path: str
    records: list[RawRecord]
    sources: dict[str, int]
    failures: int
    # Integration extras (reproduce.py).
    schema_version: str = SCHEMA_VERSION
    valuo_version: str | None = None
    seed: int | None = None
    snapshot_bytes: int | None = None
    memo_path: str | None = None
    memo_sha256: str | None = None
    duckdb_path: str | None = None
    raw_dir: str | None = None
    warnings: list[str] = Field(default_factory=list)
    run_config: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "SCHEMA_VERSION", "PERCENTILE_KEYS",
    "AssumptionSource", "VenueName", "QuoteStatus", "CorridorArchetype", "EngineKey", "EvidenceStatus", "RawSource",
    "OpenModel", "RawRecord", "Assumption",
    "EpochIssuanceMeasurement", "ContractSinkSnapshot", "NearOnchainTruth",
    "VenueQuote", "CorridorClipResult", "Corridor", "ExecutionBenchmark",
    "CallerClass", "CallerShare", "IntentsForensics", "PeerComp", "PeerComps",
    "Regime", "SupplyTrajectory", "SupplyPhysics",
    "EngineValue", "SotpValuation", "BearScenario", "BearCase",
    "EvidenceClaim", "Snapshot", "Manifest",
]
