/**
 * Client-side port of `quant/valuo/models/supply_physics.py` (pure helpers only).
 *
 * Every formula here is copied from the Python module docstring and evaluated in the same
 * operation order so that, on identical inputs, the two agree to floating-point precision
 * (`validatePort` recomputes the snapshot's own regimes and reports the max abs difference).
 *
 *   daily issuance            I(S, i)             = S x i / 365.25                (x f when realized)
 *   buyback sink              B(V, tau, alpha, P) = V x (tau / 1e4) x alpha / P
 *   net float change          dS                  = I - (B + G + L)
 *   breakeven volume          V*                  = max(0, I - G - L) x P / ((tau / 1e4) x alpha)
 *   glidepath, month m        i_m                 = i_0 + (i_T - i_0) x min(m, M_g) / M_g
 *   trajectory step           r_m = 1 + i_m x f x D / 365.25 ; S_m = S_0 x prod_{k<m} r_k ; E_m = S_m x (r_m - 1)
 *                             V_m = V_0 x (1 + g)^(m / 12) ; B_m = V_m x (tau / 1e4) x alpha / P_m x D
 *                             G_m = G x D ; L_m = L x D ; N_m = E_m - (B_m + G_m + L_m)
 *   crossover month           first 1-based m with N_m <= 0 ; cumulative: first m with sum_{k<=m} N_k <= 0
 *   nominal staking APR       i x (1 - t) / staked_ratio ; real = nominal - i ; accrual = B x 365.25 / S
 *   agent lock                agents x kb_per_agent x storage_near_per_kb
 *
 * No network, no React, no formatting: the components format the outputs via `format.ts`.
 */
import type { NearOnchainTruth, StakingYieldRow, SupplyPhysics, SupplyTrajectory } from "./types";

export const DAYS_PER_YEAR = 365.25;
/** 365.25 / 12 = 30.4375; the snapshot carries the value it used in `supply_physics.days_per_month`. */
export const DAYS_PER_MONTH = DAYS_PER_YEAR / 12.0;

export const REGIME_STATUS_QUO = "status_quo";
export const REGIME_SVRN_GLIDEPATH = "svrn_glidepath";
export const REGIME_CUSTOM_CAP = "custom_cap";
export type RegimeKind = typeof REGIME_STATUS_QUO | typeof REGIME_SVRN_GLIDEPATH | typeof REGIME_CUSTOM_CAP;
export const REGIME_KINDS: readonly RegimeKind[] = [REGIME_STATUS_QUO, REGIME_SVRN_GLIDEPATH, REGIME_CUSTOM_CAP];

// ============================================================================ pure helpers
/** Gross daily issuance `I = S x i / 365.25` (NEAR/day). */
export function dailyIssuanceNear(totalSupplyNear: number, annualRate: number): number {
  return (totalSupplyNear * annualRate) / DAYS_PER_YEAR;
}

/** Annual inflation rate in force at the start of each model month (length `months`). */
export function inflationPath(regime: RegimeKind, months: number, startRate: number, targetRate: number, glideMonths: number): number[] {
  if (!(months >= 1)) throw new Error("months must be >= 1");
  const path = new Array<number>(months);
  if (regime === REGIME_STATUS_QUO) {
    for (let m = 0; m < months; m++) path[m] = startRate;
  } else if (regime === REGIME_SVRN_GLIDEPATH) {
    if (!(glideMonths >= 1)) throw new Error("glideMonths must be >= 1");
    for (let m = 0; m < months; m++) {
      const frac = Math.min(m, glideMonths) / glideMonths;
      path[m] = startRate + (targetRate - startRate) * frac;
    }
  } else if (regime === REGIME_CUSTOM_CAP) {
    for (let m = 0; m < months; m++) path[m] = targetRate;
  } else {
    throw new Error(`unknown regime ${String(regime)}`);
  }
  return path;
}

export interface DailySinks {
  buyback: number;
  gas_burn: number;
  state_lock: number;
  total: number;
}

/** NEAR removed from float per day. `buyback = V x (tau / 1e4) x alpha / P`. */
export function dailySinksNear(volumeUsdDay: number, grossTakeBps: number, captureRatio: number, priceUsd: number, gasBurnNearDay: number, stateLockNearDay: number): DailySinks {
  if (!(priceUsd > 0)) throw new Error("priceUsd must be > 0");
  const buyback = (((volumeUsdDay * (grossTakeBps / 1e4)) * captureRatio) / priceUsd);
  return { buyback, gas_burn: gasBurnNearDay, state_lock: stateLockNearDay, total: buyback + gasBurnNearDay + stateLockNearDay };
}

/** `dS = I - sinks.total` (NEAR/day). Negative means the float shrinks. */
export function netFloatChangeNearDay(issuanceNearDay: number, sinks: DailySinks): number {
  return issuanceNearDay - sinks.total;
}

/**
 * Daily volume `V*` at which `dS = 0`. Returns null (instead of raising, as Python does) when the
 * buyback channel is closed (`tau x alpha <= 0`) or the price is not positive.
 */
export function breakevenDailyVolumeUsd(issuanceNearDay: number, gasBurn: number, stateLock: number, price: number, grossTakeBps: number, captureRatio: number): number | null {
  const take = (grossTakeBps / 1e4) * captureRatio;
  if (!(take > 0) || !(price > 0)) return null;
  const residual = Math.max(0.0, issuanceNearDay - gasBurn - stateLock);
  return (residual * price) / take;
}

export interface TrajectoryParams {
  total_supply_near: number;
  daily_volume_usd: number;
  gross_take_bps: number;
  capture_ratio: number;
  price_usd: number;
  gas_burn_near_day: number;
  state_lock_near_day: number;
  realization_factor?: number;
  volume_growth_yoy?: number;
  price_path?: number[] | null;
  /** defaults to DAYS_PER_MONTH; pass `supply_physics.days_per_month` from the snapshot */
  days_per_month?: number;
}

/** Monthly float accounting over `inflationPathAnnual.length` months (see module formulas). */
export function trajectory(regime: string, inflationPathAnnual: readonly number[], p: TrajectoryParams): SupplyTrajectory {
  const months = inflationPathAnnual.length;
  if (months < 1) throw new Error("inflationPathAnnual must have at least one month");
  const D = p.days_per_month ?? DAYS_PER_MONTH;
  const f = p.realization_factor ?? 1.0;
  const g = p.volume_growth_yoy ?? 0.0;
  const prices = p.price_path ?? null;
  if (prices && prices.length !== months) throw new Error("price_path length must equal the number of months");
  if (!(p.price_usd > 0) || (prices && prices.some((x) => !(x > 0)))) throw new Error("prices must be > 0");

  const r = new Array<number>(months);
  for (let m = 0; m < months; m++) r[m] = 1.0 + ((inflationPathAnnual[m] * f) * D) / DAYS_PER_YEAR;

  // supply_start = S_0 x concat([1], cumprod(r)[:-1]); the product is formed before scaling by S_0.
  const supplyStart = new Array<number>(months);
  let prod = 1.0;
  for (let m = 0; m < months; m++) {
    supplyStart[m] = p.total_supply_near * prod;
    prod = prod * r[m];
  }

  const issuance = new Array<number>(months);
  const buyback = new Array<number>(months);
  const gas = new Array<number>(months);
  const lock = new Array<number>(months);
  const net = new Array<number>(months);
  const volume = new Array<number>(months);
  const gasMonth = p.gas_burn_near_day * D;
  const lockMonth = p.state_lock_near_day * D;
  for (let m = 0; m < months; m++) {
    issuance[m] = supplyStart[m] * (r[m] - 1.0);
    volume[m] = p.daily_volume_usd * Math.pow(1.0 + g, m / 12.0);
    const price = prices ? prices[m] : p.price_usd;
    buyback[m] = (((volume[m] * (p.gross_take_bps / 1e4)) * p.capture_ratio) / price) * D;
    gas[m] = gasMonth;
    lock[m] = lockMonth;
    net[m] = issuance[m] - (buyback[m] + gas[m] + lock[m]);
  }

  const cumsum = (a: number[]): number[] => {
    const out = new Array<number>(a.length);
    let s = 0.0;
    for (let i = 0; i < a.length; i++) {
      s = s + a[i];
      out[i] = s;
    }
    return out;
  };
  const netCum = cumsum(net);
  let flowCross: number | null = null;
  let cumCross: number | null = null;
  for (let m = 0; m < months; m++) {
    if (flowCross === null && net[m] <= 0) flowCross = m + 1;
    if (cumCross === null && netCum[m] <= 0) cumCross = m + 1;
  }

  return {
    regime,
    months: Array.from({ length: months }, (_, i) => i + 1),
    gross_issuance_cum: cumsum(issuance),
    buyback_cum: cumsum(buyback),
    gas_burn_cum: cumsum(gas),
    state_lock_cum: cumsum(lock),
    net_float_change_cum: netCum,
    crossover_month: flowCross,
    daily_issuance_start: issuance[0] / D,
    daily_issuance_end: issuance[months - 1] / D,
    monthly_net_float_change: net,
    cumulative_crossover_month: cumCross,
    supply_end_near: supplyStart[months - 1] * r[months - 1],
    volume_growth_yoy: g,
    daily_volume_usd_start: volume[0],
    daily_volume_usd_end: volume[months - 1],
    realization_factor: f,
  };
}

/** One `staking_yield_table` row at a regime's terminal inflation rate. */
export function stakingYieldRow(regime: string, rate: number, treasuryShare: number, stakedSupplyRatio: number, totalSupplyNear: number, buybackNearPerDay: number): StakingYieldRow {
  if (!(stakedSupplyRatio > 0)) throw new Error("stakedSupplyRatio must be > 0");
  const accrual = (buybackNearPerDay * DAYS_PER_YEAR) / totalSupplyNear;
  const nominal = (rate * (1.0 - treasuryShare)) / stakedSupplyRatio;
  const real = nominal - rate;
  return {
    regime,
    inflation_rate: rate,
    nominal_staking_apr: nominal,
    real_staking_apr: real,
    buyback_accrual_apr: accrual,
    real_staking_apr_with_buyback: real + accrual,
    real_non_staker_apr: -rate + accrual,
    daily_issuance_near: dailyIssuanceNear(totalSupplyNear, rate),
  };
}

/** Permanent state-lock from agent vaults: `locked = agents x kb_per_agent x storage_near_per_kb`. */
export function agentLockNear(agents: number, kbPerAgent: number, storageNearPerKb: number): number {
  return agents * kbPerAgent * storageNearPerKb;
}

// ============================================================================ snapshot -> model inputs
/** The measured / labelled scalars the regime lab recomputes from (all read from the snapshot). */
export interface SupplyModelInputs {
  total_supply_near: number;
  current_max_inflation_rate: number;
  treasury_share: number;
  staked_supply_ratio: number;
  issuance_realization_factor: number;
  near_price_usd: number;
  daily_volume_usd: number;
  gross_take_bps: number;
  capture_ratio: number;
  gas_burn_near_per_day: number;
  state_lock_growth_near_per_day: number;
  svrn_target_inflation: number;
  svrn_glidepath_months: number;
  public_volume_growth_yoy: number;
  /** null when the execution benchmark produced no ceiling */
  competitive_fee_ceiling_bps: number | null;
  horizon_months: number;
  days_per_month: number;
  storage_near_per_kb: number | null;
}

const REQUIRED_INPUT_KEYS = [
  "total_supply_near",
  "current_max_inflation_rate",
  "treasury_share",
  "staked_supply_ratio",
  "issuance_realization_factor",
  "near_price_usd",
  "daily_volume_usd",
  "gross_take_bps",
  "capture_ratio",
  "gas_burn_near_per_day",
  "state_lock_growth_near_per_day",
  "svrn_target_inflation",
  "svrn_glidepath_months",
  "public_volume_growth_yoy",
] as const;

function finite(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/**
 * Pull the model inputs out of `supply_physics.inputs` (labelled Assumption rows). Returns the
 * list of missing keys instead of inventing defaults; the lab renders n/a + reason when any is absent.
 */
export function extractSupplyInputs(sp: SupplyPhysics | null | undefined, rpc: NearOnchainTruth | null | undefined): { inputs: SupplyModelInputs | null; missing: string[] } {
  const missing: string[] = [];
  const raw = sp?.inputs ?? {};
  const vals: Record<string, number> = {};
  for (const key of REQUIRED_INPUT_KEYS) {
    const v = raw[key]?.value;
    if (finite(v)) vals[key] = v;
    else missing.push(`supply_physics.inputs.${key}`);
  }
  const horizon = finite(sp?.horizon_months) ? (sp!.horizon_months as number) : sp?.regimes?.[0]?.inflation_path_annual?.length;
  if (!finite(horizon) || horizon < 1) missing.push("supply_physics.horizon_months");
  if (missing.length) return { inputs: null, missing };
  const ceiling = raw["competitive_fee_ceiling_bps"]?.value;
  return {
    inputs: {
      total_supply_near: vals.total_supply_near,
      current_max_inflation_rate: vals.current_max_inflation_rate,
      treasury_share: vals.treasury_share,
      staked_supply_ratio: vals.staked_supply_ratio,
      issuance_realization_factor: vals.issuance_realization_factor,
      near_price_usd: vals.near_price_usd,
      daily_volume_usd: vals.daily_volume_usd,
      gross_take_bps: vals.gross_take_bps,
      capture_ratio: vals.capture_ratio,
      gas_burn_near_per_day: vals.gas_burn_near_per_day,
      state_lock_growth_near_per_day: vals.state_lock_growth_near_per_day,
      svrn_target_inflation: vals.svrn_target_inflation,
      svrn_glidepath_months: Math.round(vals.svrn_glidepath_months),
      public_volume_growth_yoy: vals.public_volume_growth_yoy,
      competitive_fee_ceiling_bps: finite(ceiling) && ceiling > 0 ? ceiling : null,
      horizon_months: horizon as number,
      days_per_month: finite(sp?.days_per_month) ? (sp!.days_per_month as number) : DAYS_PER_MONTH,
      storage_near_per_kb: finite(rpc?.storage_near_per_kb) ? (rpc!.storage_near_per_kb as number) : null,
    },
    missing,
  };
}

// ============================================================================ regime runs
export interface RegimeRun {
  kind: RegimeKind;
  /** regime key as written in the snapshot / Python module */
  key: string;
  label: string;
  terminal_rate: number;
  inflation_path_annual: number[];
  trajectory: SupplyTrajectory;
  /** V* at the live gross take and capture ratio (terminal inflation rate); null if undefined */
  breakeven_daily_volume_usd: number | null;
  /** V* at the benchmark's competitive fee ceiling; null when no ceiling */
  breakeven_daily_volume_usd_at_ceiling: number | null;
  staking: StakingYieldRow;
  sinks_now: DailySinks;
  daily_issuance_now: number;
}

function pctLabel(rate: number): string {
  return `${(rate * 100).toFixed(2)}%`;
}

/** Same label strings `run_supply_physics` writes into `supply_physics.regimes[].label`. */
export function regimeLabel(kind: RegimeKind, inputs: SupplyModelInputs, customCap: number | null): string {
  const i0 = inputs.current_max_inflation_rate;
  switch (kind) {
    case REGIME_STATUS_QUO:
      return `Status quo (${pctLabel(i0)} max inflation, flat)`;
    case REGIME_SVRN_GLIDEPATH:
      return `SVRN glidepath (${pctLabel(i0)} -> ${pctLabel(inputs.svrn_target_inflation)} linear over ${inputs.svrn_glidepath_months} months, then flat)`;
    case REGIME_CUSTOM_CAP:
      return `Custom cap (${pctLabel(customCap ?? i0)} flat)`;
  }
}

/** Inflation path for a regime kind from the snapshot inputs (custom cap needs `customCap`). */
export function regimePath(kind: RegimeKind, inputs: SupplyModelInputs, customCap: number | null): { path: number[]; terminal: number } {
  const i0 = inputs.current_max_inflation_rate;
  const glide = inputs.svrn_glidepath_months;
  const M = inputs.horizon_months;
  if (kind === REGIME_STATUS_QUO) return { path: inflationPath(kind, M, i0, i0, glide), terminal: i0 };
  if (kind === REGIME_SVRN_GLIDEPATH) return { path: inflationPath(kind, M, i0, inputs.svrn_target_inflation, glide), terminal: inputs.svrn_target_inflation };
  const cap = customCap ?? i0;
  return { path: inflationPath(kind, M, i0, cap, glide), terminal: cap };
}

/**
 * Run one regime end to end (mirrors the per-regime block of `run_supply_physics`): path,
 * trajectory at `volumeGrowthYoy` (0 = the snapshot's `trajectories`, the labelled assumption = its
 * `growth_trajectories`), breakeven volumes and the staking row.
 */
export function runRegime(kind: RegimeKind, inputs: SupplyModelInputs, opts: { customCap?: number | null; volumeGrowthYoy?: number } = {}): RegimeRun {
  const customCap = opts.customCap ?? null;
  const g = opts.volumeGrowthYoy ?? 0.0;
  const { path, terminal } = regimePath(kind, inputs, customCap);
  const common: TrajectoryParams = {
    total_supply_near: inputs.total_supply_near,
    daily_volume_usd: inputs.daily_volume_usd,
    gross_take_bps: inputs.gross_take_bps,
    capture_ratio: inputs.capture_ratio,
    price_usd: inputs.near_price_usd,
    gas_burn_near_day: inputs.gas_burn_near_per_day,
    state_lock_near_day: inputs.state_lock_growth_near_per_day,
    realization_factor: inputs.issuance_realization_factor,
    volume_growth_yoy: g,
    days_per_month: inputs.days_per_month,
  };
  const traj = trajectory(kind, path, common);
  const issuanceTerminal = dailyIssuanceNear(inputs.total_supply_near, terminal) * inputs.issuance_realization_factor;
  const sinksNow = dailySinksNear(inputs.daily_volume_usd, inputs.gross_take_bps, inputs.capture_ratio, inputs.near_price_usd, inputs.gas_burn_near_per_day, inputs.state_lock_growth_near_per_day);
  const be = breakevenDailyVolumeUsd(issuanceTerminal, inputs.gas_burn_near_per_day, inputs.state_lock_growth_near_per_day, inputs.near_price_usd, inputs.gross_take_bps, inputs.capture_ratio);
  const beCeil =
    inputs.competitive_fee_ceiling_bps !== null
      ? breakevenDailyVolumeUsd(issuanceTerminal, inputs.gas_burn_near_per_day, inputs.state_lock_growth_near_per_day, inputs.near_price_usd, inputs.competitive_fee_ceiling_bps, inputs.capture_ratio)
      : null;
  const staking = stakingYieldRow(kind, terminal, inputs.treasury_share, inputs.staked_supply_ratio, inputs.total_supply_near, sinksNow.buyback);
  return {
    kind,
    key: kind,
    label: regimeLabel(kind, inputs, customCap),
    terminal_rate: terminal,
    inflation_path_annual: path,
    trajectory: traj,
    breakeven_daily_volume_usd: be,
    breakeven_daily_volume_usd_at_ceiling: beCeil,
    staking,
    sinks_now: sinksNow,
    daily_issuance_now: dailyIssuanceNear(inputs.total_supply_near, inputs.current_max_inflation_rate) * inputs.issuance_realization_factor,
  };
}

// ============================================================================ comparison helper
/** Element-wise max |a - b|; null when the arrays are empty or of unequal length. */
export function maxAbsDiff(a: readonly number[] | null | undefined, b: readonly number[] | null | undefined): number | null {
  if (!a || !b || a.length !== b.length || a.length === 0) return null;
  let worst = 0;
  for (let i = 0; i < a.length; i++) {
    const d = Math.abs(a[i] - b[i]);
    if (!Number.isFinite(d)) return Number.POSITIVE_INFINITY;
    if (d > worst) worst = d;
  }
  return worst;
}
