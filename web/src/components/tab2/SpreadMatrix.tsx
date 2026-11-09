import { Card, Table, type Column } from "@/components/ui";
import { cn } from "@/lib/cn";
import { fmtBps, fmtInt } from "@/lib/format";
import { VENUE_NAMES, type Corridor, type CorridorClipResult, type ExecutionBenchmark, type VenueName, type VenueQuote } from "@/lib/types";
import {
  TONE_TEXT,
  VENUE_SOURCE,
  cellFrictionBasis,
  clipLabel,
  capitalize,
  headroomMissingReason,
  quoteByVenue,
  quoteRecordName,
  routeName,
  signTone,
  venueShort,
  type FrictionBasis,
} from "./benchUtil";
import { VenueCell } from "./VenueCell";
import { VenueLabel } from "./VenueLabel";

interface Row {
  cell: CorridorClipResult;
  basis: FrictionBasis;
  byVenue: Partial<Record<VenueName, VenueQuote>>;
}

function buildColumns(corridor: Corridor): Column<Row>[] {
  const venueCols: Column<Row>[] = VENUE_NAMES.map((v) => ({
    key: v,
    header: <VenueLabel venue={v} />,
    render: (row) => {
      const q = row.byVenue[v];
      const provenance = q && !q.declared ? { source: VENUE_SOURCE[v], name: quoteRecordName(row.cell.corridor_id, row.cell.clip_usd) } : null;
      return (
        <VenueCell
          quote={q}
          destDecimals={corridor.destination.decimals}
          destSymbol={corridor.destination.symbol}
          basis={row.basis}
          provenance={provenance}
          isBestCompetitor={row.cell.best_competitor === v}
        />
      );
    },
  }));
  return [
    {
      key: "clip",
      header: "Trade size",
      width: "7rem",
      render: (row) => (
        <span className="tnum font-medium text-ink" title={`Input sent: ${row.cell.quotes[0]?.amount_in_raw ?? "n/a"} raw ${corridor.origin.symbol} units`}>
          {clipLabel(row.cell.clip_usd)}
        </span>
      ),
    },
    ...venueCols,
    {
      key: "headroom",
      header: "1Click headroom",
      numeric: true,
      title: "1Click output vs the best competitor's output, in basis points; positive = 1Click delivers more",
      render: (row) => {
        const h = row.cell.headroom_bps;
        if (typeof h !== "number") {
          return (
            <div className="flex flex-col items-end gap-0.5">
              <span className="text-dim">n/a</span>
              <span className="max-w-[10rem] text-right text-[12px] leading-snug text-muted">{capitalize(headroomMissingReason(row.cell).replace(/^1Click no liquidity: No liquidity available$/, "No 1Click liquidity"))}</span>
            </div>
          );
        }
        return (
          <div className="flex flex-col items-end gap-0.5">
            <span className={cn("tnum font-medium", TONE_TEXT[signTone(h)])}>{fmtBps(h, { decimals: 2 })}</span>
            <span className="text-[12px] text-muted">
              vs {venueShort(row.cell.best_competitor)}
              {row.cell.oneclick_rank != null ? `, rank ${fmtInt(row.cell.oneclick_rank)} of ${fmtInt(row.cell.n_venues_ok)}` : ""}
            </span>
          </div>
        );
      },
    },
  ];
}

function CorridorTable({ corridor, cells }: { corridor: Corridor; cells: CorridorClipResult[] }) {
  const rows: Row[] = [...cells]
    .sort((a, b) => a.clip_usd - b.clip_usd)
    .map((cell) => ({ cell, basis: cellFrictionBasis(cell), byVenue: quoteByVenue(cell.quotes) }));
  const declared = Object.entries(corridor.venues_declared_unsupported ?? {});
  return (
    <div className="min-w-0">
      <h4 className="text-[15px] font-medium text-ink">{routeName(corridor.corridor_id, corridor.label)}</h4>
      {declared.length ? (
        <p className="mt-0.5 text-[13px] text-muted">
          {declared.map(([v, why]) => `${venueShort(v)} not quoted: ${why}.`).join(" ")}
        </p>
      ) : null}
      <Table className="mt-2" columns={buildColumns(corridor)} rows={rows} rowKey={(r) => `${r.cell.corridor_id}:${r.cell.clip_usd}`} stickyHeader={false} emptyText="No cells for this route in the snapshot" />
    </div>
  );
}

export interface SpreadMatrixProps {
  bench: ExecutionBenchmark;
  /** count of `quote:*` records in the manifest, null when no manifest was loaded */
  quoteRecordCount?: number | null;
}

/**
 * Per-venue quotes for every route and trade size in the committed benchmark: destination units out,
 * all-in cost, settlement estimate and the raw-response source of each quote, plus 1Click headroom.
 */
export function SpreadMatrix({ bench }: SpreadMatrixProps) {
  return (
    <Card
      title="Every quote in the benchmark"
      subtitle="Amount each venue would deliver for the same input, with its all-in cost and settlement estimate. Each figure links to the raw response it was parsed from."
    >
      <div className="space-y-8">
        {bench.corridors.map((c) => (
          <CorridorTable key={c.corridor_id} corridor={c} cells={bench.results.filter((r) => r.corridor_id === c.corridor_id)} />
        ))}
      </div>
    </Card>
  );
}
