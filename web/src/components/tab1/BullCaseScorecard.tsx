import type { BullCase, BullCondition, BullStatus, Snapshot } from "@/lib/types";
import { fmtBps, fmtInt, fmtPct, fmtUsdCompact } from "@/lib/format";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant } from "@/components/ui/Badge";
import { MethodNote, SectionIntro } from "@/components/ui/Section";

const STATUS: Record<BullStatus, { label: string; variant: BadgeVariant }> = {
  on_track: { label: "On track", variant: "ok" },
  behind: { label: "Behind", variant: "warn" },
  against: { label: "Against", variant: "error" },
  not_measured: { label: "Not measured", variant: "neutral" },
};

/** Required / live values in the condition's own unit. */
function fmtValue(v: number | null, unit: string): string {
  switch (unit) {
    case "ratio_yoy":
      return `${fmtPct(v, { decimals: 0 })} a year`;
    case "ratio":
      return fmtPct(v, { decimals: 1 });
    case "usd_per_year":
      return `${fmtUsdCompact(v)} a year`;
    case "usd_per_day":
      return `${fmtUsdCompact(v)} a day`;
    case "usd":
      return fmtUsdCompact(v, { signed: true });
    case "bps":
      return fmtBps(v, { decimals: 2, signed: true });
    case "x":
      return v === null ? "n/a" : `${fmtInt(v)}×`;
    case "hhi":
      return fmtInt(v);
    default:
      return v === null ? "n/a" : String(v);
  }
}

function fmtRequired(c: BullCondition): string {
  if (c.key === "pricing_power" || c.key === "confidential_growth") return "above 0";
  if (c.key === "solver_competition") return `at most ${fmtValue(c.required, c.unit)}`;
  if (c.key === "issuance_cut") return `${fmtValue(c.required, c.unit)} cap`;
  return fmtValue(c.required, c.unit);
}

function Row({ c }: { c: BullCondition }) {
  const s = STATUS[c.status] ?? STATUS.not_measured;
  return (
    <li className="grid grid-cols-[minmax(0,1fr)] gap-x-8 gap-y-3 border-b border-border py-5 last:border-b-0 lg:grid-cols-[minmax(0,1.5fr)_9rem_9rem_minmax(0,1fr)_7rem] lg:items-baseline">
      <div className="min-w-0">
        <div className="text-[15px] text-ink">{c.statement}</div>
        <p className="mt-1 text-[13px] leading-relaxed text-muted">{c.why}</p>
      </div>
      <div className="flex items-baseline justify-between gap-3 lg:block lg:text-right">
        <span className="text-[12px] text-dim lg:hidden">Required</span>
        <span className="tnum text-[14px] text-muted">{fmtRequired(c)}</span>
      </div>
      <div className="flex items-baseline justify-between gap-3 lg:block lg:text-right">
        <span className="text-[12px] text-dim lg:hidden">Live</span>
        <span className="tnum text-[15px] font-medium text-ink">{fmtValue(c.live, c.unit)}</span>
      </div>
      <div className="flex items-baseline justify-between gap-3 lg:block">
        <span className="text-[12px] text-dim lg:hidden">Trend</span>
        {c.trend ? (
          <span className="text-[13px] text-muted" title={c.trend.source}>
            <span className={cn("tnum", c.trend.direction === "up" ? "text-emerald" : c.trend.direction === "down" ? "text-crimson" : "text-ink")}>
              {fmtPct(c.trend.change, { decimals: 0, signed: true })}
            </span>{" "}
            {c.trend.label}
          </span>
        ) : (
          <span className="text-[13px] text-dim">no series</span>
        )}
      </div>
      <div className="lg:text-right">
        <Badge variant={s.variant}>{s.label}</Badge>
      </div>
    </li>
  );
}

/**
 * The long-term bull case as falsifiable conditions (snapshot.bull_case, quant/valuo/models/bull_case.py).
 * Every requirement, live value and trend is read from the snapshot; nothing is computed here.
 */
export function BullCaseScorecard({ snapshot }: { snapshot: Snapshot }) {
  const bc: BullCase | null | undefined = snapshot.bull_case;
  if (!bc || !bc.conditions?.length) return null;
  const c = bc.counts;
  return (
    <section id="bull-case" className="space-y-6">
      <SectionIntro
        eyebrow="The long-term case, made falsifiable"
        title={
          <>
            {c.on_track} of {bc.n_measured} conditions for NEAR&apos;s long-term case are on track today
          </>
        }
        aside={
          <>
            <Badge variant="ok">{c.on_track} on track</Badge>
            <Badge variant="warn">{c.behind} behind</Badge>
            <Badge variant="error">{c.against} against</Badge>
          </>
        }
      >
        {bc.headline}
      </SectionIntro>

      <div className="rounded-lg border border-border bg-surface px-5">
        <div className="hidden grid-cols-[minmax(0,1.5fr)_9rem_9rem_minmax(0,1fr)_7rem] gap-x-8 border-b border-border-strong py-3 text-[12.5px] text-dim lg:grid">
          <span>Condition</span>
          <span className="text-right">Required</span>
          <span className="text-right">Live</span>
          <span>Trend</span>
          <span className="text-right">Status</span>
        </div>
        <ul>
          {bc.conditions.map((cond) => (
            <Row key={cond.key} c={cond} />
          ))}
        </ul>
      </div>

      <MethodNote>
        <p>{bc.basis}</p>
        <p className="mt-2">
          Requirements for volume growth, holder revenue and the multiple are the reverse-valuation solves (one input moved at a time until the
          model&apos;s expected-path FDV equals the market FDV), so each says what that condition alone must deliver. The deflation requirement is the
          breakeven daily volume under the 1.6% glidepath; solver competition uses the bear-case HHI threshold. Trends compare the last 30 days with
          the 30 days ending 90 days earlier in DefiLlama&apos;s daily series, and confidential TVL with its value 90 days earlier in the NEAR-reported
          history. Fields: <code>bull_case.conditions[]</code>.
        </p>
      </MethodNote>
    </section>
  );
}
