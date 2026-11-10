import { Card } from "@/components/ui/Card";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { Stat } from "@/components/ui/Stat";
import { Table, type Column } from "@/components/ui/Table";
import { fmtInt, fmtNum, fmtPct, fmtUsdCompact } from "@/lib/format";
import { SERIES_COLORS } from "@/lib/theme";
import type { BacktestHorizonStats, BacktestRow, VolumeBacktest } from "@/lib/types";
import { TimeChart, type TimePoint } from "./TimeChart";

/**
 * Out-of-sample backtest of the SOTP volume engine (snapshot.backtest, quant/valuo/models/backtest.py).
 * At each monthly origin the model is re-calibrated on data up to that day only; each chart puts the
 * P10 to P90 band it drew for 30-day volume h months ahead against the 30-day volume that followed.
 * Values are plotted on a log10 scale because volume grew by three orders of magnitude over the sample.
 */

const log10 = (v: number) => (v > 0 ? Math.log10(v) : NaN);
const usdFromLog = (v: number) => fmtUsdCompact(10 ** v, { decimals: 0 });
const usdFromLog1 = (v: number) => fmtUsdCompact(10 ** v, { decimals: 1 });
const pct0 = (v: number | null | undefined) => fmtPct(v, { decimals: 0 });
const ratio = (v: number | null | undefined) => (typeof v === "number" && Number.isFinite(v) ? `${fmtNum(v, { decimals: 2 })}x` : "n/a");

function monthsLabel(h: string | number): string {
  return Number(h) === 1 ? "1 month" : `${h} months`;
}

function horizonChart(rows: BacktestRow[], h: number) {
  const rs = rows.filter((r) => r.h === h).sort((a, b) => a.target_date.localeCompare(b.target_date));
  const p = (f: (r: BacktestRow) => number): TimePoint[] => rs.map((r) => [r.target_date, log10(f(r))]);
  return { n: rs.length, misses: rs.filter((r) => !r.inside).length, realized: p((r) => r.realized_30d_usd), p50: p((r) => r.p50), p10: p((r) => r.p10), p90: p((r) => r.p90) };
}

type SummaryRow = { key: string; sample: string; h: string; s: BacktestHorizonStats };

function statRows(label: string, block: Record<string, BacktestHorizonStats> | undefined, prefix: string): SummaryRow[] {
  if (!block) return [];
  return Object.entries(block)
    .filter(([, s]) => s && s.n > 0)
    .map(([h, s]) => ({ key: `${prefix}-${h}`, sample: label, h, s }));
}

export function BacktestPanel({ backtest }: { backtest: VolumeBacktest | null | undefined }) {
  if (!backtest || !Array.isArray(backtest.rows) || backtest.rows.length === 0) {
    return (
      <section className="space-y-3">
        <SectionIntro eyebrow="Backtest" title="Volume model backtest not in this snapshot">
          <p>
            <code className="font-mono text-[12.5px] text-ink">snapshot.backtest</code> is missing or has no scored forecasts. Run <code className="font-mono text-[12.5px] text-ink">make reproduce</code> to compute it.
          </p>
        </SectionIntro>
      </section>
    );
  }
  const bt = backtest;
  const horizons = (bt.horizons_months ?? []).filter((h) => (bt.by_horizon[String(h)]?.n ?? 0) > 0);
  const s1 = bt.by_horizon["1"];
  const per = bt.calibrated?.per_horizon ?? {};

  const covText = horizons.map((h) => `${pct0(bt.by_horizon[String(h)]?.coverage_p10_p90)} at ${monthsLabel(h)}`);
  const title = covText.length
    ? `The volume model's P10 to P90 band held ${covText.slice(0, -1).join(", ")}${covText.length > 1 ? " and " : ""}${covText[covText.length - 1]} of realized 30-day volume, against 80% if calibrated`
    : "Volume model backtest";
  const r1 = s1?.median_ratio_realized_to_p50 ?? null;
  const direction = r1 === null ? "" : r1 > 1 ? "under-predicted" : r1 < 1 ? "over-predicted" : "matched";
  const period = bt.by_period;
  const e1 = period?.early?.["1"];
  const l1 = period?.late?.["1"];
  const md = bt.variants?.measured_drift?.by_horizon;

  const tableRows: SummaryRow[] = [
    ...statRows("All origins", bt.by_horizon, "all"),
    ...(period ? statRows(`Origins before ${period.split_origin_date}`, period.early, "early") : []),
    ...(period ? statRows(`Origins from ${period.split_origin_date}`, period.late, "late") : []),
    ...statRows("Variant: trailing measured drift", md, "md"),
  ];
  const columns: Column<SummaryRow>[] = [
    { key: "sample", header: "Sample", render: (r) => r.sample },
    { key: "h", header: "Horizon", className: "whitespace-nowrap", render: (r) => monthsLabel(r.h) },
    { key: "n", header: "n", numeric: true, render: (r) => fmtInt(r.s.n) },
    {
      key: "cov",
      header: "P10 to P90 coverage",
      numeric: true,
      render: (r) => (
        <>
          {pct0(r.s.coverage_p10_p90)}
          {r.s.coverage_ci90_wilson ? <span className="text-dim"> [{pct0(r.s.coverage_ci90_wilson[0])} to {pct0(r.s.coverage_ci90_wilson[1])}]</span> : null}
        </>
      ),
    },
    { key: "p", header: "Binomial p vs 80%", numeric: true, render: (r) => fmtNum(r.s.binom_p_vs_80, { decimals: 2 }) },
    { key: "miss", header: "Below P10 / above P90", numeric: true, render: (r) => `${fmtInt(r.s.below_p10)} / ${fmtInt(r.s.above_p90)}` },
    { key: "bias", header: "Realized / median", numeric: true, render: (r) => ratio(r.s.median_ratio_realized_to_p50) },
    { key: "pit", header: "PIT histogram (5 bins)", render: (r) => <span className="font-mono text-[12.5px]">{(r.s.pit_hist ?? []).join(" ")}</span> },
  ];

  return (
    <section className="space-y-6">
      <SectionIntro eyebrow="Backtest: volume engine, out of sample" title={title}>
        <p>
          {fmtInt(bt.n_origins)} monthly origins from {bt.first_origin} to {bt.last_origin}, each calibrated only on DefiLlama NEAR Intents daily volume up to that day ({bt.first_day} to {bt.last_day} in all).
          {r1 !== null ? ` One month ahead the model ${direction} volume: the median realized 30-day volume was ${ratio(r1)} the forecast median.` : ""}
          {e1 && l1 && e1.n > 0 && l1.n > 0 ? ` One-month coverage was ${pct0(e1.coverage_p10_p90)} for origins before ${period?.split_origin_date} and ${pct0(l1.coverage_p10_p90)} from it.` : ""}{" "}
          Only the volume distribution is tested; take rate, capture, confidential share and multiples are not.
        </p>
      </SectionIntro>

      <StatGrid cols={4}>
        {horizons.map((h) => {
          const s = bt.by_horizon[String(h)];
          const ok = per[String(h)];
          return (
            <Stat
              key={h}
              label={`P10 to P90 coverage, ${monthsLabel(h)} ahead`}
              value={s.coverage_p10_p90}
              format={(v) => fmtPct(v, { decimals: 0 })}
              tone={ok === true ? "emerald" : ok === false ? "crimson" : "neutral"}
              hint={`${fmtInt(s.inside ?? 0)} of ${fmtInt(s.n)} inside; ${ok === true ? "80% not rejected" : ok === false ? "80% rejected" : "untested"} (p ${fmtNum(s.binom_p_vs_80, { decimals: 2 })})`}
            />
          );
        })}
        <Stat
          label="Realized / forecast median, 1 month"
          value={r1}
          format={(v) => ratio(v)}
          tone={r1 !== null && Math.abs(Math.log(r1)) > 0.25 ? "amber" : "neutral"}
          hint={horizons
            .filter((h) => h !== 1)
            .map((h) => `${monthsLabel(h)} ${ratio(bt.by_horizon[String(h)]?.median_ratio_realized_to_p50)}`)
            .join("; ") || undefined}
        />
      </StatGrid>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-3">
        {horizons.map((h) => {
          const c = horizonChart(bt.rows, h);
          return (
            <Card
              key={h}
              kicker={`${monthsLabel(h)} ahead`}
              title={`Forecast band vs realized, ${monthsLabel(h)}`}
              subtitle="30-day NEAR Intents volume at each target date, log scale. Shaded: the P10 to P90 band drawn at the origin; dashed: its median."
              footer={`${fmtInt(c.n)} forecasts; ${fmtInt(c.misses)} outside the band.`}
            >
              <TimeChart
                title={`Volume backtest, ${monthsLabel(h)} ahead`}
                series={[
                  { name: "Realized", points: c.realized, color: SERIES_COLORS[1] },
                  { name: "Median", points: c.p50, color: SERIES_COLORS[0], dashed: true },
                ]}
                band={{ name: "P10 to P90 forecast", lo: c.p10, hi: c.p90, color: SERIES_COLORS[0] }}
                yFormat={usdFromLog}
                valueFormat={usdFromLog1}
                width={420}
                height={260}
              />
            </Card>
          );
        })}
      </div>

      <Table columns={columns} rows={tableRows} rowKey={(r) => r.key} caption="Coverage, bias and PIT counts per horizon. A calibrated model puts about 80% inside the band and a flat PIT histogram." stickyHeader={false} />

      <MethodNote summary="Backtest method: what was and was not tested">
        <p>
          Origins every {fmtInt(bt.step_days)} days, anchored at the last complete day of <code>{bt.source}</code>
          {bt.source_sha256 ? (
            <>
              {" "}
              (SHA-256 <code>{bt.source_sha256.slice(0, 16)}...</code>, the same payload recorded in <code>artifacts/manifest.json</code>)
            </>
          ) : null}
          . At each origin the live calibration is rerun on the days up to the origin only: starting volume is the trailing {fmtInt(bt.window_days)}-day sum; the monthly volume sigma comes from{" "}
          <code>intents_forensics.volume_volatility</code> over the trailing {fmtInt(bt.sigma_lookback_days)} days through <code>sotp_valuation._sigmas</code>; the drift is the run&apos;s labeled{" "}
          <code>public_volume_growth_yoy</code> ({pct0(bt.growth_yoy_used)} a year) with the Ito correction of <code>simulate_paths</code>. The 30-day volume h months ahead is lognormal under that GBM, so the P10, P50 and
          P90 are closed-form (a unit test checks them against <code>simulate_paths</code> with seed 20261114). The realized value is the 30-day sum ending round(h x 30.44) days after the origin.
        </p>
        <p>
          Grading: {bt.calibrated?.rule}. PIT is the forecast CDF at the realized value; a calibrated model gives a flat histogram, a pile-up in the top bin means realized volume ran above the forecast. The measured-drift variant
          replaces the registry growth (chosen with the whole history in view) with the trailing mean monthly log return at each origin, so it has no look-ahead.
        </p>
        <p>Not tested: {(bt.not_tested ?? []).join("; ")}.</p>
        {(bt.caveats ?? []).map((c) => (
          <p key={c}>{c}</p>
        ))}
      </MethodNote>
    </section>
  );
}
