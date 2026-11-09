import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Badge, QuoteStatusBadge } from "@/components/ui";
import { fmtBps, fmtMs, fmtNum, fmtSeconds } from "@/lib/format";
import type { RawRecord, VenueQuote } from "@/lib/types";
import { frictionOf, truncate, type FrictionBasis } from "./benchUtil";

/** Manifest (source, name) pair, a live RawRecord, or null for a venue that made no HTTP exchange. */
export type VenueProvenance = { source: string; name: string } | RawRecord | null;

export interface VenueCellProps {
  quote: VenueQuote | undefined;
  destDecimals: number;
  destSymbol: string;
  basis: FrictionBasis;
  provenance: VenueProvenance;
  showLatency?: boolean;
  isBestCompetitor?: boolean;
}

/**
 * One venue's quote in a benchmark cell: destination units out, all-in cost on the cell's basis,
 * settlement estimate and the source of the raw response. A failed quote shows its status and the
 * venue's own message; nothing is substituted.
 */
export function VenueCell({ quote, destDecimals, destSymbol, basis, provenance, showLatency = false, isBestCompetitor = false }: VenueCellProps) {
  if (!quote) return <span className="text-[13px] text-dim">Not attempted</span>;
  const ok = quote.status === "ok";
  const friction = ok ? frictionOf(quote, basis) : null;
  const msg = quote.error_message ?? null;
  return (
    <div className="flex min-w-[9.5rem] flex-col gap-0.5 text-left">
      {ok ? (
        <>
          <div className="tnum text-[13.5px] text-ink">
            {fmtNum(quote.amount_out_formatted, { decimals: destDecimals })} <span className="text-muted">{destSymbol}</span>
          </div>
          <div className="tnum text-[12px] text-muted">
            <span title={quote.note ?? quote.usd_basis_note ?? "All-in cost: input less output, in basis points of input"}>
              {friction === null ? "cost n/a" : `${fmtBps(friction, { signed: false, decimals: 2 })} cost`}
            </span>
            <span className="text-dim">, </span>
            {fmtSeconds(quote.time_estimate_s)}
          </div>
          {quote.routes_via_near_intents || isBestCompetitor ? (
            <div className="mt-0.5 flex flex-wrap items-center gap-1">
              {quote.routes_via_near_intents ? (
                <Badge variant="warn" title={`LI.FI tool "${quote.route_tool ?? "near"}" resells NEAR Intents execution; not an independent price`}>
                  Via NEAR Intents
                </Badge>
              ) : null}
              {isBestCompetitor ? <span className="text-[12px] text-muted">Best competitor</span> : null}
            </div>
          ) : null}
        </>
      ) : (
        <>
          <div>
            <QuoteStatusBadge status={quote.status} title={msg ?? undefined} />
          </div>
          <div className="text-[12px] leading-snug text-muted" title={msg ?? undefined}>
            {quote.declared ? "Declared unsupported: " : null}
            {msg ? truncate(msg.replace(/^[A-Z_]+:\s*/, ""), 70) : "No message returned"}
          </div>
        </>
      )}
      <div className="flex flex-wrap items-center gap-1.5 text-[12px] text-dim">
        {showLatency ? <span className="tnum">{fmtMs(quote.latency_ms)}</span> : null}
        {provenance ? (
          <ProvenanceBadge {...("sha256" in provenance ? { record: provenance } : { source: provenance.source, name: provenance.name })} />
        ) : quote.declared ? (
          <span>No HTTP exchange</span>
        ) : null}
      </div>
    </div>
  );
}
