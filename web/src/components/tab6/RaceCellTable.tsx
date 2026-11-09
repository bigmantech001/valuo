import { Card } from "@/components/ui/Card";
import { Table, type Column } from "@/components/ui/Table";
import { corridorText } from "@/components/tab1/derive";
import { ARCHETYPE_LABELS, CORRIDOR_IDS, getCorridor, VENUE_LABELS } from "@/lib/corridors";
import { fmtBps, fmtInt, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import type { BenchCell, BenchSeriesBlock } from "@/lib/history";
import type { CorridorArchetype, VenueName } from "@/lib/types";

interface Row {
  id: string;
  cell: BenchCell;
  headroom: BenchSeriesBlock | null;
}

function venueLabel(v: string): string {
  return VENUE_LABELS[v as VenueName] ?? v;
}

function shortVenue(v: string): string {
  return v === "1click" ? "1Click" : venueLabel(v);
}

function rate(r: number | null, n: number): string {
  if (r === null || !Number.isFinite(r)) return NA;
  return `${fmtPct(r, { decimals: 0 })} (${fmtInt(Math.round(r * n))}/${fmtInt(n)})`;
}

/** Per corridor x clip over every recorded race: 1Click availability, rank, and the headroom distribution. */
export function RaceCellTable({ cells, series, ciMinN }: { cells: Record<string, BenchCell>; series: Record<string, BenchSeriesBlock>; ciMinN: number | null }) {
  const order = (c: BenchCell) => {
    const i = c.corridor_id ? CORRIDOR_IDS.indexOf(c.corridor_id) : -1;
    return (i < 0 ? 99 : i) * 1e9 + (c.clip_usd ?? 0);
  };
  const rows: Row[] = Object.entries(cells)
    .map(([id, cell]) => ({ id, cell, headroom: series[`cell.${id}.headroom_bps`] ?? null }))
    .sort((a, b) => order(a.cell) - order(b.cell));

  const columns: Column<Row>[] = [
    {
      key: "route",
      header: "Route",
      render: (r) => {
        const def = r.cell.corridor_id ? getCorridor(r.cell.corridor_id) : null;
        return (
          <div>
            <div className="text-ink">{def ? corridorText(def.label) : (r.cell.corridor_id ?? NA)}</div>
            <div className="text-[12.5px] text-dim">{r.cell.archetype ? (ARCHETYPE_LABELS[r.cell.archetype as CorridorArchetype] ?? r.cell.archetype) : NA}</div>
          </div>
        );
      },
    },
    { key: "clip", header: "Clip", numeric: true, render: (r) => fmtUsdCompact(r.cell.clip_usd, { decimals: 0 }) },
    { key: "n", header: "Races", numeric: true, render: (r) => fmtInt(r.cell.n_runs) },
    { key: "ok", header: "1Click quoted", numeric: true, title: "Share of races in which 1Click returned an ok quote", render: (r) => rate(r.cell.oneclick_ok_rate, r.cell.n_runs) },
    { key: "rank1", header: "1Click ranked first", numeric: true, title: "Share of races in which 1Click delivered the most output of all venues", render: (r) => rate(r.cell.oneclick_rank1_rate, r.cell.n_runs) },
    {
      key: "best",
      header: "Best competitor",
      title: "Competitor with the highest output, counted per race",
      render: (r) => {
        const entries = Object.entries(r.cell.best_competitor_counts ?? {}).filter(([k]) => k !== "None" && k !== "null").sort((a, b) => b[1] - a[1]);
        if (!entries.length) return <span className="text-dim">none quoted</span>;
        return <span className="tnum">{entries.map(([k, n]) => `${shortVenue(k)} ${fmtInt(n)}/${fmtInt(r.cell.n_runs)}`).join(", ")}</span>;
      },
    },
    {
      key: "median",
      header: "Median headroom",
      numeric: true,
      title: "Median over races of (1Click output - best competitor output) / best competitor output, in bps",
      render: (r) => {
        const s = r.headroom?.stats;
        const med = s?.median ?? null;
        if (med === null) return <span className="text-dim">n/a: no paired quote</span>;
        return <span className={med > 0 ? "text-emerald" : med < 0 ? "text-crimson" : "text-ink"}>{fmtBps(med, { decimals: 2 })}</span>;
      },
    },
    {
      key: "ci",
      header: "90% CI of median",
      numeric: true,
      render: (r) => {
        const s = r.headroom?.stats;
        if (!s || s.n === 0) return <span className="text-dim">{NA}</span>;
        if (s.median_ci90) return `${fmtBps(s.median_ci90[0], { decimals: 2 })} to ${fmtBps(s.median_ci90[1], { decimals: 2 })}`;
        return (
          <span className="whitespace-nowrap text-dim" title={`${fmtInt(s.n)} races recorded so far`}>
            needs ≥{ciMinN !== null ? fmtInt(ciMinN) : NA} races
          </span>
        );
      },
    },
    {
      key: "range",
      header: "Range",
      numeric: true,
      render: (r) => {
        const s = r.headroom?.stats;
        if (!s || s.n === 0 || s.min === null || s.max === null) return <span className="text-dim">{NA}</span>;
        if (s.n === 1) return <span className="text-dim">one value</span>;
        return <span className="whitespace-nowrap">{fmtBps(s.min, { decimals: 1 })} to {fmtBps(s.max, { decimals: 1 })}</span>;
      },
    },
    {
      key: "venues",
      header: "Competitors not quoting",
      render: (r) => {
        const out: string[] = [];
        for (const [venue, counts] of Object.entries(r.cell.venue_status_counts ?? {})) {
          if (venue === "1click") continue;
          const notOk = Object.entries(counts).filter(([st]) => st !== "ok");
          const total = Object.values(counts).reduce((a, b) => a + b, 0);
          if (!notOk.length) continue;
          out.push(`${shortVenue(venue)}: ${notOk.map(([st, n]) => `${st.replace(/_/g, " ")}${n !== total ? ` ${fmtInt(n)}/${fmtInt(total)}` : ""}`).join(", ")}`);
        }
        return out.length ? <span className="text-[12.5px] text-muted">{out.join("; ")}</span> : <span className="text-[12.5px] text-dim">all quoted</span>;
      },
    },
  ];

  return (
    <Card
      kicker="Hourly quote race · per route and clip"
      title="Where 1Click wins, and how consistently"
      subtitle="Each row pools every recorded race for one route and clip size. Headroom is 1Click's output against the best competing quote in the same race; positive means 1Click delivers more."
      padded={false}
      bodyClassName="px-2 pb-2"
    >
      <Table columns={columns} rows={rows} rowKey={(r) => r.id} emptyText="no races in artifacts/history/bench.jsonl yet" />
    </Card>
  );
}
