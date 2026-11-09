import "server-only";
import { serverEnv } from "./env";
import type { Freshness, Snapshot } from "./types";

/**
 * One live `block {"finality":"final"}` call against NEAR mainnet to measure how far the
 * snapshot is behind the chain head. 5 s AbortController timeout; any failure yields nulls
 * plus the error string rather than a guessed height.
 */

export interface LiveHead {
  height: number;
  hash: string;
  timestamp_ns: number;
  timestamp_utc: string;
  endpoint: string;
}

export function rpcEndpoint(): string {
  return serverEnv("NEAR_RPC_URL", "https://free.rpc.fastnear.com");
}

export async function fetchLiveHead(timeoutMs = 5000): Promise<LiveHead> {
  const endpoint = rpcEndpoint();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: "valuo-web", method: "block", params: { finality: "final" } }),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = (await res.json()) as { result?: { header?: Record<string, unknown> }; error?: { message?: string; data?: unknown } };
    if (body.error) throw new Error(body.error.message ?? JSON.stringify(body.error.data ?? body.error));
    const header = body.result?.header;
    const height = header?.height;
    const hash = header?.hash;
    const tsRaw = header?.timestamp_nanosec ?? header?.timestamp;
    if (typeof height !== "number" || typeof hash !== "string") throw new Error("malformed block header");
    const timestamp_ns = typeof tsRaw === "string" ? Number(tsRaw) : typeof tsRaw === "number" ? tsRaw : NaN;
    const timestamp_utc = Number.isFinite(timestamp_ns) ? new Date(timestamp_ns / 1e6).toISOString() : new Date().toISOString();
    return { height, hash, timestamp_ns, timestamp_utc, endpoint };
  } finally {
    clearTimeout(timer);
  }
}

export async function buildFreshness(snapshot: Snapshot | null, timeoutMs = 5000): Promise<Freshness> {
  const snapshot_block = snapshot?.near_rpc?.block_height ?? null;
  const snapshot_timestamp_utc = snapshot?.near_rpc?.timestamp_utc ?? null;
  const checked_at_utc = new Date().toISOString();
  try {
    const head = await fetchLiveHead(timeoutMs);
    const snapTs = snapshot_timestamp_utc ? Date.parse(snapshot_timestamp_utc) : NaN;
    const liveTs = Date.parse(head.timestamp_utc);
    return {
      snapshot_block,
      snapshot_timestamp_utc,
      live_block: head.height,
      live_timestamp_utc: head.timestamp_utc,
      blocks_behind: snapshot_block === null ? null : head.height - snapshot_block,
      seconds_behind: Number.isFinite(snapTs) && Number.isFinite(liveTs) ? Math.round((liveTs - snapTs) / 1000) : null,
      rpc_endpoint: head.endpoint,
      checked_at_utc,
      error: null,
    };
  } catch (err) {
    const message = err instanceof Error ? (err.name === "AbortError" ? `timeout after ${timeoutMs} ms` : err.message) : String(err);
    return {
      snapshot_block,
      snapshot_timestamp_utc,
      live_block: null,
      live_timestamp_utc: null,
      blocks_behind: null,
      seconds_behind: null,
      rpc_endpoint: rpcEndpoint(),
      checked_at_utc,
      error: message,
    };
  }
}
