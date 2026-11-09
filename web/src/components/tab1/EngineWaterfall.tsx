import { Waterfall, type WaterfallStep } from "@/components/charts";
import { MethodNote } from "@/components/ui/Section";
import { Badge, Table, type Column } from "@/components/ui";
import { cn } from "@/lib/cn";
import { fmtUsdCompact, NA } from "@/lib/format";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import type { EngineValue, Snapshot } from "@/lib/types";
import { isNum, percentiles, ratio } from "./derive";
import { Panel, SubHead } from "./parts";

interface EngineRow {
  engine: EngineValue;
  deterministic: number | null;
}

/** Categorical colours: engines are not good or bad, so no sign colours. */
const ENGINE_COLOR: Record<string, string> = { clearinghouse: SERIES_COLORS[0], confidential: SERIES_COLORS[1], monetary: SERIES_COLORS[2] };

const ENGINE_NAME: Record<string, string> = { clearinghouse: "Clearinghouse", confidential: "Confidential execution", monetary: "Monetary premium" };

function engineName(key: string): string {
  return ENGINE_NAME[key] ?? key;
}

/**
 * The three engine P50s stacked as a waterfall, with the total FDV P50 drawn as a reference line.
 * The two differ by construction (a percentile of a per-path sum is not the sum of per-engine
 * percentiles), and the lede says so with this snapshot's numbers.
 */
export function EngineWaterfall({ snapshot, className }: { snapshot: Snapshot; className?: string }) {
  const sotp = snapshot.sotp;
  const engines = sotp?.engines ?? [];
  const fdv = percentiles(sotp?.fdv_percentiles);
  const det = sotp?.calibration?.deterministic_base ?? null;
  const currentFdv = isNum(sotp?.current_fdv_usd) ? sotp.current_fdv_usd : null;
  const mcMean = isNum(sotp?.calibration?.mc_mean_fdv) ? sotp.calibration.mc_mean_fdv : null;

  const steps: WaterfallStep[] = engines
    .filter((e) => isNum(e.p50))
    .map((e) => ({ label: engineName(e.key), value: e.p50, color: ENGINE_COLOR[e.key] ?? COLORS.dim, sublabel: e.assumption_heavy ? "Assumption-heavy" : "Measured inputs" }));
  const sumP50 = steps.length ? steps.reduce((s, x) => s + x.value, 0) : null;
  const totalP50 = fdv?.p50 ?? null;
  const sumToTotal = ratio(sumP50, totalP50);

  const rows: EngineRow[] = engines.map((e) => {
    const dKey = `engine_${e.key}` as keyof NonNullable<typeof det>;
    const d = det ? det[dKey] : null;
    return { engine: e, deterministic: isNum(d) ? d : null };
  });

  const columns: Column<EngineRow>[] = [
    {
      key: "engine",
      header: "Engine",
      render: (r) => (
        <div>
          <span className="inline-flex items-center gap-2 whitespace-nowrap text-ink">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: ENGINE_COLOR[r.engine.key] ?? COLORS.dim }} aria-hidden />
            {engineName(r.engine.key)}
          </span>
          {r.engine.assumption_heavy ? (
            <div className="mt-1 pl-[18px]">
              <Badge variant="assumption">Assumption-heavy</Badge>
            </div>
          ) : (
            <div className="mt-0.5 pl-[18px] text-[12.5px] text-dim">Measured inputs</div>
          )}
        </div>
      ),
    },
    { key: "p10", header: "P10", numeric: true, render: (r) => <span className="tnum text-muted">{fmtUsdCompact(r.engine.p10)}</span> },
    { key: "p50", header: "P50", numeric: true, headerClassName: "text-ink", render: (r) => <span className="tnum font-semibold text-ink">{fmtUsdCompact(r.engine.p50)}</span> },
    { key: "p90", header: "P90", numeric: true, render: (r) => <span className="tnum text-muted">{fmtUsdCompact(r.engine.p90)}</span> },
    { key: "det", header: "Expected path", numeric: true, render: (r) => <span className="tnum text-ink">{fmtUsdCompact(r.deterministic)}</span> },
  ];

  const lede =
    isNum(sumP50) && isNum(totalP50)
      ? `The engine medians sum to ${fmtUsdCompact(sumP50)}, ${isNum(sumToTotal) ? `${sumToTotal.toFixed(2)}×` : NA} the ${fmtUsdCompact(totalP50)} median of the path totals. Percentiles do not add: each path is valued as a whole and the median is taken over those totals.`
      : "Engine percentiles are missing from this snapshot.";

  return (
    <section id="engines" className={cn("space-y-4", className)}>
      <SubHead title="Three valuation engines">{lede}</SubHead>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)]">
        <Panel className="px-4 pb-2 pt-4">
          {steps.length ? (
            <Waterfall
              title="Engine medians stacked"
              description="Each engine's Monte Carlo median stacked on the running total; the dashed line is the median of the per-path FDV total."
              steps={steps}
              total={{ label: "Sum of medians", color: COLORS.ink }}
              reference={isNum(totalP50) ? { y: totalP50, label: `Path-total median ${fmtUsdCompact(totalP50)}`, color: COLORS.muted } : null}
              valueFormat={(v) => (v === 0 ? "$0" : fmtUsdCompact(v))}
              height={260}
              margin={{ left: 60, right: 12 }}
            />
          ) : (
            <p className="py-3 text-[14px] text-muted">No engine percentiles in this snapshot.</p>
          )}
        </Panel>
        <div className="space-y-4">
          <Panel className="px-2 py-1">
            <Table<EngineRow> columns={columns} rows={rows} rowKey={(r) => r.engine.key} emptyText="No engines in this snapshot" dense={false} />
          </Panel>
          <p className="text-[13px] leading-relaxed text-muted">
            The expected path is additive by construction: {fmtUsdCompact(det?.fdv_total ?? null)} in total. The Monte Carlo mean is {fmtUsdCompact(mcMean)} against a current FDV of {fmtUsdCompact(currentFdv)}
            {isNum(mcMean) && isNum(totalP50) ? (mcMean > totalP50 ? "; the mean sits above the median because the paths are right-skewed, so quote percentiles, not the mean." : "; the mean is at or below the median.") : "."}
          </p>
        </div>
      </div>
      <MethodNote>
        <p>
          {engines.length ? engines.map((e) => e.label).join("; ") : "No engine labels in this snapshot"}.
        </p>
        <p>
          Fields: <code>sotp.engines[].p10</code>, <code>.p50</code>, <code>.p90</code>; total <code>sotp.fdv_percentiles.p50</code>; expected path <code>sotp.calibration.deterministic_base.engine_&lt;key&gt;</code> and <code>fdv_total</code> (deterministic_sotp() at the median inputs); mean <code>sotp.calibration.mc_mean_fdv</code>.
        </p>
      </MethodNote>
    </section>
  );
}
