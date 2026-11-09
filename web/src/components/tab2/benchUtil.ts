import { ARCHETYPE_LABELS, clipToRawAmount, getCorridor, type CorridorDef } from "@/lib/corridors";
import { fmtUsd } from "@/lib/format";
import { SERIES_COLORS, type Tone } from "@/lib/theme";
import type { CallerClass, Corridor, CorridorArchetype, CorridorClipResult, QuoteStatus, VenueName, VenueQuote } from "@/lib/types";

/**
 * Pure helpers shared by the Tab 2 components. No React and no server-only imports, so the
 * same code runs in server components and in the client race widget.
 */

/** Ledger `source` of a venue's quote records (manifest.sources keys; `1click` is recorded as `oneclick`). */
export const VENUE_SOURCE: Record<VenueName, string> = { "1click": "oneclick", relay: "relay", lifi: "lifi", across: "across" };

export const VENUE_SHORT: Record<VenueName, string> = { "1click": "1Click", relay: "Relay", lifi: "LI.FI", across: "Across" };

export function venueShort(v: string | null | undefined): string {
  if (!v) return "n/a";
  return (VENUE_SHORT as Record<string, string>)[v] ?? v;
}

/** Record name used by execution_bench.py and liveBenchmark.ts for one venue quote: `quote:<corridor_id>:<clip>`. */
export function quoteRecordName(corridorId: string, clipUsd: number): string {
  return `quote:${corridorId}:${clipUsd}`;
}

export function clipLabel(clipUsd: number): string {
  return fmtUsd(clipUsd, { decimals: 0 });
}

export type FrictionBasis = "raw" | "usd";

export const FRICTION_BASIS_LABEL: Record<FrictionBasis, string> = {
  raw: "raw destination units (same-asset corridor, no oracle)",
  usd: "USD legs (cross-asset corridor; oracle per quote usd_basis)",
};

/** Which friction field a cell is read on: `friction_bps_raw` where the cell was scored raw, else `friction_bps_usd`. */
export function cellFrictionBasis(cell: Pick<CorridorClipResult, "headroom_basis" | "quotes">): FrictionBasis {
  if (cell.headroom_basis === "raw") return "raw";
  if (cell.headroom_basis === "usd") return "usd";
  return cell.quotes.some((q) => typeof q.friction_bps_raw === "number") ? "raw" : "usd";
}

export function frictionOf(q: VenueQuote, basis: FrictionBasis): number | null {
  const v = basis === "raw" ? q.friction_bps_raw : q.friction_bps_usd;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** Positive = emerald (1Click delivers more), negative = crimson, zero or missing = neutral. */
export function signTone(v: number | null | undefined): Tone {
  if (typeof v !== "number" || !Number.isFinite(v) || v === 0) return "neutral";
  return v > 0 ? "emerald" : "crimson";
}

export const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-ink",
  emerald: "text-emerald",
  amber: "text-amber",
  crimson: "text-crimson",
  accent: "text-ink",
};

export function quoteByVenue(quotes: VenueQuote[]): Partial<Record<VenueName, VenueQuote>> {
  const out: Partial<Record<VenueName, VenueQuote>> = {};
  for (const q of quotes) out[q.venue] = q;
  return out;
}

export function statusText(status: QuoteStatus): string {
  return status.replace(/_/g, " ");
}

export function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

/** Why a cell carries no headroom, read from its own quotes. */
export function headroomMissingReason(cell: CorridorClipResult): string {
  const oc = cell.quotes.find((q) => q.venue === "1click");
  if (!oc) return "no 1Click quote in this cell";
  if (oc.status !== "ok") return `1Click ${statusText(oc.status)}${oc.error_message ? `: ${oc.error_message}` : ""}`;
  if (!cell.quotes.some((q) => q.venue !== "1click" && q.status === "ok")) return "no competitor returned an ok quote";
  return "cell not scored by the collector";
}

function parseRaw(raw: string | null | undefined): bigint | null {
  if (!raw || !/^\d+$/.test(raw)) return null;
  return BigInt(raw);
}

// --------------------------------------------------------------------------- caller classes
/** Categorical colours for caller classes: series palette only, never the sign colours. */
export const CALLER_CLASS_COLOR: Record<CallerClass, string> = {
  named_account: SERIES_COLORS[0],
  bridge_relayer: SERIES_COLORS[1],
  ai_agent: SERIES_COLORS[2],
  implicit_account: SERIES_COLORS[3],
  self_internal: SERIES_COLORS[4],
  system: SERIES_COLORS[4],
};

const CALLER_CLASS_LABEL: Record<string, string> = {
  named_account: "Named account",
  bridge_relayer: "Bridge or token contract",
  ai_agent: "AI agent (by name)",
  implicit_account: "Implicit account",
  self_internal: "intents.near itself",
  system: "System",
};

export function callerClassLabel(c: string): string {
  return CALLER_CLASS_LABEL[c] ?? c.replace(/_/g, " ");
}

// --------------------------------------------------------------------------- request reconstruction (audit)
export interface ReconstructedRequest {
  venue: VenueName;
  method: "POST";
  body: Record<string, unknown>;
  note: string;
}

/**
 * The two POST venues' bodies, rebuilt from `corridors.ts` plus the recipient/refund addresses the
 * server echoed in `response.corridor`. GET venues need no reconstruction: their records carry the
 * exact URL. The 1Click `deadline` is generated server-side at send time, so its sha256 cannot be
 * recomputed from this text; the Relay body has no time-dependent field.
 */
export function reconstructPostBodies(def: CorridorDef, corridor: Corridor, clipUsd: number): ReconstructedRequest[] {
  const amount = clipToRawAmount(clipUsd, def.origin.decimals);
  const out: ReconstructedRequest[] = [];
  if (def.venues_attempted.includes("1click")) {
    out.push({
      venue: "1click",
      method: "POST",
      body: {
        dry: true,
        swapType: "EXACT_INPUT",
        slippageTolerance: 100,
        originAsset: def.venues.oneclick.originAsset,
        depositType: "ORIGIN_CHAIN",
        destinationAsset: def.venues.oneclick.destinationAsset,
        amount,
        refundTo: corridor.origin.address,
        refundType: "ORIGIN_CHAIN",
        recipient: corridor.destination.address,
        recipientType: "DESTINATION_CHAIN",
        deadline: "<set server-side at send time: now + 2 h, ISO-8601 UTC, .000Z>",
      },
      note: "reconstructed from corridors.ts and response.corridor addresses; the deadline is generated server-side, so verify against the record request_body_sha256 rather than this text",
    });
  }
  const relay = def.venues.relay;
  if (relay && def.venues_attempted.includes("relay")) {
    out.push({
      venue: "relay",
      method: "POST",
      body: {
        user: corridor.origin.address,
        originChainId: relay.originChainId,
        destinationChainId: relay.destinationChainId,
        originCurrency: relay.originCurrency,
        destinationCurrency: relay.destinationCurrency,
        recipient: corridor.destination.address,
        tradeType: "EXACT_INPUT",
        amount,
      },
      note: "reconstructed from corridors.ts and response.corridor addresses; no time-dependent field, so sha256 of the sorted-key compact JSON should equal the Relay record request_body_sha256",
    });
  }
  return out;
}

// --------------------------------------------------------------------------- display labels
/** "Cross-VM" -> "cross-VM", "Native BTC" -> "native BTC", "EVM L2" unchanged: for use mid-sentence. */
export function archetypePhrase(a: CorridorArchetype): string {
  const l = ARCHETYPE_LABELS[a] ?? a;
  return l.length > 1 && l[1] === l[1].toLowerCase() && l[1] !== l[1].toUpperCase() ? l[0].toLowerCase() + l.slice(1) : l;
}

/** Human route name from corridors.ts ("USDC on Ethereum to BTC on Bitcoin"); falls back to the id. */
export function routeName(corridorId: string, fallback?: string): string {
  const d = getCorridor(corridorId);
  if (!d) return (fallback ?? corridorId).replace(/\s*->\s*/g, " to ");
  return `${d.origin.symbol} on ${d.origin.chain_label} to ${d.destination.symbol} on ${d.destination.chain_label}`;
}

const HEADROOM_BASIS_LABEL: Record<string, string> = {
  dest_units: "destination units",
  out_units: "output units",
  raw: "raw units",
  usd: "USD legs",
};
export function headroomBasisLabel(b: string | null | undefined): string {
  if (!b) return "n/a";
  return HEADROOM_BASIS_LABEL[b] ?? b.replace(/_/g, " ");
}

const PRICE_BASIS_LABEL: Record<string, string> = {
  oneclick_token_list_oracle: "1Click token-list price",
  median_venue_oracle: "median of venue-implied prices",
  venue_oracle: "each venue's own USD legs",
};
export function priceBasisLabel(b: string | null | undefined): string {
  if (!b) return "none";
  return PRICE_BASIS_LABEL[b] ?? b.replace(/_/g, " ");
}

/** Sum of a quote's itemised USD fees (null when the venue itemised none). */
export function feeTotalUsd(q: VenueQuote): number | null {
  const vals = Object.values(q.fee_breakdown_usd ?? {}).filter((v) => typeof v === "number" && Number.isFinite(v));
  return vals.length ? vals.reduce((a, b) => a + b, 0) : null;
}

/**
 * 1Click's advantage over each ok competitor on raw destination units, same sign convention as
 * headroom: (out_1click - out_venue) / out_venue x 1e4; positive = 1Click delivers more.
 */
export function oneclickAdvantageBps(quotes: VenueQuote[]): Map<VenueName, number> {
  const out = new Map<VenueName, number>();
  const oc = quotes.find((q) => q.venue === "1click" && q.status === "ok");
  const base = parseRaw(oc?.amount_out_raw);
  if (base === null) return out;
  for (const q of quotes) {
    if (q.venue === "1click" || q.status !== "ok") continue;
    const v = parseRaw(q.amount_out_raw);
    if (v === null || v === BigInt(0)) continue;
    out.set(q.venue, (Number(base - v) / Number(v)) * 1e4);
  }
  return out;
}

/**
 * One plain-language verdict per route, built only from the cells: who delivers more at each scored
 * size, where 1Click returned no quote, and which venues cannot route the pair.
 */
export function routeVerdict(cells: CorridorClipResult[]): string {
  const sorted = [...cells].sort((a, b) => a.clip_usd - b.clip_usd);
  const scored = sorted.filter((c) => typeof c.headroom_bps === "number");
  const leads = scored.filter((c) => (c.headroom_bps as number) > 0);
  const trails = scored.filter((c) => (c.headroom_bps as number) < 0);
  const bests = [...new Set(trails.map((c) => c.best_competitor).filter(Boolean))].map(venueShort);
  const parts: string[] = [];
  if (!scored.length) parts.push("Not scored: 1Click returned no comparable quote at any size.");
  else if (leads.length === scored.length) parts.push(`1Click delivers the most at every scored size (${scored.map((c) => clipLabel(c.clip_usd)).join(", ")}).`);
  else if (trails.length === scored.length) parts.push(`${bests.join(" and ") || "A competitor"} delivers more than 1Click at every scored size.`);
  else {
    parts.push(
      `Mixed: 1Click leads at ${leads.map((c) => clipLabel(c.clip_usd)).join(", ") || "no size"} and trails at ${trails.map((c) => clipLabel(c.clip_usd)).join(", ") || "no size"}.`,
    );
  }
  const noQuote = sorted.filter((c) => typeof c.headroom_bps !== "number" && c.quotes.some((q) => q.venue === "1click" && q.status !== "ok"));
  if (noQuote.length) parts.push(`1Click returned no quote at ${noQuote.map((c) => clipLabel(c.clip_usd)).join(" and ")} (${statusText(noQuote[0].quotes.find((q) => q.venue === "1click")?.status ?? "error")}).`);
  const unsupported = new Set<string>();
  for (const c of sorted) for (const q of c.quotes) if (q.status === "unsupported_route" && q.venue !== "1click") unsupported.add(venueShort(q.venue));
  if (unsupported.size) parts.push(`${[...unsupported].join(" and ")} cannot route this pair.`);
  return parts.join(" ");
}

export function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}
