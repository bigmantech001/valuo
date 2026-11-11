import { cn } from "@/lib/cn";
import { fmtTimes } from "./landingData";
import { fmtUsdCompact } from "@/lib/format";

/**
 * Small single-series trend line. Pure SVG, no axes: the row it sits in names the measure, and the
 * caption gives the first and last values so the shape is never the only carrier of the number.
 */
export function Sparkline({
  points,
  caption,
  extra,
  minRange = 0,
  className,
}: {
  points: number[];
  caption: string;
  /** an extra point drawn after the series in the accent colour (a live reading) */
  extra?: number | null;
  /** smallest y-range drawn, in the series' unit, so sub-noise wiggles in a flat series are not stretched into spikes */
  minRange?: number;
  className?: string;
}) {
  const all = extra !== null && extra !== undefined ? [...points, extra] : points;
  if (points.length < 2) return null;
  const W = 240, H = 28, PAD = 3;
  let lo = Math.min(...all), hi = Math.max(...all);
  const floor = Math.max(minRange, 1e-9);
  if (hi - lo < floor) {
    // A (near-)flat series stays flat in the middle instead of being stretched into noise.
    const mid = (hi + lo) / 2;
    lo = mid - floor / 2;
    hi = mid + floor / 2;
  }
  const x = (i: number) => PAD + (i * (W - 2 * PAD)) / Math.max(1, all.length - 1);
  const y = (v: number) => H - PAD - ((v - lo) * (H - 2 * PAD)) / (hi - lo);
  const d = points.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const last = points.length - 1;
  return (
    <figure className={cn("flex items-center gap-3", className)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-7 w-[150px] shrink-0 overflow-visible sm:w-[180px]" role="img" aria-label={caption} preserveAspectRatio="none">
        <title>{caption}</title>
        <path d={d} fill="none" stroke="var(--color-muted)" strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        <circle cx={x(last)} cy={y(points[last])} r={2.5} fill="var(--color-ink)" />
        {extra !== null && extra !== undefined ? (
          <>
            <line x1={x(last)} y1={y(points[last])} x2={x(all.length - 1)} y2={y(extra)} stroke="var(--color-accent)" strokeWidth={1.5} strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
            <circle cx={x(all.length - 1)} cy={y(extra)} r={3.5} fill="var(--color-accent)" stroke="var(--color-surface)" strokeWidth={1.5} />
          </>
        ) : null}
      </svg>
      <figcaption className="min-w-0 text-[12px] leading-snug text-dim">{caption}</figcaption>
    </figure>
  );
}

/** The thesis in one picture: what the market pays against what Intents cash flow supports. */
export function GapBars({ market, supported, mcMedian }: { market: number; supported: number; mcMedian: number | null }) {
  if (!(market > 0) || !(supported >= 0)) return null;
  const top = Math.max(market, supported);
  const pct = (v: number) => `${Math.max(0.6, (v / top) * 100)}%`;
  const gap = supported > 0 ? market / supported : null;
  return (
    <figure className="mt-8 max-w-[38rem]" aria-label="Market FDV against the FDV Intents cash flow supports">
      <div className="space-y-3.5">
        <Bar label="What the market pays (FDV)" value={fmtUsdCompact(market)} width={pct(market)} color="bg-ink" />
        <Bar label="What Intents cash flow supports (model's expected path)" value={fmtUsdCompact(supported)} width={pct(supported)} color="bg-accent" />
      </div>
      <figcaption className="mt-3 text-[13px] leading-snug text-dim">
        Bars to scale{gap !== null ? <>, a <span className="tnum text-ink">{fmtTimes(gap)}</span> gap</> : null}
        {mcMedian !== null ? (
          <>
            . Monte Carlo median of the supported value: <span className="tnum text-ink">{fmtUsdCompact(mcMedian)}</span>
          </>
        ) : null}
        .
      </figcaption>
    </figure>
  );
}

function Bar({ label, value, width, color }: { label: string; value: string; width: string; color: string }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4 text-[13px]">
        <span className="text-muted">{label}</span>
        <span className="tnum font-medium text-ink">{value}</span>
      </div>
      <div className="mt-1.5 h-2.5 w-full rounded-[4px] bg-surface-2">
        <div className={cn("h-full rounded-[4px]", color)} style={{ width }} />
      </div>
    </div>
  );
}

type Status = "on_track" | "behind" | "against" | "not_measured";
const DOT: Record<Status, { cls: string; glyph: string; label: string; rank: number }> = {
  on_track: { cls: "bg-emerald text-surface", glyph: "✓", label: "on track", rank: 0 },
  behind: { cls: "bg-amber text-surface", glyph: "–", label: "behind", rank: 1 },
  against: { cls: "bg-crimson text-surface", glyph: "✕", label: "against", rank: 2 },
  not_measured: { cls: "border border-border-strong bg-surface text-dim", glyph: "?", label: "not measured", rank: 3 },
};

/** One dot per bull-case condition, grouped by status; each glyph repeats the status so colour is never alone. */
export function StatusDots({ conditions, counts }: { conditions: { key: string; statement: string; status: Status }[]; counts: { onTrack: number; behind: number; against: number; measured: number } }) {
  if (!conditions.length) return null;
  const sorted = [...conditions].sort((a, b) => (DOT[a.status]?.rank ?? 9) - (DOT[b.status]?.rank ?? 9));
  return (
    <div className="mt-7">
      <a href="/terminal#thesis" className="group inline-flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50">
        <span className="flex items-center gap-1.5" role="list" aria-label="Bull-case conditions by status">
          {sorted.map((c) => {
            const s = DOT[c.status] ?? DOT.not_measured;
            return (
              <span
                key={c.key}
                role="listitem"
                title={`${s.label[0].toUpperCase()}${s.label.slice(1)}: ${c.statement}`}
                aria-label={`${s.label}: ${c.statement}`}
                className={cn("flex size-5 items-center justify-center rounded-full text-[11px] font-semibold leading-none", s.cls)}
              >
                {s.glyph}
              </span>
            );
          })}
        </span>
        <span className="text-[14px] text-muted group-hover:text-ink">
          <span className="tnum text-ink">{counts.onTrack}</span> of <span className="tnum text-ink">{counts.measured}</span> long-term conditions on track,{" "}
          <span className="tnum text-ink">{counts.behind}</span> behind, <span className="tnum text-ink">{counts.against}</span> against
          <span className="ml-1.5 text-accent">scorecard →</span>
        </span>
      </a>
    </div>
  );
}
