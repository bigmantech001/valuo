import { fmtBps, fmtNum, fmtPct, fmtUsd, fmtUsdCompact, NA } from "@/lib/format";
import type { IntentsForensics, NearOnchainTruth, SupplyPhysics } from "@/lib/types";
import { ProvenanceBadge, type ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import { Card } from "@/components/ui/Card";
import { MethodNote } from "@/components/ui/Section";
import { Table, type Column } from "@/components/ui/Table";
import { SERIES_COLORS } from "@/lib/theme";
import { REF_DEXS_VOLUME, REF_GROSS_FEES, REF_HOLDERS_REVENUE, REF_NEARSTATS_SUMMARY, refBlock, refPredBlock, refStateLockGrowth } from "./provenanceRefs";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

const times = (v: number) => `${fmtNum(v, { decimals: 1 })}×`;

/** Short display names for the two snapshot regimes; anything else falls back to its snapshot label. */
const SHORT_REGIME: Record<string, string> = { status_quo: "Status quo", svrn_glidepath: "SVRN glidepath" };

type BreakevenRow = {
  regime: string;
  label: string;
  terminal_rate: number | null;
  v_star: number | null;
  v_star_ceiling: number | null;
  multiple: number | null;
  multiple_ceiling: number | null;
};

export interface BreakevenPanelProps {
  sp: SupplyPhysics | null | undefined;
  fx: IntentsForensics | null | undefined;
  rpc: NearOnchainTruth | null | undefined;
  regimeLabels: Record<string, string>;
}

function Multiple({ v }: { v: number | null }) {
  if (!finite(v)) return <span className="text-dim">{NA}</span>;
  return <span className={v <= 1 ? "text-emerald" : "text-crimson"}>{times(v)}</span>;
}

/**
 * Breakeven volume V* per regime (issuance fully offset by buyback + gas burn + state lock at the
 * live take and capture ratio) against the current daily volume, plus today's flows.
 */
export function BreakevenPanel({ sp, fx, rpc, regimeLabels }: BreakevenPanelProps) {
  const vol30 = fx?.volume?.["30d"] ?? null;
  const currentDaily = finite(vol30) ? vol30 / 30 : null;
  const modelDaily = sp?.inputs?.daily_volume_usd?.value ?? null;
  const tau = sp?.inputs?.gross_take_bps?.value ?? null;
  const alpha = sp?.inputs?.capture_ratio?.value ?? null;
  const ceiling = sp?.inputs?.competitive_fee_ceiling_bps?.value ?? null;
  const price = sp?.inputs?.near_price_usd?.value ?? null;
  const sinks = sp?.current_daily_sinks_near ?? null;
  const issuance = sp?.current_daily_issuance_near ?? null;
  const epoch = rpc?.epoch_issuance?.epoch_start_height ?? null;
  const terminalByRegime = new Map<string, number>();
  for (const r of sp?.staking_yield_table ?? []) terminalByRegime.set(r.regime, r.inflation_rate);

  const be: Record<string, number | undefined> = sp?.breakeven_daily_volume_usd ?? {};
  const beCeil: Record<string, number | undefined> = sp?.breakeven_daily_volume_usd_at_ceiling ?? {};
  const regimeKeys = Array.from(new Set([...(sp?.regimes ?? []).map((r) => r.key), ...Object.keys(be)]));
  const rows: BreakevenRow[] = regimeKeys.map((key) => {
    const v = finite(be[key]) ? be[key] : null;
    const vc = finite(beCeil[key]) ? (beCeil[key] as number) : null;
    return {
      regime: key,
      label: SHORT_REGIME[key] ?? regimeLabels[key] ?? key,
      terminal_rate: terminalByRegime.get(key) ?? null,
      v_star: v,
      v_star_ceiling: vc,
      multiple: finite(v) && finite(currentDaily) && currentDaily > 0 ? v / currentDaily : null,
      multiple_ceiling: finite(vc) && finite(currentDaily) && currentDaily > 0 ? vc / currentDaily : null,
    };
  });

  const columns: Column<BreakevenRow>[] = [
    { key: "regime", header: "Regime", render: (r) => <span className="text-ink" title={regimeLabels[r.regime]}>{r.label}</span> },
    { key: "rate", header: "Terminal rate", numeric: true, render: (r) => fmtPct(r.terminal_rate, { decimals: 2 }) },
    { key: "vstar", header: "At live take", numeric: true, render: (r) => `${fmtUsdCompact(r.v_star)}/day` },
    { key: "mult", header: "× today", numeric: true, render: (r) => <Multiple v={r.multiple} /> },
    { key: "vceil", header: "At fee ceiling", numeric: true, render: (r) => (finite(r.v_star_ceiling) ? `${fmtUsdCompact(r.v_star_ceiling)}/day` : <span className="text-dim">{NA}</span>) },
    { key: "multc", header: "× today", numeric: true, render: (r) => <Multiple v={r.multiple_ceiling} /> },
  ];

  const lockRef = refStateLockGrowth(rpc);
  const flows: Array<{ label: string; value: number; color: string; ref: ProvenanceRef | null }> =
    finite(issuance) && sinks
      ? [
          { label: "Gross issuance", value: issuance, color: SERIES_COLORS[1], ref: refBlock(epoch) },
          { label: "Buybacks", value: sinks.buyback, color: SERIES_COLORS[2], ref: REF_HOLDERS_REVENUE },
          { label: "Gas burn", value: sinks.gas_burn, color: SERIES_COLORS[2], ref: refPredBlock(epoch) },
          { label: "Storage lock growth", value: sinks.state_lock, color: SERIES_COLORS[2], ref: lockRef },
        ]
      : [];
  const flowMax = Math.max(1e-9, ...flows.map((f) => f.value));

  return (
    <Card
      title="Breakeven volume"
      subtitle="The daily Intents volume at which buybacks, gas burn and storage lock together equal issuance at each regime's terminal rate, at spot price."
      actions={<ProvenanceBadge source={REF_NEARSTATS_SUMMARY.source} name={REF_NEARSTATS_SUMMARY.name} label="Volume" />}
    >
      <div className="space-y-6">
        <div>
          <h3 className="mb-2 text-[13.5px] font-medium text-ink">Today&apos;s flows, NEAR per day</h3>
          {flows.length ? (
            <ul className="space-y-2.5">
              {flows.map((f) => (
                <li key={f.label} className="grid grid-cols-[9.5rem_1fr_4.5rem] items-center gap-3 text-[13.5px] max-sm:grid-cols-[7.5rem_1fr_4rem]">
                  <span className="text-ink">{f.label}</span>
                  <span className="h-2.5 rounded-sm bg-surface-2">
                    <span className="block h-full rounded-sm" style={{ width: `${Math.max(0.6, (f.value / flowMax) * 100)}%`, background: f.color }} />
                  </span>
                  <span className="tnum text-right text-ink">{fmtNum(f.value, { decimals: 0 })}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[13px] text-dim">Today&apos;s issuance or sink figures are missing from this snapshot.</p>
          )}
        </div>

        <Table<BreakevenRow>
          columns={columns}
          rows={rows}
          rowKey={(r) => r.regime}
          caption={finite(currentDaily) ? `Breakeven daily volume against today's ${fmtUsdCompact(currentDaily)}/day` : "Breakeven daily volume"}
          emptyText="No breakeven volumes: the buyback channel is closed (take × capture ≤ 0)"
        />
        <p className="text-[13px] leading-relaxed text-muted">
          A multiple above 1× is how many times today&apos;s volume must grow, at a fixed take rate, before the float stops expanding. A lower take rate raises it one for one.
        </p>

        <MethodNote>
          <p>
            <code>V* = max(0, I − G − L) × P / ((τ / 1e4) × α)</code>, with price P {fmtUsd(price)}, gross take τ {fmtBps(tau, { signed: false, decimals: 2 })}, capture α {fmtPct(alpha, { decimals: 1 })}, and the
            competitive fee ceiling {finite(ceiling) ? fmtBps(ceiling, { signed: false, decimals: 2 }) : "not measured"} (median over cross-VM cells of the best competitor&apos;s friction). Fields:{" "}
            <code>supply_physics.breakeven_daily_volume_usd</code> and <code>supply_physics.breakeven_daily_volume_usd_at_ceiling</code>.
          </p>
          <p>
            Today&apos;s volume is <code>intents_forensics.volume.30d / 30</code>
            {finite(vol30) ? ` (${fmtUsdCompact(vol30)} over 30 days)` : ""}. The sinks were computed from the aligned-window model volume <code>supply_physics.inputs.daily_volume_usd</code> ={" "}
            {finite(modelDaily) ? `${fmtUsdCompact(modelDaily)}/day` : NA}. Flows: <code>supply_physics.current_daily_sinks_near</code> and <code>supply_physics.current_daily_issuance_near</code>.
          </p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            Sources:
            {flows.map((f) => (f.ref ? <ProvenanceBadge key={f.label} source={f.ref.source} name={f.ref.name} label={f.label} /> : null))}
            <ProvenanceBadge source={REF_DEXS_VOLUME.source} name={REF_DEXS_VOLUME.name} label="Model volume" />
            <ProvenanceBadge source={REF_GROSS_FEES.source} name={REF_GROSS_FEES.name} label="Take rate" />
          </div>
        </MethodNote>
      </div>
    </Card>
  );
}
