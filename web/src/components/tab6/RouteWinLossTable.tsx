import { Card } from "@/components/ui/Card";
import { Table, type Column } from "@/components/ui/Table";
import { corridorText } from "@/components/tab1/derive";
import { ARCHETYPE_LABELS, CORRIDOR_IDS, getCorridor, VENUE_LABELS } from "@/lib/corridors";
import { fmtBps, fmtInt, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import type { CorridorRouteRecord, RouteRecord, RoutesSummary } from "@/lib/history";
import type { CorridorArchetype, VenueName } from "@/lib/types";
import { fmtSpan, plural } from "./derive";

function venueLabel(v: string | null): string {
  if (!v) return NA;
  return VENUE_LABELS[v as VenueName] ?? v;
}

function routeLabel(r: CorridorRouteRecord): string {
  const def = getCorridor(r.corridor_id);
  return def ? corridorText(def.label) : r.corridor_id;
}

function spanText(days: number | null): string {
  return days === null ? NA : fmtSpan(days * 86_400_000);
}

function pct0(v: number | null): string {
  return fmtPct(v, { decimals: 0 });
}

function ciText(ci: [number, number] | null): string {
  return ci ? `${pct0(ci[0])} to ${pct0(ci[1])}` : NA;
}

/** "72–0"; ties are named only when there are any. */
function wl(r: RouteRecord): string {
  return `${fmtInt(r.wins)}–${fmtInt(r.losses)}${r.ties ? `, ${fmtInt(r.ties)} tied` : ""}`;
}

/** Headline in the house register: one sentence, the number first, the interval in brackets. */
export function winLossHeadline(routes: RoutesSummary | null | undefined): string | null {
  const o = routes?.overall;
  if (!o || o.decided === 0 || o.win_rate === null) return null;
  return `1Click won ${pct0(o.win_rate)} of ${plural(o.races, "contested race")} across ${plural(o.n_routes, "route")} over ${spanText(o.span_days)}${o.win_rate_ci90 ? ` (90% CI ${ciText(o.win_rate_ci90)})` : ""}`;
}

/** One clause per route, worded by the side of 50% the win rate falls on. */
function routeSentence(rows: CorridorRouteRecord[]): string {
  const won = rows.filter((r) => r.win_rate !== null && r.win_rate >= 0.5);
  const lost = rows.filter((r) => r.win_rate !== null && r.win_rate < 0.5);
  const parts: string[] = [];
  if (won.length) parts.push(`It won ${won.map((r) => (r.losses === 0 ? `every decided race on ${routeLabel(r)}` : `${pct0(r.win_rate)} on ${routeLabel(r)}`)).join(" and ")}`);
  if (lost.length) parts.push(`${won.length ? "and lost" : "It lost"} most races on ${lost.map((r) => `${routeLabel(r)} (won ${pct0(r.win_rate)}, beaten mostly by ${venueLabel(r.top_beaten_by)})`).join(" and ")}`);
  return parts.length ? `${parts.join(" ")}.` : "";
}

/**
 * 1Click's win/loss record per route over every recorded hourly race (summary.bench.routes, quant/valuo/history.py).
 * A race is one (run, route, clip) cell where 1Click and at least one competitor both quoted; clips are pooled
 * per route. The interval is the 90% Wilson score interval on wins / (wins + losses).
 */
export function RouteWinLossTable({ routes }: { routes: RoutesSummary | null | undefined }) {
  if (!routes) {
    return (
      <Card kicker="Hourly quote race · win/loss by route" title="Win/loss by route" subtitle="summary.json carries no win/loss block yet; make history-summary rebuilds it from bench.jsonl.">
        <p className="text-[13px] text-dim">{NA}</p>
      </Card>
    );
  }
  const order = (id: string) => {
    const i = CORRIDOR_IDS.indexOf(id);
    return i < 0 ? 99 : i;
  };
  const rows = Object.values(routes.by_corridor).sort((a, b) => order(a.corridor_id) - order(b.corridor_id));
  const o = routes.overall;
  const headline = winLossHeadline(routes) ?? "No contested race recorded yet";

  const columns: Column<CorridorRouteRecord>[] = [
    {
      key: "route",
      header: "Route",
      render: (r) => (
        <div>
          <div className="text-ink">{routeLabel(r)}</div>
          <div className="text-[12.5px] text-dim">
            {r.archetype ? (ARCHETYPE_LABELS[r.archetype as CorridorArchetype] ?? r.archetype) : NA} · clips {r.clips_usd.map((c) => fmtUsdCompact(c, { decimals: 0 })).join(", ")}
          </div>
        </div>
      ),
    },
    {
      key: "races",
      header: "Races",
      numeric: true,
      title: "Contested races: 1Click and at least one competitor quoted ok. Excluded cells are listed under the table.",
      render: (r) => (
        <span title={r.excluded ? `${fmtInt(r.excluded)} cells excluded: ${Object.entries(r.excluded_reasons).map(([k, n]) => `${k.replace(/_/g, " ")} ${fmtInt(n)}`).join(", ")}` : undefined}>
          {fmtInt(r.races)}
          {r.excluded ? <span className="text-dim"> (+{fmtInt(r.excluded)} excl.)</span> : null}
        </span>
      ),
    },
    {
      key: "won",
      header: "1Click won",
      numeric: true,
      title: "wins / (wins + losses), with the win–loss count",
      render: (r) =>
        r.win_rate === null ? (
          <span className="text-dim">no decided race</span>
        ) : (
          <span className="whitespace-nowrap">
            <span className={r.win_rate >= 0.5 ? "text-emerald" : "text-crimson"}>{pct0(r.win_rate)}</span> <span className="text-muted">({wl(r)})</span>
          </span>
        ),
    },
    { key: "ci", header: "90% CI", numeric: true, title: "Wilson score interval on the win rate; assumes independent races (see note)", render: (r) => <span className="whitespace-nowrap">{ciText(r.win_rate_ci90)}</span> },
    {
      key: "margin",
      header: "Typical margin",
      numeric: true,
      title: "Median headroom on wins and on losses: (1Click output - best competitor output) / best competitor output, in bps",
      render: (r) => (
        <div className="flex flex-col items-end gap-0.5 whitespace-nowrap">
          {r.median_headroom_bps_wins !== null ? <span className="text-emerald">wins by {fmtBps(r.median_headroom_bps_wins, { decimals: 2, signed: false })}</span> : null}
          {r.median_headroom_bps_losses !== null ? <span className="text-crimson">loses by {fmtBps(Math.abs(r.median_headroom_bps_losses), { decimals: 2, signed: false })}</span> : null}
          {r.median_headroom_bps_wins === null && r.median_headroom_bps_losses === null ? <span className="text-dim">{NA}</span> : null}
        </div>
      ),
    },
    {
      key: "beaten",
      header: "Winner when 1Click loses",
      render: (r) =>
        r.losses === 0 ? (
          <span className="text-dim">never lost</span>
        ) : (
          <span className="tnum">
            {venueLabel(r.top_beaten_by)} {fmtInt(r.top_beaten_by_n)} of {fmtInt(r.losses)}
            {Object.keys(r.beaten_by_counts).length > 1 ? (
              <span className="text-[12.5px] text-dim">
                {" "}
                ({Object.entries(r.beaten_by_counts)
                  .filter(([k]) => k !== r.top_beaten_by)
                  .map(([k, n]) => `${venueLabel(k)} ${fmtInt(n)}`)
                  .join(", ")})
              </span>
            ) : null}
          </span>
        ),
    },
    { key: "span", header: "Span", numeric: true, render: (r) => <span className="whitespace-nowrap text-muted">over {spanText(r.span_days)}</span> },
  ];

  const excludedNote = o.excluded
    ? ` ${plural(o.excluded, "cell")} excluded as not a contest (${Object.entries(o.excluded_reasons)
        .map(([k, n]) => `${k.replace(/_/g, " ")}: ${fmtInt(n)}`)
        .join(", ")}).`
    : " No cell was excluded: 1Click and at least one competitor quoted in every recorded cell.";

  return (
    <Card
      kicker="Hourly quote race · win/loss by route"
      title={headline}
      subtitle={`${routeSentence(rows)} A race is one route and clip in one hourly run; the three clips of a route are pooled.`}
      padded={false}
      bodyClassName="px-2 pb-2"
      footer={
        <>
          Win: headroom at or above +{routes.method.tie_bps} bps; loss: at or below −{routes.method.tie_bps} bps; anything between is a tie, reported and left out of the win rate ({plural(o.ties, "tie")} so far).
          {excludedNote} The interval is a 90% Wilson score interval. It treats races as independent; consecutive hourly races on one route are autocorrelated and the clips of one run share a market state, so the true uncertainty is wider than shown.
        </>
      }
    >
      <Table columns={columns} rows={rows} rowKey={(r) => r.corridor_id} emptyText="no races in artifacts/history/bench.jsonl yet" />
    </Card>
  );
}
