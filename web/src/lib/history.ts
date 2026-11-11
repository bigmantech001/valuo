import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { rpcEndpoint } from "./nearRpc";
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
  /** elapsed days from the first to the last record of the current streak (one record = 0) */
  breached_streak_days: number | null;
  falsification_rule: string;
  // Fields below are written by history.py since the 36 h gap rule; absent in older summaries.
  /** "breached" | "clear" | "unmeasured" (trigger not evaluated in the latest record) */
  state_now?: "breached" | "clear" | "unmeasured";
  n_unmeasured?: number;
  last_t_utc?: string | null;
  last_value?: number | null;
  last_snapshot_sha256?: string | null;
  /** daily records inside the current streak */
  observed_days?: number;
  /** what ended the streak before it: an earlier clear / unmeasured record, a data gap, or the start of history */
  streak_broken_by?: "clear" | "unmeasured" | "gap" | "start_of_history" | null;
  /** set when the streak restarted after a gap of more than streak_max_gap_h between daily records */
  gap_reset_at_utc?: string | null;
  days_to_falsification?: number;
  falsified?: boolean;
  streak_max_gap_h?: number;
  falsification_days?: number;
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

/** history._route_block: 1Click win/loss record over a set of race cells. */
export interface RouteRecord {
  /** contested races = wins + losses + ties */
  races: number;
  wins: number;
  losses: number;
  ties: number;
  decided: number;
  /** wins / (wins + losses); null when no race was decided */
  win_rate: number | null;
  /** 90% Wilson score interval of win_rate */
  win_rate_ci90: [number, number] | null;
  median_headroom_bps_wins: number | null;
  median_headroom_bps_losses: number | null;
  /** venue -> losses it caused (best competitor on each loss), most frequent first */
  beaten_by_counts: Record<string, number>;
  top_beaten_by: string | null;
  top_beaten_by_n: number;
  /** cells that were not a contest */
  excluded: number;
  excluded_reasons: Record<string, number>;
  first_t_utc: string | null;
  last_t_utc: string | null;
  span_days: number | null;
}

export interface CorridorRouteRecord extends RouteRecord {
  corridor_id: string;
  archetype: string | null;
  clips_usd: number[];
}

export interface CellRouteRecord extends RouteRecord {
  corridor_id: string | null;
  clip_usd: number | null;
}

export interface RoutesSummary {
  method: { unit: string; contest_rule: string; outcome_rule: string; headroom_definition: string; win_rate: string; ci: string; beaten_by: string; tie_bps: number };
  overall: RouteRecord & { n_routes: number; n_runs: number };
  by_corridor: Record<string, CorridorRouteRecord>;
  by_cell: Record<string, CellRouteRecord>;
}

export interface BenchHistory {
  n_runs: number;
  first_t_utc: string | null;
  last_t_utc: string | null;
  series: Record<string, BenchSeriesBlock>;
  cells: Record<string, BenchCell>;
  /** absent in summaries written before the win/loss block existed */
  routes?: RoutesSummary | null;
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
      routes: isObj(bench.routes) && isObj((bench.routes as RoutesSummary).overall) && isObj((bench.routes as RoutesSummary).by_corridor) ? bench.routes : null,
    },
  };
  cache = { mtimeMs: stat.mtimeMs, size: stat.size, value };
  return { summary: value, file, reason: null };
}

// ----------------------------------------------------------------------------- on-chain falsification records
/**
 * The account the daily VPS job anchors with (VALUO_ANCHOR_ACCOUNT in ops/vps/valuo-run.sh). The value is the
 * implicit account named in README.md ("The anchor account is 0161aff7…81f0"); override with VALUO_ANCHOR_ACCOUNT.
 */
export const DEFAULT_ANCHOR_ACCOUNT = "0161aff765e5412f3d3cac430933fb44325b5b012cf525410a9c7d1fa2fa81f0";
export const FALSIFICATION_PATH = ["valuo", "falsification"] as const;

export function anchorAccount(): string {
  const env = process.env.VALUO_ANCHOR_ACCOUNT?.trim();
  return env && /^[a-z0-9._-]{2,64}$/.test(env) ? env : DEFAULT_ANCHOR_ACCOUNT;
}

/** quant/valuo/anchor.py falsification_record, as written to <account>/valuo/falsification/<trigger_key>. */
export interface FalsificationValue {
  schema?: string;
  trigger?: string;
  metric?: string | null;
  threshold?: number | null;
  comparator?: string | null;
  breached_since_utc?: string | null;
  streak_days?: number | null;
  observed_days?: number | null;
  last_t_utc?: string | null;
  last_value?: number | null;
  snapshot_sha256?: string | null;
  rule?: string;
}

export interface FalsificationRecord {
  key: string;
  value: FalsificationValue | null;
  raw: string | null;
  write_block_height: number | null;
}

export interface FalsificationRead {
  account: string;
  records: FalsificationRecord[];
  /** null when the read succeeded (records may still be empty) */
  error: string | null;
  checked_at_utc: string;
  rpc: string;
}

const FALSIFICATION_TTL_MS = 5 * 60 * 1000;
let falsificationCache: { at: number; value: FalsificationRead } | null = null;

/**
 * Live SocialDB read (view call, no key) of every record under <account>/valuo/falsification/*, with the block
 * height each value was written at. Cached 5 minutes in-process; 4 s timeout. A failed read returns the error,
 * never an empty list presented as "no record".
 */
export async function loadFalsificationRecords(timeoutMs = 4000): Promise<FalsificationRead> {
  if (falsificationCache && Date.now() - falsificationCache.at < FALSIFICATION_TTL_MS) return falsificationCache.value;
  const account = anchorAccount();
  const rpc = rpcEndpoint();
  const checked_at_utc = new Date().toISOString();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let value: FalsificationRead;
  try {
    const args = { keys: [`${account}/${FALSIFICATION_PATH.join("/")}/*`], options: { with_block_height: true } };
    const res = await fetch(rpc, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: "valuo-falsification",
        method: "query",
        params: { request_type: "call_function", finality: "final", account_id: "social.near", method_name: "get", args_base64: Buffer.from(JSON.stringify(args)).toString("base64") },
      }),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`RPC HTTP ${res.status}`);
    const body = (await res.json()) as { result?: { result?: number[]; error?: string }; error?: { message?: string } };
    if (body.error) throw new Error(body.error.message ?? "RPC error");
    if (body.result?.error) throw new Error(body.result.error);
    if (!Array.isArray(body.result?.result)) throw new Error("malformed RPC view result");
    const text = Buffer.from(body.result.result).toString("utf8");
    let node: unknown = text ? JSON.parse(text) : {};
    for (const part of [account, ...FALSIFICATION_PATH]) node = isObj(node) ? node[part] : undefined;
    const records: FalsificationRecord[] = [];
    if (isObj(node)) {
      for (const [key, leaf] of Object.entries(node)) {
        if (key.startsWith(":") || !isObj(leaf)) continue;
        const raw = typeof leaf[""] === "string" ? (leaf[""] as string) : null;
        let parsed: FalsificationValue | null = null;
        try {
          const v: unknown = raw ? JSON.parse(raw) : null;
          parsed = isObj(v) ? (v as FalsificationValue) : null;
        } catch {
          parsed = null;
        }
        records.push({ key, value: parsed, raw, write_block_height: typeof leaf[":block"] === "number" ? (leaf[":block"] as number) : null });
      }
    }
    records.sort((a, b) => a.key.localeCompare(b.key));
    value = { account, records, error: null, checked_at_utc, rpc };
    falsificationCache = { at: Date.now(), value };
  } catch (err) {
    const message = err instanceof Error ? (err.name === "AbortError" ? `timeout after ${timeoutMs} ms` : err.message) : String(err);
    value = { account, records: [], error: message, checked_at_utc, rpc };
  } finally {
    clearTimeout(timer);
  }
  return value;
}
