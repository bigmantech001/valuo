/**
 * TypeScript mirror of the `fee_pool_share` snapshot section written by
 * `quant/valuo/collectors/fee_pool.py`: NEAR Intents' share of the fees collected by the
 * cross-chain routers DefiLlama covers, over the window on which every included series has data.
 *
 * Shares are ratios in [0, 1]; `*_pp_*` fields are percentage points; dates are UTC `YYYY-MM-DD`.
 * When `status` is not "measured" the share, rank and trend fields are null or absent and `note`
 * says why. Every figure derives from the `defillama / fee_pool:<slug>:dailyFees` payloads.
 */

export type FeePoolStatus = "measured" | "insufficient_data" | "unavailable";

export interface FeePoolProtocol {
  slug: string;
  /** name as DefiLlama reports it (e.g. "THORChain DEX") */
  name: string;
  /** short display label (e.g. "THORChain") */
  label: string;
  category?: string | null;
  first_day: string | null;
  last_day: string | null;
  /** newest chart point; provisional, left out of the window */
  newest_point_day?: string | null;
  n_days: number;
  /** DefiLlama's own trailing-30-day total, for cross-checking `fees_30d_usd` */
  defillama_total30d?: number | null;
  /** the adapter's own definition of "fees", quoted verbatim */
  methodology_fees: string | null;
  methodology_url?: string | null;
  /** manifest record name, `defillama/fee_pool:<slug>:dailyFees` */
  record?: string | null;
  sha256: string | null;
  fetched_at_utc?: string | null;
  rank_30d: number | null;
  fees_30d_usd: number | null;
  fees_90d_usd: number | null;
  share_30d: number | null;
  fees_30d_window_start_usd?: number | null;
  fees_30d_peak_usd?: number | null;
  fees_30d_peak_date?: string | null;
  fees_30d_median_usd?: number | null;
  n_days_in_window?: number | null;
  zero_days_in_window?: number | null;
  longest_zero_run_days?: number | null;
  zero_run_start?: string | null;
  zero_run_end?: string | null;
}

export interface FeePoolWindow {
  start: string | null;
  end: string | null;
  n_days: number;
  missing_days?: number;
  /** slug of the protocol whose first day sets the window start */
  limited_by?: string | null;
  limited_by_name?: string | null;
  excluded_trailing_days: Array<{ date: string; reason: string }>;
  rule?: string;
}

export interface FeePoolPoint {
  date: string;
  share: number;
}

export interface FeePoolReadout {
  now: FeePoolPoint | null;
  d30_ago: FeePoolPoint | null;
  d90_ago: FeePoolPoint | null;
  window_start: FeePoolPoint | null;
  low?: FeePoolPoint | null;
  high?: FeePoolPoint | null;
  change_pp_30d: number | null;
  change_pp_90d: number | null;
  change_pp_window: number | null;
  days_start_to_now?: number | null;
}

export interface FeePoolTrend {
  status: string;
  basis?: string;
  n_points?: number;
  hac_lag_days?: number;
  slope_pp_per_30d?: number | null;
  se_pp_per_30d?: number | null;
  ci90_pp_per_30d?: [number, number] | null;
  excludes_zero?: boolean | null;
  direction?: "rising" | "falling" | "flat" | null;
  r2?: number | null;
  method?: string;
  first_day?: string | null;
  last_day?: string | null;
  note?: string;
}

export interface FeePoolRankRef {
  slug: string;
  name: string;
  share_30d: number | null;
  fees_30d_usd: number | null;
  relation?: "behind" | "ahead of";
}

export interface FeePoolRank {
  near_intents: number | null;
  of: number;
  leader?: FeePoolRankRef | null;
  reference?: FeePoolRankRef | null;
}

export interface FeePoolRobustness {
  key: string;
  label: string;
  excluded: string[];
  share_now: number | null;
  share_window_start: number | null;
  change_pp_window: number | null;
  trend: FeePoolTrend | null;
}

export interface FeePoolRolling {
  window_days: number;
  /** "date", "share", "share_ex_relay", "pool_30d_usd", then one column of rolling fees per slug */
  columns: string[];
  rows: Array<Array<string | number | null>>;
}

export interface FeePoolShare {
  status: FeePoolStatus;
  source?: string;
  focus_slug?: string;
  requested?: string[];
  included?: string[];
  unavailable?: Array<{ slug: string; name: string; reason: string }>;
  window?: FeePoolWindow | null;
  /** "six-protocol", "five-protocol", ... */
  pool_label?: string;
  rolling_days?: number;
  protocols: FeePoolProtocol[];
  pool_30d_usd?: number | null;
  rolling?: FeePoolRolling | null;
  share?: FeePoolReadout | null;
  share_ex_relay?: FeePoolReadout | null;
  rank?: FeePoolRank | null;
  trend?: FeePoolTrend | null;
  trend_ex_relay?: FeePoolTrend | null;
  trend_daily_cross_check?: FeePoolTrend | null;
  robustness?: FeePoolRobustness[];
  headline?: string | null;
  /** what the measurement says about the long-term case and what would overturn it */
  read?: string | null;
  caveats?: string[];
  warnings?: string[];
  /** reason, when `status` is not "measured" */
  note?: string | null;
  fetched_at_utc?: string | null;
  elapsed_s?: number | null;
}

/** One rolling row as named numbers; a missing or non-numeric cell is null. */
export interface FeePoolRollingPoint {
  date: string;
  share: number | null;
  share_ex_relay: number | null;
  pool_30d_usd: number | null;
}

/** Decode `rolling.rows` by column name, dropping rows without a date. Pure; safe on old shapes. */
export function feePoolRollingPoints(rolling: FeePoolRolling | null | undefined): FeePoolRollingPoint[] {
  if (!rolling || !Array.isArray(rolling.columns) || !Array.isArray(rolling.rows)) return [];
  const idx = (name: string) => rolling.columns.indexOf(name);
  const [iDate, iShare, iEx, iPool] = [idx("date"), idx("share"), idx("share_ex_relay"), idx("pool_30d_usd")];
  const num = (row: Array<string | number | null>, i: number): number | null => {
    const v = i >= 0 ? row[i] : null;
    return typeof v === "number" && Number.isFinite(v) ? v : null;
  };
  const out: FeePoolRollingPoint[] = [];
  for (const row of rolling.rows) {
    if (!Array.isArray(row)) continue;
    const date = iDate >= 0 ? row[iDate] : null;
    if (typeof date !== "string") continue;
    out.push({ date, share: num(row, iShare), share_ex_relay: num(row, iEx), pool_30d_usd: num(row, iPool) });
  }
  return out;
}

/** UTC `YYYY-MM-DD` -> days since 1970-01-01, or null when unparseable. */
export function feePoolDayIndex(date: string | null | undefined): number | null {
  if (!date) return null;
  const t = Date.parse(`${date}T00:00:00Z`);
  return Number.isFinite(t) ? Math.round(t / 86_400_000) : null;
}

/** Days since epoch -> "12 Sep 2026" style axis label (UTC). */
export function feePoolDayLabel(day: number, withYear = false): string {
  const d = new Date(day * 86_400_000);
  if (Number.isNaN(d.getTime())) return "";
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const base = `${d.getUTCDate()} ${months[d.getUTCMonth()]}`;
  return withYear ? `${base} ${d.getUTCFullYear()}` : base;
}
