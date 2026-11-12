import type { ReactNode } from "react";
import { LineChart, type LineSeries } from "@/components/charts";
import { Card, Stat, Table, type Column } from "@/components/ui";
import { MethodNote, StatGrid } from "@/components/ui/Section";
import { fmtBps, fmtInt, fmtNum, fmtPctPoints, fmtUsdCompact } from "@/lib/format";
import {
  takeRateColumn,
  type TakeRateElasticity,
  type TakeRateSeries as TakeRateSeriesData,
  type TakeRateTrend,
  type TakeRateWindow,
} from "@/lib/takeRateSeries";
import { COLORS, SERIES_COLORS, type Tone } from "@/lib/theme";

export interface TakeRateSeriesProps {
  /** `snapshot.take_rate_series`; absent from snapshots written before the model landed */
  data: TakeRateSeriesData | null | undefined;
}

const bps = (v: number | null | undefined, decimals = 1) => fmtBps(v, { signed: false, decimals });
const perYear = (v: number | null | undefined) => fmtPctPoints(v, { signed: true, decimals: 1 });

function ciText(ci: [number, number] | null | undefined): string {
  return ci ? `${perYear(ci[0])} to ${perYear(ci[1])}` : "n/a";
}

function monthLabel(tsUnixS: number): string {
  return new Date(tsUnixS * 1000).toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}

/**
 * The model writes the headline as "verdict: numbers". The verdict is the section title and the
 * numbers are the lede; a headline without that separator is shown whole as the title.
 */
export function splitHeadline(headline: string): { title: string; detail: string | null } {
  const i = headline.indexOf(": ");
  if (i < 0) return { title: headline.replace(/\.$/, ""), detail: null };
  const rest = headline.slice(i + 2);
  return { title: headline.slice(0, i), detail: rest.charAt(0).toUpperCase() + rest.slice(1) };
}

/** Red only when the interval sits wholly below zero, green only when wholly above. */
function trendTone(t: TakeRateTrend | null | undefined): Tone {
  if (!t || t.status !== "measured" || !t.ci_excludes_zero || t.change_per_year_pct == null) return "neutral";
  return t.change_per_year_pct < 0 ? "crimson" : "emerald";
}

function trendHint(t: TakeRateTrend | null | undefined): ReactNode {
  if (!t) return "not measured";
  if (t.status !== "measured") return t.note ?? "too few points";
  return `90% CI ${ciText(t.ci90_pct)}, ${t.ci_excludes_zero ? "excludes" : "includes"} zero`;
}

function elasticityHint(e: TakeRateElasticity | null | undefined): ReactNode {
  if (!e) return "not measured";
  if (e.status !== "measured") return e.note ?? "too few days";
  const ci = e.ci90 ? `${fmtNum(e.ci90[0], { signed: true })} to ${fmtNum(e.ci90[1], { signed: true })}` : "n/a";
  return `90% CI ${ci}, ${e.ci_excludes_zero ? "excludes" : "includes"} zero; R2 ${fmtNum(e.r2, { decimals: 3 })}`;
}

function Line({ label, children }: { label: string; children: ReactNode }) {
  return (
    <li className="leading-relaxed">
      <span className="text-ink">{label}.</span> {children}
    </li>
  );
}

/**
 * Execution tab section: has the realized take rate (fees / volume) compressed as volume grew?
 * Rolling 30-day gross and holder take on one bps axis, the window table, the trend and
 * elasticity estimates with their intervals, and the limits of the method.
 */
export function TakeRateSeries({ data }: TakeRateSeriesProps) {
  if (!data || data.status !== "measured" || !data.series?.length || !data.latest) return null;

  const iTs = takeRateColumn(data, "ts_unix_s");
  const iGross = takeRateColumn(data, "gross_take_bps");
  const iHolder = takeRateColumn(data, "holder_take_bps");
  if (iTs < 0 || iGross < 0) return null;

  const { title, detail } = splitHeadline(data.headline);
  const xs = data.series.map((r) => r[iTs] as number);
  const num = (v: number | null | undefined) => (typeof v === "number" ? v : Number.NaN);
  const floor = data.floor_read;
  const rb = data.regime_break;
  const trend = data.trend;
  const t365 = trend.trailing_365d;
  const t180 = trend.trailing_180d;
  const tFull = trend.full_history;
  const blk = trend.block_check_365d;
  const e365 = data.elasticity.trailing_365d;
  const eFull = data.elasticity.full_history;
  const latest = data.latest;
  const ago = data.year_ago;
  const range = data.range_trailing_365d;
  const n = data.rolling_window_days;
  const pre = rb?.before_trailing_365d ?? rb?.before ?? null;
  // The full-history line is only worth a row when it covers more than the trailing year.
  const longerHistory = (tFull?.n_points ?? 0) > (t365?.n_points ?? 0);
  // A series that starts far below where it ends is the fee switch-on, not a pricing trend.
  const feeRamp = tFull?.start_bps != null && tFull.end_bps != null && tFull.start_bps < 0.25 * tFull.end_bps;
  // The chart's own finding: the level a year apart and the range in between.
  const chartTitle = ago
    ? `Rolling ${n}-day gross take went from ${bps(ago.gross_take_bps)} to ${bps(latest.gross_take_bps)} in ${fmtInt(ago.days_before_latest)} days` +
      (range?.gross_min && range.gross_max ? `, inside a ${bps(range.gross_min.bps)} to ${bps(range.gross_max.bps)} range` : "")
    : `Rolling ${n}-day gross take is ${bps(latest.gross_take_bps)} on ${latest.date}`;

  const series: LineSeries[] = [{ name: `Gross take, rolling ${n}d`, values: data.series.map((r) => num(r[iGross])), color: SERIES_COLORS[0], strokeWidth: 2 }];
  if (data.holders_available && iHolder >= 0) {
    series.push({ name: `Holder take, rolling ${n}d`, values: data.series.map((r) => num(r[iHolder])), color: SERIES_COLORS[1] });
  }
  if (floor) {
    series.push({ name: `Model floor, ${bps(floor.public_take_floor_bps, 2)}`, values: xs.map(() => floor.public_take_floor_bps), color: COLORS.dim, dashed: true });
  }

  const columns: Column<TakeRateWindow>[] = [
    { key: "label", header: "Window", render: (w) => <span className="whitespace-nowrap text-ink">{w.label}</span> },
    {
      key: "days",
      header: "Days (UTC)",
      render: (w) => <span className="tnum whitespace-nowrap text-muted">{w.n_days && w.start_date && w.end_date ? `${w.start_date} to ${w.end_date}` : "n/a"}</span>,
    },
    { key: "gross", header: "Gross take", numeric: true, render: (w) => bps(w.gross_take_bps, 2) },
    { key: "net", header: "Net take", numeric: true, title: "Revenue swept to NEAR's wallets over volume", render: (w) => bps(w.net_take_bps, 2) },
    { key: "holder", header: "Holder take", numeric: true, title: "Buyback (holders revenue) over volume", render: (w) => bps(w.holder_take_bps, 2) },
    { key: "volume", header: "Avg daily volume", numeric: true, render: (w) => fmtUsdCompact(w.avg_daily_volume_usd) },
  ];

  return (
    <section className="space-y-6">
      <div className="max-w-3xl">
        <div className="mb-2 text-[13px] text-dim">Take-rate history</div>
        <h3 className="font-serif text-[24px] font-medium leading-tight text-ink">{title}</h3>
        {detail ? <p className="tnum mt-2 text-[15px] leading-relaxed text-muted">{detail}</p> : null}
      </div>

      <StatGrid cols={4}>
        <Stat
          label={`Gross take, rolling ${n}d`}
          value={bps(latest.gross_take_bps, 2)}
          hint={ago ? `${bps(ago.gross_take_bps, 2)} on ${ago.date}; window ends ${latest.date}` : `window ends ${latest.date}`}
        />
        <Stat
          label="Trend, trailing 365d"
          value={t365?.status === "measured" ? perYear(t365.change_per_year_pct) : null}
          unit="per year"
          tone={trendTone(t365)}
          hint={trendHint(t365)}
        />
        <Stat
          label="Trend, trailing 180d"
          value={t180?.status === "measured" ? perYear(t180.change_per_year_pct) : null}
          unit="per year"
          tone={trendTone(t180)}
          hint={trendHint(t180)}
        />
        <Stat
          label="Elasticity to volume, 365d"
          value={e365?.status === "measured" ? fmtNum(e365.elasticity, { signed: true }) : null}
          hint={elasticityHint(e365)}
        />
      </StatGrid>

      <Card
        title={chartTitle}
        subtitle={`Rolling ${n}-day take in bps of volume, ${data.first_day} to ${data.last_day} (UTC); each point pools ${n} settled days and is dated by its last day`}
      >
        <LineChart
          title={chartTitle}
          description={`Rolling ${n}-day gross and holder take rate of NEAR Intents in basis points of volume, with the model floor on the gross take`}
          series={series}
          x={xs}
          xFormat={monthLabel}
          yFormat={(v) => fmtNum(v, { decimals: v % 1 === 0 ? 0 : 1 })}
          markers={rb?.ts_unix_s && rb.date ? [{ x: rb.ts_unix_s, label: `Buyback from ${rb.date}`, color: COLORS.muted }] : []}
          yTicks={6}
          width={720}
          height={300}
          margin={{ left: 40, right: 12 }}
          pointLimit={0}
        />
        <p className="tnum mt-2 text-[12.5px] leading-snug text-dim">
          Y axis: bps of volume.
          {range?.gross_max && range.gross_min
            ? ` Trailing-year gross range ${bps(range.gross_min.bps)} (${range.gross_min.date}) to ${bps(range.gross_max.bps)} (${range.gross_max.date}).`
            : ""}
          {data.holders_available ? "" : " Holder take is not drawn: the holders-revenue chart was not available to this run."}
        </p>
      </Card>

      <Card title="Take rate by window" subtitle="Pooled over each block: sum of fees over sum of volume" padded={false}>
        <Table columns={columns} rows={data.windows} rowKey={(w) => w.label} stickyHeader={false} className="tnum" />
      </Card>

      <ul className="tnum max-w-3xl space-y-2 text-[14px] text-muted">
        {blk?.status === "measured" ? (
          <Line label="Stricter check">
            {fmtInt(blk.n_blocks)} non-overlapping {n}-day windows give {perYear(blk.change_per_year_pct)} per year, Student-t 90% CI {ciText(blk.ci90_pct)} (
            {blk.ci_excludes_zero ? "excludes" : "includes"} zero). {trend.block_check_agrees === false ? "It does not confirm the overlapping-point trend." : ""}
          </Line>
        ) : null}
        {tFull?.status === "measured" && longerHistory ? (
          <Line label="Full history">
            {perYear(tFull.change_per_year_pct)} per year, 90% CI {ciText(tFull.ci90_pct)}, over {fmtInt(tFull.n_points)} rolling points from {tFull.first_day}.
            {feeRamp
              ? ` The series starts at ${bps(tFull.start_bps, 2)}, so this measures fees being switched on, not competition${
                  eFull?.status === "measured" ? `; the full-history elasticity of ${fmtNum(eFull.elasticity, { signed: true })} carries the same ramp` : ""
                }.`
              : ""}
          </Line>
        ) : null}
        {rb?.date && rb.after ? (
          <Line label="Regime break">
            Holders revenue first appears on {rb.date}. Pooled gross take is {bps(pre?.gross_take_bps, 2)} over the {fmtInt(pre?.n_days)} days before it
            {rb.before_trailing_365d ? " that fall inside the trailing year" : ""} and {bps(rb.after.gross_take_bps, 2)} over the {fmtInt(rb.after.n_days)} days since; net take{" "}
            {bps(pre?.net_take_bps, 2)} before and {bps(rb.after.net_take_bps, 2)} since.
          </Line>
        ) : rb?.note ? (
          <Line label="Regime break">Not identified: {rb.note}.</Line>
        ) : null}
        {floor ? (
          <Line label="Floor read">
            Gross take sat below the {bps(floor.public_take_floor_bps, 2)} model floor on {fmtInt(floor.gross_below_floor)} of {fmtInt(floor.n_points)} trailing rolling points
            {floor.min_gross ? ` (minimum ${bps(floor.min_gross.bps, 2)}, ${floor.min_gross.date})` : ""}. Net take sat below the {bps(floor.bear_fee_race_trigger_net_take_bps, 2)}{" "}
            bear-case fee-race trigger on {fmtInt(floor.net_below_trigger)} of them
            {floor.since_regime_break ? `, and on ${fmtInt(floor.since_regime_break.net_below_trigger)} of the ${fmtInt(floor.since_regime_break.n_points)} windows that start after the break` : ""}.
          </Line>
        ) : null}
      </ul>

      {data.investor_read ? (
        <p className="tnum max-w-3xl border-l-2 border-border-strong pl-4 text-[15px] leading-relaxed text-ink">{data.investor_read}</p>
      ) : null}

      <MethodNote>
        <p>
          <span className="text-ink">Method.</span> {data.method} Snapshot field <code>take_rate_series</code>.
        </p>
        <p>
          <span className="text-ink">Data.</span> {fmtInt(data.n_days)} aligned settled days, {data.first_day} to {data.last_day}; {fmtInt(data.n_rolling_points)} rolling points;{" "}
          {data.excluded_unsettled_days.length ? `unsettled trailing day(s) excluded: ${data.excluded_unsettled_days.join(", ")}` : "no unsettled trailing day"}
          {data.n_gaps ? `; ${fmtInt(data.n_gaps)} calendar gap(s), windows spanning a gap are skipped` : ""}.
          {data.source_mode === "snapshot_fallback" ? " Built from the series stored in the snapshot, not the raw payloads." : ""}
        </p>
        <p>
          <span className="text-ink">Sources.</span>{" "}
          {data.sources.map((s, i) => (
            <span key={s.record}>
              {i ? "; " : ""}
              <code>{s.record}</code>
              {s.sha256 ? ` sha256 ${s.sha256.slice(0, 12)}` : ""}
            </span>
          ))}
          .
        </p>
        {trend.lag_sensitivity_365d?.length ? (
          <p>
            <span className="text-ink">Lag sensitivity, trailing 365d.</span>{" "}
            {trend.lag_sensitivity_365d.map((l) => `${l.hac_lag_days}-day lag ${ciText(l.ci90_pct)}`).join("; ")}; graded interval uses {t365?.hac_lag_days ?? "n/a"} days.
          </p>
        ) : null}
        {data.caveats.map((c, i) => (
          <p key={i}>
            <span className="text-ink">Limit {i + 1}.</span> {c}
          </p>
        ))}
        {data.data_warnings.map((w, i) => (
          <p key={`w${i}`}>
            <span className="text-ink">Data warning.</span> {w}
          </p>
        ))}
      </MethodNote>
    </section>
  );
}
