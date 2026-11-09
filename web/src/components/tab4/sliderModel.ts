/**
 * Slider state -> `deterministic_sotp` inputs, mirroring the transformations `build_inputs` performs in
 * quant/valuo/models/sotp_valuation.py (monthly growth from YoY, odds-ratio confidential growth, the
 * tau floor rule) plus two helpers for the heatmap operating point. Pure functions, no React.
 */
import { REGIME_GLIDEPATH, baseInputsFromSnapshot, present, type BaseInputsResult, type SotpInputs, type SotpSnapshotSlice } from "@/lib/quantClient";
import type { RegimeKey, SensitivityHeatmap } from "@/lib/types";

export interface SliderState {
  /** public volume growth, YoY ratio (0.3 = +30%) */
  growth_yoy: number;
  /** public GROSS take at t = 0, bps of volume */
  tau_pub_bps: number;
  /** confidential share of volume the expected (deterministic) path drifts to by H */
  conf_share_target: number;
  /** confidential GROSS take at t = 0, bps */
  tau_conf_bps: number;
  /** alpha: share of gross fees swept to buybacks */
  alpha_capture: number;
  regime: RegimeKey;
}

/** g_monthly = (1 + g_yoy)^(1/12) - 1 (build_inputs). */
export function monthlyFromYoy(g: number): number {
  return (1 + g) ** (1 / 12) - 1;
}

export function yoyFromMonthly(gm: number): number {
  return (1 + gm) ** 12 - 1;
}

/** Expected-path confidential growth: the share moves linearly to the target, so odds scale by odds_H / odds_0 (build_inputs). */
export function confidentialGrowth(gPub: number, share0: number, shareTarget: number, horizon: number): number {
  const s0 = share0;
  const st = Math.min(Math.max(shareTarget, 0), 0.99);
  if (!(s0 > 0 && s0 < 1)) return gPub;
  const odds0 = s0 / (1 - s0);
  const oddsH = st / (1 - st);
  return ((1 + gPub) ** horizon * (oddsH / odds0)) ** (1 / horizon) - 1;
}

/** tau_pub_0 that makes month-0 modelled fees equal the measured window fees (build_inputs reconciliation). */
export function reconciledTauPub(grossFeesWindowUsd: number, vConfWindowUsd: number, tauConfBps: number, vPubWindowUsd: number): number | null {
  if (!(vPubWindowUsd > 0)) return null;
  return ((grossFeesWindowUsd - (vConfWindowUsd * tauConfBps) / 1e4) / vPubWindowUsd) * 1e4;
}

/** tau_floor = max(hard floor, min(tau_pub_0, cross-VM headroom)); the stored floor when headroom is null (`_tau_floor`). */
export function tauFloorFor(tauPub0: number, hardFloorBps: number | null | undefined, headroomCrossVmBps: number | null | undefined, storedFloorBps: number): number {
  if (!present(headroomCrossVmBps)) return storedFloorBps;
  return Math.max(hardFloorBps ?? 0, Math.min(tauPub0, headroomCrossVmBps));
}

/** Slider defaults = the values the Python run used (calibration), so the untouched panel equals deterministic_base. */
export function sliderDefaults(snapshot: SotpSnapshotSlice): SliderState | null {
  const cal = snapshot.sotp?.calibration;
  const inputs = snapshot.sotp?.inputs;
  if (!cal) return null;
  const gm = cal.growth_monthly_pub;
  const yoy = inputs?.public_volume_growth_yoy?.value;
  return {
    growth_yoy: present(yoy) ? yoy : present(gm) ? yoyFromMonthly(gm) : 0,
    tau_pub_bps: cal.tau_pub_start_bps,
    conf_share_target: cal.confidential_share_target ?? inputs?.confidential_share_target?.value ?? cal.confidential_share_start,
    tau_conf_bps: cal.tau_conf_start_bps,
    alpha_capture: cal.alpha_capture,
    regime: REGIME_GLIDEPATH,
  };
}

/** Base inputs with the slider state applied (the same transformations build_inputs performs). */
export function inputsFromSliders(snapshot: SotpSnapshotSlice, state: SliderState): BaseInputsResult {
  const base = baseInputsFromSnapshot(snapshot, state.regime);
  if (!base.inputs) return base;
  const cal = snapshot.sotp.calibration;
  const H = base.inputs.horizon_months;
  const gPub = monthlyFromYoy(state.growth_yoy);
  const inputs: SotpInputs = {
    ...base.inputs,
    tau_pub_bps: state.tau_pub_bps,
    tau_conf_bps: state.tau_conf_bps,
    alpha_capture: state.alpha_capture,
    growth_monthly_pub: gPub,
    growth_monthly_conf: confidentialGrowth(gPub, cal.confidential_share_start, state.conf_share_target, H),
    tau_floor_bps: tauFloorFor(state.tau_pub_bps, cal.public_take_floor_bps, cal.headroom_cross_vm_bps, cal.tau_floor_bps),
  };
  return { ...base, inputs };
}

/** Live operating point: aligned-window daily volume and the net take (tau x alpha) at t = 0. */
export function liveOperatingPoint(snapshot: SotpSnapshotSlice): { daily_volume_usd: number | null; net_take_bps: number | null } {
  const cal = snapshot.sotp?.calibration;
  if (!cal) return { daily_volume_usd: null, net_take_bps: null };
  const windowDays = (cal.take_rate_window_days as number | undefined) ?? snapshot.intents_forensics?.fees?.take_rate_window_days ?? 30;
  const v = present(cal.v_pub_30d_usd) && present(cal.v_conf_30d_usd) ? (cal.v_pub_30d_usd + cal.v_conf_30d_usd) / windowDays : null;
  return { daily_volume_usd: v, net_take_bps: present(cal.net_take_start_bps) ? cal.net_take_start_bps : null };
}

/** [rowIndex, colIndex] of the heatmap cell nearest the operating point (volume compared in log space). */
export function nearestHeatmapCell(hm: SensitivityHeatmap, dailyVolumeUsd: number | null, netTakeBps: number | null): [number, number] | null {
  if (!present(dailyVolumeUsd) || !present(netTakeBps) || !hm.x?.length || !hm.y?.length) return null;
  let ci = 0;
  let best = Infinity;
  hm.x.forEach((x, i) => {
    const d = Math.abs(Math.log(x) - Math.log(dailyVolumeUsd));
    if (d < best) {
      best = d;
      ci = i;
    }
  });
  let ri = 0;
  best = Infinity;
  hm.y.forEach((y, i) => {
    const d = Math.abs(y - netTakeBps);
    if (d < best) {
      best = d;
      ri = i;
    }
  });
  return [ri, ci];
}
