import { Badge, Card, Table, type Column } from "@/components/ui";
import { fmtBlock, fmtInt, fmtNum, fmtUtc, NA } from "@/lib/format";
import { FALSIFICATION_PATH, loadFalsificationRecords, loadHistory, type FalsificationRead, type TriggerHistory } from "@/lib/history";
import type { BearCase, TriggerComparator } from "@/lib/types";
import { comparatorRule, fmtMetricValue, humanizeKey, metricLabel } from "./bearData";

/**
 * The 30-consecutive-day falsification rule, live: per trigger streak from artifacts/history/summary.json
 * (quant/valuo/history.py, daily records, 36 h gap rule) and the on-chain records the daily job writes to
 * <account>/valuo/falsification/<trigger> (quant/valuo/anchor.py falsification), read back from SocialDB.
 * Async server components; each loader is cached in-process.
 */

const NS = FALSIFICATION_PATH.join("/");

function shortAccount(a: string): string {
  return a.length > 20 ? `${a.slice(0, 8)}…${a.slice(-4)}` : a;
}

function AccountLink({ account }: { account: string }) {
  return (
    <a href={`https://nearblocks.io/address/${account}`} target="_blank" rel="noreferrer" title={account} className="text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent">
      {shortAccount(account)}
    </a>
  );
}

function titlesOf(bear: BearCase): Map<string, string> {
  return new Map((bear.scenarios ?? []).map((s) => [s.key, s.title]));
}

/** Rendered only when at least one falsification record exists on-chain: the thesis has failed its own test. */
export async function FalsificationAlert({ bear }: { bear: BearCase }) {
  const read = await loadFalsificationRecords();
  if (!read.records.length) return null;
  const titles = titlesOf(bear);
  return (
    <section role="alert" className="rounded-lg border-2 border-crimson bg-surface px-5 py-4">
      <div className="text-[12px] font-medium uppercase tracking-wide text-crimson">Recorded on NEAR mainnet</div>
      <h2 className="mt-1 font-serif text-[22px] font-medium leading-tight text-ink">Thesis falsified: {read.records.map((r) => titles.get(r.key) ?? humanizeKey(r.key)).join("; ")}</h2>
      <ul className="mt-3 space-y-2 text-[13.5px] leading-relaxed text-ink">
        {read.records.map((r) => {
          const v = r.value;
          return (
            <li key={r.key} className="tnum">
              <code>{`${shortAccount(read.account)}/${NS}/${r.key}`}</code>, written at block {fmtBlock(r.write_block_height)}:{" "}
              {v ? (
                <>
                  {metricLabel(v.metric ?? null)} {comparatorRule((v.comparator ?? null) as TriggerComparator | null, fmtMetricValue(v.metric ?? null, v.threshold ?? null))} held for {fmtNum(v.streak_days, { decimals: 1 })} days from{" "}
                  {fmtUtc(v.breached_since_utc)}; last value {fmtMetricValue(v.metric ?? null, v.last_value ?? null)}, snapshot <code>{(v.snapshot_sha256 ?? "").slice(0, 16)}…</code>.
                </>
              ) : (
                <span className="text-muted">value is not valid JSON: {r.raw ?? "empty"}</span>
              )}
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[12.5px] text-muted">
        Read live from <code>social.near</code> at {fmtUtc(read.checked_at_utc)}. Re-check without a key: <code>make falsification-list ANCHOR={read.account}</code>.
      </p>
    </section>
  );
}

interface Row {
  key: string;
  title: string;
  t: TriggerHistory;
  onchain: boolean;
}

function streakText(t: TriggerHistory, days: number): { text: string; tone: "crimson" | "ink" | "muted" | "dim" } {
  const state = t.state_now ?? (t.breached_now === true ? "breached" : t.breached_now === false ? "clear" : "unmeasured");
  if (state === "clear") return { text: "clear", tone: "muted" };
  if (state === "unmeasured") return { text: "not measured in the latest daily record", tone: "dim" };
  const s = t.breached_streak_days ?? 0;
  if (t.falsified) return { text: `falsified: breached ${fmtNum(s, { decimals: 1 })} of ${fmtInt(days)} consecutive days`, tone: "crimson" };
  return { text: `breached ${fmtNum(s, { decimals: 1 })} of ${fmtInt(days)} consecutive days`, tone: "ink" };
}

const TONE_CLASS = { crimson: "font-medium text-crimson", ink: "text-ink", muted: "text-muted", dim: "text-dim" } as const;

function readLine(read: FalsificationRead): string {
  if (read.error) return `The live SocialDB read failed (${read.error}); whether a record exists is unknown, not assumed absent.`;
  if (!read.records.length) return `Live read at ${fmtUtc(read.checked_at_utc)}: no record under ${NS}/* yet.`;
  return `Live read at ${fmtUtc(read.checked_at_utc)}: ${fmtInt(read.records.length)} record${read.records.length === 1 ? "" : "s"} on-chain (shown above).`;
}

/** Per-trigger progress against the 30-day rule, and who writes the on-chain record when one completes. */
export async function FalsificationWatch({ bear }: { bear: BearCase }) {
  const [history, read] = await Promise.all([loadHistory(), loadFalsificationRecords()]);
  const triggers = history.summary?.snapshots.bear_triggers ?? {};
  const titles = titlesOf(bear);
  const onchain = new Set(read.records.map((r) => r.key));
  const rows: Row[] = Object.entries(triggers).map(([key, t]) => ({ key, title: titles.get(key) ?? humanizeKey(key), t, onchain: onchain.has(key) }));
  const days = rows.find((r) => typeof r.t.falsification_days === "number")?.t.falsification_days ?? 30;
  const gapH = rows.find((r) => typeof r.t.streak_max_gap_h === "number")?.t.streak_max_gap_h ?? 36;
  const longest = rows.reduce<Row | null>((best, r) => ((r.t.breached_streak_days ?? -1) > (best?.t.breached_streak_days ?? -1) ? r : best), null);
  const nFalsified = rows.filter((r) => r.t.falsified).length;

  const title = !rows.length
    ? "No daily trigger history recorded yet"
    : nFalsified
      ? `${fmtInt(nFalsified)} trigger${nFalsified === 1 ? " has" : "s have"} held for ${fmtInt(days)} consecutive days`
      : longest && typeof longest.t.breached_streak_days === "number"
        ? `No trigger has held for ${fmtInt(days)} consecutive days; the longest current streak is ${fmtNum(longest.t.breached_streak_days, { decimals: 1 })} days`
        : "No trigger is in a breach streak";

  const columns: Column<Row>[] = [
    {
      key: "trigger",
      header: "Trigger",
      render: (r) => (
        <div>
          <div className="text-ink">{r.title}</div>
          <div className="text-[12.5px] text-dim">
            {metricLabel(r.t.metric)} {comparatorRule(r.t.comparator as TriggerComparator | null, fmtMetricValue(r.t.metric, r.t.threshold))}
          </div>
        </div>
      ),
    },
    {
      key: "streak",
      header: "Streak",
      render: (r) => {
        const s = streakText(r.t, days);
        return (
          <div>
            <div className={TONE_CLASS[s.tone]}>{s.text}</div>
            {r.t.breached_since_utc ? (
              <div className="text-[12.5px] text-muted">
                since {fmtUtc(r.t.breached_since_utc)}
                {typeof r.t.observed_days === "number" ? `, ${fmtInt(r.t.observed_days)} daily record${r.t.observed_days === 1 ? "" : "s"}` : ""}
                {r.t.gap_reset_at_utc ? "; restarted after a gap in the daily records" : ""}
              </div>
            ) : null}
          </div>
        );
      },
    },
    {
      key: "left",
      header: "Days to falsification",
      numeric: true,
      render: (r) => (typeof r.t.days_to_falsification === "number" && r.t.state_now === "breached" ? fmtNum(r.t.days_to_falsification, { decimals: 1 }) : <span className="text-dim">{NA}</span>),
    },
    {
      key: "chain",
      header: "On-chain record",
      render: (r) =>
        r.onchain ? (
          <Badge variant="error" dot>
            written
          </Badge>
        ) : read.error ? (
          <span className="text-[12.5px] text-dim">read failed</span>
        ) : (
          <span className="text-[12.5px] text-muted">none</span>
        ),
    },
  ];

  return (
    <Card
      kicker="Daily canonical snapshot · the 30-day rule"
      title={title}
      subtitle={`A streak counts elapsed days between the first and the latest daily record of an unbroken breach. Records more than ${fmtInt(gapH)} h apart break it (a missed daily run does not count as breached), and so does a day the trigger was not measured.`}
      padded={false}
      bodyClassName="px-2 pb-2"
      footer={
        <>
          On the day a streak reaches {fmtInt(days)} days, the daily job (<code>ops/vps/valuo-run.sh snapshot</code>) writes <code>{NS}/&lt;trigger&gt;</code> to NEAR mainnet SocialDB under <AccountLink account={read.account} />, signed with the
          same key that anchors each snapshot; no one has to act. {readLine(read)}
        </>
      }
    >
      <Table columns={columns} rows={rows} rowKey={(r) => r.key} emptyText="no bear triggers in artifacts/history/summary.json" />
    </Card>
  );
}
