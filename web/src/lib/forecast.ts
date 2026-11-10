/**
 * Visitor forecasts stored on NEAR SocialDB (`social.near`), mirroring the key layout of quant/valuo/anchor.py:
 *
 *     <account>/valuo/forecast/<YYYYMMDDTHHMMSSZ>  =  '{"schema":"valuo-forecast/1", ...}'
 *
 * The value is one compact JSON string written by the visitor's own wallet (SocialDB accepts writes only under
 * the signer's namespace). Pure functions, no React, no server-only imports: the browser uses the builders,
 * /api/forecasts uses the parser and the scorer. Every value read back is user-written, so `parseForecastTree`
 * validates and coerces each field and drops anything malformed; nothing from it is ever rendered as HTML.
 */
import type { RegimeKey } from "./types";

export const SOCIAL_CONTRACT = "social.near";
export const FORECAST_SCHEMA = "valuo-forecast/1";
export const FORECAST_PATH = ["valuo", "forecast"] as const;
/** 100 Tgas, as in anchor.py; a SocialDB set of ~700 bytes uses well under this. */
export const FORECAST_GAS = "100000000000000";
/** SocialDB charges storage_amount_per_byte = 1e19 yoctoNEAR per byte (10 KB per NEAR). */
export const YOCTO_PER_BYTE = 10n ** 19n;
/** 0.01 NEAR on top of the registration minimum, credited to the account's SocialDB storage balance. */
export const EXTRA_DEPOSIT_YOCTO = 10n ** 22n;
/** Fallback when storage_balance_bounds cannot be read: the live value on mainnet (Nov 2026) is 0.02 NEAR. */
export const DEFAULT_MIN_STORAGE_YOCTO = 2n * 10n ** 22n;
/** Hard cap on the stored string: anything longer is not a Valuo forecast. */
export const MAX_VALUE_CHARS = 2048;

const REGIMES: readonly RegimeKey[] = ["status_quo", "svrn_glidepath"];
const ACCOUNT_RE = /^(([a-z\d]+[-_])*[a-z\d]+\.)*([a-z\d]+[-_])*[a-z\d]+$/;
const KEY_RE = /^\d{8}T\d{6}Z$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const SHA_RE = /^[0-9a-f]{64}$/;
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;

export interface ForecastSettings {
  growth_yoy: number;
  tau_pub_bps: number;
  conf_share_target: number;
  tau_conf_bps: number;
  alpha_capture: number;
  regime: RegimeKey;
}

/** The JSON value written on-chain. */
export interface ForecastValue {
  schema: typeof FORECAST_SCHEMA;
  created_at: string;
  /** sha256 of the latest_snapshot.json the forecast was made against (manifest.snapshot_sha256) */
  snapshot_sha256: string;
  snapshot_generated_at: string | null;
  /** snapshot NEAR price at forecast time (intents_forensics.price.current_usd) */
  spot_usd: number | null;
  price_target_usd: number;
  /** resolution date, YYYY-MM-DD (UTC) */
  horizon: string;
  model: { implied_price_usd: number | null; horizon_months: number | null };
  settings: ForecastSettings;
}

/** One forecast as read back from SocialDB. */
export interface ForecastEntry {
  account: string;
  key: string;
  /** block at which SocialDB recorded the write (":block") */
  block_height: number | null;
  value: ForecastValue;
  /** true when the entry comes from a direct social.near RPC read (not only from the indexer) */
  verified_onchain: boolean;
}

export interface Realized {
  price_usd: number;
  as_of: string;
  source: string;
  snapshot_sha256: string | null;
}

export interface ForecastScore {
  status: "resolved" | "open";
  resolves_on: string;
  /** target / realized − 1, signed */
  error_pct: number | null;
  abs_error_pct: number | null;
  /** days from the realized price date to the horizon (positive = still open) */
  days_to_horizon: number;
  /** for resolved forecasts: days between the horizon and the price date used to score it */
  scored_days_after_horizon: number | null;
}

// ---------------------------------------------------------------------------------------------------------------
// Builders (browser)

/** '2026-11-10T12:34:56.789Z' -> '20261110T123456Z' (SocialDB keys avoid '.', ':' and '/'), same as anchor_key. */
export function forecastKey(d: Date): string {
  const iso = d.toISOString();
  return `${iso.slice(0, 4)}${iso.slice(5, 7)}${iso.slice(8, 10)}T${iso.slice(11, 13)}${iso.slice(14, 16)}${iso.slice(17, 19)}Z`;
}

/** Round to 6 significant digits so the stored string stays short; non-finite -> null. */
export function sig6(v: number | null | undefined): number | null {
  if (typeof v !== "number" || !Number.isFinite(v)) return null;
  return Number(v.toPrecision(6));
}

export interface BuildForecastInput {
  now: Date;
  snapshot_sha256: string;
  snapshot_generated_at: string | null;
  spot_usd: number | null;
  price_target_usd: number;
  horizon: string;
  implied_price_usd: number | null;
  horizon_months: number | null;
  settings: ForecastSettings;
}

export function buildForecastValue(i: BuildForecastInput): ForecastValue {
  if (!SHA_RE.test(i.snapshot_sha256)) throw new Error("snapshot_sha256 must be 64 lowercase hex characters");
  if (!(Number.isFinite(i.price_target_usd) && i.price_target_usd > 0 && i.price_target_usd < 1e6)) throw new Error("price target must be a positive number below $1,000,000");
  if (!validDate(i.horizon)) throw new Error("horizon must be a date YYYY-MM-DD");
  if (!REGIMES.includes(i.settings.regime)) throw new Error(`unknown issuance regime ${i.settings.regime}`);
  const s = i.settings;
  const settings: ForecastSettings = {
    growth_yoy: req(sig6(s.growth_yoy), "growth_yoy"),
    tau_pub_bps: req(sig6(s.tau_pub_bps), "tau_pub_bps"),
    conf_share_target: req(sig6(s.conf_share_target), "conf_share_target"),
    tau_conf_bps: req(sig6(s.tau_conf_bps), "tau_conf_bps"),
    alpha_capture: req(sig6(s.alpha_capture), "alpha_capture"),
    regime: s.regime,
  };
  return {
    schema: FORECAST_SCHEMA,
    created_at: i.now.toISOString().replace(/\.\d{3}Z$/, "Z"),
    snapshot_sha256: i.snapshot_sha256,
    snapshot_generated_at: i.snapshot_generated_at,
    spot_usd: sig6(i.spot_usd),
    price_target_usd: req(sig6(i.price_target_usd), "price_target_usd"),
    horizon: i.horizon,
    model: { implied_price_usd: sig6(i.implied_price_usd), horizon_months: i.horizon_months },
    settings,
  };
}

function req(v: number | null, name: string): number {
  if (v === null) throw new Error(`${name} is not a finite number`);
  return v;
}

/** JSON args for social.near `set`: one compact JSON string under <account>/valuo/forecast/<key> (anchor.py set_args). */
export function buildSetArgs(account: string, key: string, value: ForecastValue): { data: Record<string, { valuo: { forecast: Record<string, string> } }> } {
  if (!isAccountId(account)) throw new Error(`not a NEAR account id: ${account}`);
  if (!KEY_RE.test(key)) throw new Error(`bad forecast key ${key}`);
  const str = JSON.stringify(value);
  if (str.length > MAX_VALUE_CHARS) throw new Error(`forecast value is ${str.length} characters; the cap is ${MAX_VALUE_CHARS}`);
  return { data: { [account]: { valuo: { forecast: { [key]: str } } } } };
}

export interface StorageBalance {
  total: string;
  available: string;
}

/**
 * Deposit attached to `set`. SocialDB needs the account registered (storage balance >= bounds.min, 0.02 NEAR) and
 * enough available balance for the bytes written (1e19 yocto per byte). Unregistered: min + extra; registered:
 * extra. `extra` = max(0.01 NEAR, 1.5 x estimated bytes x 1e19) so a large value is still covered; any unused part
 * stays in the account's SocialDB storage balance (withdrawable with storage_withdraw).
 */
export function depositFor(balance: StorageBalance | null, minStorageYocto: bigint | null, args: object): { deposit: bigint; registered: boolean; extra: bigint; min: bigint } {
  const bytes = BigInt(new TextEncoder().encode(JSON.stringify(args)).length);
  const byBytes = (bytes * YOCTO_PER_BYTE * 3n) / 2n;
  const extra = byBytes > EXTRA_DEPOSIT_YOCTO ? byBytes : EXTRA_DEPOSIT_YOCTO;
  const min = minStorageYocto ?? DEFAULT_MIN_STORAGE_YOCTO;
  const registered = balance !== null && safeBig(balance.total) >= min;
  return { deposit: registered ? extra : min + extra, registered, extra, min };
}

/** The single FunctionCall the wallet signs (wallet-selector internal-action shape). */
export function buildSetAction(args: object, deposit: bigint): { type: "FunctionCall"; params: { methodName: "set"; args: object; gas: string; deposit: string } } {
  return { type: "FunctionCall", params: { methodName: "set", args, gas: FORECAST_GAS, deposit: deposit.toString() } };
}

export function yoctoToNear(y: bigint): string {
  const whole = y / 10n ** 24n;
  const frac = (y % 10n ** 24n).toString().padStart(24, "0").slice(0, 4).replace(/0+$/, "");
  return frac ? `${whole}.${frac}` : whole.toString();
}

function safeBig(s: unknown): bigint {
  try {
    return typeof s === "string" && /^\d+$/.test(s) ? BigInt(s) : 0n;
  } catch {
    return 0n;
  }
}

// ---------------------------------------------------------------------------------------------------------------
// Parsing (server): user-written values, validate everything

export function isAccountId(a: unknown): a is string {
  return typeof a === "string" && a.length >= 2 && a.length <= 64 && ACCOUNT_RE.test(a);
}

export function validDate(s: unknown): s is string {
  if (typeof s !== "string" || !DATE_RE.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

function num(v: unknown, lo: number, hi: number): number | null {
  const n = typeof v === "number" ? v : typeof v === "string" && v.length < 32 ? Number(v) : NaN;
  return Number.isFinite(n) && n >= lo && n <= hi ? n : null;
}

function isoOrNull(v: unknown): string | null {
  return typeof v === "string" && v.length <= 32 && ISO_RE.test(v) && !Number.isNaN(Date.parse(v)) ? v : null;
}

/** Coerce one stored string into a ForecastValue, or null when it is not a well-formed Valuo forecast. */
export function parseForecastValue(raw: unknown): ForecastValue | null {
  if (typeof raw !== "string" || raw.length === 0 || raw.length > MAX_VALUE_CHARS) return null;
  let o: unknown;
  try {
    o = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!o || typeof o !== "object" || Array.isArray(o)) return null;
  const r = o as Record<string, unknown>;
  if (r.schema !== FORECAST_SCHEMA) return null;
  const created_at = isoOrNull(r.created_at);
  const sha = typeof r.snapshot_sha256 === "string" && SHA_RE.test(r.snapshot_sha256) ? r.snapshot_sha256 : null;
  const target = num(r.price_target_usd, 1e-9, 1e6);
  const horizon = validDate(r.horizon) ? r.horizon : null;
  const s = r.settings && typeof r.settings === "object" && !Array.isArray(r.settings) ? (r.settings as Record<string, unknown>) : null;
  if (!created_at || !sha || target === null || !horizon || !s) return null;
  const regime = REGIMES.find((k) => k === s.regime);
  const settings = {
    growth_yoy: num(s.growth_yoy, -1, 100),
    tau_pub_bps: num(s.tau_pub_bps, 0, 10_000),
    conf_share_target: num(s.conf_share_target, 0, 1),
    tau_conf_bps: num(s.tau_conf_bps, 0, 10_000),
    alpha_capture: num(s.alpha_capture, 0, 1),
  };
  if (!regime || Object.values(settings).some((v) => v === null)) return null;
  const m = r.model && typeof r.model === "object" && !Array.isArray(r.model) ? (r.model as Record<string, unknown>) : {};
  const hm = num(m.horizon_months, 1, 600);
  return {
    schema: FORECAST_SCHEMA,
    created_at,
    snapshot_sha256: sha,
    snapshot_generated_at: isoOrNull(r.snapshot_generated_at),
    spot_usd: num(r.spot_usd, 1e-9, 1e6),
    price_target_usd: target,
    horizon,
    model: { implied_price_usd: num(m.implied_price_usd, 0, 1e9), horizon_months: hm === null ? null : Math.round(hm) },
    settings: { ...(settings as Omit<ForecastSettings, "regime">), regime },
  };
}

/**
 * Flatten a SocialDB `get` tree ({account: {valuo: {forecast: {key: {"": value, ":block": h}}}}}, as returned with
 * with_block_height) into entries. Invalid accounts, keys and values are skipped and counted.
 */
export function parseForecastTree(tree: unknown, maxEntries = 500): { entries: ForecastEntry[]; rejected: number } {
  const entries: ForecastEntry[] = [];
  let rejected = 0;
  if (!tree || typeof tree !== "object" || Array.isArray(tree)) return { entries, rejected };
  for (const [account, node] of Object.entries(tree as Record<string, unknown>)) {
    if (!isAccountId(account)) {
      rejected++;
      continue;
    }
    let cur: unknown = node;
    for (const part of FORECAST_PATH) cur = cur && typeof cur === "object" ? (cur as Record<string, unknown>)[part] : undefined;
    if (!cur || typeof cur !== "object") continue;
    for (const [key, leaf] of Object.entries(cur as Record<string, unknown>)) {
      if (key.startsWith(":")) continue;
      if (!KEY_RE.test(key) || !leaf || typeof leaf !== "object") {
        rejected++;
        continue;
      }
      const l = leaf as Record<string, unknown>;
      const value = parseForecastValue(l[""]);
      if (!value) {
        rejected++;
        continue;
      }
      const bh = l[":block"];
      entries.push({ account, key, block_height: typeof bh === "number" && Number.isSafeInteger(bh) && bh > 0 ? bh : null, value, verified_onchain: false });
      if (entries.length >= maxEntries) return { entries, rejected };
    }
  }
  return { entries, rejected };
}

// ---------------------------------------------------------------------------------------------------------------
// Scoring: only against a realized price taken from the snapshot

const DAY_MS = 86_400_000;

/**
 * A forecast resolves once the realized price date is on or after its horizon. Resolved: error = target / realized − 1,
 * where realized is the snapshot price (the snapshot carries no daily price series, so a forecast resolved before
 * the snapshot date is scored on the first snapshot price at or after its horizon that this server has: the latest;
 * `scored_days_after_horizon` reports that gap). Open: the same ratio against the latest price, reported as
 * distance to target, not as a score.
 */
export function scoreForecast(v: ForecastValue, realized: Realized | null): ForecastScore {
  const horizonMs = Date.parse(`${v.horizon}T00:00:00Z`);
  if (!realized) return { status: "open", resolves_on: v.horizon, error_pct: null, abs_error_pct: null, days_to_horizon: NaN, scored_days_after_horizon: null };
  const asOfMs = Date.parse(realized.as_of);
  const days = Math.ceil((horizonMs - asOfMs) / DAY_MS);
  const err = realized.price_usd > 0 ? v.price_target_usd / realized.price_usd - 1 : null;
  const resolved = asOfMs >= horizonMs;
  return {
    status: resolved ? "resolved" : "open",
    resolves_on: v.horizon,
    error_pct: err,
    abs_error_pct: err === null ? null : Math.abs(err),
    days_to_horizon: days,
    scored_days_after_horizon: resolved ? Math.floor((asOfMs - horizonMs) / DAY_MS) : null,
  };
}

/** GET /api/forecasts response. */
export interface ForecastBoardResponse {
  forecasts: (ForecastEntry & { score: ForecastScore })[];
  count: number;
  resolved_count: number;
  mean_abs_error_pct_resolved: number | null;
  rejected_entries: number;
  realized: Realized | null;
  sources: {
    indexer: { url: string; ok: boolean; error: string | null; accounts: number };
    rpc: { url: string; verified_accounts: number; not_on_chain: number; failed_accounts: number; unverified_reason: string | null };
    contract: string;
    pattern: string;
    extra_account: string | null;
    extra_account_error: string | null;
  };
  fetched_at: string;
  cache_s: number;
  error?: string;
}

/** UTC date `months` after `from`, as YYYY-MM-DD (day clamped to the month's end). */
export function addMonthsUtc(from: Date, months: number): string {
  const y = from.getUTCFullYear();
  const m = from.getUTCMonth() + months;
  const target = new Date(Date.UTC(y, m, 1));
  const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
  target.setUTCDate(Math.min(from.getUTCDate(), last));
  return target.toISOString().slice(0, 10);
}
