import type { ReactNode } from "react";
import { fmtBps, fmtInt, fmtNear, fmtNum, fmtPct, fmtUsdCompact } from "@/lib/format";
import { MethodNote } from "@/components/ui/Section";
import { ARCHETYPE_SHORT, REGIME_LABEL, VENUE_LABEL, fmtSolveValue, fmtSpan, minus, solveByParam, type LandingData } from "./landingData";
import { LandingSection, SectionHeader, TextLink } from "./SectionHeader";

const N = ({ children }: { children: ReactNode }) => <span className="tnum font-medium text-ink">{children}</span>;

/**
 * The four Investment Committee questions that volume dashboards leave open, each with the live
 * answer from the snapshot. Corridors where 1Click trails are named from the data.
 */
export function Questions({ data }: { data: LandingData | null }) {
  const b = data?.bench ?? null;
  const none = "No snapshot on disk yet; run make reproduce.";

  const take = data ? solveByParam(data, "tau_pub_bps") : null;
  let a1: ReactNode = data ? "The snapshot was built without the quote benchmark (--skip-bench)." : none;
  if (b) {
    const parts = Object.entries(b.headroom)
      .filter(([, h]) => h !== null)
      .map(([arch, h]) => {
        const v = b.corridors.find((c) => c.archetype === arch)?.bestCompetitor ?? null;
        return { arch, h: h as number, venue: v ? (VENUE_LABEL[v] ?? v) : null };
      });
    const lead = parts.filter((p) => p.h > 0);
    const trail = parts.filter((p) => p.h < 0);
    a1 = (
      <>
        {lead.length ? (
          <>
            Not on the evidence so far. 1Click delivers more than the best competitor on {lead.map((p, i) => (
              <span key={p.arch}>
                {i ? " and " : ""}
                {ARCHETYPE_SHORT[p.arch] ?? p.arch} (<N>{minus(fmtBps(p.h, { decimals: 2 }))}</N>)
              </span>
            ))}
            {trail.length ? ", " : "."}
          </>
        ) : (
          <>The evidence does not show a moat in this run{trail.length ? ": " : "."}</>
        )}
        {trail.length ? (
          <>
            {lead.length ? "but trails on " : "1Click trails on "}
            {trail.map((p, i) => (
              <span key={p.arch}>
                {i ? " and " : ""}
                {ARCHETYPE_SHORT[p.arch] ?? p.arch} (<N>{minus(fmtBps(p.h, { decimals: 2 }))}</N>
                {p.venue ? ` vs ${p.venue}` : ""})
              </span>
            ))}
            . The advantage is corridor-specific.
          </>
        ) : null}
        {take && take.requiredValue !== null && take.evidenceValue !== null ? (
          <>
            {" "}Carrying the market price on take rate alone would need a starting public take of <N>{fmtSolveValue("bps", take.requiredValue)}</N>, against{" "}
            <N>{fmtSolveValue("bps", take.baseValue)}</N> today and a <N>{fmtSolveValue("bps", take.evidenceValue)}</N> competitive ceiling
            {take.requiredValue > take.evidenceValue ? ", so the price cannot rest on fee expansion." : "."}
          </>
        ) : null}
      </>
    );
  }

  const c = data?.concentration;
  const cartel = data?.bear.scenarios.find((x) => x.key === "solver_cartelization") ?? null;
  const a2: ReactNode = c ? (
    <>
      Deposit-side callers are {c.hhiExternal > 2500 ? "highly concentrated" : c.hhiExternal > 1500 ? "moderately concentrated" : "unconcentrated"}: HHI <N>{fmtInt(c.hhiExternal)}</N>, roughly <N>{fmtNum(c.nEffExternal, { decimals: 1 })}</N> equal-sized callers, with AI agents at{" "}
      <N>{fmtPct(c.aiAgentShare, { decimals: 1 })}</N>.{" "}
      {c.hhiSolver === null ? "On the solver side, " : c.hhiSolver < c.hhiExternal ? "The solver side is less concentrated: " : "The solver side is at least as concentrated: "}
      {c.hhiSolver === null ? (
        "no fills were attributed this run."
      ) : (
        <>
          HHI <N>{fmtInt(c.hhiSolver)}</N>
          {c.hhiSolverCi90 ? (
            <>
              {" "}(90% CI <N>{fmtInt(c.hhiSolverCi90[0])}</N> to <N>{fmtInt(c.hhiSolverCi90[1])}</N>)
            </>
          ) : null}{" "}
          across <N>{fmtInt(c.uniqueSolvers)}</N> solvers in <N>{fmtInt(c.solverFills)}</N> sampled fills
          {cartel?.status === "inconclusive" ? (
            <>
              , over <N>{fmtSpan(cartel.sampleSpanS ?? c.sampleSpanS)}</N>: too short a window to grade the cartel trigger, so it is reported as inconclusive.
            </>
          ) : (
            "."
          )}
        </>
      )}
    </>
  ) : (
    none
  );

  const s = data?.stateLock;
  const a3: ReactNode = s ? (
    <>
      Storage staking. intents.near alone holds <N>{fmtNear(s.intentsLocked)}</N>
      {s.intentsGrowthNearPerDay !== null ? (
        <>
          , growing <N>{minus(fmtNear(s.intentsGrowthNearPerDay, { signed: true, decimals: 1 }))}</N> a day
        </>
      ) : (
        " (growth not measured: archival RPC unavailable)"
      )}
      ; <N>{fmtInt(s.sinkCount)}</N> tracked contracts hold <N>{fmtNear(s.totalLocked)}</N>.
    </>
  ) : (
    none
  );

  const sp = data?.supply;
  const a4: ReactNode = sp ? (
    <>
      Daily Intents volume of <N>{fmtUsdCompact(sp.breakeven.status_quo)}</N> under {REGIME_LABEL.status_quo}, or <N>{fmtUsdCompact(sp.breakeven.svrn_glidepath)}</N> under{" "}
      {REGIME_LABEL.svrn_glidepath}, at today&apos;s take and capture. Trailing volume is <N>{fmtUsdCompact(sp.dailyVolumeNow)}</N> a day, and sinks cover{" "}
      <N>{fmtPct(sp.coverageRatio, { decimals: 1 })}</N> of issuance.
    </>
  ) : (
    none
  );

  const items: Array<{ q: string; a: ReactNode; href: string; link: string }> = [
    { q: "Will competing bridges compress the Intents take rate to zero?", a: a1, href: "/terminal#execution", link: "Execution tab" },
    { q: "Who actually settles on intents.near, and how concentrated is that flow?", a: a2, href: "/terminal#execution", link: "Solver audit" },
    { q: "Where is the supply sink that token models leave out?", a: a3, href: "/terminal#supply", link: "Supply tab" },
    { q: "What has to happen for net supply to start shrinking?", a: a4, href: "/terminal#supply", link: "Crossover model" },
  ];

  return (
    <LandingSection id="questions">
      <SectionHeader
        number="2"
        eyebrow="Committee questions"
        title="Headline volume is not an investment thesis"
        lede="revenue.near.org, nearstats.org and svrn.net already chart Intents volume and cumulative fees. Valuo takes those as inputs and answers the four questions a committee asks before sizing a position."
      />

      <div className="mt-14 grid gap-x-16 gap-y-12 border-t border-border-strong pt-12 md:grid-cols-2">
        {items.map((it, i) => (
          <article key={it.q} className="flex min-w-0 flex-col">
            <div className="tnum text-[13px] text-dim">Question {i + 1}</div>
            <h3 className="mt-2 font-serif text-[23px] font-medium leading-[1.3] text-ink">{it.q}</h3>
            <p className="mt-4 flex-1 text-[15.5px] leading-relaxed text-muted">{it.a}</p>
            <TextLink href={it.href} className="mt-4 text-[14px]">
              {it.link}
            </TextLink>
          </article>
        ))}
      </div>

      <MethodNote className="mt-14" summary="How each question is measured">
        <p>
          <span className="text-ink">Question 1.</span> Identical dry quotes go to 1Click, Relay, LI.FI and Across across three corridor archetypes and three clip sizes. Headroom = (1Click output
          − best competitor output) / best competitor output, on physical destination units, in basis points, with no price oracle in the comparison.
          {b?.headroomDefinition ? ` Snapshot definition: ${b.headroomDefinition}` : ""}
        </p>
        <p>
          <span className="text-ink">Question 2.</span> Predecessor accounts of recent <code>intents.near</code> receipts are classified (AI escrow agents, bridge relayers, implicit accounts,
          named users) for the deposit-side <code>hhi_external</code> and the AI-agent share. NEP-413 signers of <code>execute_intents</code> fills give <code>hhi_solver</code>, the index the
          cartel trigger reads.{c ? ` ${fmtInt(c.receiptsSampled)} receipts and ${fmtInt(c.solverFills)} fills this run; both indices move between runs.` : ""}
        </p>
        <p>
          <span className="text-ink">Question 3.</span> <code>storage_usage</code> from <code>view_account</code> × <code>storage_amount_per_byte</code> from <code>protocol_config</code>;
          growth from archival state.
        </p>
        <p>
          <span className="text-ink">Question 4.</span> Solve for the daily volume at which buybacks, gas burn and state-lock growth offset realized issuance under each regime (
          <code>supply_physics.breakeven_daily_volume_usd</code>), then run the same system stochastically.
        </p>
      </MethodNote>
    </LandingSection>
  );
}
