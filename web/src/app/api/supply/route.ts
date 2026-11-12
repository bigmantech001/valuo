import { NextRequest, NextResponse } from "next/server";
import { rawToFloat } from "@/lib/format";
import { rpcEndpoint } from "@/lib/nearRpc";
import { clientIp, createLimiter, tooManyRequests } from "@/lib/rateLimit";
import type { SupplyReading } from "@/components/landing/landingData";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const TTL_MS = 60_000;
/** After a failed read, answer with the same error for this long instead of calling the RPC again. */
const FAILURE_TTL_MS = 10_000;
const TIMEOUT_MS = 5000;
const NO_STORE = { "Cache-Control": "no-store" };

// Cached answers cost nothing upstream, so the cap is per client only; the 60 s cache plus the
// single in-flight promise bound outbound RPC calls to about one a minute per server process.
const limit = createLimiter({ perIp: 20, windowMs: 60_000 });

let cache: { atMs: number; reading: SupplyReading } | null = null;
let inflight: Promise<SupplyReading> | null = null;
let lastFailure: { atMs: number; reason: string } | null = null;

const failure = (reason: string) => NextResponse.json({ error: `NEAR RPC total supply read failed: ${reason}` }, { status: 502, headers: NO_STORE });

/** yoctoNEAR decimal string from the block header -> NEAR; null unless it is a positive integer string. */
function yoctoToNear(raw: unknown): number | null {
  if (typeof raw !== "string" || raw.length > 45) return null;
  const v = rawToFloat(raw, 24);
  return v !== null && Number.isFinite(v) && v > 0 ? v : null;
}

async function readSupply(): Promise<SupplyReading> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(rpcEndpoint(), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: "valuo-web", method: "block", params: { finality: "final" } }),
      signal: controller.signal,
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = (await res.json()) as { result?: { header?: Record<string, unknown> }; error?: unknown };
    if (body.error) throw new Error("RPC returned an error object");
    const header = body.result?.header;
    const height = header?.height;
    const supply = yoctoToNear(header?.total_supply);
    const tsRaw = header?.timestamp_nanosec ?? header?.timestamp;
    const tsMs = (typeof tsRaw === "string" ? Number(tsRaw) : typeof tsRaw === "number" ? tsRaw : NaN) / 1e6;
    if (typeof height !== "number" || !Number.isSafeInteger(height) || height <= 0) throw new Error("malformed block header: height");
    if (supply === null) throw new Error("malformed block header: total_supply");
    if (!Number.isFinite(tsMs) || tsMs <= 0) throw new Error("malformed block header: timestamp");
    return { block_height: height, block_timestamp_utc: new Date(tsMs).toISOString(), total_supply_near: supply, fetched_at_utc: new Date().toISOString() };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * GET /api/supply -> { block_height, block_timestamp_utc, total_supply_near, fetched_at_utc, cached }
 * One `block {"finality":"final"}` header read from NEAR mainnet RPC (endpoint from NEAR_RPC_URL, as
 * the freshness check uses), cached in memory for 60 s. Failure -> 502 { error } (held for 10 s), never a
 * guessed or stale value.
 */
export async function GET(req: NextRequest): Promise<Response> {
  const decision = limit(clientIp(req));
  if (!decision.ok) return tooManyRequests(decision, "supply reading");

  if (cache && Date.now() - cache.atMs < TTL_MS) return NextResponse.json({ ...cache.reading, cached: true }, { status: 200, headers: NO_STORE });

  if (lastFailure && Date.now() - lastFailure.atMs < FAILURE_TTL_MS) return failure(lastFailure.reason);

  try {
    inflight ??= readSupply().finally(() => {
      inflight = null;
    });
    const reading = await inflight;
    cache = { atMs: Date.now(), reading };
    lastFailure = null;
    return NextResponse.json({ ...reading, cached: false }, { status: 200, headers: NO_STORE });
  } catch (err) {
    const reason = err instanceof Error ? (err.name === "AbortError" ? `timeout after ${TIMEOUT_MS} ms` : err.message) : "unknown error";
    lastFailure = { atMs: Date.now(), reason };
    return failure(reason);
  }
}
