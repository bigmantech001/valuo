import type { ReactNode } from "react";
import { MethodNote } from "@/components/ui/Section";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/cn";
import { fmtBps, fmtInt, fmtMultiple, fmtNear, fmtNum, fmtPct, fmtPctPoints, fmtUsdCompact, fmtUtc, NA } from "@/lib/format";
import type { CorridorArchetype, Snapshot } from "@/lib/types";
import { ARCHETYPE_LABEL, ARCHETYPE_ORDER, archetypeQuoteRef, corridorText, epochBlockRef, isNum, joinAnd, percentiles, quotesAttempted, toneBySign } from "./derive";
import { FigureList, Panel, SubHead, type FigureItem } from "./parts";

const THIN_SAMPLE_FILLS = 30;

function times(v: number | null | undefined, decimals = 1): string {
  return isNum(v) ? fmtMultiple(v, { decimals }).replace(/x$/, "×") : NA;
}

function Step({ n, title, claim, items, empty }: { n: number; title: string; claim: ReactNode; items: FigureItem[]; empty?: ReactNode }) {
  return (
    <li className="grid grid-cols-[minmax(0,1fr)] gap-x-10 gap-y-4 border-t border-border py-7 first:border-t-0 first:pt-2 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div className="flex gap-4">
        <span aria-hidden className="tnum mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border-strong text-[13px] text-muted">
          {n}
        </span>
        <div className="min-w-0">
          <h4 className="font-serif text-[20px] font-medium leading-snug text-ink">
            <span className="sr-only">Step {n}: </span>
            {title}
          </h4>
          <p className="mt-2 text-[15px] leading-relaxed text-muted">{claim}</p>
        </div>
      </div>
      <Panel className="px-5 py-1">{items.length ? <FigureList items={items} /> : <p className="py-3 text-[14px] text-muted">{empty ?? "Not available in this snapshot."}</p>}</Panel>
    </li>
  );
}

/**
 * The causal chain behind the thesis, read top to bottom: execution headroom sets how far
 * competitors can compress the take rate; take rate and capture set the buyback sink; sinks against
 * issuance set the supply path; the three valuation engines price the result. Negative cells (an
 * archetype where 1Click trails) are shown as measured.
 */
export function CausalChain({ snapshot, className }: { snapshot: Snapshot; className?: string }) {
  const bench = snapshot.execution_bench ?? null;
  const fees = snapshot.intents_forensics?.fees;
  const forensics = snapshot.intents_forensics;
  const solver = forensics?.solver_concentration ?? null;
  const supply = snapshot.supply_physics;
  const sotp = snapshot.sotp;
  const cal = sotp?.calibration;
  const fdv = percentiles(sotp?.fdv_percentiles);
  const upside = isNum(sotp?.upside_p50_pct) ? sotp.upside_p50_pct : null;

  // ------------------------------------------------------------------ 1. execution headroom
  const archetypes = ARCHETYPE_ORDER.filter((a) => bench && a in (bench.headroom_by_archetype_bps ?? {}));
  const headroom = (a: CorridorArchetype) => bench?.headroom_by_archetype_bps?.[a] ?? null;
  const leads = archetypes.filter((a) => isNum(headroom(a)) && (headroom(a) as number) > 0).map((a) => ARCHETYPE_LABEL[a]);
  const trails = archetypes.filter((a) => isNum(headroom(a)) && (headroom(a) as number) < 0).map((a) => ARCHETYPE_LABEL[a]);
  const attempted = quotesAttempted(bench);
  const ceiling = bench?.competitive_fee_ceiling_bps ?? null;

  let claim1: string;
  if (!bench) claim1 = "The execution benchmark did not run for this snapshot (it failed or was skipped), so headroom is not measured. See the caveats below.";
  else {
    const parts: string[] = [];
    if (leads.length) parts.push(`1Click delivers more than the best competitor on ${joinAnd(leads)} routes`);
    if (trails.length) parts.push(`${leads.length ? "less" : "1Click delivers less than the best competitor"} on ${joinAnd(trails)}`);
    claim1 = parts.length ? `${parts.join(" and ")}.` : "No archetype had a comparable cell in this run.";
    if (isNum(ceiling)) claim1 += ` The best competitor's median friction on cross-VM routes is ${fmtBps(ceiling, { signed: false, decimals: 2 })}, which bounds how far rivals can undercut the take rate.`;
  }
  const items1: FigureItem[] = bench
    ? [
        ...archetypes.map<FigureItem>((a) => {
          const v = headroom(a);
          const n = bench.headroom_n_by_archetype?.[a] ?? null;
          const corridor = bench.corridors?.find((c) => c.archetype === a);
          return {
            key: a,
            label: `Headroom, ${ARCHETYPE_LABEL[a]}`,
            sub: `${corridorText(corridor?.label)}${isNum(n) ? `, ${fmtInt(n)} ${n === 1 ? "cell" : "cells"}` : ""}`,
            value: isNum(v) ? fmtBps(v, { decimals: 2 }) : "No comparable cell",
            tone: toneBySign(v),
            prov: archetypeQuoteRef(bench, a),
          };
        }),
        { key: "ceiling", label: "Competitive fee ceiling", sub: isNum(bench.competitive_fee_ceiling_n) ? `Median over ${fmtInt(bench.competitive_fee_ceiling_n)} cross-VM cells` : null, value: fmtBps(ceiling, { signed: false, decimals: 2 }) },
        { key: "quotes", label: "Quotes returned", sub: trails.length ? "Trailing cells are shown as measured" : null, value: `${fmtInt(bench.n_quotes_ok)} of ${isNum(attempted) ? fmtInt(attempted) : NA}` },
      ]
    : [];

  // ------------------------------------------------------------------ 2. take rate and stickiness
  const thin = solver ? solver.n_fills < THIN_SAMPLE_FILLS : false;
  const confShare = forensics?.volume?.confidential_share_30d ?? null;
  const confStatus = forensics?.volume?.confidential_share_status ?? cal?.confidential_share_status ?? null;
  // Older snapshots carry no status: treat the share as measured only when the status says so or is absent.
  const confMeasured = confStatus === null || confStatus === "measured";
  const confWhy = confStatus === "implausible_fallback" ? "nearstats split implausible" : "nearstats split unavailable";
  const solverCi = solver?.hhi_solver_ci90 ?? null;
  const depositCi = forensics?.caller_sample?.hhi_external_ci90 ?? null;
  const ciText = (ci: [number, number] | null | undefined) => (ci && isNum(ci[0]) && isNum(ci[1]) ? `90% CI ${fmtInt(ci[0])} to ${fmtInt(ci[1])}` : null);
  const windowDays = isNum(fees?.take_rate_window_days) ? fees.take_rate_window_days : 30;
  const claim2 =
    isNum(fees?.gross_take_bps) && isNum(fees?.net_take_bps)
      ? `NEAR Intents keeps ${fmtBps(fees.gross_take_bps, { signed: false, decimals: 2 })} of volume before revenue sharing and ${fmtBps(fees.net_take_bps, { signed: false, decimals: 2 })} after, on ${fmtUsdCompact(fees?.volume_30d_usd ?? null)} of ${fmtInt(windowDays)}-day volume.${isNum(confShare) ? (confMeasured ? ` ${fmtPct(confShare, { decimals: 1 })} of that volume settles confidentially.` : ` The confidential share is not measured this run (${confWhy}); the model assumes ${fmtPct(confShare, { decimals: 0 })}.`) : ""}${solver && isNum(solver.n_eff_solver) ? ` Fills spread across the equivalent of ${fmtNum(solver.n_eff_solver, { decimals: 1 })} equal-sized solvers${thin ? ", on a thin sample" : ""}.` : ""}`
      : "Take-rate fields are missing from this snapshot.";
  const items2: FigureItem[] = [
    { key: "gross", label: "Gross take", sub: `Fees over volume, ${fmtInt(windowDays)} days`, value: fmtBps(fees?.gross_take_bps ?? null, { signed: false, decimals: 2 }), prov: { source: "defillama", name: "fees:near-intents" } },
    { key: "net", label: "Net take, captured by NEAR", sub: isNum(fees?.capture_ratio) ? `${fmtPct(fees.capture_ratio, { decimals: 1 })} of gross fees` : null, value: fmtBps(fees?.net_take_bps ?? null, { signed: false, decimals: 2 }), prov: { source: "defillama", name: "fees:near-intents:dailyRevenue" } },
  ];
  if (solver) {
    items2.push({
      key: "solver",
      label: "Solver concentration (HHI)",
      sub: `${ciText(solverCi) ? `${ciText(solverCi)}; ` : ""}${fmtInt(solver.unique_solvers)} solvers in ${fmtInt(solver.n_fills)} sampled fills; ${fmtNum(solver.n_eff_solver, { decimals: 2 })} effective`,
      value: isNum(solver.hhi_solver) ? fmtInt(solver.hhi_solver) : "No fill attributed",
      badge: thin ? (
        <Badge variant="warn" title={`Fewer than ${THIN_SAMPLE_FILLS} fills sampled: a point estimate within sampling noise, not a market-share measure`}>
          Thin sample
        </Badge>
      ) : null,
      prov: { source: "nearblocks", name: "txns:intents.near:p1" },
    });
  }
  items2.push({
    key: "deposit",
    label: "Deposit-source concentration (HHI)",
    sub: `${ciText(depositCi) ? `${ciText(depositCi)}; bridges` : "Bridges"} and direct callers, not solvers; ${fmtNum(forensics?.n_eff_external ?? null, { decimals: 2 })} effective${isNum(forensics?.ai_agent_share) ? `, ${fmtPct(forensics.ai_agent_share, { decimals: 1 })} AI-agent-labelled` : ""}`,
    value: isNum(forensics?.hhi_external) ? fmtInt(forensics.hhi_external) : NA,
    prov: { source: "nearblocks", name: "txns:intents.near:p1" },
  });
  items2.push({
    key: "conf",
    label: "Confidential share of volume",
    sub: !confMeasured
      ? `Assumed ${fmtPct(confShare, { decimals: 0 })} (${confWhy}); not a measurement`
      : forensics?.confidential_tvl_verified === false
        ? `TVL of ${fmtUsdCompact(forensics.confidential_tvl_usd ?? null)} is unverified by NearStats`
        : "Last 30 days",
    value: confMeasured ? fmtPct(confShare, { decimals: 1 }) : `Assumed ${fmtPct(confShare, { decimals: 0 })}`,
    badge: confMeasured ? null : (
      <Badge variant="assumption" title={forensics?.volume?.confidential_share_source ?? "Registry assumption; the nearstats public/confidential split was not used this run"}>
        Assumption
      </Badge>
    ),
    prov: { source: "nearstats", name: "summary" },
  });

  // ------------------------------------------------------------------ 3. sinks against issuance
  const sinks = supply?.current_daily_sinks_near;
  const issuance = supply?.current_daily_issuance_near ?? null;
  const netFloat = supply?.current_net_float_change_near_day ?? null;
  const epochRef = epochBlockRef(snapshot);
  const coverage = supply?.sink_coverage_ratio ?? null;
  const claim3 =
    isNum(sinks?.total) && isNum(issuance)
      ? `Buybacks, gas burn and state lock absorb ${fmtNear(sinks.total)} of the ${fmtNear(issuance)} issued each day (${fmtPct(coverage, { decimals: 1 })}).${isNum(netFloat) ? ` At spot, net supply ${netFloat > 0 ? "still grows" : netFloat < 0 ? "shrinks" : "is flat"}${netFloat !== 0 ? ` by ${fmtNear(Math.abs(netFloat))} a day` : ""}.` : ""}`
      : "Supply-sink fields are missing from this snapshot.";
  const items3: FigureItem[] = [
    { key: "iss", label: "Gross issuance per day", sub: "Measured from the last epoch's supply jump", value: fmtNear(issuance), prov: epochRef },
    { key: "buy", label: "Buyback sink per day", value: fmtNear(sinks?.buyback ?? null), prov: { source: "defillama", name: "fees:near-intents:dailyHoldersRevenue" } },
    { key: "gas", label: "Gas burn per day", value: fmtNear(sinks?.gas_burn ?? null), prov: epochRef },
    {
      key: "lock",
      label: "State-lock growth per day",
      sub: snapshot.near_rpc?.measured_state_lock_growth_sinks?.length ? `Measured on ${joinAnd(snapshot.near_rpc.measured_state_lock_growth_sinks)}` : "No archival growth measured",
      value: fmtNear(sinks?.state_lock ?? null),
      prov: { source: "near_rpc", name: "view_account:intents.near" },
    },
    { key: "net", label: "Net supply change per day", sub: "Positive means supply is still rising", value: fmtNear(netFloat, { signed: true }), tone: toneBySign(netFloat, { positiveGood: false }) },
  ];

  // ------------------------------------------------------------------ 4. valuation
  const multipleRaw = cal?.terminal_multiple_raw ?? null;
  const multipleUsed = cal?.terminal_multiple_used ?? null;
  const clipped = cal?.terminal_multiple_clipped === true;
  const floor = sotp?.inputs?.terminal_multiple_floor?.value ?? null;
  const cap = sotp?.inputs?.terminal_multiple_cap?.value ?? null;
  const claim4 = fdv
    ? `Valued path by path, the three engines give a median FDV of ${fmtUsdCompact(fdv.p50)}, ${fmtPctPoints(upside, { signed: true })} against the current market.${clipped ? ` The peer terminal multiple of ${times(multipleRaw)} is clipped to ${times(multipleUsed)}, so the multiple is an assumption, not a measurement.` : ""}`
    : "Valuation outputs are missing from this snapshot.";
  const items4: FigureItem[] = [
    {
      key: "mult",
      label: "Terminal multiple used",
      sub: `Peer median FDV over revenue, ${fmtInt(snapshot.comps?.n_peers_in_revenue_median ?? null)} peers`,
      value: times(multipleUsed),
      badge: clipped ? (
        <Badge variant="warn" title={`Raw peer median ${times(multipleRaw)} clipped to the ${times(floor, 0)} to ${times(cap, 0)} guardrails`}>
          Clipped
        </Badge>
      ) : null,
      prov: { source: "coingecko", name: "coins_markets" },
    },
    { key: "disc", label: "Discount rate", value: fmtPct(sotp?.discount_rate ?? null, { decimals: 0 }), badge: <Badge variant="assumption">Assumption</Badge> },
    { key: "floor", label: "Public take-rate floor in the model", sub: "Mean-reversion target for the public take", value: fmtBps(cal?.tau_floor_bps ?? null, { signed: false, decimals: 2 }) },
    { key: "fdv", label: "Median FDV against current", sub: isNum(fdv?.p50) ? `${fmtUsdCompact(fdv.p50)} median` : null, value: fmtPctPoints(upside, { signed: true }), tone: toneBySign(upside) },
  ];

  return (
    <section id="chain" className={cn("space-y-4", className)}>
      <SubHead title="How the thesis is built">Four measured links, each feeding the next. Every figure below is read from the snapshot; the source link on a figure opens its raw payload record.</SubHead>
      <ol className="list-none">
        <Step n={1} title="Execution headroom" claim={claim1} items={items1} empty="The execution benchmark is missing from this snapshot." />
        <Step n={2} title="Take rate and stickiness" claim={claim2} items={items2} />
        <Step n={3} title="Supply sinks against issuance" claim={claim3} items={items3} />
        <Step n={4} title="Valuation" claim={claim4} items={items4} />
      </ol>
      <MethodNote>
        <p>
          <span className="text-ink">Execution headroom.</span>{" "}
          {bench ? `Benchmark ran ${fmtUtc(bench.ran_at_utc, { seconds: true })}. ` : ""}
          Headroom is 1Click output minus the best competitor&apos;s output, in destination units for the same input (basis <code>{bench?.headroom_basis ?? "dest_units"}</code>), as the median over cells where 1Click and at least one competitor quoted. Fields: <code>execution_bench.headroom_by_archetype_bps</code>, <code>execution_bench.headroom_n_by_archetype</code>, <code>execution_bench.competitive_fee_ceiling_bps</code>
          {bench?.competitive_fee_ceiling_basis ? ` (${bench.competitive_fee_ceiling_basis})` : ""}, <code>execution_bench.n_quotes_ok</code>.
        </p>
        <p>
          <span className="text-ink">Take rate and stickiness.</span> Take = fees / volume on {fees?.take_rate_window ? `one canonical window (${fees.take_rate_window})` : "the DefiLlama 30-day window"}; capture = holders revenue / fees{fees?.volume_30d_source ? `; volume source ${fees.volume_30d_source}` : ""}. The model&apos;s public take mean-reverts from its start toward the floor at λ = {fmtNum(cal?.lambda_pub_monthly ?? null, { decimals: 2 })} a month (<code>sotp.calibration.tau_floor_bps</code>
          {sotp?.inputs?.tau_floor_bps?.justification ? `: ${sotp.inputs.tau_floor_bps.justification}` : cal?.tau_floor_source ? `: ${cal.tau_floor_source}` : ""}). Capture source: {cal?.alpha_source ?? NA}.
        </p>
        <p>
          Solver HHI (<code>intents_forensics.solver_concentration.hhi_solver</code>) is computed over {solver ? fmtInt(solver.n_fills_attributed) : NA} attributed fill participations in {solver ? fmtInt(solver.n_fills) : NA} <code>execute_intents</code> fills (NEP-413 signer payloads); the cartelisation trigger in the bear case reads this index{thin ? `, and with fewer than ${THIN_SAMPLE_FILLS} fills it is a point estimate within sampling noise` : ""}. Deposit-source HHI (<code>intents_forensics.hhi_external</code>) is over deposit callers, not solvers
          {isNum(forensics?.receipts_sampled) ? `: ${fmtInt(forensics.receipts_sampled)} receipts over ${fmtInt(forensics.pages_fetched)} pages, AI-agent-labelled share ${fmtPct(forensics.ai_agent_share, { decimals: 1 })}, bridge share ${fmtPct(forensics.bridge_share, { decimals: 1 })}` : ""}. Confidential share: <code>intents_forensics.volume.confidential_share_30d</code>, status <code>{confStatus ?? "measured"}</code>
          {forensics?.volume?.confidential_share_source ? ` (${forensics.volume.confidential_share_source})` : ""}. HHI intervals: <code>intents_forensics.solver_concentration.hhi_solver_ci90</code>, <code>intents_forensics.caller_sample.hhi_external_ci90</code> (bootstrap over the sampled units; within-sample noise only).
        </p>
        <p>
          <span className="text-ink">Supply sinks.</span> Issuance is measured from the total-supply jump at the epoch boundary (<code>supply_physics.current_daily_issuance_near</code>); buyback = holders revenue / price; gas burn = within-epoch supply drift (<code>supply_physics.current_daily_sinks_near.gas_burn</code>); state lock = archival storage growth × 10⁻⁵ NEAR per byte. Net change: <code>supply_physics.current_net_float_change_near_day</code>.
        </p>
        <p>
          <span className="text-ink">Valuation.</span> Terminal multiple <code>sotp.calibration.terminal_multiple_used</code>: raw peer-median FDV / revenue ex-NEAR {times(multipleRaw)}, guardrails {times(floor, 0)} to {times(cap, 0)}. Discount rate <code>sotp.discount_rate</code>. The total FDV P50 (<code>sotp.fdv_percentiles.p50</code>) is a percentile of the per-path engine sum, not the sum of engine P50s.
          {cal ? ` Price basis: ${cal.price_basis}; supply at horizon ${fmtNear(cal.supply_at_horizon_used)} (${cal.crossover_basis}).` : ""}
        </p>
      </MethodNote>
    </section>
  );
}
