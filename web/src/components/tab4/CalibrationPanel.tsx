import type { ReactNode } from "react";
import { ProvenanceBadge, type ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import { Badge, Card, Table, type Column } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { fmtBps, fmtInt, fmtNear, fmtNearCompact, fmtNum, fmtPct, fmtUsd, fmtUsdCompact } from "@/lib/format";
import type { Manifest, RawRecord, Snapshot } from "@/lib/types";
import { mult } from "./fmt";
import { REF, findRecord } from "./refs";
import { yoyFromMonthly } from "./sliderModel";

function finite(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

const pct2 = (v: number) => fmtPct(v, { decimals: 2 });
const pct1 = (v: number) => fmtPct(v, { decimals: 1 });
const bps2 = (v: number) => fmtBps(v, { signed: false, decimals: 2 });
const num3 = (v: number) => fmtNum(v, { decimals: 3 });

type Basis = "measured" | "derived" | "assumption" | "mixed";
type Row = { key: string; group: string; header?: boolean; srcText?: string; name: string; value: ReactNode; basis: Basis; note?: ReactNode; prov?: RawRecord | ProvenanceRef | null; caution?: boolean };

const BASIS_BADGE: Record<Basis, { variant: "verified-api" | "derived" | "assumption" | "neutral"; label: string }> = {
  measured: { variant: "verified-api", label: "Measured" },
  derived: { variant: "derived", label: "Derived" },
  assumption: { variant: "assumption", label: "Assumption" },
  mixed: { variant: "neutral", label: "Measured and assumed" },
};

/** Every measured / derived / assumed parameter the Monte Carlo used, as one ruled table with its source. */
export function CalibrationPanel({ snapshot, manifest }: { snapshot: Snapshot; manifest: Manifest | null }) {
  const sotp = snapshot.sotp;
  const cal = sotp?.calibration;
  const growthMeasured = (snapshot.assumptions ?? []).some((a) => a.key === "public_volume_growth_yoy" && a.source === "measured");
  if (!cal) {
    return (
      <Card title="Calibration">
        <p className="text-[13.5px] text-muted">Not available: the calibration block is absent because the valuation stage did not run.</p>
      </Card>
    );
  }
  const vol = snapshot.intents_forensics?.volatility;
  const stateLockRecord = findRecord(manifest, "near_rpc_archival", "view_account:intents.near@");
  const meanToP50 = typeof cal.mc_mean_to_p50_fdv === "number" ? cal.mc_mean_to_p50_fdv : sotp.fdv_percentiles?.p50 > 0 ? cal.mc_mean_fdv / sotp.fdv_percentiles.p50 : null;
  const supplyByRegime = cal.supply_at_horizon_by_regime ?? {};
  const warnings = cal.warnings ?? [];
  // Gas burn at t=0 is the on-chain within-epoch supply drift (supply_physics.inputs.gas_burn_near_per_day); the DefiLlama
  // near-chain revenue figure is the cross-check, not the source, so the chip points at the predecessor block record.
  const epochStart = snapshot.near_rpc?.epoch_issuance?.epoch_start_height;
  const gasBurnRef: ProvenanceRef = finite(epochStart) ? { source: "near_rpc", name: `block:pred_of:${epochStart}` } : REF.blockFinal;
  const gasBurnDefillama = snapshot.supply_physics?.cross_checks?.gas_burn_defillama_near_day;
  const nearPerKb = snapshot.near_rpc?.storage_near_per_kb;
  const H = sotp.horizon_months;
  const yoy = yoyFromMonthly(cal.growth_monthly_pub);

  const rows: Row[] = [
    { key: "sp", group: "Volatility", name: "Price volatility, annual", value: num3(cal.sigma_price_annual), basis: "measured", note: `${fmtInt(cal.volatility_n_obs)} daily closes over ${vol?.window ?? cal.volatility_window}; ${num3(cal.sigma_price_monthly)} a month`, prov: REF.priceHistory1y },
    { key: "sv", group: "Volatility", name: "Volume volatility, monthly", value: num3(cal.sigma_volume_monthly), basis: "measured", note: `${fmtInt(vol?.volume_monthly_n_obs ?? cal.sigma_volume_monthly_n_obs)} monthly returns; confidential leg × ${fmtNum(cal.confidential_sigma_multiplier, { decimals: 2 })}`, prov: REF.intentsDexVolume },
    { key: "vol", group: "Volume and fees", name: "Volume, 30 days, public / confidential", value: `${fmtUsdCompact(cal.v_pub_30d_usd)} / ${fmtUsdCompact(cal.v_conf_30d_usd)}`, basis: "measured", note: `Confidential share ${pct1(cal.confidential_share_start)}`, prov: REF.nearstatsSummary },
    { key: "tp", group: "Volume and fees", name: "Public take rate at start", value: bps2(cal.tau_pub_start_bps), basis: "derived", note: `Blended gross ${bps2(cal.blended_gross_take_bps)} = fees ${fmtUsdCompact(cal.gross_fees_30d_usd)} / volume`, prov: REF.intentsFees },
    { key: "tc", group: "Volume and fees", name: "Confidential take rate at start", value: bps2(cal.tau_conf_start_bps), basis: "assumption", note: "No live confidential fee series" },
    { key: "al", group: "Volume and fees", name: "Buyback share of fees", value: pct1(cal.alpha_capture), basis: "measured", note: `Net take ${bps2(cal.net_take_start_bps)} at start`, prov: REF.intentsHoldersRevenue },
    { key: "fl", group: "Volume and fees", name: "Take-rate floor", value: bps2(cal.tau_floor_bps), basis: "derived", note: `Cross-VM headroom; competitive ceiling ${bps2(cal.competitive_fee_ceiling_bps ?? NaN)}`, prov: REF.oneclickCrossVm50k },
    { key: "lm", group: "Growth and decay", name: "Take-rate decay, public / confidential", value: `${pct2(cal.lambda_pub_monthly)} / ${pct2(cal.lambda_conf_monthly)} a month`, basis: "assumption" },
    { key: "gp", group: "Growth and decay", name: "Public volume growth", value: fmtPct(cal.growth_monthly_pub, { decimals: 2, signed: true }) + " a month", basis: growthMeasured ? "measured" : "assumption", note: `${fmtPct(yoy, { decimals: 0, signed: true })} a year, ${growthMeasured ? "measured trend used as the expected path" : "expected path"}` },
    { key: "gc", group: "Growth and decay", name: "Confidential volume growth", value: fmtPct(cal.growth_monthly_conf, { decimals: 2, signed: true }) + " a month", basis: "mixed", note: `Share ${pct1(cal.confidential_share_start)} measured to ${pct1(cal.confidential_share_target)} assumed by M${fmtInt(H)}`, prov: REF.nearstatsSummary },
    { key: "tm", group: "Valuation", name: "Terminal multiple, raw / used", value: `${mult(cal.terminal_multiple_raw)} / ${mult(cal.terminal_multiple_used)}`, basis: "derived", note: cal.terminal_multiple_clipped ? "Peer median clipped to the cap" : "Peer median, inside the guardrail", prov: REF.coingeckoMarkets, caution: cal.terminal_multiple_clipped === true },
    { key: "px", group: "Valuation", name: "NEAR price", value: fmtUsd(cal.price_usd, { decimals: 2 }), basis: "measured", note: `Current FDV ${fmtUsdCompact(cal.current_fdv_usd)}`, prov: REF.nearstatsSummary },
    { key: "dr", group: "Valuation", name: "Discount rate", value: fmtPct(sotp.discount_rate, { decimals: 0 }), basis: "assumption" },
    {
      key: "mc",
      group: "Valuation",
      name: "Monte Carlo mean FDV",
      value: fmtUsdCompact(cal.mc_mean_fdv),
      basis: "derived",
      note: `${mult(meanToP50, { decimals: 2 })} the P50; convexity, not a base case`,
      caution: true,
      srcText: "Model output",
    },
    {
      key: "gb",
      group: "Supply",
      name: "Gas burn at start",
      value: `${fmtNear(cal.gas_burn_near_day, { decimals: 0 })} a day`,
      basis: "measured",
      note: (
        <span className="inline-flex flex-wrap items-center gap-x-1.5">
          On-chain supply drift; DefiLlama cross-check {fmtNear(gasBurnDefillama, { decimals: 0 })} a day
          <ProvenanceBadge source={REF.nearGasRevenue.source} name={REF.nearGasRevenue.name} label="DefiLlama" />
        </span>
      ),
      prov: gasBurnRef,
    },
    { key: "sl", group: "Supply", name: "State lock growth at start", value: `${fmtNear(cal.state_lock_near_day, { decimals: 0 })} a day`, basis: "measured", note: finite(nearPerKb) && nearPerKb > 0 ? `Storage growth × 1 NEAR per ${fmtInt(1 / nearPerKb)} KB` : "Storage growth × storage price", prov: stateLockRecord ?? REF.blockFinal },
    { key: "sh", group: "Supply", name: `Supply at M${fmtInt(H)}, glidepath / status quo`, value: `${fmtNearCompact(supplyByRegime.svrn_glidepath)} / ${fmtNearCompact(supplyByRegime.status_quo)}`, basis: "derived", note: `Issuance scale ${fmtNum(cal.issuance_scale_measured_over_path, { decimals: 4 })} measured / nominal`, prov: REF.blockFinal },
  ];

  const params = rows;
  const tableRows: Row[] = params.flatMap((r, i) => (i === 0 || params[i - 1].group !== r.group ? [{ key: `g-${r.group}`, group: r.group, header: true, name: r.group, value: null, basis: r.basis }, r] : [r]));

  const columns: Column<Row>[] = [
    {
      key: "name",
      header: "Parameter",
      render: (r) => (r.header ? <span className="font-medium text-ink">{r.group}</span> : <div className="min-w-[13rem] pl-3 text-ink">{r.name}</div>),
    },
    { key: "value", header: "Value", numeric: true, render: (r) => (r.header ? null : <span className={r.caution ? "whitespace-nowrap text-amber" : "whitespace-nowrap text-ink"}>{r.value}</span>) },
    { key: "basis", header: "Basis", render: (r) => (r.header ? null : <Badge variant={BASIS_BADGE[r.basis].variant}>{BASIS_BADGE[r.basis].label}</Badge>) },
    { key: "note", header: "Note", render: (r) => <span className="text-[12.5px] text-muted">{r.note ?? ""}</span>, className: "min-w-[16rem]" },
    { key: "src", header: "Source", render: (r) => (r.header ? null : r.prov ? <ProvenanceBadge {...("sha256" in r.prov ? { record: r.prov } : { source: r.prov.source, name: r.prov.name })} /> : <span className="text-dim">{r.srcText ?? "Model input"}</span>) },
  ];

  return (
    <Card
      title="Calibration"
      subtitle="Every parameter behind the paths, marked by how it was obtained."
      actions={
        cal.confidential_tvl_verified ? null : (
          <Badge variant="assumption" dot>
            Confidential TVL unverified
          </Badge>
        )
      }
    >
      <Table<Row> columns={columns} rows={tableRows} rowKey={(r) => r.key} rowClassName={(r) => (r.header ? "bg-surface-2/60 hover:bg-surface-2/60" : undefined)} />
      {warnings.length ? (
        <div className="mt-5 rounded-md border border-amber/30 bg-amber/5 px-4 py-3 text-[13px] leading-relaxed">
          <div className="mb-1 font-medium text-amber">Model warnings</div>
          <ul className="list-disc space-y-0.5 pl-5 text-ink">
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <MethodNote className="mt-6">
        <p>Take basis: {cal.take_basis}. Public take start: {cal.tau_pub_start_method}. Buyback share: {cal.alpha_source}. Floor: {cal.tau_floor_source}, max({bps2(cal.public_take_floor_bps)}, min(public take, cross-VM headroom {bps2(cal.headroom_cross_vm_bps ?? NaN)})).</p>
        <p>
          Volatility: {vol?.source ?? "price series"}, log-return σ × √365 for price; {cal.sigma_volume_source} for volume. Price drift is zero unless the assumption is changed. Mean FDV: {cal.mc_mean_fdv_note ?? "mean over paths exceeds the P50 by lognormal convexity"}.
        </p>
        <p>
          Gas burn: −net burn per epoch × epochs per year / 365.25 from the epoch-start block vs its predecessor (<code>supply_physics.current_daily_sinks_near.gas_burn</code>); cross-check <code>supply_physics.cross_checks.gas_burn_defillama_near_day</code>. State lock: archival storage_usage growth across tracked sinks × <code>near_rpc.storage_near_per_kb</code>
          {finite(nearPerKb) ? ` (${fmtNum(nearPerKb, { decimals: 2 })} NEAR per KB)` : ""}.
        </p>
        <p>
          Crossover: {cal.crossover_basis}. Price: {cal.price_basis}. Current FDV: {cal.current_fdv_basis ?? "spot × on-chain total supply"}. Days per month {fmtNum(cal.days_per_month, { decimals: 4 })}; discount rate {fmtPct(sotp.discount_rate)}; horizon {fmtInt(H)} months; seed {fmtInt(sotp.seed)}; {fmtInt(sotp.n_paths)} paths.
        </p>
        <p>
          Fields: <code>sotp.calibration</code> (<code>sigma_price_annual</code>, <code>sigma_volume_monthly</code>, <code>tau_pub_start_bps</code>, <code>tau_conf_start_bps</code>, <code>alpha_capture</code>, <code>tau_floor_bps</code>, <code>lambda_pub_monthly</code>, <code>growth_monthly_pub</code>, <code>growth_monthly_conf</code>, <code>terminal_multiple_raw</code>, <code>terminal_multiple_used</code>, <code>v_pub_30d_usd</code>, <code>v_conf_30d_usd</code>, <code>gas_burn_near_day</code>, <code>state_lock_near_day</code>, <code>supply_at_horizon_by_regime</code>, <code>mc_mean_fdv</code>, <code>warnings</code>), <code>sotp.inputs</code>.
        </p>
      </MethodNote>
    </Card>
  );
}
