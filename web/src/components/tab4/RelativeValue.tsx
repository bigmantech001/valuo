import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { FigureList, Panel, SubHead, type FigureItem } from "@/components/tab1/parts";
import { Table, Tooltip, type Column } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
import { fmtInt, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import type { RelativeValue as RelativeValueData, RelativeValueBandLeg, RelativeValueCoverage, RelativeValueEntity, RelativeValueStakingRegime } from "@/lib/types";
import { REGIME_NAME, mult } from "./fmt";
import { peerFeesRef } from "./refs";

type Kind = "peer" | "near" | "component";
type Row = RelativeValueEntity & { kind: Kind };

function fin(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function rankText(c: RelativeValueCoverage | undefined): string | null {
  if (!c || !fin(c.rank)) return null;
  return `rank ${fmtInt(c.rank)} of ${fmtInt(c.n)}`;
}

function Methodology({ text }: { text: string | null | undefined }) {
  if (!text) return null;
  return (
    <Tooltip wide side="left" content={<div>Revenue as DefiLlama defines it: {text}</div>}>
      <span tabIndex={0} className="cursor-help text-[12px] text-dim underline decoration-dotted underline-offset-2 hover:text-ink">
        Revenue definition
      </span>
    </Tooltip>
  );
}

interface BandRow {
  key: string;
  label: string;
  leg: RelativeValueBandLeg;
}

/**
 * Relative value: NEAR's FDV multiples against the live peer set, its rank, a peer-multiple implied
 * FDV band labelled as a cross-check (not a fair value), and the staking / security-budget lens.
 * Reads `relative_value`; findings and the small-sample caveat are the pipeline's own sentences.
 */
export function RelativeValue({ data }: { data: RelativeValueData | null | undefined }) {
  if (!data) return null;
  const cov = data.coverage ?? {};
  const rows: Row[] = [
    ...[...(data.peers ?? [])].sort((a, b) => (a.fdv_to_fees_run_rate ?? Infinity) - (b.fdv_to_fees_run_rate ?? Infinity)).map((p) => ({ ...p, kind: "peer" as Kind })),
    ...(data.near ? [{ ...data.near, kind: "near" as Kind }] : []),
    ...(data.near_components ?? []).map((p) => ({ ...p, kind: "component" as Kind })),
  ];
  const nPeers = fin(data.n_peers) ? data.n_peers : (data.peers ?? []).length;

  const columns: Column<Row>[] = [
    {
      key: "chain",
      header: "Chain",
      render: (r) => (
        <div className={cn(r.kind === "component" && "pl-4")}>
          <div className={cn(r.kind === "near" ? "font-medium text-ink" : r.kind === "component" ? "text-muted" : "text-ink")}>
            {r.label.startsWith(r.symbol) ? (
              <span className={cn(r.kind === "near" && "font-medium")}>{r.label}</span>
            ) : (
              <>
                <span className="font-medium">{r.symbol}</span> <span className={r.kind === "near" ? "text-ink" : "text-muted"}>{r.label}</span>
              </>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-3">
            {r.kind === "component" ? <span className="text-[12px] text-dim">Component of the NEAR row</span> : null}
            <Methodology text={r.revenue_methodology} />
          </div>
        </div>
      ),
    },
    { key: "fdv", header: "FDV", numeric: true, render: (r) => (r.kind === "component" ? <span className="text-dim">same</span> : fmtUsdCompact(r.fdv_usd)) },
    {
      key: "fees",
      header: "Annualised fees",
      numeric: true,
      render: (r) => (
        <div>
          <div>{fmtUsdCompact(r.annualized_fees_usd)}</div>
          {r.kind === "peer" ? <ProvenanceBadge source={peerFeesRef(r.slug).source} name={peerFeesRef(r.slug).name} /> : null}
        </div>
      ),
    },
    { key: "rev", header: "Annualised revenue", numeric: true, render: (r) => fmtUsdCompact(r.annualized_revenue_usd) },
    {
      key: "f2f",
      header: "FDV / fees",
      numeric: true,
      render: (r) => (
        <div>
          <div className={cn(r.kind === "near" && "font-semibold text-ink")}>{mult(r.fdv_to_fees_run_rate, { decimals: 0 })}</div>
          {r.kind === "near" && rankText(cov.fdv_to_fees_run_rate) ? <div className="text-[12px] text-muted">{rankText(cov.fdv_to_fees_run_rate)}</div> : null}
        </div>
      ),
    },
    {
      key: "f2r",
      header: "FDV / revenue",
      numeric: true,
      render: (r) => (
        <div>
          <div className={cn(r.kind === "near" && "font-semibold text-ink")}>{mult(r.fdv_to_revenue_run_rate, { decimals: 0 })}</div>
          {r.kind === "near" && rankText(cov.fdv_to_revenue_run_rate) ? <div className="text-[12px] text-muted">{rankText(cov.fdv_to_revenue_run_rate)}</div> : null}
        </div>
      ),
    },
  ];

  // ------------------------------------------------------------------ implied band
  const band = data.implied_fdv_band;
  const bandRows: BandRow[] = [];
  if (band?.fees) bandRows.push({ key: "fees", label: "Peer FDV / fees", leg: band.fees });
  if (band?.revenue) bandRows.push({ key: "revenue", label: "Peer FDV / revenue", leg: band.revenue });
  const bandCurrent = fin(band?.current_fdv_usd) ? band.current_fdv_usd : null;
  const bandColumns: Column<BandRow>[] = [
    { key: "label", header: "Multiple applied", render: (r) => <span className="text-ink">{r.label}</span> },
    { key: "cf", header: "NEAR cash flow, annualised", numeric: true, render: (r) => fmtUsdCompact(r.leg.near_cash_flow_usd) },
    { key: "p25", header: "Peer P25", numeric: true, render: (r) => fmtUsdCompact(r.leg.p25_fdv_usd) },
    { key: "p50", header: "Peer median", numeric: true, render: (r) => <span className="font-medium text-ink">{fmtUsdCompact(r.leg.median_fdv_usd)}</span> },
    { key: "p75", header: "Peer P75", numeric: true, render: (r) => fmtUsdCompact(r.leg.p75_fdv_usd) },
    { key: "n", header: "Peers", numeric: true, render: (r) => fmtInt(r.leg.n_peers) },
    {
      key: "vs",
      header: "Median ÷ market FDV",
      numeric: true,
      render: (r) => (fin(r.leg.median_fdv_usd) && fin(bandCurrent) && bandCurrent > 0 ? mult(r.leg.median_fdv_usd / bandCurrent, { decimals: 1 }) : NA),
    },
  ];

  // ------------------------------------------------------------------ staking
  const st = data.staking;
  const stakingItems: FigureItem[] = st
    ? [
        { key: "budget", label: "Security budget", sub: "Issuance to validators and delegators, at spot", value: `${fmtUsdCompact(st.security_budget_usd_per_year)} a year` },
        { key: "pct", label: "Security budget as share of FDV", value: fmtPct(st.security_budget_pct_of_fdv, { decimals: 1 }) },
        { key: "fees", label: "Fees ÷ security budget", sub: `${fmtUsdCompact(st.annualized_fees_usd)} of annualised fees`, value: fmtPct(st.fees_to_security_budget, { decimals: 0 }) },
        { key: "rev", label: "Holder revenue ÷ security budget", sub: `${fmtUsdCompact(st.annualized_holder_revenue_usd)} of gas burn plus Intents buyback`, value: fmtPct(st.revenue_to_security_budget, { decimals: 0 }) },
        { key: "dil", label: "Net dilution", sub: "Security budget less holder revenue", value: `${fmtUsdCompact(st.net_dilution_usd_per_year)} a year` },
        { key: "staked", label: "Staked share of supply", sub: fin(st.nominal_staking_apr_current) ? `Nominal staking yield ${fmtPct(st.nominal_staking_apr_current, { decimals: 2 })}` : null, value: fmtPct(st.staked_supply_ratio, { decimals: 1 }) },
      ]
    : [];
  const regimeColumns: Column<RelativeValueStakingRegime>[] = [
    { key: "regime", header: "Issuance regime", render: (r) => <span className="text-ink">{REGIME_NAME[r.regime] ?? r.regime}</span> },
    { key: "infl", header: "Inflation", numeric: true, render: (r) => fmtPct(r.inflation_rate, { decimals: 1 }) },
    { key: "nom", header: "Staker yield, nominal", numeric: true, render: (r) => fmtPct(r.nominal_staking_apr, { decimals: 2 }) },
    { key: "real", header: "Staker yield, real incl. buyback", numeric: true, render: (r) => fmtPct(r.real_staking_apr_with_buyback, { decimals: 2 }) },
    { key: "non", header: "Non-staker, real", numeric: true, render: (r) => fmtPct(r.real_non_staker_apr, { decimals: 2, signed: true }) },
  ];

  return (
    <section id="relative-value" className="space-y-6">
      <SubHead title="Relative value">
        NEAR&apos;s multiples against the live peer set, ranked lowest first. This places NEAR among other L1s; it does not value the Intents cash flow.
      </SubHead>

      <div className="rounded-md border border-amber/30 bg-amber/5 px-4 py-3 text-[13.5px] leading-relaxed text-muted">
        <span className="font-medium text-amber">{`Only ${fmtInt(nPeers)} ${nPeers === 1 ? "peer" : "peers"}. `}</span>
        {/* field paths belong in the method note, not the body */}
        {data.caveat.replace(/\s*\([a-z_]+(\[\])?\.[a-z_.]+\)/g, "")}
      </div>

      <Panel className="valuo-scroll overflow-x-auto px-2 py-1">
        <div className="min-w-[50rem]">
          <Table<Row> columns={columns} rows={rows} rowKey={(r) => `${r.kind}-${r.slug}`} rowClassName={(r) => (r.kind === "near" ? "bg-surface-2/70" : undefined)} dense={false} emptyText="No peer multiples in this snapshot" />
        </div>
      </Panel>

      {data.findings?.length ? (
        <ul className="max-w-4xl list-disc space-y-1.5 pl-5 text-[14.5px] leading-relaxed text-muted marker:text-dim">
          {data.findings.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      ) : null}

      {bandRows.length ? (
        <div className="space-y-3">
          <h4 className="font-serif text-[19px] font-medium text-ink">Peer-multiple cross-check, not a fair value</h4>
          <p className="max-w-3xl text-[14px] leading-relaxed text-muted">
            NEAR&apos;s annualised cash flow times the peer multiple distribution{fin(bandCurrent) ? `, set against the ${fmtUsdCompact(bandCurrent)} market FDV` : ""}. With {fmtInt(nPeers)} peers the quartiles are reference points, and peer multiples carry each chain&apos;s monetary premium.
          </p>
          <Panel className="valuo-scroll overflow-x-auto px-2 py-1">
            <div className="min-w-[46rem]">
              <Table<BandRow> columns={bandColumns} rows={bandRows} rowKey={(r) => r.key} dense={false} />
            </div>
          </Panel>
        </div>
      ) : null}

      {st ? (
        <div className="space-y-3">
          <h4 className="font-serif text-[19px] font-medium text-ink">Staking and the security budget</h4>
          <div className="grid gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
            <Panel className="px-5 py-1">
              <FigureList items={stakingItems} />
            </Panel>
            <Panel className="valuo-scroll self-start overflow-x-auto px-2 py-1">
              <div className="min-w-[32rem]">
                <Table<RelativeValueStakingRegime> columns={regimeColumns} rows={st.regimes ?? []} rowKey={(r) => r.regime} dense={false} />
              </div>
            </Panel>
          </div>
        </div>
      ) : null}

      <MethodNote>
        <p>
          Basis: {data.basis}. Fields: <code>relative_value.peers[]</code>, <code>relative_value.near</code>, <code>relative_value.near_components[]</code>, <code>relative_value.coverage</code>. Run-rate multiples annualise the last 30 days; trailing-year multiples are in{" "}
          <code>fdv_to_fees_1y</code> / <code>fdv_to_revenue_1y</code>
          {cov.fdv_to_fees_1y && fin(cov.fdv_to_fees_1y.value) ? ` (NEAR ${mult(cov.fdv_to_fees_1y.value, { decimals: 0 })} on fees, ${rankText(cov.fdv_to_fees_1y) ?? NA})` : ""}
          {cov.fdv_to_revenue_1y && fin(cov.fdv_to_revenue_1y.value) ? `; ${mult(cov.fdv_to_revenue_1y.value, { decimals: 0 })} on revenue, ${rankText(cov.fdv_to_revenue_1y) ?? NA}` : ""}.
        </p>
        <p>Caveat as written by the pipeline: {data.caveat}</p>
        <p>
          Model terminal multiple {mult(data.model_terminal_multiple, { decimals: 0 })}; peers at or below it: {fmtInt(data.n_peers_at_or_below_model_multiple)} of {fmtInt(nPeers)} (<code>relative_value.model_terminal_multiple</code>).
        </p>
        {band ? (
          <p>
            Cross-check: {band.label}. {band.fees ? `Fees leg: ${band.fees.basis}.` : ""} {band.revenue ? `Revenue leg: ${band.revenue.basis}.` : ""} (<code>relative_value.implied_fdv_band</code>)
          </p>
        ) : null}
        {st ? (
          <p>
            Security budget: {st.basis}. Measured inflation {fmtPct(st.measured_inflation_rate, { decimals: 2 })}, NEAR at {fmtUsdCompact(st.near_price_usd)} (<code>relative_value.staking</code>).
          </p>
        ) : null}
      </MethodNote>
    </section>
  );
}
