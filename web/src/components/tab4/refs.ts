import type { ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import type { Manifest, RawRecord } from "@/lib/types";

/** Manifest (source, name) pairs the Tab 4 figures trace to. Names match `artifacts/manifest.json` records. */
export const REF = {
  blockFinal: { source: "near_rpc", name: "block_final" },
  protocolConfig: { source: "near_rpc", name: "protocol_config" },
  nearstatsSummary: { source: "nearstats", name: "summary" },
  priceHistory1y: { source: "nearstats", name: "price_history:1y" },
  intentsDexVolume: { source: "defillama", name: "dexs:near-intents" },
  intentsFees: { source: "defillama", name: "fees:near-intents:dailyFees" },
  intentsHoldersRevenue: { source: "defillama", name: "fees:near-intents:dailyHoldersRevenue" },
  nearGasRevenue: { source: "defillama", name: "fees:near:dailyRevenue" },
  coingeckoMarkets: { source: "coingecko", name: "coins_markets" },
  oneclickCrossVm50k: { source: "oneclick", name: "quote:eth_usdc_sol_usdc:50000" },
  relayCrossVm50k: { source: "relay", name: "quote:eth_usdc_sol_usdc:50000" },
} as const satisfies Record<string, ProvenanceRef>;

export function peerFeesRef(slug: string): ProvenanceRef {
  return { source: "defillama", name: `fees:${slug}:dailyFees` };
}

export function peerRevenueRef(slug: string): ProvenanceRef {
  return { source: "defillama", name: `fees:${slug}:dailyRevenue` };
}

/** Most recent record of `source` whose name starts with `prefix` (archival names embed the block height). */
export function findRecord(manifest: Manifest | null, source: string, prefix: string): RawRecord | null {
  if (!manifest) return null;
  let found: RawRecord | null = null;
  for (const r of manifest.records) if (r.source === source && r.name.startsWith(prefix)) found = r;
  return found;
}
