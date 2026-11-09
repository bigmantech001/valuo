import type { ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import { fmtBps, fmtInt, fmtNum, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import type { Assumption, BearCase, BearScenario, TriggerComparator } from "@/lib/types";

/**
 * Pure helpers for Tab 5 (bear case). No fetching and no defaults: a value that is missing in
 * the snapshot stays `null` and the components render "n/a" with the reason. Every formatter
 * here delegates to `@/lib/format`.
 */

export function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

// ----------------------------------------------------------------------------- trigger status
export type TriggerStatus = "breached" | "clear" | "inconclusive" | "unmeasured";

/** A trigger is only "breached" / "not breached" when the live metric was measured this run. */
export function triggerStatus(value: number | null | undefined, breached: boolean | null | undefined, evaluated?: boolean): TriggerStatus {
  if (evaluated === false || num(value) === null || breached === null || breached === undefined) return "unmeasured";
  return breached ? "breached" : "clear";
}

/**
 * Status of a scenario's whole trigger row. Prefers the pipeline's graded `trigger_status`
 * ("inconclusive" = measured, but on a sample too short to grade); older snapshots fall back to
 * the breached / evaluated flags.
 */
export function scenarioStatus(s: BearScenario): TriggerStatus {
  switch (s.trigger_status) {
    case "breached":
      return "breached";
    case "not_breached":
      return "clear";
    case "inconclusive":
      return "inconclusive";
    case "not_measured":
      return "unmeasured";
    default:
      return triggerStatus(s.current_value, s.trigger_breached, s.trigger_evaluated);
  }
}

/** Why a row is inconclusive, from the span fields: "sample span 188 s, below the 3,600 s minimum". */
export function inconclusiveReason(s: BearScenario): string | null {
  const span = num(s.sample_span_s);
  const min = num(s.min_sample_span_s);
  if (span !== null && min !== null) return `Sample span ${fmtSpan(span)} against ${fmtSpan(min)} required`;
  if (s.primary_status === "thin") return "Sample too thin to grade";
  return null;
}

function fmtSpan(sec: number): string {
  if (sec >= 3600) return `${fmtNum(sec / 3600, { decimals: sec % 3600 === 0 ? 0 : 1 })} h`;
  if (sec >= 120) return `${fmtNum(sec / 60, { decimals: 1 })} min`;
  return `${fmtInt(sec)} s`;
}

export const TRIGGER_BADGE: Record<TriggerStatus, { variant: "warn" | "ok" | "neutral" | "assumption"; label: string }> = {
  breached: { variant: "warn", label: "Breached" },
  clear: { variant: "ok", label: "Not breached" },
  inconclusive: { variant: "assumption", label: "Inconclusive" },
  unmeasured: { variant: "neutral", label: "Not measured" },
};

export function comparatorRule(comparator: TriggerComparator | null | undefined, threshold: string): string {
  return comparator ? `${comparator} ${threshold}` : `threshold ${threshold}`;
}

// ----------------------------------------------------------------------------- value formatting
/** Format a trigger metric by its name (`net_take_bps_30d`, `max_inflation_rate`, `hhi_external_ex_ai_agent`, ...). */
export function fmtMetricValue(metric: string | null | undefined, v: number | null | undefined): string {
  const x = num(v);
  if (x === null) return NA;
  const m = (metric ?? "").toLowerCase();
  if (m.includes("headroom")) return fmtBps(x, { decimals: 2, signed: true });
  if (m.includes("bps") || m.includes("take")) return fmtBps(x, { decimals: 2, signed: false });
  if (m.includes("inflation")) return fmtPct(x, { decimals: 2 });
  if (m.includes("vs_record") || m.includes("drawdown") || m.includes("share")) return fmtPct(x, { decimals: 1, signed: true });
  if (m.includes("hhi")) return fmtInt(x);
  if (m.includes("n_eff")) return fmtNum(x, { decimals: 1 });
  if (m.endsWith("_usd") || m.includes("usd")) return fmtUsdCompact(x);
  if (m.endsWith("_s")) return `${fmtNum(x, { decimals: 1 })} s`;
  if (m.includes("sampled") || m.includes("attributed") || m.includes("count")) return fmtInt(x);
  return fmtNum(x, { decimals: 2 });
}

/** Format a perturbed model input by its key (`tau_pub_bps`, `v_pub_daily_usd`, `svrn_target_inflation`, ...). */
export function fmtPerturbation(key: string, v: number | null | undefined): string {
  const x = num(v);
  if (x === null) return NA;
  const k = key.toLowerCase();
  if (k.includes("headroom")) return fmtBps(x, { decimals: 1, signed: true });
  if (k.endsWith("_bps")) return fmtBps(x, { decimals: 2, signed: false });
  if (k.includes("inflation")) return fmtPct(x, { decimals: 2 });
  if (k.endsWith("_usd")) return fmtUsdCompact(x);
  if (k.includes("hhi")) return fmtInt(x);
  if (k.includes("lambda")) return `${fmtNum(x, { decimals: 2 })} per month`;
  if (k.includes("multiplier")) return `×${fmtNum(x, { decimals: 2 })}`;
  if (k.includes("months")) return `${fmtInt(x)} mo`;
  if (k.includes("share") || k.includes("ratio") || k.includes("alpha") || k.includes("haircut")) return fmtPct(x, { decimals: 1 });
  return fmtNum(x, { decimals: 2 });
}

/** Format a labeled stress parameter by its declared unit. */
export function fmtAssumptionValue(a: Assumption): string {
  const x = num(a.value);
  if (x === null) return NA;
  switch (a.unit) {
    case "bps":
      return fmtBps(x, { decimals: 2, signed: false });
    case "hhi":
      return fmtInt(x);
    case "per_month":
      return `${fmtNum(x, { decimals: 2 })} per month`;
    case "usd":
      return fmtUsdCompact(x);
    case "pct":
    case "percent":
    case "fraction":
      return fmtPct(x, { decimals: 2 });
    case "ratio":
      if (a.key.includes("multiplier")) return `×${fmtNum(x, { decimals: 2 })}`;
      if (a.key.includes("drawdown")) return fmtPct(x, { decimals: 0, signed: true });
      return fmtNum(x, { decimals: 2 });
    case "months":
      return `${fmtInt(x)} mo`;
    default:
      return `${fmtNum(x, { decimals: 2 })} ${a.unit}`;
  }
}

export function fmtAssumptionBound(a: Assumption, v: number): string {
  return fmtAssumptionValue({ ...a, value: v });
}

// ----------------------------------------------------------------------------- provenance mapping
/**
 * Manifest records that back each live metric the triggers are graded against. The names are
 * lookup keys into `artifacts/manifest.json` (ProvenanceLedger names), not data; a missing
 * record renders as "no record".
 */
const DEFILLAMA_TAKE: ProvenanceRef[] = [
  { source: "defillama", name: "fees:near-intents:dailyRevenue" },
  { source: "defillama", name: "dexs:near-intents" },
];
const NEARBLOCKS_CALLERS: ProvenanceRef[] = [{ source: "nearblocks", name: "txns:intents.near:p1" }];
const NEARSTATS_SUMMARY: ProvenanceRef[] = [{ source: "nearstats", name: "summary" }];
const PROTOCOL_CONFIG: ProvenanceRef[] = [{ source: "near_rpc", name: "protocol_config" }];
const CROSS_VM_QUOTES: ProvenanceRef[] = [
  { source: "oneclick", name: "quote:eth_usdc_sol_usdc:50000" },
  { source: "relay", name: "quote:eth_usdc_sol_usdc:50000" },
];

export interface LiveMetricMeta {
  /** plain-language label shown in tables */
  label: string;
  /** what the number is, in one plain sentence */
  describe: string;
  /** exact source field or formula; shown only in the Method note */
  field: string;
  provenance: ProvenanceRef[];
}

export const LIVE_METRIC_META: Record<string, LiveMetricMeta> = {
  net_take_bps: { label: "Net take rate, 30 days", describe: "Protocol revenue divided by swap volume over the last 30 complete days.", field: "DefiLlama near-intents 30d dailyRevenue / 30d DEX volume × 1e4", provenance: DEFILLAMA_TAKE },
  net_take_bps_30d: { label: "Net take rate, 30 days", describe: "Protocol revenue divided by swap volume over the last 30 complete days.", field: "DefiLlama near-intents 30d dailyRevenue / 30d DEX volume × 1e4", provenance: DEFILLAMA_TAKE },
  hhi_external: {
    label: "Deposit-source concentration (HHI)",
    describe: "Concentration of the external accounts that call intents.near (bridge callbacks, direct callers). Not a solver measure; context only, it cannot fire the cartelization trigger.",
    field: "HHI over external predecessor_account_id receipt shares on intents.near, system and self excluded; fills are relayer self-receipts",
    provenance: NEARBLOCKS_CALLERS,
  },
  hhi_external_ex_ai_agent: { label: "Deposit-source HHI, AI agents excluded", describe: "The same caller concentration with AI-agent accounts removed.", field: "deposit/caller HHI excluding *.ai.near and *.agent.near callers", provenance: NEARBLOCKS_CALLERS },
  external_receipts_sampled: { label: "External receipts sampled", describe: "Receipts in the NearBlocks sample the caller concentration is computed on.", field: "count of external receipts in the NearBlocks page", provenance: NEARBLOCKS_CALLERS },
  sample_span_s: { label: "Sample time span", describe: "Wall-clock time covered by the sampled receipts.", field: "wall-clock span of the sampled receipts (seconds)", provenance: NEARBLOCKS_CALLERS },
  hhi_solver: {
    label: "Solver concentration (HHI)",
    describe: "Concentration of fills across solver accounts; the cartelization trigger reads this number.",
    field: "HHI over fill participations per solver, decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); intents_forensics.solver_concentration.hhi_solver",
    provenance: NEARBLOCKS_CALLERS,
  },
  n_eff_solver: { label: "Effective number of solvers", describe: "10,000 divided by solver HHI: how many equal-sized solvers the concentration corresponds to.", field: "10,000 / hhi_solver", provenance: NEARBLOCKS_CALLERS },
  solver_fills_attributed: { label: "Solver fills attributed", describe: "Fill participations matched to a solver account; the trigger is graded only above a minimum sample.", field: "count of solver-attributed fill legs", provenance: NEARBLOCKS_CALLERS },
  solver_fills_sampled: { label: "Fills sampled", describe: "execute_intents fills inspected for solver attribution.", field: "count of execute_intents calls decoded", provenance: NEARBLOCKS_CALLERS },
  headroom_cross_vm_bps: { label: "Cross-VM execution headroom", describe: "Median amount by which 1Click out-delivers the best competitor on ETH USDC to SOL USDC clips.", field: "median (1Click out − best competitor out) / best, ETH USDC → SOL USDC clips with ≥ 1 competitor quote", provenance: CROSS_VM_QUOTES },
  max_inflation_rate: { label: "Protocol inflation cap", describe: "Maximum annual issuance currently set on-chain.", field: "EXPERIMENTAL_protocol_config.max_inflation_rate (num / den)", provenance: PROTOCOL_CONFIG },
  volume_30d_usd: { label: "Intents volume, 30 days", describe: "NEAR Intents swap volume over the last 30 days.", field: "nearstats intents.totals.volume30dUsd", provenance: NEARSTATS_SUMMARY },
  record_30d_usd: { label: "Record 30-day volume", describe: "Highest 30-day volume NEAR Intents has recorded.", field: "nearstats intents.totalsBreakdown.records.max30dUsd", provenance: NEARSTATS_SUMMARY },
  confidential_tvl_usd: { label: "Confidential TVL", describe: "Value held in confidential (shielded) execution, as reported by NearStats.", field: "nearstats intents.protocolMetrics.confidentialTvlUsd", provenance: NEARSTATS_SUMMARY },
  confidential_tvl_verified: { label: "Confidential TVL verified at source", describe: "False when NearStats marks its confidential TVL observation as unverified.", field: "nearstats confidentialTvlObservation.sourceStatus != 'unverified'", provenance: NEARSTATS_SUMMARY },
};

/** Plain-language labels for trigger metrics that are not themselves live-metric keys. */
const METRIC_LABEL_EXTRA: Record<string, string> = {
  volume_30d_vs_record_30d: "30-day volume versus its 30-day record",
};

/** Sentence-case fallback for an unknown snake_case key. */
export function humanizeKey(key: string): string {
  const s = key.replace(/_/g, " ").trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : key;
}

/** Human name for a trigger / live metric key. */
export function metricLabel(metric: string | null | undefined): string {
  if (!metric) return NA;
  return LIVE_METRIC_META[metric]?.label ?? METRIC_LABEL_EXTRA[metric] ?? humanizeKey(metric);
}

const PERTURBATION_LABEL: Record<string, string> = {
  tau_pub_bps: "Public take rate",
  tau_conf_bps: "Confidential take rate",
  tau_floor_bps: "Take-rate floor",
  svrn_target_inflation: "Issuance target",
  v_pub_daily_usd: "Public daily volume",
  v_conf_daily_usd: "Confidential daily volume",
  confidential_tvl_usd: "Confidential TVL",
  hhi_external: "Deposit-source HHI",
  headroom_cross_vm_bps: "Cross-VM headroom",
  fee_compression_lambda_monthly: "Fee compression rate",
};

/** Human name for a perturbed model input. */
export function perturbationLabel(key: string): string {
  return PERTURBATION_LABEL[key] ?? humanizeKey(key);
}

const STRESS_PARAM_LABEL: Record<string, string> = {
  bear_fee_race_tau_pub_bps: "Fee race: public take rate",
  bear_fee_race_tau_conf_bps: "Fee race: confidential take rate",
  bear_fee_race_trigger_net_take_bps: "Fee race: trigger on net take",
  bear_decay_v_pub_multiplier: "Volume decay: public volume multiplier",
  bear_decay_v_conf_multiplier: "Volume decay: confidential volume multiplier",
  bear_decay_tvl_multiplier: "Volume decay: confidential TVL multiplier",
  bear_decay_trigger_volume_drawdown: "Volume decay: trigger on volume versus record",
  bear_cartel_hhi_external: "Cartelization: concentration level",
  bear_cartel_headroom_bps: "Cartelization: cross-VM headroom",
  bear_tau_floor_bps: "Take-rate floor",
  bear_cartel_lambda_monthly: "Cartelization: fee compression rate",
};

/** Human name for a stress-register parameter. */
export function stressParamLabel(key: string): string {
  return STRESS_PARAM_LABEL[key] ?? humanizeKey(key.replace(/^bear_/, ""));
}

/** Provenance for a scenario's early-warning metric, by metric name (falls back to a substring match). */
export function metricProvenance(metric: string | null | undefined): ProvenanceRef[] {
  if (!metric) return [];
  const direct = LIVE_METRIC_META[metric];
  if (direct) return direct.provenance;
  const m = metric.toLowerCase();
  if (m.includes("take")) return DEFILLAMA_TAKE;
  if (m.includes("hhi") || m.includes("solver")) return NEARBLOCKS_CALLERS;
  if (m.includes("headroom")) return CROSS_VM_QUOTES;
  if (m.includes("inflation")) return PROTOCOL_CONFIG;
  if (m.includes("volume") || m.includes("record") || m.includes("tvl")) return NEARSTATS_SUMMARY;
  return [];
}

// ----------------------------------------------------------------------------- basis
/** The model's long statement of what `*_fdv_p50` means (`basis`), else the short `value_basis`. */
export function bearBasis(bc: BearCase): string | null {
  if (typeof bc.basis === "string" && bc.basis) return bc.basis;
  return typeof bc.value_basis === "string" && bc.value_basis ? bc.value_basis : null;
}

/** The short label (`value_basis`, e.g. "deterministic at median inputs; not a Monte Carlo percentile"). */
export function bearValueBasis(bc: BearCase): string | null {
  return typeof bc.value_basis === "string" && bc.value_basis ? bc.value_basis : null;
}

// ----------------------------------------------------------------------------- stress rows
export type StressRowKind = "base" | "scenario" | "combined";

export interface StressRow {
  kind: StressRowKind;
  key: string;
  title: string;
  narrative: string | null;
  perturbations: Record<string, number>;
  applied: Record<string, string>;
  unapplied: string[];
  fdv: number | null;
  drawdown: number | null;
  price: number | null;
  priceDrawdown: number | null;
  /** `undefined` when the field is absent from the snapshot (not computed), `null` = none within horizon */
  crossover: number | null | undefined;
  fdvExMonetary: number | null;
  mcFdv: number | null;
  mcDrawdown: number | null;
  fdvBasis: string | null;
}

function scenarioRow(s: BearScenario): StressRow {
  return {
    kind: "scenario",
    key: s.key,
    title: s.title,
    narrative: s.narrative ?? null,
    perturbations: s.perturbations ?? {},
    applied: s.perturbations_applied ?? {},
    unapplied: s.perturbations_unapplied ?? [],
    fdv: num(s.sotp_fdv_p50),
    drawdown: num(s.drawdown_pct),
    price: num(s.price_p50),
    priceDrawdown: num(s.price_drawdown_pct),
    crossover: "crossover_month" in s ? (s.crossover_month ?? null) : undefined,
    fdvExMonetary: num(s.fdv_ex_monetary),
    mcFdv: num(s.mc_fdv_p50),
    mcDrawdown: num(s.mc_drawdown_pct),
    fdvBasis: s.fdv_basis ?? null,
  };
}

export function buildStressRows(bc: BearCase): StressRow[] {
  const base: StressRow = {
    kind: "base",
    key: "base",
    title: "Base case, unperturbed inputs",
    narrative: null,
    perturbations: {},
    applied: {},
    unapplied: [],
    fdv: num(bc.base_fdv_p50),
    drawdown: null,
    price: num(bc.base_price_p50),
    priceDrawdown: null,
    crossover: "base_crossover_month" in bc ? (bc.base_crossover_month ?? null) : undefined,
    fdvExMonetary: null,
    mcFdv: num(bc.base_mc_fdv_p50),
    mcDrawdown: null,
    fdvBasis: null,
  };
  const combined: StressRow = {
    kind: "combined",
    key: "combined_worst",
    title: `All ${(bc.scenarios ?? []).length} scenarios at once (combined worst)`,
    narrative: null,
    perturbations: bc.combined_perturbations ?? {},
    applied: bc.combined_perturbations_applied ?? {},
    unapplied: bc.combined_perturbations_unapplied ?? [],
    fdv: num(bc.combined_worst_fdv),
    drawdown: num(bc.combined_drawdown_pct),
    price: num(bc.combined_worst_price),
    priceDrawdown: num(bc.combined_price_drawdown_pct),
    crossover: "combined_crossover_month" in bc ? (bc.combined_crossover_month ?? null) : undefined,
    fdvExMonetary: null,
    mcFdv: num(bc.combined_mc_fdv_p50),
    mcDrawdown: num(bc.combined_mc_drawdown_pct),
    fdvBasis: null,
  };
  return [base, ...(bc.scenarios ?? []).map(scenarioRow), combined];
}

/** Count of breached triggers from the snapshot field, else derived from the evaluated scenarios. */
export function triggersBreached(bc: BearCase): { breached: number | null; evaluated: number; unevaluated: string[]; inconclusive: string[] } {
  const scenarios = bc.scenarios ?? [];
  const allUngraded = bc.triggers_unevaluated ?? scenarios.filter((s) => { const st = scenarioStatus(s); return st === "unmeasured" || st === "inconclusive"; }).map((s) => s.key);
  // Split the ungraded keys: inconclusive (measured on too short a sample) vs not measured at all.
  const inconclusive = allUngraded.filter((k) => { const s = scenarios.find((x) => x.key === k); return s ? scenarioStatus(s) === "inconclusive" : false; });
  const unevaluated = allUngraded.filter((k) => !inconclusive.includes(k));
  const evaluated = bc.triggers_evaluated ?? scenarios.length - allUngraded.length;
  const fromSnapshot = num(bc.triggers_breached);
  if (fromSnapshot !== null) return { breached: fromSnapshot, evaluated, unevaluated, inconclusive };
  if (!scenarios.length) return { breached: null, evaluated, unevaluated, inconclusive };
  return { breached: scenarios.filter((s) => scenarioStatus(s) === "breached").length, evaluated, unevaluated, inconclusive };
}

/** Split the falsification summary into one paragraph per scenario key (text is left verbatim). */
export function splitSummary(summary: string | null | undefined, keys: string[]): string[] {
  if (!summary) return [];
  const markers = [...keys, "All four at once"].filter(Boolean);
  if (!markers.length) return [summary];
  const re = new RegExp(`(?=(?:${markers.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")}):)`, "g");
  const parts = summary.split(re).map((p) => p.trim()).filter(Boolean);
  return parts.length ? parts : [summary];
}

/** Hostname + first path segment of a monitor URL, for link text. */
export function shortUrl(url: string | null | undefined): string {
  if (!url) return NA;
  try {
    const u = new URL(url);
    const seg = u.pathname.split("/").filter(Boolean);
    return `${u.hostname}${seg.length ? `/${seg.slice(0, 3).join("/")}` : ""}${seg.length > 3 ? "/…" : ""}`;
  } catch {
    return url;
  }
}

/** Typographic clean-up of model prose for display (ASCII arrows and hyphen-minus); wording is unchanged. */
export function prose(text: string): string {
  return text.replace(/\s->\s/g, " → ").replace(/(^|[\s(])-(?=\d)/g, "$1−");
}
