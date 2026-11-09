import type { BearCase } from "@/lib/types";
import { prose, splitSummary } from "./bearData";

/**
 * The model's own falsification summary (bear_case.falsification_summary), set as memo prose.
 * The text is verbatim from the quant engine; it is only broken into one paragraph per scenario,
 * with the scenario key replaced by its title as the paragraph lead.
 */
export function FalsificationSummary({ bear }: { bear: BearCase }) {
  const scenarios = bear.scenarios ?? [];
  const titles = new Map(scenarios.map((s) => [s.key, s.title]));
  const parts = splitSummary(bear.falsification_summary, scenarios.map((s) => s.key));
  return (
    <section aria-labelledby="bear-falsification" className="max-w-3xl">
      <h3 id="bear-falsification" className="font-serif text-[22px] font-medium leading-tight text-ink">
        Conditions under which the thesis is wrong
      </h3>
      <p className="mt-1 text-[13px] text-dim">Written by the quant engine from the same numbers as the tables; identical to the paragraph in the IC memo.</p>
      {parts.length ? (
        <div className="mt-4 space-y-3.5">
          {parts.map((p, i) => {
            const colon = p.indexOf(":");
            const key = colon > 0 && colon < 40 ? p.slice(0, colon) : null;
            const lead = key ? (titles.get(key) ?? key) : null;
            const rest = key ? p.slice(colon + 1).trim() : p;
            return (
              <p key={`${i}-${p.slice(0, 16)}`} className="text-[15px] leading-relaxed text-ink">
                {lead ? <span className="font-semibold">{lead}. </span> : null}
                <span className="tnum">{prose(rest.charAt(0).toUpperCase() + rest.slice(1))}</span>
              </p>
            );
          })}
        </div>
      ) : (
        <p className="mt-4 text-[13.5px] text-muted">The snapshot carries no falsification summary.</p>
      )}
    </section>
  );
}
