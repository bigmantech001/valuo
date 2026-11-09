import "server-only";
import fs from "node:fs";
import path from "node:path";

/**
 * Server-side env lookup mirroring `quant/valuo/config.py`: the process environment wins,
 * then the repo-root `.env` (python-dotenv `override=False` semantics), so a judge who sets
 * `VALUO_ARTIFACTS_DIR` or `VALUO_BTC_ADDRESS` once at the repo root drives both the quant
 * engine and the web terminal.
 */

let rootEnvCache: Record<string, string> | null = null;

/** `web/` is expected to sit next to `quant/` and `artifacts/`; override with VALUO_REPO_ROOT. */
export function repoRoot(): string {
  const fromEnv = process.env.VALUO_REPO_ROOT;
  if (fromEnv && fromEnv.trim()) return path.resolve(fromEnv.trim());
  return path.resolve(process.cwd(), "..");
}

function parseDotenv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim().replace(/^export\s+/, "");
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    } else {
      const hash = value.indexOf(" #");
      if (hash >= 0) value = value.slice(0, hash).trim();
    }
    if (key) out[key] = value;
  }
  return out;
}

function rootEnv(): Record<string, string> {
  if (rootEnvCache) return rootEnvCache;
  const file = path.join(repoRoot(), ".env");
  try {
    rootEnvCache = fs.existsSync(file) ? parseDotenv(fs.readFileSync(file, "utf8")) : {};
  } catch {
    rootEnvCache = {};
  }
  return rootEnvCache;
}

/** Non-empty value of `key` from process.env, else repo-root `.env`, else `fallback`. */
export function serverEnv(key: string, fallback: string): string;
export function serverEnv(key: string): string | undefined;
export function serverEnv(key: string, fallback?: string): string | undefined {
  const fromProcess = process.env[key];
  if (fromProcess && fromProcess.trim()) return fromProcess.trim();
  const fromFile = rootEnv()[key];
  if (fromFile && fromFile.trim()) return fromFile.trim();
  return fallback;
}

export function serverEnvFlag(key: string): boolean {
  return serverEnv(key) === "1";
}

export function serverEnvNumber(key: string, fallback: number): number {
  const v = serverEnv(key);
  if (v === undefined) return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}
