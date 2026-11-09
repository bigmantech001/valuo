import "server-only";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { repoRoot, serverEnv, serverEnvFlag } from "./env";
import type { ReproduceJob } from "./types";

/**
 * In-process job registry for `uv run python -m valuo.reproduce`, so the terminal's Refresh
 * button works in `next dev`. State lives on `globalThis` (keyed by a Symbol) so it survives
 * HMR and is shared by the `/api/reproduce` and `/api/reproduce/status` route modules. Only one
 * job runs at a time; the registry keeps the last few for status polling. Gated by
 * `VALUO_ALLOW_REPRODUCE=1` because it executes a local process.
 */

const TAIL_LINES = 400;
const KEEP_JOBS = 10;
const ALLOWED_FLAGS = new Set(["--skip-bench", "--no-archival", "--quiet"]);
const ALLOWED_VALUED = new Set(["--paths", "--seed", "--clips"]);

interface Store {
  jobs: Map<string, ReproduceJob>;
  order: string[];
}

const KEY = Symbol.for("valuo.reproduceJobs");
function store(): Store {
  const g = globalThis as unknown as Record<symbol, Store | undefined>;
  if (!g[KEY]) g[KEY] = { jobs: new Map(), order: [] };
  return g[KEY] as Store;
}

export function reproduceEnabled(): boolean {
  return serverEnvFlag("VALUO_ALLOW_REPRODUCE");
}

export function quantDir(): string {
  const fromEnv = serverEnv("VALUO_QUANT_DIR");
  return fromEnv ? path.resolve(fromEnv) : path.resolve(repoRoot(), "quant");
}

/**
 * Accept only the CLI flags `valuo.reproduce` defines (MODEL_DESIGN section 5), with numeric
 * validation for the valued ones, so the browser cannot pass arbitrary arguments to a shell.
 */
export function validateArgs(input: unknown): { args: string[] } | { error: string } {
  if (input === undefined || input === null) return { args: [] };
  if (!Array.isArray(input) || !input.every((a) => typeof a === "string")) return { error: "args must be a string array" };
  const args: string[] = [];
  for (let i = 0; i < input.length; i++) {
    const a = input[i] as string;
    if (ALLOWED_FLAGS.has(a)) {
      args.push(a);
      continue;
    }
    if (ALLOWED_VALUED.has(a)) {
      const v = input[i + 1] as string | undefined;
      if (v === undefined) return { error: `${a} needs a value` };
      if (a === "--clips" ? !/^\d+(\.\d+)?(,\d+(\.\d+)?)*$/.test(v) : !/^\d{1,9}$/.test(v)) return { error: `invalid value for ${a}` };
      args.push(a, v);
      i++;
      continue;
    }
    return { error: `argument not allowed: ${a}` };
  }
  return { args };
}

export function getJob(id: string): ReproduceJob | null {
  return store().jobs.get(id) ?? null;
}

export function listJobs(): ReproduceJob[] {
  const s = store();
  return s.order.map((id) => s.jobs.get(id)).filter((j): j is ReproduceJob => j !== undefined);
}

export function runningJob(): ReproduceJob | null {
  return listJobs().find((j) => j.status === "running") ?? null;
}

function pushTail(buf: string[], chunk: string): void {
  for (const line of chunk.split(/\r?\n/)) {
    if (!line) continue;
    buf.push(line);
    if (buf.length > TAIL_LINES) buf.splice(0, buf.length - TAIL_LINES);
  }
}

export function startReproduceJob(args: string[]): ReproduceJob {
  const s = store();
  const cwd = quantDir();
  const command = ["uv", "run", "python", "-m", "valuo.reproduce", ...args].join(" ");
  const job: ReproduceJob = {
    id: randomUUID(),
    status: "running",
    command,
    cwd,
    started_at_utc: new Date().toISOString(),
    finished_at_utc: null,
    exit_code: null,
    stdout_tail: [],
    stderr_tail: [],
    error: null,
  };
  s.jobs.set(job.id, job);
  s.order.push(job.id);
  while (s.order.length > KEEP_JOBS) {
    const old = s.order.shift();
    if (old) s.jobs.delete(old);
  }

  if (!fs.existsSync(path.join(cwd, "pyproject.toml"))) {
    job.status = "failed";
    job.error = `quant project not found at ${cwd} (set VALUO_QUANT_DIR)`;
    job.finished_at_utc = new Date().toISOString();
    return job;
  }

  let child;
  try {
    child = spawn("uv", ["run", "python", "-m", "valuo.reproduce", ...args], {
      cwd,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (err) {
    job.status = "failed";
    job.error = err instanceof Error ? err.message : String(err);
    job.finished_at_utc = new Date().toISOString();
    return job;
  }
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (d: string) => pushTail(job.stdout_tail, d));
  child.stderr.on("data", (d: string) => pushTail(job.stderr_tail, d));
  child.on("error", (err) => {
    job.status = "failed";
    job.error = `${err.name}: ${err.message}`;
    job.finished_at_utc = new Date().toISOString();
  });
  child.on("close", (code) => {
    if (job.status === "running") {
      job.exit_code = code;
      job.status = code === 0 ? "succeeded" : "failed";
      job.finished_at_utc = new Date().toISOString();
    }
  });
  return job;
}
