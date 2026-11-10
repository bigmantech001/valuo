import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Badge, Card, Stat } from "@/components/ui";
import { StatGrid } from "@/components/ui/Section";
import { fmtBlock, fmtCompact, fmtInt, fmtNum, fmtPct, fmtSeconds, fmtUtc } from "@/lib/format";
import { explorerAccountUrl, explorerBlockUrl } from "@/lib/manifestIndex";
import { COLORS } from "@/lib/theme";
import type { BearScenario, IntentsForensics } from "@/lib/types";
import { CallerBreakdown, LINK, MethodMix, ShareBars, type ShareRow } from "./CallerBreakdown";

export interface ActorAuditProps {
  f: IntentsForensics;
  /** bear_case.scenarios[solver_cartelization], so the audit can state which HHI the trigger reads and its status */
  cartelTrigger?: BearScenario | null;
}

/**
 * "Breached" / "Not breached" only when the model graded the trigger; "Inconclusive" when it was
 * measured on a sample too short to grade; otherwise "Not measured". Prefers the graded
 * `trigger_status`; older snapshots fall back to the flags.
 */
export function triggerText(s: BearScenario): "Breached" | "Not breached" | "Inconclusive" | "Not measured" {
  if (s.trigger_status === "breached") return "Breached";
  if (s.trigger_status === "not_breached") return "Not breached";
  if (s.trigger_status === "inconclusive") return "Inconclusive";
  if (s.trigger_status === "not_measured") return "Not measured";
  if (s.trigger_evaluated === false || s.trigger_breached === null || s.trigger_breached === undefined || typeof s.current_value !== "number") return "Not measured";
  return s.trigger_breached ? "Breached" : "Not breached";
}

/** "90% CI 3,863 to 5,764" from a bootstrap interval, or null. */
function ciText(ci: [number, number] | null | undefined): string | null {
  return ci && Number.isFinite(ci[0]) && Number.isFinite(ci[1]) ? `90% CI ${fmtInt(ci[0])} to ${fmtInt(ci[1])}` : null;
}

function joinHint(...parts: Array<string | null | undefined>): string | undefined {
  const p = parts.filter((x): x is string => Boolean(x));
  return p.length ? p.join("; ") : undefined;
}

/** US DOJ / FTC horizontal-merger bands, the same ones the gauges elsewhere use. */
export function hhiBand(v: number | null | undefined): string | null {
  if (typeof v !== "number" || !Number.isFinite(v)) return null;
  if (v < 1500) return "Unconcentrated (below 1,500)";
  if (v <= 2500) return "Moderately concentrated (1,500 to 2,500)";
  return "Highly concentrated (above 2,500)";
}

/**
 * Who settles on intents.near, as two separate populations read from the NearBlocks receipt sample:
 * deposit sources and direct callers (context only), and the solvers that fill signed intents (the
 * population the bear-case cartelization trigger reads). Sample size and caveats follow.
 */
export function ActorAudit({ f, cartelTrigger = null }: ActorAuditProps) {
  const cs = f.caller_sample ?? null;
  const sc = f.solver_concentration ?? null;
  const cartelReadsSolver = cartelTrigger?.early_warning_metric === "hhi_solver";
  const base = f.explorer_base || "https://nearblocks.io";
  const pages = Array.from({ length: Math.max(0, Math.floor(f.pages_fetched)) }, (_, i) => `txns:intents.near:p${i + 1}`);
  const oneIn = f.lifetime_receipts && f.receipts_sampled > 0 ? Math.round(f.lifetime_receipts / f.receipts_sampled) : null;
  const agents = f.callers.filter((c) => c.cls === "ai_agent");
  const [blockLo, blockHi] = [f.sample_block_range[0] ?? null, f.sample_block_range[1] ?? null];
  const thin = cartelTrigger ? (cartelTrigger as { sample_thin?: unknown }).sample_thin === true : false;
  const trig = cartelTrigger && cartelReadsSolver ? triggerText(cartelTrigger) : null;
  const span = cartelTrigger && typeof cartelTrigger.sample_span_s === "number" ? cartelTrigger.sample_span_s : null;
  const minSpan = cartelTrigger && typeof cartelTrigger.min_sample_span_s === "number" ? cartelTrigger.min_sample_span_s : null;
  const inconclusiveWhy = trig === "Inconclusive" ? (span !== null && minSpan !== null ? `the solver sample spans ${fmtSeconds(span)} of chain time against the ${fmtSeconds(minSpan)} minimum` : "the sample is too short to grade") : null;
  const solverRows: ShareRow[] = sc
    ? [...sc.solvers]
        .sort((a, b) => b.share - a.share || b.fills - a.fills)
        .map((s) => ({ account_id: s.account_id, share: s.share, count: s.fills, sublabel: `${fmtInt(s.payloads_signed)} payloads signed`, color: COLORS.muted, example_tx_hash: s.example_tx_hash }))
    : [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-2">
        <Card
          kicker="Context only; not a solver measure"
          title="Who deposits into and calls the contract"
          subtitle={`External predecessors of intents.near receipts: bridge token contracts, wallets and agents. ${fmtInt(cs?.external_receipts_sampled ?? null)} external receipts from ${fmtInt(cs?.unique_external_callers ?? null)} callers.`}
        >
          <StatGrid cols={2}>
            <Stat label="Caller concentration (HHI)" value={f.hhi_external} format={(v) => fmtInt(v)} hint={joinHint(ciText(cs?.hhi_external_ci90), hhiBand(f.hhi_external))} />
            <Stat label="Effective callers" value={f.n_eff_external} format={(v) => fmtNum(v, { decimals: 2 })} hint="10,000 divided by HHI" />
            <Stat
              label="AI agent share"
              value={f.ai_agent_share}
              format={(v) => fmtPct(v, { decimals: 1 })}
              hint={
                agents.length ? (
                  <>
                    {agents.map((a, i) => (
                      <span key={a.account_id}>
                        {i > 0 ? ", " : ""}
                        <a href={explorerAccountUrl(a.account_id, base)} target="_blank" rel="noreferrer" className={LINK}>
                          {a.account_id}
                        </a>
                      </span>
                    ))}
                    , classified by name only
                  </>
                ) : (
                  "No agent-named caller in the sample"
                )
              }
            />
            <Stat label="Bridge and token-contract share" value={f.bridge_share} format={(v) => fmtPct(v, { decimals: 1 })} hint={`HHI excluding agents: ${fmtInt(cs?.hhi_external_ex_ai_agent ?? null)}`} />
          </StatGrid>
          <div className="mt-5">
            <CallerBreakdown f={f} />
          </div>
        </Card>

        <Card
          kicker={cartelReadsSolver ? "Read by the solver-cartelization trigger" : "Solver side"}
          title="Which solvers fill signed intents"
          subtitle={sc ? `Fills decoded from execute_intents receipts: ${fmtInt(sc.n_fills)} fills, ${fmtInt(sc.n_fills_attributed)} solver participations attributed across ${fmtInt(sc.unique_solvers)} accounts.` : "The snapshot carries no solver attribution for this sample."}
          actions={
            trig || thin ? (
              <>
                {trig && cartelTrigger ? (
                  <Badge
                    variant={trig === "Breached" ? "error" : trig === "Not breached" ? "ok" : trig === "Inconclusive" ? "assumption" : "neutral"}
                    dot
                    title={`Trigger fires when solver HHI ${cartelTrigger.trigger_comparator ?? ">"} ${fmtInt(cartelTrigger.trigger_threshold)}${inconclusiveWhy ? `; not graded because ${inconclusiveWhy}` : ""}`}
                  >
                    Trigger {trig.toLowerCase()}
                  </Badge>
                ) : null}
                {thin ? (
                  <Badge variant="warn" dot title="Below the disclosed minimum fill count; the index moves by hundreds of points between runs at this size">
                    Thin sample{sc ? `: ${fmtInt(sc.n_fills)} fills` : ""}
                  </Badge>
                ) : null}
              </>
            ) : null
          }
          footer={
            cartelTrigger && cartelReadsSolver ? (
              <>
                The trigger fires above a solver HHI of {fmtInt(cartelTrigger.trigger_threshold)}; the caller index on the left cannot fire it.
                {inconclusiveWhy ? ` This run it is inconclusive, neither breached nor clear: ${inconclusiveWhy}.` : ""}
              </>
            ) : undefined
          }
        >
          {sc ? (
            <>
              <StatGrid cols={2}>
                <Stat label="Solver concentration (HHI)" value={sc.hhi_solver} format={(v) => fmtInt(v)} hint={joinHint(ciText(sc.hhi_solver_ci90), hhiBand(sc.hhi_solver))} />
                <Stat label="Effective solvers" value={sc.n_eff_solver} format={(v) => fmtNum(v, { decimals: 2 })} hint="10,000 divided by HHI" />
                <Stat label="Fills sampled" value={sc.n_fills} format={(v) => fmtInt(v)} hint={`${fmtInt(sc.n_fills_unresolved)} participations unresolved`} />
                <Stat
                  label="Receipts calling execute_intents"
                  value={sc.n_execute_intents_receipts}
                  format={(v) => fmtInt(v)}
                  hint={`${fmtInt(sc.n_signed_payloads)} signed payloads, ${fmtInt(sc.n_payloads_undecodable)} undecodable`}
                />
              </StatGrid>
              <div className="mt-5">
                <ShareBars rows={solverRows} countLabel="Fills" base={base} empty="No solver attributed in the sample." />
              </div>
            </>
          ) : (
            <p className="text-[13.5px] text-muted">Solver concentration is not available in this snapshot; the cartelization trigger is therefore not measured.</p>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-6 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          title="Sample size and coverage"
          subtitle="Both indices are a point-in-time receipt sample, not volume-weighted or lifetime measures. Read the counts before the index."
          footer={
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>Sources:</span>
              <ProvenanceBadge source="nearblocks" name="txns_count:intents.near" label="Receipt count" />
              {pages.map((p, i) => (
                <ProvenanceBadge key={p} source="nearblocks" name={p} label={`Page ${i + 1}`} />
              ))}
            </div>
          }
        >
          <StatGrid cols={3}>
            <Stat label="Receipts sampled" value={f.receipts_sampled} format={(v) => fmtInt(v)} hint={`${fmtInt(f.pages_fetched)} pages of ${fmtInt(cs?.per_page ?? null)} receipts`} />
            <Stat label="External receipts" value={cs?.external_receipts_sampled ?? null} format={(v) => fmtInt(v)} hint="Excluding system and self-receipts" />
            <Stat label="Lifetime receipts" value={f.lifetime_receipts ?? null} format={(v) => fmtCompact(v)} hint={f.lifetime_receipts != null ? `Sample covers 1 in ${fmtInt(oneIn)}` : "NearBlocks count failed"} />
            <Stat
              label="Block range"
              value={
                blockLo !== null && blockHi !== null ? (
                  <span className="text-[17px]">
                    <a href={explorerBlockUrl(blockLo, base)} target="_blank" rel="noreferrer" className={LINK}>
                      {fmtBlock(blockLo)}
                    </a>
                    <span className="text-muted"> to </span>
                    <a href={explorerBlockUrl(blockHi, base)} target="_blank" rel="noreferrer" className={LINK}>
                      {fmtBlock(blockHi)}
                    </a>
                  </span>
                ) : null
              }
              hint={blockLo !== null && blockHi !== null ? `${fmtInt(blockHi - blockLo)} blocks` : undefined}
            />
            <Stat
              label="Chain time covered"
              value={cs?.sample_span_s ?? null}
              format={(v) => fmtSeconds(v)}
              hint={cs?.sample_time_range_utc?.length === 2 ? `Ending ${fmtUtc(cs.sample_time_range_utc[1], { seconds: true })}` : undefined}
            />
            <Stat label="HHI, all predecessors" value={f.hhi_all} format={(v) => fmtInt(v)} hint="Including system and self-receipts" />
          </StatGrid>
          <ul className="mt-4 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-muted">
            <li>
              The caller index rests on {fmtInt(cs?.external_receipts_sampled ?? null)} external receipts from {fmtInt(cs?.unique_external_callers ?? null)} callers over {fmtSeconds(cs?.sample_span_s ?? null)} of chain time. One burst from one caller moves it materially: read it as a snapshot of traffic, not a market share.
            </li>
            {f.warnings.map((w) => (
              <li key={w} className="text-amber">
                {w}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Receipt methods" subtitle={`All ${fmtInt(f.receipts_sampled)} sampled receipts, including system and self-receipts.`}>
          <MethodMix f={f} />
        </Card>
      </div>
    </div>
  );
}
