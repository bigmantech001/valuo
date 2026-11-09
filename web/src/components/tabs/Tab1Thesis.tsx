import { CausalChain, Caveats, EngineWaterfall, EvidenceScorecard, MarketImpliedOpening, VerdictBanner } from "@/components/tab1";
import type { TabProps } from "./types";

/**
 * Tab 1: the executive summary of the investment thesis.
 *
 * 1. What the market is pricing: each model input solved alone against the market FDV, set
 *    against what this run measured (absent from older snapshots; the verdict then leads)
 * 2. What the cash-flow model values: key figures, valuation percentiles, supply crossover
 * 3. The causal chain: execution headroom, take rate and stickiness, supply sinks, valuation
 * 4. Evidence scorecard exactly as the pipeline graded it
 * 5. The three valuation engines (medians do not add)
 * 6. Warnings and failed fetches, fully listed
 *
 * Server component. Every number is read from the snapshot; snapshot paths and formulas sit in
 * each section's "Method and sources" note.
 */
export function Tab1Thesis({ snapshot, manifest }: TabProps) {
  const hasMarketImplied = Boolean(snapshot.market_implied?.solves?.length);
  return (
    <div className="space-y-16">
      {hasMarketImplied ? <MarketImpliedOpening snapshot={snapshot} /> : null}
      <VerdictBanner snapshot={snapshot} lead={!hasMarketImplied} />
      <CausalChain snapshot={snapshot} />
      <EvidenceScorecard snapshot={snapshot} manifest={manifest} />
      <EngineWaterfall snapshot={snapshot} />
      <Caveats snapshot={snapshot} manifest={manifest} />
    </div>
  );
}
