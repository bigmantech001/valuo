"use client";

import { useMemo, useState } from "react";
import { fmtInt, fmtMonth, fmtNear, fmtNearCompact, fmtNum, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import { REGIME_CUSTOM_CAP, REGIME_STATUS_QUO, REGIME_SVRN_GLIDEPATH, runRegime, type RegimeKind, type RegimeRun, type SupplyModelInputs } from "@/lib/supplyClient";
import type { PortCheck } from "./portCheck";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import { LineChart, type LineMarker, type LineSeries } from "@/components/charts/LineChart";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Card } from "@/components/ui/Card";
import { MethodNote, StatGrid } from "@/components/ui/Section";
import { Slider } from "@/components/ui/Slider";
import { Stat } from "@/components/ui/Stat";
import { Table, type Column } from "@/components/ui/Table";
import { Toggle } from "@/components/ui/Toggle";
import { REF_BLOCK_FINAL, REF_HOLDERS_REVENUE, refBlock } from "./provenanceRefs";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

type VolumeMode = "flat" | "yoy";

export interface RegimeLabProps {
  /** true when the registry's volume growth was replaced by the measured trend this run */
  growthMeasured?: boolean;
  inputs: SupplyModelInputs | null;
  /** snapshot paths that were missing when `inputs` is null */
  missing: string[];
  /** regime key -> label from supply_physics.regimes */
  regimeLabels: Record<string, string>;
  /** server-side comparison of this port against supply_physics.trajectories */
  portChecks: PortCheck[];
  epochStartHeight: number | null;
  /** intents_forensics.volume.30d / 30 */
  currentDailyVolumeUsd: number | null;
}

const CAP_MIN_PCT = 0.5;
const CAP_MAX_PCT = 3.0;
const CAP_STEP_PCT = 0.05;

const TABLE_NAME: Record<PortCheck["table"], string> = { trajectories: "Flat volume", growth_trajectories: "Volume growth" };

function fmtDiff(d: number | null): string {
  if (d === null) return NA;
  if (d === 0) return "0";
  return d.toExponential(2);
}

const yTick = (y: number) => (y === 0 ? "0" : `${fmtNum(y / 1e6, { decimals: Math.abs(y) < 5e6 ? 1 : 0 })}M`);

const times = (v: number) => `${fmtNum(v, { decimals: 1 })}×`;

/**
 * Issuance regime toggle (status quo / SVRN glidepath / custom cap) driving a client-side rerun
 * of the supply model, with the cumulative issuance-versus-sinks chart and the crossover month.
 * Formulas are the TS port in `lib/supplyClient.ts`; the port check (in the method note) shows how
 * far it sits from the Python output stored in the snapshot (zero on the shipped snapshot).
 */
export function RegimeLab({ inputs, missing, regimeLabels, portChecks, epochStartHeight, currentDailyVolumeUsd, growthMeasured = false }: RegimeLabProps) {
  const [kind, setKind] = useState<RegimeKind>(REGIME_STATUS_QUO);
  const [capPct, setCapPct] = useState<number>(() => (inputs ? Math.round(inputs.current_max_inflation_rate * 100 * 100) / 100 : CAP_MAX_PCT));
  const [volumeMode, setVolumeMode] = useState<VolumeMode>("flat");

  const runs = useMemo<Record<RegimeKind, RegimeRun> | null>(() => {
    if (!inputs) return null;
    const g = volumeMode === "yoy" ? inputs.public_volume_growth_yoy : 0.0;
    return {
      [REGIME_STATUS_QUO]: runRegime(REGIME_STATUS_QUO, inputs, { volumeGrowthYoy: g }),
      [REGIME_SVRN_GLIDEPATH]: runRegime(REGIME_SVRN_GLIDEPATH, inputs, { volumeGrowthYoy: g }),
      [REGIME_CUSTOM_CAP]: runRegime(REGIME_CUSTOM_CAP, inputs, { customCap: capPct / 100, volumeGrowthYoy: g }),
    };
  }, [inputs, capPct, volumeMode]);

  if (!inputs || !runs) {
    return (
      <Card title="Issuance regime lab" subtitle="The regime lab needs every model input from the snapshot. These are missing:">
        <ul className="list-disc space-y-1 pl-5 text-[13px] text-crimson">
          {missing.map((m) => (
            <li key={m}>
              <code className="font-mono text-[12px]">{m}</code>
            </li>
          ))}
        </ul>
      </Card>
    );
  }

  const run = runs[kind];
  const t = run.trajectory;
  const M = inputs.horizon_months;
  const last = M - 1;
  const sinksCum = t.buyback_cum.map((b, i) => b + t.gas_burn_cum[i] + t.state_lock_cum[i]);
  const series: LineSeries[] = [
    { name: "Gross issuance", values: t.gross_issuance_cum, color: SERIES_COLORS[1], strokeWidth: 2 },
    { name: "All sinks", values: sinksCum, color: SERIES_COLORS[2], strokeWidth: 2 },
    { name: "Buybacks only", values: t.buyback_cum, color: SERIES_COLORS[2], dashed: true },
    { name: "Net float change", values: t.net_float_change_cum, color: COLORS.ink, dashed: true, strokeWidth: 1.25 },
  ];
  const markers: LineMarker[] = [];
  if (finite(t.crossover_month)) markers.push({ x: t.crossover_month, label: `Crossover ${fmtMonth(t.crossover_month)}`, color: COLORS.ink });
  if (kind === REGIME_SVRN_GLIDEPATH && inputs.svrn_glidepath_months < M) markers.push({ x: inputs.svrn_glidepath_months, label: `Glidepath ends M${inputs.svrn_glidepath_months}`, color: COLORS.dim });

  const netEnd = t.net_float_change_cum[last];
  const multiple = finite(run.breakeven_daily_volume_usd) && finite(currentDailyVolumeUsd) && currentDailyVolumeUsd > 0 ? run.breakeven_daily_volume_usd / currentDailyVolumeUsd : null;
  const labelFor = (k: RegimeKind): string => (k === REGIME_CUSTOM_CAP ? runs[k].label : regimeLabels[k] ?? runs[k].label);
  const hintFor = (k: RegimeKind): string => `${fmtNear(runs[k].trajectory.daily_issuance_start)}/day at M1, ${fmtNear(runs[k].trajectory.daily_issuance_end)}/day at M${M}`;
  const coverEnd = t.gross_issuance_cum[last] > 0 ? sinksCum[last] / t.gross_issuance_cum[last] : null;

  const checkColumns: Column<PortCheck>[] = [
    { key: "regime", header: "Regime", render: (c) => <span className="text-ink">{regimeLabels[c.regime] ?? c.regime}</span> },
    { key: "table", header: "Volume path", render: (c) => <span className="text-muted">{TABLE_NAME[c.table]}</span> },
    { key: "path", header: "Max |Δ| inflation path", numeric: true, render: (c) => fmtDiff(c.path_max_abs_diff) },
    { key: "series", header: "Max |Δ| cumulative series", numeric: true, render: (c) => fmtDiff(c.max_abs_diff) },
    { key: "scale", header: "Reference scale", numeric: true, render: (c) => fmtNearCompact(c.reference_scale) },
    { key: "be", header: "Max |Δ| breakeven", numeric: true, render: (c) => fmtDiff(Math.max(c.breakeven_abs_diff ?? 0, c.breakeven_at_ceiling_abs_diff ?? 0)) },
    { key: "stake", header: "Max |Δ| staking row", numeric: true, render: (c) => fmtDiff(c.staking_max_abs_diff) },
    { key: "cross", header: "Crossover", render: (c) => (c.crossover_match && c.cumulative_crossover_match ? "Match" : <span className="text-crimson">Mismatch</span>) },
    { key: "ok", header: "Result", render: (c) => (c.ok ? "Exact" : <span className="text-crimson">Diverges</span>) },
  ];
  const allOk = portChecks.length > 0 && portChecks.every((c) => c.ok);
  const nBad = portChecks.filter((c) => !c.ok).length;
  const epochRef = refBlock(epochStartHeight);

  const readout = (
    <>
      Under <span className="text-ink">{labelFor(kind)}</span>
      {volumeMode === "yoy" ? ` with volume growing ${fmtPct(inputs.public_volume_growth_yoy, { decimals: 0 })} a year` : " with volume flat at the 30-day run-rate"}, sinks cover{" "}
      <span className="tnum text-ink">{fmtPct(coverEnd, { decimals: 1 })}</span> of cumulative issuance over {M} months and the float{" "}
      {netEnd > 0 ? "grows" : "shrinks"} by <span className={`tnum ${netEnd > 0 ? "text-crimson" : "text-emerald"}`}>{fmtNearCompact(Math.abs(netEnd))}</span>.{" "}
      {finite(t.crossover_month)
        ? `Monthly sinks first exceed issuance in ${fmtMonth(t.crossover_month, { quarter: true })}.`
        : "Monthly sinks never exceed issuance within the horizon."}
    </>
  );

  const chartTitle = `Cumulative issuance versus sinks, ${labelFor(kind)}`;
  const chartDesc = "Cumulative gross NEAR issuance against cumulative buyback plus gas burn plus state lock over the model horizon, in NEAR";

  return (
    <Card
      title="Issuance regime lab"
      subtitle={`Cumulative issuance against cumulative sinks over ${M} months at spot price. Switch the regime or set a cap; the model reruns in the browser from the snapshot inputs.`}
      actions={
        <span className="flex items-center gap-3">
          {epochRef ? <ProvenanceBadge source={epochRef.source} name={epochRef.name} label="Issuance" /> : null}
          <ProvenanceBadge source={REF_HOLDERS_REVENUE.source} name={REF_HOLDERS_REVENUE.name} label="Buybacks" />
        </span>
      }
    >
      <div className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-5 border-b border-border pb-5 lg:grid-cols-[auto_minmax(16rem,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <div className="max-w-full overflow-x-auto">
            <Toggle<RegimeKind>
              label="Issuance regime"
              value={kind}
              onChange={setKind}
              options={[
                { value: REGIME_STATUS_QUO, label: `Status quo ${fmtPct(inputs.current_max_inflation_rate, { decimals: 2 })}`, hint: hintFor(REGIME_STATUS_QUO) },
                { value: REGIME_SVRN_GLIDEPATH, label: `SVRN glidepath → ${fmtPct(inputs.svrn_target_inflation, { decimals: 2 })}`, hint: hintFor(REGIME_SVRN_GLIDEPATH) },
                { value: REGIME_CUSTOM_CAP, label: `Custom ${fmtNum(capPct, { decimals: 2 })}%`, hint: hintFor(REGIME_CUSTOM_CAP) },
              ]}
            />
          </div>
          <div className="max-w-full overflow-x-auto">
            <Toggle<VolumeMode>
              label="Intents volume path"
              value={volumeMode}
              onChange={setVolumeMode}
              options={[
                { value: "flat", label: "Flat 30-day run-rate" },
                { value: "yoy", label: `${fmtPct(inputs.public_volume_growth_yoy, { decimals: 0, signed: true })} a year (${growthMeasured ? "measured trend" : "assumption"})` },
              ]}
            />
          </div>
        </div>
        <Slider
          label="Custom cap, annual maximum inflation"
          value={capPct}
          min={CAP_MIN_PCT}
          max={CAP_MAX_PCT}
          step={CAP_STEP_PCT}
          onChange={(v) => {
            setCapPct(v);
            setKind(REGIME_CUSTOM_CAP);
          }}
          format={(v) => `${fmtNum(v, { decimals: 2 })}%`}
          marker={{ value: Math.round(inputs.current_max_inflation_rate * 100 * 100) / 100, label: "Live cap", tone: "neutral" }}
          description="Moving the slider selects the custom regime. Custom caps have no Python reference in the snapshot."
        />
      </div>

      <p className="mt-5 max-w-4xl text-[14.5px] leading-relaxed text-muted" aria-live="polite">
        {readout}
      </p>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-[12.5px] text-muted" aria-hidden>
        {series.map((s) => (
          <span key={s.name} className="inline-flex items-center gap-2">
            <svg width="18" height="6" className="shrink-0">
              <line x1="0" x2="18" y1="3" y2="3" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? "4 3" : undefined} />
            </svg>
            {s.name}
          </span>
        ))}
        <span className="text-dim">Cumulative NEAR (millions), by model month</span>
      </div>
      <div className="mt-2 hidden md:block">
        <LineChart
          title={chartTitle}
          description={chartDesc}
          series={series}
          x={t.months}
          xFormat={(m) => `M${Math.round(m)}`}
          yFormat={yTick}
          markers={markers}
          width={1000}
          height={360}
          margin={{ left: 48, right: 12, bottom: 24 }}
          yTicks={6}
          xTicks={12}
          legend={false}
          pointLimit={0}
        />
      </div>
      <div className="mt-2 md:hidden">
        <LineChart
          title={`${chartTitle} (compact)`}
          description={chartDesc}
          series={series}
          x={t.months}
          xFormat={(m) => `M${Math.round(m)}`}
          yFormat={yTick}
          markers={markers}
          width={380}
          height={260}
          margin={{ left: 40, right: 8, bottom: 22 }}
          xTicks={4}
          legend={false}
          pointLimit={0}
        />
      </div>

      <StatGrid cols={3} className="mt-6">
        <Stat label="Daily issuance" value={t.daily_issuance_start} format={(v) => fmtNear(v)} unit="at M1" size="sm" delta={{ value: fmtNear(t.daily_issuance_end), label: `at M${M}` }} />
        <Stat label={`Cumulative issuance, ${M} months`} value={t.gross_issuance_cum[last]} format={(v) => fmtNearCompact(v)} size="sm" hint={`Supply ends at ${fmtNearCompact(t.supply_end_near)}`} provenance={REF_BLOCK_FINAL} />
        <Stat
          label={`Cumulative sinks, ${M} months`}
          value={sinksCum[last]}
          format={(v) => fmtNearCompact(v)}
          size="sm"
          hint={`Buybacks ${fmtNearCompact(t.buyback_cum[last])}, burn ${fmtNearCompact(t.gas_burn_cum[last])}, lock ${fmtNearCompact(t.state_lock_cum[last])}`}
        />
        <Stat label={`Net float change, ${M} months`} value={netEnd} format={(v) => fmtNearCompact(v, { signed: true })} size="sm" tone={netEnd <= 0 ? "emerald" : "crimson"} hint="Positive means the float grows" />
        <Stat
          label="Crossover month"
          value={finite(t.crossover_month) ? fmtMonth(t.crossover_month, { quarter: true }) : "None in horizon"}
          size="sm"
          hint={finite(t.cumulative_crossover_month) ? `Cumulative crossover ${fmtMonth(t.cumulative_crossover_month, { quarter: true })}` : "Cumulative sinks never catch issuance"}
        />
        <Stat
          label="Breakeven daily volume"
          value={run.breakeven_daily_volume_usd}
          format={(v) => fmtUsdCompact(v)}
          unit="per day"
          size="sm"
          delta={finite(multiple) ? { value: times(multiple), tone: multiple <= 1 ? "emerald" : "crimson", label: "today's volume" } : undefined}
          hint={`At the terminal ${fmtPct(run.terminal_rate, { decimals: 2 })} rate`}
        />
      </StatGrid>

      <p className="mt-4 text-[13px] text-muted">
        {portChecks.length === 0 ? (
          "No snapshot regimes to check this client model against."
        ) : allOk ? (
          `Client model matches the Python output exactly in all ${fmtInt(portChecks.length)} snapshot comparisons.`
        ) : (
          <span className="text-crimson">{`Client model diverges from the Python output in ${fmtInt(nBad)} of ${fmtInt(portChecks.length)} snapshot comparisons; see the method note.`}</span>
        )}
      </p>

      <MethodNote className="mt-4" summary="Method, formulas and port check">
        <p>
          Supply compounds monthly: <code>S_m+1 = S_m × (1 + i_m × f × D / 365.25)</code>, with <code>D = {fmtNum(inputs.days_per_month, { decimals: 4 })}</code> days (
          <code>supply_physics.days_per_month</code>) and <code>f = {fmtNum(inputs.issuance_realization_factor, { decimals: 4 })}</code> (measured over nominal issuance).
        </p>
        <p>
          Buyback per day is <code>V × τ / 1e4 × α / P</code> with V {fmtUsdCompact(inputs.daily_volume_usd)}/day, τ {fmtNum(inputs.gross_take_bps, { decimals: 2 })} bps, α {fmtPct(inputs.capture_ratio, { decimals: 1 })}, P{" "}
          {fmtNum(inputs.near_price_usd, { decimals: 2 })} USD. Gas burn ({fmtNear(inputs.gas_burn_near_per_day)}/day) and state lock ({fmtNear(inputs.state_lock_growth_near_per_day)}/day) are held at their measured
          run-rates with no growth credit.
        </p>
        <p>
          Net float change is <code>E_m − (B_m + G_m + L_m)</code>. The crossover month is the first month with monthly net float change ≤ 0. Breakeven V* is computed at the regime&apos;s terminal rate
          {finite(run.breakeven_daily_volume_usd_at_ceiling) ? `; at the competitive fee ceiling it would be ${fmtUsdCompact(run.breakeven_daily_volume_usd_at_ceiling)}/day for this regime` : "; the snapshot has no competitive ceiling"}.
        </p>
        <p>
          Port check: each snapshot regime is recomputed from <code>supply_physics.inputs</code> with <code>lib/supplyClient.ts</code> (inflation path, then trajectory, breakeven and staking row) and compared
          element-wise with <code>supply_physics.trajectories</code> and <code>supply_physics.growth_trajectories</code>. The custom cap runs the same functions and has no stored reference.
        </p>
        <Table<PortCheck> className="mt-2" columns={checkColumns} rows={portChecks} rowKey={(c) => `${c.table}:${c.regime}`} emptyText="No snapshot regimes to compare against" />
      </MethodNote>
    </Card>
  );
}
