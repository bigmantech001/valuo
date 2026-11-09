import "server-only";
import { DEFAULT_ADDRESSES, clipToRawAmount, getCorridor, toCorridor, type Addresses, type CorridorDef } from "./corridors";
import { serverEnv, serverEnvNumber } from "./env";
import { rawToFloat } from "./format";
import { EMPTY_SHA256, sha256Hex, sha256Json } from "./hash";
import type {
  CorridorClipResult,
  HeadroomBasis,
  LiveBenchmarkResponse,
  PriceBasis,
  QuoteStatus,
  RawRecord,
  UsdFrictionBasis,
  VenueName,
  VenueQuote,
} from "./types";

/**
 * Live quote race: one corridor x one clip, all venues concurrently, each with its own timeout.
 * A TypeScript port of `quant/valuo/collectors/execution_bench.py` (payloads, parsers, status
 * mapping, `common_price_basis` and `score_cell`), so the browser race and the snapshot measure
 * the same thing:
 *
 *   friction_bps_usd = (in_usd - out_usd) / in_usd x 1e4 with BOTH legs of EVERY venue valued at
 *                      ONE price per cell (`price_basis`): the live 1Click token-list prices
 *                      (`usd_basis = "oneclick_token_list_oracle"`), else - when the token list
 *                      failed - the MEDIAN of the ok venues' own implied destination / origin prices
 *                      (`usd_basis = "median_venue_oracle"`, `common_price_basis`). The venue's own
 *                      USD legs survive as `venue_*` fields; on their own they are not comparable
 *                      across venues (venues mark the same BTC 20-30 bps apart).
 *   friction_bps_raw = (in_raw - out_raw) / in_raw x 1e4, same-asset (USDC -> USDC) corridors only.
 *   headroom_bps     = (out_1click - out_best_competitor) / out_best_competitor x 1e4 on the PHYSICAL
 *                      destination units (`headroom_basis = "dest_units"`): every venue in a cell
 *                      delivers the same asset for the same raw input, so no oracle is needed.
 *   oneclick_rank    = 1 + number of ok competitors that delivered strictly more units.
 *
 * Status mapping (VenueQuote.status), identical to the Python docstring except where noted:
 *   1Click  2xx with `quote`                          -> ok;  4xx "No liquidity available" -> no_liquidity
 *   Relay   errorCode in RELAY_ROUTE_ERROR_CODES      -> unsupported_route;  in RELAY_NO_LIQUIDITY_CODES -> no_liquidity
 *   LI.FI   message "not supported" etc.              -> unsupported_route;  "No available quotes" -> no_liquidity
 *   Across  code AMOUNT_TOO_HIGH                      -> no_liquidity
 *           any other 4xx carrying a `code`           -> unsupported_route  (ROUTE_NOT_ENABLED, INVALID_PARAM, UNSUPPORTED_*;
 *                                                        wider than the Python set, which maps INVALID_PARAM to error)
 *           2xx with isAmountTooLow                   -> error (AMOUNT_TOO_LOW)
 *           declared unsupported (no Bitcoin chain)   -> unsupported_route, verified live against GET /api/chains
 *   anything else (transport error, unknown body)     -> error, with the verbatim message
 * A venue's response is parsed, never synthesised: a failed venue carries the message and null amounts.
 */

const USER_AGENT = "valuo-web/0.1.0 (reproducible research; fetch)";

/** Output order of quotes in a cell (execution_bench.VENUES). */
const VENUE_ORDER: readonly VenueName[] = ["1click", "relay", "lifi", "across"];
const ROUTE_TOOL: Record<"1click" | "relay" | "across", string> = { "1click": "1click-solver-network", relay: "relay", across: "across" };

const RELAY_ROUTE_ERROR_CODES = new Set([
  "INVALID_INPUT_CURRENCY",
  "INVALID_OUTPUT_CURRENCY",
  "UNSUPPORTED_CHAIN",
  "UNSUPPORTED_CURRENCY",
  "UNSUPPORTED_ROUTE",
  "NO_SWAP_ROUTES_FOUND",
  "NO_INTERNAL_SWAP_ROUTES_FOUND",
  "ROUTE_TEMPORARILY_RESTRICTED",
]);
const RELAY_NO_LIQUIDITY_CODES = new Set(["INSUFFICIENT_LIQUIDITY", "SWAP_IMPACT_TOO_HIGH", "NO_QUOTES"]);
const ACROSS_NO_LIQUIDITY_CODES = new Set(["AMOUNT_TOO_HIGH"]);
const LIFI_UNSUPPORTED = /not supported|unsupported|invalid chain|unknown chain|invalid token|unknown token/i;
const LIFI_NO_QUOTES = /no available quotes|no quotes|no routes? (?:found|available)/i;
const ONECLICK_NO_LIQUIDITY = /no liquidity/i;

const USD_BASIS_ORACLE: UsdFrictionBasis = "oneclick_token_list_oracle";
/** transient: a quote's own legs before score_cell applies the cell's common price */
const USD_BASIS_VENUE: UsdFrictionBasis = "venue_oracle";
const USD_BASIS_MEDIAN_VENUE: UsdFrictionBasis = "median_venue_oracle";
const HEADROOM_BASIS_DEST_UNITS: HeadroomBasis = "dest_units";
const NO_PRICE_BASIS: PriceBasis = { source: null, dest_price_usd: null, origin_price_usd: null, n_venue_oracles: 0 };
const ACROSS_USD_NOTE =
  "Across returns no USD legs; amount_in_usd / amount_out_usd are valued at the 1Click token-list oracle (null if that list failed); raw USDC friction is exact";

interface Endpoints {
  oneclick: string;
  relay: string;
  lifi: string;
  across: string;
  oneclickJwt: string | undefined;
}

function endpoints(): Endpoints {
  return {
    oneclick: serverEnv("ONECLICK_API_BASE", "https://1click.chaindefuser.com").replace(/\/$/, ""),
    relay: serverEnv("RELAY_API_BASE", "https://api.relay.link").replace(/\/$/, ""),
    lifi: serverEnv("LIFI_API_BASE", "https://li.quest/v1").replace(/\/$/, ""),
    across: serverEnv("ACROSS_API_BASE", "https://app.across.to/api").replace(/\/$/, ""),
    oneclickJwt: serverEnv("ONECLICK_JWT"),
  };
}

export function benchmarkAddresses(): Addresses {
  return {
    evm: serverEnv("VALUO_EVM_ADDRESS", DEFAULT_ADDRESSES.evm),
    sol: serverEnv("VALUO_SOL_ADDRESS", DEFAULT_ADDRESSES.sol),
    btc: serverEnv("VALUO_BTC_ADDRESS", DEFAULT_ADDRESSES.btc),
  };
}

export function venueTimeoutMs(): number {
  return serverEnvNumber("VALUO_BENCH_TIMEOUT_MS", 12_000);
}

function oneclickHeaders(ep: Endpoints): Record<string, string> {
  return ep.oneclickJwt ? { Authorization: `Bearer ${ep.oneclickJwt}` } : {};
}

// --------------------------------------------------------------------------- raw fetch + record
interface RawExchange {
  status: number | null;
  json: unknown | null;
  latency_ms: number;
  fetched_at_utc: string;
  transport_error: string | null;
  record: RawRecord;
}

/** Ledger source names as the Python ProvenanceLedger records them (manifest.sources keys). */
type ExchangeSource = "oneclick" | "relay" | "lifi" | "across";

function utcNow(): string {
  return new Date().toISOString();
}

async function exchange(
  source: ExchangeSource,
  name: string,
  method: "GET" | "POST",
  url: string,
  init: { body?: unknown; headers?: Record<string, string>; timeoutMs: number },
): Promise<RawExchange> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), init.timeoutMs);
  const started = performance.now();
  const fetched_at_utc = utcNow();
  const bodyText = init.body === undefined ? undefined : JSON.stringify(init.body);
  const request_body_sha256 = init.body === undefined ? null : sha256Json(init.body);
  let status: number | null = null;
  let bytes = new Uint8Array();
  let transport_error: string | null = null;
  try {
    const res = await fetch(url, {
      method,
      headers: {
        Accept: "application/json",
        "User-Agent": USER_AGENT,
        ...(bodyText ? { "Content-Type": "application/json" } : {}),
        ...(init.headers ?? {}),
      },
      body: bodyText,
      signal: controller.signal,
      cache: "no-store",
    });
    status = res.status;
    bytes = new Uint8Array(await res.arrayBuffer());
  } catch (err) {
    transport_error =
      err instanceof Error ? (err.name === "AbortError" ? `timeout after ${init.timeoutMs} ms` : `${err.name}: ${err.message}`) : String(err);
  } finally {
    clearTimeout(timer);
  }
  const latency_ms = Math.round((performance.now() - started) * 10) / 10;
  const text = bytes.length ? new TextDecoder().decode(bytes) : "";
  let json: unknown | null = null;
  if (text) {
    try {
      json = JSON.parse(text);
    } catch {
      json = null;
    }
  }
  const ok = status !== null && status >= 200 && status < 300;
  const bodyMsg = bodyMessage(json);
  const error = transport_error ?? (ok ? null : `HTTP ${status}${bodyMsg ? `: ${bodyMsg}` : ""}`);
  const record: RawRecord = {
    source,
    name,
    url,
    method,
    request_body_sha256,
    http_status: status,
    ok,
    error,
    fetched_at_utc,
    latency_ms,
    bytes: bytes.length,
    sha256: bytes.length ? sha256Hex(bytes) : EMPTY_SHA256,
    raw_path: null,
    attempts: 1,
    note: "live browser race; raw bytes not persisted",
  };
  return { status, json, latency_ms, fetched_at_utc, transport_error, record };
}

function bodyMessage(json: unknown): string | null {
  const o = obj(json);
  if (!o) return null;
  const code = strish(o.errorCode) ?? strish(o.code);
  const message = strish(o.message);
  if (code && message) return `${code}: ${message}`;
  return message ?? code;
}

function obj(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}
function arr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
/** Finite number from a number or numeric string (API fields arrive as either). */
function numish(v: unknown): number | null {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}
function strish(v: unknown): string | null {
  return typeof v === "string" ? v : typeof v === "number" ? String(v) : null;
}
/** Integer from a raw-unit field (digits only), exact at any magnitude (execution_bench._int_str). */
function intStr(v: unknown): bigint | null {
  if (typeof v === "number" && Number.isInteger(v)) return BigInt(v);
  if (typeof v === "string" && /^-?\d+$/.test(v.trim())) return BigInt(v.trim());
  return null;
}
function frictionBps(amountIn: number | null, amountOut: number | null): number | null {
  if (amountIn === null || amountOut === null || amountIn <= 0) return null;
  return ((amountIn - amountOut) / amountIn) * 1e4;
}
/** First non-empty string among `keys` in the JSON body, else the record's error (execution_bench._message). */
function messageOf(x: RawExchange, ...keys: string[]): string | null {
  const o = obj(x.json);
  if (o) {
    for (const key of keys) {
      const v = o[key];
      if (typeof v === "string" && v.trim()) return v.trim();
    }
  }
  return x.record.error ?? null;
}
function codedText(code: string | null, message: string | null): string | null {
  return code && message && !message.includes(code) ? `${code}: ${message}` : message ?? code;
}

// --------------------------------------------------------------------------- 1Click token universe
interface TokenUniverse {
  ok: boolean;
  prices: Map<string, number>;
  count: number | null;
  blockchains: string[];
  record: RawRecord;
}

/** GET /v0/tokens once per race: USD prices for the common oracle (execution_bench.fetch_oneclick_tokens). */
async function fetchTokenUniverse(ep: Endpoints, timeoutMs: number): Promise<TokenUniverse> {
  const x = await exchange("oneclick", "tokens", "GET", `${ep.oneclick}/v0/tokens`, { headers: oneclickHeaders(ep), timeoutMs });
  if (x.transport_error || !x.record.ok || !Array.isArray(x.json)) {
    return { ok: false, prices: new Map(), count: null, blockchains: [], record: x.record };
  }
  const prices = new Map<string, number>();
  const chains = new Set<string>();
  let count = 0;
  for (const token of x.json) {
    const t = obj(token);
    const id = strish(t?.assetId);
    if (!t || !id) continue;
    count += 1;
    const price = numish(t.price);
    if (price !== null) prices.set(id, price);
    const chain = strish(t.blockchain);
    if (chain) chains.add(chain);
  }
  return { ok: true, prices, count, blockchains: [...chains].sort(), record: x.record };
}

// --------------------------------------------------------------------------- quote context + assembly
/** Everything a parser needs besides the response (execution_bench.QuoteContext). */
interface QuoteContext {
  corridor: CorridorDef;
  amountInRaw: string;
  /** live 1Click token-list USD price of the destination / origin asset (null when the list failed) */
  destPriceUsd: number | null;
  originPriceUsd: number | null;
}

function oracleOriginPrice(ctx: QuoteContext): number | null {
  if (ctx.originPriceUsd !== null) return ctx.originPriceUsd;
  return ctx.corridor.same_asset ? ctx.destPriceUsd : null;
}

function recordFields(x: RawExchange | null): Pick<VenueQuote, "latency_ms" | "fetched_at_utc" | "raw_record_sha256"> {
  return x
    ? { latency_ms: x.latency_ms, fetched_at_utc: x.fetched_at_utc, raw_record_sha256: x.record.sha256 }
    : { latency_ms: 0, fetched_at_utc: utcNow(), raw_record_sha256: EMPTY_SHA256 };
}

function failure(
  ctx: QuoteContext,
  venue: VenueName,
  x: RawExchange | null,
  status: QuoteStatus,
  supported: boolean,
  message: string | null,
  extras: Partial<VenueQuote> = {},
): VenueQuote {
  return {
    venue,
    supported,
    status,
    error_message: (message || "no response").slice(0, 300),
    amount_in_raw: ctx.amountInRaw,
    amount_in_usd: null,
    amount_out_raw: null,
    amount_out_formatted: null,
    amount_out_usd: null,
    friction_bps_usd: null,
    friction_bps_raw: null,
    time_estimate_s: null,
    route_tool: null,
    fee_breakdown_usd: {},
    ...recordFields(x),
    error_code: null,
    note: null,
    routes_via_near_intents: false,
    ...extras,
  };
}

interface SuccessFields {
  amount_in_usd: number | null;
  amount_out_raw: string | null;
  amount_out_formatted: number | null;
  amount_out_usd: number | null;
  time_estimate_s: number | null;
  route_tool: string | null;
  fee_breakdown_usd: Record<string, number>;
}

/**
 * Assemble an ok quote; friction is computed here so every venue shares one identity
 * (execution_bench._success). `amount_in_usd` / `amount_out_usd` passed in are the VENUE's own USD
 * legs (null for Across); the published legs are re-valued with the token-list oracle when both
 * prices are known, and the venue legs survive as `venue_*` fields.
 */
function success(ctx: QuoteContext, venue: VenueName, x: RawExchange, f: SuccessFields, extras: Partial<VenueQuote> = {}): VenueQuote {
  const destDecimals = ctx.corridor.destination.decimals;
  const inRaw = intStr(ctx.amountInRaw);
  const outRaw = intStr(f.amount_out_raw);
  const outUnits = outRaw !== null ? rawToFloat(outRaw.toString(), destDecimals) : f.amount_out_formatted;
  const venueInUsd = f.amount_in_usd;
  const venueOutUsd = f.amount_out_usd;
  const venueImpliedPrice = venueOutUsd !== null && outUnits ? venueOutUsd / outUnits : null;
  const originPrice = oracleOriginPrice(ctx);
  let inUsd: number | null;
  let outUsd: number | null;
  let usdBasis: UsdFrictionBasis;
  if (originPrice !== null && ctx.destPriceUsd !== null && inRaw !== null && outUnits !== null) {
    inUsd = (rawToFloat(inRaw.toString(), ctx.corridor.origin.decimals) ?? 0) * originPrice;
    outUsd = outUnits * ctx.destPriceUsd;
    usdBasis = USD_BASIS_ORACLE;
  } else {
    inUsd = venueInUsd;
    outUsd = venueOutUsd;
    usdBasis = USD_BASIS_VENUE;
  }
  const oracleGapBps =
    venueImpliedPrice !== null && ctx.destPriceUsd ? ((venueImpliedPrice - ctx.destPriceUsd) / ctx.destPriceUsd) * 1e4 : null;
  return {
    venue,
    supported: true,
    status: "ok",
    error_message: null,
    amount_in_raw: ctx.amountInRaw,
    amount_in_usd: inUsd,
    amount_out_raw: outRaw !== null ? outRaw.toString() : null,
    amount_out_formatted: f.amount_out_formatted,
    amount_out_usd: outUsd,
    friction_bps_usd: frictionBps(inUsd, outUsd),
    friction_bps_raw:
      ctx.corridor.same_asset && inRaw !== null && outRaw !== null ? frictionBps(Number(inRaw), Number(outRaw)) : null,
    time_estimate_s: f.time_estimate_s,
    route_tool: f.route_tool,
    fee_breakdown_usd: f.fee_breakdown_usd,
    ...recordFields(x),
    error_code: null,
    note: null,
    routes_via_near_intents: false,
    usd_basis: usdBasis,
    oracle_dest_price_usd: ctx.destPriceUsd,
    oracle_origin_price_usd: originPrice,
    venue_amount_in_usd: venueInUsd,
    venue_amount_out_usd: venueOutUsd,
    venue_friction_bps_usd: frictionBps(venueInUsd, venueOutUsd),
    venue_implied_dest_price_usd: venueImpliedPrice,
    venue_oracle_gap_bps: oracleGapBps,
    ...extras,
  };
}

/** Integrity guard: a quote priced for a different input than we sent must not be scored as ok. */
function echoMismatch(ctx: QuoteContext, venue: VenueName, x: RawExchange, echoedAmountIn: unknown): VenueQuote | null {
  const echoed = intStr(echoedAmountIn);
  const requested = intStr(ctx.amountInRaw);
  if (echoed === null || requested === null || echoed === requested) return null;
  return failure(ctx, venue, x, "error", true, `venue echoed amountIn ${echoed} != requested ${requested}`, { error_code: "AMOUNT_ECHO_MISMATCH" });
}

// --------------------------------------------------------------------------- payloads (FACTS 2-3)
function oneclickPayload(corridor: CorridorDef, amountRaw: string, addr: Addresses) {
  return {
    dry: true,
    swapType: "EXACT_INPUT",
    slippageTolerance: 100,
    originAsset: corridor.venues.oneclick.originAsset,
    depositType: "ORIGIN_CHAIN",
    destinationAsset: corridor.venues.oneclick.destinationAsset,
    amount: amountRaw,
    refundTo: addr[corridor.origin.address_kind],
    refundType: "ORIGIN_CHAIN",
    recipient: addr[corridor.destination.address_kind],
    recipientType: "DESTINATION_CHAIN",
    // 1Click deadline: now + 2 h, ISO-8601 UTC, millisecond precision (execution_bench.deadline_iso)
    deadline: new Date(Date.now() + 2 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, ".000Z"),
  };
}

function relayPayload(corridor: CorridorDef, amountRaw: string, addr: Addresses) {
  const p = corridor.venues.relay!;
  return {
    user: addr[corridor.origin.address_kind],
    originChainId: p.originChainId,
    destinationChainId: p.destinationChainId,
    originCurrency: p.originCurrency,
    destinationCurrency: p.destinationCurrency,
    recipient: addr[corridor.destination.address_kind],
    tradeType: "EXACT_INPUT",
    amount: amountRaw,
  };
}

function lifiParams(corridor: CorridorDef, amountRaw: string, addr: Addresses): URLSearchParams {
  const p = corridor.venues.lifi!;
  return new URLSearchParams({
    fromChain: p.fromChain,
    toChain: p.toChain,
    fromToken: p.fromToken,
    toToken: p.toToken,
    fromAmount: amountRaw,
    fromAddress: addr[corridor.origin.address_kind],
    toAddress: addr[corridor.destination.address_kind],
  });
}

function acrossParams(corridor: CorridorDef, amountRaw: string): URLSearchParams {
  const p = corridor.venues.across!;
  return new URLSearchParams({
    inputToken: p.inputToken,
    outputToken: p.outputToken,
    originChainId: String(p.originChainId),
    destinationChainId: String(p.destinationChainId),
    amount: amountRaw,
  });
}

/** Ledger record name, as the Python collector names its quote records. */
function recordName(corridor: CorridorDef, clipUsd: number): string {
  return `quote:${corridor.corridor_id}:${Number.isInteger(clipUsd) ? clipUsd : clipUsd}`;
}

// --------------------------------------------------------------------------- pure parsers
function parseOneClick(x: RawExchange, ctx: QuoteContext): VenueQuote {
  const root = obj(x.json);
  const quote = obj(root?.quote);
  if (!x.transport_error && x.record.ok && quote && quote.amountOut != null) {
    const mismatch = echoMismatch(ctx, "1click", x, quote.amountIn);
    if (mismatch) return mismatch;
    const inUsd = numish(quote.amountInUsd);
    const fees: Record<string, number> = {};
    const withdrawFee = numish(quote.withdrawFee); // raw destination units
    if (withdrawFee !== null && ctx.destPriceUsd !== null) {
      fees.withdrawFee = (withdrawFee / 10 ** ctx.corridor.destination.decimals) * ctx.destPriceUsd;
    }
    const request = obj(root?.quoteRequest);
    let appFeeBps = 0;
    for (const item of arr(request?.appFees)) appFeeBps += numish(obj(item)?.fee) ?? 0; // fee is in bps of the input
    if (inUsd !== null && appFeeBps) fees.appFee = (inUsd * appFeeBps) / 1e4;
    return success(
      ctx,
      "1click",
      x,
      {
        amount_in_usd: inUsd,
        amount_out_raw: strish(quote.amountOut),
        amount_out_formatted: numish(quote.amountOutFormatted),
        amount_out_usd: numish(quote.amountOutUsd),
        time_estimate_s: numish(quote.timeEstimate),
        route_tool: ROUTE_TOOL["1click"],
        fee_breakdown_usd: fees,
      },
      {
        app_fee_bps: appFeeBps,
        min_amount_out_raw: strish(quote.minAmountOut),
        refund_fee_raw: strish(quote.refundFee),
        confidentiality: strish(request?.confidentiality),
      },
    );
  }
  const message = messageOf(x, "message");
  if (message && ONECLICK_NO_LIQUIDITY.test(message)) return failure(ctx, "1click", x, "no_liquidity", true, message);
  return failure(ctx, "1click", x, "error", true, message);
}

function parseRelay(x: RawExchange, ctx: QuoteContext): VenueQuote {
  const root = obj(x.json);
  const details = obj(root?.details);
  const currencyOut = obj(details?.currencyOut);
  if (!x.transport_error && x.record.ok && currencyOut && currencyOut.amount != null) {
    const currencyIn = obj(details?.currencyIn);
    const mismatch = echoMismatch(ctx, "relay", x, currencyIn?.amount);
    if (mismatch) return mismatch;
    const fees: Record<string, number> = {};
    for (const [key, value] of Object.entries(obj(root?.fees) ?? {})) {
      const usd = numish(obj(value)?.amountUsd);
      if (usd !== null) fees[key] = usd;
    }
    const impact = obj(details?.totalImpact);
    return success(
      ctx,
      "relay",
      x,
      {
        amount_in_usd: numish(currencyIn?.amountUsd),
        amount_out_raw: strish(currencyOut.amount),
        amount_out_formatted: numish(currencyOut.amountFormatted),
        amount_out_usd: numish(currencyOut.amountUsd),
        time_estimate_s: numish(details?.timeEstimate),
        route_tool: ROUTE_TOOL.relay,
        fee_breakdown_usd: fees,
      },
      { price_impact_pct: numish(impact?.percent), min_amount_out_raw: strish(currencyOut.minimumAmount) },
    );
  }
  const code = strish(root?.errorCode);
  const text = codedText(code, messageOf(x, "message"));
  if (code && RELAY_ROUTE_ERROR_CODES.has(code)) return failure(ctx, "relay", x, "unsupported_route", false, text, { error_code: code });
  if (code && RELAY_NO_LIQUIDITY_CODES.has(code)) return failure(ctx, "relay", x, "no_liquidity", true, text, { error_code: code });
  return failure(ctx, "relay", x, "error", true, text, { error_code: code });
}

function parseLifi(x: RawExchange, ctx: QuoteContext): VenueQuote {
  const root = obj(x.json);
  const est = obj(root?.estimate);
  if (!x.transport_error && x.record.ok && est && est.toAmount != null) {
    const mismatch = echoMismatch(ctx, "lifi", x, est.fromAmount);
    if (mismatch) return mismatch;
    const toToken = obj(obj(root?.action)?.toToken);
    const decimals = typeof toToken?.decimals === "number" && Number.isInteger(toToken.decimals) ? toToken.decimals : ctx.corridor.destination.decimals;
    const outRaw = intStr(est.toAmount);
    const fees: Record<string, number> = {};
    for (const cost of arr(est.feeCosts)) {
      const c = obj(cost);
      const usd = numish(c?.amountUSD);
      if (c && usd !== null) {
        const name = strish(c.name) || "fee";
        fees[name] = (fees[name] ?? 0) + usd;
      }
    }
    const gasUsd = arr(est.gasCosts).map((g) => numish(obj(g)?.amountUSD)).filter((u): u is number => u !== null);
    if (gasUsd.length) fees.gas = gasUsd.reduce((s, u) => s + u, 0);
    const toolDetails = obj(root?.toolDetails);
    const tool = String(root?.tool || est.tool || "lifi");
    // LI.FI's bridge key "near" is NEAR Intents itself: 1Click execution resold with LI.FI's fee on top, not an
    // independent competitor price. It still counts for headroom (it is what a LI.FI user receives).
    return success(
      ctx,
      "lifi",
      x,
      {
        amount_in_usd: numish(est.fromAmountUSD),
        amount_out_raw: strish(est.toAmount),
        amount_out_formatted: outRaw !== null ? rawToFloat(outRaw.toString(), decimals) : null,
        amount_out_usd: numish(est.toAmountUSD),
        time_estimate_s: numish(est.executionDuration),
        route_tool: tool,
        fee_breakdown_usd: fees,
      },
      { tool_name: strish(toolDetails?.name), min_amount_out_raw: strish(est.toAmountMin), routes_via_near_intents: tool.toLowerCase() === "near" },
    );
  }
  const message = messageOf(x, "message");
  if (message && LIFI_UNSUPPORTED.test(message)) return failure(ctx, "lifi", x, "unsupported_route", false, message);
  if (message && LIFI_NO_QUOTES.test(message)) return failure(ctx, "lifi", x, "no_liquidity", true, message);
  return failure(ctx, "lifi", x, "error", true, message);
}

function parseAcross(x: RawExchange, ctx: QuoteContext): VenueQuote {
  const root = obj(x.json);
  if (!x.transport_error && x.record.ok && root && root.outputAmount != null) {
    if (root.isAmountTooLow === true) {
      return failure(ctx, "across", x, "error", true, "isAmountTooLow: amount below Across minimum deposit", { error_code: "AMOUNT_TOO_LOW" });
    }
    const scale = 10 ** ctx.corridor.destination.decimals;
    const outRaw = intStr(root.outputAmount);
    const fees: Record<string, number> = {};
    for (const key of ["totalRelayFee", "relayerCapitalFee", "relayerGasFee", "lpFee"]) {
      const total = numish(obj(root[key])?.total);
      if (total !== null) fees[key] = total / scale; // USDC origin units ~ USD
    }
    const totalPct = numish(obj(root.totalRelayFee)?.pct); // 1e18-scaled fraction (FACTS section 3)
    const limits = obj(root.limits);
    return success(
      ctx,
      "across",
      x,
      {
        amount_in_usd: null,
        amount_out_raw: strish(root.outputAmount),
        amount_out_formatted: outRaw !== null ? rawToFloat(outRaw.toString(), ctx.corridor.destination.decimals) : null,
        amount_out_usd: null,
        time_estimate_s: numish(root.estimatedFillTimeSec),
        route_tool: ROUTE_TOOL.across,
        fee_breakdown_usd: fees,
      },
      {
        relay_fee_bps: totalPct !== null ? (totalPct / 1e18) * 1e4 : null,
        usd_basis_note: ACROSS_USD_NOTE,
        note: ACROSS_USD_NOTE,
        max_deposit_raw: strish(limits?.maxDeposit),
        exclusive_relayer: strish(root.exclusiveRelayer),
      },
    );
  }
  const code = strish(root?.code);
  const text = codedText(code, messageOf(x, "message"));
  const is4xx = x.status !== null && x.status >= 400 && x.status < 500;
  if (code && ACROSS_NO_LIQUIDITY_CODES.has(code)) return failure(ctx, "across", x, "no_liquidity", true, text, { error_code: code });
  if (code && is4xx) return failure(ctx, "across", x, "unsupported_route", false, text, { error_code: code });
  return failure(ctx, "across", x, "error", true, text, { error_code: code });
}

/**
 * A venue the corridor declares structurally unsupported is not quoted (execution_bench
 * declared_unsupported_quote). Rather than assert that statically, the race reads Across's live
 * chain list and records whether the destination chain is absent; the record is the evidence.
 */
function parseAcrossChains(x: RawExchange, ctx: QuoteContext, reason: string): VenueQuote {
  const label = ctx.corridor.destination.chain_label;
  if (x.transport_error || !x.record.ok) {
    return failure(ctx, "across", x, "unsupported_route", false, reason, {
      declared: true,
      note: `declared unsupported; live GET /api/chains verification failed (${x.record.error ?? "no response"})`,
    });
  }
  const rows = Array.isArray(x.json) ? x.json : arr(obj(x.json)?.chains);
  const wanted = label.toLowerCase();
  const found = rows.some((c) => (strish(obj(c)?.name) ?? "").toLowerCase().includes(wanted));
  if (!found) {
    return failure(ctx, "across", x, "unsupported_route", false, reason, {
      declared: true,
      note: `verified live: GET /api/chains (${rows.length} chains) lists no ${label} chain; suggested-fees cannot be requested`,
    });
  }
  return failure(ctx, "across", x, "skipped", true, `Across now lists ${label}; corridors.ts needs Across parameters before it can be quoted`, {
    declared: true,
    note: `GET /api/chains (${rows.length} chains) lists ${label}; the static declaration in corridors.ts is stale`,
  });
}

// --------------------------------------------------------------------------- venue dispatch
interface Attempt {
  venue: VenueName;
  kind: "quote" | "chains" | "skipped";
  x: RawExchange | null;
  reason: string | null;
}

async function attempt(venue: VenueName, corridor: CorridorDef, clipUsd: number, amountRaw: string, addr: Addresses, ep: Endpoints, timeoutMs: number): Promise<Attempt> {
  const name = recordName(corridor, clipUsd);
  const declared = corridor.venues_declared_unsupported[venue];
  if (venue === "across" && (declared || !corridor.venues.across)) {
    const x = await exchange("across", `chains_check:${corridor.corridor_id}`, "GET", `${ep.across}/chains`, { timeoutMs });
    return { venue, kind: "chains", x, reason: declared ?? `Across is EVM-only; no ${corridor.destination.chain} route` };
  }
  if (declared) return { venue, kind: "skipped", x: null, reason: declared };
  if (venue === "1click") {
    const x = await exchange("oneclick", name, "POST", `${ep.oneclick}/v0/quote`, { body: oneclickPayload(corridor, amountRaw, addr), headers: oneclickHeaders(ep), timeoutMs });
    return { venue, kind: "quote", x, reason: null };
  }
  if (venue === "relay") {
    if (!corridor.venues.relay) return { venue, kind: "skipped", x: null, reason: "no Relay parameters for this corridor" };
    const x = await exchange("relay", name, "POST", `${ep.relay}/quote`, { body: relayPayload(corridor, amountRaw, addr), timeoutMs });
    return { venue, kind: "quote", x, reason: null };
  }
  if (venue === "lifi") {
    if (!corridor.venues.lifi) return { venue, kind: "skipped", x: null, reason: "no LI.FI parameters for this corridor" };
    const x = await exchange("lifi", name, "GET", `${ep.lifi}/quote?${lifiParams(corridor, amountRaw, addr)}`, { timeoutMs });
    return { venue, kind: "quote", x, reason: null };
  }
  const x = await exchange("across", name, "GET", `${ep.across}/suggested-fees?${acrossParams(corridor, amountRaw)}`, { timeoutMs });
  return { venue, kind: "quote", x, reason: null };
}

function parseAttempt(a: Attempt, ctx: QuoteContext): VenueQuote {
  if (a.kind === "chains" && a.x) return parseAcrossChains(a.x, ctx, a.reason ?? "declared unsupported");
  if (a.kind === "skipped" || !a.x) {
    const declared = ctx.corridor.venues_declared_unsupported[a.venue];
    if (declared) return failure(ctx, a.venue, null, "unsupported_route", false, declared, { declared: true });
    return failure(ctx, a.venue, null, "skipped", false, a.reason);
  }
  switch (a.venue) {
    case "1click":
      return parseOneClick(a.x, ctx);
    case "relay":
      return parseRelay(a.x, ctx);
    case "lifi":
      return parseLifi(a.x, ctx);
    case "across":
      return parseAcross(a.x, ctx);
  }
}

// --------------------------------------------------------------------------- common price (execution_bench.common_price_basis)
function median(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/**
 * Value every ok quote's USD legs in a cell at ONE price; returns the (possibly re-valued) quotes
 * and the `price_basis`. Preferred: the 1Click token-list oracle, already applied by `success()`.
 * When the token list failed every ok quote carries its own venue legs, which are not comparable
 * across venues; the fallback takes the MEDIAN of the venues' implied destination prices
 * (venue_amount_out_usd / destination units) and origin prices (venue_amount_in_usd / origin units)
 * and re-values all legs with it (`usd_basis = "median_venue_oracle"`). The venue legs survive in
 * the `venue_*` fields. `source` is null when no USD valuation is possible (frictions stay as returned).
 */
export function commonPriceBasis(corridor: CorridorDef, amountInRaw: string, quotes: VenueQuote[]): { quotes: VenueQuote[]; price_basis: PriceBasis } {
  const ok = quotes.filter((q) => q.status === "ok");
  const oracle = ok.filter((q) => q.usd_basis === USD_BASIS_ORACLE);
  if (oracle.length || !ok.length) {
    const q0 = oracle[0] ?? null;
    return {
      quotes,
      price_basis: {
        source: q0 ? USD_BASIS_ORACLE : null,
        dest_price_usd: q0?.oracle_dest_price_usd ?? null,
        origin_price_usd: q0?.oracle_origin_price_usd ?? null,
        n_venue_oracles: 0,
      },
    };
  }
  const inRaw = intStr(amountInRaw);
  const inUnits = inRaw !== null && inRaw !== 0n ? rawToFloat(inRaw.toString(), corridor.origin.decimals) : null;
  const destDecimals = corridor.destination.decimals;
  const destPrices = ok.map((q) => q.venue_implied_dest_price_usd).filter((p): p is number => typeof p === "number" && Number.isFinite(p) && p > 0);
  const originPrices = inUnits
    ? ok
        .map((q) => q.venue_amount_in_usd)
        .filter((v): v is number => typeof v === "number" && Number.isFinite(v))
        .map((v) => v / inUnits)
    : [];
  if (!destPrices.length || !originPrices.length) return { quotes, price_basis: NO_PRICE_BASIS };
  const destP = median(destPrices);
  const originP = median(originPrices);
  const out = quotes.map((q) => {
    if (q.status !== "ok") return q;
    const outRaw = intStr(q.amount_out_raw);
    const outUnits = outRaw !== null ? rawToFloat(outRaw.toString(), destDecimals) : (q.amount_out_formatted ?? null);
    const inUsd = inUnits ? inUnits * originP : null;
    const outUsd = outUnits !== null ? outUnits * destP : null;
    return {
      ...q,
      amount_in_usd: inUsd,
      amount_out_usd: outUsd,
      friction_bps_usd: frictionBps(inUsd, outUsd),
      usd_basis: USD_BASIS_MEDIAN_VENUE,
      oracle_dest_price_usd: destP,
      oracle_origin_price_usd: originP,
    };
  });
  return { quotes: out, price_basis: { source: USD_BASIS_MEDIAN_VENUE, dest_price_usd: destP, origin_price_usd: originP, n_venue_oracles: destPrices.length } };
}

// --------------------------------------------------------------------------- cell scoring (execution_bench.score_cell)
function preferredFriction(q: VenueQuote): number | null {
  return q.friction_bps_raw ?? q.friction_bps_usd ?? null;
}

/** A scored cell always carries its price basis (optional on stored snapshot cells written by older collectors). */
export type ScoredCell = CorridorClipResult & { price_basis: PriceBasis };

/**
 * Headroom, best competitor and 1Click rank for one (corridor, clip) cell, on physical destination
 * units. Cells without an ok 1Click quote carry null headroom. `venue_oracle_gap_bps` records how
 * far each venue's own USD mark of the destination asset sits from the cell's common price; when
 * that gap exceeds the headroom, a USD-leg comparison would have been decided by oracles.
 */
export function scoreCell(corridor: CorridorDef, clipUsd: number, quotes: VenueQuote[]): ScoredCell {
  const sorted = [...quotes].sort((a, b) => VENUE_ORDER.indexOf(a.venue) - VENUE_ORDER.indexOf(b.venue));
  const amountInRaw = sorted[0]?.amount_in_raw ?? clipToRawAmount(clipUsd, corridor.origin.decimals);
  const { quotes: ordered, price_basis } = commonPriceBasis(corridor, amountInRaw, sorted);
  const withUnits = ordered
    .filter((q) => q.status === "ok")
    .map((q) => ({ q, out: intStr(q.amount_out_raw) }))
    .filter((p): p is { q: VenueQuote; out: bigint } => p.out !== null);
  const oneclick = withUnits.find((p) => p.q.venue === "1click") ?? null;
  const competitors = withUnits.filter((p) => p.q.venue !== "1click");
  const best = competitors.length ? competitors.reduce((a, b) => (b.out > a.out ? b : a)) : null;
  const headroom = best && oneclick && best.out > 0n ? (Number(oneclick.out - best.out) / Number(best.out)) * 1e4 : null;
  const rank = oneclick ? 1 + competitors.filter((p) => p.out > oneclick.out).length : null;
  const commonDest = price_basis.dest_price_usd;
  const gaps: Partial<Record<VenueName, number>> = {};
  for (const { q } of withUnits) {
    const implied = q.venue_implied_dest_price_usd;
    if (typeof implied === "number" && Number.isFinite(implied) && commonDest) gaps[q.venue] = ((implied - commonDest) / commonDest) * 1e4;
  }
  const maxGap = Object.values(gaps).reduce<number | null>((m, g) => (g === undefined ? m : m === null ? Math.abs(g) : Math.max(m, Math.abs(g))), null);
  return {
    corridor_id: corridor.corridor_id,
    clip_usd: clipUsd,
    quotes: ordered,
    best_competitor: best ? best.q.venue : null,
    headroom_bps: headroom,
    oneclick_rank: rank,
    n_venues_ok: ordered.filter((q) => q.status === "ok").length,
    headroom_basis: headroom !== null ? HEADROOM_BASIS_DEST_UNITS : null,
    archetype: corridor.archetype,
    oneclick_friction_bps: oneclick ? preferredFriction(oneclick.q) : null,
    best_competitor_friction_bps: best ? preferredFriction(best.q) : null,
    n_competitors_ok: competitors.length,
    price_basis,
    oneclick_amount_out_raw: oneclick ? oneclick.out.toString() : null,
    best_competitor_amount_out_raw: best ? best.out.toString() : null,
    venue_oracle_gap_bps: gaps,
    oracle_gap_exceeds_headroom: maxGap !== null && headroom !== null && maxGap > Math.abs(headroom),
  };
}

// --------------------------------------------------------------------------- race
export async function runLiveBenchmark(corridorId: string, clipUsd: number): Promise<LiveBenchmarkResponse> {
  const corridor = getCorridor(corridorId);
  if (!corridor) throw new Error(`unknown corridor_id ${corridorId}`);
  const amountRaw = clipToRawAmount(clipUsd, corridor.origin.decimals);
  const addr = benchmarkAddresses();
  const ep = endpoints();
  const timeoutMs = venueTimeoutMs();
  const ran_at_utc = utcNow();
  const started = performance.now();

  // Every venue the Python collector attempts, plus declared-unsupported venues (verified live, not asserted).
  const venues = VENUE_ORDER.filter((v) => corridor.venues_attempted.includes(v) || v in corridor.venues_declared_unsupported);
  const [tokens, attempts] = await Promise.all([
    fetchTokenUniverse(ep, timeoutMs),
    Promise.all(venues.map((v) => attempt(v, corridor, clipUsd, amountRaw, addr, ep, timeoutMs))),
  ]);
  const ctx: QuoteContext = {
    corridor,
    amountInRaw: amountRaw,
    destPriceUsd: tokens.prices.get(corridor.venues.oneclick.destinationAsset) ?? null,
    originPriceUsd: tokens.prices.get(corridor.venues.oneclick.originAsset) ?? null,
  };
  const quotes = attempts.map((a) => parseAttempt(a, ctx));
  const records: RawRecord[] = [tokens.record, ...attempts.map((a) => a.x?.record).filter((r): r is RawRecord => r !== undefined)];

  return {
    ...scoreCell(corridor, clipUsd, quotes),
    corridor: toCorridor(corridor, addr),
    ranking_basis: corridor.same_asset ? "raw" : "usd",
    // execution_bench: the token-list oracle when it was fetched, else the median venue oracle applied per cell
    usd_friction_basis: tokens.ok ? USD_BASIS_ORACLE : USD_BASIS_MEDIAN_VENUE,
    token_list_ok: tokens.ok,
    ran_at_utc,
    total_latency_ms: Math.round(performance.now() - started),
    records,
  };
}
