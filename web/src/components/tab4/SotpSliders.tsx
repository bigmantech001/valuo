"use client";

import { useMemo, useState } from "react";
import { Button, Card, Slider, Toggle } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { fmtBps, fmtInt, fmtPct, fmtUsdCompact } from "@/lib/format";
import { deterministicSotp, type PortCheck, type SotpSnapshotSlice } from "@/lib/quantClient";
import type { RegimeKey } from "@/lib/types";
import { DeterministicReadout } from "./DeterministicReadout";
import { inputsFromSliders, monthlyFromYoy, reconciledTauPub, sliderDefaults, type SliderState } from "./sliderModel";

export interface RegimeOption {
  value: RegimeKey;
  label: string;
  hint: string;
}

export interface SotpSlidersProps {
  slice: SotpSnapshotSlice;
  regimeOptions: RegimeOption[];
  portCheck: PortCheck;
}

const TAU_PUB = { min: 1, max: 20, step: 0.05 };
const ALPHA = { min: 0, max: 0.5, step: 0.005 };

function sameState(a: SliderState | null, b: SliderState | null): boolean {
  if (!a || !b) return a === b;
  return a.growth_yoy === b.growth_yoy && a.tau_pub_bps === b.tau_pub_bps && a.conf_share_target === b.conf_share_target && a.tau_conf_bps === b.tau_conf_bps && a.alpha_capture === b.alpha_capture && a.regime === b.regime;
}

const bps2 = (v: number) => fmtBps(v, { signed: false, decimals: 2 });
const pct0 = (v: number) => fmtPct(v, { decimals: 0, signed: true });
const pct1 = (v: number) => fmtPct(v, { decimals: 1 });

/**
 * Scenario panel. The sliders drive the deterministic model (quantClient.deterministicSotp, a verbatim port of
 * sotp_valuation.deterministic_sotp). Defaults are the calibration values the Python run used, so the untouched
 * panel reproduces sotp.calibration.deterministic_base. Monte Carlo percentiles elsewhere on the tab do not move.
 */
export function SotpSliders({ slice, regimeOptions, portCheck }: SotpSlidersProps) {
  const defaults = useMemo(() => sliderDefaults(slice), [slice]);
  const [state, setState] = useState<SliderState | null>(defaults);
  const cal = slice.sotp?.calibration;
  const reg = slice.sotp?.inputs;

  const computed = useMemo(() => {
    if (!state) return null;
    const built = inputsFromSliders(slice, state);
    if (!built.inputs) return { ...built, result: null, error: null as string | null };
    try {
      return { ...built, result: deterministicSotp(built.inputs), error: null as string | null };
    } catch (e) {
      return { ...built, result: null, error: e instanceof Error ? e.message : String(e) };
    }
  }, [slice, state]);

  if (!state || !cal || !defaults) {
    return (
      <Card title="Scenario model">
        <p className="text-[13.5px] text-muted">
          Not available: the calibration block is missing from this snapshot, so the model inputs cannot be rebuilt. The valuation stage did not run; see the snapshot warnings and re-run <code className="font-mono text-[12px]">make reproduce</code>.
        </p>
      </Card>
    );
  }

  const H = slice.sotp.horizon_months;
  const set = (patch: Partial<SliderState>) => setState((s) => (s ? { ...s, ...patch } : s));
  const growthRange = { min: reg?.public_volume_growth_yoy?.low ?? -0.2, max: reg?.public_volume_growth_yoy?.high ?? 1.5 };
  const shareRange = { min: reg?.confidential_share_target?.low ?? 0.05, max: reg?.confidential_share_target?.high ?? 0.6 };
  const confTakeRange = { min: reg?.confidential_take_bps?.low ?? 10, max: reg?.confidential_take_bps?.high ?? 30 };
  const ceiling = cal.competitive_fee_ceiling_bps;
  const floorNow = computed?.inputs?.tau_floor_bps ?? cal.tau_floor_bps;
  const reconciled = reconciledTauPub(cal.gross_fees_30d_usd, cal.v_conf_30d_usd, state.tau_conf_bps, cal.v_pub_30d_usd);
  const reconciledClamped = reconciled === null ? null : Math.min(TAU_PUB.max, Math.max(TAU_PUB.min, reconciled));
  const reconciledApplied = reconciledClamped === null || Math.abs(reconciledClamped - state.tau_pub_bps) < 1e-9;
  const isDefault = sameState(state, defaults);
  const portOk = portCheck.ok && Number.isFinite(portCheck.max_rel_error);
  const confDivisor = reg?.confidential_compression_divisor?.value;

  return (
    <Card
      title="Scenario model"
      subtitle={`Change the inputs to recompute the three-engine valuation on its expected path, in your browser. The defaults are the values the snapshot run used. The Monte Carlo percentiles below come from the seeded ${fmtInt(slice.sotp.n_paths)}-path run and do not move.`}
      actions={
        <Button size="sm" variant="secondary" onClick={() => setState(defaults)} disabled={isDefault}>
          Reset to snapshot
        </Button>
      }
      footer={
        <span className={portOk ? undefined : "text-crimson"} title={portCheck.notes.join("; ") || undefined}>
          {portOk
            ? `The browser model reproduces the Python base path and all ${fmtInt(portCheck.heatmap_cells)} heatmap cells (largest relative difference ${portCheck.max_rel_error.toExponential(1)}).`
            : `The browser model does not reproduce the Python base path${Number.isFinite(portCheck.max_rel_error) ? ` (largest relative difference ${portCheck.max_rel_error.toExponential(1)})` : ""}; treat slider outputs with caution.`}
        </span>
      }
    >
      <div className="grid grid-cols-1 gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="flex min-w-0 flex-col gap-7">
          <Slider
            label="Public volume growth, per year"
            value={state.growth_yoy}
            min={growthRange.min}
            max={growthRange.max}
            step={0.01}
            onChange={(v) => set({ growth_yoy: v })}
            format={pct0}
            description={`Assumption, default ${pct0(reg?.public_volume_growth_yoy?.value ?? NaN)}; ${fmtPct(monthlyFromYoy(state.growth_yoy), { decimals: 2, signed: true })} a month on the expected path.`}
          />
          <div className="flex flex-col gap-2">
            <Slider
              label="Public take rate at start, gross"
              value={state.tau_pub_bps}
              min={TAU_PUB.min}
              max={TAU_PUB.max}
              step={TAU_PUB.step}
              onChange={(v) => set({ tau_pub_bps: v })}
              format={bps2}
              marker={typeof ceiling === "number" ? { value: ceiling, label: "Live competitive ceiling", tone: "amber" } : null}
              description={`Decays toward a floor of ${bps2(floorNow)} at ${fmtPct(cal.lambda_pub_monthly, { decimals: 1 })} a month. The ceiling is the best competitor's measured friction on cross-VM routes.`}
            />
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[12.5px] text-muted">
              <span className="tnum">Matches measured fees at {reconciled === null ? "n/a (no public volume)" : bps2(reconciled)}</span>
              <Button size="xs" variant="ghost" disabled={reconciledApplied} onClick={() => reconciledClamped !== null && set({ tau_pub_bps: Number(reconciledClamped.toFixed(4)) })}>
                Use measured value
              </Button>
            </div>
          </div>
          <Slider
            label={`Confidential share of volume by month ${fmtInt(H)}`}
            value={state.conf_share_target}
            min={shareRange.min}
            max={shareRange.max}
            step={0.01}
            onChange={(v) => set({ conf_share_target: v })}
            format={pct1}
            marker={{ value: cal.confidential_share_start, label: "Live 30-day share", tone: "neutral" }}
            description={`Assumption; the share moves linearly from the measured ${pct1(cal.confidential_share_start)}. Confidential TVL is ${cal.confidential_tvl_verified ? "verified" : "unverified at the source"}.`}
          />
          <Slider
            label="Confidential take rate at start, gross"
            value={state.tau_conf_bps}
            min={confTakeRange.min}
            max={confTakeRange.max}
            step={0.5}
            onChange={(v) => set({ tau_conf_bps: v })}
            format={bps2}
            description={`Assumption, default ${bps2(reg?.confidential_take_bps?.value ?? NaN)}: no live confidential fee series exists. Decays at ${fmtPct(cal.lambda_conf_monthly, { decimals: 1 })} a month.`}
          />
          <Slider
            label="Share of fees spent on buybacks"
            value={state.alpha_capture}
            min={ALPHA.min}
            max={ALPHA.max}
            step={ALPHA.step}
            onChange={(v) => set({ alpha_capture: v })}
            format={pct1}
            marker={{ value: cal.alpha_capture, label: "Measured, 30 days", tone: "neutral" }}
            description={`Holder revenue as a share of gross fees. At the measured share the net take rate is ${bps2(cal.net_take_start_bps)}.`}
          />
          <Toggle<RegimeKey> label="Issuance schedule" options={regimeOptions} value={state.regime} onChange={(v) => set({ regime: v })} />
        </div>
        <div className="min-w-0">
          {computed?.result && computed.inputs ? (
            <DeterministicReadout result={computed.result} inputs={computed.inputs} base={cal.deterministic_base} cal={cal} regime={state.regime} windowDays={computed.window_days} />
          ) : (
            <div className="rounded-md border border-dashed border-border-strong px-4 py-6 text-[13.5px] text-muted">
              The model cannot run on this snapshot.
              {computed?.missing?.length ? ` Missing: ${computed.missing.join(", ")}.` : ""}
              {computed?.error ? ` Error: ${computed.error}` : ""}
            </div>
          )}
        </div>
      </div>
      <MethodNote className="mt-8">
        <p>
          The panel runs <code>quantClient.deterministicSotp</code>, a line-for-line port of <code>deterministic_sotp</code> in <code>quant/valuo/models/sotp_valuation.py</code>; untouched, it reproduces <code>sotp.calibration.deterministic_base</code>, the expected path under the mean-matching GBM.
        </p>
        <p>
          Growth: monthly g = (1 + g<sub>yoy</sub>)<sup>1/12</sup> − 1 (<code>sotp.inputs.public_volume_growth_yoy</code>); confidential growth is set so the confidential share reaches the target by M{fmtInt(H)} (odds-ratio construction, <code>sotp.inputs.confidential_share_target</code>).
        </p>
        <p>
          Public take: τ<sub>t</sub> = floor + (τ<sub>0</sub> − floor)(1 − λ)<sup>t</sup>, floor = max({bps2(cal.public_take_floor_bps)}, min(τ<sub>0</sub>, cross-VM headroom {bps2(cal.headroom_cross_vm_bps ?? NaN)})), λ = {fmtPct(cal.lambda_pub_monthly, { decimals: 1 })} per month. The ceiling marker is <code>execution_bench.competitive_fee_ceiling_bps</code>: the median over cross-VM cells of the best competitor&apos;s friction. The measured start rate solves (gross fees − V<sub>conf</sub> × τ<sub>conf</sub>) / V<sub>pub</sub> over the 30-day window. Holder revenue = V × τ × α.
        </p>
        <p>
          Confidential take: <code>sotp.inputs.confidential_take_bps</code>, compressing at λ / {confDivisor ?? "n/a"}. Buyback share α = DefiLlama near-intents dailyHoldersRevenue / dailyFees ({cal.alpha_source}).
        </p>
        <p>
          Issuance: <code>sotp.calibration.regime_inflation_paths_annual[regime]</code> × measured scale {cal.issuance_scale_measured_over_path?.toFixed(4)} (per-epoch minting / nominal). Implied price divides FDV by the supply at the horizon for the chosen schedule; current FDV {fmtUsdCompact(cal.current_fdv_usd)} is spot × on-chain total supply.
        </p>
        <p>
          Port check (<code>verifyPort</code>): {portCheck.ok ? "passed" : "failed"}; base-path max relative error {Number.isFinite(portCheck.max_rel_error) ? portCheck.max_rel_error.toExponential(1) : "n/a"}; crossover month {portCheck.crossover_match ? "matches" : "differs"}; heatmap {fmtInt(portCheck.heatmap_cells)} cells, max relative error {Number.isFinite(portCheck.heatmap_max_rel_error) ? portCheck.heatmap_max_rel_error.toExponential(1) : "n/a"}
          {portCheck.notes.length ? `. Notes: ${portCheck.notes.join("; ")}` : ""}.
        </p>
      </MethodNote>
    </Card>
  );
}
