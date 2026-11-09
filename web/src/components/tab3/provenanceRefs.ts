import type { ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import type { ContractSinkSnapshot, NearOnchainTruth } from "@/lib/types";

/**
 * Manifest record names the supply tab resolves its figures against (see `artifacts/manifest.json`).
 * Names are built from the snapshot (epoch heights, account ids) so they track whatever block the
 * pipeline actually read; when a record is absent the badge says "no record" rather than guessing.
 */
export const REF_BLOCK_FINAL: ProvenanceRef = { source: "near_rpc", name: "block_final" };
export const REF_PROTOCOL_CONFIG: ProvenanceRef = { source: "near_rpc", name: "protocol_config" };
export const REF_VALIDATORS: ProvenanceRef = { source: "near_rpc", name: "validators" };
export const REF_NEARSTATS_SUMMARY: ProvenanceRef = { source: "nearstats", name: "summary" };
export const REF_DEXS_VOLUME: ProvenanceRef = { source: "defillama", name: "dexs:near-intents" };
export const REF_GROSS_FEES: ProvenanceRef = { source: "defillama", name: "fees:near-intents:dailyFees" };
export const REF_HOLDERS_REVENUE: ProvenanceRef = { source: "defillama", name: "fees:near-intents:dailyHoldersRevenue" };

export function refBlock(height: number | null | undefined): ProvenanceRef | null {
  return typeof height === "number" && Number.isFinite(height) ? { source: "near_rpc", name: `block:${height}` } : null;
}

/** The block before an epoch start: the supply jump is `total_supply(h) - total_supply(pred_of h)`. */
export function refPredBlock(height: number | null | undefined): ProvenanceRef | null {
  return typeof height === "number" && Number.isFinite(height) ? { source: "near_rpc", name: `block:pred_of:${height}` } : null;
}

export function refViewAccount(accountId: string): ProvenanceRef {
  return { source: "near_rpc", name: `view_account:${accountId}` };
}

/** Archival `view_account` at a historical block (`near_rpc_archival` source); `days_before_now === 0` is the live read. */
export function refSinkHistoryPoint(sink: ContractSinkSnapshot, blockHeight: number, daysBeforeNow: number): ProvenanceRef {
  if (daysBeforeNow === 0 || blockHeight === sink.state_block_height) return refViewAccount(sink.account_id);
  return { source: "near_rpc_archival", name: `view_account:${sink.account_id}@${blockHeight}` };
}

/** The oldest archival reading behind the measured state-lock growth (first measured sink). */
export function refStateLockGrowth(rpc: NearOnchainTruth | null | undefined): ProvenanceRef | null {
  if (!rpc) return null;
  const measured = new Set(rpc.measured_state_lock_growth_sinks ?? []);
  for (const sink of rpc.tracked_sinks ?? []) {
    if (!measured.has(sink.account_id) || !Array.isArray(sink.history) || sink.history.length === 0) continue;
    const oldest = [...sink.history].sort((a, b) => b.days_before_now - a.days_before_now)[0];
    if (oldest) return refSinkHistoryPoint(sink, oldest.block_height, oldest.days_before_now);
  }
  return null;
}

/**
 * Record behind each `supply_physics.inputs` row. Assumptions have no record by construction and
 * return null (the panel shows the assumption badge and the justification instead).
 */
export function inputProvenance(key: string, rpc: NearOnchainTruth | null | undefined): ProvenanceRef | null {
  const epoch = rpc?.epoch_issuance?.epoch_start_height ?? null;
  switch (key) {
    case "total_supply_near":
      return REF_BLOCK_FINAL;
    case "current_max_inflation_rate":
    case "treasury_share":
      return REF_PROTOCOL_CONFIG;
    case "staked_supply_ratio":
      return REF_VALIDATORS;
    case "annual_issuance_near":
    case "issuance_realization_factor":
      return refBlock(epoch);
    case "gas_burn_near_per_day":
      return refPredBlock(epoch);
    case "state_lock_growth_near_per_day":
      return refStateLockGrowth(rpc);
    case "near_price_usd":
      return REF_NEARSTATS_SUMMARY;
    case "daily_volume_usd":
      return REF_DEXS_VOLUME;
    case "gross_take_bps":
      return REF_GROSS_FEES;
    case "capture_ratio":
      return REF_HOLDERS_REVENUE;
    default:
      return null;
  }
}

/** Snapshot path hint for inputs without a single raw record (derived statistics, assumptions). */
export function inputPathHint(key: string): string {
  switch (key) {
    case "competitive_fee_ceiling_bps":
      return "execution_bench.competitive_fee_ceiling_bps (median over cross-VM cells of the best competitor's friction)";
    case "custom_cap_inflation":
      return "web slider; never written to the snapshot";
    default:
      return `supply_physics.inputs.${key}`;
  }
}
