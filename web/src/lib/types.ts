/**
 * TypeScript mirror of `quant/valuo/schemas.py` (SCHEMA_VERSION 1.0.0).
 *
 * Names and snake_case fields are identical to the pydantic models. Conventions:
 *  - A Python field whose default is `None` is optional here (`?: T | null`); a field with a
 *    non-null default (`[]`, `{}`, `0`, `False`, `""`) is required because pydantic always
 *    serialises it. Fields without a default are required.
 *  - Python `dict[str, Any]` sections whose keys are set by the owning collector/model are typed
 *    as `type` aliases with the exact keys found in `artifacts/latest_snapshot.json` (so they stay
 *    assignable to `Record<string, unknown>` for `num()` / `str()`). Fetched numbers are
 *    `number | null`: a failed fetch is recorded as null, never substituted.
 *  - Collector/model outputs are `OpenModel` (`extra="allow"`). Extras the current Python emits
 *    beyond `schemas.py` are declared optional and marked "collector extra" / "model extra"; a
 *    snapshot written before the emitting code landed will not carry them. Anything else goes
 *    through `getExtra()`.
 */

export const SCHEMA_VERSION = "1.0.0";

export const PERCENTILE_KEYS = ["p10", "p25", "p50", "p75", "p90"] as const;
export type PercentileKey = (typeof PERCENTILE_KEYS)[number];
/** `dict[str, float]` keyed by p10..p90 (extra keys allowed). */
export type PercentileMap = Record<PercentileKey, number> & Record<string, number>;

// --------------------------------------------------------------------------- literal aliases
export type AssumptionSource = "assumption" | "derived" | "measured";
export type VenueName = "1click" | "relay" | "lifi" | "across";
export type QuoteStatus = "ok" | "no_liquidity" | "unsupported_route" | "error" | "skipped";
export type CorridorArchetype = "cross_vm" | "native_btc" | "evm_l2" | "native_zec";
export type EngineKey = "clearinghouse" | "confidential" | "monetary";
export type EvidenceStatus =
  | "VERIFIED_ON_CHAIN"
  | "VERIFIED_LIVE_API"
  | "DERIVED"
  | "ASSUMPTION"
  | "NOT_SUPPORTED";
export type RawSource =
  | "near_rpc"
  | "near_rpc_archival"
  | "oneclick"
  | "relay"
  | "lifi"
  | "across"
  | "nearstats"
  | "nearblocks"
  | "defillama"
  | "coingecko";
/** `CallerClass(str, Enum)`: values equal names. */
export type CallerClass =
  | "ai_agent"
  | "bridge_relayer"
  | "implicit_account"
  | "named_account"
  | "self_internal"
  | "system";

export const VENUE_NAMES: readonly VenueName[] = ["1click", "relay", "lifi", "across"];
export const QUOTE_STATUSES: readonly QuoteStatus[] = [
  "ok",
  "no_liquidity",
  "unsupported_route",
  "error",
  "skipped",
];

/**
 * Issuance regimes the supply model emits (`supply_physics.regimes[].key`). Python types the key
 * as `str`; these are the two keys present in every snapshot. The web slider's custom cap is
 * computed client-side and never appears in the snapshot.
 */
export const REGIME_KEYS = ["status_quo", "svrn_glidepath"] as const;
export type RegimeKey = (typeof REGIME_KEYS)[number];
/** Per-regime map (`dict[str, T]` keyed by regime). */
export type PerRegime<T> = { [regime in RegimeKey]: T } & { [regime: string]: T };

/** `bear_case.scenarios[].key` (Python `str`; `bear_case.SCENARIO_KEYS`). */
export const BEAR_SCENARIO_KEYS = [
  "fee_race_to_zero",
  "governance_stalemate",
  "post_incentive_decay",
  "solver_cartelization",
] as const;
export type BearScenarioKey = (typeof BEAR_SCENARIO_KEYS)[number];

/**
 * `CorridorClipResult.headroom_basis`: "dest_units" = (out_1click - out_best) / out_best on physical
 * destination units for the identical raw input (current collector, `execution_bench.HEADROOM_BASIS_DEST_UNITS`;
 * the web live race emits the same label). "out_units" was the former name of the same basis; "raw" / "usd"
 * are friction-difference bases written by the first collector version and still present in older snapshots.
 */
export type HeadroomBasis = "dest_units" | "out_units" | "raw" | "usd";
/**
 * `VenueQuote.usd_basis` / `ExecutionBenchmark.usd_friction_basis`: which price valued the USD legs.
 * "oneclick_token_list_oracle" = live 1Click token-list prices (preferred); "median_venue_oracle" = the
 * median of the ok venues' own implied prices, applied to every venue in the cell when the token list
 * failed (`execution_bench.common_price_basis`); "venue_oracle" = a quote's own legs (transient, before
 * the cell's common price is applied; not comparable across venues).
 */
export type UsdFrictionBasis = "oneclick_token_list_oracle" | "median_venue_oracle" | "venue_oracle";
/**
 * `CorridorClipResult.price_basis`: the ONE price every venue's USD friction in the cell is valued at
 * (collector extra; `source` null when no USD valuation was possible and frictions stay as returned).
 */
export type PriceBasis = {
  source: UsdFrictionBasis | null;
  dest_price_usd: number | null;
  origin_price_usd: number | null;
  /** venues whose own implied price entered the median (0 under the token-list oracle) */
  n_venue_oracles: number;
};
/** `BearScenario.trigger_comparator` (bear_case._trigger ops). */
export type TriggerComparator = "<" | "<=" | ">" | ">=";

// --------------------------------------------------------------------------- section 2: provenance
export interface RawRecord {
  /** RawSource in practice; kept `string` like the Python model. */
  source: string;
  /** e.g. "block_final", "quote:eth_usdc->sol_usdc:50000", "fees:near-intents:dailyRevenue" */
  name: string;
  url: string;
  method: string;
  request_body_sha256?: string | null;
  http_status?: number | null;
  ok: boolean;
  error?: string | null;
  /** ISO-8601 Z */
  fetched_at_utc: string;
  latency_ms: number;
  bytes: number;
  /** sha256 of the exact raw response bytes (sha256(b"") when nothing was received) */
  sha256: string;
  /** artifacts/raw/... relative to repo root */
  raw_path?: string | null;
  /** Python default 1; optional here so TS producers that do not retry may omit it. */
  attempts?: number;
  /** e.g. "primary GARBAGE_COLLECTED_BLOCK; retried on archival" */
  note?: string | null;
}

// --------------------------------------------------------------------------- section 3: contract
export interface Assumption {
  key: string;
  value: number;
  unit: string;
  low: number;
  high: number;
  source: AssumptionSource;
  justification: string;
}

/** `EpochIssuanceMeasurement.jumps[]`: one epoch-boundary supply jump. */
export type EpochIssuanceJump = {
  height: number;
  hash: string;
  minted_near: number;
};

export interface EpochIssuanceMeasurement {
  epoch_start_height: number;
  epoch_start_hash: string;
  prev_epoch_start_height?: number | null;
  /** supply jump at epoch boundary */
  minted_per_epoch_near?: number | null;
  epoch_duration_hours?: number | null;
  epochs_per_year?: number | null;
  /** within-epoch supply drift (negative = burn) */
  net_burn_per_epoch_near?: number | null;
  implied_annual_issuance_near?: number | null;
  implied_annual_inflation_rate?: number | null;
  /** max_inflation_rate x total_supply */
  nominal_annual_issuance_near: number;
  method_note: string;
  // Promoted collector extras (near_rpc): second independent boundary reading and timing detail.
  prev_minted_per_epoch_near?: number | null;
  avg_block_time_s?: number | null;
  measured_minus_nominal_annual_near?: number | null;
  epoch_start_timestamp_utc?: string | null;
  prev_epoch_start_timestamp_utc?: string | null;
  jumps: EpochIssuanceJump[];
}

/** `ContractSinkSnapshot.history[]`: archival `view_account` reading. */
export type SinkHistoryPoint = {
  block_height: number;
  timestamp_utc: string;
  storage_bytes: number;
  days_before_now: number;
};

export interface ContractSinkSnapshot {
  account_id: string;
  label: string;
  has_contract: boolean;
  storage_bytes: number;
  storage_locked_near: number;
  liquid_balance_near: number;
  total_balance_near: number;
  staked_near: number;
  /** empty when archival history was not fetched */
  history: SinkHistoryPoint[];
  growth_bytes_per_day?: number | null;
  growth_locked_near_per_day?: number | null;
  growth_window_days?: number | null;
  code_hash?: string | null;
  state_block_height?: number | null;
}

export interface NearOnchainTruth {
  block_height: number;
  block_hash: string;
  timestamp_ns: number;
  timestamp_utc: string;
  total_supply_near: number;
  gas_price_yocto: number;
  max_inflation_rate: number;
  protocol_reward_rate: number;
  storage_amount_per_byte_yocto: number;
  storage_near_per_kb: number;
  num_blocks_per_year: number;
  epoch_length_blocks: number;
  protocol_version: number;
  active_validator_count: number;
  total_staked_near: number;
  staked_supply_ratio: number;
  /** max_inflation_rate x (1 - protocol_reward_rate) / staked_ratio */
  nominal_staking_apr_current: number;
  nominal_staking_apr_svrn_1_6: number;
  gross_daily_issuance_near: number;
  gross_daily_issuance_svrn_near: number;
  epoch_issuance: EpochIssuanceMeasurement;
  tracked_sinks: ContractSinkSnapshot[];
  total_state_locked_near: number;
  measured_state_lock_growth_near_per_day?: number | null;
  rpc_endpoint_used: string;
  archival_available: boolean;
  // Promoted collector extras (near_rpc).
  warnings: string[];
  archival_attempted: boolean;
  /** implied_annual_issuance_near / 365.25 */
  measured_daily_issuance_near?: number | null;
  missing_accounts: string[];
  /** account ids whose archival growth entered measured_state_lock_growth_near_per_day */
  measured_state_lock_growth_sinks: string[];
  epoch_height?: number | null;
  epoch_id?: string | null;
  protocol_treasury_account?: string | null;
  svrn_target_inflation_used?: number | null;
}

export interface VenueQuote {
  venue: VenueName;
  supported: boolean;
  status: QuoteStatus;
  error_message?: string | null;
  amount_in_raw: string;
  amount_in_usd?: number | null;
  amount_out_raw?: string | null;
  amount_out_formatted?: number | null;
  amount_out_usd?: number | null;
  /** (in_usd - out_usd) / in_usd x 1e4 on the legs valued per `usd_basis` */
  friction_bps_usd?: number | null;
  /** same-asset corridors only */
  friction_bps_raw?: number | null;
  time_estimate_s?: number | null;
  route_tool?: string | null;
  fee_breakdown_usd: Record<string, number>;
  latency_ms: number;
  fetched_at_utc: string;
  raw_record_sha256: string;
  // Promoted collector extras (execution_bench): venue error code and a basis note (e.g. Across USD legs).
  error_code?: string | null;
  note?: string | null;
  /** LI.FI tool "near" resells NEAR Intents; not an independent price */
  routes_via_near_intents: boolean;
  // Collector extras (execution_bench._success / parsers), present on `status === "ok"` quotes.
  /** which oracle valued amount_in_usd / amount_out_usd */
  usd_basis?: UsdFrictionBasis;
  /** live 1Click token-list USD price of the destination asset (null when the list failed) */
  oracle_dest_price_usd?: number | null;
  oracle_origin_price_usd?: number | null;
  /** the venue's own USD legs, kept so oracle disagreement is visible */
  venue_amount_in_usd?: number | null;
  venue_amount_out_usd?: number | null;
  venue_friction_bps_usd?: number | null;
  venue_implied_dest_price_usd?: number | null;
  /** (venue implied dest price - oracle dest price) / oracle x 1e4 */
  venue_oracle_gap_bps?: number | null;
  /** 1Click: sum of quoteRequest.appFees[].fee (bps) */
  app_fee_bps?: number | null;
  min_amount_out_raw?: string | null;
  /** 1Click refundFee (raw origin units) */
  refund_fee_raw?: string | null;
  /** 1Click quoteRequest.confidentiality ("public") */
  confidentiality?: string | null;
  /** Relay details.totalImpact.percent */
  price_impact_pct?: number | null;
  /** LI.FI toolDetails.name */
  tool_name?: string | null;
  /** Across totalRelayFee.pct / 1e18 x 1e4 */
  relay_fee_bps?: number | null;
  usd_basis_note?: string | null;
  /** Across limits.maxDeposit (raw origin units) */
  max_deposit_raw?: string | null;
  exclusive_relayer?: string | null;
  /** true when the venue was not called because the corridor declares it structurally unsupported */
  declared?: boolean;
}

export interface CorridorClipResult {
  corridor_id: string;
  clip_usd: number;
  quotes: VenueQuote[];
  best_competitor?: string | null;
  /** see HeadroomBasis; positive = 1Click delivers more */
  headroom_bps?: number | null;
  /** 1 + number of ok competitors delivering strictly more */
  oneclick_rank?: number | null;
  n_venues_ok: number;
  // Promoted collector extras (execution_bench).
  headroom_basis?: HeadroomBasis | null;
  /** Python `str | None`; always the corridor's archetype */
  archetype?: CorridorArchetype | null;
  /** preferred basis: raw where present, else usd */
  oneclick_friction_bps?: number | null;
  best_competitor_friction_bps?: number | null;
  n_competitors_ok: number;
  // Collector extras (execution_bench.score_cell), absent from snapshots written before the dest_units basis.
  oneclick_amount_out_raw?: string | null;
  best_competitor_amount_out_raw?: string | null;
  /** per ok venue: how far its own USD mark of the destination asset sits from the cell's common price */
  venue_oracle_gap_bps?: Partial<Record<VenueName, number>>;
  /** true when any |venue_oracle_gap_bps| > |headroom_bps|: a USD-leg comparison would be decided by oracles */
  oracle_gap_exceeds_headroom?: boolean;
  /** the common price the cell's USD frictions are valued at (execution_bench.common_price_basis) */
  price_basis?: PriceBasis;
}

/**
 * One side of a benchmark corridor exactly as `execution_bench._leg()` emits it (Python types it
 * `dict[str, Any]`). `address` is the dry-quote recipient / refund address on that chain, never a
 * token contract; the token identifiers are the per-venue fields.
 */
export type CorridorLeg = {
  /** 1Click `blockchain` key: eth, sol, btc, base, arb, near, zec, ... */
  chain: string;
  symbol: string;
  decimals: number;
  /** Defuse/Omni asset id, e.g. "nep141:btc.omft.near" */
  oneclick_asset_id: string;
  /** recipient (destination) or refund (origin) address used for dry quotes */
  address: string;
  relay_chain_id: number | null;
  /** ERC-20 / mint address, or Relay's native-asset placeholder */
  relay_currency: string | null;
  /** LI.FI chain key: ETH, SOL, BTC, BAS, ARB */
  lifi_chain: string;
  lifi_token: string;
  across_chain_id: number | null;
  across_token: string | null;
};

export interface Corridor {
  corridor_id: string;
  label: string;
  archetype: CorridorArchetype;
  origin: CorridorLeg;
  destination: CorridorLeg;
  /** venues actually called for this corridor (Python `list[str]`) */
  venues_attempted: VenueName[];
  /** venue -> structural reason it is not called (no HTTP) */
  venues_declared_unsupported: Partial<Record<VenueName, string>>;
}

/** `ExecutionBenchmark.competitor_friction_by_venue_bps[venue]` */
export type CompetitorFrictionStats = {
  median: number;
  n: number;
  values: number[];
};

export interface ExecutionBenchmark {
  ran_at_utc: string;
  clips_usd: number[];
  corridors: Corridor[];
  results: CorridorClipResult[];
  /** median cell headroom per archetype over cells with 1Click ok and >= 1 competitor ok */
  headroom_by_archetype_bps: Partial<Record<CorridorArchetype, number | null>>;
  /** median over cross_vm cells of the best competitor's friction */
  competitive_fee_ceiling_bps?: number | null;
  /** size of the live 1Click token list (null if the fetch failed) */
  oneclick_1y_token_universe?: number | null;
  oneclick_blockchains: string[];
  summary_note: string;
  // Promoted collector extras (execution_bench).
  headroom_n_by_archetype: Partial<Record<CorridorArchetype, number>>;
  competitive_fee_ceiling_n?: number | null;
  competitive_fee_ceiling_basis?: string | null;
  token_list_ok?: boolean | null;
  token_list_sha256?: string | null;
  budget_s?: number | null;
  concurrency?: number | null;
  request_timeout_s?: number | null;
  elapsed_s?: number | null;
  n_quotes_ok?: number | null;
  // Collector extras (execution_bench.collect_execution_bench), absent from older snapshots.
  competitor_friction_by_venue_bps?: Partial<Record<VenueName, CompetitorFrictionStats>>;
  headroom_basis?: HeadroomBasis;
  /** formula text, e.g. "(out_1click - out_best_competitor) / out_best_competitor x 1e4 on destination units ..." */
  headroom_definition?: string;
  /** "oneclick_token_list_oracle" when the token list was fetched, else "median_venue_oracle" */
  usd_friction_basis?: UsdFrictionBasis;
}

export interface CallerShare {
  account_id: string;
  cls: CallerClass;
  receipts: number;
  share: number;
  example_tx_hash?: string | null;
}

// ---- IntentsForensics dict sections (keys as written by collectors/intents_forensics.py)
export type VolumeSplitCheck = { id: string; status: string };
export type VolumeWeekOverWeek = {
  endDate: string | null;
  days: Array<{ date: string; volumeUsd: number | null }>;
  thisWeekUsd: number | null;
  priorWeekUsd: number | null;
  changePct: number | null;
};
export type VolumeRecords = {
  maxDayUsd: number | null;
  maxDayDate: string | null;
  max7dUsd: number | null;
  max7dEndDate: string | null;
  max30dUsd: number | null;
  max30dEndDate: string | null;
};
/** DefiLlama dexs/near-intents totals, carried for the nearstats cross-check. */
export type DefiLlamaVolume = {
  "24h": number | null;
  "7d": number | null;
  "30d": number | null;
  "1y": number | null;
  allTimeUsd: number | null;
};

/** `intents_forensics.volume.confidential_share_status`. */
export type ConfidentialShareStatus = "measured" | "implausible_fallback" | "unavailable";

/** `intents_forensics.volume` (nearstats intents.totals + totalsBreakdown; USD). */
export type VolumeDict = {
  /** e.g. "nearstats:intents.totals" */
  source: string;
  allTimeUsd: number | null;
  "24h": number | null;
  "7d": number | null;
  "30d": number | null;
  /** null when the nearstats public/confidential split is unavailable or implausible (see confidential_share_status) */
  public30d: number | null;
  confidential30d: number | null;
  /** confidential30d / 30d; under "implausible_fallback" this is the registry assumption, not a measurement */
  confidential_share_30d: number | null;
  /** how confidential_share_30d was obtained (collector confidential_split_guard) */
  confidential_share_status?: ConfidentialShareStatus;
  /** human-readable origin of confidential_share_30d ("measured: ...", "assumption: ...", "unavailable: ...") */
  confidential_share_source?: string;
  confidential_share_measured?: boolean;
  public7d: number | null;
  confidential7d: number | null;
  confidential_share_7d: number | null;
  public24h: number | null;
  confidential24h: number | null;
  public_allTimeUsd: number | null;
  confidential_allTimeUsd: number | null;
  split_as_of_date: string | null;
  /** "public+confidential" */
  split_basis: string | null;
  split_sources: { total: string; public: string } | null;
  split_checks: VolumeSplitCheck[];
  weekOverWeek: VolumeWeekOverWeek | null;
  records: VolumeRecords | null;
  /** 30d / records.max30dUsd */
  vs_30d_record_ratio: number | null;
  /** 30d / records.max30dUsd - 1 (negative = below record) */
  drawdown_from_30d_record: number | null;
  defillama: DefiLlamaVolume | null;
};

export type FeesMethodology = {
  fees: string | null;
  revenue: string | null;
  holders_revenue: string | null;
};
/** `[ts_unix_s, fees_usd, revenue_usd, volume_usd]` (see `daily_series_columns`). */
export type FeesDailySeriesRow = [number, number | null, number | null, number | null];

/** `intents_forensics.fees` (DefiLlama fees / dailyRevenue / dailyHoldersRevenue / dexs; USD). */
export type FeesDict = {
  gross_fees_30d_usd: number | null;
  net_revenue_30d_usd: number | null;
  holders_revenue_30d_usd: number | null;
  gross_fees_24h_usd: number | null;
  net_revenue_24h_usd: number | null;
  gross_fees_7d_usd: number | null;
  net_revenue_7d_usd: number | null;
  fees_1y_usd: number | null;
  revenue_1y_usd: number | null;
  holders_revenue_1y_usd: number | null;
  cumulative_fees_usd: number | null;
  cumulative_revenue_usd: number | null;
  cumulative_holders_revenue_usd: number | null;
  /** denominator of the take rates */
  volume_30d_usd: number | null;
  /** e.g. "defillama:dexs/near-intents" */
  volume_30d_source: string | null;
  /** gross_fees_30d / volume_30d x 1e4 */
  gross_take_bps: number | null;
  net_take_bps: number | null;
  holders_take_bps: number | null;
  gross_take_bps_on_public_volume: number | null;
  /** net_revenue_30d / gross_fees_30d */
  capture_ratio: number | null;
  holders_capture_ratio: number | null;
  annualized_gross_fees_30d_usd: number | null;
  annualized_net_revenue_30d_usd: number | null;
  methodology: FeesMethodology;
  daily_series_columns: string[];
  daily_series_days: number;
  daily_series: FeesDailySeriesRow[];
  /** nearstats intents.protocolMetrics.totalGeneratedFeesUsd, for the cross-check */
  cumulative_fees_nearstats_usd: number | null;
  // Collector extras (current intents_forensics.py), absent from older snapshots.
  volume_30d_nearstats_usd?: number | null;
  /** ONE canonical window, e.g. "aligned daily charts, 30 complete UTC days 2026-10-02..2026-10-31" */
  take_rate_window?: string;
  take_rate_window_days?: number;
  take_rate_window_start_utc?: string | null;
  take_rate_window_end_utc?: string | null;
  /** DefiLlama's own rolling total30d fields, kept for the cross-check only (not the canonical window) */
  defillama_total30d?: DefiLlamaTotal30d;
};

/** `intents_forensics.fees.defillama_total30d` (DefiLlama rolling 30d totals; USD). */
export type DefiLlamaTotal30d = {
  fees: number | null;
  revenue: number | null;
  holders: number | null;
  volume: number | null;
};

export type PricePerf = {
  "24h": number | null;
  "7d": number | null;
  "1m": number | null;
  "3m": number | null;
  ytd: number | null;
  "1y": number | null;
  all: number | null;
};
export type PriceChangePct = {
  "24h": number | null;
  "7d": number | null;
  "14d": number | null;
  "30d": number | null;
  "60d": number | null;
  "200d": number | null;
  "1y": number | null;
};

/** `intents_forensics.price` (nearstats price.{currentUsd, facts, performance} + NearBlocks stats). */
export type PriceDict = {
  current_usd: number | null;
  change_24h_pct: number | null;
  fdv_usd: number | null;
  market_cap_usd: number | null;
  circulating_supply: number | null;
  total_supply: number | null;
  perf: PricePerf | null;
  price_change_pct: PriceChangePct | null;
  ath_usd: number | null;
  ath_date: string | null;
  /** "coingecko" (nearstats' upstream) */
  source: string | null;
  fetched_at: string | null;
  circulating_supply_nearblocks: number | null;
  total_supply_nearblocks: number | null;
  price_nearblocks_usd: number | null;
  market_cap_nearblocks_usd: number | null;
};

/** `intents_forensics.volatility` (1y daily closes -> log-return sigma; DefiLlama daily volume). */
export type VolatilityDict = {
  /** "1y" */
  window: string;
  /** "nearstats:price-history" */
  source: string;
  n_points: number | null;
  n_obs: number | null;
  first_t_utc: string | null;
  last_t_utc: string | null;
  price_first_usd: number | null;
  price_last_usd: number | null;
  periods_per_year: number | null;
  daily_sigma: number | null;
  annualized_sigma: number | null;
  mean_daily_log_return: number | null;
  sigma_30d_annualized: number | null;
  sigma_90d_annualized: number | null;
  volume_series_days: number | null;
  /** "defillama:dexs/near-intents" */
  volume_source: string | null;
  volume_daily_sigma: number | null;
  volume_annualized_sigma: number | null;
  volume_daily_n_obs: number | null;
  /** sigma of monthly log returns of 30-day volume aggregates (the MC calibration input) */
  volume_monthly_sigma: number | null;
  volume_monthly_n_obs: number | null;
  volume_monthly_mean_log_return: number | null;
  volume_first_t_utc: string | null;
  volume_last_t_utc: string | null;
};

/** `intents_forensics.top_swaps[]` (nearstats intents.topSwaps, snake_cased). */
export type TopSwap = {
  tx_hash: string;
  origin_symbol: string | null;
  origin_chain: string | null;
  destination_symbol: string | null;
  destination_chain: string | null;
  volume_usd: number | null;
  amount_in_usd: number | null;
  amount_out_usd: number | null;
  referral: string | null;
  affiliates: string[];
  status: string | null;
  created_at: string | null;
  explorer_url: string;
};

/** `intents_forensics.caller_sample`: how the NearBlocks receipt sample was drawn and classified. */
export type CallerSample = {
  account: string;
  pages_requested: number;
  per_page: number;
  external_receipts_sampled: number;
  unique_external_callers: number;
  hhi_external_ex_ai_agent: number | null;
  n_eff_external_ex_ai_agent: number | null;
  // Collector extras (current intents_forensics.py).
  /** what hhi_external measures: deposit-source / caller concentration, not solver concentration */
  hhi_external_meaning?: string;
  /** execute_intents receipts by predecessor class (fills are relayer self-receipts) */
  execute_intents_by_predecessor_class?: Partial<Record<CallerClass, number>>;
  class_counts: Partial<Record<CallerClass, number>>;
  class_share_external: Partial<Record<CallerClass, number>>;
  /** [first, last] receipt timestamps in the sample */
  sample_time_range_utc: string[];
  sample_span_s: number | null;
  classification_note: string;
  /** 90% bootstrap interval of hhi_external [lo, hi]; null when the sample is too small */
  hhi_external_ci90?: [number, number] | null;
  n_eff_external_ci90?: [number, number] | null;
  hhi_external_ex_ai_agent_ci90?: [number, number] | null;
};

/** `intents_forensics.source_status`: which upstream calls succeeded. */
export type ForensicsSourceStatus = {
  nearstats_summary: boolean;
  nearstats_price_history: boolean;
  defillama_fees: boolean;
  defillama_revenue: boolean;
  defillama_holders_revenue: boolean;
  defillama_dexs: boolean;
  nearblocks_pages_ok: number;
  nearblocks_count: boolean;
  nearblocks_stats: boolean;
};

export type SolverMeasurementStatus = "measured" | "thin" | "not_measured";

/** `intents_forensics.solver_concentration.settlement_hub` (detect_settlement_hub). */
export type SettlementHub = {
  account_id: string;
  distinct_counterparties: number;
  runner_up_counterparties: number;
  transfers_in: number;
  transfers_out: number;
  account_class: string;
};

/** `intents_forensics.solver_concentration.solvers[]` (collector extra). */
export type SolverShare = {
  account_id: string;
  fills: number;
  share: number;
  example_tx_hash: string | null;
  payloads_signed: number;
  name_matches_solver_pattern: boolean;
  fills_atomic?: number;
  fills_hub?: number;
};

/**
 * `intents_forensics.solver_concentration` (collector extra, current intents_forensics.py): HHI over
 * fill participations per solver account, parsed from execute_intents payloads. Absent from
 * snapshots written before the solver audit landed.
 */
export type SolverConcentration = {
  hhi_solver: number | null;
  n_eff_solver: number | null;
  // Bootstrap / settlement-mode extras (current intents_forensics.py), absent from older snapshots.
  /** 90% percentile-bootstrap interval of hhi_solver [lo, hi] over sampled fill units */
  hhi_solver_ci90?: [number, number] | null;
  n_eff_solver_ci90?: [number, number] | null;
  hhi_solver_ci90_percentile?: [number, number] | null;
  bootstrap_draws?: number;
  bootstrap_units?: number;
  bootstrap_seed?: number;
  bootstrap_method?: string;
  /** "measured" | "thin" (too few participations) | "not_measured" */
  measurement_status?: SolverMeasurementStatus;
  min_participations_for_measured?: number;
  /** atomic token_diff fills (n_fills = n_fills_atomic + n_fills_hub_legs) */
  n_fills_atomic?: number;
  /** solver-to-hub transfer legs */
  n_fills_hub_legs?: number;
  hhi_solver_atomic?: number | null;
  hhi_solver_hub?: number | null;
  n_transfer_intents?: number;
  /** account most transfer intents route through, when one clearly dominates; null otherwise */
  settlement_hub?: SettlementHub | null;
  sample_time_range_utc?: string[];
  sample_span_s?: number | null;
  n_fills: number;
  n_fills_attributed: number;
  n_fills_unresolved: number;
  n_execute_intents_receipts: number;
  n_signed_payloads: number;
  n_payloads_undecodable: number;
  unique_solvers: number;
  solvers: SolverShare[];
  taker_class_mix: Partial<Record<CallerClass, number>>;
  attribution_rules: Record<string, number>;
  top_signers_by_payloads: Record<string, number>;
  known_solvers_from_structure: string[];
  method: string;
};

export interface IntentsForensics {
  volume: VolumeDict;
  fees: FeesDict;
  confidential_tvl_usd?: number | null;
  /** nearstats flags confidentialTvlObservation.sourceStatus "unverified"; carried through */
  confidential_tvl_verified: boolean;
  unique_users_7d?: number | null;
  price: PriceDict;
  volatility: VolatilityDict;
  callers: CallerShare[];
  /** HHI over external callers (excluding `system` and self-receipts), 0..10000 */
  hhi_external: number;
  /** 10000 / hhi_external */
  n_eff_external: number;
  hhi_all: number;
  ai_agent_share: number;
  bridge_share: number;
  /** method name -> receipts (open: method names come from the chain) */
  method_mix: Record<string, number>;
  receipts_sampled: number;
  pages_fetched: number;
  lifetime_receipts?: number | null;
  /** [min, max] block height of the sample */
  sample_block_range: number[];
  explorer_base: string;
  // Promoted collector extras (intents_forensics).
  warnings: string[];
  fetched_at_utc?: string | null;
  nearstats_generated_at?: string | null;
  confidential_tvl_source_status?: string | null;
  confidential_tvl_warnings: string[];
  top_swaps: TopSwap[];
  caller_sample: CallerSample;
  source_status: ForensicsSourceStatus;
  // Collector extra (current intents_forensics.py).
  solver_concentration?: SolverConcentration;
}

export interface PeerComp {
  slug: string;
  symbol: string;
  fees_30d_usd?: number | null;
  revenue_30d_usd?: number | null;
  fees_1y_usd?: number | null;
  revenue_1y_usd?: number | null;
  fdv_usd?: number | null;
  market_cap_usd?: number | null;
  price_usd?: number | null;
  annualized_fees_usd?: number | null;
  annualized_revenue_usd?: number | null;
  fdv_to_fees?: number | null;
  fdv_to_revenue?: number | null;
  revenue_methodology?: string | null;
  // Promoted collector extras (comps).
  label?: string | null;
  coingecko_id?: string | null;
  fees_24h_usd?: number | null;
  revenue_24h_usd?: number | null;
  fees_7d_usd?: number | null;
  revenue_7d_usd?: number | null;
  /** "coins.llama.fi" | "coingecko" */
  price_source?: string | null;
  /** "coingecko" | "nearstats" (reproduce.py backfill for NEAR) */
  fdv_source?: string | null;
  mcap_to_fees?: number | null;
  mcap_to_revenue?: number | null;
  fees_methodology?: string | null;
  // Collector extras present on `near_combined` only (which DefiLlama slugs were summed).
  components?: string[];
  components_included?: { fees: string[]; revenue: string[] };
  components_missing?: { fees: string[]; revenue: string[] };
}

/** `comps.fetch_status` */
export type CompsFetchStatus = {
  defillama_fees_ok: string[];
  defillama_revenue_ok: string[];
  coins_llama_prices_ok: boolean;
  coingecko_markets_ok: boolean;
};

export interface PeerComps {
  /** ex-NEAR peers (solana, ethereum, hyperliquid) */
  peers: PeerComp[];
  /** near + near-intents summed */
  near_combined: PeerComp;
  median_fdv_to_revenue_ex_near?: number | null;
  median_fdv_to_fees_ex_near?: number | null;
  fetched_at_utc: string;
  // Promoted collector extras (comps): NEAR rows kept out of `peers` so ex-NEAR medians stay unambiguous.
  near_components: PeerComp[];
  n_peers_in_revenue_median?: number | null;
  n_peers_in_fees_median?: number | null;
  /** slug (or "near_combined") -> methodology note */
  notes: Record<string, string>;
  annualization?: string | null;
  fetch_status: CompsFetchStatus;
}

export interface Regime {
  /** RegimeKey in practice (Python `str`) */
  key: string;
  label: string;
  /** HORIZON_MONTHS monthly values */
  inflation_path_annual: number[];
}

export interface SupplyTrajectory {
  regime: string;
  months: number[];
  gross_issuance_cum: number[];
  buyback_cum: number[];
  gas_burn_cum: number[];
  state_lock_cum: number[];
  net_float_change_cum: number[];
  /** first month whose monthly net float change <= 0 */
  crossover_month?: number | null;
  daily_issuance_start: number;
  daily_issuance_end: number;
  // Promoted model extras (supply_physics).
  monthly_net_float_change: number[];
  /** first month whose cumulative net float change <= 0 */
  cumulative_crossover_month?: number | null;
  supply_end_near?: number | null;
  volume_growth_yoy?: number | null;
  daily_volume_usd_start?: number | null;
  daily_volume_usd_end?: number | null;
  realization_factor?: number | null;
}

/** `supply_physics.staking_yield_table[]` (one row per regime). */
export type StakingYieldRow = {
  regime: string;
  inflation_rate: number;
  /** inflation x (1 - treasury) / staked_ratio */
  nominal_staking_apr: number;
  /** nominal - inflation */
  real_staking_apr: number;
  /** buyback_annual / total_supply */
  buyback_accrual_apr: number;
  real_staking_apr_with_buyback: number;
  real_non_staker_apr: number;
  daily_issuance_near: number;
};

/** `supply_physics.agent_scale_table[]`: locked = agents x kb_per_agent / 100. */
export type AgentScaleRow = {
  agents: number;
  kb_per_agent: number;
  locked_near: number;
  is_default_kb: boolean;
  days_of_issuance_absorbed: number;
  share_of_supply: number;
};

/** `supply_physics.cross_checks` (`dict[str, float | None]`): independent readings of the same sinks. */
export type SupplyCrossChecks = {
  gas_burn_onchain_near_day: number | null;
  gas_burn_defillama_near_day: number | null;
  buyback_from_holders_revenue_near_day: number | null;
  buyback_identity_near_day: number | null;
  nominal_annual_issuance_near: number | null;
  measured_annual_issuance_near: number | null;
  nominal_daily_issuance_near: number | null;
  truth_gross_daily_issuance_near: number | null;
  /** further cross-checks the model adds (e.g. take_rate_window_days, volume_30d_*) */
  [check: string]: number | null;
};

export interface SupplyPhysics {
  inputs: Record<string, Assumption>;
  regimes: Regime[];
  trajectories: SupplyTrajectory[];
  /** per regime: V* where dS <= 0 at current price & take & alpha */
  breakeven_daily_volume_usd: PerRegime<number>;
  /** {buyback, gas_burn, state_lock, total} NEAR/day */
  current_daily_sinks_near: { buyback: number; gas_burn: number; state_lock: number; total: number };
  current_daily_issuance_near: number;
  /** sinks / issuance */
  sink_coverage_ratio: number;
  staking_yield_table: StakingYieldRow[];
  agent_scale_table: AgentScaleRow[];
  // Promoted model extras (supply_physics).
  warnings: string[];
  /** V* at the benchmark's competitive fee ceiling; empty when the benchmark was missing */
  breakeven_daily_volume_usd_at_ceiling: Partial<PerRegime<number>>;
  /** trajectories with public volume grown at the labelled YoY assumption */
  growth_trajectories: SupplyTrajectory[];
  current_net_float_change_near_day?: number | null;
  cross_checks: SupplyCrossChecks;
  horizon_months?: number | null;
  days_per_month?: number | null;
}

export interface EngineValue {
  key: EngineKey;
  label: string;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  method: string;
  assumption_heavy: boolean;
}

/** `sotp.fan_chart`: month axis plus running implied FDV and cumulative holder revenue, p10..p90. */
export type FanSeriesKey = `${"fdv" | "rev"}_${PercentileKey}`;
export type FanChart = { months: number[] } & Record<FanSeriesKey, number[]>;

/** `sotp.crossover_month_distribution[regime]` */
export type CrossoverRegimeStats = {
  /** fraction of paths with cumulative net float change <= 0 by the horizon */
  p_crossover_within_36m: number;
  p10_month: number | null;
  p50_month: number | null;
  p90_month: number | null;
  n_paths_crossed: number;
  p_deflationary_at_horizon: number;
  median_cum_net_float_change_near: number;
};
export type CrossoverMonthDistribution = {
  status_quo: CrossoverRegimeStats;
  svrn_glidepath: CrossoverRegimeStats;
  basis: string;
  deterministic_crossover_month: number | null;
  note: string;
};

/** `sotp.sensitivity_heatmap`: 5x5 deterministic FDV over daily volume x net take. */
export type SensitivityHeatmap = {
  /** daily volume USD (columns) */
  x: number[];
  /** net take bps (rows) */
  y: number[];
  x_label: string;
  y_label: string;
  /** fdv_p50[yi][xi] */
  fdv_p50: number[][];
  /** net_deflation[yi][xi] under `regime` */
  net_deflation: boolean[][];
  basis: string;
  confidential_share_used: number;
  regime: string;
};

/** `sotp.calibration.deterministic_base`: deterministic_sotp() at the median inputs. */
export type DeterministicBase = {
  fdv_total: number;
  fdv_ex_monetary: number;
  engine_clearinghouse: number;
  engine_confidential: number;
  engine_monetary: number;
  implied_price: number;
  crossover_month: number | null;
  cum_holder_revenue_usd: number;
};

/**
 * `sotp.calibration` (`dict[str, Any]`): every measured/derived input the Monte Carlo used, with
 * its source. Keys below are those present in the snapshot; the model adds diagnostics freely,
 * so the map is open (index signature) unlike the other dict sections.
 */
export type SotpCalibration = {
  take_basis: string;
  v_pub_30d_usd: number;
  v_conf_30d_usd: number;
  gross_fees_30d_usd: number;
  blended_gross_take_bps: number;
  tau_pub_start_bps: number;
  tau_pub_start_method: string;
  tau_conf_start_bps: number;
  net_take_start_bps: number;
  alpha_capture: number;
  alpha_source: string;
  tau_floor_bps: number;
  tau_floor_source: string;
  headroom_cross_vm_bps: number | null;
  competitive_fee_ceiling_bps: number | null;
  public_take_floor_bps: number;
  terminal_multiple_raw: number | null;
  terminal_multiple_used: number;
  terminal_multiple_clipped: boolean;
  sigma_price_annual: number;
  sigma_price_monthly: number;
  sigma_volume_monthly: number;
  sigma_volume_source: string;
  volatility_window: string;
  volatility_n_obs: number;
  lambda_pub_monthly: number;
  lambda_conf_monthly: number;
  growth_monthly_pub: number;
  growth_monthly_conf: number;
  confidential_share_start: number;
  confidential_share_target: number;
  confidential_sigma_multiplier: number;
  sigma_volume_monthly_conf: number;
  confidential_tvl_verified: boolean;
  issuance_scale_measured_over_path: number;
  regime_inflation_paths_annual: PerRegime<number[]>;
  supply_at_horizon_near: number;
  supply_at_horizon_by_regime: PerRegime<number>;
  price_basis: string;
  gas_burn_near_day: number;
  state_lock_near_day: number;
  price_usd: number;
  current_fdv_usd: number;
  days_per_month: number;
  crossover_basis: string;
  warnings: string[];
  deterministic_base: DeterministicBase;
  monthly_tau_pub_bps: number[];
  monthly_tau_conf_bps: number[];
  mc_mean_fdv: number;
  supply_at_horizon_used: number;
  // Model extras (current sotp_valuation.py), absent from older snapshots.
  mc_mean_fdv_note?: string;
  mc_mean_to_p50_fdv?: number | null;
  /** the canonical take-rate window consumed from intents_forensics.fees (never recomputed) */
  take_rate_window?: string;
  take_rate_window_days?: number;
  take_rate_window_note?: string;
  gross_take_bps?: number | null;
  net_take_bps?: number | null;
  volume_30d_total_usd?: number | null;
  volume_30d_source?: string;
  confidential_share_source?: string;
  confidential_share_assumed?: boolean;
  /** false when the nearstats public/confidential split was unavailable (Engine 2 not measured) */
  confidential_engine_measured?: boolean;
  /** how the starting confidential share was obtained (mirrors intents_forensics.volume) */
  confidential_share_status?: ConfidentialShareStatus;
  /** mean-matching (Ito) GBM statement: the labelled growth is the EXPECTED path; the median path is lower */
  gbm_convention?: string;
  volume_mean_to_median_12m?: number | null;
  volume_mean_to_median_horizon?: number | null;
  volume_start_usd_day?: number | null;
  /** analytic E[V_H] and median V_H of the public-volume GBM, USD/day */
  volume_terminal_mean_usd_day?: number | null;
  volume_terminal_median_usd_day?: number | null;
  /** their sampled twins over the seeded paths */
  volume_terminal_mean_usd_day_mc?: number | null;
  volume_terminal_median_usd_day_mc?: number | null;
  price_source?: string;
  current_fdv_basis?: string;
  current_fdv_coingecko_usd?: number | null;
  current_fdv_nearstats_usd?: number | null;
  current_fdv_nearstats_gap_pct?: number | null;
  /** fallback chain position of the terminal multiple */
  terminal_multiple_source?: "derived" | "derived_fdv_to_fees" | "assumption";
  terminal_multiple_basis?: string;
  sigma_price_measured?: boolean;
  sigma_price_source?: string;
  sigma_volume_monthly_n_obs?: number | null;
  sigma_volume_monthly_log_returns?: number[];
  sigma_volume_monthly_ex_first_3?: number | null;
  /** additive decomposition of the one path whose total is the sample median */
  engine_shares_on_median_total_path?: EngineSharesOnMedianPath;
  engine_percentiles_note?: string;
  [key: string]: unknown;
};

/** `sotp.calibration.engine_shares_on_median_total_path` (model extra). */
export type EngineSharesOnMedianPath = {
  path_index: number;
  fdv_total: number;
  clearinghouse: number;
  confidential: number;
  monetary: number;
  clearinghouse_share: number;
  confidential_share: number;
  monetary_share: number;
};

export interface SotpValuation {
  seed: number;
  n_paths: number;
  horizon_months: number;
  discount_rate: number;
  inputs: Record<string, Assumption>;
  engines: EngineValue[];
  /** horizon FDV discounted to today */
  fdv_percentiles: PercentileMap;
  /** FDV / projected total supply */
  price_percentiles: PercentileMap;
  fdv_ex_monetary_percentiles: PercentileMap;
  current_fdv_usd: number;
  upside_p50_pct: number;
  fan_chart: FanChart;
  crossover_month_distribution: CrossoverMonthDistribution;
  sensitivity_heatmap: SensitivityHeatmap;
  calibration: SotpCalibration;
}

/** `bear_case.scenarios[].trigger_status`. */
export type TriggerStatus = "breached" | "not_breached" | "inconclusive" | "not_measured";

export interface BearScenario {
  /** BearScenarioKey in practice (Python `str`) */
  key: string;
  title: string;
  narrative: string;
  /** model input -> perturbed value */
  perturbations: Record<string, number>;
  sotp_fdv_p50: number;
  /** fdv_scenario / fdv_base - 1 (signed fraction) */
  drawdown_pct: number;
  price_p50: number;
  crossover_month?: number | null;
  early_warning_metric: string;
  current_value?: number | null;
  trigger_threshold: number;
  /** null = not measured this run (metric null or sample too thin); never read null as "not breached" */
  trigger_breached: boolean | null;
  /** graded status of the whole row (bear_case.py); absent from older snapshots */
  trigger_status?: TriggerStatus;
  /** status of the primary condition alone ("thin" and "clear" appear here too) */
  primary_status?: "breached" | "clear" | "inconclusive" | "not_measured" | "thin" | "short_span";
  /** URL of the live source the trigger reads */
  monitor_source: string;
  // Promoted model extras (bear_case).
  monitor_field?: string | null;
  trigger_comparator?: TriggerComparator | null;
  trigger_note?: string | null;
  /** per-token drawdown; differs from drawdown_pct when horizon supply changes */
  price_drawdown_pct?: number | null;
  fdv_ex_monetary?: number | null;
  supply_at_horizon_near?: number | null;
  /** "deterministic_sotp" | "supply_model" */
  crossover_source?: string | null;
  /** perturbation key -> model input key it reached */
  perturbations_applied: Record<string, string>;
  /** perturbation keys the model has no input for */
  perturbations_unapplied: string[];
  secondary_metric?: string | null;
  secondary_value?: number | null;
  secondary_threshold?: number | null;
  secondary_comparator?: TriggerComparator | null;
  secondary_breached?: boolean | null;
  // Model extras (current bear_case.py), absent from older snapshots.
  /** false when the metric was unmeasured or the sample too thin: not breached, not clear */
  trigger_evaluated?: boolean;
  secondary_evaluated?: boolean;
  fdv_basis?: string;
  /** seeded Monte Carlo median at the perturbed inputs, when computed */
  mc_fdv_p50?: number | null;
  mc_drawdown_pct?: number | null;
  hhi_deposit_source_external?: number | null;
  solver_fills_attributed?: number | null;
  solver_fills_sampled?: number | null;
  sample_thin?: boolean;
  /** 90% bootstrap interval of the solver HHI the trigger read */
  hhi_solver_ci90?: [number, number] | null;
  /** seconds covered by the sample the trigger read, and the minimum the grader requires */
  sample_span_s?: number | null;
  min_sample_span_s?: number | null;
  span_sufficient?: boolean | null;
}

/** `bear_case.live_metrics`: the measured values the triggers were graded against (null = unmeasured). */
export type BearLiveMetrics = {
  net_take_bps: number | null;
  hhi_external: number | null;
  hhi_external_ex_ai_agent: number | null;
  external_receipts_sampled: number | null;
  sample_span_s: number | null;
  headroom_cross_vm_bps: number | null;
  max_inflation_rate: number | null;
  volume_30d_usd: number | null;
  record_30d_usd: number | null;
  confidential_tvl_usd: number | null;
  confidential_tvl_verified: boolean | null;
  // Model extras (current bear_case.py), absent from older snapshots.
  hhi_solver?: number | null;
  n_eff_solver?: number | null;
  solver_fills_attributed?: number | null;
  solver_fills_sampled?: number | null;
};

export interface BearCase {
  base_fdv_p50: number;
  scenarios: BearScenario[];
  combined_worst_fdv: number;
  combined_drawdown_pct: number;
  falsification_summary: string;
  // Promoted model extras (bear_case).
  base_price_p50?: number | null;
  base_crossover_month?: number | null;
  combined_worst_price?: number | null;
  combined_price_drawdown_pct?: number | null;
  combined_crossover_month?: number | null;
  combined_perturbations: Record<string, number>;
  combined_perturbations_applied: Record<string, string>;
  combined_perturbations_unapplied: string[];
  triggers_breached?: number | null;
  live_metrics: BearLiveMetrics;
  /** the labelled stress parameters (Assumption rows) the scenarios were built from */
  stress_parameters: Assumption[];
  drawdown_definition?: string | null;
  // Model extras (current bear_case.py), absent from older snapshots.
  /** "deterministic at median inputs; not a Monte Carlo percentile" */
  value_basis?: string;
  /** longer statement of what base_fdv_p50 / sotp_fdv_p50 / combined_worst_fdv are */
  basis?: string;
  base_mc_fdv_p50?: number | null;
  combined_mc_fdv_p50?: number | null;
  combined_mc_drawdown_pct?: number | null;
  triggers_evaluated?: number;
  triggers_unevaluated?: string[];
}

export interface EvidenceClaim {
  claim: string;
  status: EvidenceStatus;
  value: string;
  source: string;
  confidence: string;
  note: string;
}

/** `snapshot.provenance_summary` (ProvenanceLedger.summary()). */
export type ProvenanceSummary = {
  records: number;
  ok: number;
  failures: number;
  bytes: number;
  /** RawSource -> record count (Python `dict[str, int]`) */
  sources: Record<string, number>;
  /** "source:name" of each failed record */
  failed: string[];
  warnings: string[];
};

/** `config.as_dict()` as stored in `run_config.endpoints` (non-secret). */
export type RunEndpoints = {
  near_rpc_url: string;
  near_rpc_fallback_url: string;
  near_archival_rpc_url: string;
  oneclick_api_base: string;
  relay_api_base: string;
  lifi_api_base: string;
  across_api_base: string;
  nearstats_api_base: string;
  nearblocks_api_base: string;
  nearblocks_api_key_set: boolean;
  defillama_api_base: string;
  coins_llama_base: string;
  coingecko_api_base: string;
  seed: number;
  mc_paths: number;
  horizon_months: number;
  http_timeout_s: number;
  /** repo-relative ("artifacts") in current snapshots; older ones stored an absolute path */
  artifacts_dir: string;
  nearblocks_page_delay_s?: number;
};

/** `reproduce.py` CLI configuration as run (snapshot.run_config; manifest.run_config omits `endpoints`). */
export type RunConfig = {
  argv: string[];
  skip_bench: boolean;
  paths: number;
  seed: number;
  no_archival: boolean;
  clips_usd: number[];
  nearblocks_pages: number;
  nearblocks_delay_s: number;
  bench_budget_s: number;
  horizon_months: number;
  /** assumptions preset, e.g. "base" */
  preset: string;
  endpoints?: RunEndpoints;
  // Integration extras (current reproduce.py).
  nearblocks_delay_source?: "cli" | "env:VALUO_NEARBLOCKS_PAGE_DELAY_S";
  /** true only for a full default run, the one allowed to write the canonical artifacts/ */
  canonical?: boolean;
  /** repo-relative directory the run wrote to ("artifacts" or "artifacts/dev") */
  artifacts_dir?: string;
  raw_files_pruned?: number;
};

/** Pipeline stages timed by reproduce.py (`snapshot.timings_s` keys). */
export type ReproduceStage = "near_rpc" | "api_collectors" | "supply_physics" | "sotp" | "bear_case";

export interface Snapshot {
  schema_version: string;
  generated_at_utc: string;
  seed: number;
  runtime_s: number;
  valuo_version: string;
  near_rpc: NearOnchainTruth;
  /** null when the benchmark failed (reproduce.py records a warning) */
  execution_bench?: ExecutionBenchmark | null;
  intents_forensics: IntentsForensics;
  comps: PeerComps;
  supply_physics: SupplyPhysics;
  sotp: SotpValuation;
  bear_case: BearCase;
  evidence_scorecard: EvidenceClaim[];
  assumptions: Assumption[];
  warnings: string[];
  provenance_summary: ProvenanceSummary;
  // Integration extras (reproduce.py): what was run and how long each stage took.
  run_config: RunConfig;
  timings_s: Partial<Record<ReproduceStage, number>>;
  // Model extras (market_implied.py, sensitivity.py, relative_value.py), absent from older snapshots.
  market_implied?: MarketImplied | null;
  sensitivity?: Sensitivity | null;
  relative_value?: RelativeValue | null;
  // bull_case.py: the long-term case as falsifiable conditions graded against live data.
  bull_case?: BullCase | null;
}

// --------------------------------------------------------------------------- bull case (bull_case.py)
export type BullStatus = "on_track" | "behind" | "against" | "not_measured";
export type BullUnit = "ratio_yoy" | "ratio" | "usd_per_year" | "usd_per_day" | "usd" | "bps" | "x" | "hhi";

export interface BullTrend {
  label: string;
  now: number;
  then: number;
  change: number;
  window: string;
  source: string;
  direction: "up" | "down" | "flat";
}

export interface BullCondition {
  key: string;
  statement: string;
  kind: "requirement" | "supporting";
  required: number | null;
  live: number | null;
  unit: BullUnit | string;
  status: BullStatus;
  why: string;
  trend: BullTrend | null;
  required_source: string;
  live_source: string;
}

export interface BullCase {
  basis: string;
  current_fdv_usd: number | null;
  conditions: BullCondition[];
  counts: Record<BullStatus, number>;
  n_conditions: number;
  n_measured: number;
  headline: string;
  watch: string[];
}

// --------------------------------------------------------------------------- market-implied solves
/** `market_implied.solves[].evidence`: the measured (or assumed) comparator for a required value. */
export type MarketImpliedEvidence = {
  value: number | null;
  label: string;
  source: string;
  /** e.g. confidential_share_status when the comparator is itself an assumption */
  status?: string;
  assumption?: boolean;
  peers?: Array<{ symbol: string; fdv_to_revenue: number }>;
  model_cap?: number;
  range?: [number, number];
  base_model_year3_usd?: number;
  [key: string]: unknown;
};

/** `market_implied.solves[]`: one input moved alone until the model FDV equals the market FDV. */
export type MarketImpliedSolve = {
  param: string;
  label: string;
  short_label: string;
  /** ratio_yoy | bps | x | ratio_annual | ratio | usd_per_year | ... */
  unit: string;
  base_value: number;
  /** null when no value inside the search bounds reaches the market FDV */
  required_value: number | null;
  reachable: boolean;
  reason: string | null;
  search_bounds: [number, number];
  harder_direction: "higher" | "lower";
  evidence: MarketImpliedEvidence;
  required_vs_evidence: { ratio: number | null; difference: number | null; within_evidence: boolean | null };
  fdv_at_required_usd: number | null;
  check_rel_error: number | null;
  verdict: string;
  required_volume_scale?: number;
};

/** `market_implied` (docs/MODEL_DESIGN.md 4.5). */
export type MarketImplied = {
  basis: string;
  current_fdv_usd: number | null;
  base_fdv_usd: number | null;
  base_fdv_mc_p50_usd: number | null;
  gap_multiple: number | null;
  gap_multiple_vs_mc_p50: number | null;
  horizon_months: number;
  solver?: string;
  n_reachable: number;
  n_within_evidence: number;
  headline: string;
  solves: MarketImpliedSolve[];
};

// --------------------------------------------------------------------------- one-at-a-time sensitivity
/** `sensitivity.rows[]`: deterministic FDV at one input's low and high, all else at base. */
export type SensitivityRow = {
  rank: number;
  param: string;
  label: string;
  /** "measured" | "derived" | "assumption" */
  source: string;
  unit: string;
  base: number;
  low: number;
  high: number;
  fdv_low: number;
  fdv_high: number;
  swing_usd: number;
  implied_price_low: number | null;
  implied_price_high: number | null;
  range_basis: string;
  variance_share: number | null;
};

/** `sensitivity` (docs/MODEL_DESIGN.md 4.6). */
export type Sensitivity = {
  basis: string;
  variance_proxy?: string;
  base_fdv_usd: number | null;
  base_implied_price?: number | null;
  current_fdv_usd: number | null;
  top3_share: number | null;
  n_rows_reaching_market_fdv: number | null;
  excluded: Array<{ param: string; reason: string }>;
  notes: string[];
  headline: string;
  rows: SensitivityRow[];
};

// --------------------------------------------------------------------------- relative value
/** `relative_value.peers[]` / `.near` / `.near_components[]`. */
export type RelativeValueEntity = {
  slug: string;
  symbol: string;
  label: string;
  fdv_usd: number | null;
  annualized_fees_usd: number | null;
  annualized_revenue_usd: number | null;
  fees_1y_usd: number | null;
  revenue_1y_usd: number | null;
  revenue_to_fees_run_rate: number | null;
  revenue_methodology?: string | null;
  fdv_to_fees_run_rate: number | null;
  fdv_to_revenue_run_rate: number | null;
  fdv_to_fees_1y: number | null;
  fdv_to_revenue_1y: number | null;
};

export type RelativeValueCoverageKey = "fdv_to_fees_run_rate" | "fdv_to_revenue_run_rate" | "fdv_to_fees_1y" | "fdv_to_revenue_1y";

/** `relative_value.coverage[metric]`: NEAR's position in the peer distribution (rank 1 = lowest). */
export type RelativeValueCoverage = {
  value: number | null;
  rank: number | null;
  n: number;
  percentile: number | null;
  peer_median: number | null;
  peer_p25: number | null;
  peer_p75: number | null;
  peer_min: number | null;
  peer_max: number | null;
  position: string;
  vs_peer_median: number | null;
  label: string;
};

export type RelativeValueBandLeg = {
  near_cash_flow_usd: number | null;
  basis: string;
  n_peers: number;
  p25_fdv_usd: number | null;
  median_fdv_usd: number | null;
  p75_fdv_usd: number | null;
};

export type RelativeValueStakingRegime = {
  regime: string;
  inflation_rate: number | null;
  nominal_staking_apr: number | null;
  real_staking_apr: number | null;
  buyback_accrual_apr: number | null;
  real_staking_apr_with_buyback: number | null;
  real_non_staker_apr: number | null;
  daily_issuance_near: number | null;
};

export type RelativeValueStaking = {
  basis: string;
  regimes: RelativeValueStakingRegime[];
  staked_supply_ratio: number | null;
  nominal_staking_apr_current: number | null;
  annual_issuance_near: number | null;
  measured_inflation_rate: number | null;
  near_price_usd: number | null;
  security_budget_usd_per_year: number | null;
  security_budget_pct_of_fdv: number | null;
  annualized_fees_usd: number | null;
  annualized_holder_revenue_usd: number | null;
  fees_to_security_budget: number | null;
  revenue_to_security_budget: number | null;
  net_dilution_usd_per_year: number | null;
};

/** `relative_value` (docs/MODEL_DESIGN.md 4.7). */
export type RelativeValue = {
  basis: string;
  peers: RelativeValueEntity[];
  near: RelativeValueEntity | null;
  near_components: RelativeValueEntity[];
  coverage: Partial<Record<RelativeValueCoverageKey, RelativeValueCoverage>>;
  implied_fdv_band: {
    label: string;
    current_fdv_usd: number | null;
    fees?: RelativeValueBandLeg | null;
    revenue?: RelativeValueBandLeg | null;
  } | null;
  staking: RelativeValueStaking | null;
  model_terminal_multiple: number | null;
  n_peers_at_or_below_model_multiple: number | null;
  n_peers: number;
  findings: string[];
  caveat: string;
};

export interface Manifest {
  generated_at_utc: string;
  block_height: number;
  block_hash: string;
  /** sha256 over the exact bytes of latest_snapshot.json */
  snapshot_sha256: string;
  snapshot_path: string;
  records: RawRecord[];
  /** RawSource -> record count (Python `dict[str, int]`) */
  sources: Record<string, number>;
  failures: number;
  // Integration extras (reproduce.py).
  schema_version: string;
  valuo_version?: string | null;
  seed?: number | null;
  snapshot_bytes?: number | null;
  memo_path?: string | null;
  memo_sha256?: string | null;
  duckdb_path?: string | null;
  raw_dir?: string | null;
  warnings: string[];
  run_config: RunConfig;
}

/** The snapshot section names a tab may claim as "its" data (scalars and run metadata excluded). */
export type SnapshotSectionKey = Exclude<
  keyof Snapshot,
  "schema_version" | "generated_at_utc" | "seed" | "runtime_s" | "valuo_version" | "run_config" | "timings_s"
>;

// --------------------------------------------------------------------------- web API contracts
/** `/api/snapshot` freshness block: live head via one RPC call, 5 s timeout, nulls on failure. */
export interface Freshness {
  snapshot_block: number | null;
  snapshot_timestamp_utc: string | null;
  live_block: number | null;
  live_timestamp_utc: string | null;
  blocks_behind: number | null;
  seconds_behind: number | null;
  rpc_endpoint: string;
  checked_at_utc: string;
  error: string | null;
}

/** sha256 of the snapshot file on disk compared with `manifest.snapshot_sha256`. */
export interface Integrity {
  snapshot_sha256_file: string | null;
  snapshot_sha256_manifest: string | null;
  matches: boolean | null;
  snapshot_path: string;
  manifest_path: string;
}

export interface SnapshotApiResponse {
  snapshot: Snapshot | null;
  manifest: Manifest | null;
  freshness: Freshness | null;
  integrity: Integrity | null;
  error: string | null;
}

export interface LiveBenchmarkRequest {
  corridor_id: string;
  clip_usd: number;
}

/**
 * `CorridorClipResult` plus the per-venue provenance of this live race. Scoring mirrors
 * `execution_bench.score_cell`: headroom and rank are on physical destination units
 * (`headroom_basis = "dest_units"`); USD frictions are valued at the cell's one `price_basis`
 * (`common_price_basis`) and carried for display on `ranking_basis`.
 */
export interface LiveBenchmarkResponse extends CorridorClipResult {
  corridor: Corridor;
  /** always present on a live race (the collector extra is optional on stored cells) */
  price_basis: PriceBasis;
  /** friction display basis: "raw" on same-asset corridors (no oracle noise), "usd" otherwise */
  ranking_basis: "raw" | "usd";
  /** which price valued every venue's USD legs in this race: the live token list, else the median venue oracle */
  usd_friction_basis: UsdFrictionBasis;
  token_list_ok: boolean;
  ran_at_utc: string;
  total_latency_ms: number;
  /** one RawRecord per HTTP exchange (quotes, the 1Click token list, the Across chain list) */
  records: RawRecord[];
}

export type ReproduceJobStatus = "running" | "succeeded" | "failed";

export interface ReproduceJob {
  id: string;
  status: ReproduceJobStatus;
  command: string;
  cwd: string;
  started_at_utc: string;
  finished_at_utc: string | null;
  exit_code: number | null;
  /** last N lines of stdout / stderr */
  stdout_tail: string[];
  stderr_tail: string[];
  error: string | null;
}

// --------------------------------------------------------------------------- helpers
/** Read an undeclared (`extra="allow"`) field from any model object. */
export function getExtra<T = unknown>(obj: object | null | undefined, key: string): T | undefined {
  if (!obj) return undefined;
  return (obj as Record<string, unknown>)[key] as T | undefined;
}

/** Finite number at `key` of a loosely typed dict, else null. Never coerces strings. */
export function num(dict: Record<string, unknown> | null | undefined, key: string): number | null {
  if (!dict) return null;
  const v = dict[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** String at `key` of a loosely typed dict, else null. */
export function str(dict: Record<string, unknown> | null | undefined, key: string): string | null {
  if (!dict) return null;
  const v = dict[key];
  return typeof v === "string" ? v : null;
}

export function isPercentileMap(v: unknown): v is PercentileMap {
  if (!v || typeof v !== "object") return false;
  return PERCENTILE_KEYS.every((k) => typeof (v as Record<string, unknown>)[k] === "number");
}
