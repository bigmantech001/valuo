import { Card } from "@/components/ui/Card";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { Stat } from "@/components/ui/Stat";
import { Table, type Column } from "@/components/ui/Table";
import { fmtInt, fmtNum, fmtPct, fmtUsdCompact } from "@/lib/format";
import { SERIES_COLORS } from "@/lib/theme";
import type { BacktestHorizonStats, BacktestRow, VolumeBacktest, VolumeEngineScore } from "@/lib/types";
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

type Triple = { p10: number; p50: number; p90: number };
type EngineRow = { key: string; h: number; g: BacktestHorizonStats | undefined; b: BacktestHorizonStats | undefined; gOk: boolean | null | undefined; bOk: boolean | null | undefined; width: number | null | undefined };
type EffectRow = { key: string; measure: string; engine: string; t: Triple; fmt: (v: number) => string };

const pval = (v: number | null | undefined) => (typeof v === "number" && v < 0.005 ? "<0.01" : fmtNum(v, { decimals: 2 }));
const insideText = (s: BacktestHorizonStats | undefined) => (s && s.n > 0 ? `${fmtInt(s.inside ?? 0)} of ${fmtInt(s.n)} (${pct0(s.coverage_p10_p90)})` : "n/a");

function verdictCell(s: BacktestHorizonStats | undefined, ok: boolean | null | undefined, target: number) {
  if (!s || s.n === 0 || ok === null || ok === undefined) return <span className="text-dim">untested</span>;
  if (ok) return <span className="text-emerald">not rejected</span>;
  return <span className="text-crimson">rejected, band too {(s.coverage_p10_p90 ?? 0) > target ? "wide" : "narrow"}</span>;
}

function rejectedCount(e: VolumeEngineScore, hs: number[]): number {
  return hs.filter((h) => e.calibrated?.per_horizon?.[String(h)] === false).length;
}

function coverageLine(e: VolumeEngineScore | undefined, hs: number[]): string | null {
  if (!e) return null;
  const parts = hs.filter((h) => (e.by_horizon?.[String(h)]?.n ?? 0) > 0).map((h) => `${monthsLabel(h)} ${insideText(e.by_horizon[String(h)])}, p ${pval(e.by_horizon[String(h)]?.binom_p_vs_80)}`);
  return parts.length ? parts.join("; ") : null;
}

/**
 * Second volume engine (stationary block bootstrap) scored on the same origins as the GBM, plus what swapping it into the
 * valuation would do. Rendered only when snapshot.backtest.engines is present; the valuation itself stays on the GBM.
 */
function EngineComparison({ bt, horizons }: { bt: VolumeBacktest; horizons: number[] }) {
  const eng = bt.engines;
  if (!eng?.gbm?.by_horizon || !eng.block_bootstrap?.by_horizon) return null;
  const { gbm, block_bootstrap: boot } = eng;
  const cmp = bt.comparison;
  const target = eng.target_coverage ?? bt.target_coverage ?? 0.8;
  const hs = horizons.filter((h) => (boot.by_horizon[String(h)]?.n ?? 0) > 0);
  if (hs.length === 0) return null;

  const rows: EngineRow[] = hs.map((h) => ({
    key: String(h),
    h,
    g: gbm.by_horizon[String(h)],
    b: boot.by_horizon[String(h)],
    gOk: gbm.calibrated?.per_horizon?.[String(h)],
    bOk: boot.calibrated?.per_horizon?.[String(h)],
    width: cmp?.per_horizon?.[String(h)]?.band_width_ratio_bootstrap_to_gbm,
  }));
  const columns: Column<EngineRow>[] = [
    { key: "h", header: "Horizon", className: "whitespace-nowrap", render: (r) => monthsLabel(r.h) },
    { key: "g-in", header: "GBM: inside band", numeric: true, className: "whitespace-nowrap", render: (r) => insideText(r.g) },
    { key: "g-p", header: `GBM: p vs ${pct0(target)}`, numeric: true, render: (r) => pval(r.g?.binom_p_vs_80) },
    { key: "g-v", header: "GBM: verdict", render: (r) => verdictCell(r.g, r.gOk, target) },
    { key: "b-in", header: "Bootstrap: inside band", numeric: true, className: "whitespace-nowrap", render: (r) => insideText(r.b) },
    { key: "b-p", header: `Bootstrap: p vs ${pct0(target)}`, numeric: true, render: (r) => pval(r.b?.binom_p_vs_80) },
    { key: "b-v", header: "Bootstrap: verdict", render: (r) => verdictCell(r.b, r.bOk, target) },
    { key: "b-bias", header: "Bootstrap: realized / median", numeric: true, render: (r) => ratio(r.b?.median_ratio_realized_to_p50) },
    { key: "w", header: "Band width, bootstrap / GBM", numeric: true, title: "Ratio of the median ln(P90 / P10) of the two engines", render: (r) => (typeof r.width === "number" ? `${fmtNum(r.width, { decimals: 1 })}x` : "n/a") },
  ];

  const nb = rejectedCount(boot, hs);
  const ng = rejectedCount(gbm, hs);
  const title =
    nb === 0
      ? `The block bootstrap's coverage is not rejected at any of ${fmtInt(hs.length)} horizons; the GBM's is rejected at ${fmtInt(ng)}`
      : `Coverage against ${pct0(target)}: block bootstrap rejected at ${fmtInt(nb)} of ${fmtInt(hs.length)} horizons, GBM at ${fmtInt(ng)} of ${fmtInt(hs.length)}`;
  const registry = coverageLine(boot.variants?.registry_drift, hs);
  const thumb = coverageLine(boot.variants?.rule_of_thumb_blocks, hs);
  const power = cmp?.power_1m;

  const ve = bt.valuation_effect;
  const vol = ve?.volume_12m;
  const fdv = ve?.fdv?.computed ? ve.fdv : null;
  const multiple = (v: number) => `${fmtNum(v, { decimals: 2 })}x`;
  const usd = (v: number) => fmtUsdCompact(v);
  const volMeasure = vol ? `30-day volume in ${fmtInt(vol.horizon_months)} months, multiple of today's` : "";
  const fdvMeasure = fdv ? `Model FDV${fdv.horizon_months ? `, ${fmtInt(fdv.horizon_months)}-month run` : ""}` : "";
  const effectRows: EffectRow[] = [
    ...(vol?.gbm ? [{ key: "v-g", measure: volMeasure, engine: "GBM (used by the valuation)", t: vol.gbm, fmt: multiple }] : []),
    ...(vol?.block_bootstrap_registry_drift ? [{ key: "v-br", measure: volMeasure, engine: "Block bootstrap, same expected path", t: vol.block_bootstrap_registry_drift, fmt: multiple }] : []),
    ...(vol?.block_bootstrap_resampled_drift ? [{ key: "v-bs", measure: volMeasure, engine: "Block bootstrap, resampled drift", t: vol.block_bootstrap_resampled_drift, fmt: multiple }] : []),
    ...(fdv?.gbm ? [{ key: "f-g", measure: fdvMeasure, engine: "GBM (used by the valuation)", t: fdv.gbm, fmt: usd }] : []),
    ...(fdv?.block_bootstrap ? [{ key: "f-b", measure: fdvMeasure, engine: "Block bootstrap, same expected path", t: fdv.block_bootstrap, fmt: usd }] : []),
  ];
  const effectColumns: Column<EffectRow>[] = [
    { key: "measure", header: "Measure", render: (r) => r.measure },
    { key: "engine", header: "Volume engine", render: (r) => r.engine },
    { key: "p10", header: "P10", numeric: true, render: (r) => r.fmt(r.t.p10) },
    { key: "p50", header: "P50", numeric: true, render: (r) => r.fmt(r.t.p50) },
    { key: "p90", header: "P90", numeric: true, render: (r) => r.fmt(r.t.p90) },
  ];

  return (
    <Card
      kicker="Second engine, same out-of-sample test"
      title={title}
      subtitle={`Stationary block bootstrap of realized daily log-changes (${fmtInt(boot.n_paths)} paths, seed ${boot.seed}), scored on the same origins and realized values as the GBM. It is reported next to the base case; the valuation does not use it.`}
    >
      <div className="space-y-4">
        {cmp?.headline ? <p className="max-w-4xl text-[13.5px] leading-relaxed text-ink">{cmp.headline}</p> : null}
        <Table columns={columns} rows={rows} rowKey={(r) => r.key} caption={`P10 to P90 coverage per horizon against the ${pct0(target)} target, exact two-sided binomial test. Both engines are scored on the same forecasts.`} stickyHeader={false} />
        {registry || thumb || power ? (
          <div className="max-w-4xl space-y-1.5 text-[13px] leading-relaxed text-muted">
            {registry ? <p>Bootstrap shape at the GBM&apos;s expected path: {registry}.</p> : null}
            {thumb ? <p>Sensitivity, cube-root block length: {thumb}.</p> : null}
            {power ? (
              <p>
                Power: with {fmtInt(power.n)} one-month forecasts the test accepts {fmtInt(power.accept_min)} to {fmtInt(power.accept_max)} inside. An engine whose true coverage is 60% is rejected {pct0(power.reject_prob_if_true_60)} of the time and one at 70%{" "}
                {pct0(power.reject_prob_if_true_70)} of the time, so a pass on this sample is weak evidence.
              </p>
            ) : null}
          </div>
        ) : null}
        {effectRows.length ? (
          <Table
            columns={effectColumns}
            rows={effectRows}
            rowKey={(r) => r.key}
            caption={`What the engine choice does to the valuation inputs${vol ? `, from the ${vol.origin_date} origin` : ""}. Headline figures use the GBM rows.`}
            stickyHeader={false}
          />
        ) : null}
        {ve?.headline ? <p className="max-w-4xl text-[13.5px] leading-relaxed text-ink">{ve.headline}</p> : null}
        {ve?.fdv && !ve.fdv.computed ? <p className="text-[13px] text-muted">FDV under the bootstrap was not computed{ve.fdv.reason ? `: ${ve.fdv.reason}` : ""}.</p> : null}
      </div>
      <MethodNote className="mt-5" summary="Block bootstrap: rule, limits and what was not tuned">
        <p>{boot.method}</p>
        <p>
          Block length rule <code>{boot.block_length_rule}</code>, fixed before any coverage was computed
          {boot.mean_block_days ? `; mean block ${fmtNum(boot.mean_block_days.min, { decimals: 1 })} to ${fmtNum(boot.mean_block_days.max, { decimals: 1 })} days across origins (median ${fmtNum(boot.mean_block_days.median, { decimals: 1 })})` : ""}. Lookback{" "}
          {fmtInt(boot.lookback_days)} days, the same window the GBM sigma uses. Grading: {boot.calibrated?.rule}
        </p>
        {(boot.caveats ?? []).map((c) => (
          <p key={c}>{c}</p>
        ))}
      </MethodNote>
    </Card>
  );
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

      <EngineComparison bt={bt} horizons={horizons} />

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
