import { fmtInt, fmtPct, fmtUsdCompact } from "@/lib/format";
import { Badge } from "@/components/ui/Badge";
import { MethodNote } from "@/components/ui/Section";
import { comparatorRule, fmtMetricValue } from "@/components/tab5/bearData";
import { fmtSpan, metricLabel, minus, numberWord, typo, type BearScenarioView, type LandingData } from "./landingData";
import { LandingSection, SectionHeader, TextLink } from "./SectionHeader";

const word = numberWord;
const ddTone = (v: number) => (v < 0 ? "text-crimson" : v > 0 ? "text-emerald" : "text-muted");

type TriggerState = "breached" | "clear" | "inconclusive" | "unmeasured";
/** trigger_status when the snapshot carries it; otherwise derived from trigger_breached / trigger_evaluated. */
function stateOf(s: BearScenarioView): TriggerState {
  if (s.status === "inconclusive") return "inconclusive";
  if (s.status === "breached") return "breached";
  if (s.status === "clear" || s.status === "not_breached") return "clear";
  if (s.status === "not_measured" || s.status === "unmeasured") return "unmeasured";
  return s.evaluated === false || s.current === null || s.breached === null ? "unmeasured" : s.breached ? "breached" : "clear";
}
const STATE_BADGE: Record<TriggerState, { variant: "error" | "ok" | "warn" | "neutral"; label: string }> = {
  breached: { variant: "error", label: "Breached" },
  clear: { variant: "ok", label: "Not breached" },
  inconclusive: { variant: "warn", label: "Inconclusive" },
  unmeasured: { variant: "neutral", label: "Not measured" },
};
/** One-line reason for an inconclusive grade, from the scenario's span fields or the first clause of its note. */
function inconclusiveReason(s: BearScenarioView): string | null {
  if (s.sampleSpanS !== null && s.minSampleSpanS !== null && s.sampleSpanS < s.minSampleSpanS) {
    const ci = s.hhiCi90 ? `; HHI 90% CI ${fmtInt(s.hhiCi90[0])} to ${fmtInt(s.hhiCi90[1])}` : "";
    return `Inconclusive: the sample spans ${fmtSpan(s.sampleSpanS)}, under the ${fmtSpan(s.minSampleSpanS)} minimum needed to grade it${ci}.`;
  }
  if (!s.note) return null;
  const first = s.note.replace(/^inconclusive:\s*/i, "").split(";")[0].trim();
  return first ? `Inconclusive: ${first}.` : null;
}

/**
 * Falsifiability preview: each stress scenario with its drawdown against the deterministic base
 * and the live early-warning trigger status. "x of y breached" counts only triggers graded this
 * run; unmeasured triggers are labelled as such.
 */
export function BearPreview({ data }: { data: LandingData }) {
  const b = data.bear;
  const maxDd = Math.max(...b.scenarios.map((s) => Math.abs(s.drawdownPct)), Math.abs(b.combinedDrawdownPct), 1e-9);
  const states = b.scenarios.map(stateOf);
  const inconclusive = states.filter((x) => x === "inconclusive").length;
  const unmeasured = states.filter((x) => x === "unmeasured").length;
  const breached = b.triggersBreached ?? (states.some((x) => x !== "unmeasured" && x !== "inconclusive") ? states.filter((x) => x === "breached").length : null);
  const graded = b.triggersEvaluated;
  const n = b.scenarios.length;

  return (
    <LandingSection id="bear">
      <SectionHeader
        number="5"
        eyebrow="Bear case"
        title={`${word(n)} ways the thesis fails, and the number that would warn first`}
        lede={
          <>
            Each scenario perturbs the inputs of the deterministic engine and is re-valued against a base of <span className="tnum text-ink">{fmtUsdCompact(b.baseFdv)}</span>. Together
            they {b.combinedDrawdownPct <= 0 ? "take" : "add"} <span className={`tnum ${ddTone(b.combinedDrawdownPct)}`}>{fmtPct(Math.abs(b.combinedDrawdownPct), { decimals: 1 })}</span>{" "}
            {b.combinedDrawdownPct <= 0 ? "off" : "to"} that value.
          </>
        }
        aside={
          <>
            <Badge variant={breached ? "error" : breached === 0 ? "ok" : "neutral"} dot size="sm">
              {breached === null ? "Trigger count not in snapshot" : `${fmtInt(breached)} of ${fmtInt(graded)} graded triggers breached`}
            </Badge>
            {inconclusive ? (
              <Badge variant="warn" dot size="sm">
                {fmtInt(inconclusive)} inconclusive
              </Badge>
            ) : null}
            {unmeasured ? (
              <Badge variant="neutral" dot size="sm">
                {fmtInt(unmeasured)} not measured
              </Badge>
            ) : null}
          </>
        }
      />

      <div className="mt-12 border-t border-border-strong">
        <div className="hidden grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_10rem] gap-10 border-b border-border py-2.5 text-[13px] text-muted lg:grid">
          <div>Scenario and early-warning metric</div>
          <div>Drawdown vs base</div>
          <div className="text-right">Trigger</div>
        </div>
        {b.scenarios.map((s, idx) => {
          const status = states[idx];
          const reason = status === "inconclusive" ? inconclusiveReason(s) : null;
          const width = Math.min(100, (Math.abs(s.drawdownPct) / maxDd) * 100);
          return (
            <div key={s.key} className="grid gap-x-10 gap-y-4 border-b border-border py-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_10rem] lg:items-center">
              <div className="min-w-0">
                <h3 className="font-serif text-[20px] font-medium leading-snug text-ink">{s.title}</h3>
                <p className="mt-1.5 text-[14.5px] leading-relaxed text-muted">
                  {metricLabel(s.metric)} is <span className="tnum text-ink">{s.current === null ? "not measured" : typo(fmtMetricValue(s.metric, s.current))}</span>; the trigger is{" "}
                  <span className="tnum text-ink">{typo(comparatorRule(s.comparator, fmtMetricValue(s.metric, s.threshold)))}</span>.
                  {reason ? <span className="text-amber"> {reason}</span> : s.sampleThin && s.fillsSampled !== null ? <span className="text-amber"> Thin sample: {fmtInt(s.fillsSampled)} fills.</span> : null}{" "}
                  <a href={s.monitor} target="_blank" rel="noreferrer" className="text-dim underline decoration-dotted underline-offset-[3px] hover:text-muted">
                    Monitor
                  </a>
                </p>
              </div>
              <div className="min-w-0">
                <div className="flex items-baseline justify-between gap-4">
                  <span className={`tnum text-[17px] font-medium ${ddTone(s.drawdownPct)}`}>{minus(fmtPct(s.drawdownPct, { decimals: 1, signed: true }))}</span>
                  <span className="tnum text-[13px] text-dim">to {fmtUsdCompact(s.fdv)}</span>
                </div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-surface-2" role="img" aria-label={`${s.title}: ${fmtPct(s.drawdownPct, { decimals: 1 })} drawdown`}>
                  <div className="h-1.5 rounded-full bg-crimson/80" style={{ width: `${width}%` }} />
                </div>
              </div>
              <div className="lg:text-right">
                <Badge variant={STATE_BADGE[status].variant} dot size="sm">
                  {STATE_BADGE[status].label}
                </Badge>
              </div>
            </div>
          );
        })}
        <div className="grid gap-x-10 gap-y-4 border-b border-border-strong py-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_10rem] lg:items-center">
          <div>
            <h3 className="font-serif text-[20px] font-medium text-ink">All {n === 1 ? "scenarios" : word(n).toLowerCase()} at once</h3>
          </div>
          <div>
            <div className="flex items-baseline justify-between gap-4">
              <span className={`tnum text-[17px] font-semibold ${ddTone(b.combinedDrawdownPct)}`}>{minus(fmtPct(b.combinedDrawdownPct, { decimals: 1, signed: true }))}</span>
              <span className="tnum text-[13px] text-dim">to {fmtUsdCompact(b.combinedWorstFdv)}</span>
            </div>
            <div className="mt-2 h-1.5 w-full rounded-full bg-surface-2">
              <div className="h-1.5 rounded-full bg-crimson" style={{ width: `${Math.min(100, (Math.abs(b.combinedDrawdownPct) / maxDd) * 100)}%` }} />
            </div>
          </div>
          <div className="lg:text-right">
            <TextLink href="/terminal#bear">Full stress matrix</TextLink>
          </div>
        </div>
      </div>

      <MethodNote className="mt-10">
        <p>
          Base value: <code>bear_case.base_fdv_p50</code> = {fmtUsdCompact(b.baseFdv)} ({b.valueBasis ?? "deterministic value at median inputs, not a Monte Carlo percentile"}). It differs from
          the Monte Carlo median by construction
          {data.marketImplied?.baseFdv !== null && data.marketImplied?.baseFdv !== undefined && Math.abs(data.marketImplied.baseFdv / b.baseFdv - 1) < 1e-6
            ? ", and equals the expected-path value the market-implied solves in section 1 start from."
            : "."}
        </p>
        <p>
          Early-warning metrics, by key:{" "}
          {b.scenarios.map((s, i) => (
            <span key={s.key}>
              {i ? "; " : ""}
              {s.title} reads <code>{s.metric}</code>
            </span>
          ))}
          .{b.triggersUnevaluated.length ? ` Not graded this run: ${b.triggersUnevaluated.join(", ")}.` : ""} The count is <code>bear_case.triggers_breached</code> of{" "}
          <code>triggers_evaluated</code>; an inconclusive trigger (<code>trigger_status</code> = inconclusive, <code>trigger_breached</code> null) is counted as neither breached nor clear.
        </p>
      </MethodNote>
    </LandingSection>
  );
}
