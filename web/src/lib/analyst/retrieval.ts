import type { Manifest, RawRecord } from "../types";
import type { AnalystContextItem, AnalystFigureCheck, AnalystRecordRef } from "./types";

/**
 * Retrieval layer for the IC analyst. Pure functions (no I/O, no "@/" imports) so the same code
 * runs in the route and in a plain `node` check script.
 *
 * 1. `buildCorpus` flattens latest_snapshot.json into addressable facts. A fact is one JSON
 *    object node and its scalar fields (`near_rpc.epoch_issuance` with minted_per_epoch_near,
 *    epochs_per_year, ...), so a value travels with its labels, notes and units. Each fact carries
 *    the manifest records it traces to (raw_record_sha256 fields, "source/name" strings, and a
 *    path -> record table); quant-engine outputs carry none and are marked basis "model".
 *    IC_MEMO.md is split at its ## / ### headings into memo facts.
 * 2. `retrieve` scores facts against the question with BM25 over path segments, field names,
 *    labels and string values (numbers are not indexed), with a small synonym table for IC
 *    vocabulary. No embedding service.
 * 3. `renderContext` numbers the selected facts [1..n] for the prompt; values are printed with
 *    JSON.stringify, i.e. exactly as stored in the snapshot.
 */

export interface Fact {
  kind: "snapshot" | "memo";
  /** JSON path (snapshot) or section heading (memo) */
  ref: string;
  label: string;
  /** prompt rendering of the fact body (fields or memo prose) */
  body: string;
  records: AnalystRecordRef[];
  basis: "raw" | "model" | "memo";
  /** BM25 term frequencies and document length */
  tf: Map<string, number>;
  len: number;
  /** top-level section, used to keep the selection diverse */
  group: string;
}

export interface Corpus {
  facts: Fact[];
  /** document frequency per term */
  df: Map<string, number>;
  avgLen: number;
  header: Fact;
}

// --------------------------------------------------------------------------- tokenizer

const STOP = new Set(
  "a an and are as at be been but by can could did do does for from had has have how i if in into is it its of on or so than that the their them then there these this those to too under up was were what when where which who why will with would you your near s t usd per vs not no yes value values".split(" "),
);

/** IC vocabulary -> field-name vocabulary used in the snapshot. */
const SYNONYMS: Record<string, string[]> = {
  concentrated: ["hhi", "concentration", "n_eff", "share"],
  concentration: ["hhi", "n_eff", "share"],
  solver: ["solver_concentration", "execute_intents", "signer"],
  agent: ["ai_agent_share", "escrow", "ai"],
  ai: ["ai_agent_share", "agent"],
  inflation: ["issuance", "max_inflation_rate", "svrn"],
  issuance: ["inflation", "minted", "epoch"],
  supply: ["total_supply_near", "issuance", "sink"],
  burn: ["burn", "sink", "buyback"],
  buyback: ["buyback", "holders_revenue", "sink"],
  sink: ["sinks", "state_locked", "storage", "buyback"],
  storage: ["storage_locked_near", "state_lock", "storage_bytes", "sink"],
  valuation: ["fdv", "sotp", "price", "market_implied"],
  worth: ["fdv", "sotp", "price"],
  fdv: ["fdv_usd", "market_implied", "gap_multiple", "fdv_percentiles"],
  true: ["market_implied", "solves", "required"],
  believe: ["market_implied", "solves", "sensitivity"],
  priced: ["market_implied", "fdv"],
  pricing: ["market_implied", "take", "bps", "headroom"],
  fee: ["fees", "take_bps", "revenue"],
  take: ["take_bps", "capture_ratio", "fees"],
  rate: ["bps", "take_bps"],
  revenue: ["net_revenue", "holders_revenue", "fees"],
  volume: ["volume", "allTimeUsd", "30d"],
  stake: ["staked", "staking", "apr", "validator"],
  staking: ["staked", "apr", "validator", "yield"],
  yield: ["apr", "staking_yield_table"],
  validator: ["active_validator_count", "staked"],
  bear: ["bear_case", "scenarios", "triggers", "drawdown"],
  risk: ["bear_case", "triggers", "drawdown", "warnings"],
  fail: ["falsification", "bear_case", "triggers"],
  falsify: ["falsification", "triggers"],
  trigger: ["triggers", "breached", "live_metrics"],
  competitor: ["relay", "lifi", "across", "best_competitor", "headroom"],
  bridge: ["relay", "lifi", "across", "bridge_share"],
  router: ["relay", "lifi", "across", "headroom"],
  quote: ["quotes", "headroom", "execution_bench", "friction"],
  spread: ["headroom", "friction", "bps"],
  execution: ["execution_bench", "headroom", "quotes"],
  "1click": ["oneclick", "headroom"],
  oneclick: ["1click", "headroom"],
  btc: ["native_btc", "eth_usdc_btc"],
  bitcoin: ["native_btc", "btc"],
  solana: ["sol", "cross_vm"],
  confidential: ["confidential_share", "confidential_tvl", "shard"],
  dark: ["confidential"],
  peer: ["comps", "peers", "relative_value"],
  comps: ["peers", "fdv_to_revenue", "fdv_to_fees"],
  multiple: ["fdv_to_revenue", "fdv_to_fees", "gap_multiple"],
  monte: ["sotp", "n_paths", "fdv_percentiles"],
  carlo: ["sotp", "paths"],
  probability: ["percentiles", "p10", "p90"],
  crossover: ["crossover_month_distribution", "breakeven"],
  breakeven: ["breakeven_daily_volume_usd", "crossover"],
  deflationary: ["net_float_change", "breakeven", "sink_coverage_ratio"],
  assumption: ["assumptions", "justification"],
  evidence: ["evidence_scorecard", "claim", "status"],
  verified: ["evidence_scorecard", "status"],
  price: ["current_usd", "price_percentiles", "price"],
  volatility: ["sigma", "annualized_sigma"],
  user: ["unique_users_7d"],
};

function stem(w: string): string {
  if (w.length > 4 && w.endsWith("ies")) return w.slice(0, -3) + "y";
  if (w.length > 4 && w.endsWith("es") && /(ch|sh|x|ss)es$/.test(w)) return w.slice(0, -2);
  if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) return w.slice(0, -1);
  return w;
}

/** Lowercase words; snake_case and camelCase are split, the joined form is kept too. */
export function tokenize(text: string): string[] {
  const out: string[] = [];
  const spaced = text.replace(/([a-z])([A-Z])/g, "$1 $2");
  for (const raw of spaced.toLowerCase().split(/[^a-z0-9_]+/)) {
    if (!raw) continue;
    const parts = raw.includes("_") ? [raw, ...raw.split("_")] : [raw];
    for (const p of parts) {
      if (!p || STOP.has(p) || /^\d+$/.test(p)) continue;
      out.push(stem(p));
    }
  }
  return out;
}

function expandQuery(tokens: string[]): Map<string, number> {
  const q = new Map<string, number>();
  const add = (t: string, w: number) => q.set(t, Math.max(q.get(t) ?? 0, w));
  for (const t of tokens) {
    add(t, 1);
    const syn = SYNONYMS[t] ?? SYNONYMS[t + "s"];
    if (syn) for (const s of syn) for (const st of tokenize(s)) add(st, 0.6);
  }
  return q;
}

// --------------------------------------------------------------------------- provenance

const SOURCES = "near_rpc_archival|near_rpc|nearstats|nearblocks|defillama|oneclick|coingecko|relay|lifi|across";
const SRC_RE = new RegExp(`\\b(${SOURCES})\\/([A-Za-z0-9_:.@\\-]+[A-Za-z0-9])`, "g");
const MAX_RECORDS = 4;
const EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

type Scalars = Record<string, unknown>;

class RecordResolver {
  private latest = new Map<string, RawRecord>();
  private bySha = new Map<string, RawRecord[]>();
  private records: RawRecord[];
  constructor(records: RawRecord[]) {
    this.records = records;
    for (const r of records) {
      this.latest.set(`${r.source}\u0000${r.name}`, r);
      const l = this.bySha.get(r.sha256);
      if (l) l.push(r);
      else this.bySha.set(r.sha256, [r]);
    }
  }
  get(source: string, name: string): RawRecord | null {
    return this.latest.get(`${source}\u0000${name}`) ?? null;
  }
  prefix(source: string | null, prefix: string, limit = MAX_RECORDS): RawRecord[] {
    const out: RawRecord[] = [];
    const seen = new Set<string>();
    for (const r of this.records) {
      if ((source === null || r.source === source) && r.name.startsWith(prefix) && !seen.has(r.source + r.name)) {
        seen.add(r.source + r.name);
        out.push(r);
        if (out.length >= limit) break;
      }
    }
    return out;
  }
  sha(sha: string, venue?: unknown): RawRecord[] {
    const hits = this.bySha.get(sha) ?? [];
    if (typeof venue === "string") {
      const src = venue === "1click" ? "oneclick" : venue;
      const narrowed = hits.filter((r) => r.source === src);
      if (narrowed.length) return narrowed;
    }
    return sha === EMPTY_SHA ? [] : hits;
  }
  /** "near_rpc/view_account:intents.near" -> record (exact name, else name prefix). */
  fromText(text: string, corridorHint: string | null = null): RawRecord[] {
    const out: RawRecord[] = [];
    // "oneclick/relay/lifi/across quote records ..." (evidence scorecard): one quote record per venue,
    // on the corridor the claim names when it names one.
    const venues = /\b((?:oneclick|relay|lifi|across)(?:\/(?:oneclick|relay|lifi|across))+) quote records/.exec(text);
    if (venues) for (const v of venues[1].split("/")) out.push(...this.prefix(v, corridorHint ? `quote:${corridorHint}:` : "quote:", 1));
    for (const m of text.matchAll(SRC_RE)) {
      const exact = this.get(m[1], m[2]);
      if (exact) out.push(exact);
      else out.push(...this.prefix(m[1], m[2], 2));
    }
    return out;
  }
}

function clipName(v: unknown): string | null {
  return typeof v === "number" && Number.isFinite(v) ? String(Math.round(v)) : null;
}

/** Path rules: the first matching rule names the records behind a snapshot node. */
const PATH_RULES: { re: RegExp; records: (r: RecordResolver, s: Scalars) => RawRecord[] }[] = [
  { re: /^near_rpc\.tracked_sinks\[\d+\]/, records: (r, s) => [r.get("near_rpc", `view_account:${String(s.account_id ?? "")}`)].filter(Boolean) as RawRecord[] },
  { re: /^near_rpc\.measured_state_lock_growth_sinks/, records: (r, s) => r.prefix("near_rpc_archival", `view_account:${String(s.account_id ?? "")}@`, 2) },
  {
    re: /^near_rpc\.epoch_issuance/,
    records: (r, s) => [r.get("near_rpc", `block:${String(s.epoch_start_height ?? "")}`), r.get("near_rpc", `block:${String(s.prev_epoch_start_height ?? "")}`)].filter(Boolean) as RawRecord[],
  },
  { re: /^near_rpc/, records: (r) => [r.get("near_rpc", "block_final"), r.get("near_rpc", "protocol_config"), r.get("near_rpc", "validators")].filter(Boolean) as RawRecord[] },
  { re: /^execution_bench\.results\[\d+\]\.quotes\[\d+\]/, records: () => [] /* raw_record_sha256 field resolves these */ },
  {
    re: /^execution_bench\.results\[\d+\]/,
    records: (r, s) => {
      const clip = clipName(s.clip_usd);
      return typeof s.corridor_id === "string" && clip ? ["oneclick", "relay", "lifi", "across"].map((src) => r.get(src, `quote:${s.corridor_id}:${clip}`)).filter(Boolean) as RawRecord[] : [];
    },
  },
  { re: /^execution_bench/, records: (r) => [r.get("oneclick", "tokens")].filter(Boolean) as RawRecord[] },
  { re: /^intents_forensics\.volume/, records: (r) => [r.get("nearstats", "summary"), r.get("defillama", "dexs:near-intents")].filter(Boolean) as RawRecord[] },
  { re: /^intents_forensics\.fees/, records: (r) => [r.get("defillama", "fees:near-intents"), r.get("defillama", "fees:near-intents:dailyRevenue"), r.get("defillama", "fees:near-intents:dailyHoldersRevenue"), r.get("defillama", "dexs:near-intents")].filter(Boolean) as RawRecord[] },
  { re: /^intents_forensics\.price/, records: (r) => [r.get("coingecko", "coins_markets"), r.get("nearblocks", "stats")].filter(Boolean) as RawRecord[] },
  { re: /^intents_forensics\.volatility/, records: (r) => [r.get("nearstats", "price_history:1y"), r.get("defillama", "dexs:near-intents")].filter(Boolean) as RawRecord[] },
  { re: /^intents_forensics\.solver_concentration/, records: (r) => r.prefix("nearblocks", "txns:intents.near:execute_intents:", 3) },
  { re: /^intents_forensics\.confidential/, records: (r) => [...r.prefix("near_rpc", "confidential:", 3), r.get("nearstats", "summary")].filter(Boolean) as RawRecord[] },
  { re: /^intents_forensics\.top_swaps/, records: (r) => [r.get("nearstats", "summary")].filter(Boolean) as RawRecord[] },
  { re: /^intents_forensics/, records: (r) => [...r.prefix("nearblocks", "txns:intents.near:p", 2), r.get("nearblocks", "txns_count:intents.near"), r.get("nearstats", "summary")].filter(Boolean) as RawRecord[] },
  {
    re: /^comps\.(peers|near_components)\[\d+\]/,
    records: (r, s) => [...(typeof s.slug === "string" ? r.prefix("defillama", `fees:${s.slug}:`, 2) : []), r.get("coingecko", "coins_markets"), r.get("defillama", "prices:current")].filter(Boolean) as RawRecord[],
  },
  { re: /^comps/, records: (r) => [r.get("defillama", "fees:near:dailyFees"), r.get("defillama", "fees:near-intents"), r.get("coingecko", "coins_markets")].filter(Boolean) as RawRecord[] },
];

/** Corridor id named by a claim's wording (the scorecard does not store the id itself). */
function corridorHint(text: string): string | null {
  if (/native BTC|USDC -> (native )?BTC|BTC per USDC/i.test(text)) return "eth_usdc_btc";
  if (/SOL USDC|cross-VM/i.test(text)) return "eth_usdc_sol_usdc";
  if (/EVM L2|Base USDC|Arbitrum/i.test(text)) return "base_usdc_arb_usdc";
  return null;
}

function resolveRecords(res: RecordResolver, path: string, scalars: Scalars): AnalystRecordRef[] {
  const found: RawRecord[] = [];
  const venue = scalars.venue;
  const hint = corridorHint(Object.values(scalars).filter((v): v is string => typeof v === "string").join(" "));
  for (const [k, v] of Object.entries(scalars)) {
    if (typeof v !== "string") continue;
    if (/sha256$/.test(k) && /^[0-9a-f]{64}$/.test(v)) found.push(...res.sha(v, venue));
    else if (/source|provenance|basis|note|value/.test(k)) found.push(...res.fromText(v, hint));
  }
  const rule = PATH_RULES.find((p) => p.re.test(path));
  if (rule) found.push(...rule.records(res, scalars));
  const seen = new Set<string>();
  const out: AnalystRecordRef[] = [];
  for (const r of found) {
    const key = `${r.source}/${r.name}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ source: r.source, name: r.name, sha256: r.sha256, ok: r.ok });
    if (out.length >= MAX_RECORDS) break;
  }
  return out;
}

// --------------------------------------------------------------------------- flattening

const MAX_STR = 480;
const FIELDS_PER_FACT = 24;
const INLINE_ARRAY = 12;
const OBJECT_ROWS_PER_FACT = 8;
const ID_KEYS = ["claim", "key", "name", "label", "account_id", "slug", "venue", "corridor_id", "engine", "scenario", "id", "metric", "regime", "title"];

/** Section headers that are not quant evidence; excluded from the corpus. */
const SKIP_TOP = new Set(["timings_s"]);

function isScalar(v: unknown): v is string | number | boolean | null {
  return v === null || typeof v === "string" || typeof v === "number" || typeof v === "boolean";
}

function fmtScalar(v: unknown): string {
  if (typeof v === "string") return JSON.stringify(v.length > MAX_STR ? v.slice(0, MAX_STR) + "..." : v);
  return JSON.stringify(v);
}

function fmtPrimitiveArray(a: unknown[]): string {
  if (a.length <= INLINE_ARRAY) return JSON.stringify(a.map((v) => (typeof v === "string" && v.length > MAX_STR ? v.slice(0, MAX_STR) + "..." : v)));
  return `[${a.length} values; first ${fmtScalar(a[0])}; last ${fmtScalar(a[a.length - 1])}]`;
}

function labelFor(path: string, scalars: Scalars): string {
  for (const k of ID_KEYS) {
    const v = scalars[k];
    if (typeof v === "string" && v) return v.length > 120 ? v.slice(0, 117) + "..." : v;
  }
  const tail = path.split(".").pop() ?? path;
  return tail || "snapshot";
}

function topGroup(path: string): string {
  const m = /^([^.[]+)(?:\.([^.[]+))?/.exec(path);
  return m ? `${m[1]}.${m[2] ?? ""}` : path;
}

function makeFact(kind: Fact["kind"], ref: string, label: string, body: string, indexText: string, records: AnalystRecordRef[], basis: Fact["basis"], group: string): Fact {
  const tf = new Map<string, number>();
  const toks = tokenize(indexText);
  for (const t of toks) tf.set(t, (tf.get(t) ?? 0) + 1);
  return { kind, ref, label, body, records, basis, tf, len: toks.length, group };
}

function walk(node: unknown, path: string, res: RecordResolver, out: Fact[], inherited: AnalystRecordRef[] = []): void {
  if (Array.isArray(node)) {
    if (node.every(isScalar)) return; // handled by the parent as a field
    if (node.every((v) => Array.isArray(v))) return; // matrix; handled by the parent as a field
    const objectRows = node.length > 40 && node.every((v) => v && typeof v === "object" && !Array.isArray(v) && Object.values(v).every(isScalar));
    if (objectRows) {
      // Long tables of flat rows (daily series): group rows so each fact stays small.
      for (let i = 0; i < node.length; i += OBJECT_ROWS_PER_FACT) {
        const rows = node.slice(i, i + OBJECT_ROWS_PER_FACT) as Scalars[];
        const ref = `${path}[${i}..${i + rows.length - 1}]`;
        const body = rows.map((r, j) => `[${i + j}] ` + Object.entries(r).map(([k, v]) => `${k}=${fmtScalar(v)}`).join(", ")).join("\n");
        const own = resolveRecords(res, path, {});
        const records = own.length ? own : inherited;
        out.push(makeFact("snapshot", ref, `${path.split(".").pop()} rows ${i}-${i + rows.length - 1}`, body, `${path} ${Object.keys(rows[0] ?? {}).join(" ")} ${rows.map((r) => Object.values(r).filter((v) => typeof v === "string").join(" ")).join(" ")}`, records, records.length ? "raw" : "model", topGroup(path)));
      }
      return;
    }
    node.forEach((v, i) => walk(v, `${path}[${i}]`, res, out, inherited));
    return;
  }
  if (!node || typeof node !== "object") return;
  const scalars: Scalars = {};
  const lines: string[] = [];
  const children: [string, unknown][] = [];
  for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
    if (path === "" && SKIP_TOP.has(k)) continue;
    const childPath = path ? `${path}.${k}` : k;
    if (isScalar(v)) {
      scalars[k] = v;
      lines.push(`${k} = ${fmtScalar(v)}`);
    } else if (Array.isArray(v) && (v.every(isScalar) || v.every((x) => Array.isArray(x)))) {
      lines.push(`${k} = ${v.every(isScalar) ? fmtPrimitiveArray(v) : `[${v.length} rows; first ${JSON.stringify(v[0])}; last ${JSON.stringify(v[v.length - 1])}]`}`);
    } else {
      children.push([childPath, v]);
    }
  }
  // A node without its own trace inherits its parent's records (fee_breakdown_usd under a quote).
  const own = resolveRecords(res, path, scalars);
  const records = own.length ? own : inherited;
  for (const [childPath, v] of children) walk(v, childPath, res, out, records);
  if (!lines.length) return;
  const label = labelFor(path, scalars);
  const parts = Math.ceil(lines.length / FIELDS_PER_FACT);
  for (let i = 0; i < lines.length; i += FIELDS_PER_FACT) {
    const chunk = lines.slice(i, i + FIELDS_PER_FACT);
    const ref = path || "(root)";
    const partLabel = parts > 1 ? `${label} (fields ${i + 1}-${i + chunk.length} of ${lines.length})` : label;
    const stringVals = chunk.filter((l) => / = "/.test(l)).join(" ");
    const keys = chunk.map((l) => l.split(" = ")[0]).join(" ");
    // Path and keys are indexed twice: they are the most reliable description of a number.
    const indexText = `${ref} ${ref} ${label} ${keys} ${keys} ${stringVals}`;
    out.push(makeFact("snapshot", ref, partLabel, chunk.join("\n"), indexText, records, records.length ? "raw" : "model", topGroup(path)));
  }
}

/** Split IC_MEMO.md at ## and ### headings. */
function memoFacts(memo: string): Fact[] {
  const out: Fact[] = [];
  let heading: string | null = null;
  let buf: string[] = [];
  const flush = () => {
    if (!heading) return;
    const text = buf.join("\n").trim();
    if (text) {
      const body = text.length > 1800 ? text.slice(0, 1800) + "\n..." : text;
      out.push(makeFact("memo", heading, `IC memo: ${heading}`, body, `${heading} ${heading} ${heading} ${body}`, [], "memo", `memo:${heading}`));
    }
  };
  let inCode = false;
  for (const line of memo.split(/\r?\n/)) {
    if (line.startsWith("```")) inCode = !inCode;
    const m = inCode ? null : /^(#{2,3})\s+(.*)$/.exec(line);
    if (m) {
      flush();
      heading = m[2].trim();
      buf = [];
    } else buf.push(line);
  }
  flush();
  return out;
}

export function buildCorpus(snapshot: unknown, manifest: Manifest | null, memo: string | null): Corpus {
  const res = new RecordResolver(manifest?.records ?? []);
  const facts: Fact[] = [];
  walk(snapshot, "", res, facts);
  if (memo) facts.push(...memoFacts(memo));
  const df = new Map<string, number>();
  let total = 0;
  for (const f of facts) {
    total += f.len;
    for (const t of f.tf.keys()) df.set(t, (df.get(t) ?? 0) + 1);
  }
  const s = (snapshot ?? {}) as Record<string, unknown>;
  const near = (s.near_rpc ?? {}) as Record<string, unknown>;
  const headerBody = [
    `snapshot_file = "artifacts/latest_snapshot.json"`,
    `snapshot_sha256 = ${JSON.stringify(manifest?.snapshot_sha256 ?? null)}`,
    `generated_at_utc = ${JSON.stringify(s.generated_at_utc ?? null)}`,
    `block_height = ${JSON.stringify(near.block_height ?? manifest?.block_height ?? null)}`,
    `block_hash = ${JSON.stringify(near.block_hash ?? manifest?.block_hash ?? null)}`,
    `seed = ${JSON.stringify(s.seed ?? null)}`,
    `manifest_records = ${JSON.stringify(manifest?.records.length ?? null)}`,
  ].join("\n");
  const blockRec = res.get("near_rpc", "block_final");
  const header = makeFact("snapshot", "(snapshot header)", "Snapshot identity", headerBody, "snapshot header block height generated", blockRec ? [{ source: blockRec.source, name: blockRec.name, sha256: blockRec.sha256, ok: blockRec.ok }] : [], blockRec ? "raw" : "model", "(header)");
  return { facts, df, avgLen: facts.length ? total / facts.length : 1, header };
}

// --------------------------------------------------------------------------- retrieval

export interface RetrieveOptions {
  maxSnapshotFacts?: number;
  maxMemoFacts?: number;
  maxChars?: number;
  /** facts per top-level group (keeps 9 quote cells from crowding out everything else) */
  maxPerGroup?: number;
}

export interface Scored {
  fact: Fact;
  score: number;
}

export function score(corpus: Corpus, question: string): Scored[] {
  const q = expandQuery(tokenize(question));
  const N = corpus.facts.length;
  const k1 = 1.2;
  const b = 0.75;
  const out: Scored[] = [];
  for (const f of corpus.facts) {
    let s = 0;
    for (const [t, w] of q) {
      const tf = f.tf.get(t);
      if (!tf) continue;
      const df = corpus.df.get(t) ?? 0;
      const idf = Math.log(1 + (N - df + 0.5) / (df + 0.5));
      s += w * idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + (b * f.len) / corpus.avgLen)));
    }
    if (s > 0) out.push({ fact: f, score: s });
  }
  return out.sort((a, b2) => b2.score - a.score);
}

/** Header first, then the best-scoring facts within the item, group and character budgets. */
export function retrieve(corpus: Corpus, question: string, opts: RetrieveOptions = {}): Scored[] {
  const maxSnap = opts.maxSnapshotFacts ?? 16;
  const maxMemo = opts.maxMemoFacts ?? 4;
  const maxChars = opts.maxChars ?? 26_000;
  const maxPerGroup = opts.maxPerGroup ?? 5;
  const ranked = score(corpus, question);
  const picked: Scored[] = [{ fact: corpus.header, score: 0 }];
  let chars = corpus.header.body.length;
  let nSnap = 0;
  let nMemo = 0;
  const perGroup = new Map<string, number>();
  const top = ranked[0]?.score ?? 0;
  for (const s of ranked) {
    if (s.score < top * 0.12) break;
    const f = s.fact;
    if (f.kind === "memo" ? nMemo >= maxMemo : nSnap >= maxSnap) continue;
    const g = perGroup.get(f.group) ?? 0;
    if (g >= maxPerGroup) continue;
    if (chars + f.body.length > maxChars) continue;
    picked.push(s);
    chars += f.body.length;
    perGroup.set(f.group, g + 1);
    if (f.kind === "memo") nMemo++;
    else nSnap++;
    if (nSnap >= maxSnap && nMemo >= maxMemo) break;
  }
  return picked;
}

export function toContextItems(picked: Scored[]): AnalystContextItem[] {
  return picked.map((s, i) => ({ n: i + 1, kind: s.fact.kind, ref: s.fact.ref, label: s.fact.label, records: s.fact.records, basis: s.fact.basis }));
}

/** Numbered context block for the prompt. */
export function renderContext(picked: Scored[]): string {
  return picked
    .map((s, i) => {
      const f = s.fact;
      const where = f.kind === "memo" ? `IC_MEMO.md section "${f.ref}"` : `latest_snapshot.json path ${f.ref}`;
      const prov =
        f.basis === "raw"
          ? `raw records: ${f.records.map((r) => `${r.source}/${r.name} sha256 ${r.sha256.slice(0, 12)}${r.ok ? "" : " (fetch failed)"}`).join("; ")}`
          : f.basis === "memo"
            ? "basis: IC memo prose generated from this snapshot"
            : "basis: quant-engine output or labeled assumption computed from snapshot inputs (no direct raw payload)";
      return `[${i + 1}] ${where}${f.label && f.label !== f.ref ? ` (${f.label})` : ""}\n${prov}\n${f.body}`;
    })
    .join("\n\n");
}

// --------------------------------------------------------------------------- answer checks

/** Citation numbers in the answer: [3], [3, 5], [3][5], [2-4]. */
export function parseCitations(answer: string): number[] {
  const out = new Set<number>();
  for (const m of answer.matchAll(/\[(\d{1,3}(?:\s*[,;–-]\s*\d{1,3})*)\]/g)) {
    for (const part of m[1].split(/\s*[,;]\s*/)) {
      const range = /^(\d+)\s*[–-]\s*(\d+)$/.exec(part);
      if (range) {
        const a = Number(range[1]);
        const b = Number(range[2]);
        if (b >= a && b - a <= 20) for (let n = a; n <= b; n++) out.add(n);
      } else if (/^\d+$/.test(part)) out.add(Number(part));
    }
  }
  return Array.from(out).sort((a, b) => a - b);
}

const NUM_RE = /-?\d[\d,]*(?:\.\d+)?/g;

function contextNumbers(context: string): { raw: Set<string>; values: number[] } {
  const raw = new Set<string>();
  const values: number[] = [];
  for (const m of context.matchAll(NUM_RE)) {
    const s = m[0].replace(/,/g, "");
    raw.add(s.replace(/^-/, ""));
    const v = Number(s);
    if (Number.isFinite(v)) values.push(Math.abs(v));
  }
  return { raw, values };
}

/**
 * Figure check: every number in the answer (citation markers and bare years excluded) must appear
 * in the context verbatim or as a rounding of a context number, read directly or scaled by
 * 100 (ratio -> %), 1e3, 1e6 or 1e9 (K / M / B). Reported to the reader; never used to rewrite.
 */
export function checkFigures(answer: string, context: string): AnalystFigureCheck {
  const stripped = answer.replace(/\[(\d{1,3}(?:\s*[,;–-]\s*\d{1,3})*)\]/g, " ");
  const ctx = contextNumbers(context);
  const ungrounded: string[] = [];
  let total = 0;
  let grounded = 0;
  for (const m of stripped.matchAll(NUM_RE)) {
    const text = m[0];
    const s = text.replace(/,/g, "").replace(/^-/, "");
    if (/^(19|20)\d\d$/.test(s)) continue;
    // Ordinals, section numbers and list markers: single digits are too ambiguous to check.
    if (/^\d$/.test(s)) continue;
    total++;
    if (ctx.raw.has(s)) {
      grounded++;
      continue;
    }
    const x = Number(s);
    const decimals = s.includes(".") ? s.split(".")[1].length : 0;
    const tol = 0.5 * 10 ** -decimals + 1e-9;
    const ok = ctx.values.some((c) => [c, c * 100, c / 1e3, c / 1e6, c / 1e9].some((v) => Math.abs(v - x) <= tol));
    if (ok) grounded++;
    else ungrounded.push(text);
  }
  return { total, grounded, ungrounded: ungrounded.slice(0, 12) };
}

// --------------------------------------------------------------------------- suggestions

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** Up to four questions the loaded snapshot can answer, built from the sections it carries. */
export function suggestQuestions(snapshot: unknown): string[] {
  const s = (snapshot ?? {}) as Record<string, Record<string, unknown> | undefined>;
  const out: string[] = [];
  const fdv = num(s.market_implied?.current_fdv_usd) ?? num((s.intents_forensics?.price as Record<string, unknown> | undefined)?.fdv_usd);
  if (s.market_implied) out.push(fdv ? `What has to be true for NEAR's market FDV of $${(fdv / 1e9).toFixed(2)}B?` : "What has to be true for NEAR's market FDV?");
  if (s.intents_forensics?.solver_concentration) out.push("How concentrated are solvers on intents.near, and what share is AI agents?");
  if (s.supply_physics) out.push("Do measured supply sinks offset epoch issuance today, and at what daily volume would they?");
  if (s.execution_bench) out.push("Where does 1Click out-deliver Relay and LI.FI, and where does it lose?");
  if (out.length < 4 && s.bear_case) out.push("Which bear-case triggers are breached in this snapshot?");
  return out.slice(0, 4);
}
