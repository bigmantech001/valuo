import { Fragment } from "react";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Badge, Stat, type BadgeVariant } from "@/components/ui";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
import { fmtInt, fmtNum, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import type { MarketImpliedSolve, Snapshot } from "@/lib/types";
import { isNum, joinAnd } from "./derive";
import { evidenceRef, fmtUnit, joinOr, leverPhrase, solveStatus, upperFirst, type SolveStatus } from "./marketImplied";
import { Panel, SubHead } from "./parts";

const STATUS: Record<SolveStatus, { label: string; variant: BadgeVariant; hint: string }> = {
  inside: { label: "Inside evidence", variant: "ok", hint: "The required value sits on the measured side of the comparator" },
  outside: { label: "Outside evidence", variant: "error", hint: "The required value lies beyond what this run measured" },
  unreachable: { label: "Unreachable", variant: "neutral", hint: "No value inside the search bounds makes the model equal the market" },
  assumption: { label: "Against an assumption", variant: "assumption", hint: "The comparator is an assumed value, not a measurement, so the comparison is not evidence" },
  not_compared: { label: "Not compared", variant: "neutral", hint: "No comparator was available" },
};

function times(v: number | null | undefined): string {
  if (!isNum(v)) return NA;
  return `${fmtNum(v, { decimals: Math.abs(v) >= 10 ? 0 : 1 })}×`;
}

/**
 * Opening of the executive summary: what NEAR's market value requires, input by input, against
 * what this run measured. Reads `market_implied` (one-at-a-time root solves of the deterministic
 * SOTP against the market FDV). Every sentence is assembled from the solves, so it stays true when
 * the numbers or their signs change.
 */
export function MarketImpliedOpening({ snapshot }: { snapshot: Snapshot }) {
  const mi = snapshot.market_implied;
  if (!mi) return null;
  const sotp = snapshot.sotp;
  const solves: MarketImpliedSolve[] = mi.solves ?? [];
  const current = isNum(mi.current_fdv_usd) ? mi.current_fdv_usd : null;
  const base = isNum(mi.base_fdv_usd) ? mi.base_fdv_usd : null;
  const p50 = isNum(mi.base_fdv_mc_p50_usd) ? mi.base_fdv_mc_p50_usd : null;
  const gap = isNum(mi.gap_multiple) ? mi.gap_multiple : null;

  const withStatus = solves.map((s) => ({ s, status: solveStatus(s) }));
  const outside = withStatus.filter((x) => x.status === "outside").map((x) => x.s);
  const inside = withStatus.filter((x) => x.status === "inside").map((x) => x.s);
  const unreachable = withStatus.filter((x) => x.status === "unreachable").map((x) => x.s);
  const assumed = withStatus.filter((x) => x.status === "assumption").map((x) => x.s);
  const comparable = outside.length + inside.length;

  // ------------------------------------------------------------------ headline
  const fdvText = current !== null ? fmtUsdCompact(current) : null;
  let title: string;
  if (!fdvText || !solves.length) title = "The market-implied solves are missing from this snapshot";
  else if (outside.length && inside.length)
    title = `NEAR's ${fdvText} market value needs ${joinOr(outside.slice(0, 2).map(leverPhrase))} on Intents cash flow alone; only ${joinAnd(inside.map(leverPhrase))} closes the gap inside the evidence`;
  else if (outside.length)
    title = `NEAR's ${fdvText} market value needs ${joinOr(outside.slice(0, 2).map(leverPhrase))} on Intents cash flow alone; no single lever closes the gap inside the evidence`;
  else if (inside.length) title = `NEAR's ${fdvText} market value is reachable inside the measured evidence through ${joinOr(inside.map(leverPhrase))}`;
  else title = `No single model input reaches NEAR's ${fdvText} market value against measured evidence`;

  const eyebrow = sotp
    ? `Investment thesis. What the market is pricing, against a ${fmtInt(sotp.horizon_months)}-month cash-flow model and ${fmtInt(sotp.n_paths)} seeded paths`
    : "Investment thesis. What the market is pricing";

  // ------------------------------------------------------------------ lede
  const lede: string[] = [];
  if (base !== null && current !== null) {
    const rel = gap !== null ? (gap >= 1 ? `${times(gap)} the expected path` : `${fmtPct(gap, { decimals: 0 })} of the expected path`) : null;
    lede.push(
      `The cash-flow model values NEAR at ${fmtUsdCompact(base)} on its expected path${p50 !== null ? ` and ${fmtUsdCompact(p50)} at the Monte Carlo median` : ""}; the ${fmtUsdCompact(current)} market FDV${rel ? ` is ${rel}` : " is the reference"}.`,
    );
  }
  const mult = solves.find((s) => s.param === "terminal_multiple");
  const peerMedian = mult && isNum(mult.evidence?.value) ? mult.evidence.value : null;
  const cap = mult && isNum(mult.evidence?.model_cap) ? mult.evidence.model_cap : null;
  const nearRev = snapshot.relative_value?.near?.fdv_to_revenue_run_rate ?? null;
  if (mult && solveStatus(mult) === "inside" && peerMedian !== null && gap !== null && gap > 1)
    lede.push(
      `Peer L1s trade at a median ${times(peerMedian)} FDV to revenue${isNum(nearRev) ? ` and NEAR at ${times(nearRev)}` : ""}, so the market prices NEAR on an L1 multiple that carries a monetary premium, not on Intents cash flow at the model's ${cap !== null ? `${times(cap)} ` : ""}cap.`,
    );
  else lede.push("Each row below moves one input alone until the model equals the market, then sets that value against what this run measured.");

  // ------------------------------------------------------------------ reading
  const reading: string[] = [];
  if (comparable)
    reading.push(
      `${fmtInt(outside.length)} of ${fmtInt(comparable)} levers with a measured comparator need values outside the evidence${outside.length ? `: ${joinAnd(outside.map((s) => `${s.short_label} ${fmtUnit(s.required_value, s.unit)} against ${fmtUnit(s.evidence?.value, s.unit)}${isNum(s.required_vs_evidence?.ratio) ? ` (${times(s.required_vs_evidence.ratio)})` : ""}`))}` : ""}.`,
    );
  for (const s of inside)
    reading.push(`${upperFirst(s.short_label)} closes the gap at ${fmtUnit(s.required_value, s.unit)}, inside the ${s.evidence?.label ?? "measured comparator"} of ${fmtUnit(s.evidence?.value, s.unit)}.`);
  for (const s of unreachable) reading.push(`${upperFirst(s.short_label)} cannot close it: ${s.reason ?? "no value inside the search bounds reaches the market FDV"}.`);
  for (const s of assumed)
    reading.push(`${upperFirst(s.short_label)} needs ${fmtUnit(s.required_value, s.unit)}, but its comparator of ${fmtUnit(s.evidence?.value, s.unit)} is an assumption, not a measurement, so this row is not evidence either way.`);

  return (
    <section id="market-implied" className="space-y-10">
      <SectionIntro eyebrow={eyebrow} title={title}>
        <p>{lede.join(" ")}</p>
      </SectionIntro>

      <StatGrid cols={4}>
        <Stat label="Market FDV" value={fmtUsdCompact(current)} provenance={{ source: "coingecko", name: "coins_markets" }} hint="Fully diluted, at spot" />
        <Stat label="Model, expected path" value={fmtUsdCompact(base)} hint={gap !== null ? `Market is ${times(gap)} this` : undefined} />
        <Stat label="Model, Monte Carlo median" value={fmtUsdCompact(p50)} hint={isNum(mi.gap_multiple_vs_mc_p50) ? `Market is ${times(mi.gap_multiple_vs_mc_p50)} this` : undefined} />
        <Stat
          label="Levers that close the gap inside evidence"
          value={`${fmtInt(mi.n_within_evidence)} of ${fmtInt(solves.length)}`}
          hint={`${fmtInt(mi.n_reachable)} reachable at any value; one input moved at a time`}
        />
      </StatGrid>

      <div className="space-y-4">
        <SubHead title="What the market is pricing">
          Each input is moved alone, all others at the snapshot base, until the model&apos;s expected-path FDV equals the market FDV. The required value is then set against the comparator this run measured.
        </SubHead>
        <Panel className="valuo-scroll overflow-x-auto px-2 py-1">
          <table className="w-full min-w-[60rem] border-collapse text-[13.5px]">
            <thead>
              <tr>
                {["Lever", "Model base", "Required for market FDV", "Evidence this run", "Required ÷ evidence", "Status"].map((h, i) => (
                  <th key={h} scope="col" className={cn("border-b border-ink/80 px-3 py-2 text-[12.5px] font-medium text-muted", i === 0 || i === 3 || i === 5 ? "text-left" : "text-right")}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {withStatus.map(({ s, status }) => {
                const st = STATUS[status];
                const ref = evidenceRef(s, snapshot.execution_bench);
                const ratio = s.required_vs_evidence?.ratio ?? null;
                return (
                  <Fragment key={s.param}>
                    <tr className="align-top">
                      <td className="px-3 pb-1 pt-3" style={{ width: "15rem" }}>
                        <div className="text-ink">{upperFirst(s.short_label)}</div>
                        <div className="text-[12.5px] leading-snug text-dim">{s.label}</div>
                      </td>
                      <td className="tnum px-3 pb-1 pt-3 text-right text-muted">{fmtUnit(s.base_value, s.unit)}</td>
                      <td className="tnum px-3 pb-1 pt-3 text-right font-semibold text-ink">{isNum(s.required_value) ? fmtUnit(s.required_value, s.unit) : <span className="font-normal text-dim">None in range</span>}</td>
                      <td className="px-3 pb-1 pt-3" style={{ width: "19rem" }}>
                        <div className="tnum text-ink">{fmtUnit(s.evidence?.value, s.unit)}</div>
                        <div className="text-[12.5px] leading-snug text-dim">{s.evidence?.label ?? NA}</div>
                        {ref ? <ProvenanceBadge source={ref.source} name={ref.name} /> : null}
                      </td>
                      <td className="tnum px-3 pb-1 pt-3 text-right text-ink">{isNum(ratio) ? times(ratio) : <span className="text-dim">n/a</span>}</td>
                      <td className="px-3 pb-1 pt-3">
                        <Badge variant={st.variant} dot title={st.hint}>
                          {st.label}
                        </Badge>
                      </td>
                    </tr>
                    <tr className="border-b border-border last:border-b-0">
                      <td colSpan={6} className="px-3 pb-3 pt-1 text-[13px] leading-relaxed text-muted">
                        {s.verdict}
                      </td>
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </Panel>
        {reading.length ? (
          <ul className="max-w-4xl list-disc space-y-1.5 pl-5 text-[14.5px] leading-relaxed text-muted marker:text-dim">
            {reading.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        ) : null}
      </div>

      <MethodNote>
        <p>
          Basis: {mi.basis}. Solver: {mi.solver ?? NA}; each solve is checked by re-running the model at the required value (relative error shown below). Horizon {fmtInt(mi.horizon_months)} months. Fields: <code>market_implied.solves[]</code>,{" "}
          <code>market_implied.current_fdv_usd</code>, <code>market_implied.base_fdv_usd</code>, <code>market_implied.base_fdv_mc_p50_usd</code>.
        </p>
        <p>
          Status: inside evidence when <code>required_vs_evidence.within_evidence</code> is true, outside when false; unreachable when no value in <code>search_bounds</code> reaches the market FDV; a comparator flagged <code>evidence.assumption</code> is not evidence.
        </p>
        <ul className="list-disc space-y-1 pl-5">
          {solves.map((s) => (
            <li key={s.param}>
              <code>{s.param}</code>: search [{fmtUnit(s.search_bounds?.[0], s.unit)}, {fmtUnit(s.search_bounds?.[1], s.unit)}], harder direction {s.harder_direction}; evidence source: {s.evidence?.source ?? NA}
              {isNum(s.check_rel_error) ? `; check error ${s.check_rel_error.toExponential(1)}` : ""}.
            </li>
          ))}
        </ul>
      </MethodNote>
    </section>
  );
}
