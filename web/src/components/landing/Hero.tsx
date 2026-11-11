import type { ReactNode } from "react";
import Link from "next/link";
import { fmtBlock, fmtInt, fmtNear, fmtNum, fmtUsdCompact, fmtUtc } from "@/lib/format";
import { explorerBlockUrl } from "@/lib/manifestIndex";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { bindingSolve, fmtEvidenceValue, fmtSolveValue, fmtTimes, minus, rankPhrase, type LandingData } from "./landingData";
import { Figure } from "./HeroFigure";
import { GapBars, Sparkline, StatusDots } from "./HeroVisuals";
import { LiveBlock, LiveRaceFigure } from "./HeroLive";

/**
 * Above the fold: the question the page answers (what the market price requires), a lede built
 * from market_implied and relative_value, two calls to action and a key-figures panel pinned to
 * the snapshot's mainnet block. Every figure is read from the snapshot.
 */
export function Hero({ data, headroomHistory = [] }: { data: LandingData | null; headroomHistory?: number[] }) {
  const mi = data?.marketImplied ?? null;
  return (
    <section className="border-b border-border">
      <div className="mx-auto grid max-w-none gap-14 px-6 lg:px-[5vw] pb-20 pt-16 sm:pt-20 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-16 lg:pb-24 lg:pt-24">
        <div className="flex min-w-0 flex-col justify-center">
          <p className="text-[14px] text-muted">NEAR Hackathon 2026 &middot; Investment thesis track</p>
          <h1 className="mt-5 max-w-[18ch] font-serif text-[42px] font-medium leading-[1.06] tracking-tight text-ink sm:text-[54px] lg:text-[58px]">
            The long-term case for NEAR, made falsifiable.
          </h1>
          <p className="mt-7 max-w-[38rem] text-[17px] leading-[1.65] text-muted">{data ? <Lede data={data} /> : <>Valuo measures NEAR&apos;s execution, supply and fee data from public endpoints and solves for what the market price assumes. Generate a snapshot to see the figures.</>}</p>
          {mi && mi.currentFdv !== null && mi.baseFdv !== null ? <GapBars market={mi.currentFdv} supported={mi.baseFdv} mcMedian={mi.baseFdvMcP50 ?? null} /> : null}
          {data?.bullCase ? <StatusDots conditions={data.bullCase.conditions} counts={data.bullCase} /> : null}
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

        <KeyFigures data={data} headroomHistory={headroomHistory} />
      </div>
    </section>
  );
}

const T = ({ children }: { children: ReactNode }) => <span className="tnum text-ink">{children}</span>;

/**
 * Two sentences from market_implied: the gap, then what closing it on Intents alone requires against the
 * measured value. Each clause is conditional on the sign it describes, so the text stays true when the numbers
 * move. The gap bars and status dots below carry the rest.
 */
function Lede({ data }: { data: LandingData }) {
  const mi = data.marketImplied;
  const bind = bindingSolve(data);
  const gap = mi?.gapMultiple ?? null;
  return (
    <>
      {mi && mi.currentFdv !== null && mi.baseFdv !== null ? (
        <>
          The market values NEAR at <T>{fmtUsdCompact(mi.currentFdv)}</T>; Intents cash flow on the model&apos;s expected path supports <T>{fmtUsdCompact(mi.baseFdv)}</T>
          {gap !== null && gap > 1 ? (
            <>
              , a <T>{fmtTimes(gap)}</T> gap.{" "}
            </>
          ) : (
            <>, {gap !== null && gap < 1 ? "above" : "in line with"} the market value. </>
          )}
        </>
      ) : null}
      {gap !== null && gap > 1 && bind ? (
        <>
          Closing it on Intents alone needs <T>{fmtSolveValue(bind.unit, bind.requiredValue)}</T> of {bind.shortLabel} against a measured <T>{fmtEvidenceValue(bind)}</T>; below
          are the measured strengths, the weaknesses and the triggers that would falsify the case.
        </>
      ) : (
        <>Below: the measured strengths, the measured weaknesses, and the triggers that would falsify the case.</>
      )}
    </>
  );
}

function KeyFigures({ data, headroomHistory }: { data: LandingData | null; headroomHistory: number[] }) {
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
  const t30 = data.trailing30d;
  const span = t30 && t30.volume.length ? `${t30.volume[0][0]} to ${t30.volume[t30.volume.length - 1][0]}` : "";
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
        <LiveBlock snapshotBlock={chain.block} />
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
          spark={
            t30 && bind?.param === "public_volume_growth_yoy" ? (
              <Sparkline
                points={t30.volume.map((p) => p[1])}
                caption={`Intents volume, rolling 30 days: ${fmtUsdCompact(t30.volume[0][1])} to ${fmtUsdCompact(t30.volume[t30.volume.length - 1][1])} (${span}, DefiLlama)`}
              />
            ) : null
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
          spark={
            t30 ? (
              <Sparkline
                points={t30.fees.map((p) => p[1])}
                caption={`Intents fees, rolling 30 days: ${fmtUsdCompact(t30.fees[0][1])} to ${fmtUsdCompact(t30.fees[t30.fees.length - 1][1])} (${span})`}
              />
            ) : null
          }
        />
        {bench ? (
          <LiveRaceFigure
            corridorId={crossCorridor?.id ?? null}
            snapshotBps={cross}
            snapshotVenue={crossCorridor?.bestCompetitor ?? null}
            history={headroomHistory}
            source={crossCorridor ? <ProvenanceBadge source="oneclick" name={`quote:${crossCorridor.id}:50000`} /> : null}
          />
        ) : (
          <Figure label="1Click headroom, cross-VM" value="Not run" note="Snapshot built without the quote benchmark" />
        )}
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
