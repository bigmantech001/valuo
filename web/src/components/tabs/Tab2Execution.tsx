import type { ReactNode } from "react";
import { ActorAudit, hhiBand } from "@/components/tab2/ActorAudit";
import { FeePoolShare } from "@/components/tab2/FeePoolShare";
import { LiquidityLadder } from "@/components/tab2/LiquidityLadder";
import { LiveRace } from "@/components/tab2/LiveRace";
import { MoatMatrix } from "@/components/tab2/MoatMatrix";
import type { SnapshotCellRef } from "@/components/tab2/RaceResult";
import { SpreadMatrix } from "@/components/tab2/SpreadMatrix";
import { TakeRateSeries } from "@/components/tab2/TakeRateSeries";
import { archetypePhrase, signTone } from "@/components/tab2/benchUtil";
import { Card, Stat } from "@/components/ui";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { ARCHETYPE_LABELS, CORRIDORS } from "@/lib/corridors";
import { fmtBps, fmtInt, fmtNum, fmtUtc } from "@/lib/format";
import type { CorridorArchetype, ExecutionBenchmark } from "@/lib/types";
import type { TabProps } from "./types";

function SubHead({ title, children }: { title: ReactNode; children?: ReactNode }) {
  return (
    <div className="max-w-3xl">
      <h3 className="font-serif text-[24px] font-medium leading-tight text-ink">{title}</h3>
      {children ? <p className="mt-2 text-[15px] leading-relaxed text-muted">{children}</p> : null}
    </div>
  );
}

function joinWords(xs: string[]): string {
  if (xs.length <= 1) return xs.join("");
  return `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;
}

/** The finding as one sentence, built from the archetype medians and true whichever way they point. */
function headline(bench: ExecutionBenchmark | null): string {
  if (!bench) return "This snapshot carries no execution benchmark";
  const entries = Object.entries(bench.headroom_by_archetype_bps) as Array<[CorridorArchetype, number | null]>;
  const lead = entries.filter(([, v]) => typeof v === "number" && v > 0) as Array<[CorridorArchetype, number]>;
  const trail = entries.filter(([, v]) => typeof v === "number" && v < 0) as Array<[CorridorArchetype, number]>;
  const tie = entries.filter(([, v]) => v === 0);
  if (!lead.length && !trail.length) return tie.length ? "1Click matches the best competitor on every scored route" : "No route in this benchmark produced a comparable 1Click quote";
  const leadPart =
    lead.length === 1
      ? `by ${fmtBps(lead[0][1], { decimals: 2 })} on ${archetypePhrase(lead[0][0])} routes`
      : `on ${joinWords(lead.map(([a, v]) => `${archetypePhrase(a)} (${fmtBps(v, { decimals: 2 })})`))} routes`;
  const trailNames = joinWords(trail.map(([a]) => archetypePhrase(a)));
  if (lead.length && trail.length) return `1Click out-delivers the best competitor ${leadPart} and trails on ${trailNames}`;
  if (lead.length) return `1Click out-delivers the best competitor ${leadPart}${tie.length ? "" : ", on every route type measured"}`;
  return `Competing routers out-deliver 1Click on ${trailNames} routes`;
}

/**
 * Tab 2: execution quality. The finding, key figures, the live quote race, the committed
 * route x size benchmark, and who settles on intents.near. Server component; only the race is client-side.
 */
export function Tab2Execution({ snapshot, manifest }: TabProps) {
  const bench = snapshot.execution_bench ?? null;
  const f = snapshot.intents_forensics;
  const quoteRecordCount = manifest ? manifest.records.filter((r) => r.name.startsWith("quote:")).length : null;
  const snapshotCells: SnapshotCellRef[] = bench
    ? bench.results.map((c) => ({
        corridor_id: c.corridor_id,
        clip_usd: c.clip_usd,
        headroom_bps: c.headroom_bps ?? null,
        headroom_basis: c.headroom_basis ?? null,
        best_competitor: c.best_competitor ?? null,
        oneclick_rank: c.oneclick_rank ?? null,
        n_venues_ok: c.n_venues_ok,
        ran_at_utc: bench.ran_at_utc,
      }))
    : [];
  const benchWarnings = snapshot.warnings.filter((w) => /execution_bench|benchmark|1click|oneclick|quote/i.test(w));
  const venueAttempts = bench ? bench.results.reduce((s, c) => s + c.quotes.length, 0) : 0;
  const cartelTrigger = snapshot.bear_case?.scenarios?.find((s) => s.key === "solver_cartelization") ?? null;
  const archetypes = bench ? ([...new Set(bench.corridors.map((c) => c.archetype))] as CorridorArchetype[]) : [];
  const sc = f.solver_concentration ?? null;
  const cs = f.caller_sample ?? null;

  return (
    <div className="space-y-16">
      {/* 1. Finding and key figures */}
      <section className="space-y-8">
        <SectionIntro eyebrow="Execution quality" title={headline(bench)}>
          {bench ? (
            <>
              Each venue receives an identical dry quote for the same input; deliveries are compared in destination units, so no price oracle enters the result. {fmtInt(bench.results.length)} cells ({fmtInt(bench.corridors.length)} routes at {fmtInt(bench.clips_usd.length)} trade sizes), run {fmtUtc(bench.ran_at_utc)}.
            </>
          ) : (
            "The quote matrix failed within its time budget when this snapshot was built. The live race below still quotes all four venues, and the settlement audit reads the NearBlocks sample."
          )}
        </SectionIntro>

        {bench ? (
          <StatGrid cols={3}>
            {archetypes.map((a) => {
              const median = bench.headroom_by_archetype_bps[a] ?? null;
              const n = bench.headroom_n_by_archetype?.[a] ?? 0;
              const cells = bench.results.filter((r) => bench.corridors.find((c) => c.corridor_id === r.corridor_id)?.archetype === a).length;
              return (
                <Stat
                  key={a}
                  label={`${ARCHETYPE_LABELS[a]} headroom, median`}
                  value={median}
                  format={(v) => fmtBps(v, { decimals: 2 })}
                  tone={signTone(median)}
                  hint={median === null ? "No scored cell" : `${fmtInt(n)} of ${fmtInt(cells)} sizes scored`}
                />
              );
            })}
            <Stat
              label="Competitive fee ceiling"
              value={bench.competitive_fee_ceiling_bps ?? null}
              format={(v) => fmtBps(v, { signed: false, decimals: 2 })}
              hint={`Best competitor's all-in cost on cross-VM, median of ${fmtInt(bench.competitive_fee_ceiling_n ?? null)}`}
            />
            <Stat
              label="Quotes returned"
              value={bench.n_quotes_ok ?? null}
              format={(v) => `${fmtInt(v)} of ${fmtInt(venueAttempts)}`}
              hint={typeof bench.elapsed_s === "number" ? `All venues in ${fmtNum(bench.elapsed_s, { decimals: 1 })} s` : undefined}
            />
            <Stat
              label="1Click settlement universe"
              value={bench.oneclick_1y_token_universe ?? null}
              format={(v) => fmtInt(v)}
              unit="assets"
              hint={`On ${fmtInt(bench.oneclick_blockchains.length)} chains`}
              provenance={{ source: "oneclick", name: "tokens" }}
            />
          </StatGrid>
        ) : (
          <Card title="Benchmark missing from this snapshot">
            <p className="text-[14px] leading-relaxed text-muted">
              The pipeline stores no benchmark when the live quote matrix fails within its budget, and records why in the snapshot warnings. Re-run <code className="font-mono text-[13px] text-ink">make reproduce</code> with network access to the four venue APIs.
            </p>
            {benchWarnings.length ? (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-[13px] text-amber">
                {benchWarnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-[13px] text-dim">The snapshot warnings carry no benchmark-related entry.</p>
            )}
          </Card>
        )}
      </section>

      {/* 2. Live race */}
      <section className="space-y-6">
        <SubHead title="Live quote race">
          Re-run any cell of the benchmark now, against the same four endpoints, and read it next to the committed result.
        </SubHead>
        <LiveRace snapshotCells={snapshotCells} />
      </section>

      {/* 3. Committed benchmark */}
      {bench ? (
        <section className="space-y-6">
          <SubHead title="Committed benchmark">
            The reproducible run stored in the snapshot. Green cells are sizes where 1Click delivers more than every competitor; red cells are sizes where a competitor delivers more.
          </SubHead>
          <MoatMatrix bench={bench} />
          <SpreadMatrix bench={bench} quoteRecordCount={quoteRecordCount} />
          <LiquidityLadder data={snapshot.liquidity_ladder} />
          <MethodNote>
            <p>
              <span className="text-ink">Headroom.</span> {bench.headroom_definition ?? "(out_1click - out_best_competitor) / out_best_competitor x 1e4 on destination units for the same raw input"}. Basis{" "}
              <code>{bench.headroom_basis ?? "per cell"}</code>: destination units, the same raw input sent to every venue, no oracle. Positive means 1Click delivers more.
            </p>
            <p>
              <span className="text-ink">Scored cell.</span> 1Click and at least one competitor returned an ok quote. Archetype medians are over scored cells only (<code>execution_bench.headroom_by_archetype_bps</code>, counts in <code>headroom_n_by_archetype</code>). A route with one scored cell is a single observation.
            </p>
            <p>
              <span className="text-ink">All-in cost.</span> (input - output) / input in bps: on raw units when both legs are the same stablecoin, else on USD legs valued at <code>{bench.usd_friction_basis ?? "n/a"}</code>. The competitive fee ceiling is {bench.competitive_fee_ceiling_basis ?? "not recorded"} (<code>execution_bench.competitive_fee_ceiling_bps</code>).
            </p>
            <p>
              <span className="text-ink">Run.</span> {fmtUtc(bench.ran_at_utc, { seconds: true })}; {fmtInt(bench.n_quotes_ok ?? null)} of {fmtInt(venueAttempts)} quotes ok; wall clock {fmtNum(bench.elapsed_s ?? null, { decimals: 1 })} s against a {bench.budget_s ?? "n/a"} s budget, {bench.request_timeout_s ?? "n/a"} s per-request timeout, concurrency {bench.concurrency ?? "n/a"}. {fmtInt(quoteRecordCount)} quote records in the manifest (<code>quote:&lt;corridor&gt;:&lt;clip&gt;</code>). Token list ok: <code>{String(bench.token_list_ok ?? "n/a")}</code>.
            </p>
            <p>
              <span className="text-ink">Collector summary, verbatim.</span> <code className="whitespace-normal">{bench.summary_note}</code>
            </p>
            <p>
              <span className="text-ink">1Click chains.</span> <code className="whitespace-normal">{bench.oneclick_blockchains.join(", ")}</code>
            </p>
            <p>
              <span className="text-ink">Reproduce.</span> <code>make reproduce</code> or <code>cd quant &amp;&amp; uv run python -m valuo.reproduce</code>. Snapshot fields: <code>execution_bench.results[]</code>, <code>.corridors[]</code>, <code>.competitor_friction_by_venue_bps</code>.
            </p>
            <p>
              <span className="text-ink">Live race.</span> <code>POST /api/live-benchmark</code> with <code>{"{corridor_id, clip_usd}"}</code>; routes from <code>src/lib/corridors.ts</code> ({CORRIDORS.map((c) => c.corridor_id).join(", ")}); request payloads per <code>docs/LIVE_ENDPOINT_FACTS.md</code> sections 2 and 3. Venues declared unsupported are re-verified live against the Across chain list.
            </p>
          </MethodNote>
        </section>
      ) : null}

      <FeePoolShare data={snapshot.fee_pool_share} />

      <TakeRateSeries data={snapshot.take_rate_series} />

      {/* 4. Settlement audit */}
      <section className="space-y-6">
        <SubHead title="Who settles on intents.near">
          Two populations, measured separately. Deposit sources and direct callers are context;{" "}
          {sc
            ? `solver concentration, ${fmtInt(sc.hhi_solver)} HHI across ${fmtNum(sc.n_eff_solver, { decimals: 1 })} effective solvers (${(hhiBand(sc.hhi_solver) ?? "n/a").replace(/ \(.*\)$/, "").toLowerCase()}), is what the cartelization trigger reads.`
            : "solver concentration, which the cartelization trigger reads, is not in this snapshot."}
        </SubHead>
        <ActorAudit f={f} cartelTrigger={cartelTrigger} />
        <MethodNote>
          <p>
            <span className="text-ink">HHI.</span> Sum of squared percentage shares (0 to 10,000); effective participants = 10,000 / HHI. Bands follow the US DOJ/FTC merger guidelines: below 1,500 unconcentrated, 1,500 to 2,500 moderate, above 2,500 highly concentrated.
          </p>
          <p>
            <span className="text-ink">Caller index</span> (<code>intents_forensics.hhi_external</code>): {cs?.hhi_external_meaning ?? "deposit-source / caller concentration over external predecessors; not solver concentration"}. System and intents.near self-receipts are excluded. <code>hhi_all</code> includes them.
          </p>
          {cs?.classification_note ? (
            <p>
              <span className="text-ink">Classification.</span> {cs.classification_note}
            </p>
          ) : null}
          {sc ? (
            <p>
              <span className="text-ink">Solver index</span> (<code>intents_forensics.solver_concentration.hhi_solver</code>): {sc.method}.
            </p>
          ) : null}
          {cartelTrigger ? (
            <p>
              <span className="text-ink">Cartelization trigger</span> (<code>bear_case.scenarios[solver_cartelization]</code>): reads <code>{cartelTrigger.early_warning_metric}</code>, fires at {cartelTrigger.trigger_comparator ?? ">"} {fmtInt(cartelTrigger.trigger_threshold)}.
              {cartelTrigger.trigger_note ? ` ${cartelTrigger.trigger_note}.` : ""}
            </p>
          ) : null}
          <p>
            <span className="text-ink">Sample.</span> {fmtInt(f.receipts_sampled)} receipts over {fmtInt(f.pages_fetched)} NearBlocks pages (<code>api.nearblocks.io/v1/account/intents.near/txns</code>), block range <code>intents_forensics.sample_block_range</code>
            {f.fetched_at_utc ? `, fetched ${fmtUtc(f.fetched_at_utc, { seconds: true })}` : ""}. escrow.ai.near is a plain account with no contract: a caller, not a state sink.
          </p>
        </MethodNote>
      </section>
    </div>
  );
}
