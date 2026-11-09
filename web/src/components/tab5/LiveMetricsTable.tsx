import type { BearCase } from "@/lib/types";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Badge, Card, Table, type Column } from "@/components/ui";
import { fmtMetricValue, LIVE_METRIC_META, metricLabel } from "./bearData";

interface LiveRow {
  key: string;
  value: number | boolean | null;
}

function ValueCell({ row }: { row: LiveRow }) {
  if (row.value === null) return <span className="text-dim" title="Null in the snapshot: the collector did not measure this value">Not measured</span>;
  if (typeof row.value === "boolean") return <span className={row.value ? "text-ink" : "text-amber"}>{row.value ? "Yes" : "No"}</span>;
  return <span className="tnum text-ink">{fmtMetricValue(row.key, row.value)}</span>;
}

const columns: Column<LiveRow>[] = [
  { key: "metric", header: "Metric", width: "24%", render: (r) => <span className="text-ink" title={r.key}>{metricLabel(r.key)}</span> },
  { key: "value", header: "Value", numeric: true, width: "12%", render: (r) => <ValueCell row={r} /> },
  {
    key: "describe",
    header: "What it measures",
    render: (r) => <span className="block max-w-[34rem] text-[13px] leading-snug text-muted">{LIVE_METRIC_META[r.key]?.describe ?? "No description for this key in the terminal."}</span>,
  },
  {
    key: "provenance",
    header: "Source",
    render: (r) => {
      const p = LIVE_METRIC_META[r.key]?.provenance[0];
      if (!p) return <span className="text-dim">No mapped record</span>;
      return <ProvenanceBadge source={p.source} name={p.name} />;
    },
  },
];

/** Every measured value the triggers were graded against, with the raw-payload record behind it. */
export function LiveMetricsTable({ bear }: { bear: BearCase }) {
  const lm = (bear.live_metrics ?? {}) as Record<string, unknown>;
  const rows: LiveRow[] = Object.entries(lm).map(([key, v]) => ({
    key,
    value: typeof v === "number" && Number.isFinite(v) ? v : typeof v === "boolean" ? v : null,
  }));
  const unmeasured = rows.filter((r) => r.value === null).length;
  return (
    <Card
      title="Live values the triggers were graded against"
      subtitle="Carried unchanged from the collectors. A missing value is a trigger that could not be evaluated this run, not a pass."
      padded={false}
      actions={
        unmeasured ? (
          <Badge variant="warn" dot>
            {unmeasured} of {rows.length} not measured
          </Badge>
        ) : null
      }
    >
      <Table<LiveRow> columns={columns} rows={rows} rowKey={(r) => r.key} stickyHeader={false} emptyText="No live metrics in this snapshot" />
    </Card>
  );
}
