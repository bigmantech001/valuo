import { existsSync, promises as fs } from "node:fs";
import path from "node:path";
import { fmtInt, fmtNum, NA } from "@/lib/format";
import type { SeriesBlock, SeriesStats } from "@/lib/history";

/**
 * Pure helpers for Tab 6 (history), plus one server-side read of the VPS crontab
 * files so the cadence quoted in the UI is the schedule actually committed, not a typed-in claim.
 */

export function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function statsOf(block: SeriesBlock | null | undefined): SeriesStats | null {
  return block?.stats && typeof block.stats.n === "number" ? block.stats : null;
}

/** "2.4 min", "5.3 h", "7.0 days" */
export function fmtSpan(ms: number | null): string {
  if (ms === null || !Number.isFinite(ms)) return NA;
  const s = ms / 1000;
  if (s < 90) return `${fmtInt(s)} s`;
  if (s < 5400) return `${fmtNum(s / 60, { decimals: 1 })} min`;
  if (s < 2 * 86400) return `${fmtNum(s / 3600, { decimals: 1 })} h`;
  return `${fmtNum(s / 86400, { decimals: 1 })} days`;
}

export function spanMs(first: string | null, last: string | null): number | null {
  if (!first || !last) return null;
  const a = Date.parse(first);
  const b = Date.parse(last);
  return Number.isFinite(a) && Number.isFinite(b) ? b - a : null;
}

/** "Nov 1, 2026" (UTC) */
export function fmtDay(iso: string | null): string {
  if (!iso) return NA;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${fmtInt(n)} ${n === 1 ? one : many}`;
}

// ----------------------------------------------------------------------------- workflow schedules
export interface WorkflowSchedule {
  file: string;
  cron: string;
  /** "daily at 06:05 UTC" / "hourly at minute 17" / the raw expression */
  plain: string;
  /** "per day" / "per hour" / null when the expression is not a simple cadence */
  per: string | null;
}

function describeCron(cron: string): { plain: string; per: string | null } {
  const f = cron.trim().split(/\s+/);
  if (f.length !== 5) return { plain: `cron "${cron}"`, per: null };
  const [min, hour, dom, mon, dow] = f;
  const isNum = (x: string) => /^\d+$/.test(x);
  if (isNum(min) && hour === "*" && dom === "*" && mon === "*" && dow === "*") return { plain: `hourly at minute ${min} (cron "${cron}")`, per: "per hour" };
  if (isNum(min) && isNum(hour) && dom === "*" && mon === "*" && dow === "*")
    return { plain: `daily at ${hour.padStart(2, "0")}:${min.padStart(2, "0")} UTC (cron "${cron}")`, per: "per day" };
  return { plain: `cron "${cron}"`, per: null };
}

/**
 * Reads the job schedule from ops/vps/valuo.crontab (the scheduled runs live on a VPS, installed by
 * ops/vps/setup.sh) and classifies each line as the snapshot or the bench job by the command it runs.
 * The repo root is the parent of the web app (the same root `artifactsDir()` defaults to); deployments
 * rooted at web/ read the build-time copy in .valuo-data. Returns {} when the file is absent, in which
 * case the UI says the schedule could not be read.
 */
export async function readWorkflowSchedules(): Promise<{ snapshot?: WorkflowSchedule; bench?: WorkflowSchedule }> {
  const rel = path.join("ops", "vps", "valuo.crontab");
  const sibling = path.resolve(process.cwd(), "..", rel);
  const file = existsSync(sibling) ? sibling : path.resolve(process.cwd(), ".valuo-data", rel);
  const out: { snapshot?: WorkflowSchedule; bench?: WorkflowSchedule } = {};
  let text: string;
  try {
    text = await fs.readFile(file, "utf8");
  } catch {
    return out;
  }
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*((?:\S+\s+){4}\S+)\s+\S*valuo-run\.sh\s+(snapshot|bench)\b/);
    if (!m) continue;
    const kind = m[2] as "snapshot" | "bench";
    if (!out[kind]) out[kind] = { file: "ops/vps/valuo.crontab", cron: m[1], ...describeCron(m[1]) };
  }
  return out;
}
