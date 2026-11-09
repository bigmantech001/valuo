import "server-only";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * In-memory token buckets for the API routes that make outbound requests or read many files.
 * One bucket per client IP plus one global bucket per limiter. State lives in the Node process,
 * so limits reset on restart and are per instance; that is enough to stop a single browser tab or
 * script from hammering upstream APIs through this server. Not a substitute for an edge WAF.
 */

interface Bucket {
  tokens: number;
  updatedMs: number;
}

export interface LimiterOptions {
  /** requests allowed per client IP per window */
  perIp: number;
  /** requests allowed across all clients per window (omit for no global cap) */
  global?: number;
  windowMs: number;
}

export interface LimitDecision {
  ok: boolean;
  /** seconds until one token is available in the bucket that refused */
  retryAfterS: number;
  scope: "ip" | "global" | null;
  remaining: number;
}

const MAX_TRACKED_IPS = 10_000;

function refill(b: Bucket, capacity: number, windowMs: number, now: number): void {
  const rate = capacity / windowMs; // tokens per ms
  b.tokens = Math.min(capacity, b.tokens + (now - b.updatedMs) * rate);
  b.updatedMs = now;
}

function waitS(b: Bucket, capacity: number, windowMs: number): number {
  const rate = capacity / windowMs;
  return Math.max(1, Math.ceil((1 - b.tokens) / rate / 1000));
}

export function createLimiter(opts: LimiterOptions) {
  const buckets = new Map<string, Bucket>();
  const global: Bucket | null = opts.global ? { tokens: opts.global, updatedMs: Date.now() } : null;

  function prune(now: number): void {
    if (buckets.size < MAX_TRACKED_IPS) return;
    // Full buckets carry no state worth keeping; drop them first, then the oldest entries.
    for (const [k, b] of buckets) {
      refill(b, opts.perIp, opts.windowMs, now);
      if (b.tokens >= opts.perIp) buckets.delete(k);
    }
    if (buckets.size >= MAX_TRACKED_IPS) {
      const drop = buckets.size - MAX_TRACKED_IPS + 1;
      let i = 0;
      for (const k of buckets.keys()) {
        if (i++ >= drop) break;
        buckets.delete(k);
      }
    }
  }

  return function take(ip: string): LimitDecision {
    const now = Date.now();
    prune(now);
    let b = buckets.get(ip);
    if (!b) {
      b = { tokens: opts.perIp, updatedMs: now };
      buckets.set(ip, b);
    }
    refill(b, opts.perIp, opts.windowMs, now);
    if (b.tokens < 1) return { ok: false, retryAfterS: waitS(b, opts.perIp, opts.windowMs), scope: "ip", remaining: 0 };
    if (global && opts.global) {
      refill(global, opts.global, opts.windowMs, now);
      if (global.tokens < 1) return { ok: false, retryAfterS: waitS(global, opts.global, opts.windowMs), scope: "global", remaining: 0 };
      global.tokens -= 1;
    }
    b.tokens -= 1;
    return { ok: true, retryAfterS: 0, scope: null, remaining: Math.floor(b.tokens) };
  };
}

/** Best-effort client IP: first X-Forwarded-For hop, then X-Real-IP, else a shared "local" key. */
export function clientIp(req: NextRequest): string {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) {
    const first = xff.split(",")[0]?.trim();
    if (first) return first;
  }
  return req.headers.get("x-real-ip")?.trim() || "local";
}

/** 429 JSON body with a Retry-After header. */
export function tooManyRequests(d: LimitDecision, what: string): Response {
  const msg =
    d.scope === "global"
      ? `This server is handling too many ${what} requests right now. Retry in ${d.retryAfterS} s.`
      : `Too many ${what} requests from this address. Retry in ${d.retryAfterS} s.`;
  return NextResponse.json(
    { error: msg, reason: "rate-limited", scope: d.scope, retry_after_s: d.retryAfterS },
    { status: 429, headers: { "Retry-After": String(d.retryAfterS), "Cache-Control": "no-store" } },
  );
}
