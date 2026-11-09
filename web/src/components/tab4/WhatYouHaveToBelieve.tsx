import { niceTicks } from "@/components/charts/util";
import { fmtUnit, upperFirst } from "@/components/tab1/marketImplied";
import { joinAnd } from "@/components/tab1/derive";
import { Panel, SubHead } from "@/components/tab1/parts";
import { MethodNote } from "@/components/ui/Section";
import { fmtInt, fmtPct, fmtUsdCompact, NA } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { Sensitivity, SensitivityRow } from "@/lib/types";

/** Two neutral greys: the bar half reached with the input at its low end, and at its high end. */
const LOW_FILL = "#C9C3B5";
const HIGH_FILL = "#6E6A60";

/** Lower-case the first letter unless the word is an acronym ("NEAR price drift" stays). */
function lcFirst(s: string): string {
  return s.length > 1 && s[1] === s[1].toLowerCase() ? s.charAt(0).toLowerCase() + s.slice(1) : s;
}

function fin(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function Tornado({ rows, base, market }: { rows: SensitivityRow[]; base: number; market: number | null }) {
  const vals = rows.flatMap((r) => [r.fdv_low, r.fdv_high]).filter(fin);
  const hi = Math.max(base, ...(fin(market) ? [market] : []), ...vals) * 1.03;
  const ticks = niceTicks([0, hi], 6);
  const domainHi = Math.max(hi, ticks[ticks.length - 1] ?? hi);
  const pct = (v: number) => `${(Math.max(0, Math.min(domainHi, v)) / domainHi) * 100}%`;
  const grid = "grid grid-cols-[minmax(0,20rem)_minmax(0,1fr)_9.5rem] items-center gap-x-5";
  const marketNearEnd = fin(market) && market / domainHi > 0.85;
  return (
    <div role="img" aria-label="Deterministic FDV with each input at its low and high end, all others at base, sorted by swing">
      {/* reference-line labels */}
      <div className={grid}>
        <div />
        <div className="relative h-6 text-[12px] text-ink">
          <span className="tnum absolute bottom-1 -translate-x-1/2 whitespace-nowrap" style={{ left: pct(base) }}>
            Model base {fmtUsdCompact(base)}
          </span>
          {fin(market) ? (
            <span className={cn("tnum absolute bottom-1 whitespace-nowrap", marketNearEnd ? "-translate-x-full pr-1" : "-translate-x-1/2")} style={{ left: pct(market) }}>
              Market FDV {fmtUsdCompact(market)}
            </span>
          ) : null}
        </div>
        <div />
      </div>
      <div className="relative">
        {rows.map((r) => {
          const segs: Array<{ key: string; from: number; to: number; fill: string }> = [
            { key: "lo", from: Math.min(base, r.fdv_low), to: Math.max(base, r.fdv_low), fill: LOW_FILL },
            { key: "hi", from: Math.min(base, r.fdv_high), to: Math.max(base, r.fdv_high), fill: HIGH_FILL },
          ];
          const lo = Math.min(r.fdv_low, r.fdv_high);
          const hiV = Math.max(r.fdv_low, r.fdv_high);
          return (
            <div
              key={r.param}
              className={cn(grid, "border-t border-border py-1.5 first:border-t-0")}
              title={`${r.label}: ${fmtUnit(r.low, r.unit)} gives ${fmtUsdCompact(r.fdv_low)}, ${fmtUnit(r.high, r.unit)} gives ${fmtUsdCompact(r.fdv_high)} (base ${fmtUnit(r.base, r.unit)}); ${r.range_basis}`}
            >
              <div className="min-w-0">
                <div className="truncate text-[13px] text-ink">{r.label}</div>
                <div className="truncate text-[12px] text-dim">
                  {fmtUnit(r.low, r.unit)} to {fmtUnit(r.high, r.unit)}, base {fmtUnit(r.base, r.unit)} · {r.source}
                </div>
              </div>
              <div className="relative h-7">
                {ticks.map((t) => (
                  <span key={t} aria-hidden className="absolute inset-y-0 border-l border-border/70" style={{ left: pct(t) }} />
                ))}
                {segs.map((sg) => (
                  <span key={sg.key} aria-hidden className="absolute top-1/2 h-3.5 -translate-y-1/2" style={{ left: pct(sg.from), width: `calc(${pct(sg.to)} - ${pct(sg.from)})`, background: sg.fill }} />
                ))}
                <span aria-hidden className="absolute -inset-y-1.5 border-l border-ink" style={{ left: pct(base) }} />
                {fin(market) ? <span aria-hidden className="absolute -inset-y-1.5 border-l border-dashed border-ink" style={{ left: pct(market) }} /> : null}
              </div>
              <div className="text-right">
                <div className="tnum text-[13px] text-ink">
                  {fmtUsdCompact(lo)} to {fmtUsdCompact(hiV)}
                </div>
                <div className="tnum text-[12px] text-dim">{fin(r.variance_share) ? `${fmtPct(r.variance_share, { decimals: 1 })} of variance` : NA}</div>
              </div>
            </div>
          );
        })}
      </div>
      {/* axis */}
      <div className={cn(grid, "border-t border-border-strong pt-1.5")}>
        <div className="text-[12px] text-dim">Input range, source</div>
        <div className="relative h-5 text-[12px] text-dim">
          {ticks.map((t) => (
            <span key={t} className="tnum absolute -translate-x-1/2 whitespace-nowrap" style={{ left: pct(t) }}>
              {fmtUsdCompact(t, { decimals: t >= 1e9 ? 1 : 0 })}
            </span>
          ))}
        </div>
        <div className="text-right text-[12px] text-dim">FDV range, share</div>
      </div>
    </div>
  );
}

/**
 * "What you have to believe": a tornado of the deterministic expected-path FDV with each input at
 * the low and high end of its registry (or measured) range, all others at base, sorted by swing.
 * Bars are neutral greys; the market FDV is a dashed reference line. Reads `sensitivity`.
 */
export function WhatYouHaveToBelieve({ sensitivity }: { sensitivity: Sensitivity | null | undefined }) {
  if (!sensitivity) return null;
  const rows = [...(sensitivity.rows ?? [])].filter((r) => fin(r.fdv_low) && fin(r.fdv_high)).sort((a, b) => b.swing_usd - a.swing_usd);
  const base = sensitivity.base_fdv_usd;
  const market = fin(sensitivity.current_fdv_usd) ? sensitivity.current_fdv_usd : null;
  if (!rows.length || !fin(base)) {
    return (
      <section className="space-y-4">
        <SubHead title="What you have to believe">The one-at-a-time sensitivity is missing from this snapshot.</SubHead>
      </section>
    );
  }

  const top3 = rows.slice(0, 3).map((r) => lcFirst(r.label));
  const lede: string[] = [];
  if (fin(sensitivity.top3_share))
    lede.push(`${upperFirst(joinAnd(top3))} carry ${fmtPct(sensitivity.top3_share, { decimals: 0 })} of the swing-squared variance proxy.`);
  const widest = rows[0];
  lede.push(`${upperFirst(lcFirst(widest.label))} alone moves FDV from ${fmtUsdCompact(Math.min(widest.fdv_low, widest.fdv_high))} to ${fmtUsdCompact(Math.max(widest.fdv_low, widest.fdv_high))} across its range.`);
  if (market !== null) {
    const n = fin(sensitivity.n_rows_reaching_market_fdv) ? sensitivity.n_rows_reaching_market_fdv : rows.filter((r) => Math.max(r.fdv_low, r.fdv_high) >= market).length;
    lede.push(`${fmtInt(n)} of ${fmtInt(rows.length)} single-input ranges reach the ${fmtUsdCompact(market)} market FDV.`);
  }

  return (
    <section id="what-you-have-to-believe" className="space-y-4">
      <SubHead title="What you have to believe">{lede.join(" ")}</SubHead>
      <Panel className="px-5 py-4">
        <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-[12.5px] text-muted">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-4" style={{ background: LOW_FILL }} aria-hidden />
            Input at its low end
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-4" style={{ background: HIGH_FILL }} aria-hidden />
            Input at its high end
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-3 w-0 border-l border-ink" aria-hidden />
            Model base
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-3 w-0 border-l border-dashed border-ink" aria-hidden />
            Market FDV
          </span>
        </div>
        <div className="valuo-scroll overflow-x-auto">
          <div className="min-w-[56rem]">
            <Tornado rows={rows} base={base} market={market} />
          </div>
        </div>
      </Panel>
      <MethodNote>
        <p>
          Basis: {sensitivity.basis}. Variance proxy: {sensitivity.variance_proxy ?? "swing² / Σ swing²"}. Fields: <code>sensitivity.rows[]</code> (<code>low</code>, <code>high</code>, <code>fdv_low</code>, <code>fdv_high</code>, <code>swing_usd</code>, <code>variance_share</code>), <code>sensitivity.base_fdv_usd</code>,{" "}
          <code>sensitivity.current_fdv_usd</code>, <code>sensitivity.top3_share</code>.
        </p>
        <ul className="list-disc space-y-1 pl-5">
          {rows.map((r) => (
            <li key={r.param}>
              <code>{r.param}</code> ({r.source}): {r.range_basis}.
            </li>
          ))}
        </ul>
        {sensitivity.excluded?.length ? (
          <p>
            Not shown:{" "}
            {sensitivity.excluded.map((e, i) => (
              <span key={e.param}>
                {i ? "; " : ""}
                <code>{e.param}</code> ({e.reason})
              </span>
            ))}
            .
          </p>
        ) : null}
        {sensitivity.notes?.map((n) => (
          <p key={n}>{n}</p>
        ))}
      </MethodNote>
    </section>
  );
}
