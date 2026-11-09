import { FanChart } from "@/components/charts";
import { Card } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { fmtInt, fmtNum, fmtUsdCompact } from "@/lib/format";
import { COLORS, SERIES_COLORS, withAlpha } from "@/lib/theme";
import type { FanChart as FanChartData, SotpValuation } from "@/lib/types";
import { mult } from "./fmt";

function hasSeries(fan: FanChartData | null | undefined, prefix: "fdv" | "rev"): boolean {
  if (!fan) return false;
  return (["p10", "p25", "p50", "p75", "p90"] as const).every((k) => Array.isArray(fan[`${prefix}_${k}`]) && fan[`${prefix}_${k}`].length > 0);
}

function Legend({ color, reference }: { color: string; reference?: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="inline-block h-2.5 w-4 rounded-sm" style={{ background: withAlpha(color, 0.14) }} />
        P10 to P90
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="inline-block h-2.5 w-4 rounded-sm" style={{ background: withAlpha(color, 0.32) }} />
        P25 to P75
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span aria-hidden className="inline-block h-0.5 w-4" style={{ background: COLORS.ink }} />
        Median
      </span>
      {reference ? (
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden className="inline-block w-4 border-t border-dashed" style={{ borderColor: COLORS.amber }} />
          Current FDV
        </span>
      ) : null}
    </div>
  );
}

/** Two percentile fans from `sotp.fan_chart`: running implied FDV and cumulative holder revenue by month. */
export function McFanCharts({ sotp }: { sotp: SotpValuation }) {
  const fan = sotp.fan_chart;
  const fdvOk = hasSeries(fan, "fdv");
  const revOk = hasSeries(fan, "rev");
  const months = fan?.months && fdvOk && fan.months.length === fan.fdv_p50.length ? fan.months : undefined;
  const cal = sotp.calibration;
  const H = sotp.horizon_months;
  const fdvColor = SERIES_COLORS[0];
  const revColor = SERIES_COLORS[2];
  const hasRef = Number.isFinite(sotp.current_fdv_usd);

  return (
    <Card
      title={`How the distribution widens over ${fmtInt(H)} months`}
      subtitle={`Percentiles across ${fmtInt(sotp.n_paths)} seeded paths, taken month by month; no single path traces the median line. Dispersion comes from measured volatility: price σ ${fmtNum(cal?.sigma_price_annual, { decimals: 2 })} a year, volume σ ${fmtNum(cal?.sigma_volume_monthly, { decimals: 2 })} a month.`}
    >
      <div className="grid grid-cols-1 gap-x-10 gap-y-8 xl:grid-cols-2">
        <figure className="min-w-0">
          <figcaption className="mb-2 space-y-1.5">
            <h3 className="text-[14px] font-medium text-ink">Running implied FDV</h3>
            <Legend color={fdvColor} reference={hasRef} />
          </figcaption>
          {fdvOk ? (
            <FanChart
              title="Running implied FDV, P10 to P90 by month"
              description="running FDV at month t = terminal multiple x 12 x month-t holder revenue run-rate (public + haircut x confidential + L1 gas burn)"
              p10={fan.fdv_p10}
              p25={fan.fdv_p25}
              p50={fan.fdv_p50}
              p75={fan.fdv_p75}
              p90={fan.fdv_p90}
              months={months}
              yFormat={fmtUsdCompact}
              color={fdvColor}
              includeZero
              reference={hasRef ? { y: sotp.current_fdv_usd, label: `Current FDV ${fmtUsdCompact(sotp.current_fdv_usd)}` } : null}
              margin={{ right: 92, left: 60 }}
              width={560}
              height={300}
            />
          ) : (
            <p className="text-[13.5px] text-muted">Not available: the FDV fan series are absent from this snapshot.</p>
          )}
          <p className="mt-2 text-[12.5px] leading-snug text-muted">The FDV an investor would pay at each month&apos;s revenue run-rate, at the {mult(cal?.terminal_multiple_used)} terminal multiple.</p>
        </figure>
        <figure className="min-w-0">
          <figcaption className="mb-2 space-y-1.5">
            <h3 className="text-[14px] font-medium text-ink">Cumulative holder revenue</h3>
            <Legend color={revColor} />
          </figcaption>
          {revOk ? (
            <FanChart
              title="Cumulative holder revenue, P10 to P90 by month"
              description="sum over months of gross fees x buyback share, USD, undiscounted"
              p10={fan.rev_p10}
              p25={fan.rev_p25}
              p50={fan.rev_p50}
              p75={fan.rev_p75}
              p90={fan.rev_p90}
              months={fan.months && fan.months.length === fan.rev_p50.length ? fan.months : undefined}
              yFormat={fmtUsdCompact}
              includeZero
              color={revColor}
              margin={{ right: 92, left: 60 }}
              width={560}
              height={300}
            />
          ) : (
            <p className="text-[13.5px] text-muted">Not available: the revenue fan series are absent from this snapshot.</p>
          )}
          <p className="mt-2 text-[12.5px] leading-snug text-muted">Fees directed to buybacks, undiscounted. Month 0 reproduces the measured DefiLlama holder revenue.</p>
        </figure>
      </div>
      <MethodNote className="mt-6">
        <p>
          Running FDV<sub>t</sub> = M × 12 × (public holder revenue<sub>t</sub> + h × confidential holder revenue<sub>t</sub> + L1 gas burn<sub>t</sub>), with M = {mult(cal?.terminal_multiple_used)} and h the confidential multiple haircut. Cumulative holder revenue = Σ (V<sub>pub</sub> × τ<sub>pub</sub> + V<sub>conf</sub> × τ<sub>conf</sub>) × days × α.
        </p>
        <p>
          Mean-matching (Itô) GBM: the deterministic path is the expected path and the median path sits below it. Fields: <code>sotp.fan_chart.fdv_p10</code> … <code>fdv_p90</code>, <code>sotp.fan_chart.rev_p10</code> … <code>rev_p90</code>, <code>sotp.calibration.sigma_price_annual</code>, <code>sotp.calibration.sigma_volume_monthly</code>, <code>sotp.calibration.gbm_convention</code>.
        </p>
      </MethodNote>
    </Card>
  );
}
