import type { Assumption, EvidenceClaim, Manifest, PercentileMap, Snapshot, TriggerComparator } from "@/lib/types";

/**
 * Read-only view model for the landing page. Every field is copied from the snapshot /
 * manifest (or derived by one arithmetic step that is named in the field comment); nothing is
 * defaulted to a "typical" value - missing data stays null and the UI prints n/a.
 */

const asDict = (v: unknown): Record<string, unknown> => (v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {});
const numOf = (d: Record<string, unknown>, k: string): number | null => {
  const v = d[k];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
};
const numField = (o: object | null | undefined, k: string): number | null => (o ? numOf(o as Record<string, unknown>, k) : null);
const strField = (o: object | null | undefined, k: string): string | null => {
  const v = o ? (o as Record<string, unknown>)[k] : undefined;
  return typeof v === "string" && v.length ? v : null;
};
const boolField = (o: object | null | undefined, k: string): boolean | null => {
  const v = o ? (o as Record<string, unknown>)[k] : undefined;
  return typeof v === "boolean" ? v : null;
};
const pairOf = (v: unknown): [number, number] | null =>
  Array.isArray(v) && v.length === 2 && v.every((x) => typeof x === "number" && Number.isFinite(x)) ? [v[0] as number, v[1] as number] : null;
const strOf = (d: Record<string, unknown>, k: string): string | null => (typeof d[k] === "string" && (d[k] as string).length ? (d[k] as string) : null);
const boolOf = (d: Record<string, unknown>, k: string): boolean | null => (typeof d[k] === "boolean" ? (d[k] as boolean) : null);

function coverageOf(v: unknown): MultipleCoverage | null {
  const d = asDict(v);
  if (!Object.keys(d).length) return null;
  return {
    label: strOf(d, "label"),
    value: numOf(d, "value"),
    rank: numOf(d, "rank"),
    n: numOf(d, "n"),
    peerMedian: numOf(d, "peer_median"),
    peerMin: numOf(d, "peer_min"),
    peerMax: numOf(d, "peer_max"),
    position: strOf(d, "position"),
  };
}

/** snapshot.market_implied, read defensively (the key is new; older snapshots lack it). */
function marketImpliedOf(v: unknown): MarketImpliedView | null {
  const d = asDict(v);
  if (!Object.keys(d).length) return null;
  const solves: SolveView[] = (Array.isArray(d.solves) ? d.solves : []).map((raw) => {
    const x = asDict(raw);
    const ev = asDict(x.evidence);
    const rve = asDict(x.required_vs_evidence);
    return {
      param: strOf(x, "param") ?? "",
      label: strOf(x, "label") ?? strOf(x, "param") ?? "",
      shortLabel: strOf(x, "short_label") ?? strOf(x, "label") ?? strOf(x, "param") ?? "",
      unit: strOf(x, "unit") ?? "",
      baseValue: numOf(x, "base_value"),
      requiredValue: numOf(x, "required_value"),
      reachable: x.reachable === true,
      reason: strOf(x, "reason"),
      evidenceValue: numOf(ev, "value"),
      evidenceLabel: strOf(ev, "label"),
      evidenceSource: strOf(ev, "source"),
      evidenceIsAssumption: ev.assumption === true,
      evidenceStatus: strOf(ev, "status"),
      ratio: numOf(rve, "ratio"),
      withinEvidence: boolOf(rve, "within_evidence"),
      verdict: strOf(x, "verdict"),
      modelCap: numOf(ev, "model_cap"),
      peers: (Array.isArray(ev.peers) ? ev.peers : [])
        .map((p) => asDict(p))
        .map((p) => ({ symbol: strOf(p, "symbol") ?? "", value: numOf(p, "fdv_to_revenue") }))
        .filter((p): p is { symbol: string; value: number } => p.value !== null),
    };
  });
  return {
    currentFdv: numOf(d, "current_fdv_usd"),
    baseFdv: numOf(d, "base_fdv_usd"),
    baseFdvMcP50: numOf(d, "base_fdv_mc_p50_usd"),
    gapMultiple: numOf(d, "gap_multiple"),
    horizonMonths: numOf(d, "horizon_months"),
    basis: strOf(d, "basis"),
    headline: strOf(d, "headline"),
    nReachable: numOf(d, "n_reachable"),
    nWithinEvidence: numOf(d, "n_within_evidence"),
    solves,
  };
}

function sensitivityOf(v: unknown): SensitivityView | null {
  const d = asDict(v);
  if (!Array.isArray(d.rows)) return null;
  return {
    rows: d.rows.map((raw) => {
      const r = asDict(raw);
      return {
        rank: numOf(r, "rank"),
        param: strOf(r, "param"),
        label: strOf(r, "label") ?? strOf(r, "param") ?? "",
        fdvLow: numOf(r, "fdv_low"),
        fdvHigh: numOf(r, "fdv_high"),
        swingUsd: numOf(r, "swing_usd"),
        varianceShare: numOf(r, "variance_share"),
      };
    }),
    top3Share: numOf(d, "top3_share"),
    headline: strOf(d, "headline"),
  };
}

function relativeValueOf(v: unknown): RelativeValueView | null {
  const d = asDict(v);
  if (!Object.keys(d).length) return null;
  const cov = asDict(d.coverage);
  const band = asDict(asDict(d.implied_fdv_band).fees);
  const near = asDict(d.near);
  const staking = asDict(d.staking);
  return {
    feesRunRate: coverageOf(cov.fdv_to_fees_run_rate),
    revenueRunRate: coverageOf(cov.fdv_to_revenue_run_rate),
    nPeers: numOf(d, "n_peers"),
    peerSymbols: (Array.isArray(d.peers) ? d.peers : []).map((p) => strOf(asDict(p), "symbol")).filter((s): s is string => s !== null),
    modelTerminalMultiple: numOf(d, "model_terminal_multiple"),
    nPeersAtOrBelowModel: numOf(d, "n_peers_at_or_below_model_multiple"),
    nearFeesUsd: numOf(near, "annualized_fees_usd"),
    nearRevenueUsd: numOf(near, "annualized_revenue_usd"),
    impliedFees: Object.keys(band).length
      ? { p25: numOf(band, "p25_fdv_usd"), median: numOf(band, "median_fdv_usd"), p75: numOf(band, "p75_fdv_usd"), n: numOf(band, "n_peers") }
      : null,
    securityBudgetUsd: numOf(staking, "security_budget_usd_per_year"),
    revenueToSecurityBudget: numOf(staking, "revenue_to_security_budget"),
    caveat: strOf(d, "caveat"),
  };
}

/** `bear_case.stress_parameters` is a list of Assumption in the schema; older snapshots keyed it by name. */
const assumptionByKey = (params: unknown, key: string): Assumption | null => {
  if (Array.isArray(params)) return (params as Assumption[]).find((a) => a && a.key === key) ?? null;
  const d = asDict(params);
  return d[key] && typeof d[key] === "object" ? (d[key] as Assumption) : null;
};

export interface HeadroomCell {
  clipUsd: number;
  headroomBps: number | null;
  basis: string | null;
  bestCompetitor: string | null;
  oneclickRank: number | null;
  oneclickStatus: string | null;
  venuesOk: number;
  venuesUnsupported: string[];
}

export interface CorridorView {
  id: string;
  label: string;
  archetype: string;
  medianHeadroomBps: number | null;
  nCells: number | null;
  /** best_competitor of the scored cells (same venue in every scored cell this run; first one otherwise) */
  bestCompetitor: string | null;
  clipsUsd: number[];
  cells: HeadroomCell[];
}

export interface BearScenarioView {
  key: string;
  title: string;
  drawdownPct: number;
  fdv: number;
  metric: string;
  current: number | null;
  threshold: number;
  comparator: TriggerComparator | null;
  breached: boolean | null;
  /** false = metric unmeasured or sample too thin to grade; null on older snapshots */
  evaluated: boolean | null;
  /** cartel scenario only: HHI_solver graded on fewer fills than the model's threshold */
  sampleThin: boolean | null;
  fillsSampled: number | null;
  monitor: string;
  /** bear_case.scenarios[].trigger_status ("breached" | "clear" | "inconclusive" | "not_measured"); null on older snapshots */
  status: string | null;
  note: string | null;
  sampleSpanS: number | null;
  minSampleSpanS: number | null;
  hhiCi90: [number, number] | null;
}

export interface SolveView {
  param: string;
  label: string;
  shortLabel: string;
  unit: string;
  baseValue: number | null;
  requiredValue: number | null;
  reachable: boolean;
  reason: string | null;
  evidenceValue: number | null;
  evidenceLabel: string | null;
  evidenceSource: string | null;
  /** true when the "evidence" is itself a registry assumption (e.g. confidential share fallback) */
  evidenceIsAssumption: boolean;
  evidenceStatus: string | null;
  ratio: number | null;
  withinEvidence: boolean | null;
  verdict: string | null;
  modelCap: number | null;
  peers: Array<{ symbol: string; value: number }>;
}

export interface MultipleCoverage {
  label: string | null;
  value: number | null;
  rank: number | null;
  n: number | null;
  peerMedian: number | null;
  peerMin: number | null;
  peerMax: number | null;
  position: string | null;
}

export interface MarketImpliedView {
  currentFdv: number | null;
  baseFdv: number | null;
  baseFdvMcP50: number | null;
  gapMultiple: number | null;
  horizonMonths: number | null;
  basis: string | null;
  headline: string | null;
  nReachable: number | null;
  nWithinEvidence: number | null;
  solves: SolveView[];
}

export interface SensitivityView {
  rows: Array<{ rank: number | null; param: string | null; label: string; fdvLow: number | null; fdvHigh: number | null; swingUsd: number | null; varianceShare: number | null }>;
  top3Share: number | null;
  headline: string | null;
}

export interface RelativeValueView {
  feesRunRate: MultipleCoverage | null;
  revenueRunRate: MultipleCoverage | null;
  nPeers: number | null;
  peerSymbols: string[];
  modelTerminalMultiple: number | null;
  nPeersAtOrBelowModel: number | null;
  nearFeesUsd: number | null;
  nearRevenueUsd: number | null;
  impliedFees: { p25: number | null; median: number | null; p75: number | null; n: number | null } | null;
  securityBudgetUsd: number | null;
  revenueToSecurityBudget: number | null;
  caveat: string | null;
}

export interface LandingData {
  generatedAtUtc: string;
  runtimeS: number;
  seed: number;
  valuoVersion: string;
  chain: {
    block: number;
    blockHash: string;
    blockTsUtc: string;
    totalSupply: number;
    validators: number;
    stakedRatio: number;
    inflationCap: number;
    treasuryShare: number;
    rpc: string;
    archival: boolean;
  };
  issuance: {
    measuredDaily: number | null;
    nominalDaily: number;
    mintedPerEpoch: number | null;
    prevMintedPerEpoch: number | null;
    epochHours: number | null;
    epochsPerYear: number | null;
    impliedRate: number | null;
    netBurnPerEpoch: number | null;
    measuredMinusNominalAnnual: number | null;
    epochStartHeight: number;
  };
  stateLock: {
    intentsLocked: number | null;
    intentsBytes: number | null;
    intentsGrowthNearPerDay: number | null;
    intentsGrowthWindowDays: number | null;
    totalLocked: number;
    growthNearPerDay: number | null;
    sinkCount: number;
    storageNearPerKb: number;
  };
  volume: {
    d30: number | null;
    d24h: number | null;
    allTime: number | null;
    confidentialShare30d: number | null;
    confidential30d: number | null;
    public30d: number | null;
    drawdownFromRecord30d: number | null;
    uniqueUsers7d: number | null;
    confidentialTvl: number | null;
    confidentialTvlVerified: boolean;
    /** intents_forensics.volume.confidential_share_status: "implausible_fallback" = registry assumption, not a measurement */
    confidentialShareStatus: string | null;
    confidentialShareMeasured: boolean | null;
    confidentialShareReported: number | null;
    allTimeConfidential: number | null;
  };
  fees: {
    gross30d: number | null;
    net30d: number | null;
    grossTakeBps: number | null;
    netTakeBps: number | null;
    captureRatio: number | null;
    annualizedNet: number | null;
    cumulativeFees: number | null;
  };
  price: { current: number | null; fdv: number | null; sigmaAnnual: number | null };
  bench: {
    ranAtUtc: string;
    headroom: Record<string, number | null>;
    headroomN: Record<string, number>;
    /** "dest_units" on current snapshots; the collector's own definition sentence when present */
    headroomBasis: string | null;
    headroomDefinition: string | null;
    ceilingBps: number | null;
    corridors: CorridorView[];
    quotesOk: number | null;
    quotesTotal: number;
    tokenUniverse: number | null;
    blockchains: number;
    elapsedS: number | null;
    summaryNote: string;
  } | null;
  concentration: {
    /** deposit-side: predecessor accounts of intents.near receipts (context, not the cartel trigger) */
    hhiExternal: number;
    nEffExternal: number;
    hhiAll: number;
    /** solver side: NEP-413 signers of execute_intents fills; what bear_case.solver_cartelization reads */
    hhiSolver: number | null;
    hhiSolverCi90: [number, number] | null;
    sampleSpanS: number | null;
    nEffSolver: number | null;
    solverFills: number | null;
    solverFillsAttributed: number | null;
    uniqueSolvers: number | null;
    /** bear_case.stress_parameters[bear_cartel_hhi_external].value */
    cartelTriggerHhi: number | null;
    aiAgentShare: number;
    bridgeShare: number;
    receiptsSampled: number;
    pagesFetched: number;
    lifetimeReceipts: number | null;
    topCallers: Array<{ account: string; cls: string; share: number }>;
  };
  supply: {
    sinks: { buyback: number | null; gasBurn: number | null; stateLock: number | null; total: number | null };
    issuanceDaily: number;
    coverageRatio: number;
    breakeven: Record<string, number>;
    breakevenAtCeiling: Record<string, number>;
    dailyVolumeNow: number | null;
    deterministicCrossover: Record<string, number | null>;
    mcCrossoverProb: Record<string, number | null>;
    mcDeflationaryAtHorizon: Record<string, number | null>;
  };
  sotp: {
    nPaths: number;
    horizonMonths: number;
    discountRate: number;
    fdv: PercentileMap;
    price: PercentileMap;
    fdvExMonetary: PercentileMap;
    currentFdv: number;
    /** sotp.calibration.current_fdv_basis / price_source, verbatim */
    currentFdvBasis: string | null;
    priceSource: string | null;
    upsideP50Pct: number;
    engines: Array<{ key: string; label: string; p50: number; p10: number; p90: number; assumptionHeavy: boolean }>;
    terminalMultipleUsed: number | null;
    terminalMultipleRaw: number | null;
    terminalMultipleClipped: boolean | null;
    tauFloorBps: number | null;
    sigmaPriceAnnual: number | null;
    sigmaVolumeMonthly: number | null;
  };
  bear: {
    baseFdv: number;
    combinedWorstFdv: number;
    combinedDrawdownPct: number;
    triggersBreached: number | null;
    /** denominator for "x of y breached": triggers graded this run (falls back to scenarios with a non-null verdict) */
    triggersEvaluated: number;
    triggersUnevaluated: string[];
    valueBasis: string | null;
    scenarios: BearScenarioView[];
  };
  marketImplied: MarketImpliedView | null;
  sensitivity: SensitivityView | null;
  relativeValue: RelativeValueView | null;
  scorecard: EvidenceClaim[];
  assumptionsCount: number;
  warnings: string[];
  provenance: {
    records: number | null;
    ok: number | null;
    failures: number | null;
    bytes: number | null;
    sources: Record<string, number>;
    snapshotSha256: string | null;
    manifestBlock: number | null;
  };
}

export function buildLandingData(snapshot: Snapshot, manifest: Manifest | null): LandingData {
  const rpc = snapshot.near_rpc;
  const ep = rpc.epoch_issuance;
  const intents = rpc.tracked_sinks.find((s) => s.account_id === "intents.near") ?? null;
  const f = snapshot.intents_forensics;
  const vol = asDict(f.volume);
  const fees = asDict(f.fees);
  const price = asDict(f.price);
  const vola = asDict(f.volatility);
  const sp = snapshot.supply_physics;
  const so = snapshot.sotp;
  const cal = asDict(so.calibration);
  const cross = asDict(so.crossover_month_distribution);
  const bc = snapshot.bear_case;
  const prov = asDict(snapshot.provenance_summary);
  const eb = snapshot.execution_bench ?? null;

  const regimes = ["status_quo", "svrn_glidepath"];
  const deterministicCrossover: Record<string, number | null> = {};
  for (const r of regimes) {
    const t = sp.trajectories.find((x) => x.regime === r);
    deterministicCrossover[r] = t ? (t.crossover_month ?? null) : null;
  }
  const mcCrossoverProb: Record<string, number | null> = {};
  const mcDeflationaryAtHorizon: Record<string, number | null> = {};
  for (const r of regimes) {
    const d = asDict(cross[r]);
    mcCrossoverProb[r] = numOf(d, "p_crossover_within_36m");
    mcDeflationaryAtHorizon[r] = numOf(d, "p_deflationary_at_horizon");
  }

  const bench = eb
    ? {
        ranAtUtc: eb.ran_at_utc,
        headroom: eb.headroom_by_archetype_bps ?? {},
        headroomN: (asDict((eb as unknown as Record<string, unknown>).headroom_n_by_archetype) as Record<string, number>) ?? {},
        headroomBasis: strField(eb, "headroom_basis"),
        headroomDefinition: strField(eb, "headroom_definition"),
        ceilingBps: eb.competitive_fee_ceiling_bps ?? null,
        corridors: eb.corridors.map((c) => {
          const cells: HeadroomCell[] = eb.results
            .filter((r) => r.corridor_id === c.corridor_id)
            .sort((a, b) => a.clip_usd - b.clip_usd)
            .map((r) => {
              const one = r.quotes.find((q) => q.venue === "1click") ?? null;
              return {
                clipUsd: r.clip_usd,
                headroomBps: r.headroom_bps ?? null,
                basis: (r as unknown as Record<string, unknown>).headroom_basis as string | null ?? null,
                bestCompetitor: r.best_competitor ?? null,
                oneclickRank: r.oneclick_rank ?? null,
                oneclickStatus: one ? one.status : null,
                venuesOk: r.n_venues_ok,
                venuesUnsupported: r.quotes.filter((q) => q.status === "unsupported_route").map((q) => q.venue),
              };
            });
          const scored = cells.filter((x) => x.headroomBps !== null);
          return {
            id: c.corridor_id,
            label: c.label,
            archetype: c.archetype,
            medianHeadroomBps: eb.headroom_by_archetype_bps?.[c.archetype] ?? null,
            nCells: numOf(asDict((eb as unknown as Record<string, unknown>).headroom_n_by_archetype), c.archetype),
            bestCompetitor: scored.find((x) => x.bestCompetitor)?.bestCompetitor ?? cells.find((x) => x.bestCompetitor)?.bestCompetitor ?? null,
            clipsUsd: cells.map((x) => x.clipUsd),
            cells,
          };
        }),
        quotesOk: numField(eb, "n_quotes_ok"),
        quotesTotal: eb.results.reduce((acc, r) => acc + r.quotes.length, 0),
        tokenUniverse: eb.oneclick_1y_token_universe ?? null,
        blockchains: eb.oneclick_blockchains.length,
        elapsedS: numField(eb, "elapsed_s"),
        summaryNote: eb.summary_note,
      }
    : null;

  const sinks = sp.current_daily_sinks_near ?? {};
  const solver = f.solver_concentration ?? null;
  const cartelParam = assumptionByKey(bc.stress_parameters, "bear_cartel_hhi_external");
  const scenarios: BearScenarioView[] = bc.scenarios.map((s) => ({
    key: s.key,
    title: s.title,
    drawdownPct: s.drawdown_pct,
    fdv: s.sotp_fdv_p50,
    metric: s.early_warning_metric,
    current: s.current_value ?? null,
    threshold: s.trigger_threshold,
    comparator: s.trigger_comparator ?? null,
    breached: typeof s.trigger_breached === "boolean" ? s.trigger_breached : null,
    evaluated: boolField(s, "trigger_evaluated"),
    sampleThin: boolField(s, "sample_thin"),
    fillsSampled: numField(s, "solver_fills_sampled"),
    monitor: s.monitor_source,
    status: strField(s, "trigger_status"),
    note: strField(s, "trigger_note"),
    sampleSpanS: numField(s, "sample_span_s"),
    minSampleSpanS: numField(s, "min_sample_span_s"),
    hhiCi90: pairOf((s as unknown as Record<string, unknown>).hhi_solver_ci90),
  }));
  const gradedCount = scenarios.filter((s) => s.breached !== null && s.evaluated !== false).length;
  const snapAny = snapshot as unknown as Record<string, unknown>;

  return {
    generatedAtUtc: snapshot.generated_at_utc,
    runtimeS: snapshot.runtime_s,
    seed: snapshot.seed,
    valuoVersion: snapshot.valuo_version,
    chain: {
      block: rpc.block_height,
      blockHash: rpc.block_hash,
      blockTsUtc: rpc.timestamp_utc,
      totalSupply: rpc.total_supply_near,
      validators: rpc.active_validator_count,
      stakedRatio: rpc.staked_supply_ratio,
      inflationCap: rpc.max_inflation_rate,
      treasuryShare: rpc.protocol_reward_rate,
      rpc: rpc.rpc_endpoint_used,
      archival: rpc.archival_available,
    },
    issuance: {
      measuredDaily: numField(rpc, "measured_daily_issuance_near"),
      nominalDaily: rpc.gross_daily_issuance_near,
      mintedPerEpoch: ep.minted_per_epoch_near ?? null,
      prevMintedPerEpoch: numField(ep, "prev_minted_per_epoch_near"),
      epochHours: ep.epoch_duration_hours ?? null,
      epochsPerYear: ep.epochs_per_year ?? null,
      impliedRate: ep.implied_annual_inflation_rate ?? null,
      netBurnPerEpoch: ep.net_burn_per_epoch_near ?? null,
      measuredMinusNominalAnnual: numField(ep, "measured_minus_nominal_annual_near"),
      epochStartHeight: ep.epoch_start_height,
    },
    stateLock: {
      intentsLocked: intents?.storage_locked_near ?? null,
      intentsBytes: intents?.storage_bytes ?? null,
      intentsGrowthNearPerDay: intents?.growth_locked_near_per_day ?? null,
      intentsGrowthWindowDays: intents?.growth_window_days ?? null,
      totalLocked: rpc.total_state_locked_near,
      growthNearPerDay: rpc.measured_state_lock_growth_near_per_day ?? null,
      sinkCount: rpc.tracked_sinks.length,
      storageNearPerKb: rpc.storage_near_per_kb,
    },
    volume: {
      d30: numOf(vol, "30d"),
      d24h: numOf(vol, "24h"),
      allTime: numOf(vol, "allTimeUsd"),
      confidentialShare30d: numOf(vol, "confidential_share_30d"),
      confidential30d: numOf(vol, "confidential30d"),
      public30d: numOf(vol, "public30d"),
      drawdownFromRecord30d: numOf(vol, "drawdown_from_30d_record"),
      uniqueUsers7d: f.unique_users_7d ?? null,
      confidentialTvl: f.confidential_tvl_usd ?? null,
      confidentialTvlVerified: f.confidential_tvl_verified,
      confidentialShareStatus: strOf(vol, "confidential_share_status"),
      confidentialShareMeasured: boolOf(vol, "confidential_share_measured"),
      confidentialShareReported: numOf(vol, "confidential_share_30d_reported"),
      allTimeConfidential: numOf(vol, "confidential_allTimeUsd"),
    },
    fees: {
      gross30d: numOf(fees, "gross_fees_30d_usd"),
      net30d: numOf(fees, "net_revenue_30d_usd"),
      grossTakeBps: numOf(fees, "gross_take_bps"),
      netTakeBps: numOf(fees, "net_take_bps"),
      captureRatio: numOf(fees, "capture_ratio"),
      annualizedNet: numOf(fees, "annualized_net_revenue_30d_usd"),
      cumulativeFees: numOf(fees, "cumulative_fees_usd"),
    },
    price: { current: numOf(price, "current_usd"), fdv: numOf(price, "fdv_usd"), sigmaAnnual: numOf(vola, "annualized_sigma") },
    bench,
    concentration: {
      hhiExternal: f.hhi_external,
      nEffExternal: f.n_eff_external,
      hhiAll: f.hhi_all,
      hhiSolver: solver?.hhi_solver ?? null,
      hhiSolverCi90: pairOf(solver ? (solver as unknown as Record<string, unknown>).hhi_solver_ci90 : null),
      sampleSpanS: numField(solver, "sample_span_s"),
      nEffSolver: solver?.n_eff_solver ?? null,
      solverFills: numField(solver, "n_fills"),
      solverFillsAttributed: numField(solver, "n_fills_attributed"),
      uniqueSolvers: numField(solver, "unique_solvers"),
      cartelTriggerHhi: cartelParam ? cartelParam.value : null,
      aiAgentShare: f.ai_agent_share,
      bridgeShare: f.bridge_share,
      receiptsSampled: f.receipts_sampled,
      pagesFetched: f.pages_fetched,
      lifetimeReceipts: f.lifetime_receipts ?? null,
      topCallers: [...f.callers].sort((a, b) => b.share - a.share).slice(0, 3).map((c) => ({ account: c.account_id, cls: c.cls, share: c.share })),
    },
    supply: {
      sinks: { buyback: numOf(sinks, "buyback"), gasBurn: numOf(sinks, "gas_burn"), stateLock: numOf(sinks, "state_lock"), total: numOf(sinks, "total") },
      issuanceDaily: sp.current_daily_issuance_near,
      coverageRatio: sp.sink_coverage_ratio,
      breakeven: sp.breakeven_daily_volume_usd ?? {},
      breakevenAtCeiling: (asDict((sp as unknown as Record<string, unknown>).breakeven_daily_volume_usd_at_ceiling) as Record<string, number>) ?? {},
      // one arithmetic step: trailing-30d volume / 30
      dailyVolumeNow: numOf(vol, "30d") !== null ? (numOf(vol, "30d") as number) / 30 : null,
      deterministicCrossover,
      mcCrossoverProb,
      mcDeflationaryAtHorizon,
    },
    sotp: {
      nPaths: so.n_paths,
      horizonMonths: so.horizon_months,
      discountRate: so.discount_rate,
      fdv: so.fdv_percentiles,
      price: so.price_percentiles,
      fdvExMonetary: so.fdv_ex_monetary_percentiles,
      currentFdv: so.current_fdv_usd,
      currentFdvBasis: strField(cal, "current_fdv_basis"),
      priceSource: strField(cal, "price_source"),
      upsideP50Pct: so.upside_p50_pct,
      engines: so.engines.map((e) => ({ key: e.key, label: e.label, p50: e.p50, p10: e.p10, p90: e.p90, assumptionHeavy: e.assumption_heavy })),
      terminalMultipleUsed: numOf(cal, "terminal_multiple_used"),
      terminalMultipleRaw: numOf(cal, "terminal_multiple_raw"),
      terminalMultipleClipped: typeof cal.terminal_multiple_clipped === "boolean" ? (cal.terminal_multiple_clipped as boolean) : null,
      tauFloorBps: numOf(cal, "tau_floor_bps"),
      sigmaPriceAnnual: numOf(cal, "sigma_price_annual"),
      sigmaVolumeMonthly: numOf(cal, "sigma_volume_monthly"),
    },
    bear: {
      baseFdv: bc.base_fdv_p50,
      combinedWorstFdv: bc.combined_worst_fdv,
      combinedDrawdownPct: bc.combined_drawdown_pct,
      triggersBreached: numField(bc, "triggers_breached"),
      triggersEvaluated: numField(bc, "triggers_evaluated") ?? gradedCount,
      triggersUnevaluated: Array.isArray(bc.triggers_unevaluated)
        ? bc.triggers_unevaluated.filter((k): k is string => typeof k === "string")
        : scenarios.filter((s) => s.breached === null || s.evaluated === false).map((s) => s.key),
      valueBasis: strField(bc, "value_basis"),
      scenarios,
    },
    marketImplied: marketImpliedOf(snapAny.market_implied),
    sensitivity: sensitivityOf(snapAny.sensitivity),
    relativeValue: relativeValueOf(snapAny.relative_value),
    scorecard: snapshot.evidence_scorecard,
    assumptionsCount: snapshot.assumptions.length,
    warnings: snapshot.warnings,
    provenance: {
      records: numOf(prov, "records") ?? (manifest ? manifest.records.length : null),
      ok: numOf(prov, "ok"),
      failures: numOf(prov, "failures") ?? (manifest ? manifest.failures : null),
      bytes: numOf(prov, "bytes"),
      sources: (asDict(prov.sources) as Record<string, number>) ?? manifest?.sources ?? {},
      snapshotSha256: manifest?.snapshot_sha256 ?? null,
      manifestBlock: manifest?.block_height ?? null,
    },
  };
}

/** emerald for favourable sign, crimson for unfavourable, neutral at zero/null. */
export function signTone(v: number | null | undefined, higherIsBetter = true): "emerald" | "crimson" | "neutral" {
  if (v === null || v === undefined || !Number.isFinite(v) || v === 0) return "neutral";
  return (v > 0) === higherIsBetter ? "emerald" : "crimson";
}

export const ARCHETYPE_LABEL: Record<string, string> = {
  cross_vm: "Cross-VM, Ethereum USDC to Solana USDC",
  native_btc: "Native BTC, Ethereum USDC to BTC",
  evm_l2: "EVM L2, Base USDC to Arbitrum USDC",
  native_zec: "Native ZEC",
};

export const ARCHETYPE_SHORT: Record<string, string> = {
  cross_vm: "cross-VM",
  native_btc: "native BTC",
  evm_l2: "EVM L2",
  native_zec: "native ZEC",
};

export const VENUE_LABEL: Record<string, string> = {
  "1click": "1Click",
  oneclick: "1Click",
  relay: "Relay",
  lifi: "LI.FI",
  across: "Across",
};

export const REGIME_LABEL: Record<string, string> = {
  status_quo: "the current issuance cap",
  svrn_glidepath: "the SVRN glidepath",
};

/** Human names for the bear-case early-warning metrics; the raw key stays in the method note. */
export const METRIC_LABEL: Record<string, string> = {
  net_take_bps_30d: "Net take rate, 30 days",
  max_inflation_rate: "Protocol inflation cap",
  volume_30d_vs_record_30d: "30-day volume vs the 30-day record",
  hhi_solver: "Solver concentration (HHI)",
  hhi_external: "Caller concentration (HHI)",
  hhi_external_ex_ai_agent: "Caller concentration ex AI agents (HHI)",
};

export function metricLabel(key: string): string {
  if (METRIC_LABEL[key]) return METRIC_LABEL[key];
  const s = key.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Human names for the pipeline modules that prefix warning strings ("execution_bench: ..."). */
export const MODULE_LABEL: Record<string, string> = {
  near_rpc: "NEAR RPC",
  execution_bench: "Execution benchmark",
  intents_forensics: "Intents forensics",
  comps: "Peer comparables",
  supply_physics: "Supply physics",
  sotp: "Valuation",
  bear_case: "Bear case",
};

/** "5.49" -> "5.5×"; null-safe. Used for "n× today's volume". */
export function fmtTimes(v: number | null | undefined, decimals = 1): string {
  return v === null || v === undefined || !Number.isFinite(v) ? "n/a" : `${v.toFixed(decimals)}×`;
}

/** "+1.08 bps" with a true minus sign for negatives (typographic, not a hyphen). */
export function minus(s: string): string {
  return s.replace(/^-/, "\u2212");
}

const NUMBER_WORD = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];
/** 6 -> "Six" (sentence start); integers above ten stay numerals. */
export function numberWord(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "n/a";
  return Number.isInteger(n) && n >= 0 && n < NUMBER_WORD.length ? NUMBER_WORD[n] : n.toLocaleString("en-US");
}

/** Typographic comparators and minus signs for display: "<= -40.0%" -> "≤ −40.0%". */
export function typo(s: string): string {
  return s.replace(/<=/g, "\u2264").replace(/>=/g, "\u2265").replace(/(^|[\s(])-(?=\d)/g, "$1\u2212");
}

/** True when the confidential share is a registry assumption this run, not a measurement. */
export function confidentialIsAssumed(v: LandingData["volume"]): boolean {
  return v.confidentialShareMeasured === false || (v.confidentialShareStatus !== null && v.confidentialShareStatus !== "ok" && v.confidentialShareStatus !== "measured");
}

/** Format a market-implied solve value in its own unit ("161%/yr", "178 bps", "372×", "$175M/yr"). */
export function fmtSolveValue(unit: string, v: number | null): string {
  if (v === null || !Number.isFinite(v)) return "n/a";
  switch (unit) {
    case "ratio_yoy":
      return `${minus(`${v < 0 ? "-" : ""}${Math.abs(v * 100).toFixed(Math.abs(v) < 1 ? 1 : 0)}%`)} a year`;
    case "bps":
      return `${minus(v.toFixed(v < 10 ? 2 : 0))} bps`;
    case "x":
      return `${Math.round(v).toLocaleString("en-US")}×`;
    case "ratio_annual":
    case "ratio":
      return minus(`${(v * 100).toFixed(0)}%`);
    case "usd_per_year": {
      const a = Math.abs(v);
      const s = a >= 1e9 ? `$${(a / 1e9).toFixed(2)}B` : a >= 1e6 ? `$${(a / 1e6).toFixed(0)}M` : `$${Math.round(a).toLocaleString("en-US")}`;
      return `${v < 0 ? "\u2212" : ""}${s} a year`;
    }
    default:
      return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
}

/** "188 s" / "12 min" / "3.2 h" */
export function fmtSpan(s: number | null | undefined): string {
  if (s === null || s === undefined || !Number.isFinite(s)) return "n/a";
  if (s < 120) return `${Math.round(s)} s`;
  if (s < 7200) return `${Math.round(s / 60)} min`;
  return `${(s / 3600).toFixed(1)} h`;
}

/**
 * The requirement to headline: the market-implied solve for the input that moves value most
 * (sensitivity rank order), skipping unreachable solves and solves whose "evidence" is itself an
 * assumption. Falls back to solve order when the sensitivity block is missing.
 */
export function bindingSolve(d: LandingData): SolveView | null {
  const solves = (d.marketImplied?.solves ?? []).filter((s) => s.reachable && s.requiredValue !== null && !s.evidenceIsAssumption && s.evidenceValue !== null);
  if (!solves.length) return null;
  const order = (d.sensitivity?.rows ?? []).slice().sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99)).map((r) => r.param);
  for (const p of order) {
    const hit = solves.find((s) => s.param === p && s.withinEvidence === false);
    if (hit) return hit;
  }
  return solves.find((s) => s.withinEvidence === false) ?? solves[0];
}

export function solveByParam(d: LandingData, param: string): SolveView | null {
  return d.marketImplied?.solves.find((s) => s.param === param) ?? null;
}

/** "lowest of the 4 chains compared" / "rank 2 of 4, lowest first" */
export function rankPhrase(c: MultipleCoverage | null): string | null {
  if (!c || c.rank === null || c.n === null) return null;
  if (c.rank === 1) return `the lowest of the ${c.n} chains compared`;
  if (c.rank === c.n) return `the highest of the ${c.n} chains compared`;
  return `rank ${c.rank} of ${c.n}, lowest first`;
}

/** Evidence value in the solve's unit; growth rates carry an explicit sign ("+19.5% a year"). */
export function fmtEvidenceValue(s: SolveView): string {
  if (s.evidenceValue === null) return "n/a";
  if (s.unit === "ratio_yoy") {
    const v = s.evidenceValue;
    return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v * 100).toFixed(1)}% a year`;
  }
  return fmtSolveValue(s.unit, s.evidenceValue);
}
