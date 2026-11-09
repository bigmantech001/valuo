import { maxAbsDiff, REGIME_CUSTOM_CAP, REGIME_KINDS, runRegime, type RegimeKind, type SupplyModelInputs } from "@/lib/supplyClient";
import type { Regime, SupplyPhysics, SupplyTrajectory } from "@/lib/types";

/**
 * Port verification: recompute every regime the snapshot carries with `lib/supplyClient.ts` and
 * compare with the Python output field by field. The trajectories are recomputed from the
 * recomputed inflation path (not the stored one), so a path error would surface in both numbers.
 */
export const TRAJECTORY_SERIES = ["gross_issuance_cum", "buyback_cum", "gas_burn_cum", "state_lock_cum", "net_float_change_cum", "monthly_net_float_change"] as const;
export type TrajectorySeriesKey = (typeof TRAJECTORY_SERIES)[number];

const STAKING_FIELDS = ["inflation_rate", "nominal_staking_apr", "real_staking_apr", "buyback_accrual_apr", "real_staking_apr_with_buyback", "real_non_staker_apr", "daily_issuance_near"] as const;

export interface PortCheck {
  regime: string;
  /** "trajectories" (flat volume) or "growth_trajectories" (labelled YoY growth) */
  table: "trajectories" | "growth_trajectories";
  /** max |TS - Python| over the inflation path */
  path_max_abs_diff: number | null;
  /** max |TS - Python| per series (NEAR) */
  series_max_abs_diff: Record<TrajectorySeriesKey, number | null>;
  /** worst of the series */
  max_abs_diff: number | null;
  crossover_match: boolean;
  cumulative_crossover_match: boolean;
  breakeven_abs_diff: number | null;
  breakeven_at_ceiling_abs_diff: number | null;
  staking_max_abs_diff: number | null;
  /** largest magnitude among the compared Python values (for a relative reading) */
  reference_scale: number;
  ok: boolean;
}

/** Tolerance for "ok": 1e-6 NEAR on cumulative series of ~1e8 NEAR (well below display precision). */
export const PORT_TOLERANCE_NEAR = 1e-6;

function finite(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

export function validatePort(sp: SupplyPhysics | null | undefined, inputs: SupplyModelInputs): PortCheck[] {
  if (!sp) return [];
  const out: PortCheck[] = [];
  const tables: Array<["trajectories" | "growth_trajectories", SupplyTrajectory[] | undefined, number]> = [
    ["trajectories", sp.trajectories, 0.0],
    ["growth_trajectories", sp.growth_trajectories, inputs.public_volume_growth_yoy],
  ];
  const regimes: Regime[] = Array.isArray(sp.regimes) ? sp.regimes : [];
  const be: Record<string, number | undefined> = sp.breakeven_daily_volume_usd ?? {};
  const beCeil: Record<string, number | undefined> = sp.breakeven_daily_volume_usd_at_ceiling ?? {};
  for (const [table, list, growth] of tables) {
    if (!Array.isArray(list)) continue;
    for (const py of list) {
      const kind = py.regime as RegimeKind;
      if (!REGIME_KINDS.includes(kind) || kind === REGIME_CUSTOM_CAP) continue;
      const run = runRegime(kind, inputs, { volumeGrowthYoy: growth });
      const pyPath = regimes.find((r) => r.key === py.regime)?.inflation_path_annual ?? null;
      const series = {} as Record<TrajectorySeriesKey, number | null>;
      let worst = 0;
      let scale = 0;
      for (const k of TRAJECTORY_SERIES) {
        const d = maxAbsDiff(run.trajectory[k], py[k]);
        series[k] = d;
        if (d === null) worst = Number.POSITIVE_INFINITY;
        else if (d > worst) worst = d;
        for (const v of py[k] ?? []) scale = Math.max(scale, Math.abs(v));
      }
      const pyBe = be[py.regime];
      const pyBeCeil = beCeil[py.regime];
      const pyStake = Array.isArray(sp.staking_yield_table) ? sp.staking_yield_table.find((r) => r.regime === py.regime) : undefined;
      const stakeDiff = pyStake ? Math.max(...STAKING_FIELDS.map((k) => Math.abs(run.staking[k] - pyStake[k]))) : null;
      const pathDiff = maxAbsDiff(run.inflation_path_annual, pyPath);
      const beDiff = finite(pyBe) && run.breakeven_daily_volume_usd !== null ? Math.abs(run.breakeven_daily_volume_usd - pyBe) : null;
      const beCeilDiff = finite(pyBeCeil) && run.breakeven_daily_volume_usd_at_ceiling !== null ? Math.abs(run.breakeven_daily_volume_usd_at_ceiling - pyBeCeil) : null;
      const crossMatch = (run.trajectory.crossover_month ?? null) === (py.crossover_month ?? null);
      const cumMatch = (run.trajectory.cumulative_crossover_month ?? null) === (py.cumulative_crossover_month ?? null);
      // Volume growth uses pow(); allow a relative 1e-9 slack there (libm vs V8 may differ in the last ulp).
      const tol = table === "growth_trajectories" ? Math.max(PORT_TOLERANCE_NEAR, scale * 1e-9) : PORT_TOLERANCE_NEAR;
      out.push({
        regime: py.regime,
        table,
        path_max_abs_diff: pathDiff,
        series_max_abs_diff: series,
        max_abs_diff: Number.isFinite(worst) ? worst : null,
        crossover_match: crossMatch,
        cumulative_crossover_match: cumMatch,
        breakeven_abs_diff: beDiff,
        breakeven_at_ceiling_abs_diff: beCeilDiff,
        staking_max_abs_diff: stakeDiff,
        reference_scale: scale,
        ok:
          Number.isFinite(worst) &&
          worst <= tol &&
          (pathDiff ?? 0) <= 1e-15 &&
          crossMatch &&
          cumMatch &&
          (beDiff ?? 0) <= 1e-3 &&
          (beCeilDiff ?? 0) <= 1e-3 &&
          (stakeDiff ?? 0) <= 1e-9,
      });
    }
  }
  return out;
}
