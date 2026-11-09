import type { ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import { fmtNum, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import type { ExecutionBenchmark, MarketImpliedSolve } from "@/lib/types";
import { archetypeQuoteRef, isNum } from "./derive";

/**
 * Value of a model input in its own unit, for the market-implied and sensitivity tables.
 * Units are the pipeline's unit tags (market_implied.py / sensitivity.py); unknown tags fall back
 * to a plain number so a new input never renders blank.
 */
export function fmtUnit(v: number | null | undefined, unit: string): string {
  if (!isNum(v)) return NA;
  const a = Math.abs(v);
  switch (unit) {
    case "ratio_yoy":
      return `${fmtPct(v, { decimals: a >= 0.1 || a === 0 ? 0 : 1 })} a year`;
    case "ratio_annual":
      return `${fmtPct(v, { decimals: a >= 0.1 || a === 0 ? 0 : 1 })}`;
    case "ratio":
      return fmtPct(v, { decimals: a >= 0.1 || a === 0 ? 0 : 1 });
    case "per_month":
      return `${fmtPct(v, { decimals: a >= 0.1 || a === 0 ? 0 : 1 })} a month`;
    case "bps":
      return `${fmtNum(v, { decimals: a >= 100 ? 0 : a >= 10 ? 1 : 2 })} bps`;
    case "x":
      return `${fmtNum(v, { decimals: a >= 10 ? 0 : 1 })}×`;
    case "x_base":
      return `${fmtNum(v, { decimals: 2 })}× base`;
    case "usd_per_year":
      return `${fmtUsdCompact(v)} a year`;
    case "usd":
      return fmtUsdCompact(v);
    default:
      return fmtNum(v, { decimals: a >= 100 ? 0 : 2 });
  }
}

/** Short form for the headline: "161% annual volume growth", "a 178 bps public take rate". */
export function leverPhrase(s: MarketImpliedSolve): string {
  const v = s.required_value;
  if (!isNum(v)) return s.short_label;
  switch (s.param) {
    case "public_volume_growth_yoy":
      return `${fmtPct(v, { decimals: 0 })} annual volume growth`;
    case "tau_pub_bps":
      return `a ${fmtUnit(v, "bps")} take rate`;
    case "terminal_multiple":
      return `a ${fmtUnit(v, "x")} multiple`;
    case "confidential_share_target":
      return `a ${fmtPct(v, { decimals: 0 })} confidential share`;
    case "holder_revenue_scale":
      return `${fmtUsdCompact(v)} of year-3 holder revenue`;
    default:
      return `${s.short_label} of ${fmtUnit(v, s.unit)}`;
  }
}

/** Manifest record each solve's evidence traces to (null for assumption-only comparators). */
export function evidenceRef(s: MarketImpliedSolve, bench: ExecutionBenchmark | null | undefined): ProvenanceRef | null {
  switch (s.param) {
    case "public_volume_growth_yoy":
      return { source: "defillama", name: "dexs:near-intents" };
    case "tau_pub_bps":
      return archetypeQuoteRef(bench, "cross_vm");
    case "terminal_multiple":
      return { source: "coingecko", name: "coins_markets" };
    case "confidential_share_target":
      return { source: "nearstats", name: "summary" };
    case "holder_revenue_scale":
      return { source: "defillama", name: "fees:near-intents:dailyHoldersRevenue" };
    default:
      return null;
  }
}

export type SolveStatus = "inside" | "outside" | "unreachable" | "assumption" | "not_compared";

export function solveStatus(s: MarketImpliedSolve): SolveStatus {
  if (!s.reachable || !isNum(s.required_value)) return "unreachable";
  if (s.evidence?.assumption === true) return "assumption";
  const w = s.required_vs_evidence?.within_evidence;
  if (w === true) return "inside";
  if (w === false) return "outside";
  return "not_compared";
}

export function upperFirst(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export function joinOr(items: string[]): string {
  if (items.length <= 1) return items.join("");
  if (items.length === 2) return `${items[0]} or ${items[1]}`;
  return `${items.slice(0, -1).join(", ")} or ${items[items.length - 1]}`;
}
