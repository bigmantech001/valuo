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

function plural(n: number, one: string): string {
  return `${fmtInt(n)} ${n === 1 ? one : `${one}s`}`;
}

/** "breached 0.7 of 30" / "clear" / "not measured", with the daily records in the streak and whether a gap reset it. */
export function StreakCell({ t, ruleDays: days }: { t: TriggerHistory; ruleDays: number | null }) {
  const state = t.state_now ?? (t.breached_now === true ? "breached" : t.breached_now === false ? "clear" : "unmeasured");
  if (state === "clear") return <span className="text-muted">clear</span>;
  if (state === "unmeasured")
    return (
      <span className="text-dim" title="A record where the trigger was not evaluated ends a streak">
        not measured
      </span>
    );
  const s = t.breached_streak_days;
  if (s === null || s === undefined) return <span className="text-dim">{NA}</span>;
  const falsified = t.falsified ?? (days !== null && s >= days);
  return (
    <div className="flex flex-col items-end gap-0.5">
      <span className={falsified ? "font-medium text-crimson" : "text-ink"}>
        {falsified ? "falsified: " : "breached "}
        {fmtNum(s, { decimals: 1 })}
        {days !== null ? <span className="text-muted"> of {fmtInt(days)}</span> : null}
      </span>
      {typeof t.observed_days === "number" ? (
        <span className="whitespace-nowrap text-[12px] text-muted">
          {plural(t.observed_days, "daily record")}
          {t.gap_reset_at_utc ? "; restarted after a data gap" : ""}
        </span>
      ) : null}
    </div>
  );
}

export function TriggerHistoryTable({ triggers, titles, account }: { triggers: Record<string, TriggerHistory>; titles: Record<string, string>; account?: string }) {
  const rows: Row[] = Object.entries(triggers).map(([key, t]) => ({ key, title: titles[key] ?? humanizeKey(key), t, ruleDays: ruleDays(t.falsification_rule) }));
  const rule = rows.find((r) => r.t.falsification_rule)?.t.falsification_rule ?? null;
  const nBreachedNow = rows.filter((r) => r.t.breached_now === true).length;
  const gapH = rows.find((r) => typeof r.t.streak_max_gap_h === "number")?.t.streak_max_gap_h ?? 36;
  const days = rows.find((r) => r.ruleDays !== null)?.ruleDays ?? 30;

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
      header: "Consecutive days breached",
      numeric: true,
      title: "Elapsed days from the first to the latest daily record of the current unbroken breach, against the falsification rule",
      render: (r) => <StreakCell t={r.t} ruleDays={r.ruleDays} />,
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
          ? `Rule as recorded in the summary: ${rule}. A streak runs from the first daily record of the current unbroken breach to the latest one, so a breach seen once reads 0.0 days. Daily records more than ${fmtInt(gapH)} h apart break it, as does a day the trigger was not measured.`
          : "The summary carries no falsification rule."
      }
      footer={
        account ? (
          <>
            On the day a streak reaches {fmtInt(days)} days the daily job writes <code>valuo/falsification/&lt;trigger&gt;</code> to NEAR mainnet SocialDB under{" "}
            <a href={`https://nearblocks.io/address/${account}`} target="_blank" rel="noreferrer" title={account} className="text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent">
              {account.length > 20 ? `${account.slice(0, 8)}…${account.slice(-4)}` : account}
            </a>{" "}
            (<code>make falsification-list ANCHOR=&lt;account&gt;</code> reads it back without a key).
          </>
        ) : undefined
      }
      padded={false}
      bodyClassName="px-2 pb-2"
    >
      <Table columns={columns} rows={rows} rowKey={(r) => r.key} emptyText="no bear triggers in artifacts/history/summary.json" />
    </Card>
  );
}
