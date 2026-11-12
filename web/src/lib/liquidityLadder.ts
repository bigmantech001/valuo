/**
 * Types and pure helpers for `snapshot.liquidity_ladder` (quant/valuo/collectors/liquidity_ladder.py):
 * dry quotes at eight sizes ($1K to $5M) per benchmarked corridor and venue. Every figure is the
 * "largest size quoted" on that ladder, never depth.
 */

export type LadderOutcome = "quoted" | "no_liquidity" | "unsupported" | "error" | "not_attempted";

export interface LadderCell {
  size_usd: number;
  outcome: LadderOutcome;
  /** all-in cost in bps on the bench's basis; null unless quoted */
  cost_bps: number | null;
  cost_basis: "raw" | "usd" | null;
  /** destination units */
  amount_out: number | null;
  amount_out_raw: string | null;
  time_estimate_s: number | null;
  /** the venue's refusal or error text, verbatim (truncated) */
  message: string | null;
  route_tool: string | null;
  /** LI.FI quote whose bridge is NEAR Intents itself (1Click execution resold) */
  via_near_intents: boolean;
  called: boolean;
  record_source: string | null;
  record_name: string | null;
  sha256: string | null;
  http_status: number | null;
  latency_ms: number | null;
  fetched_at_utc: string | null;
}

export interface LadderVenue {
  venue: string;
  /** false when the venue does not serve the corridor at all */
  routes: boolean;
  largest_size_quoted_usd: number | null;
  first_size_refused_usd: number | null;
  first_refusal_message: string | null;
  contiguous_to_usd: number | null;
  /** a size below the largest size quoted was refused */
  non_monotone: boolean;
  clean_ladder: boolean;
  ceiling_observed: boolean;
  unresolved_below_largest_usd: number[];
  cost_bps_at_largest: number | null;
  cost_bps_at_250k: number | null;
  via_near_intents_at_largest: boolean;
  largest_size_quoted_independent_usd: number | null;
  n_quoted: number;
  n_attempted: number;
  cost_curve: { size_usd: number; cost_bps: number | null }[];
  cells: LadderCell[];
}

export interface LadderCheapest {
  size_usd: number;
  venue: string | null;
  cost_bps: number | null;
  n_quoted: number;
  venues_quoted: string[];
}

export type LadderRelation = "larger" | "equal" | "smaller" | "inconclusive" | "not_measured";

export interface LadderCorridor {
  corridor_id: string;
  label: string;
  archetype?: string | null;
  cost_basis?: string | null;
  price_basis?: Record<string, unknown> | null;
  largest_size_quoted_usd: number | null;
  largest_size_venues: string[];
  oneclick_largest_size_quoted_usd: number | null;
  best_competitor: string | null;
  best_competitor_largest_size_quoted_usd: number | null;
  best_competitor_via_near_intents: boolean;
  best_independent_competitor?: string | null;
  best_independent_competitor_largest_size_quoted_usd?: number | null;
  oneclick_vs_best_competitor: LadderRelation;
  any_non_monotone: boolean;
  cheapest_by_size: LadderCheapest[];
  venues: LadderVenue[];
}

export interface LiquidityLadder {
  ran_at_utc: string;
  sizes_usd: number[];
  institutional_size_usd: number;
  venues: string[];
  headline: string;
  takeaway: string;
  caveats: string[];
  corridors: LadderCorridor[];
  outcome_counts: Partial<Record<LadderOutcome, number>>;
  n_cells: number;
  n_http_records: number;
  cost_definition: string;
  record_name_pattern: string;
  token_list_ok: boolean;
  token_list_sha256?: string | null;
  all_quotes_dry: boolean;
  budget_s: number;
  concurrency: number;
  request_timeout_s: number;
  elapsed_s: number;
}

/** $1K, $250K, $2.5M: the ladder's rung labels. */
export function ladderSizeLabel(sizeUsd: number | null | undefined): string {
  if (typeof sizeUsd !== "number" || !Number.isFinite(sizeUsd)) return "none";
  const trim = (v: number) => String(Number(v.toFixed(2)));
  if (sizeUsd >= 1e6) return `$${trim(sizeUsd / 1e6)}M`;
  if (sizeUsd >= 1e3) return `$${trim(sizeUsd / 1e3)}K`;
  return `$${trim(sizeUsd)}`;
}

/** The cell of one venue at one size, or null when the snapshot holds none. */
export function ladderCellAt(venue: LadderVenue, sizeUsd: number): LadderCell | null {
  return venue.cells.find((c) => c.size_usd === sizeUsd) ?? null;
}

/** Short text for a cell that carries no quote. A missed budget is never worded as a refusal. */
export function ladderOutcomeText(cell: LadderCell | null): string {
  if (!cell) return "Not attempted";
  switch (cell.outcome) {
    case "quoted":
      return "Quoted";
    case "no_liquidity":
      return "No quote at this size";
    case "unsupported":
      return cell.called ? "Route refused at this size" : "Does not route this corridor";
    case "error":
      return "Request failed";
    default:
      return "Not attempted";
  }
}

/** Largest quoted cost on a corridor, the common scale of its bars (one scale per corridor, all venues and sizes). */
export function ladderMaxCost(corridor: LadderCorridor): number {
  let max = 0;
  for (const v of corridor.venues) for (const c of v.cells) if (c.outcome === "quoted" && typeof c.cost_bps === "number") max = Math.max(max, c.cost_bps);
  return max;
}
