import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { fmtBps, fmtCompact, fmtInt, fmtNear, fmtNearCompact, fmtNum, fmtPct, fmtUsdCompact } from "@/lib/format";
import { MethodNote } from "@/components/ui/Section";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { ARCHETYPE_SHORT, VENUE_LABEL, confidentialIsAssumed, fmtEvidenceValue, fmtSolveValue, fmtSpan, fmtTimes, minus, numberWord, rankPhrase, signTone, type LandingData, type SolveView } from "./landingData";
import { LandingSection, SectionHeader, TextLink } from "./SectionHeader";

const TONE_TEXT = { emerald: "text-emerald", crimson: "text-crimson", neutral: "text-ink" } as const;
type Tone = keyof typeof TONE_TEXT;

interface KeyFigure {
  label: string;
  value: string;
  tone?: Tone;
  /** one short line under the value: the evidence it is compared with */
  note?: ReactNode;
}

interface Finding {
  key: string;
  claim: ReactNode;
  figures: KeyFigure[];
  context: ReactNode;
  sources: ReactNode;
  href: string;
  hrefLabel: string;
}

/** What each market-implied solve is compared with, as a short prefix for the figure note. */
const EVIDENCE_PREFIX: Record<string, string> = {
  public_volume_growth_yoy: "Trailing 12 months",
  tau_pub_bps: "Competitive ceiling",
  terminal_multiple: "Peer median",
  holder_revenue_scale: "Today",
  discount_rate: "Registry low",
  confidential_share_target: "Assumed",
};
const fmtX = (v: number | null | undefined) => fmtSolveValue("x", v ?? null);
const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

const B = ({ children }: { children: ReactNode }) => <span className="tnum">{children}</span>;

/**
 * Numbered findings in prose-plus-figure form. Each claim is a sentence assembled from snapshot
 * values and phrased conditionally, so it stays true when a sign flips. The first two findings
 * frame the market price (what it requires of Intents cash flow; where it sits among peer L1s);
 * the rest are the measured strengths and weaknesses, which carry equal weight.
 */
export function Findings({ data }: { data: LandingData }) {
  const { issuance, stateLock, volume, fees, concentration, supply, sotp, bench, chain } = data;
  const findings: Finding[] = [];
  const mi = data.marketImplied;
  const rv = data.relativeValue;

  // 1. What the market is pricing (market_implied).
  if (mi && mi.currentFdv !== null && mi.baseFdv !== null) {
    const gap = mi.gapMultiple;
    const reachable = mi.solves.filter((x) => x.reachable && x.requiredValue !== null);
    const within = reachable.filter((x) => x.withinEvidence === true);
    const outside = reachable.filter((x) => x.withinEvidence === false && !x.evidenceIsAssumption);
    const assumed = reachable.filter((x) => x.evidenceIsAssumption);
    const unreachable = mi.solves.filter((x) => !x.reachable);
    const shown = [...outside, ...within].slice(0, 4);
    const nLevers = mi.solves.length;
    const fig = (x: SolveView): KeyFigure => ({
      label: `Required ${x.shortLabel}`,
      value: fmtSolveValue(x.unit, x.requiredValue),
      note: (
        <>
          {EVIDENCE_PREFIX[x.param] ?? "Measured"} <B>{fmtEvidenceValue(x)}</B>
          {x.param === "terminal_multiple" && x.modelCap !== null ? <>; model cap <B>{fmtSolveValue("x", x.modelCap)}</B></> : null}
        </>
      ),
    });
    const ratioRange = (xs: SolveView[]) => {
      const r = xs.map((x) => x.ratio).filter((v): v is number => v !== null);
      if (!r.length) return "more than";
      const lo = Math.min(...r);
      const hi = Math.max(...r);
      return lo === hi ? `${fmtTimes(lo)}` : `${fmtTimes(lo)} to ${fmtTimes(hi)}`;
    };
    const listShort = (xs: SolveView[]) => xs.map((x) => x.shortLabel).join(", ").replace(/, ([^,]*)$/, " and $1");
    findings.push({
      key: "market",
      claim:
        gap === null ? (
          <>The market-implied solve returned no gap multiple this run.</>
        ) : gap > 1 ? (
          <>
            The market values NEAR at <B>{fmtTimes(gap)}</B> what Intents cash flow supports on the model&apos;s expected path;{" "}
            {within.length === 0 ? (
              <>no single lever closes that gap inside measured evidence.</>
            ) : (
              <>
                of {numberWord(nLevers).toLowerCase()} levers, only the {listShort(within)} closes it inside measured evidence.
              </>
            )}
          </>
        ) : (
          <>
            The model&apos;s expected path, <B>{fmtUsdCompact(mi.baseFdv)}</B>, is at or above the market&apos;s <B>{fmtUsdCompact(mi.currentFdv)}</B>: Intents cash flow alone carries the price.
          </>
        ),
      figures: shown.length ? shown.map(fig) : [{ label: "Expected-path FDV", value: fmtUsdCompact(mi.baseFdv) }],
      context: (
        <>
          Market FDV <B>{fmtUsdCompact(mi.currentFdv)}</B> against an expected-path value of <B>{fmtUsdCompact(mi.baseFdv)}</B> over <B>{fmtInt(mi.horizonMonths)}</B> months. Each lever is
          solved for the value that matches the market with every other input at base.{" "}
          {outside.length ? (
            <>
              {cap(listShort(outside))} would each need {ratioRange(outside)} what the data shows today.{" "}
            </>
          ) : null}
          {within.map((x) =>
            x.modelCap !== null ? (
              <span key={x.param}>
                The {x.shortLabel} needed, <B>{fmtSolveValue(x.unit, x.requiredValue)}</B>, is below where peers trade (<B>{fmtEvidenceValue(x)}</B>
                {x.peers.length ? `, n = ${x.peers.length}` : ""}), but the model caps it at <B>{fmtSolveValue(x.unit, x.modelCap)}</B>, which is consistent with the market pricing NEAR as a layer 1
                rather than as an Intents cash-flow stream.{" "}
              </span>
            ) : (
              <span key={x.param}>
                The {x.shortLabel} needed, <B>{fmtSolveValue(x.unit, x.requiredValue)}</B>, is within the measured <B>{fmtEvidenceValue(x)}</B>.{" "}
              </span>
            ),
          )}
          {assumed.map((x) => (
            <span key={x.param}>
              The {x.shortLabel} would need to reach <B>{fmtSolveValue(x.unit, x.requiredValue)}</B>; it is not measured this run (the model assumes <B>{fmtEvidenceValue(x)}</B>).{" "}
            </span>
          ))}
          {unreachable.map((x) => (
            <span key={x.param}>{x.verdict ?? `No ${x.shortLabel} closes the gap${x.reason ? `: ${x.reason}` : ""}.`} </span>
          ))}
          The seeded Monte Carlo median is <B>{fmtUsdCompact(mi.baseFdvMcP50)}</B> (10th to 90th percentile <B>{fmtUsdCompact(sotp.fdv.p10)}</B> to <B>{fmtUsdCompact(sotp.fdv.p90)}</B>); the
          solves run on the expected path.
        </>
      ),
      sources: (
        <>
          <ProvenanceBadge source="nearstats" name="summary" label="NearStats price" />
          <ProvenanceBadge source="defillama" name="dexs:near-intents" />
        </>
      ),
      href: "/terminal#sotp",
      hrefLabel: "Market-implied solves and sensitivities",
    });
  }

  // 2. Relative value against peer L1s (relative_value).
  const fr = rv?.feesRunRate ?? null;
  if (rv && fr && fr.value !== null) {
    const rr = rv.revenueRunRate;
    const band = rv.impliedFees;
    const rank = rankPhrase(fr);
    const below = fr.peerMedian !== null ? fr.value < fr.peerMedian : null;
    findings.push({
      key: "relative",
      claim: (
        <>
          Against peer layer 1s NEAR trades at <B>{fmtX(fr.value)}</B> annualised fees, {rank ?? "unranked"}
          {below === null ? "." : below ? <>, below the peer median of <B>{fmtX(fr.peerMedian)}</B>.</> : <>, above the peer median of <B>{fmtX(fr.peerMedian)}</B>.</>}
        </>
      ),
      figures: [
        { label: "FDV to fees, NEAR", value: fmtX(fr.value), note: <>Peer median <B>{fmtX(fr.peerMedian)}</B></> },
        ...(rr && rr.value !== null ? [{ label: "FDV to revenue, NEAR", value: fmtX(rr.value), note: <>Peer median <B>{fmtX(rr.peerMedian)}</B></> }] : []),
        ...(band && band.median !== null ? [{ label: "Fees at the peer median multiple", value: fmtUsdCompact(band.median), note: <>Market FDV <B>{fmtUsdCompact(mi?.currentFdv ?? data.sotp.currentFdv)}</B></> }] : []),
      ],
      context: (
        <>
          Peers: {rv.peerSymbols.join(", ") || "n/a"}, with fees and revenue from DefiLlama and FDV from CoinGecko; NEAR counts L1 gas and Intents fees together (
          <B>{fmtUsdCompact(rv.nearFeesUsd)}</B> a year).{" "}
          {rr && rr.value !== null ? (
            <>
              On revenue NEAR is at <B>{fmtX(rr.value)}</B>, {rankPhrase(rr) ?? "unranked"}.{" "}
            </>
          ) : null}
          {band && band.p25 !== null && band.p75 !== null ? (
            <>
              At the peers&apos; FDV-to-fees multiples, NEAR&apos;s fees map to <B>{fmtUsdCompact(band.p25)}</B> to <B>{fmtUsdCompact(band.p75)}</B>: a cross-check on how the market prices
              layer 1s, not a fair value.{" "}
            </>
          ) : null}
          {rv.nPeersAtOrBelowModel !== null && rv.modelTerminalMultiple !== null ? (
            <>
              {rv.nPeersAtOrBelowModel === 0 ? "None" : numberWord(rv.nPeersAtOrBelowModel)} of the <B>{fmtInt(rv.nPeers)}</B> peers {rv.nPeersAtOrBelowModel === 1 ? "trades" : "trade"} at or below the model&apos;s <B>{fmtX(rv.modelTerminalMultiple)}</B> terminal multiple.{" "}
            </>
          ) : null}
          {rv.securityBudgetUsd !== null && rv.revenueToSecurityBudget !== null ? (
            <>
              The weak side: issuance pays stakers <B>{fmtUsdCompact(rv.securityBudgetUsd)}</B> a year, and holder revenue covers <B>{fmtPct(rv.revenueToSecurityBudget, { decimals: 0 })}</B> of it.
            </>
          ) : null}
        </>
      ),
      sources: (
        <>
          <ProvenanceBadge source="defillama" name="fees:solana:dailyFees" />
          <ProvenanceBadge source="coingecko" name="coins_markets" />
        </>
      ),
      href: "/terminal#sotp",
      hrefLabel: "Peer comparables",
    });
  }

  // 3. Execution microstructure.
  if (bench) {
    const archs = ["cross_vm", "native_btc", "evm_l2"].filter((a) => a in bench.headroom);
    const venueOf = (a: string) => {
      const v = bench.corridors.find((c) => c.archetype === a)?.bestCompetitor ?? null;
      return v ? (VENUE_LABEL[v] ?? v) : null;
    };
    const cross = bench.headroom.cross_vm ?? null;
    const losing = archs.filter((a) => a !== "cross_vm" && (bench.headroom[a] ?? 0) < 0);
    const losingText = losing.map((a) => `${ARCHETYPE_SHORT[a] ?? a}${venueOf(a) ? ` (vs ${venueOf(a)})` : ""}`).join(" and ");
    const clips = bench.corridors[0]?.clipsUsd.map((c) => fmtUsdCompact(c, { decimals: 0 })) ?? [];
    findings.push({
      key: "execution",
      claim:
        cross === null ? (
          <>The quote benchmark found no comparable cross-VM cell in this run.</>
        ) : cross > 0 ? (
          <>
            1Click delivers more than the best competitor on cross-VM routes{losing.length ? <>, but trails on {losingText}.</> : <> and on every other corridor measured.</>}
          </>
        ) : (
          <>
            1Click does not out-deliver the best competitor on cross-VM routes{losing.length ? <>, and also trails on {losingText}.</> : "."}
          </>
        ),
      figures: archs.map((a) => ({ label: `Headroom, ${ARCHETYPE_SHORT[a] ?? a}`, value: minus(fmtBps(bench.headroom[a] ?? null, { decimals: 2 })), tone: signTone(bench.headroom[a] ?? null) })),
      context: (
        <>
          Identical dry quotes{clips.length ? ` at ${clips.join(", ")}` : ""} sent to 1Click, Relay, LI.FI and Across, compared on units delivered at the destination.
          Competitor friction on cross-VM routes caps a sustainable fee at <B>{fmtBps(bench.ceilingBps, { decimals: 2, signed: false })}</B>; {fmtInt(bench.quotesOk)} of{" "}
          {fmtInt(bench.quotesTotal)} quotes returned.
        </>
      ),
      sources: (
        <>
          <ProvenanceBadge source="oneclick" name={`quote:${bench.corridors[0]?.id ?? ""}:50000`} />
          <ProvenanceBadge source="relay" name={`quote:${bench.corridors[0]?.id ?? ""}:50000`} />
        </>
      ),
      href: "/terminal#execution",
      hrefLabel: "Quote race and corridor matrix",
    });
  }

  // 4. Supply coverage.
  const covers = supply.coverageRatio >= 1;
  const vNow = supply.dailyVolumeNow;
  const times = (v: number | undefined) => (v !== undefined && vNow ? v / vNow : null);
  const pq = supply.mcCrossoverProb.status_quo ?? null;
  const pg = supply.mcCrossoverProb.svrn_glidepath ?? null;
  findings.push({
    key: "supply",
    claim: covers ? (
      <>
        Buybacks, gas burn and storage locks now absorb more NEAR than the protocol issues: <B>{fmtPct(supply.coverageRatio, { decimals: 1 })}</B> of issuance.
      </>
    ) : (
      <>
        Buybacks, gas burn and storage locks offset only <B>{fmtPct(supply.coverageRatio, { decimals: 1 })}</B> of realized issuance; net supply still grows.
      </>
    ),
    figures: [
      { label: "Sinks as a share of issuance", value: fmtPct(supply.coverageRatio, { decimals: 1 }), tone: covers ? "emerald" : "crimson" },
      { label: "Sinks vs issuance, per day", value: `${fmtCompact(supply.sinks.total, { decimals: 1 })} / ${fmtNearCompact(supply.issuanceDaily, { decimals: 1 })}` },
    ],
    context: (
      <>
        Break-even needs <B>{fmtUsdCompact(supply.breakeven.status_quo)}</B> of daily Intents volume under the current <B>{fmtPct(chain.inflationCap, { decimals: 1 })}</B> cap (<B>{fmtTimes(times(supply.breakeven.status_quo))}</B> today&apos;s{" "}
        <B>{fmtUsdCompact(vNow)}</B>) or <B>{fmtUsdCompact(supply.breakeven.svrn_glidepath)}</B> under the SVRN glidepath (<B>{fmtTimes(times(supply.breakeven.svrn_glidepath))}</B>). The
        simulation puts the chance of a crossover within 36 months at <B>{fmtPct(pq, { decimals: 1 })}</B> and <B>{fmtPct(pg, { decimals: 1 })}</B> respectively.
      </>
    ),
    sources: (
      <>
        <ProvenanceBadge source="near_rpc" name={`block:${issuance.epochStartHeight}`} />
        <ProvenanceBadge source="defillama" name="fees:near-intents" />
      </>
    ),
    href: "/terminal#supply",
    hrefLabel: "Issuance crossover",
  });

  // 5. Storage-staking lock.
  const g = stateLock.intentsGrowthNearPerDay;
  const lockShare = supply.sinks.stateLock !== null && supply.issuanceDaily > 0 ? supply.sinks.stateLock / supply.issuanceDaily : null;
  const kbPerNear = stateLock.storageNearPerKb > 0 ? 1 / stateLock.storageNearPerKb : null;
  findings.push({
    key: "lock",
    claim:
      stateLock.intentsLocked === null ? (
        <>The intents.near storage lock could not be read in this run.</>
      ) : (
        <>
          intents.near holds <B>{fmtNear(stateLock.intentsLocked)}</B> as storage stake
          {g === null ? "." : g > 0 ? ", and the lock grows with every new account and balance it stores." : g < 0 ? ", and the lock shrank over the measured window." : ", flat over the measured window."}
        </>
      ),
    figures: [
      { label: "Locked by intents.near", value: fmtNear(stateLock.intentsLocked) },
      { label: "Change per day", value: g === null ? "Not measured" : minus(fmtNear(g, { signed: true, decimals: 1 })), tone: signTone(g) },
    ],
    context: (
      <>
        The protocol charges {kbPerNear !== null ? <>1 NEAR per <B>{fmtInt(kbPerNear)}</B> KB</> : "a fixed amount of NEAR per KB"} of contract state, released only when the state is
        deleted. Across <B>{fmtInt(stateLock.sinkCount)}</B> tracked contracts <B>{fmtNear(stateLock.totalLocked)}</B> is locked; the growth offsets{" "}
        <B>{fmtPct(lockShare, { decimals: 2 })}</B> of daily issuance, a real but small sink.
      </>
    ),
    sources: <ProvenanceBadge source="near_rpc" name="view_account:intents.near" />,
    href: "/terminal#supply",
    hrefLabel: "State-lock audit",
  });

  // 6. Volume and take rate.
  findings.push({
    key: "fees",
    claim: (
      <>
        Intents cleared <B>{fmtUsdCompact(volume.d30)}</B> in 30 days and NEAR kept <B>{fmtBps(fees.netTakeBps, { decimals: 2, signed: false })}</B> of it as net revenue.
      </>
    ),
    figures: [
      { label: "Intents volume, 30 days", value: fmtUsdCompact(volume.d30) },
      { label: "Net take rate", value: fmtBps(fees.netTakeBps, { decimals: 2, signed: false }) },
    ],
    context: (
      <>
        Gross fees were <B>{fmtBps(fees.grossTakeBps, { decimals: 2, signed: false })}</B>, of which <B>{fmtPct(fees.captureRatio, { decimals: 1 })}</B> reached the buyback.{" "}
        {confidentialIsAssumed(volume) ? (
          <>
            The confidential share is not measured this run: NearStats reported <B>{fmtPct(volume.confidentialShareReported, { decimals: 2 })}</B> against{" "}
            <B>{fmtUsdCompact(volume.confidentialTvl)}</B> of confidential TVL, so the model falls back to an assumed <B>{fmtPct(volume.confidentialShare30d, { decimals: 0 })}</B>.{" "}
          </>
        ) : volume.confidentialShare30d !== null ? (
          <>
            <B>{fmtPct(volume.confidentialShare30d, { decimals: 1 })}</B> of volume ran through confidential execution.{" "}
          </>
        ) : null}
        {volume.drawdownFromRecord30d !== null && volume.drawdownFromRecord30d > 0 ? (
          <>
            Volume is <B>{fmtPct(volume.drawdownFromRecord30d, { decimals: 1 })}</B> below its 30-day record.
          </>
        ) : null}
      </>
    ),
    sources: (
      <>
        <ProvenanceBadge source="nearstats" name="summary" />
        <ProvenanceBadge source="defillama" name="fees:near-intents:dailyRevenue" />
      </>
    ),
    href: "/terminal#thesis",
    hrefLabel: "Thesis and scorecard",
  });

  // 7. Solver concentration.
  const cartel = data.bear.scenarios.find((s) => s.key === "solver_cartelization") ?? null;
  const hhi = concentration.hhiSolver;
  const trig = concentration.cartelTriggerHhi ?? cartel?.threshold ?? null;
  const ci = cartel?.hhiCi90 ?? concentration.hhiSolverCi90;
  const span = cartel?.sampleSpanS ?? concentration.sampleSpanS;
  const minSpan = cartel?.minSampleSpanS ?? null;
  const inconclusive = cartel?.status === "inconclusive";
  const ciVsTrig = ci && trig !== null ? (ci[0] > trig ? "above" : ci[1] < trig ? "below" : "straddles") : null;
  findings.push({
    key: "solvers",
    claim:
      hhi === null ? (
        <>No sampled fills could be attributed to solvers in this run, so solver concentration is not measured.</>
      ) : (
        <>
          {numberWord(concentration.uniqueSolvers)} solvers shared the sampled fills, at an HHI of <B>{fmtInt(hhi)}</B>
          {inconclusive ? <>; the sample is too short to grade the cartel trigger.</> : trig !== null ? <>, {hhi > trig ? "above" : "below"} the <B>{fmtInt(trig)}</B> cartel trigger.</> : "."}
        </>
      ),
    figures: [
      { label: "Solver HHI", value: hhi === null ? "Not measured" : fmtInt(hhi), note: ci ? <>90% CI <B>{fmtInt(ci[0])}</B> to <B>{fmtInt(ci[1])}</B></> : undefined },
      {
        label: "Sample span",
        value: fmtSpan(span),
        tone: undefined,
        note: minSpan !== null ? <>Minimum to grade <B>{fmtSpan(minSpan)}</B></> : <>{fmtInt(concentration.solverFillsAttributed)} fill participations</>,
      },
    ],
    context: (
      <>
        {hhi !== null && ci ? (
          <>
            Over <B>{fmtInt(concentration.solverFillsAttributed)}</B> fill participations the bootstrap 90% interval is <B>{fmtInt(ci[0])}</B> to <B>{fmtInt(ci[1])}</B>
            {trig !== null && ciVsTrig ? (ciVsTrig === "straddles" ? <>, which straddles the <B>{fmtInt(trig)}</B> trigger. </> : <>, {ciVsTrig} the <B>{fmtInt(trig)}</B> trigger. </>) : ". "}
          </>
        ) : null}
        {inconclusive && span !== null && minSpan !== null ? (
          <>
            The fills span <B>{fmtSpan(span)}</B> of settlement, under the <B>{fmtSpan(minSpan)}</B> minimum: one short window is serially correlated and its interval covers only
            within-window noise, so the trigger is reported as inconclusive, neither breached nor clear.{" "}
          </>
        ) : null}
        On the deposit side, caller HHI is <B>{fmtInt(concentration.hhiExternal)}</B> (about <B>{fmtNum(concentration.nEffExternal, { decimals: 1 })}</B> equal-sized callers) and AI
        agents account for <B>{fmtPct(concentration.aiAgentShare, { decimals: 1 })}</B> of <B>{fmtInt(concentration.receiptsSampled)}</B> sampled receipts.
      </>
    ),
    sources: <ProvenanceBadge source="nearblocks" name="txns:intents.near:p1" />,
    href: "/terminal#execution",
    hrefLabel: "Solver audit",
  });

  return (
    <LandingSection id="findings">
      <SectionHeader
        number="1"
        eyebrow="Findings"
        title="What the market is pricing, and what the chain and order books show"
        lede={
          <>
            {numberWord(findings.length)} findings from the snapshot pinned at block <span className="tnum">{fmtInt(chain.block)}</span>: first what the market price requires, then the measured
            strengths and weaknesses with equal weight. Each sentence is assembled from measured values and rewrites itself when a sign flips.
          </>
        }
      />

      <ol className="mt-14 border-t border-border-strong">
        {findings.map((f, i) => (
          <li key={f.key} className="grid grid-cols-[minmax(0,1fr)] gap-x-10 gap-y-6 border-b border-border py-10 lg:grid-cols-[3rem_minmax(0,1fr)_17rem]">
            <div className="tnum font-serif text-[22px] leading-none text-dim">{String(i + 1).padStart(2, "0")}</div>
            <div className="min-w-0 max-w-3xl">
              <h3 className="font-serif text-[24px] font-medium leading-[1.3] text-ink sm:text-[26px]">{f.claim}</h3>
              <p className="mt-4 text-[15.5px] leading-relaxed text-muted">{f.context}</p>
              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-dim">
                <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span>Source</span>
                  {f.sources}
                </span>
                <TextLink href={f.href} className="text-[13px]">
                  {f.hrefLabel}
                </TextLink>
              </div>
            </div>
            <dl className="grid grid-cols-[minmax(0,1fr)] content-start gap-5 sm:grid-cols-2 lg:grid-cols-1 lg:border-l lg:border-border lg:pl-8">
              {f.figures.map((k) => (
                <div key={k.label}>
                  <dt className="text-[13px] text-muted">{k.label}</dt>
                  <dd className={cn("tnum mt-1 text-[26px] font-medium leading-none tracking-tight", TONE_TEXT[k.tone ?? "neutral"])}>{k.value}</dd>
                  {k.note ? <dd className="mt-1.5 text-[13px] leading-snug text-dim">{k.note}</dd> : null}
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ol>

      <MethodNote className="mt-10">
        <p>
          Headroom is <code>execution_bench.headroom_by_archetype_bps</code>, the median over comparable cells (
          {Object.entries(bench?.headroomN ?? {})
            .map(([a, n]) => `${a} n=${n}`)
            .join(", ") || "none"}
          ) on basis <code>{bench?.headroomBasis ?? "n/a"}</code>.{bench?.headroomDefinition ? ` ${bench.headroomDefinition}` : ""}
        </p>
        <p>
          Coverage is <code>supply_physics.sink_coverage_ratio</code>: buyback {fmtNear(supply.sinks.buyback)} (DefiLlama holders revenue at spot) + gas burn {fmtNear(supply.sinks.gasBurn)}{" "}
          (within-epoch supply drift) + state lock {fmtNear(supply.sinks.stateLock)} (archival growth), over measured issuance {fmtNear(supply.issuanceDaily)} a day. Break-even is{" "}
          <code>supply_physics.breakeven_daily_volume_usd</code>; crossover odds are <code>sotp.crossover_month_distribution.*.p_crossover_within_36m</code>.
        </p>
        <p>
          The state lock is <code>near_rpc.tracked_sinks[intents.near].storage_locked_near</code> = storage_usage × <code>storage_amount_per_byte</code>; growth is measured against archival
          state over {fmtNum(stateLock.intentsGrowthWindowDays, { decimals: 1 })} days.
        </p>
        <p>
          Market-implied solves are <code>market_implied.solves</code>: Brent root-finding on the deterministic engine&apos;s expected path ({mi?.basis ?? "one input moved at a time"}), each
          required value compared with <code>evidence.value</code>. Relative value is <code>relative_value.coverage</code> (rank 1 = lowest multiple) and{" "}
          <code>implied_fdv_band.fees</code>.{rv?.caveat ? ` ${rv.caveat}` : ""}
        </p>
        <p>
          Monte Carlo percentiles are <code>sotp.fdv_percentiles</code> (model output, no single payload). Market FDV basis: <code>{sotp.currentFdvBasis ?? "spot × on-chain total supply"}</code>
          {sotp.priceSource ? (
            <>
              , price from <code>{sotp.priceSource}</code>
            </>
          ) : null}
          . Total supply {fmtNum(chain.totalSupply / 1e9, { decimals: 4 })}B NEAR at the pinned block.
        </p>
        <p>
          Take rates are <code>intents_forensics.fees.gross_take_bps</code> and <code>net_take_bps</code> over aligned 30-day DefiLlama series. Solver HHI is{" "}
          <code>intents_forensics.solver_concentration.hhi_solver</code> over NEP-413 signers of <code>execute_intents</code> fills ({fmtInt(concentration.solverFillsAttributed)} fill
          participations; interval <code>hhi_solver_ci90</code>); the cartel trigger reads <code>bear_case.scenarios[solver_cartelization].trigger_status</code>
          {cartel?.status ? <> = <code>{cartel.status}</code></> : null}. Caller HHI is <code>hhi_external</code> over {fmtInt(concentration.pagesFetched)} NearBlocks pages.
          {volume.confidentialShareStatus ? (
            <>
              {" "}Confidential share status: <code>intents_forensics.volume.confidential_share_status</code> = <code>{volume.confidentialShareStatus}</code>.
            </>
          ) : null}
        </p>
      </MethodNote>
    </LandingSection>
  );
}
