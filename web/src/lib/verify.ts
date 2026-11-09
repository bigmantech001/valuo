/**
 * In-browser provenance verification helpers (isomorphic: no Node-only imports).
 *
 * - `sha256HexBrowser`: SHA-256 via WebCrypto, used by the "Verify sources" drawer to re-hash the exact
 *   raw bytes served by /api/raw and compare them with the manifest digest, so the check does not rely on
 *   the server's own claim.
 * - `rpcRequestBody`: rebuilds the JSON-RPC body the quant engine sent for a NEAR RPC record from the
 *   record name. The manifest stores only `request_body_sha256` (sha256 of the canonical JSON body), so
 *   /api/refetch re-issues an RPC call only when the rebuilt body hashes to exactly that digest.
 * - `jsonDiffSummary`: bounded structural diff between the stored and the re-fetched JSON body.
 */

/** Hex SHA-256 of bytes using WebCrypto (browser, or Node 20+ globalThis.crypto). */
export async function sha256HexBrowser(data: ArrayBuffer | Uint8Array): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) throw new Error("WebCrypto (crypto.subtle) is unavailable: the page must be served over HTTPS or localhost");
  const view = data instanceof Uint8Array ? data : new Uint8Array(data);
  // Copy into a fresh ArrayBuffer so a view over a larger/shared buffer cannot leak extra bytes into the digest.
  const buf = view.slice().buffer;
  const digest = await subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/* ------------------------------------------------------------------------------------------ API shapes */

export interface RawHashResult {
  source: string;
  name: string;
  /** sha256 recorded in the manifest for this row */
  expected: string;
  /** sha256 computed in the browser over the bytes /api/raw returned (null when nothing could be fetched) */
  actual: string | null;
  bytes: number | null;
  matches: boolean | null;
  /** reason when the check could not run (no stored bytes, HTTP error, WebCrypto unavailable) */
  error?: string | null;
}

export interface NumericChange {
  path: string;
  /** numbers stay numbers; numeric strings (yoctoNEAR balances) stay strings so no precision is lost */
  old: number | string;
  new: number | string;
}

export interface LengthChange {
  path: string;
  old: number;
  new: number;
}

export interface DiffSummary {
  kind: "json" | "non-json";
  /** top-level keys present in the live body but not in the stored one */
  added_keys: string[];
  /** top-level keys present in the stored body but not in the live one */
  removed_keys: string[];
  /** up to `maxChanges` changed numeric leaves, shallowest first */
  changed_numeric: NumericChange[];
  /** total changed numeric leaves found within the depth/visit bounds */
  changed_numeric_total: number;
  /** arrays whose length changed (up to `maxChanges`) */
  array_length_changes: LengthChange[];
  /** changed string / boolean / null leaves within the bounds (count only) */
  changed_other_total: number;
  /** true when the traversal hit the depth or visit bound */
  truncated: boolean;
  max_depth: number;
}

export interface RefetchResponse {
  source: string;
  name: string;
  url: string;
  method: string;
  /** HTTP status of the live response (null on transport failure / timeout) */
  status: number | null;
  bytes: number;
  sha256: string | null;
  fetched_at: string;
  latency_ms: number;
  stored_sha256: string;
  stored_fetched_at: string;
  /** sha256 != stored sha256 */
  changed: boolean | null;
  /** for POST JSON-RPC records: the rebuilt body hashed to the manifest's request_body_sha256 */
  request_body_verified?: boolean;
  diff_summary: DiffSummary | null;
  error: string | null;
  /** routing note, e.g. primary RPC garbage-collected the block and the archival node answered */
  note?: string | null;
  /** set when a different (allowlisted) endpoint than the recorded URL answered */
  answered_url?: string;
}

export interface RefetchRefusal {
  error: string;
  reason?: "unknown-record" | "post-body-not-stored" | "host-not-allowlisted" | "bad-request" | "no-manifest";
}

/* ------------------------------------------------------------------------------- NEAR JSON-RPC bodies */

export interface RpcBody {
  jsonrpc: "2.0";
  id: "valuo";
  method: string;
  params: unknown;
}

function rpcBody(method: string, params: unknown): RpcBody {
  // Must match quant/valuo/provenance.py::_rpc_body exactly (hashed with canonical JSON).
  return { jsonrpc: "2.0", id: "valuo", method, params };
}

/**
 * Rebuild the JSON-RPC body for a NEAR RPC record name, mirroring quant/valuo/collectors/near_rpc.py:
 *   protocol_config            -> EXPERIMENTAL_protocol_config {finality: final}
 *   block_final                -> block {finality: final}
 *   validators                 -> validators [null]
 *   view_account:<id>          -> query {request_type: view_account, account_id, finality: final}
 *   view_account:<id>@<height> -> query {request_type: view_account, account_id, block_id: height}
 *   block:<height>             -> block {block_id: height}
 *   block:pred_of:<height>     -> block {block_id: prev_hash}; needs `prevHashOf(height)` from the stored
 *                                 raw response of block:<height>
 * Returns null for names it does not know. The caller must still check the canonical-JSON SHA-256 against
 * the record's request_body_sha256 before sending anything.
 */
export function rpcRequestBody(name: string, prevHashOf?: (height: number) => string | null): RpcBody | null {
  if (name === "protocol_config") return rpcBody("EXPERIMENTAL_protocol_config", { finality: "final" });
  if (name === "block_final") return rpcBody("block", { finality: "final" });
  if (name === "validators") return rpcBody("validators", [null]);
  const pred = /^block:pred_of:(\d+)$/.exec(name);
  if (pred) {
    const prev = prevHashOf?.(Number(pred[1])) ?? null;
    return prev ? rpcBody("block", { block_id: prev }) : null;
  }
  const blk = /^block:(\d+)$/.exec(name);
  if (blk) return rpcBody("block", { block_id: Number(blk[1]) });
  const va = /^view_account:([^@]+)(?:@(\d+))?$/.exec(name);
  if (va) {
    const params: Record<string, unknown> = { request_type: "view_account", account_id: va[1] };
    if (va[2] !== undefined) params.block_id = Number(va[2]);
    else params.finality = "final";
    return rpcBody("query", params);
  }
  return null;
}

/* ------------------------------------------------------------------------------------ JSON diff summary */

export interface DiffOptions {
  maxDepth?: number;
  maxChanges?: number;
  /** stop visiting after this many nodes (big DefiLlama chart arrays) */
  maxVisits?: number;
  /** compare at most this many elements per array, index-wise */
  maxArrayItems?: number;
}

const NUMERIC_STRING = /^-?\d+(\.\d+)?$/;

function isObj(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

function joinPath(base: string, key: string | number): string {
  if (typeof key === "number") return `${base}[${key}]`;
  return base ? `${base}.${key}` : key;
}

/**
 * Breadth-first structural diff of two parsed JSON values. Numeric leaves are compared exactly; the first
 * `maxChanges` changes (shallowest first) are listed with old and new values. Bounded by depth, by number of
 * visited nodes and by elements per array, and reports `truncated` when a bound was hit.
 */
export function jsonDiffSummary(oldVal: unknown, newVal: unknown, opts: DiffOptions = {}): DiffSummary {
  const maxDepth = opts.maxDepth ?? 5;
  const maxChanges = opts.maxChanges ?? 10;
  const maxVisits = opts.maxVisits ?? 50_000;
  const maxArrayItems = opts.maxArrayItems ?? 50;

  const out: DiffSummary = {
    kind: "json",
    added_keys: [],
    removed_keys: [],
    changed_numeric: [],
    changed_numeric_total: 0,
    array_length_changes: [],
    changed_other_total: 0,
    truncated: false,
    max_depth: maxDepth,
  };
  if (isObj(oldVal) && isObj(newVal)) {
    out.added_keys = Object.keys(newVal).filter((k) => !(k in oldVal)).sort();
    out.removed_keys = Object.keys(oldVal).filter((k) => !(k in newVal)).sort();
  }

  const queue: Array<{ path: string; a: unknown; b: unknown; depth: number }> = [{ path: "", a: oldVal, b: newVal, depth: 0 }];
  let visits = 0;
  for (let head = 0; head < queue.length; head++) {
    if (++visits > maxVisits) {
      out.truncated = true;
      break;
    }
    const { path, a, b, depth } = queue[head];
    if (typeof a === "number" && typeof b === "number") {
      if (a !== b) {
        out.changed_numeric_total++;
        if (out.changed_numeric.length < maxChanges) out.changed_numeric.push({ path: path || "(root)", old: a, new: b });
      }
      continue;
    }
    // Numeric strings (NEAR yoctoNEAR balances, block heights as strings) are reported as numeric changes too.
    if (typeof a === "string" && typeof b === "string") {
      if (a !== b) {
        if (NUMERIC_STRING.test(a) && NUMERIC_STRING.test(b)) {
          out.changed_numeric_total++;
          if (out.changed_numeric.length < maxChanges) out.changed_numeric.push({ path: path || "(root)", old: a, new: b });
        } else out.changed_other_total++;
      }
      continue;
    }
    if (Array.isArray(a) && Array.isArray(b)) {
      if (a.length !== b.length && out.array_length_changes.length < maxChanges) out.array_length_changes.push({ path: path || "(root)", old: a.length, new: b.length });
      if (depth >= maxDepth) {
        out.truncated = true;
        continue;
      }
      const n = Math.min(a.length, b.length);
      if (n > maxArrayItems) out.truncated = true;
      for (let i = 0; i < Math.min(n, maxArrayItems); i++) queue.push({ path: joinPath(path, i), a: a[i], b: b[i], depth: depth + 1 });
      continue;
    }
    if (isObj(a) && isObj(b)) {
      if (depth >= maxDepth) {
        out.truncated = true;
        continue;
      }
      for (const k of Object.keys(a)) if (k in b) queue.push({ path: joinPath(path, k), a: a[k], b: b[k], depth: depth + 1 });
      continue;
    }
    if (a !== b && JSON.stringify(a) !== JSON.stringify(b)) out.changed_other_total++;
  }
  return out;
}

/** One-line human text for a numeric change: "volume30dUsd 3,860,604,915 → 3,882,727,886". */
export function fmtNumericChange(c: NumericChange): string {
  const f = (v: number | string) => {
    if (typeof v === "string") {
      const [int, frac] = v.split(".");
      const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
      return frac !== undefined ? `${grouped}.${frac}` : grouped;
    }
    return Number.isInteger(v) ? v.toLocaleString("en-US") : v.toLocaleString("en-US", { maximumFractionDigits: 6 });
  };
  return `${c.path} ${f(c.old)} → ${f(c.new)}`;
}
