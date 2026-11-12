"use client";

import { useState } from "react";
import { Card, Slider, Toggle } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
import { fmtBps, fmtInt, fmtNum, fmtSeconds, fmtUtc } from "@/lib/format";
import {
  ladderCellAt,
  ladderMaxCost,
  ladderOutcomeText,
  ladderSizeLabel,
  type LadderCell,
  type LadderCorridor,
  type LadderVenue,
  type LiquidityLadder as LiquidityLadderData,
} from "@/lib/liquidityLadder";
import { VENUE_COLORS } from "@/lib/theme";
import { VENUE_NAMES, type VenueName } from "@/lib/types";
import { truncate, venueShort } from "./benchUtil";
import { VenueLabel } from "./VenueLabel";

const isVenueName = (v: string): v is VenueName => (VENUE_NAMES as readonly string[]).includes(v);

function Venue({ venue }: { venue: string }) {
  return isVenueName(venue) ? <VenueLabel venue={venue} /> : <span className="whitespace-nowrap">{venueShort(venue)}</span>;
}

/** "ETH USDC -> SOL USDC" reads as "ETH USDC to SOL USDC" in prose. */
const arrowsToWords = (s: string): string => s.replace(/\s*->\s*/g, " to ");

function corridorLabel(c: LadderCorridor): string {
  return arrowsToWords(c.label);
}

/** Hover text of one cell: what the venue answered and where the raw response is. */
function cellTitle(venue: string, cell: LadderCell | null): string {
  if (!cell) return `${venueShort(venue)}: not attempted`;
  const where = cell.record_name ? ` Raw response: ${cell.record_source}/${cell.record_name}.` : "";
  if (cell.outcome === "quoted") {
    const via = cell.via_near_intents ? " Routed through NEAR Intents (1Click execution resold)." : cell.route_tool ? ` Route: ${cell.route_tool}.` : "";
    return `${venueShort(venue)} at ${ladderSizeLabel(cell.size_usd)}: ${fmtBps(cell.cost_bps, { decimals: 2, signed: false })} all-in, settles in about ${fmtSeconds(cell.time_estimate_s)}.${via}${where}`;
  }
  return `${venueShort(venue)} at ${ladderSizeLabel(cell.size_usd)}: ${ladderOutcomeText(cell).toLowerCase()}${cell.message ? ` (${cell.message})` : ""}.${where}`;
}

/** One venue at the chosen size: a cost bar on the route's common scale, or the reason there is no quote. */
function VenueRow({ venue, cell, maxCost, cheapest }: { venue: LadderVenue; cell: LadderCell | null; maxCost: number; cheapest: boolean }) {
  const quoted = cell?.outcome === "quoted" && typeof cell.cost_bps === "number";
  const cost = quoted ? (cell.cost_bps as number) : null;
  const width = cost != null && maxCost > 0 ? Math.max(1.5, (Math.max(0, cost) / maxCost) * 100) : 0;
  return (
    <li className={cn("grid grid-cols-[5rem_minmax(0,1fr)] items-center gap-x-3 gap-y-1 py-2.5 sm:grid-cols-[6rem_minmax(0,1fr)]", !quoted && "text-dim")} title={cellTitle(venue.venue, cell)}>
      <span className={cn("text-[14px]", quoted ? "text-ink" : "text-muted")}>
        <Venue venue={venue.venue} />
      </span>
      {cost != null ? (
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <div className="h-2 min-w-0 flex-1 rounded-full bg-surface-2">
              <div className="h-2 rounded-full" style={{ width: `${width}%`, backgroundColor: VENUE_COLORS[venue.venue] ?? "var(--color-muted)" }} />
            </div>
            <span className="tnum w-[5.5rem] shrink-0 text-right text-[14px] font-medium text-ink">{fmtBps(cost, { decimals: 2, signed: false })}</span>
          </div>
          <p className="mt-0.5 text-[12px] leading-snug text-muted">
            {cheapest ? "Cheapest at this size. " : ""}
            Settles in about {fmtSeconds(cell?.time_estimate_s)}
            {cell?.via_near_intents ? "; routed through NEAR Intents, so this is 1Click execution resold" : ""}
          </p>
        </div>
      ) : !venue.routes ? (
        <div className="min-w-0">
          <p className="text-[14px] text-muted">Does not route this corridor</p>
          {venue.cells.find((c) => c.called)?.message ? <p className="mt-0.5 text-[12px] leading-snug text-dim">{truncate(venue.cells.find((c) => c.called)?.message ?? "", 110)}</p> : null}
        </div>
      ) : (
        <div className="min-w-0">
          <p className="text-[14px] text-muted">{ladderOutcomeText(cell)}</p>
          <p className="mt-0.5 text-[12px] leading-snug text-dim">
            {cell?.message && cell.outcome !== "not_attempted" ? `${truncate(cell.message, 110)} ` : ""}
            {venue.largest_size_quoted_usd != null ? `Largest size quoted: ${ladderSizeLabel(venue.largest_size_quoted_usd)}.` : ""}
          </p>
        </div>
      )}
    </li>
  );
}

function matrixText(cell: LadderCell | null, routes: boolean): { text: string; quoted: boolean } {
  if (!routes) return { text: "-", quoted: false };
  if (!cell) return { text: "not run", quoted: false };
  switch (cell.outcome) {
    case "quoted":
      return { text: fmtNum(cell.cost_bps, { decimals: 2 }), quoted: true };
    case "no_liquidity":
      return { text: "refused", quoted: false };
    case "unsupported":
      return { text: cell.called ? "refused" : "-", quoted: false };
    case "error":
      return { text: "error", quoted: false };
    default:
      return { text: "not run", quoted: false };
  }
}

export interface LiquidityLadderProps {
  data: LiquidityLadderData | null | undefined;
}

/**
 * Liquidity cliff ladder: for one route, which venues still quote as the trade size rises from $1K to $5M
 * and what the all-in cost is at each size. "Largest size quoted" is the top rung a venue answered in one
 * run of dry quotes; it is not depth.
 */
export function LiquidityLadder({ data }: LiquidityLadderProps) {
  const [corridorId, setCorridorId] = useState<string | null>(null);
  const [sizeIdx, setSizeIdx] = useState<number | null>(null);
  if (!data || !Array.isArray(data.corridors) || data.corridors.length === 0 || !Array.isArray(data.sizes_usd) || data.sizes_usd.length === 0) return null;

  const sizes = data.sizes_usd;
  const corridor = data.corridors.find((c) => c.corridor_id === corridorId) ?? data.corridors[0];
  // Default rung: the benchmark's largest trade size ($250K) when the ladder has it, else the middle rung.
  const defaultIdx = sizes.indexOf(250_000) >= 0 ? sizes.indexOf(250_000) : Math.floor(sizes.length / 2);
  const idx = Math.min(sizes.length - 1, Math.max(0, sizeIdx ?? defaultIdx));
  const size = sizes[idx];
  const maxCost = ladderMaxCost(corridor);
  const cheapest = corridor.cheapest_by_size.find((r) => r.size_usd === size) ?? null;
  const oneClick = corridor.venues.find((v) => v.venue === "1click") ?? null;
  const nRouting = corridor.venues.filter((v) => v.routes).length;
  const counts = data.outcome_counts ?? {};

  return (
    <Card
      kicker="Size limits"
      title={`${arrowsToWords(data.headline)}.`}
      subtitle={`Non-binding quotes at ${fmtInt(sizes.length)} sizes from ${ladderSizeLabel(sizes[0])} to ${ladderSizeLabel(sizes[sizes.length - 1])} on each benchmarked route, run ${fmtUtc(data.ran_at_utc)}. "Largest size quoted" is the top size a venue answered in this run. It is not depth.`}
    >
      <div className="space-y-5">
        <div className="grid gap-x-8 gap-y-4 md:grid-cols-2">
          <Toggle
            label="Route"
            value={corridor.corridor_id}
            onChange={setCorridorId}
            options={data.corridors.map((c) => ({ value: c.corridor_id, label: corridorLabel(c) }))}
          />
          <Slider
            label="Trade size"
            value={idx}
            min={0}
            max={sizes.length - 1}
            step={1}
            onChange={setSizeIdx}
            format={(i) => ladderSizeLabel(sizes[Math.round(i)])}
          />
        </div>

        <div>
          <h3 className="text-[15px] font-medium text-ink">
            {cheapest && cheapest.n_quoted > 0
              ? `${fmtInt(cheapest.n_quoted)} of ${fmtInt(nRouting)} venues quote ${ladderSizeLabel(size)} on ${corridorLabel(corridor)}; ${venueShort(cheapest.venue)} is cheapest at ${fmtBps(cheapest.cost_bps, { decimals: 2, signed: false })}`
              : `No venue quotes ${ladderSizeLabel(size)} on ${corridorLabel(corridor)}`}
          </h3>
          <p className="mt-0.5 text-[12.5px] text-muted">
            All-in cost in basis points of the amount sent; lower is better. Bars share one scale across sizes on this route (0 to {fmtBps(maxCost, { decimals: 1, signed: false })}).
          </p>
          <ul className="mt-2 divide-y divide-border border-y border-border">
            {corridor.venues.map((v) => (
              <VenueRow key={v.venue} venue={v} cell={ladderCellAt(v, size)} maxCost={maxCost} cheapest={cheapest?.venue === v.venue} />
            ))}
          </ul>
          {oneClick ? (
            <p className="mt-2 text-[13px] leading-relaxed text-muted">
              1Click on this route: largest size quoted{" "}
              <span className="tnum font-medium text-ink">{ladderSizeLabel(oneClick.largest_size_quoted_usd)}</span>
              {oneClick.first_size_refused_usd != null ? (
                <>
                  , first size refused <span className="tnum font-medium text-ink">{ladderSizeLabel(oneClick.first_size_refused_usd)}</span>
                </>
              ) : null}
              . Best competitor: {venueShort(corridor.best_competitor)}{" "}
              <span className="tnum font-medium text-ink">{ladderSizeLabel(corridor.best_competitor_largest_size_quoted_usd)}</span>
              {corridor.best_competitor_via_near_intents
                ? `, routed through NEAR Intents; the largest quote on an independent route is ${ladderSizeLabel(corridor.best_independent_competitor_largest_size_quoted_usd)} (${venueShort(corridor.best_independent_competitor)})`
                : ""}
              .{oneClick.non_monotone ? " 1Click refused a size below its largest size quoted, so that figure is not a clean limit." : ""}
            </p>
          ) : null}
        </div>

        <div>
          <h3 className="text-[15px] font-medium text-ink">Cost at every size, {corridorLabel(corridor)}</h3>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-[13px]">
              <thead>
                <tr className="border-b border-border-strong text-left text-[12.5px] text-muted">
                  <th scope="col" className="py-1.5 pr-3 font-normal">
                    Venue
                  </th>
                  {sizes.map((s, i) => (
                    <th key={s} scope="col" className={cn("px-1 py-1 text-right font-normal", i === idx && "bg-surface-2")}>
                      <button
                        type="button"
                        onClick={() => setSizeIdx(i)}
                        aria-pressed={i === idx}
                        title={`Show ${ladderSizeLabel(s)} above`}
                        className={cn("tnum rounded px-1 py-0.5 hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50", i === idx ? "font-medium text-ink" : "text-muted")}
                      >
                        {ladderSizeLabel(s)}
                      </button>
                    </th>
                  ))}
                  <th scope="col" className="py-1.5 pl-3 text-right font-normal">
                    Largest size quoted
                  </th>
                </tr>
              </thead>
              <tbody>
                {corridor.venues.map((v) => (
                  <tr key={v.venue} className="border-b border-border">
                    <th scope="row" className="py-2 pr-3 text-left font-normal text-ink">
                      <Venue venue={v.venue} />
                    </th>
                    {sizes.map((s, i) => {
                      const cell = ladderCellAt(v, s);
                      const m = matrixText(cell, v.routes);
                      const best = m.quoted && corridor.cheapest_by_size.find((r) => r.size_usd === s)?.venue === v.venue;
                      return (
                        <td key={s} title={cellTitle(v.venue, cell)} className={cn("tnum px-2 py-2 text-right", i === idx && "bg-surface-2", m.quoted ? (best ? "font-semibold text-ink" : "text-ink") : "text-dim")}>
                          {m.text}
                          {cell?.via_near_intents ? <sup className="ml-0.5 text-muted">N</sup> : null}
                        </td>
                      );
                    })}
                    <td className="tnum py-2 pl-3 text-right text-ink">
                      {v.routes ? ladderSizeLabel(v.largest_size_quoted_usd) : "does not route"}
                      {v.non_monotone ? <span className="ml-1 text-[12px] text-amber">gap</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[12.5px] leading-relaxed text-muted">
            Figures are all-in cost in bps; bold marks the cheapest venue at that size. &quot;refused&quot; is the venue&apos;s explicit answer that it will not quote the size, &quot;-&quot; a route the venue does not serve,
            &quot;not run&quot; a request that did not finish inside the time budget and says nothing about liquidity. <sup>N</sup> marks a LI.FI quote routed through NEAR Intents. &quot;gap&quot; marks a venue that refused a size below
            its largest size quoted. Select a size in the header to inspect it above.
          </p>
        </div>

        <p className="border-l-2 border-border-strong pl-3 text-[14px] leading-relaxed text-ink">{arrowsToWords(data.takeaway)}</p>

        <MethodNote summary="Method and limits">
          <p>
            Each cell is one dry quote request sent with the same request body the benchmark uses, at a larger or smaller input. 1Click is called with <code>dry: true</code>, so no deposit address is created and nothing is
            binding. Cost: {data.cost_definition}.
          </p>
          <p>
            This run ({fmtUtc(data.ran_at_utc, { seconds: true })}): {fmtInt(counts.quoted ?? 0)} cells quoted, {fmtInt(counts.no_liquidity ?? 0)} refused, {fmtInt(counts.error ?? 0)} failed, {fmtInt(counts.not_attempted ?? 0)} not
            attempted, {fmtInt(counts.unsupported ?? 0)} on routes a venue does not serve, of {fmtInt(data.n_cells)}; {fmtNum(data.elapsed_s, { decimals: 1 })} s against a {fmtNum(data.budget_s, { decimals: 0 })} s budget. Raw
            responses are stored and hashed under <code>{data.record_name_pattern}</code>.
          </p>
          <ul className="list-disc space-y-1 pl-5">
            {data.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </MethodNote>
      </div>
    </Card>
  );
}
