import { Card, Table, type Column } from "@/components/ui";
import { ARCHETYPE_LABELS } from "@/lib/corridors";
import { cn } from "@/lib/cn";
import { fmtBps, fmtInt } from "@/lib/format";
import { VENUE_NAMES, type Corridor, type CorridorClipResult, type ExecutionBenchmark } from "@/lib/types";
import { TONE_TEXT, VENUE_SHORT, clipLabel, headroomMissingReason, routeName, routeVerdict, signTone, statusText, venueShort } from "./benchUtil";

interface ArchRow {
  corridor: Corridor;
  cells: CorridorClipResult[];
  median: number | null;
  n: number;
}

function HeadroomCell({ cell }: { cell: CorridorClipResult | undefined }) {
  if (!cell) return <span className="text-dim">Not run</span>;
  const h = cell.headroom_bps;
  if (typeof h !== "number") {
    const oc = cell.quotes.find((q) => q.venue === "1click");
    const short = oc && oc.status !== "ok" ? `No 1Click quote (${statusText(oc.status)})` : "Not scored";
    return (
      <span className="text-[13px] text-dim" title={headroomMissingReason(cell)}>
        {short}
      </span>
    );
  }
  return (
    <div className="flex flex-col items-end gap-0.5">
      <span className={cn("tnum font-medium", TONE_TEXT[signTone(h)])}>{fmtBps(h, { decimals: 2 })}</span>
      <span className="text-[12px] text-muted">vs {venueShort(cell.best_competitor)}</span>
    </div>
  );
}

function columns(clips: number[]): Column<ArchRow>[] {
  return [
    {
      key: "route",
      header: "Route",
      width: "15rem",
      render: (row) => (
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-ink">{ARCHETYPE_LABELS[row.corridor.archetype]}</span>
          <span className="text-[12.5px] text-muted">{routeName(row.corridor.corridor_id, row.corridor.label)}</span>
        </div>
      ),
    },
    ...clips.map<Column<ArchRow>>((clip) => ({
      key: `clip-${clip}`,
      header: clipLabel(clip),
      numeric: true,
      render: (row) => <HeadroomCell cell={row.cells.find((c) => c.clip_usd === clip)} />,
    })),
    {
      key: "median",
      header: "Median",
      numeric: true,
      title: "Median headroom over scored cells (1Click and at least one competitor returned a quote)",
      render: (row) =>
        row.median === null ? (
          <span className="text-dim">n/a</span>
        ) : (
          <div className="flex flex-col items-end gap-0.5">
            <span className={cn("tnum font-medium", TONE_TEXT[signTone(row.median)])}>{fmtBps(row.median, { decimals: 2 })}</span>
            <span className="tnum text-[12px] text-muted">
              {fmtInt(row.n)} of {fmtInt(row.cells.length)} scored
            </span>
          </div>
        ),
    },
    {
      key: "verdict",
      header: "What the quotes show",
      width: "22rem",
      render: (row) => <p className="min-w-[14rem] text-[13px] leading-snug text-ink">{routeVerdict(row.cells)}</p>,
    },
  ];
}

export interface MoatMatrixProps {
  bench: ExecutionBenchmark;
}

/**
 * Route x trade-size matrix of 1Click headroom from the committed benchmark, with the median per
 * route and a verdict built only from the cells. Negative cells read as competitor wins.
 */
export function MoatMatrix({ bench }: MoatMatrixProps) {
  const rows: ArchRow[] = bench.corridors.map((corridor) => ({
    corridor,
    cells: bench.results.filter((r) => r.corridor_id === corridor.corridor_id),
    median: bench.headroom_by_archetype_bps[corridor.archetype] ?? null,
    n: bench.headroom_n_by_archetype?.[corridor.archetype] ?? 0,
  }));
  const clips = [...bench.clips_usd].sort((a, b) => a - b);
  const byVenue = bench.competitor_friction_by_venue_bps;
  const venueCosts = byVenue
    ? VENUE_NAMES.filter((v) => v !== "1click" && byVenue[v]).map((v) => `${VENUE_SHORT[v]} ${fmtBps(byVenue[v]!.median, { signed: false, decimals: 2 })} (${fmtInt(byVenue[v]!.n)} quotes)`)
    : [];

  return (
    <Card
      title="1Click headroom by route and trade size"
      subtitle="Basis points more (green) or less (red) that 1Click delivers than the best competing quote for the same input."
      footer={venueCosts.length ? <>Median all-in cost by competitor on cross-VM quotes, the cells behind the fee ceiling: {venueCosts.join("; ")}.</> : undefined}
    >
      <Table columns={columns(clips)} rows={rows} rowKey={(r) => r.corridor.corridor_id} stickyHeader={false} dense={false} emptyText="No routes in the snapshot benchmark" />
    </Card>
  );
}
