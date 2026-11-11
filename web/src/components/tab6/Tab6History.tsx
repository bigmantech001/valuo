import { Stat } from "@/components/ui/Stat";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { EmptyState } from "@/components/ui/EmptyState";
import { ARCHETYPE_LABELS } from "@/lib/corridors";
import { fmtBps, fmtInt, fmtPct, fmtUsdCompact, fmtUtc } from "@/lib/format";
import { anchorAccount, type HistoryLoad, type SeriesBlock, type SeriesStats } from "@/lib/history";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import type { CorridorArchetype, Snapshot } from "@/lib/types";
import { BacktestPanel } from "./BacktestPanel";
import { fmtDay, fmtSpan, plural, spanMs, statsOf, type WorkflowSchedule } from "./derive";
import { HistoryChartCard, type RunCount } from "./HistoryChartCard";
import { RaceCellTable } from "./RaceCellTable";
import { RouteWinLossTable } from "./RouteWinLossTable";
import type { TimePoint, TimeSeries } from "./TimeChart";
import { TriggerHistoryTable } from "./TriggerHistoryTable";

export interface Tab6Props {
  history: HistoryLoad;
  snapshot: Snapshot | null;
  schedules: { snapshot?: WorkflowSchedule; bench?: WorkflowSchedule };
}

const ARCH_ORDER: readonly string[] = ["cross_vm", "native_btc", "evm_l2", "native_zec"];

function archRank(a: string): number {
  const i = ARCH_ORDER.indexOf(a);
  return i < 0 ? ARCH_ORDER.length : i;
}

function archLabel(a: string): string {
  return ARCHETYPE_LABELS[a as CorridorArchetype] ?? a.replace(/_/g, " ");
}

function pts(block: SeriesBlock | null | undefined): TimePoint[] {
  return Array.isArray(block?.points) ? block.points : [];
}

function measuredCount(...blocks: Array<SeriesBlock | null | undefined>): number {
  return blocks.reduce((a, b) => a + pts(b).filter(([, v]) => typeof v === "number" && Number.isFinite(v)).length, 0);
}

/** "change since first" line for a Stat; nothing when there is only one observation. */
function changeDelta(s: SeriesStats | null, fmt: (v: number) => string, unit: string) {
  if (!s || s.n < 2 || s.change_abs === null) return undefined;
  const text = fmt(s.change_abs);
  // A change that rounds to zero at the display precision reads "unchanged", not "-0.00".
  const zero = /^[+-]?\$?0(\.0+)?(\D|$)/.test(text) && !/[1-9]/.test(text);
  return { value: zero ? "unchanged" : text, label: `since first of ${plural(s.n, unit)}` };
}

function oneRunHint(s: SeriesStats | null, unit: string): string | undefined {
  if (!s || s.n === 0) return `no ${unit}s recorded`;
  if (s.n === 1) return `1 ${unit} recorded; change needs two`;
  return undefined;
}

function signTone(v: number | null | undefined) {
  return typeof v === "number" ? (v > 0 ? "emerald" : v < 0 ? "crimson" : "neutral") : "neutral";
}

/**
 * Tab 6: the history store as a live dashboard. Server component reading artifacts/history/summary.json
 * (quant/valuo/history.py). Hourly quote races drive the execution charts; daily canonical snapshots drive
 * concentration, supply and valuation charts and the trigger history. A series with one observation is a
 * dot and a sentence, never a line; confidence intervals appear only where the summary computed one.
 */
export function Tab6History({ history, snapshot, schedules }: Tab6Props) {
  const sum = history.summary;
  if (!sum) {
    return (
      <EmptyState title="No history recorded yet." commands={["make bench-history   # one live quote race -> artifacts/history/bench.jsonl", "make history         # append the canonical snapshot -> artifacts/history/snapshots.jsonl"]}>
        <p>
          Looked for <code className="break-all font-mono text-[12.5px] text-ink">{history.file}</code>: {history.reason}. Each command rebuilds{" "}
          <code className="font-mono text-[12.5px] text-ink">summary.json</code>, which this tab reads.
        </p>
      </EmptyState>
    );
  }

  const snaps = sum.snapshots;
  const bench = sum.bench;
  const bs = bench.series;
  const ss = snaps.series;
  const ciMinMatch = sum.ci_method?.match(/n\s*<\s*(\d+)/);
  const ciMinN = ciMinMatch ? Number(ciMinMatch[1]) : null;

  const snapRuns: RunCount = { n: snaps.n_records, first: snaps.first_t_utc, last: snaps.last_t_utc, unit: "run", cadence: schedules.snapshot?.per ?? null, job: "daily job" };
  const raceRuns: RunCount = { n: bench.n_runs, first: bench.first_t_utc, last: bench.last_t_utc, unit: "race", cadence: schedules.bench?.per ?? null, job: "hourly job" };

  // Archetypes present in the race history, in the house order.
  const archetypes = Object.keys(bs)
    .filter((k) => k.startsWith("headroom_bps_"))
    .map((k) => k.slice("headroom_bps_".length))
    .sort((a, b) => archRank(a) - archRank(b));
  const headroomSeries: TimeSeries[] = archetypes.map((a, i) => ({ name: archLabel(a), points: pts(bs[`headroom_bps_${a}`]), color: SERIES_COLORS[i % SERIES_COLORS.length], signColor: true }));

  const cross = statsOf(bs.headroom_bps_cross_vm);
  const btc = statsOf(bs.headroom_bps_native_btc);
  const l2 = statsOf(bs.headroom_bps_evm_l2);
  const ceiling = statsOf(bs.competitive_fee_ceiling_bps);
  const hhi = statsOf(ss.hhi_solver);
  const hhiLo = statsOf(ss.hhi_solver_ci_low);
  const hhiHi = statsOf(ss.hhi_solver_ci_high);
  const coverage = statsOf(ss.sink_coverage_ratio);
  const p50 = statsOf(ss.sotp_fdv_p50);
  const mkt = statsOf(ss.current_fdv_usd);
  const cartel = snaps.bear_triggers.solver_cartelization ?? null;

  const bps2 = (v: number) => fmtBps(v, { decimals: 2 });
  const bpsU = (v: number) => fmtBps(v, { decimals: 2, signed: false });

  // Headline: the cross-VM headroom median over the recorded races (the thesis's pricing-power claim).
  let title = "Every rerun of the pipeline and every hourly quote race, kept and summarised";
  if (cross && cross.n > 0 && cross.median !== null) {
    const verb = cross.median > 0 ? "out-delivered" : cross.median < 0 ? "trailed" : "matched";
    const by = cross.median === 0 ? "" : ` by a median ${fmtBps(Math.abs(cross.median), { decimals: 2, signed: false })}`;
    title = `1Click ${verb} the best competitor on cross-VM routes${by} across ${plural(cross.n, "race")}`;
  }
  const raceSpan = fmtSpan(spanMs(bench.first_t_utc, bench.last_t_utc));
  const snapSpan = fmtSpan(spanMs(snaps.first_t_utc, snaps.last_t_utc));
  const streakGapH = Object.values(snaps.bear_triggers).find((t) => typeof t.streak_max_gap_h === "number")?.streak_max_gap_h ?? null;

  const titles: Record<string, string> = {};
  for (const sc of snapshot?.bear_case?.scenarios ?? []) if (sc?.key && sc.title) titles[sc.key] = sc.title;

  return (
    <div className="space-y-12">
      <div className="space-y-6">
        <SectionIntro eyebrow="History" title={title}>
          <p>
            {plural(snaps.n_records, "canonical snapshot")} recorded
            {snaps.n_records > 1 ? ` from ${fmtDay(snaps.first_t_utc)} to ${fmtDay(snaps.last_t_utc)} (${snapSpan})` : snaps.n_records === 1 ? ` (${fmtDay(snaps.first_t_utc)})` : ""} and {plural(bench.n_runs, "live quote race")}
            {bench.n_runs > 1 ? ` over ${raceSpan}` : ""}.
            {cross && cross.n > 1 && cross.min !== null && cross.max !== null
              ? bps2(cross.min) === bps2(cross.max)
                ? ` Cross-VM headroom read ${bps2(cross.min)} in every race.`
                : ` Cross-VM headroom ranged from ${bps2(cross.min)} to ${bps2(cross.max)}.`
              : ""}{" "}
            {cross && cross.median_ci90
              ? `The 90% bootstrap interval of its median is ${bps2(cross.median_ci90[0])} to ${bps2(cross.median_ci90[1])}.`
              : ciMinN !== null
                ? `Confidence intervals appear once a series has ${fmtInt(ciMinN)} or more observations; until then each figure is a point reading, not a trend.`
                : ""}
          </p>
        </SectionIntro>

        <StatGrid cols={4}>
          <Stat label="Cross-VM headroom, latest race" value={cross?.last ?? null} format={bps2} tone={signTone(cross?.last)} delta={changeDelta(cross, (v) => fmtBps(v, { decimals: 2 }), "race")} hint={oneRunHint(cross, "race") ?? (cross?.median !== null && cross ? `median ${bps2(cross.median!)}` : undefined)} />
          <Stat label="Native BTC headroom, latest race" value={btc?.last ?? null} format={bps2} tone={signTone(btc?.last)} delta={changeDelta(btc, (v) => fmtBps(v, { decimals: 2 }), "race")} hint={oneRunHint(btc, "race") ?? (btc?.median !== null && btc ? `median ${bps2(btc.median!)}` : undefined)} />
          <Stat label="EVM L2 headroom, latest race" value={l2?.last ?? null} format={bps2} tone={signTone(l2?.last)} delta={changeDelta(l2, (v) => fmtBps(v, { decimals: 2 }), "race")} hint={oneRunHint(l2, "race") ?? (l2?.median !== null && l2 ? `median ${bps2(l2.median!)}` : undefined)} />
          <Stat label="Competitive fee ceiling, latest race" value={ceiling?.last ?? null} format={bpsU} delta={changeDelta(ceiling, (v) => fmtBps(v, { decimals: 2 }), "race")} hint={oneRunHint(ceiling, "race") ?? "best competitor's cross-VM friction"} />
          <Stat
            label="Solver HHI, latest snapshot"
            value={hhi?.last ?? null}
            format={(v) => fmtInt(v)}
            delta={changeDelta(hhi, (v) => fmtInt(v, { signed: true }), "run")}
            hint={
              hhiLo?.last != null && hhiHi?.last != null
                ? `90% CI ${fmtInt(hhiLo.last)} to ${fmtInt(hhiHi.last)}`
                : `no bootstrap CI recorded; ${oneRunHint(hhi, "run") ?? `${plural(hhi?.n ?? 0, "run")}`}`
            }
          />
          <Stat label="Sink coverage, latest snapshot" value={coverage?.last ?? null} format={(v) => fmtPct(v, { decimals: 1 })} delta={changeDelta(coverage, (v) => fmtPct(v, { decimals: 1, signed: true }), "run")} hint={oneRunHint(coverage, "run") ?? "sinks / issuance"} />
          <Stat label="SOTP P50 FDV, latest snapshot" value={p50?.last ?? null} format={(v) => fmtUsdCompact(v)} delta={changeDelta(p50, (v) => fmtUsdCompact(v, { signed: true }), "run")} hint={oneRunHint(p50, "run") ?? "10,000-path Monte Carlo median"} />
          <Stat
            label="Market FDV, latest snapshot"
            value={mkt?.last ?? null}
            format={(v) => fmtUsdCompact(v)}
            delta={changeDelta(mkt, (v) => fmtUsdCompact(v, { signed: true }), "run")}
            hint={p50?.last != null && mkt?.last != null && mkt.last > 0 ? `P50 is ${fmtPct(p50.last / mkt.last - 1, { decimals: 0, signed: true })} vs market` : oneRunHint(mkt, "run")}
          />
        </StatGrid>
      </div>

      <section className="space-y-6">
        <RouteWinLossTable routes={bench.routes} />
        <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <HistoryChartCard
            kicker="Hourly quote race"
            title="Headroom per route archetype"
            subtitle="Median cell headroom of 1Click over the best competing quote, by archetype, in basis points. Above zero, 1Click delivers more output."
            runs={raceRuns}
            measured={measuredCount(...archetypes.map((a) => bs[`headroom_bps_${a}`]))}
            missingReason="no race has paired a 1Click quote with a competitor quote yet"
            chart={{ title: "Headroom per route archetype over time, bps", series: headroomSeries, yFormat: (v) => fmtBps(v, { decimals: 1 }), valueFormat: bps2, zeroLine: true, includeZero: true }}
          />
          <HistoryChartCard
            kicker="Hourly quote race"
            title="Competitive fee ceiling"
            subtitle="Median friction of the best competitor on cross-VM routes: the fee a router can charge before a rival quote beats it."
            runs={raceRuns}
            measured={measuredCount(bs.competitive_fee_ceiling_bps)}
            missingReason="no cross-VM race has a competitor quote yet"
            chart={{ title: "Competitive fee ceiling over time, bps", series: [{ name: "Ceiling", points: pts(bs.competitive_fee_ceiling_bps), color: SERIES_COLORS[0] }], yFormat: (v) => fmtBps(v, { decimals: 2, signed: false }), valueFormat: bpsU, includeZero: false }}
            footnote={
              ceiling && ceiling.n > 1 && ceiling.min !== null && ceiling.max !== null
                ? bpsU(ceiling.min) === bpsU(ceiling.max)
                  ? `Every race read ${bpsU(ceiling.min)} at two decimals.`
                  : `Range ${bpsU(ceiling.min)} to ${bpsU(ceiling.max)}.`
                : undefined
            }
          />
        </div>
        <RaceCellTable cells={bench.cells} series={bs} ciMinN={ciMinN} />
      </section>

      <section className="space-y-6">
        <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-3">
          <HistoryChartCard
            kicker="Daily canonical snapshot"
            title="Solver concentration"
            subtitle={`HHI over solver fill participations on intents.near${cartel?.threshold != null ? `, against the ${fmtInt(cartel.threshold)} cartelization trigger` : ""}. The band is the 90% bootstrap interval when recorded.`}
            runs={snapRuns}
            measured={measuredCount(ss.hhi_solver)}
            missingReason="solver HHI was not measured in any recorded run"
            chart={{
              title: "Solver HHI over time",
              series: [{ name: "HHI", points: pts(ss.hhi_solver), color: SERIES_COLORS[0] }],
              band: ss.hhi_solver_ci_low && ss.hhi_solver_ci_high ? { name: "90% bootstrap CI", lo: pts(ss.hhi_solver_ci_low), hi: pts(ss.hhi_solver_ci_high), color: SERIES_COLORS[0] } : null,
              refLines: cartel?.threshold != null ? [{ y: cartel.threshold, label: `Trigger ${cartel.comparator ?? ""} ${fmtInt(cartel.threshold)}`.replace(/\s+/g, " ") }] : [],
              yFormat: (v) => fmtInt(v),
              includeZero: true,
              width: 420,
              height: 260,
            }}
            footnote={measuredCount(ss.hhi_solver_ci_low) === 0 ? "No run so far recorded a bootstrap interval." : undefined}
          />
          <HistoryChartCard
            kicker="Daily canonical snapshot"
            title="Sink coverage"
            subtitle="Buybacks, gas burn and storage lock as a share of daily issuance. At 100% the float stops growing."
            runs={snapRuns}
            measured={measuredCount(ss.sink_coverage_ratio)}
            missingReason="sink coverage was not computed in any recorded run"
            chart={{
              title: "Sink coverage over time",
              series: [{ name: "Coverage", points: pts(ss.sink_coverage_ratio), color: SERIES_COLORS[2] }],
              refLines: [{ y: 1, label: "Sinks = issuance", color: COLORS.muted }],
              yFormat: (v) => fmtPct(v, { decimals: 0 }),
              valueFormat: (v) => fmtPct(v, { decimals: 1 }),
              includeZero: true,
              width: 420,
              height: 260,
            }}
          />
          <HistoryChartCard
            kicker="Daily canonical snapshot"
            title="Model value against the market"
            subtitle="SOTP Monte Carlo P50 FDV with its P10 to P90 range, and the market FDV recorded in the same run."
            runs={snapRuns}
            measured={measuredCount(ss.sotp_fdv_p50, ss.current_fdv_usd)}
            missingReason="neither the SOTP FDV nor the market FDV was recorded"
            chart={{
              title: "SOTP P50 FDV versus market FDV over time",
              series: [
                { name: "P50", points: pts(ss.sotp_fdv_p50), color: SERIES_COLORS[0] },
                { name: "Market", points: pts(ss.current_fdv_usd), color: SERIES_COLORS[1], dashed: true },
              ],
              band: ss.sotp_fdv_p10 && ss.sotp_fdv_p90 ? { name: "P10 to P90", lo: pts(ss.sotp_fdv_p10), hi: pts(ss.sotp_fdv_p90), color: SERIES_COLORS[0] } : null,
              yFormat: (v) => fmtUsdCompact(v),
              includeZero: true,
              width: 420,
              height: 260,
            }}
          />
        </div>
        <TriggerHistoryTable triggers={snaps.bear_triggers} titles={titles} account={anchorAccount()} />
      </section>

      <BacktestPanel backtest={snapshot?.backtest} />

      <MethodNote summary="Method, sources and how to add points">
        <p>
          Everything on this tab is read from <code>artifacts/history/summary.json</code> (schema <code>{sum.schema}</code>, rebuilt {fmtUtc(sum.generated_at_utc)}), which{" "}
          <code>quant/valuo/history.py</code> derives from two append-only logs: <code>snapshots.jsonl</code>, one record per canonical pipeline run (de-duplicated by snapshot SHA-256), and{" "}
          <code>bench.jsonl</code>, one record per live quote race. Each race gzips its raw venue responses under <code>artifacts/history/raw/&lt;utc&gt;/</code> with the SHA-256 of the uncompressed
          bytes; <code>make history-verify</code> re-hashes them.
        </p>
        {snaps.n_records_total !== undefined && snaps.n_records_total > snaps.n_records ? (
          <p>
            The daily series keeps the latest canonical run per UTC day: {fmtInt(snaps.n_records)} days shown from {fmtInt(snaps.n_records_total)} recorded runs; {fmtInt(snaps.n_records_total - snaps.n_records)} same-day re-runs are kept in{" "}
            <code>snapshots.jsonl</code> but not plotted.
          </p>
        ) : null}
        <p>
          Schedule, as committed:{" "}
          {schedules.snapshot ? (
            <>
              the canonical snapshot runs {schedules.snapshot.plain} (<code>{schedules.snapshot.file}</code>)
            </>
          ) : (
            "the snapshot schedule could not be read from ops/vps/valuo.crontab"
          )}
          ;{" "}
          {schedules.bench ? (
            <>
              the quote race runs {schedules.bench.plain} (<code>{schedules.bench.file}</code>)
            </>
          ) : (
            "the race schedule could not be read from ops/vps/valuo.crontab"
          )}
          . Both jobs run on a VPS (ops/vps/setup.sh installs them) and commit their output back to the repository, so the series grows by one point per day and one race per hour.
        </p>
        <p>
          Statistics: {sum.ci_method ?? "no CI method recorded"}. Medians, ranges and changes are over non-null observations in time order; a run that did not measure a metric leaves a gap rather than a zero. Race
          headroom per archetype is the median over cells with a 1Click quote and at least one competitor quote; snapshot series are the values of the canonical <code>latest_snapshot.json</code> of each day. Trigger
          streaks use the trigger&apos;s own breach flag from <code>bear_case.scenarios</code> in each run
          {streakGapH !== null ? `; a streak is continuous only while consecutive daily records are at most ${fmtInt(streakGapH)} h apart, and a record where the trigger was not measured ends it` : ""}.
        </p>
        <p>
          Add points locally: <code>make bench-history</code> runs one live race (all corridors and clips, zero API keys) and appends it; <code>make history</code> appends the current canonical snapshot;{" "}
          <code>make history-summary</code> rebuilds <code>summary.json</code>. Reload this page to see them.
        </p>
      </MethodNote>
    </div>
  );
}
