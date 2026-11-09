import { Card, Table, type Column } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { fmtInt, fmtMonth, fmtNearCompact, fmtPct, fmtUsd, fmtUsdCompact } from "@/lib/format";
import { PERCENTILE_KEYS, REGIME_KEYS, type CrossoverRegimeStats, type PercentileKey, type RegimeKey, type SotpValuation } from "@/lib/types";
import { REGIME_NAME } from "./fmt";

type PctRow = { key: PercentileKey; fdv: number | null; price: number | null; ex: number | null };
type XRow = { regime: RegimeKey; stats: CrossoverRegimeStats | null };

const pctS = (v: number | null) => fmtPct(v, { decimals: 1, signed: true });

function Signed({ v }: { v: number | null }) {
  if (v === null || !Number.isFinite(v)) return <span className="text-dim">n/a</span>;
  return <span className={v >= 0 ? "text-emerald" : "text-crimson"}>{pctS(v)}</span>;
}

/** Percentiles of FDV, implied price and FDV ex-monetary over paths, plus the crossover-month distribution per regime. */
export function PercentileTable({ sotp }: { sotp: SotpValuation }) {
  const cal = sotp.calibration;
  const current = sotp.current_fdv_usd;
  const spot = cal?.price_usd;
  const H = sotp.horizon_months;
  const rows: PctRow[] = PERCENTILE_KEYS.map((k) => ({
    key: k,
    fdv: sotp.fdv_percentiles?.[k] ?? null,
    price: sotp.price_percentiles?.[k] ?? null,
    ex: sotp.fdv_ex_monetary_percentiles?.[k] ?? null,
  }));
  const pctColumns: Column<PctRow>[] = [
    { key: "key", header: "Percentile", render: (r) => <span className="font-medium text-ink">{r.key.toUpperCase()}</span>, width: "6rem" },
    { key: "fdv", header: "FDV", numeric: true, render: (r) => <span className="text-ink">{fmtUsdCompact(r.fdv)}</span> },
    { key: "vs", header: "vs current FDV", numeric: true, render: (r) => <Signed v={r.fdv !== null && current > 0 ? r.fdv / current - 1 : null} /> },
    { key: "price", header: `Price at M${fmtInt(H)}`, numeric: true, render: (r) => fmtUsd(r.price, { decimals: 3 }) },
    { key: "vsSpot", header: "vs spot", numeric: true, render: (r) => <Signed v={r.price !== null && spot ? r.price / spot - 1 : null} /> },
    { key: "ex", header: "FDV excl. Engine 3", numeric: true, render: (r) => fmtUsdCompact(r.ex) },
  ];

  const x = sotp.crossover_month_distribution;
  const xRows: XRow[] = REGIME_KEYS.map((regime) => ({ regime, stats: x?.[regime] ?? null }));
  const xColumns: Column<XRow>[] = [
    { key: "regime", header: "Issuance schedule", render: (r) => <span className="text-ink">{REGIME_NAME[r.regime] ?? r.regime}</span> },
    { key: "p", header: `Crosses within ${fmtInt(H)} months`, numeric: true, render: (r) => <span className="text-ink">{fmtPct(r.stats?.p_crossover_within_36m, { decimals: 1 })}</span> },
    { key: "m50", header: "Median month", numeric: true, render: (r) => fmtMonth(r.stats?.p50_month, { na: "n/a" }) },
    { key: "range", header: "P10 to P90 month", numeric: true, render: (r) => `${fmtMonth(r.stats?.p10_month, { na: "n/a" })} to ${fmtMonth(r.stats?.p90_month, { na: "n/a" })}` },
    { key: "ph", header: `Deflationary at M${fmtInt(H)}`, numeric: true, render: (r) => fmtPct(r.stats?.p_deflationary_at_horizon, { decimals: 1 }) },
    { key: "med", header: "Median net float change", numeric: true, render: (r) => fmtNearCompact(r.stats?.median_cum_net_float_change_near, { signed: true }) },
  ];

  return (
    <Card title="Percentiles across paths" subtitle={`FDV and implied price at each percentile, against today's ${fmtUsdCompact(current)} FDV and ${fmtUsd(spot)} spot price.`}>
      <div className="space-y-8">
        <Table<PctRow> columns={pctColumns} rows={rows} rowKey={(r) => r.key} rowClassName={(r) => (r.key === "p50" ? "bg-surface-2/60" : undefined)} />
        <div className="min-w-0">
          <h3 className="mb-2 text-[14px] font-medium text-ink">When does net supply stop growing?</h3>
          <Table<XRow> columns={xColumns} rows={xRows} rowKey={(r) => r.regime} />
          <p className="mt-2 text-[12.5px] leading-snug text-muted">
            Share of paths on which monthly issuance falls below buybacks, gas burn and state lock combined. Expected path: {fmtMonth(x?.deterministic_crossover_month)}.
          </p>
        </div>
      </div>
      <MethodNote className="mt-6">
        <p>
          Implied price = FDV / supply at M{fmtInt(H)} under the SVRN glidepath ({fmtNearCompact(cal?.supply_at_horizon_used)}). FDV excluding Engine 3 sums Engines 1 and 2 per path. The Monte Carlo mean FDV ({fmtUsdCompact(cal?.mc_mean_fdv)}) exceeds the P50 by lognormal convexity and is not a base case.
        </p>
        {x ? (
          <p>
            Crossover: {x.basis}. {x.note} Paths crossed: {REGIME_KEYS.map((k) => `${REGIME_NAME[k] ?? k} ${fmtInt(x[k]?.n_paths_crossed)}`).join(", ")}. Median net float change is the median over paths of the {fmtInt(H)}-month sum; positive means net dilution.
          </p>
        ) : (
          <p>The crossover-month distribution is absent from this snapshot.</p>
        )}
        <p>
          Fields: <code>sotp.fdv_percentiles</code>, <code>sotp.price_percentiles</code>, <code>sotp.fdv_ex_monetary_percentiles</code>, <code>sotp.crossover_month_distribution</code>, <code>sotp.calibration.supply_at_horizon_used</code>.
        </p>
      </MethodNote>
    </Card>
  );
}
