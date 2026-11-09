import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { canonicalJson, sha256Hex } from "./hash";
import { buildManifestIndex } from "./manifestIndex";
import { artifactsDir, loadManifest } from "./snapshot";
import type { Manifest, RawRecord } from "./types";
import { jsonDiffSummary, rpcRequestBody, type DiffSummary, type RefetchResponse } from "./verify";

/**
 * Server half of in-browser verification (/api/raw, /api/refetch).
 *
 * Raw files: the quant engine writes the exact HTTP response body (no compression, no re-encoding) to
 * `artifacts/raw/<source>__<name>.json|.txt` and records `sha256(body)` in the manifest
 * (quant/valuo/provenance.py::write_raw). /api/raw streams those bytes unchanged so the browser can hash
 * them itself. Paths come only from the manifest's `raw_path` and must resolve inside `<artifacts>/raw`.
 */

export class VerifyError extends Error {
  constructor(
    message: string,
    public status: number,
    public reason?: string,
  ) {
    super(message);
  }
}

/** Resolve a manifest raw_path ("artifacts/raw/x.json") to an absolute path strictly inside <artifacts>/raw. */
export async function resolveRawPath(rawPath: string | null | undefined): Promise<string> {
  if (!rawPath) throw new VerifyError("this record has no stored bytes (the request failed before a response)", 404);
  if (rawPath.includes("\0")) throw new VerifyError("invalid raw_path", 400);
  const dir = artifactsDir();
  const rawDir = path.join(dir, "raw");
  const posix = rawPath.replace(/\\/g, "/");
  // Manifest convention: relative to repo root, i.e. "artifacts/raw/<file>". Anything else is resolved
  // against the artifacts dir and still has to land inside artifacts/raw.
  const rel = posix.startsWith("artifacts/") ? posix.slice("artifacts/".length) : posix;
  const candidate = path.isAbsolute(rel) ? path.resolve(rel) : path.resolve(dir, rel);
  const inside = (p: string, root: string) => p.startsWith(root + path.sep);
  if (!inside(candidate, rawDir)) throw new VerifyError("raw_path resolves outside artifacts/raw", 400);
  let real: string;
  let realRaw: string;
  try {
    [real, realRaw] = await Promise.all([fs.realpath(candidate), fs.realpath(rawDir)]);
  } catch {
    throw new VerifyError("raw file not found on disk", 404);
  }
  if (!inside(real, realRaw)) throw new VerifyError("raw_path resolves outside artifacts/raw", 400);
  return real;
}

/** Most recent manifest record for (source, name), as the drawer and the Python ledger index it. */
export async function findRecord(source: string | null, name: string | null): Promise<{ manifest: Manifest; record: RawRecord }> {
  if (!source || !name || source.length > 64 || name.length > 256) throw new VerifyError("source and name are required", 400, "bad-request");
  const manifest = await loadManifest();
  if (!manifest) throw new VerifyError("artifacts/manifest.json not found: run make reproduce", 404, "no-manifest");
  const record = buildManifestIndex(manifest).get(source, name);
  if (!record) throw new VerifyError(`no manifest record for ${source}/${name}`, 404, "unknown-record");
  return { manifest, record };
}

export async function readRawBytes(record: RawRecord): Promise<Buffer> {
  return fs.readFile(await resolveRawPath(record.raw_path));
}

/** Hosts that appear in the manifest's record URLs; /api/refetch only talks to these, over HTTPS. */
export function allowedHosts(manifest: Manifest): Set<string> {
  const hosts = new Set<string>();
  for (const r of manifest.records) {
    try {
      const u = new URL(r.url);
      if (u.protocol === "https:") hosts.add(u.hostname.toLowerCase());
    } catch {
      /* ignore malformed */
    }
  }
  return hosts;
}

export function assertAllowedUrl(url: string, manifest: Manifest): URL {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    throw new VerifyError("invalid URL", 400, "bad-request");
  }
  if (u.protocol !== "https:" || u.username || u.password || (u.port && u.port !== "443")) {
    throw new VerifyError("only plain https URLs on the default port are re-fetched", 400, "host-not-allowlisted");
  }
  if (!allowedHosts(manifest).has(u.hostname.toLowerCase())) {
    throw new VerifyError(`host ${u.hostname} is not one of the hosts recorded in the manifest`, 400, "host-not-allowlisted");
  }
  return u;
}

/** Rebuild a NEAR RPC POST body and confirm it hashes to the manifest's request_body_sha256. */
async function rebuildRpcBody(manifest: Manifest, record: RawRecord): Promise<string> {
  if (!record.request_body_sha256) throw new VerifyError("no request_body_sha256 recorded for this POST", 422, "post-body-not-stored");
  const index = buildManifestIndex(manifest);
  // block:pred_of:<h> was requested by the prev_hash read from block:<h>'s response; read it from the stored raw file.
  const prevHashes = new Map<number, string | null>();
  const pred = /^block:pred_of:(\d+)$/.exec(record.name);
  if (pred) {
    const h = Number(pred[1]);
    const parent = index.get("near_rpc", `block:${h}`) ?? index.get("near_rpc_archival", `block:${h}`);
    let prev: string | null = null;
    if (parent) {
      try {
        const parsed = JSON.parse((await readRawBytes(parent)).toString("utf8")) as { result?: { header?: { prev_hash?: string } } };
        prev = parsed.result?.header?.prev_hash ?? null;
      } catch {
        prev = null;
      }
    }
    prevHashes.set(h, prev);
  }
  const body = rpcRequestBody(record.name, (h) => prevHashes.get(h) ?? null);
  if (!body) throw new VerifyError(`cannot rebuild the JSON-RPC body for ${record.name}`, 422, "post-body-not-stored");
  const text = canonicalJson(body);
  if (sha256Hex(text) !== record.request_body_sha256) {
    throw new VerifyError("the rebuilt JSON-RPC body does not hash to the manifest's request_body_sha256; not re-issuing a different request", 422, "post-body-not-stored");
  }
  return text;
}

const USER_AGENT = "valuo-web/0.1.0 (reproducible research; provenance re-fetch)";
const MAX_BYTES = 32 * 1024 * 1024;

/**
 * Re-issue a manifest record's request and compare the live body with the stored one.
 * GET: the recorded URL as-is. POST: only NEAR JSON-RPC, and only when the rebuilt body matches the recorded
 * request_body_sha256 (1Click / Relay quote bodies are not stored, only their hash, so they are refused).
 */
export async function refetchRecord(manifest: Manifest, record: RawRecord, timeoutMs = 10_000): Promise<RefetchResponse> {
  const url = assertAllowedUrl(record.url, manifest);
  const method = record.method.toUpperCase();
  let body: string | undefined;
  let bodyVerified: boolean | undefined;
  if (method === "POST") {
    if (!record.source.startsWith("near_rpc")) {
      throw new VerifyError(
        "this POST request body is not stored in the manifest (only its SHA-256), so it cannot be re-issued exactly; re-run the quote race instead",
        422,
        "post-body-not-stored",
      );
    }
    body = await rebuildRpcBody(manifest, record);
    bodyVerified = true;
  } else if (method !== "GET") {
    throw new VerifyError(`method ${method} is not re-fetched`, 422, "bad-request");
  }

  const started = Date.now();
  const fetchedAt = new Date().toISOString();
  const base = {
    source: record.source,
    name: record.name,
    url: record.url,
    method,
    fetched_at: fetchedAt,
    stored_sha256: record.sha256,
    stored_fetched_at: record.fetched_at_utc,
    request_body_verified: bodyVerified,
  };
  let res: Response;
  let bytes: Buffer;
  let answeredUrl = url;
  let note: string | null = null;
  try {
    ({ res, bytes } = await doFetch(url, method, body, timeoutMs));
    // Same routing as quant/valuo/provenance.py::near_rpc_call: a historical block the primary RPC has
    // garbage-collected is retried on the archival node recorded in the manifest.
    if (record.source === "near_rpc" && body && isGcBlockError(bytes)) {
      const archival = manifest.records.find((r) => r.source === "near_rpc_archival")?.url;
      if (archival) {
        answeredUrl = assertAllowedUrl(archival, manifest);
        ({ res, bytes } = await doFetch(answeredUrl, method, body, timeoutMs));
        note = `primary RPC no longer serves this block (garbage collected); re-issued on the archival node ${answeredUrl.hostname}`;
      }
    }
  } catch (e) {
    const msg = e instanceof Error ? (e.name === "TimeoutError" ? `timed out after ${timeoutMs} ms` : e.message) : String(e);
    return { ...base, status: null, bytes: 0, sha256: null, latency_ms: Date.now() - started, changed: null, diff_summary: null, error: msg, note };
  }
  const sha = sha256Hex(bytes);
  let diff: DiffSummary | null = null;
  if (sha !== record.sha256) {
    let stored: unknown;
    let live: unknown;
    let parsedBoth = true;
    try {
      stored = JSON.parse((await readRawBytes(record)).toString("utf8"));
      live = JSON.parse(bytes.toString("utf8"));
    } catch {
      parsedBoth = false;
    }
    diff = parsedBoth
      ? jsonDiffSummary(stored, live)
      : { kind: "non-json", added_keys: [], removed_keys: [], changed_numeric: [], changed_numeric_total: 0, array_length_changes: [], changed_other_total: 0, truncated: false, max_depth: 0 };
  }
  return {
    ...base,
    status: res.status,
    bytes: bytes.length,
    sha256: sha,
    latency_ms: Date.now() - started,
    changed: sha !== record.sha256,
    diff_summary: diff,
    error: res.ok ? null : `HTTP ${res.status}`,
    note,
    answered_url: answeredUrl.toString() === url.toString() ? undefined : answeredUrl.toString(),
  };
}

async function doFetch(url: URL, method: string, body: string | undefined, timeoutMs: number): Promise<{ res: Response; bytes: Buffer }> {
  const res = await fetch(url, {
    method,
    body,
    headers: { "User-Agent": USER_AGENT, Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
    redirect: "error",
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
  const len = Number(res.headers.get("content-length") ?? "0");
  if (len > MAX_BYTES) throw new Error(`response too large (${len} bytes)`);
  const bytes = Buffer.from(await res.arrayBuffer());
  if (bytes.length > MAX_BYTES) throw new Error(`response too large (${bytes.length} bytes)`);
  return { res, bytes };
}

const GC_CAUSES = new Set(["GARBAGE_COLLECTED_BLOCK", "UNKNOWN_BLOCK"]);
const GC_TEXT = ["garbage collected", "unknown block", "db not found error: block"];

/** Mirrors provenance.is_gc_block_error. */
function isGcBlockError(bytes: Buffer): boolean {
  let parsed: unknown;
  try {
    parsed = JSON.parse(bytes.toString("utf8"));
  } catch {
    return false;
  }
  const err = (parsed as { error?: unknown })?.error;
  if (!err || typeof err !== "object") return false;
  const e = err as { cause?: { name?: unknown }; name?: unknown; message?: unknown; data?: unknown };
  if (typeof e.cause?.name === "string" && GC_CAUSES.has(e.cause.name)) return true;
  if (typeof e.name === "string" && GC_CAUSES.has(e.name)) return true;
  const text = `${typeof e.message === "string" ? e.message : ""} ${typeof e.data === "string" ? e.data : ""}`.toLowerCase();
  return GC_TEXT.some((t) => text.includes(t));
}
