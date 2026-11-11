import { cn } from "@/lib/cn";
import { NA } from "@/lib/format";
import type { BearCase, BearScenario, TriggerComparator } from "@/lib/types";
import { ProvenanceBadge, type ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import { Badge, Card, Table, type Column } from "@/components/ui";
import { FalsificationAlert, FalsificationWatch } from "./FalsificationWatch";
import { comparatorRule, fmtMetricValue, inconclusiveReason, metricLabel, metricProvenance, prose, scenarioStatus, shortUrl, TRIGGER_BADGE, triggerStatus, type TriggerStatus } from "./bearData";

interface TriggerRow {
  id: string;
  scenarioKey: string;
  scenarioTitle: string;
  level: "primary" | "secondary";
  metric: string | null;
  monitorField: string | null;
  comparator: TriggerComparator | null;
  threshold: number | null;
  current: number | null;
  status: TriggerStatus;
  note: string | null;
  /** inconclusive rows: why (sample span against the minimum) */
  reason: string | null;
  /** 90% bootstrap interval of the metric, when the model reports one */
  ci: [number, number] | null;
  monitorSource: string | null;
  provenance: ProvenanceRef[];
}

function rowsFor(s: BearScenario): TriggerRow[] {
  const primary: TriggerRow = {
    id: `${s.key}:primary`,
    scenarioKey: s.key,
    scenarioTitle: s.title,
    level: "primary",
    metric: s.early_warning_metric ?? null,
    monitorField: s.monitor_field ?? null,
    comparator: s.trigger_comparator ?? null,
    threshold: typeof s.trigger_threshold === "number" ? s.trigger_threshold : null,
    current: typeof s.current_value === "number" ? s.current_value : null,
    status: scenarioStatus(s),
    note: s.trigger_note ?? null,
    reason: scenarioStatus(s) === "inconclusive" ? inconclusiveReason(s) : null,
    ci: s.hhi_solver_ci90 ?? null,
    monitorSource: s.monitor_source ?? null,
    provenance: metricProvenance(s.early_warning_metric),
  };
  if (!s.secondary_metric) return [primary];
  const secondary: TriggerRow = {
    id: `${s.key}:secondary`,
    scenarioKey: s.key,
    scenarioTitle: s.title,
    level: "secondary",
    metric: s.secondary_metric,
    monitorField: null,
    comparator: s.secondary_comparator ?? null,
    threshold: typeof s.secondary_threshold === "number" ? s.secondary_threshold : null,
    current: typeof s.secondary_value === "number" ? s.secondary_value : null,
    status: triggerStatus(s.secondary_value, s.secondary_breached, s.secondary_evaluated),
    note: null,
    reason: null,
    ci: null,
    monitorSource: null,
    provenance: metricProvenance(s.secondary_metric),
  };
  return [primary, secondary];
}

/** The model flags a thin sample in the trigger note; surface it next to the status. */
function isThin(note: string | null): boolean {
  return note !== null && /thin sample/i.test(note);
}

function StatusCell({ row }: { row: TriggerRow }) {
  const b = TRIGGER_BADGE[row.status];
  return (
    <div className="flex flex-col items-start gap-1">
      <Badge
        variant={b.variant}
        dot
        title={
          row.status === "unmeasured"
            ? "The live metric was not measured this run; reported as unevaluated, never as clear"
            : row.status === "inconclusive"
              ? "Measured, but on a sample too short to grade; counted as neither breached nor clear"
              : undefined
        }
      >
        {b.label}
      </Badge>
      {row.reason ? <span className="max-w-[11rem] text-[12px] leading-snug text-muted">{row.reason}</span> : null}
      {isThin(row.note) ? (
        <Badge variant="warn" title="The model marks this sample as thin: the grade is a point estimate">
          Thin sample
        </Badge>
      ) : null}
    </div>
  );
}

const columns: Column<TriggerRow>[] = [
  {
    key: "scenario",
    header: "Scenario",
    width: "20%",
    render: (r) =>
      r.level === "primary" ? (
        <div className="text-[13.5px] leading-snug text-ink">{r.scenarioTitle}</div>
      ) : (
        <div className="pl-3 text-[13px] text-muted">Secondary trigger, same scenario</div>
      ),
  },
  {
    key: "metric",
    header: "What we watch",
    width: "34%",
    render: (r) => (
      <div className="max-w-[30rem]">
        <div className="text-[13.5px] text-ink" title={r.metric ?? undefined}>
          {metricLabel(r.metric)}
        </div>
        {r.note ? <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{prose(r.note.charAt(0).toUpperCase() + r.note.slice(1))}.</p> : null}
      </div>
    ),
  },
  {
    key: "current",
    header: "Now",
    numeric: true,
    render: (r) => (
      <div className="flex flex-col items-end gap-0.5">
        <span className={cn("tnum font-medium", r.current === null ? "text-dim" : "text-ink")}>{r.current === null ? "Not measured" : fmtMetricValue(r.metric, r.current)}</span>
        {r.ci && r.current !== null ? (
          <span className="tnum whitespace-nowrap text-[12px] text-muted" title="90% bootstrap interval over the sampled units; within-sample noise only">
            90% CI {fmtMetricValue(r.metric, r.ci[0])} to {fmtMetricValue(r.metric, r.ci[1])}
          </span>
        ) : null}
        {r.provenance[0] ? <ProvenanceBadge source={r.provenance[0].source} name={r.provenance[0].name} /> : null}
      </div>
    ),
  },
  {
    key: "rule",
    header: "Fires when",
    numeric: true,
    render: (r) => <span className="tnum whitespace-nowrap text-ink">{comparatorRule(r.comparator, fmtMetricValue(r.metric, r.threshold))}</span>,
  },
  { key: "status", header: "Status", render: (r) => <StatusCell row={r} /> },
  {
    key: "source",
    header: "Monitor",
    render: (r) =>
      r.monitorSource ? (
        <a href={r.monitorSource} target="_blank" rel="noreferrer" className="break-all text-[12.5px] text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent" title={r.monitorSource}>
          {shortUrl(r.monitorSource)}
        </a>
      ) : (
        <span className="text-[12.5px] text-dim">{r.level === "secondary" ? "Source shown under Now" : NA}</span>
      ),
  },
];

/**
 * Early-warning trigger board: one row per scenario trigger (plus a secondary row where the
 * model defines one), with the live value it was graded against, its source record and the
 * breached / not breached / inconclusive / not measured status. Above it, a banner when a
 * falsification record exists on-chain; below it, each trigger's progress against the 30-day rule.
 */
export function TriggerBoard({ bear }: { bear: BearCase }) {
  const scenarios = bear.scenarios ?? [];
  const rows = scenarios.flatMap(rowsFor);
  const breached = rows.filter((r) => r.status === "breached").length;
  const unmeasured = rows.filter((r) => r.status === "unmeasured").length;
  const inconclusive = rows.filter((r) => r.status === "inconclusive").length;
  return (
    <div className="space-y-6">
      <FalsificationAlert bear={bear} />
      <Card
        title="Early-warning triggers"
        subtitle="Each scenario is paired with a live metric and a threshold. The thesis is treated as falsified if any trigger holds for 30 consecutive days."
        padded={false}
        actions={
          <Badge variant={breached ? "warn" : "ok"} dot>
            {breached} of {rows.length} breached{inconclusive ? `, ${inconclusive} inconclusive` : ""}{unmeasured ? `, ${unmeasured} not measured` : ""}
          </Badge>
        }
      >
        <Table<TriggerRow> columns={columns} rows={rows} rowKey={(r) => r.id} dense={false} stickyHeader={false} emptyText="No scenario triggers in this snapshot" />
      </Card>
      <FalsificationWatch bear={bear} />
    </div>
  );
}
