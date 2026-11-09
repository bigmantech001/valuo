import type { Assumption, BearCase } from "@/lib/types";
import { Badge, Card, Table, type BadgeVariant, type Column } from "@/components/ui";
import { fmtAssumptionBound, fmtAssumptionValue, stressParamLabel } from "./bearData";

const SOURCE_VARIANT: Record<Assumption["source"], BadgeVariant> = {
  assumption: "assumption",
  derived: "derived",
  measured: "verified-api",
};

const SOURCE_LABEL: Record<Assumption["source"], string> = {
  assumption: "Assumption",
  derived: "Derived",
  measured: "Measured",
};

const columns: Column<Assumption>[] = [
  { key: "key", header: "Parameter", width: "26%", render: (a) => <span className="text-ink" title={`${a.key} (${a.unit})`}>{stressParamLabel(a.key)}</span> },
  { key: "value", header: "Value", numeric: true, render: (a) => <span className="tnum whitespace-nowrap text-ink">{fmtAssumptionValue(a)}</span> },
  {
    key: "range",
    header: "Plausible range",
    numeric: true,
    title: "Low and high bounds declared with the assumption",
    render: (a) => (
      <span className="tnum whitespace-nowrap text-muted">
        {fmtAssumptionBound(a, a.low)} to {fmtAssumptionBound(a, a.high)}
      </span>
    ),
  },
  {
    key: "source",
    header: "Basis",
    render: (a) => (
      <Badge variant={SOURCE_VARIANT[a.source] ?? "neutral"} dot>
        {SOURCE_LABEL[a.source] ?? a.source}
      </Badge>
    ),
  },
  { key: "justification", header: "Why this value", render: (a) => <span className="block max-w-[34rem] text-[13px] leading-snug text-muted">{a.justification}</span> },
];

/**
 * Stress parameter register: the labeled assumptions the scenarios are built from. They are
 * falsification-test definitions (how hard each scenario pushes), not measurements, and carry
 * `source: assumption` in the snapshot for exactly that reason.
 */
export function StressParameters({ bear }: { bear: BearCase }) {
  const rows = bear.stress_parameters ?? [];
  const nAssumed = rows.filter((r) => r.source === "assumption").length;
  const allAssumed = rows.length > 0 && nAssumed === rows.length;
  return (
    <Card
      title="Stress parameter register"
      subtitle={`How hard each scenario pushes. ${allAssumed ? "Every severity is an assumption with a declared range and a one-line justification; none is presented as measured." : `${nAssumed} of ${rows.length} severities are assumptions; each row is tagged with its basis.`}`}
      padded={false}
    >
      <Table<Assumption> columns={columns} rows={rows} rowKey={(a) => a.key} stickyHeader={false} emptyText="No stress parameters in this snapshot" />
    </Card>
  );
}
