/**
 * Client-side mirror of `quant/valuo/models/sotp_valuation.py::deterministic_sotp`.
 *
 * Pure arithmetic, no React, no `@/` value imports, so Node can execute it directly
 * (`node --experimental-strip-types`) to check the port against the snapshot. Formulas follow the
 * Python docstring verbatim (month index t = 1..H, D = 365.25/12, df_t = (1 + r)^(-t/12)):
 *
 *   V_pub_t   = v_pub x (1 + g_pub)^t                       V_conf_t  = v_conf x (1 + g_conf)^t
 *   tau_pub_t = floor + (tau_pub - floor) x (1 - lambda_pub)^t   (same for tau_conf with lambda_conf)
 *   P_t       = price x (1 + d)^(t/12)                      a_t = V_pub_t / v_pub (1 if v_pub == 0)
 *   rev_pub_t = V_pub_t x tau_pub_t / 1e4 x D x alpha       rev_conf_t = V_conf_t x tau_conf_t / 1e4 x D x alpha
 *   gas_near_t= gas_burn_usd_day / price x D x a_t          gas_usd_t = gas_near_t x P_t
 *   lock_t    = state_lock_near_day x D x a_t               buyback_t = (rev_pub_t + rev_conf_t) / P_t
 *   iss_t     = S_{t-1} x i_t / 12, S_t = S_{t-1} + iss_t   dF_t = iss_t - buyback_t - gas_near_t - lock_t
 *   k = min(12, H); yr3(x) = sum(x_{H-k+1..H}) x 12 / k
 *   E1 = sum rev_pub_t df_t + yr3(rev_pub) x M x df_H
 *   E2 = sum rev_conf_t df_t + yr3(rev_conf) x M x h x df_H
 *   E3 = sum gas_usd_t df_t + yr3(gas_usd) x M x df_H + sum lock_t x P_t x df_t
 *   fdv_total = E1 + E2 + E3; implied_price = fdv_total / (supply_at_horizon or S_H)
 *   crossover_month = min{t : dF_t <= 0} or null; running_fdv_t = M x 12 x (rev_pub_t + h x rev_conf_t + gas_usd_t)
 *
 * Take-rate basis: tau_* are GROSS take-rates (fees / volume, bps); alpha is the share of gross fees
 * swept to NEAR revenue wallets; holder revenue = V x tau x alpha.
 */
import type { Assumption, NearOnchainTruth, RegimeKey, SensitivityHeatmap, SotpValuation } from "./types";

/**
 * The part of the snapshot the deterministic model reads. A full `Snapshot` satisfies it; the
 * client slider panel receives only this slice so the RSC payload stays small.
 */
export type SotpSnapshotSlice = {
  sotp: SotpValuation;
  near_rpc: Pick<NearOnchainTruth, "total_supply_near">;
  assumptions?: Array<Pick<Assumption, "key" | "value">> | null;
  intents_forensics?: { fees?: { take_rate_window_days?: number } | null } | null;
};

export const DAYS_PER_MONTH = 365.25 / 12;
export const REGIME_STATUS_QUO: RegimeKey = "status_quo";
export const REGIME_GLIDEPATH: RegimeKey = "svrn_glidepath";

/** `deterministic_sotp` input dict. Optional aliases are the names bear_case.py writes. */
export interface SotpInputs {
  horizon_months: number;
  v_pub_usd_day?: number | null;
  v_pub_daily_usd?: number | null;
  v_conf_usd_day?: number | null;
  v_conf_daily_usd?: number | null;
  tau_pub_bps: number;
  tau_conf_bps: number;
  alpha_capture: number;
  discount_rate: number;
  terminal_multiple: number;
  conf_haircut: number;
  gas_burn_usd_day: number;
  state_lock_near_day: number;
  price_usd: number;
  total_supply: number;
  /** H effective annual rates, or a scalar for a flat regime */
  issuance_rate_path?: number[] | number | null;
  growth_monthly_pub: number;
  growth_monthly_conf: number;
  lambda_pub?: number | null;
  fee_compression_lambda_monthly?: number | null;
  lambda_conf: number;
  tau_floor_bps: number;
  price_drift_annual?: number | null;
  /** supply_physics float at H (implied-price denominator); default = internal S_H */
  supply_at_horizon?: number | null;
  /** non-null -> rebuild the issuance path from max_inflation_rate / svrn_glidepath_months / issuance_scale */
  svrn_target_inflation?: number | null;
  max_inflation_rate?: number | null;
  svrn_glidepath_months?: number | null;
  issuance_scale?: number | null;
}

/** `deterministic_sotp` output dict (same keys as the Python return value). */
export interface SotpResult {
  engine_clearinghouse: number;
  engine_confidential: number;
  engine_monetary: number;
  fdv_total: number;
  fdv_ex_monetary: number;
  implied_price: number;
  net_deflation: boolean;
  crossover_month: number | null;
  monthly_holder_revenue: number[];
  monthly_net_float_change_near: number[];
  monthly_running_fdv: number[];
  monthly_tau_pub_bps: number[];
  monthly_tau_conf_bps: number[];
  pv_public: number;
  tv_public: number;
  pv_confidential: number;
  tv_confidential: number;
  pv_gas_burn: number;
  tv_gas_burn: number;
  pv_state_lock: number;
  cum_holder_revenue_usd: number;
  cum_buyback_near: number;
  cum_issuance_near: number;
  net_float_change_cum_near: number;
  supply_at_horizon_internal: number;
  supply_at_horizon_used: number;
  supply_at_horizon_adjustment_near: number;
  supply_at_horizon_near: number;
  issuance_rate_path_used: number[];
  horizon_months: number;
  days_per_month: number;
}

/** Finite number guard (null / undefined / NaN are "not present" and render as n/a). */
export function present(v: number | null | undefined): v is number {
  return v !== null && v !== undefined && Number.isFinite(v);
}

function firstOf(label: string, ...vals: Array<number | null | undefined>): number {
  for (const v of vals) if (v !== null && v !== undefined) return v;
  throw new Error(`deterministic_sotp: missing input ${label}`);
}

function sum(a: ArrayLike<number>, from = 0, to = a.length): number {
  let s = 0;
  for (let i = from; i < to; i++) s += a[i];
  return s;
}

/** tau_t = floor + (tau_0 - floor) x (1 - lambda)^t, t = 1..H. */
export function tauPath(tau0: number, floor: number, lam: number, horizon: number): number[] {
  return Array.from({ length: horizon }, (_, i) => floor + (tau0 - floor) * (1 - lam) ** (i + 1));
}

/** Effective annual inflation per month (length H); see `_issuance_path` in the Python module. */
export function issuancePath(inputs: SotpInputs, horizon: number): number[] {
  const target = inputs.svrn_target_inflation;
  if (target !== null && target !== undefined) {
    const i0 = firstOf("max_inflation_rate", inputs.max_inflation_rate);
    const g = Math.max(1, firstOf("svrn_glidepath_months", inputs.svrn_glidepath_months));
    const scale = inputs.issuance_scale || 1;
    return Array.from({ length: horizon }, (_, i) => (i0 + (target - i0) * (Math.min(i, g) / g)) * scale);
  }
  const p = inputs.issuance_rate_path;
  if (p === null || p === undefined) throw new Error("deterministic_sotp: missing input issuance_rate_path");
  if (typeof p === "number") return new Array<number>(horizon).fill(p);
  if (p.length !== horizon) throw new Error(`issuance_rate_path must have length ${horizon}, got ${p.length}`);
  return p.slice();
}

/** iss_t = S_{t-1} x i_t / 12 with S_t = S_{t-1} + iss_t (identical to supply_physics.trajectory). */
export function compoundIssuance(annualRates: number[], totalSupply: number): number[] {
  const out = new Array<number>(annualRates.length);
  let prod = 1;
  for (let i = 0; i < annualRates.length; i++) {
    const r = 1 + annualRates[i] / 12;
    out[i] = totalSupply * prod * (r - 1);
    prod *= r;
  }
  return out;
}

/** Deterministic three-engine SOTP at fixed inputs. Verbatim port of the Python function. */
export function deterministicSotp(inputs: SotpInputs): SotpResult {
  const H = Math.trunc(inputs.horizon_months);
  if (H < 1) throw new Error("horizon_months must be >= 1");
  const path = issuancePath(inputs, H);
  const vPub0 = firstOf("v_pub_usd_day", inputs.v_pub_usd_day, inputs.v_pub_daily_usd);
  const vConf0 = firstOf("v_conf_usd_day", inputs.v_conf_usd_day, inputs.v_conf_daily_usd);
  const price0 = inputs.price_usd;
  if (!(price0 > 0)) throw new Error("price_usd must be > 0");
  const totalSupply = inputs.total_supply;
  const gPub = inputs.growth_monthly_pub;
  const gConf = inputs.growth_monthly_conf;
  const drift = inputs.price_drift_annual || 0;
  const floor = inputs.tau_floor_bps;
  const lambdaPub = firstOf("lambda_pub", inputs.lambda_pub, inputs.fee_compression_lambda_monthly);
  const tauPub = tauPath(inputs.tau_pub_bps, floor, lambdaPub, H);
  const tauConf = tauPath(inputs.tau_conf_bps, floor, inputs.lambda_conf, H);
  const alpha = inputs.alpha_capture;
  const M = inputs.terminal_multiple;
  const h = inputs.conf_haircut;
  const gasNearDay0 = inputs.gas_burn_usd_day / price0;
  const lockNearDay0 = inputs.state_lock_near_day;
  const issuance = compoundIssuance(path, totalSupply);

  const revPub = new Array<number>(H);
  const revConf = new Array<number>(H);
  const gasNear = new Array<number>(H);
  const gasUsd = new Array<number>(H);
  const lockNear = new Array<number>(H);
  const buybackNear = new Array<number>(H);
  const netFloat = new Array<number>(H);
  const df = new Array<number>(H);
  const runningFdv = new Array<number>(H);
  const price = new Array<number>(H);
  for (let i = 0; i < H; i++) {
    const t = i + 1;
    df[i] = (1 + inputs.discount_rate) ** (-t / 12);
    const vPub = vPub0 * (1 + gPub) ** t;
    const vConf = vConf0 * (1 + gConf) ** t;
    price[i] = price0 * (1 + drift) ** (t / 12);
    const activity = vPub0 > 0 ? vPub / vPub0 : 1;
    revPub[i] = vPub * (tauPub[i] / 1e4) * DAYS_PER_MONTH * alpha;
    revConf[i] = vConf * (tauConf[i] / 1e4) * DAYS_PER_MONTH * alpha;
    gasNear[i] = gasNearDay0 * DAYS_PER_MONTH * activity;
    gasUsd[i] = gasNear[i] * price[i];
    lockNear[i] = lockNearDay0 * DAYS_PER_MONTH * activity;
    buybackNear[i] = (revPub[i] + revConf[i]) / price[i];
    netFloat[i] = issuance[i] - buybackNear[i] - gasNear[i] - lockNear[i];
    runningFdv[i] = M * 12 * (revPub[i] + h * revConf[i] + gasUsd[i]);
  }

  const k = Math.min(12, H);
  const annualizer = 12 / k;
  const dfH = df[H - 1];
  const tvPub = sum(revPub, H - k) * annualizer * M;
  const tvConf = sum(revConf, H - k) * annualizer * M * h;
  const tvGas = sum(gasUsd, H - k) * annualizer * M;
  let pvPub = 0;
  let pvConf = 0;
  let pvGas = 0;
  let pvLock = 0;
  for (let i = 0; i < H; i++) {
    pvPub += revPub[i] * df[i];
    pvConf += revConf[i] * df[i];
    pvGas += gasUsd[i] * df[i];
    pvLock += lockNear[i] * price[i] * df[i];
  }
  const e1 = pvPub + tvPub * dfH;
  const e2 = pvConf + tvConf * dfH;
  const e3 = pvGas + tvGas * dfH + pvLock;
  const fdv = e1 + e2 + e3;

  let crossover: number | null = null;
  for (let i = 0; i < H; i++) {
    if (netFloat[i] <= 0) {
      crossover = i + 1;
      break;
    }
  }
  const netFloatCum = sum(netFloat);
  const supplyInternal = totalSupply + netFloatCum;
  const override = inputs.supply_at_horizon;
  let adjustment = 0;
  if (present(override) && inputs.svrn_target_inflation !== null && inputs.svrn_target_inflation !== undefined && inputs.issuance_rate_path !== null && inputs.issuance_rate_path !== undefined) {
    const explicit = typeof inputs.issuance_rate_path === "number" ? new Array<number>(H).fill(inputs.issuance_rate_path) : inputs.issuance_rate_path;
    if (explicit.length === path.length) adjustment = sum(issuance) - sum(compoundIssuance(explicit, totalSupply));
  }
  const supplyH = present(override) ? override + adjustment : supplyInternal;

  return {
    engine_clearinghouse: e1,
    engine_confidential: e2,
    engine_monetary: e3,
    fdv_total: fdv,
    fdv_ex_monetary: e1 + e2,
    implied_price: supplyH > 0 ? fdv / supplyH : NaN,
    net_deflation: crossover !== null,
    crossover_month: crossover,
    monthly_holder_revenue: revPub.map((v, i) => v + revConf[i]),
    monthly_net_float_change_near: netFloat,
    monthly_running_fdv: runningFdv,
    monthly_tau_pub_bps: tauPub,
    monthly_tau_conf_bps: tauConf,
    pv_public: pvPub,
    tv_public: tvPub,
    pv_confidential: pvConf,
    tv_confidential: tvConf,
    pv_gas_burn: pvGas,
    tv_gas_burn: tvGas,
    pv_state_lock: pvLock,
    cum_holder_revenue_usd: sum(revPub) + sum(revConf),
    cum_buyback_near: sum(buybackNear),
    cum_issuance_near: sum(issuance),
    net_float_change_cum_near: netFloatCum,
    supply_at_horizon_internal: supplyInternal,
    supply_at_horizon_used: supplyH,
    supply_at_horizon_adjustment_near: adjustment,
    supply_at_horizon_near: supplyH,
    issuance_rate_path_used: path,
    horizon_months: H,
    days_per_month: DAYS_PER_MONTH,
  };
}

// --------------------------------------------------------------------------- snapshot -> inputs

export interface BaseInputsResult {
  inputs: SotpInputs | null;
  /** calibration keys that were null/absent; non-empty => inputs is null */
  missing: string[];
  /** days in the take-rate window the daily volumes were derived from */
  window_days: number;
}

/**
 * Rebuild the `build_inputs` dict the Python run used from `sotp.calibration` (+ `near_rpc.total_supply_near`,
 * `sotp.discount_rate`, `sotp.inputs.*`). `calibration.deterministic_base` stores only the outputs, so the
 * inputs come from the calibration fields that record each measured / derived parameter.
 */
export function baseInputsFromSnapshot(snapshot: SotpSnapshotSlice, regime: RegimeKey = REGIME_GLIDEPATH): BaseInputsResult {
  const sotp = snapshot.sotp;
  const cal = sotp?.calibration;
  const missing: string[] = [];
  const need = (label: string, v: number | null | undefined): number => {
    if (!present(v)) {
      missing.push(label);
      return NaN;
    }
    return v;
  };
  if (!cal) return { inputs: null, missing: ["sotp.calibration"], window_days: 30 };
  const windowDays = (cal.take_rate_window_days as number | undefined) ?? snapshot.intents_forensics?.fees?.take_rate_window_days ?? 30;
  const paths = cal.regime_inflation_paths_annual ?? ({} as Record<string, number[]>);
  const regimePath = paths[regime];
  if (!Array.isArray(regimePath) || regimePath.length === 0) missing.push(`sotp.calibration.regime_inflation_paths_annual.${regime}`);
  const scale = need("sotp.calibration.issuance_scale_measured_over_path", cal.issuance_scale_measured_over_path);
  const price = need("sotp.calibration.price_usd", cal.price_usd);
  const inputs: SotpInputs = {
    horizon_months: need("sotp.horizon_months", sotp.horizon_months),
    v_pub_usd_day: need("sotp.calibration.v_pub_30d_usd", cal.v_pub_30d_usd) / windowDays,
    v_conf_usd_day: need("sotp.calibration.v_conf_30d_usd", cal.v_conf_30d_usd) / windowDays,
    tau_pub_bps: need("sotp.calibration.tau_pub_start_bps", cal.tau_pub_start_bps),
    tau_conf_bps: need("sotp.calibration.tau_conf_start_bps", cal.tau_conf_start_bps),
    alpha_capture: need("sotp.calibration.alpha_capture", cal.alpha_capture),
    discount_rate: need("sotp.discount_rate", sotp.discount_rate),
    terminal_multiple: need("sotp.calibration.terminal_multiple_used", cal.terminal_multiple_used),
    conf_haircut: need("sotp.inputs.confidential_multiple_haircut.value", sotp.inputs?.confidential_multiple_haircut?.value),
    gas_burn_usd_day: need("sotp.calibration.gas_burn_near_day", cal.gas_burn_near_day) * price,
    state_lock_near_day: need("sotp.calibration.state_lock_near_day", cal.state_lock_near_day),
    price_usd: price,
    total_supply: need("near_rpc.total_supply_near", snapshot.near_rpc?.total_supply_near),
    issuance_rate_path: Array.isArray(regimePath) ? regimePath.map((p) => p * scale) : null,
    growth_monthly_pub: need("sotp.calibration.growth_monthly_pub", cal.growth_monthly_pub),
    growth_monthly_conf: need("sotp.calibration.growth_monthly_conf", cal.growth_monthly_conf),
    lambda_pub: need("sotp.calibration.lambda_pub_monthly", cal.lambda_pub_monthly),
    lambda_conf: need("sotp.calibration.lambda_conf_monthly", cal.lambda_conf_monthly),
    tau_floor_bps: need("sotp.calibration.tau_floor_bps", cal.tau_floor_bps),
    price_drift_annual: sotp.inputs?.near_price_drift_annual?.value ?? 0,
    supply_at_horizon: cal.supply_at_horizon_by_regime?.[regime] ?? null,
    svrn_target_inflation: null,
    max_inflation_rate: Array.isArray(paths[REGIME_STATUS_QUO]) ? paths[REGIME_STATUS_QUO][0] : null,
    svrn_glidepath_months: snapshot.assumptions?.find((a) => a.key === "svrn_glidepath_months")?.value ?? null,
    issuance_scale: present(scale) ? scale : null,
  };
  return { inputs: missing.length ? null : inputs, missing, window_days: windowDays };
}

/** Inputs for one sensitivity cell exactly as `_heatmap` builds them (alpha folded into the net take). */
export function heatmapCellInputs(base: SotpInputs, dailyVolumeUsd: number, netTakeBps: number, confidentialShare: number, glidepathPath: number[] | number | null | undefined): SotpInputs {
  return {
    ...base,
    v_pub_usd_day: dailyVolumeUsd * (1 - confidentialShare),
    v_conf_usd_day: dailyVolumeUsd * confidentialShare,
    tau_pub_bps: netTakeBps,
    tau_conf_bps: netTakeBps,
    alpha_capture: 1,
    tau_floor_bps: netTakeBps,
    growth_monthly_pub: 0,
    growth_monthly_conf: 0,
    lambda_pub: 0,
    lambda_conf: 0,
    price_drift_annual: 0,
    issuance_rate_path: glidepathPath ?? base.issuance_rate_path,
  };
}

// --------------------------------------------------------------------------- port verification

export interface PortCheck {
  /** every base scalar and heatmap value within tolerance and the crossover month agrees */
  ok: boolean;
  /** every stored heatmap net_deflation flag agrees with the recomputed one */
  flags_ok: boolean;
  /** max relative error over the base scalars and every heatmap cell */
  max_rel_error: number;
  base_rel_errors: Record<string, number>;
  crossover_match: boolean;
  heatmap_max_rel_error: number;
  heatmap_flag_mismatches: number;
  heatmap_cells: number;
  notes: string[];
}

function relErr(a: number, b: number): number {
  if (!Number.isFinite(a) || !Number.isFinite(b)) return Number.isNaN(a) && Number.isNaN(b) ? 0 : Infinity;
  const d = Math.abs(a - b);
  return d === 0 ? 0 : d / Math.max(Math.abs(b), 1e-300);
}

/** Recompute `deterministic_base` and every `sensitivity_heatmap` cell; report the worst relative error. */
export function verifyPort(snapshot: SotpSnapshotSlice, tolerance = 1e-6): PortCheck {
  const notes: string[] = [];
  const { inputs, missing } = baseInputsFromSnapshot(snapshot);
  if (!inputs) return { ok: false, flags_ok: false, max_rel_error: Infinity, base_rel_errors: {}, crossover_match: false, heatmap_max_rel_error: Infinity, heatmap_flag_mismatches: 0, heatmap_cells: 0, notes: [`cannot rebuild inputs: ${missing.join(", ")}`] };
  const base = snapshot.sotp.calibration.deterministic_base;
  const res = deterministicSotp(inputs);
  const pairs: Array<[string, number, number]> = [
    ["fdv_total", res.fdv_total, base.fdv_total],
    ["fdv_ex_monetary", res.fdv_ex_monetary, base.fdv_ex_monetary],
    ["engine_clearinghouse", res.engine_clearinghouse, base.engine_clearinghouse],
    ["engine_confidential", res.engine_confidential, base.engine_confidential],
    ["engine_monetary", res.engine_monetary, base.engine_monetary],
    ["implied_price", res.implied_price, base.implied_price],
    ["cum_holder_revenue_usd", res.cum_holder_revenue_usd, base.cum_holder_revenue_usd],
  ];
  const baseErr: Record<string, number> = {};
  let maxErr = 0;
  for (const [k, a, b] of pairs) {
    baseErr[k] = relErr(a, b);
    maxErr = Math.max(maxErr, baseErr[k]);
  }
  const crossoverMatch = (res.crossover_month ?? null) === (base.crossover_month ?? null);
  if (!crossoverMatch) notes.push(`crossover_month ${String(res.crossover_month)} != base ${String(base.crossover_month)}`);

  const hm: SensitivityHeatmap | undefined = snapshot.sotp.sensitivity_heatmap;
  let hmErr = 0;
  let flagMismatch = 0;
  let cells = 0;
  if (hm && Array.isArray(hm.x) && Array.isArray(hm.y)) {
    const glide = snapshot.sotp.calibration.regime_inflation_paths_annual?.[REGIME_GLIDEPATH];
    const scale = snapshot.sotp.calibration.issuance_scale_measured_over_path;
    const glidePath = Array.isArray(glide) ? glide.map((p) => p * scale) : inputs.issuance_rate_path;
    hm.y.forEach((bps, ri) => {
      hm.x.forEach((vol, ci) => {
        const cell = deterministicSotp(heatmapCellInputs(inputs, vol, bps, hm.confidential_share_used, glidePath));
        const want = hm.fdv_p50?.[ri]?.[ci];
        if (present(want)) {
          hmErr = Math.max(hmErr, relErr(cell.fdv_total, want));
          cells++;
        }
        if (hm.net_deflation?.[ri]?.[ci] !== undefined && hm.net_deflation[ri][ci] !== cell.net_deflation) flagMismatch++;
      });
    });
  } else notes.push("sensitivity_heatmap absent; heatmap check skipped");
  if (flagMismatch > 0) notes.push(`${flagMismatch} stored net_deflation flag(s) differ from the recomputed crossover test (the FDV values agree; re-run reproduce to refresh the heatmap)`);
  const worst = Math.max(maxErr, hmErr);
  return { ok: worst <= tolerance && crossoverMatch, flags_ok: flagMismatch === 0, max_rel_error: worst, base_rel_errors: baseErr, crossover_match: crossoverMatch, heatmap_max_rel_error: hmErr, heatmap_flag_mismatches: flagMismatch, heatmap_cells: cells, notes };
}
