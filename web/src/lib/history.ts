import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { artifactsDir } from "./snapshot";

/**
 * Server-only loader for the history store written by `python -m valuo.history` (quant/valuo/history.py):
 * artifacts/history/summary.json, schema "valuo.history.summary/1". The summary is rebuilt from
 * snapshots.jsonl (one record per canonical pipeline run) and bench.jsonl (one record per hourly quote
 * race) every time either grows. Returns null when the file is missing, unparsable or of another schema;
 * the History tab then shows how to create it. Nothing is ever filled in for a missing value.
 */

export const HISTORY_SUMMARY_SCHEMA = "valuo.history.summary/1";

/** [t_utc, value]; value null when the run did not measure it. */
export type HistoryPoint = [string, number | null];

/** history.series_stats: over the non-null values, in time order. */
export interface SeriesStats {
  n: number;
  first: number | null;
  last: number | null;
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
  p10: number | null;
  p90: number | null;
  /** last - first; null when n < 2 */
  change_abs: number | null;
  /** (last - first) / |first| x 100 (percent); null when n < 2 or first = 0 */
  change_pct: number | null;
  /** 90% percentile-bootstrap CI of the median; null when n < 5 */
  median_ci90: [number, number] | null;
  ci_method: string | null;
}

export interface SeriesBlock {
  points: HistoryPoint[];
  stats: SeriesStats;
}

export interface BenchSeriesBlock extends SeriesBlock {
  window_24h?: SeriesStats;
  window_7d?: SeriesStats;
}

/** [t_utc, value, breached] with breached null when the trigger was not graded that run. */
export type TriggerPoint = [string, number | null, boolean | null];

export interface TriggerHistory {
  metric: string | null;
  threshold: number | null;
  comparator: string | null;
  points: TriggerPoint[];
  n_runs: number;
  n_breached: number;
  breached_now: boolean | null;
  /** start of the current run of consecutive breaches; null when not breached now */
  breached_since_utc: string | null;
  breached_streak_days: number | null;
  falsification_rule: string;
}

export interface SnapshotHistory {
  n_records: number;
  /** all recorded runs before the latest-per-UTC-day thinning (summary only) */
  n_records_total?: number;
  n_same_day_reruns_dropped?: number;
  dedup_rule?: string;
  first_t_utc: string | null;
  last_t_utc: string | null;
  block_heights: Array<[string, number | null]>;
  snapshot_sha256: Array<[string, string | null]>;
  series: Record<string, SeriesBlock>;
  status: Array<[string, Record<string, unknown> | null]>;
  bear_triggers: Record<string, TriggerHistory>;
}

export interface BenchCell {
  corridor_id: string | null;
  archetype: string | null;
  clip_usd: number | null;
  n_runs: number;
  oneclick_status_counts: Record<string, number>;
  best_competitor_counts: Record<string, number>;
  oneclick_rank_counts: Record<string, number>;
  venue_status_counts: Record<string, Record<string, number>>;
  oneclick_ok_rate: number | null;
  oneclick_rank1_rate: number | null;
}

export interface BenchHistory {
  n_runs: number;
  first_t_utc: string | null;
  last_t_utc: string | null;
  series: Record<string, BenchSeriesBlock>;
  cells: Record<string, BenchCell>;
}

export interface HistorySummary {
  schema: string;
  generated_at_utc: string;
  seed: number | null;
  ci_method: string | null;
  snapshots: SnapshotHistory;
  bench: BenchHistory;
}

export interface HistoryLoad {
  summary: HistorySummary | null;
  /** absolute path read (shown in the empty state) */
  file: string;
  /** why summary is null */
  reason: string | null;
}

export function historyPaths(): { dir: string; summary: string } {
  const dir = path.join(artifactsDir(), "history");
  return { dir, summary: path.join(dir, "summary.json") };
}

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

const EMPTY_SNAPSHOTS: SnapshotHistory = { n_records: 0, first_t_utc: null, last_t_utc: null, block_heights: [], snapshot_sha256: [], series: {}, status: [], bear_triggers: {} };
const EMPTY_BENCH: BenchHistory = { n_runs: 0, first_t_utc: null, last_t_utc: null, series: {}, cells: {} };

let cache: { mtimeMs: number; size: number; value: HistorySummary } | null = null;

export async function loadHistory(): Promise<HistoryLoad> {
  const file = historyPaths().summary;
  let stat;
  try {
    stat = await fs.stat(file);
  } catch {
    return { summary: null, file, reason: "artifacts/history/summary.json does not exist yet" };
  }
  if (cache && cache.mtimeMs === stat.mtimeMs && cache.size === stat.size) return { summary: cache.value, file, reason: null };
  let parsed: unknown;
  try {
    parsed = JSON.parse(await fs.readFile(file, "utf8"));
  } catch {
    return { summary: null, file, reason: "artifacts/history/summary.json is not valid JSON" };
  }
  if (!isObj(parsed) || parsed.schema !== HISTORY_SUMMARY_SCHEMA) {
    return { summary: null, file, reason: `artifacts/history/summary.json has schema ${isObj(parsed) ? JSON.stringify(parsed.schema ?? null) : "none"}, expected ${HISTORY_SUMMARY_SCHEMA}` };
  }
  // Null-safe shape: missing blocks become empty ones so the UI can render "n/a" per figure.
  const snaps = isObj(parsed.snapshots) ? (parsed.snapshots as Partial<SnapshotHistory>) : {};
  const bench = isObj(parsed.bench) ? (parsed.bench as Partial<BenchHistory>) : {};
  const value: HistorySummary = {
    schema: HISTORY_SUMMARY_SCHEMA,
    generated_at_utc: typeof parsed.generated_at_utc === "string" ? parsed.generated_at_utc : "",
    seed: typeof parsed.seed === "number" ? parsed.seed : null,
    ci_method: typeof parsed.ci_method === "string" ? parsed.ci_method : null,
    snapshots: {
      ...EMPTY_SNAPSHOTS,
      ...snaps,
      series: isObj(snaps.series) ? snaps.series : {},
      bear_triggers: isObj(snaps.bear_triggers) ? snaps.bear_triggers : {},
      block_heights: Array.isArray(snaps.block_heights) ? snaps.block_heights : [],
      snapshot_sha256: Array.isArray(snaps.snapshot_sha256) ? snaps.snapshot_sha256 : [],
      status: Array.isArray(snaps.status) ? snaps.status : [],
    },
    bench: {
      ...EMPTY_BENCH,
      ...bench,
      series: isObj(bench.series) ? bench.series : {},
      cells: isObj(bench.cells) ? bench.cells : {},
    },
  };
  cache = { mtimeMs: stat.mtimeMs, size: stat.size, value };
  return { summary: value, file, reason: null };
}
