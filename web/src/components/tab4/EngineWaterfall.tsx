import { Waterfall } from "@/components/charts";
import { Badge, Card, Table, type Column } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { fmtPct, fmtUsdCompact } from "@/lib/format";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import type { EngineKey, EngineValue, SotpValuation } from "@/lib/types";

const ENGINE_COLOR: Record<EngineKey, string> = { clearinghouse: SERIES_COLORS[0], confidential: SERIES_COLORS[1], monetary: SERIES_COLORS[2] };
const ENGINE_SHORT: Record<EngineKey, string> = { clearinghouse: "Engine 1", confidential: "Engine 2", monetary: "Engine 3" };
const ENGINE_NAME: Record<EngineKey, string> = { clearinghouse: "Public clearinghouse", confidential: "Confidential flow", monetary: "Monetary premium" };

function finite(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** Expected-path engine waterfall (additive) plus the per-engine Monte Carlo percentile table. */
export function EngineWaterfall({ sotp }: { sotp: SotpValuation }) {
  const engines = sotp.engines ?? [];
  const base = sotp.calibration?.deterministic_base;
  const median = sotp.calibration?.engine_shares_on_median_total_path;
  const totalP50 = sotp.fdv_percentiles?.p50;
  if (!engines.length) {
    return (
      <Card title="Value by engine">
        <p className="text-[13.5px] text-muted">Not available: the engine breakdown is empty in this snapshot.</p>
      </Card>
    );
  }
  const sumP50 = engines.reduce((s, e) => s + (Number.isFinite(e.p50) ? e.p50 : 0), 0);
  const baseValue: Record<EngineKey, number | null> = {
    clearinghouse: finite(base?.engine_clearinghouse),
    confidential: finite(base?.engine_confidential),
    monetary: finite(base?.engine_monetary),
  };
  const baseOk = Object.values(baseValue).every((v) => v !== null);
  const steps = engines.map((e) => ({ label: `${ENGINE_SHORT[e.key] ?? e.key}`, value: baseOk ? (baseValue[e.key] as number) : e.p50, color: ENGINE_COLOR[e.key] ?? COLORS.muted }));
  const baseTotal = finite(base?.fdv_total);
  const heavy = engines.filter((e) => e.assumption_heavy);
  const heavyShare = baseOk && baseTotal ? heavy.reduce((s, e) => s + (baseValue[e.key] ?? 0), 0) / baseTotal : null;

  const topMedian = median
    ? engines
        .map((e) => ({ key: e.key, heavy: e.assumption_heavy, share: median[`${e.key}_share` as const] as number | undefined }))
        .filter((e): e is { key: EngineKey; heavy: boolean; share: number } => typeof e.share === "number" && Number.isFinite(e.share))
        .sort((a, b) => b.share - a.share)[0] ?? null
    : null;

  const columns: Column<EngineValue>[] = [
    {
      key: "engine",
      header: "Engine",
      render: (e) => (
        <div className="min-w-[15rem]">
          <div className="flex items-center gap-2 whitespace-nowrap text-ink">
            <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: ENGINE_COLOR[e.key] ?? COLORS.muted }} />
            {ENGINE_SHORT[e.key] ?? e.key}, {(ENGINE_NAME[e.key] ?? e.label).toLowerCase()}
            {e.assumption_heavy ? <Badge variant="assumption">Assumption</Badge> : null}
          </div>
        </div>
      ),
    },
    { key: "p10", header: "P10", numeric: true, render: (e) => fmtUsdCompact(e.p10) },
    { key: "p50", header: "P50", numeric: true, render: (e) => <span className="font-medium text-ink">{fmtUsdCompact(e.p50)}</span> },
    { key: "p90", header: "P90", numeric: true, render: (e) => fmtUsdCompact(e.p90) },
    { key: "base", header: "Expected path", numeric: true, render: (e) => fmtUsdCompact(baseValue[e.key]) },
    { key: "share", header: "Median-path share", numeric: true, render: (e) => fmtPct(median ? (median[`${e.key}_share` as const] as number | undefined) : null, { decimals: 1 }) },
  ];

  return (
    <Card
      title="Value by engine"
      subtitle={
        heavyShare !== null && heavy.length > 0
          ? `On the expected path, ${heavy.length === 1 ? "the assumption-heavy engine carries" : `the ${heavy.length} assumption-heavy engines carry`} ${fmtPct(heavyShare, { decimals: 0 })} of the ${fmtUsdCompact(baseTotal)} total.`
          : "Each engine's contribution and its spread across paths."
      }
      footer={
        topMedian ? (
          <span>
            On the single path closest to the total median, {ENGINE_SHORT[topMedian.key]} ({(ENGINE_NAME[topMedian.key] ?? "").toLowerCase()}) carries {fmtPct(topMedian.share, { decimals: 0 })} of the value
            {topMedian.heavy ? ", so the median outcome rests mostly on assumed inputs." : "."}
          </span>
        ) : null
      }
    >
      <div className="grid grid-cols-1 gap-x-10 gap-y-6 xl:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
        <figure className="min-w-0">
          <figcaption className="mb-1 text-[13px] text-ink">{baseOk ? "Expected path, engines add to the total" : "Engine medians (not additive)"}</figcaption>
          <Waterfall
            title={baseOk ? "Expected-path FDV by engine" : "Engine P50 values"}
            description="Engine 1 public clearinghouse, Engine 2 confidential flow, Engine 3 monetary premium"
            steps={steps}
            total={{ label: baseOk ? "Expected FDV" : "Sum of P50s" }}
            valueFormat={fmtUsdCompact}
            width={420}
            height={300}
          />
        </figure>
        <div className="min-w-0">
          <Table<EngineValue> columns={columns} rows={engines} rowKey={(e) => e.key} />
          <p className="mt-3 text-[12.5px] leading-snug text-muted">
            Engine percentiles are taken engine by engine and do not add: the three P50s sum to {fmtUsdCompact(sumP50)} against a total P50 of {fmtUsdCompact(totalP50)}. The last column decomposes the single path closest to the total median.
          </p>
        </div>
      </div>
      <MethodNote className="mt-6">
        {engines.map((e) => (
          <p key={e.key}>
            <span className="text-ink">{ENGINE_SHORT[e.key]}:</span> {e.method}
          </p>
        ))}
        <p>
          Engine 2 is marked as an assumption because the confidential TVL is unverified at the source and no confidential fee series exists; Engine 3 values a demand flow (newly state-locked NEAR × price) that is not a cash flow. Engine 1 inherits the clipped peer multiple.
        </p>
        <p>
          Fields: <code>sotp.engines</code>, <code>sotp.calibration.deterministic_base</code>, <code>sotp.calibration.engine_shares_on_median_total_path</code>
          {median ? ` (path ${median.path_index})` : ""}, <code>sotp.fdv_percentiles.p50</code>.
        </p>
      </MethodNote>
    </Card>
  );
}
