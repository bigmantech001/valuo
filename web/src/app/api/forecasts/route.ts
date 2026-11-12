import { NextRequest, NextResponse } from "next/server";
import { serverEnv } from "@/lib/env";
import { FORECAST_PATH, SOCIAL_CONTRACT, isAccountId, parseForecastTree, scoreForecast, writeTimeConsistent, type BlockAnchor, type ForecastEntry, type ForecastScore, type Realized } from "@/lib/forecast";
import { rpcEndpoint } from "@/lib/nearRpc";
import { clientIp, createLimiter, tooManyRequests } from "@/lib/rateLimit";
import { loadArtifacts } from "@/lib/snapshot";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/forecasts[?account=<id>]
 *   -> { forecasts: [{account, key, block_height, value, verified_onchain, score}], realized, sources, ... }
 * GET /api/forecasts?storage_for=<id>
 *   -> { account, balance: {total, available} | null, bounds: {min, max} | null }   (social.near view calls)
 *
 * Discovery: a wildcard-account `get` (["*\/valuo/forecast/*"]) exceeds the view-call gas limit on social.near
 * mainnet (HostError(GasLimitExceeded), checked Nov 2026), so the account list comes from the public SocialDB
 * indexer api.near.social, which serves the same `get` semantics key-free. Every account it reports is then
 * re-read directly from social.near over NEAR RPC (`get` ["<account>/valuo/forecast/*"], with_block_height).
 * When that read succeeds, its entries replace the indexer's for the account (`verified_onchain: true`; indexer
 * entries the chain does not hold are dropped and counted); when it fails, the indexer entries are kept, flagged
 * `verified_onchain: false`. `?account=` adds one
 * account read straight from RPC (used right after a publish, before the indexer catches up).
 * Cached in memory for 30 s; 8 s timeout per upstream call. Rate limited like the other routes.
 */
const limit = createLimiter({ perIp: 30, global: 300, windowMs: 5 * 60_000 });
const CACHE_MS = 30_000;
const TIMEOUT_MS = 8_000;
const MAX_VERIFY_ACCOUNTS = 60;
const VERIFY_CONCURRENCY = 6;
const PATTERN = `*/${FORECAST_PATH.join("/")}/*`;

function indexerUrl(): string {
  return serverEnv("SOCIALDB_API_URL", "https://api.near.social").replace(/\/+$/, "");
}

async function withTimeout<T>(fn: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fn(controller.signal);
  } finally {
    clearTimeout(timer);
  }
}

/** social.near view call over JSON-RPC; returns the parsed JSON result. */
async function socialView(method: string, args: object): Promise<unknown> {
  return withTimeout(async (signal) => {
    const res = await fetch(rpcEndpoint(), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: "valuo-forecasts",
        method: "query",
        params: { request_type: "call_function", finality: "final", account_id: SOCIAL_CONTRACT, method_name: method, args_base64: Buffer.from(JSON.stringify(args)).toString("base64") },
      }),
      signal,
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`RPC HTTP ${res.status}`);
    const body = (await res.json()) as { result?: { result?: number[]; error?: string }; error?: { message?: string; data?: unknown } };
    if (body.error) throw new Error(body.error.message ?? JSON.stringify(body.error.data ?? body.error));
    if (body.result?.error) throw new Error(body.result.error);
    if (!Array.isArray(body.result?.result)) throw new Error("malformed RPC view result");
    const text = Buffer.from(body.result.result).toString("utf8");
    return text ? JSON.parse(text) : null;
  });
}

async function readAccountDirect(account: string): Promise<unknown> {
  return socialView("get", { keys: [`${account}/${FORECAST_PATH.join("/")}/*`], options: { with_block_height: true } });
}

async function readIndexer(): Promise<unknown> {
  return withTimeout(async (signal) => {
    const res = await fetch(`${indexerUrl()}/get`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ keys: [PATTERN], options: { with_block_height: true } }),
      signal,
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`indexer HTTP ${res.status}`);
    const len = Number(res.headers.get("content-length") ?? 0);
    if (len > 5_000_000) throw new Error("indexer response too large");
    const text = await res.text();
    if (text.length > 5_000_000) throw new Error("indexer response too large");
    return JSON.parse(text);
  });
}

async function mapLimit<T, R>(items: T[], n: number, fn: (t: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let i = 0;
  await Promise.all(
    Array.from({ length: Math.min(n, items.length) }, async () => {
      while (i < items.length) {
        const idx = i++;
        out[idx] = await fn(items[idx]);
      }
    }),
  );
  return out;
}

interface Board {
  entries: ForecastEntry[];
  rejected: number;
  indexer: { url: string; ok: boolean; error: string | null; accounts: number };
  rpc: { url: string; verified_accounts: number; not_on_chain: number; failed_accounts: number; unverified_reason: string | null };
  fetched_at: string;
}

let cache: { at: number; board: Board } | null = null;
let inflight: Promise<Board> | null = null;

async function buildBoard(): Promise<Board> {
  const url = indexerUrl();
  let tree: unknown = {};
  let indexerError: string | null = null;
  try {
    tree = await readIndexer();
  } catch (e) {
    indexerError = e instanceof Error ? e.message : String(e);
  }
  const parsed = parseForecastTree(tree);
  const accounts = [...new Set(parsed.entries.map((e) => e.account))];
  const toVerify = accounts.slice(0, MAX_VERIFY_ACCOUNTS);
  let failed = 0;
  // Chain is the source of truth: for every account social.near answered for, its entries replace the indexer's.
  const onchain = new Map<string, ForecastEntry[]>();
  await mapLimit(toVerify, VERIFY_CONCURRENCY, async (a) => {
    try {
      const d = parseForecastTree(await readAccountDirect(a));
      onchain.set(
        a,
        d.entries.filter((e) => e.account === a).map((e) => ({ ...e, verified_onchain: true })),
      );
    } catch {
      failed++;
    }
  });
  const notOnChain = parsed.entries.filter((e) => onchain.has(e.account) && !onchain.get(e.account)!.some((d) => d.key === e.key)).length;
  const entries = [...[...onchain.values()].flat(), ...parsed.entries.filter((e) => !onchain.has(e.account))];
  return {
    entries,
    rejected: parsed.rejected,
    indexer: { url: `${url}/get`, ok: indexerError === null, error: indexerError, accounts: accounts.length },
    rpc: {
      url: rpcEndpoint(),
      verified_accounts: onchain.size,
      not_on_chain: notOnChain,
      failed_accounts: failed,
      unverified_reason: accounts.length > MAX_VERIFY_ACCOUNTS ? `only the first ${MAX_VERIFY_ACCOUNTS} accounts are re-read from RPC per refresh` : null,
    },
    fetched_at: new Date().toISOString(),
  };
}

async function board(): Promise<Board> {
  if (cache && Date.now() - cache.at < CACHE_MS) return cache.board;
  if (!inflight) {
    inflight = buildBoard()
      .then((b) => {
        cache = { at: Date.now(), board: b };
        return b;
      })
      .finally(() => {
        inflight = null;
      });
  }
  return inflight;
}

function realizedFrom(snapshot: Awaited<ReturnType<typeof loadArtifacts>>["snapshot"], sha: string | null): Realized | null {
  const p = snapshot?.intents_forensics?.price;
  const price = p?.current_usd;
  if (typeof price !== "number" || !Number.isFinite(price) || price <= 0) return null;
  const asOf = p?.fetched_at ?? snapshot?.generated_at_utc;
  if (!asOf || Number.isNaN(Date.parse(asOf))) return null;
  return { price_usd: price, as_of: asOf, source: `latest_snapshot.json intents_forensics.price.current_usd (${p?.source ?? "nearstats"})`, snapshot_sha256: sha };
}

/** Rows returned at most; the newest by block height win. */
const MAX_ROWS = 200;

function blockAnchor(snapshot: Awaited<ReturnType<typeof loadArtifacts>>["snapshot"]): BlockAnchor | null {
  const h = snapshot?.near_rpc?.block_height;
  const t = snapshot?.generated_at_utc ? Date.parse(snapshot.generated_at_utc) : NaN;
  return typeof h === "number" && h > 0 && Number.isFinite(t) ? { block_height: h, time_ms: t } : null;
}

export async function GET(req: NextRequest): Promise<Response> {
  const decision = limit(clientIp(req));
  if (!decision.ok) return tooManyRequests(decision, "forecast board");
  const sp = req.nextUrl.searchParams;

  const storageFor = sp.get("storage_for");
  if (storageFor !== null) {
    if (!isAccountId(storageFor)) return NextResponse.json({ error: "storage_for must be a NEAR account id", reason: "bad-request" }, { status: 400 });
    try {
      const [balance, bounds] = await Promise.all([socialView("storage_balance_of", { account_id: storageFor }), socialView("storage_balance_bounds", {})]);
      const b = balance as { total?: unknown; available?: unknown } | null;
      const bd = bounds as { min?: unknown; max?: unknown } | null;
      return NextResponse.json(
        {
          account: storageFor,
          balance: b && typeof b.total === "string" && typeof b.available === "string" ? { total: b.total, available: b.available } : null,
          bounds: bd && typeof bd.min === "string" ? { min: bd.min, max: typeof bd.max === "string" ? bd.max : null } : null,
          rpc: rpcEndpoint(),
        },
        { headers: { "Cache-Control": "no-store" } },
      );
    } catch (e) {
      return NextResponse.json({ error: `social.near storage read failed: ${e instanceof Error ? e.message : String(e)}` }, { status: 502 });
    }
  }

  const extra = sp.get("account");
  if (extra !== null && !isAccountId(extra)) return NextResponse.json({ error: "account must be a NEAR account id", reason: "bad-request" }, { status: 400 });

  const [b, artifacts] = await Promise.all([board(), loadArtifacts()]);
  let entries = b.entries.map((e) => ({ ...e }));
  let extraError: string | null = null;
  if (extra) {
    try {
      const direct = parseForecastTree(await readAccountDirect(extra));
      const have = new Set(entries.map((e) => `${e.account}/${e.key}`));
      for (const e of direct.entries) {
        // read straight from social.near, so it is on-chain by construction
        e.verified_onchain = true;
        if (!have.has(`${e.account}/${e.key}`)) entries.push(e);
      }
    } catch (e) {
      extraError = e instanceof Error ? e.message : String(e);
    }
  }
  // Drop records whose declared creation time disagrees with the block that stored them (backdated forecasts).
  const anchor = blockAnchor(artifacts.snapshot);
  const before = entries.length;
  entries = entries.filter((e) => writeTimeConsistent(e, anchor));
  const backdated = before - entries.length;
  entries = entries.sort((x, y) => (y.block_height ?? 0) - (x.block_height ?? 0) || y.key.localeCompare(x.key)).slice(0, MAX_ROWS);

  const realized = realizedFrom(artifacts.snapshot, artifacts.manifest?.snapshot_sha256 ?? null);
  const forecasts: (ForecastEntry & { score: ForecastScore })[] = entries.map((e) => ({ ...e, score: scoreForecast(e.value, realized) }));
  const resolved = forecasts.filter((f) => f.score.status === "resolved");
  const mape = resolved.length ? resolved.reduce((s, f) => s + (f.score.abs_error_pct ?? 0), 0) / resolved.length : null;

  return NextResponse.json(
    {
      forecasts,
      count: forecasts.length,
      resolved_count: resolved.length,
      mean_abs_error_pct_resolved: mape,
      rejected_entries: b.rejected + backdated,
      backdated_entries: backdated,
      realized,
      sources: { indexer: b.indexer, rpc: b.rpc, contract: SOCIAL_CONTRACT, pattern: PATTERN, extra_account: extra, extra_account_error: extraError },
      fetched_at: b.fetched_at,
      cache_s: CACHE_MS / 1000,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
