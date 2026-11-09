import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Table, type Column } from "@/components/ui/Table";
import { comparatorRule, fmtMetricValue, humanizeKey, metricLabel } from "@/components/tab5/bearData";
import { fmtInt, fmtNum, fmtUtc, NA } from "@/lib/format";
import type { TriggerHistory } from "@/lib/history";
import type { TriggerComparator } from "@/lib/types";
import { COLORS } from "@/lib/theme";

interface Row {
  key: string;
  title: string;
  t: TriggerHistory;
  ruleDays: number | null;
}

/** "thesis falsified if a trigger holds for 30 consecutive days" -> 30 (read from the summary, not assumed). */
export function ruleDays(rule: string | null | undefined): number | null {
  const m = rule?.match(/(\d+(?:\.\d+)?)\s+consecutive\s+days?/i);
  return m ? Number(m[1]) : null;
}

/** Last values of a trigger as a row of dots: filled crimson = breached, ring = clear, grey = not graded. */
function BreachStrip({ points }: { points: TriggerHistory["points"] }) {
  const shown = points.slice(-60);
  const step = 7;
  const w = Math.max(step, shown.length * step);
  return (
    <svg viewBox={`0 0 ${w} 10`} width={w} height={10} className="inline-block align-middle" aria-hidden>
      {shown.map(([t, , b], i) => (
        <circle
          key={`${t}${i}`}
          cx={i * step + 3.5}
          cy={5}
          r={2.6}
          fill={b === true ? COLORS.crimson : b === false ? COLORS.surface : COLORS.borderStrong}
          stroke={b === true ? COLORS.crimson : b === false ? COLORS.muted : COLORS.borderStrong}
          strokeWidth={1}
        />
      ))}
    </svg>
  );
}

export function TriggerHistoryTable({ triggers, titles }: { triggers: Record<string, TriggerHistory>; titles: Record<string, string> }) {
  const rows: Row[] = Object.entries(triggers).map(([key, t]) => ({ key, title: titles[key] ?? humanizeKey(key), t, ruleDays: ruleDays(t.falsification_rule) }));
  const rule = rows.find((r) => r.t.falsification_rule)?.t.falsification_rule ?? null;
  const nBreachedNow = rows.filter((r) => r.t.breached_now === true).length;

  const columns: Column<Row>[] = [
    {
      key: "trigger",
      header: "Trigger",
      render: (r) => (
        <div className="min-w-0">
          <div className="text-ink">{r.title}</div>
          <div className="text-[12.5px] text-dim">
            {metricLabel(r.t.metric)} {comparatorRule(r.t.comparator as TriggerComparator | null, fmtMetricValue(r.t.metric, r.t.threshold))}
          </div>
        </div>
      ),
    },
    {
      key: "latest",
      header: "Latest value",
      numeric: true,
      render: (r) => {
        const last = r.t.points[r.t.points.length - 1];
        return last ? fmtMetricValue(r.t.metric, last[1]) : <span className="text-dim">{NA}</span>;
      },
    },
    {
      key: "status",
      header: "Status now",
      render: (r) =>
        r.t.breached_now === true ? (
          <Badge variant="warn" dot>
            Breached
          </Badge>
        ) : r.t.breached_now === false ? (
          <Badge variant="ok" dot>
            Not breached
          </Badge>
        ) : (
          <Badge variant="neutral" dot title="The metric was unmeasured or its interval straddled the threshold in the latest run">
            Not graded
          </Badge>
        ),
    },
    {
      key: "since",
      header: "Breached since",
      render: (r) => (r.t.breached_since_utc ? <span className="tnum">{fmtUtc(r.t.breached_since_utc)}</span> : <span className="text-dim">not in a breach run</span>),
    },
    {
      key: "streak",
      header: "Breach streak, days",
      numeric: true,
      render: (r) => {
        const s = r.t.breached_streak_days;
        if (s === null || s === undefined) return <span className="text-dim">{NA}</span>;
        const falsified = r.ruleDays !== null && s >= r.ruleDays;
        return (
          <span className={falsified ? "text-crimson" : "text-ink"}>
            {fmtNum(s, { decimals: 1 })}
            {r.ruleDays !== null ? <span className="text-muted"> of {fmtInt(r.ruleDays)}</span> : null}
          </span>
        );
      },
    },
    {
      key: "runs",
      header: "Runs breached",
      numeric: true,
      render: (r) => (
        <span>
          {fmtInt(r.t.n_breached)} / {fmtInt(r.t.n_runs)}
        </span>
      ),
    },
    {
      key: "strip",
      header: "Run by run",
      title: "One dot per canonical run, oldest left (last 60 shown). Filled = breached, ring = not breached, grey = not graded.",
      render: (r) => <BreachStrip points={r.t.points} />,
    },
  ];

  return (
    <Card
      kicker="Daily canonical snapshot · bear-case triggers"
      title={
        rows.length
          ? `${fmtInt(nBreachedNow)} of ${fmtInt(rows.length)} falsification triggers breached in the latest run`
          : "No trigger history recorded"
      }
      subtitle={
        rule
          ? `Rule as recorded in the summary: ${rule}. A streak runs from the first run of the current unbroken breach to the latest run, so a breach seen in a single run reads 0.0 days.`
          : "The summary carries no falsification rule."
      }
      padded={false}
      bodyClassName="px-2 pb-2"
    >
      <Table columns={columns} rows={rows} rowKey={(r) => r.key} emptyText="no bear triggers in artifacts/history/summary.json" />
    </Card>
  );
}
