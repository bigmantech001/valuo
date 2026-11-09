import type { ReactNode } from "react";
import Link from "next/link";
import { fmtBlock, fmtBps, fmtInt, fmtNear, fmtNum, fmtUsdCompact, fmtUtc } from "@/lib/format";
import { explorerBlockUrl } from "@/lib/manifestIndex";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { VENUE_LABEL, bindingSolve, fmtEvidenceValue, fmtSolveValue, fmtTimes, minus, rankPhrase, signTone, solveByParam, type LandingData } from "./landingData";

const TONE_TEXT = { emerald: "text-emerald", crimson: "text-crimson", neutral: "text-ink" } as const;

/**
 * Above the fold: the question the page answers (what the market price requires), a lede built
 * from market_implied and relative_value, two calls to action and a key-figures panel pinned to
 * the snapshot's mainnet block. Every figure is read from the snapshot.
 */
export function Hero({ data }: { data: LandingData | null }) {
  return (
    <section className="border-b border-border">
      <div className="mx-auto grid max-w-none gap-14 px-6 lg:px-[5vw] pb-20 pt-16 sm:pt-20 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-16 lg:pb-24 lg:pt-24">
        <div className="flex min-w-0 flex-col justify-center">
          <p className="text-[14px] text-muted">NEAR Hackathon 2026 &middot; Investment thesis track</p>
          <h1 className="mt-5 max-w-[18ch] font-serif text-[42px] font-medium leading-[1.06] tracking-tight text-ink sm:text-[54px] lg:text-[58px]">
            What NEAR&apos;s market value requires, and what the data shows.
          </h1>
          <p className="mt-7 max-w-[38rem] text-[17px] leading-[1.65] text-muted">{data ? <Lede data={data} /> : <>Valuo measures NEAR&apos;s execution, supply and fee data from public endpoints and solves for what the market price assumes. Generate a snapshot to see the figures.</>}</p>
          <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3">
            <Link
              href="/terminal"
              className="inline-flex items-center rounded-md bg-ink px-5 py-2.5 text-[15px] font-medium text-surface transition-colors hover:bg-ink/85 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
            >
              Open the terminal
            </Link>
            {data ? (
              <a href="/api/snapshot?format=memo" download className="text-[15px] text-accent underline-offset-4 hover:underline">
                Read the IC memo
              </a>
            ) : (
              <a href="#reproduce" className="text-[15px] text-accent underline-offset-4 hover:underline">
                Generate a snapshot
              </a>
            )}
          </div>
        </div>

        <KeyFigures data={data} />
      </div>
    </section>
  );
}

const T = ({ children }: { children: ReactNode }) => <span className="tnum text-ink">{children}</span>;

/**
 * The lede, assembled from market_implied and relative_value. Each clause is conditional on the
 * sign or rank it describes, so the paragraph stays true when the numbers move.
 */
function Lede({ data }: { data: LandingData }) {
  const mi = data.marketImplied;
  const fees = data.relativeValue?.feesRunRate ?? null;
  const rank = rankPhrase(fees);
  const bind = bindingSolve(data);
  const take = solveByParam(data, "tau_pub_bps");
  const gap = mi?.gapMultiple ?? null;
  const ceiling = take && take.evidenceValue !== null ? take : null;
  return (
    <>
      {mi && mi.currentFdv !== null && mi.baseFdv !== null ? (
        <>
          The market values NEAR at <T>{fmtUsdCompact(mi.currentFdv)}</T>. Intents cash flow, discounted on the model&apos;s expected path, supports <T>{fmtUsdCompact(mi.baseFdv)}</T>
          {gap !== null && gap > 1 ? (
            <>
              : the price carries <T>{fmtTimes(gap)}</T> what Intents fees alone justify at base inputs.{" "}
            </>
          ) : (
            <>, {gap !== null && gap < 1 ? "above" : "in line with"} the market value. </>
          )}
        </>
      ) : null}
      {fees && fees.value !== null && rank ? (
        <>
          Priced as a layer 1, NEAR trades at <T>{fmtSolveValue("x", fees.value)}</T> annualised fees, {rank} (peer median <T>{fmtSolveValue("x", fees.peerMedian)}</T>).{" "}
        </>
      ) : null}
      {gap !== null && gap > 1 && bind ? (
        <>
          On Intents alone, closing the gap needs <T>{fmtSolveValue(bind.unit, bind.requiredValue)}</T> of {bind.shortLabel} against a measured <T>{fmtEvidenceValue(bind)}</T>
          {ceiling && ceiling.param !== bind.param && ceiling.requiredValue !== null ? (
            <>
              , or a <T>{fmtSolveValue("bps", ceiling.requiredValue)}</T> take against a <T>{fmtSolveValue("bps", ceiling.evidenceValue)}</T> competitive ceiling
            </>
          ) : null}
          .{" "}
        </>
      ) : null}
      Below: the measured strengths, the measured weaknesses, and the triggers that would falsify the case.
    </>
  );
}

function KeyFigures({ data }: { data: LandingData | null }) {
  if (!data) {
    return (
      <EmptyState title="No snapshot on disk yet" commands={["make reproduce", "make dev"]} className="self-center">
        This page only shows numbers that exist in <code className="font-mono text-[12.5px] text-ink">artifacts/latest_snapshot.json</code>. Run the pipeline once
        (about a minute, no API keys) and reload.
      </EmptyState>
    );
  }
  const { chain, stateLock, bench } = data;
  const mi = data.marketImplied;
  const fees = data.relativeValue?.feesRunRate ?? null;
  const bind = bindingSolve(data);
  const cross = bench?.headroom.cross_vm ?? null;
  const crossCorridor = bench?.corridors.find((c) => c.archetype === "cross_vm") ?? null;
  const crossVenue = crossCorridor?.bestCompetitor ? (VENUE_LABEL[crossCorridor.bestCompetitor] ?? crossCorridor.bestCompetitor) : null;
  const marketFdv = mi?.currentFdv ?? data.sotp.currentFdv;

  return (
    <aside aria-label="Key figures" className="self-center rounded-lg border border-border bg-surface">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-border px-6 py-4">
        <div className="text-[14px] text-ink">
          As of NEAR block{" "}
          <a href={explorerBlockUrl(chain.block)} target="_blank" rel="noreferrer" title={chain.blockHash} className="tnum text-accent underline-offset-4 hover:underline">
            {fmtBlock(chain.block)}
          </a>
        </div>
        <div className="tnum text-[13px] text-dim">{fmtUtc(chain.blockTsUtc)}</div>
      </div>
      <dl className="divide-y divide-border">
        <Figure
          label="Market FDV"
          value={fmtUsdCompact(marketFdv)}
          note={
            mi && mi.baseFdv !== null ? (
              <>
                <span className="tnum">{fmtTimes(mi.gapMultiple)}</span> the model&apos;s expected path of <span className="tnum">{fmtUsdCompact(mi.baseFdv)}</span>; Monte Carlo median{" "}
                <span className="tnum">{fmtUsdCompact(mi.baseFdvMcP50)}</span>
              </>
            ) : (
              "Market-implied solve not in this snapshot"
            )
          }
          source={<ProvenanceBadge source="nearstats" name="summary" label="Price" />}
        />
        <Figure
          label={bind ? `Required ${bind.shortLabel}` : "Market-implied requirement"}
          value={bind ? fmtSolveValue(bind.unit, bind.requiredValue) : "n/a"}
          note={
            bind ? (
              <>
                Against <span className="tnum">{fmtEvidenceValue(bind)}</span>, {bind.evidenceLabel ?? "the measured value"}
                {bind.ratio !== null ? <> (<span className="tnum">{fmtTimes(bind.ratio)}</span> the evidence)</> : null}
              </>
            ) : (
              "No reachable solve with measured evidence this run"
            )
          }
          source={
            <a href="/terminal#sotp" className="text-[12px] text-dim underline decoration-dotted underline-offset-[3px] hover:text-muted">
              Solve
            </a>
          }
        />
        <Figure
          label="FDV to annualised fees"
          value={fees ? fmtSolveValue("x", fees.value) : "n/a"}
          note={
            fees ? (
              <>
                {rankPhrase(fees) ? <>{rankPhrase(fees)?.replace(/^./, (c) => c.toUpperCase())}; </> : null}peer median <span className="tnum">{fmtSolveValue("x", fees.peerMedian)}</span>
              </>
            ) : (
              "Relative-value block not in this snapshot"
            )
          }
          source={<ProvenanceBadge source="defillama" name="fees:near-intents:dailyFees" />}
        />
        <Figure
          label="1Click headroom, cross-VM"
          value={<span className={TONE_TEXT[signTone(cross)]}>{bench ? minus(fmtBps(cross, { decimals: 2 })) : "Not run"}</span>}
          note={
            bench
              ? `${cross === null ? "No comparable cell" : cross >= 0 ? "More" : "Less"} output than the best competitor${crossVenue ? ` (${crossVenue})` : ""}`
              : "Snapshot built without the quote benchmark"
          }
          source={crossCorridor ? <ProvenanceBadge source="oneclick" name={`quote:${crossCorridor.id}:50000`} /> : null}
        />
        <Figure
          label="Storage locked by intents.near"
          value={stateLock.intentsLocked !== null ? fmtNear(stateLock.intentsLocked) : "Not measured"}
          note={
            stateLock.intentsGrowthNearPerDay !== null
              ? `${minus(fmtNear(stateLock.intentsGrowthNearPerDay, { signed: true, decimals: 1 }))} a day over ${fmtNum(stateLock.intentsGrowthWindowDays, { decimals: 1 })} days`
              : "Growth not measured (archival RPC unavailable)"
          }
          source={<ProvenanceBadge source="near_rpc" name="view_account:intents.near" />}
        />
      </dl>
      <div className="border-t border-border px-6 py-3 text-[13px] text-dim">
        Snapshot generated {fmtUtc(data.generatedAtUtc)} from {fmtInt(data.provenance.records)} hashed source payloads.
      </div>
    </aside>
  );
}

function Figure({ label, value, unit, note, source }: { label: string; value: ReactNode; unit?: string; note?: ReactNode; source?: ReactNode }) {
  return (
    <div className="grid grid-cols-1 items-baseline gap-x-6 gap-y-1 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:px-6">
      <dt className="text-[14px] text-muted">
        {label}
        {source ? <span className="ml-2.5 align-baseline">{source}</span> : null}
      </dt>
      <dd className="sm:row-span-2 sm:self-center sm:text-right">
        <span className="tnum text-[22px] font-medium leading-none tracking-tight text-ink">{value}</span>
        {unit ? <span className="ml-1.5 text-[13px] text-muted">{unit}</span> : null}
      </dd>
      <dd className="min-w-0 text-[13px] leading-snug text-dim">
        {note}
      </dd>
    </div>
  );
}
