import type { ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import type { ManifestIndex } from "@/lib/manifestIndex";
import type { Tone } from "@/lib/theme";
import { isPercentileMap, type CorridorArchetype, type ExecutionBenchmark, type PercentileMap, type RawRecord, type Snapshot } from "@/lib/types";

/**
 * Pure helpers for Tab 1. Nothing here invents a value: every function either classifies a
 * number the snapshot already holds (tone by sign / ratio / probability) or builds the manifest
 * record name a figure traces to.
 */

export function isNum(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/** Signed quantity -> emerald when the sign is favourable, crimson otherwise, neutral at 0 / null. */
export function toneBySign(v: number | null | undefined, opts: { positiveGood?: boolean } = {}): Tone {
  if (!isNum(v) || v === 0) return "neutral";
  const positiveGood = opts.positiveGood ?? true;
  return v > 0 === positiveGood ? "emerald" : "crimson";
}

/** Attainment ratio against 1.0 (sinks / issuance, today / breakeven): >= 1 emerald, >= 0.5 amber, else crimson. */
export function toneByRatio(r: number | null | undefined): Tone {
  if (!isNum(r)) return "neutral";
  if (r >= 1) return "emerald";
  if (r >= 0.5) return "amber";
  return "crimson";
}

/** Probability in [0, 1]: >= 2/3 emerald, >= 1/3 amber, else crimson. */
export function toneByProbability(p: number | null | undefined): Tone {
  if (!isNum(p)) return "neutral";
  if (p >= 2 / 3) return "emerald";
  if (p >= 1 / 3) return "amber";
  return "crimson";
}

export function percentiles(v: unknown): PercentileMap | null {
  return isPercentileMap(v) ? v : null;
}

/** a / b when both are finite and b != 0, else null. */
export function ratio(a: number | null | undefined, b: number | null | undefined): number | null {
  if (!isNum(a) || !isNum(b) || b === 0) return null;
  return a / b;
}

// --------------------------------------------------------------------------- manifest record names

/** Benchmark quote record: `quote:<corridor_id>:<clip>` with the clip written as an integer (ledger convention). */
export function quoteRecordName(corridorId: string, clipUsd: number): string {
  return `quote:${corridorId}:${Math.round(clipUsd)}`;
}

/** `near_rpc/block:<epoch_start_height>`: the block header whose total_supply jump is the measured epoch issuance. */
export function epochBlockRef(snapshot: Snapshot): ProvenanceRef | null {
  const h = snapshot.near_rpc?.epoch_issuance?.epoch_start_height;
  return isNum(h) ? { source: "near_rpc", name: `block:${h}` } : null;
}

export const ARCHETYPE_ORDER: readonly CorridorArchetype[] = ["cross_vm", "native_btc", "evm_l2", "native_zec"];
export const ARCHETYPE_LABEL: Record<CorridorArchetype, string> = {
  cross_vm: "cross-VM",
  native_btc: "native BTC",
  evm_l2: "EVM L2",
  native_zec: "native ZEC",
};

/** Corridor label for visible copy: "ETH USDC -> SOL USDC" becomes "ETH USDC to SOL USDC". */
export function corridorText(label: string | null | undefined): string {
  return (label ?? "").replace(/\s*->\s*/g, " to ");
}

/**
 * The 1Click quote record that stands for an archetype's headroom figure: the corridor with that
 * archetype, at the clip whose cell had the most venues quoting (ties -> the larger clip).
 */
export function archetypeQuoteRef(bench: ExecutionBenchmark | null | undefined, archetype: CorridorArchetype): ProvenanceRef | null {
  if (!bench) return null;
  const corridor = (bench.corridors ?? []).find((c) => c.archetype === archetype);
  if (!corridor) return null;
  const cells = (bench.results ?? []).filter((r) => r.corridor_id === corridor.corridor_id);
  if (!cells.length) return null;
  const best = cells.reduce((a, b) => (b.n_venues_ok > a.n_venues_ok || (b.n_venues_ok === a.n_venues_ok && b.clip_usd > a.clip_usd) ? b : a));
  return { source: "oneclick", name: quoteRecordName(corridor.corridor_id, best.clip_usd) };
}

/** Sum of quotes attempted across all benchmark cells (denominator for `n_quotes_ok`). */
export function quotesAttempted(bench: ExecutionBenchmark | null | undefined): number | null {
  if (!bench?.results?.length) return null;
  return bench.results.reduce((n, r) => n + (r.quotes?.length ?? 0), 0);
}

// --------------------------------------------------------------------------- warnings / text refs

/** Merge warning lists, dropping blanks and duplicates, keeping first-seen order. */
export function dedupeWarnings(...lists: Array<ReadonlyArray<string> | null | undefined>): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const list of lists) {
    for (const w of list ?? []) {
      const t = (w ?? "").trim();
      if (t && !seen.has(t)) {
        seen.add(t);
        out.push(t);
      }
    }
  }
  return out;
}

/** "stage: message" -> { stage, message }; a warning without a stage prefix keeps stage null. */
export function splitWarning(w: string): { stage: string | null; message: string } {
  const m = /^([a-z_]+):\s+([\s\S]*)$/.exec(w);
  return m ? { stage: m[1], message: m[2] } : { stage: null, message: w };
}

/**
 * Every `source/name` token in free text (scorecard `source` strings, provenance failure lines)
 * that resolves to a manifest record. Tokens that do not resolve are dropped, so a chip is never
 * shown for a record that does not exist.
 */
export function resolveRefs(text: string, index: ManifestIndex): RawRecord[] {
  const out: RawRecord[] = [];
  const seen = new Set<string>();
  const re = /\b([a-z_]+)\/([A-Za-z0-9_.:@-]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const rec = index.get(m[1], m[2]);
    if (!rec) continue;
    const key = `${rec.source}/${rec.name}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(rec);
  }
  return out;
}

// --------------------------------------------------------------------------- regimes

/** Short nomenclature for the two regime keys the supply model emits; unknown keys pass through. */
export function regimeShortLabel(key: string): string {
  if (key === "status_quo") return "Status quo";
  if (key === "svrn_glidepath") return "SVRN glidepath";
  return key;
}

/** First and last annual inflation rate of a regime's path (null when the path is empty). */
export function regimeEndpoints(snapshot: Snapshot, key: string): { start: number | null; end: number | null } {
  const path = snapshot.supply_physics?.regimes?.find((r) => r.key === key)?.inflation_path_annual ?? [];
  const start = path.length ? path[0] : null;
  const end = path.length ? path[path.length - 1] : null;
  return { start: isNum(start) ? start : null, end: isNum(end) ? end : null };
}

export interface TodayDailyVolume {
  value: number | null;
  /** one-line statement of where the figure comes from (rendered in the regime table footer) */
  basis: string;
  /** snapshot path of the figure actually used */
  path: string;
  /** manifest record the figure traces to: the DefiLlama dexs chart for the labelled input, nearstats summary for the fallback */
  ref: ProvenanceRef | null;
}

const REF_DEXS_VOLUME: ProvenanceRef = { source: "defillama", name: "dexs:near-intents" };
const REF_NEARSTATS_SUMMARY: ProvenanceRef = { source: "nearstats", name: "summary" };

/**
 * Today's daily volume the supply model compares breakeven against: the labelled model input (DefiLlama
 * near-intents daily volume over the canonical take-rate window), else nearstats 30d / 30. The provenance
 * chip follows the branch taken, so the badge never names a payload the number did not come from.
 */
export function todayDailyVolume(snapshot: Snapshot): TodayDailyVolume {
  const input = snapshot.supply_physics?.inputs?.daily_volume_usd;
  if (input && isNum(input.value)) {
    return {
      value: input.value,
      basis: `supply_physics.inputs.daily_volume_usd (${input.source}): ${input.justification}`,
      path: "supply_physics.inputs.daily_volume_usd",
      ref: REF_DEXS_VOLUME,
    };
  }
  const v30 = snapshot.intents_forensics?.volume?.["30d"];
  if (isNum(v30)) return { value: v30 / 30, basis: "intents_forensics.volume.30d / 30 (nearstats intents.totals)", path: "intents_forensics.volume.30d", ref: REF_NEARSTATS_SUMMARY };
  return { value: null, basis: "no 30d volume in snapshot", path: "supply_physics.inputs.daily_volume_usd", ref: null };
}

// --------------------------------------------------------------------------- copy helpers

const STAGE_LABEL: Record<string, string> = {
  execution_bench: "Execution benchmark",
  intents_forensics: "Intents forensics",
  supply_physics: "Supply model",
  sotp: "Valuation model",
  near_rpc: "NEAR RPC",
  comps: "Peer comparables",
  bear_case: "Bear case",
};

/** Pipeline stage key -> human name for the caveats list; unknown keys pass through. */
export function stageLabel(stage: string | null): string {
  if (!stage) return "Pipeline";
  return STAGE_LABEL[stage] ?? stage;
}

const SOURCE_LABEL: Record<string, string> = {
  oneclick: "1Click",
  relay: "Relay",
  lifi: "LI.FI",
  across: "Across",
  near_rpc: "NEAR RPC",
  nearstats: "NearStats",
  nearblocks: "NearBlocks",
  defillama: "DefiLlama",
  coingecko: "CoinGecko",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

/** "a, b and c" */
export function joinAnd(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
