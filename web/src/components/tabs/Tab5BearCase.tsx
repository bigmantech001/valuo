import { fmtInt, fmtPct, fmtUsd, fmtUsdCompact } from "@/lib/format";
import type { BearCase } from "@/lib/types";
import { Stat } from "@/components/ui";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { DrawdownBars } from "@/components/tab5/DrawdownBars";
import { FalsificationSummary } from "@/components/tab5/FalsificationSummary";
import { LiveMetricsTable } from "@/components/tab5/LiveMetricsTable";
import { StressParameters } from "@/components/tab5/StressParameters";
import { StressTable } from "@/components/tab5/StressTable";
import { TriggerBoard } from "@/components/tab5/TriggerBoard";
import { bearBasis, bearValueBasis, inconclusiveReason, LIVE_METRIC_META, metricLabel, num, stressParamLabel, triggersBreached } from "@/components/tab5/bearData";
import type { TabProps } from "./types";

/** "1 of 4 early-warning triggers is breached" built from the snapshot counts. */
function triggerHeadline(breached: number | null, evaluated: number): string {
  if (breached === null) return "None of the early-warning triggers could be graded in this snapshot";
  const verb = breached === 1 ? "is" : "are";
  if (breached === 0) return `None of the ${fmtInt(evaluated)} measured early-warning triggers is breached`;
  return `${fmtInt(breached)} of ${fmtInt(evaluated)} measured early-warning triggers ${verb} breached`;
}

/** Second clause of the headline: the combined worst case, worded by sign. */
function combinedClause(dd: number | null, nScen: number): string {
  if (dd === null) return "";
  const words = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
  const all = nScen > 1 ? `all ${words[nScen] ?? fmtInt(nScen)} stresses together` : "the stress";
  if (dd < 0) return `; ${all} cut the deterministic value by ${fmtPct(Math.abs(dd), { decimals: 0 })}`;
  if (dd > 0) return `; ${all} raise the deterministic value by ${fmtPct(dd, { decimals: 0 })}`;
  return `; ${all} leave the deterministic value unchanged`;
}

/**
 * Tab 5: steel-manned bear case and falsifiability matrix.
 * Server component. Everything rendered is read from `snapshot.bear_case` (plus two reference
 * figures from `snapshot.sotp`); the value basis is the deterministic SOTP at median inputs and is
 * labeled as such throughout, never as a Monte Carlo percentile.
 */
export function Tab5BearCase({ snapshot }: TabProps) {
  const bear = (snapshot.bear_case ?? null) as BearCase | null;
  if (!bear) {
    return (
      <div className="space-y-6">
        <SectionIntro eyebrow="Bear case and falsification" title="The bear case did not run for this snapshot">
          The model step that writes the stress scenarios is absent (it did not run or failed). Nothing is substituted; see the snapshot warnings for the reason.
        </SectionIntro>
        <MethodNote>
          <p>
            Missing field: <code>bear_case</code>. Run warnings: <code>snapshot.warnings</code>.
          </p>
        </MethodNote>
      </div>
    );
  }

  const scenarios = bear.scenarios ?? [];
  const baseFdv = num(bear.base_fdv_p50);
  const basePrice = num(bear.base_price_p50);
  const combinedFdv = num(bear.combined_worst_fdv);
  const combinedDd = num(bear.combined_drawdown_pct);
  const combinedPrice = num(bear.combined_worst_price);
  const combinedPriceDd = num(bear.combined_price_drawdown_pct);
  const spotFdv = num(snapshot.sotp?.current_fdv_usd);
  const mcP50 = num(snapshot.sotp?.fdv_percentiles?.p50);
  const baseVsSpot = baseFdv !== null && spotFdv !== null && spotFdv > 0 ? baseFdv / spotFdv - 1 : null;
  const baseVsMc = baseFdv !== null && mcP50 !== null && mcP50 > 0 ? baseFdv / mcP50 - 1 : null;
  const trig = triggersBreached(bear);
  const basis = bearBasis(bear);
  const valueBasis = bearValueBasis(bear);
  const nScen = scenarios.length;
  const unevaluatedTitles = trig.unevaluated.map((k) => scenarios.find((s) => s.key === k)?.title ?? k);
  const inconclusiveTitles = trig.inconclusive.map((k) => {
    const s = scenarios.find((x) => x.key === k);
    const why = s ? inconclusiveReason(s) : null;
    return `${s?.title ?? k}${why ? ` (${why.charAt(0).toLowerCase()}${why.slice(1)})` : ""}`;
  });
  const breachedTitles = scenarios.filter((s) => s.trigger_breached === true).map((s) => s.title);

  return (
    <div className="space-y-10">
      <SectionIntro eyebrow="Bear case and falsification" title={`${triggerHeadline(trig.breached, trig.evaluated)}${combinedClause(combinedDd, nScen)}.`}>
        <p>
          Every value in this section is {(valueBasis ?? "deterministic at median inputs; not a Monte Carlo percentile").replace(/;\s*/, ", ")}. Each scenario changes a few inputs of the same valuation and re-prices it, so any difference comes from the scenario alone.
          {breachedTitles.length ? ` Breached now: ${breachedTitles.join("; ")}.` : ""}
          {inconclusiveTitles.length ? ` Inconclusive, measured on too short a sample to grade: ${inconclusiveTitles.join("; ")}.` : ""}
          {unevaluatedTitles.length ? ` Not measured this run: ${unevaluatedTitles.join("; ")}.` : ""}
        </p>
      </SectionIntro>

      <div className="space-y-3">
        <StatGrid cols={4}>
          <Stat label="Base value, deterministic" value={baseFdv} format={fmtUsdCompact} hint={basePrice !== null ? `Implied price ${fmtUsd(basePrice, { decimals: 3 })}` : undefined} />
          <Stat
            label="Combined worst value"
            value={combinedFdv}
            format={fmtUsdCompact}
            delta={combinedDd === null ? undefined : { value: fmtPct(combinedDd, { decimals: 1, signed: true }), tone: combinedDd < 0 ? "crimson" : combinedDd > 0 ? "emerald" : "neutral", label: "vs base" }}
            hint={
              combinedPrice !== null
                ? `Implied price ${fmtUsd(combinedPrice, { decimals: 3 })}${combinedPriceDd !== null ? ` (${fmtPct(combinedPriceDd, { decimals: 1, signed: true })})` : ""}`
                : undefined
            }
          />
          <Stat
            label="Triggers breached now"
            value={trig.breached === null ? null : `${fmtInt(trig.breached)} of ${fmtInt(trig.evaluated)}`}
            tone={trig.breached ? "crimson" : "neutral"}
            hint={
              trig.unevaluated.length || trig.inconclusive.length
                ? [trig.inconclusive.length ? `${fmtInt(trig.inconclusive.length)} inconclusive (sample too short)` : "", trig.unevaluated.length ? `${fmtInt(trig.unevaluated.length)} not measured this run` : ""].filter(Boolean).join("; ")
                : "Every scenario trigger was graded"
            }
          />
          <Stat
            label="Spot FDV, for reference"
            value={spotFdv}
            format={fmtUsdCompact}
            provenance={{ source: "nearstats", name: "summary" }}
            delta={baseVsSpot === null ? undefined : { value: fmtPct(baseVsSpot, { decimals: 1, signed: true }), tone: baseVsSpot < 0 ? "crimson" : "emerald", label: "base vs spot" }}
          />
        </StatGrid>
        <p className="max-w-3xl text-[13px] leading-relaxed text-muted">
          Scenario changes are measured from the deterministic base, not from spot.
          {mcP50 !== null && baseVsMc !== null ? ` For contrast, the seeded Monte Carlo median is ${fmtUsdCompact(mcP50)}; the deterministic base sits ${fmtPct(baseVsMc, { decimals: 1, signed: true })} against it.` : ""}
        </p>
      </div>

      <div className="space-y-6">
        <StressTable bear={bear} />
        <DrawdownBars bear={bear} />
      </div>

      <TriggerBoard bear={bear} />

      <FalsificationSummary bear={bear} />

      <LiveMetricsTable bear={bear} />

      <StressParameters bear={bear} />

      <MethodNote>
        <p>
          <span className="text-ink">Value basis.</span> {basis ?? "The snapshot carries no basis statement; per bear_case.py the scenario values are deterministic (median-input) FDVs, not Monte Carlo percentiles."}
        </p>
        <p>
          <span className="text-ink">Change definition.</span> {bear.drawdown_definition ?? "The snapshot carries no drawdown definition."}
        </p>
        <p>
          Snapshot fields: base <code>bear_case.base_fdv_p50</code>, <code>base_price_p50</code>, <code>base_crossover_month</code>; combined <code>combined_worst_fdv</code>, <code>combined_drawdown_pct</code>, <code>combined_worst_price</code>, <code>combined_price_drawdown_pct</code>,{" "}
          <code>combined_perturbations</code> (unapplied: <code>combined_perturbations_unapplied</code>); per scenario <code>bear_case.scenarios[].sotp_fdv_p50</code>, <code>drawdown_pct</code>, <code>price_p50</code>, <code>price_drawdown_pct</code>, <code>crossover_month</code>,{" "}
          <code>fdv_ex_monetary</code>, <code>mc_fdv_p50</code>; trigger counts <code>bear_case.triggers_breached</code>, <code>triggers_evaluated</code>, <code>triggers_unevaluated</code>; prose <code>bear_case.falsification_summary</code>; register <code>bear_case.stress_parameters</code>. Spot FDV is{" "}
          <code>sotp.current_fdv_usd</code>; the Monte Carlo median is <code>sotp.fdv_percentiles.p50</code>.
        </p>
        {scenarios.length ? (
          <div>
            <p>Scenario keys and the field each trigger reads:</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {scenarios.map((s) => (
                <li key={s.key}>
                  <code>{s.key}</code>: {metricLabel(s.early_warning_metric)} (<code>{s.early_warning_metric ?? "n/a"}</code>){s.monitor_field ? <>, read as <code>{s.monitor_field}</code></> : null}
                  {s.secondary_metric ? (
                    <>
                      ; secondary <code>{s.secondary_metric}</code>
                    </>
                  ) : null}
                  .
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div>
          <p>Live metrics, read from <code>bear_case.live_metrics</code>:</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {Object.keys(bear.live_metrics ?? {}).map((k) => (
              <li key={k}>
                <code>{k}</code>: {LIVE_METRIC_META[k]?.field ?? "no field mapping in the terminal; see bear_case.py live_metrics()"}
              </li>
            ))}
          </ul>
        </div>
        {(bear.stress_parameters ?? []).length ? (
          <p>
            Register keys:{" "}
            {(bear.stress_parameters ?? []).map((a, i) => (
              <span key={a.key}>
                {i ? ", " : ""}
                <code>{a.key}</code> ({stressParamLabel(a.key).toLowerCase()})
              </span>
            ))}
            .
          </p>
        ) : null}
        <p>Perturbation inputs shown struck through in the scenario table are listed by the model but have no slot in the deterministic engine, so they do not move the value.</p>
      </MethodNote>
    </div>
  );
}
