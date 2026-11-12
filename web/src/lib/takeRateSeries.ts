/**
 * TypeScript mirror of the `take_rate_series` snapshot section written by
 * `quant/valuo/models/take_rate_series.py`: NEAR Intents' realized take rate (fees / volume) over
 * time, derived from the DefiLlama near-intents daily charts already in the manifest.
 *
 * Take rates are basis points of volume; `*_pct` fields are percent per year; dates are UTC
 * `YYYY-MM-DD`. When `status` is not "measured" the point, range, regime and floor members are
 * null, `series` is empty and the trend / elasticity members are null.
 */

export type TakeRateStatus = "measured" | "insufficient_data";

/** One manifest payload the series was built from. */
export interface TakeRateSource {
  key: string;
  /** manifest record name, e.g. `defillama/fees:near-intents:dailyFees` */
  record: string;
  raw_path?: string | null;
  sha256?: string | null;
  rows?: number | null;
}

/** A rolling-30-day observation, dated by its last day. */
export interface TakeRatePoint {
  date: string;
  ts_unix_s: number;
  gross_take_bps: number | null;
  net_take_bps: number | null;
  /** null when the holders-revenue chart was not available (snapshot fallback) */
  holder_take_bps: number | null;
  avg_daily_volume_usd: number | null;
  /** only on `year_ago`: distance from the latest point in days */
  days_before_latest?: number;
}

export interface TakeRateExtreme {
  bps: number;
  date: string;
}

export interface TakeRateRange {
  n_points: number;
  gross_min: TakeRateExtreme | null;
  gross_max: TakeRateExtreme | null;
  gross_min_180d?: TakeRateExtreme | null;
}

/** Pooled take over a fixed block of days: sum(fees) / sum(volume). */
export interface TakeRatePooled {
  n_days: number;
  start_date?: string | null;
  end_date?: string | null;
  gross_take_bps: number | null;
  net_take_bps: number | null;
  holder_take_bps: number | null;
  avg_daily_volume_usd: number | null;
}

export interface TakeRateWindow extends TakeRatePooled {
  label: string;
  days_ago_from: number;
  days_ago_to: number;
}

/** OLS of ln(rolling gross take) on time in years, Newey-West interval. */
export interface TakeRateTrend {
  status: "measured" | "insufficient_data";
  n_points?: number;
  n_dropped_nonpositive?: number;
  hac_lag_days?: number;
  first_day?: string;
  last_day?: string;
  start_bps?: number;
  end_bps?: number;
  log_slope_per_year?: number;
  log_slope_se_hac?: number;
  change_per_year_pct?: number;
  ci90_pct?: [number, number];
  ci_excludes_zero?: boolean;
  direction?: string;
  note?: string;
}

export interface TakeRateLagSensitivity {
  hac_lag_days: number;
  ci90_pct: [number, number] | null;
  ci_excludes_zero: boolean | null;
}

/** The same trend on non-overlapping 30-day windows with a Student-t interval. */
export interface TakeRateBlockCheck {
  status: "measured" | "insufficient_data";
  n_blocks?: number;
  change_per_year_pct?: number;
  ci90_pct?: [number, number];
  ci_excludes_zero?: boolean;
  method?: string;
  note?: string;
}

export interface TakeRateTrends {
  trailing_365d: TakeRateTrend | null;
  trailing_180d: TakeRateTrend | null;
  full_history: TakeRateTrend | null;
  lag_sensitivity_365d?: TakeRateLagSensitivity[];
  block_check_365d?: TakeRateBlockCheck | null;
  /** null when either interval could not be computed */
  block_check_agrees?: boolean | null;
}

/** OLS of ln(daily gross take) on ln(daily volume), Newey-West interval. */
export interface TakeRateElasticity {
  status: "measured" | "insufficient_data";
  n_days?: number;
  n_dropped_zero_fee_or_volume?: number;
  hac_lag_days?: number;
  first_day?: string;
  last_day?: string;
  elasticity?: number;
  se_hac?: number;
  ci90?: [number, number];
  ci_excludes_zero?: boolean;
  r2?: number | null;
  note?: string;
}

export interface TakeRateRegimeBreak {
  /** first aligned day with holders revenue above zero; null when none was found */
  date: string | null;
  ts_unix_s: number | null;
  definition: string;
  first_revenue_day?: string | null;
  before: TakeRatePooled | null;
  before_trailing_365d?: TakeRatePooled | null;
  after: TakeRatePooled | null;
  note?: string;
}

export interface TakeRateFloorRead {
  /** model floor on the gross public take rate (assumptions.public_take_floor_bps) */
  public_take_floor_bps: number;
  /** bear-case fee-race trigger on the net take rate */
  bear_fee_race_trigger_net_take_bps: number;
  n_points: number;
  gross_below_floor: number;
  net_below_trigger: number;
  min_gross: TakeRateExtreme | null;
  min_net: TakeRateExtreme | null;
  latest_gross_above_floor: boolean;
  latest_net_above_trigger: boolean;
  since_regime_break?: {
    n_points: number;
    net_below_trigger: number;
    min_net: TakeRateExtreme | null;
    definition: string;
  } | null;
}

/** Row of `series`, in the order given by `columns`: [ts_unix_s, gross, net, holder, avg daily volume]. */
export type TakeRateRow = [number, number | null, number | null, number | null, number | null];

export interface TakeRateSeries {
  status: TakeRateStatus;
  method: string;
  source: string;
  sources: TakeRateSource[];
  source_mode: "raw" | "snapshot_fallback";
  holders_available: boolean;
  as_of_utc: string | null;
  rolling_window_days: number;
  trailing_days: number;
  n_days: number;
  first_day: string | null;
  last_day: string | null;
  n_gaps: number;
  excluded_unsettled_days: string[];
  columns: string[];
  series: TakeRateRow[];
  n_rolling_points: number;
  n_rolling_skipped: number;
  latest: TakeRatePoint | null;
  year_ago: TakeRatePoint | null;
  range_trailing_365d: TakeRateRange | null;
  windows: TakeRateWindow[];
  trend: TakeRateTrends;
  elasticity: { trailing_365d: TakeRateElasticity | null; full_history: TakeRateElasticity | null };
  regime_break: TakeRateRegimeBreak | null;
  floor_read: TakeRateFloorRead | null;
  /** one sentence, "verdict: numbers"; true whichever way the data points */
  headline: string;
  /** what the measurement says about the long-term case and what would overturn it */
  investor_read: string | null;
  caveats: string[];
  data_warnings: string[];
}

/** Column index in `series` by name, so the reader does not depend on the column order. */
export function takeRateColumn(data: Pick<TakeRateSeries, "columns">, name: string): number {
  return data.columns.indexOf(name);
}
