import { Heatmap } from "@/components/charts";
import { Card } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { fmtBps, fmtInt, fmtPct, fmtUsdCompact } from "@/lib/format";
import type { PortCheck, SotpSnapshotSlice } from "@/lib/quantClient";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import { REGIME_NAME } from "./fmt";
import { liveOperatingPoint, nearestHeatmapCell } from "./sliderModel";

export interface SensitivityGridProps {
  slice: SotpSnapshotSlice;
  portCheck: PortCheck;
}

/** 5 x 5 deterministic FDV over daily volume x blended net take; emerald border where the glidepath float turns deflationary. */
export function SensitivityGrid({ slice, portCheck }: SensitivityGridProps) {
  const hm = slice.sotp?.sensitivity_heatmap;
  if (!hm || !Array.isArray(hm.x) || !hm.x.length || !Array.isArray(hm.y) || !hm.y.length || !Array.isArray(hm.fdv_p50)) {
    return (
      <Card title="Sensitivity to volume and take rate">
        <p className="text-[13.5px] text-muted">Not available: the sensitivity grid is absent or empty in this snapshot.</p>
      </Card>
    );
  }
  const op = liveOperatingPoint(slice);
  const hl = nearestHeatmapCell(hm, op.daily_volume_usd, op.net_take_bps);
  const deflCells = (hm.net_deflation ?? []).flat().filter(Boolean).length;
  const total = hm.x.length * hm.y.length;
  const regimeName = REGIME_NAME[hm.regime ?? "svrn_glidepath"] ?? hm.regime;
  const cal = slice.sotp.calibration;
  const opValue = hl ? hm.fdv_p50[hl[0]]?.[hl[1]] : null;
  const current = cal?.current_fdv_usd;
  const reachesCurrent = typeof current === "number" && hm.fdv_p50.flat().some((v) => Number.isFinite(v) && v >= current);

  return (
    <Card
      title="Sensitivity to volume and take rate"
      subtitle={`FDV with daily volume and net take held flat for ${fmtInt(slice.sotp.horizon_months)} months. ${fmtInt(deflCells)} of ${fmtInt(total)} cells turn net supply deflationary under the ${regimeName}.`}
    >
      <div className="grid grid-cols-1 gap-x-10 gap-y-6 xl:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
        <div className="min-w-0 overflow-x-auto">
          <Heatmap
            title="FDV by daily volume and net take rate"
            description="rows: net take in bps; columns: daily intents volume in USD; emerald border where the net float change turns non-positive within the horizon; ink border marks the live operating point"
            x={hm.x}
            y={hm.y}
            values={hm.fdv_p50}
            flags={hm.net_deflation}
            cellFormat={fmtUsdCompact}
            xFormat={(v) => (typeof v === "number" ? `${fmtUsdCompact(v)}/day` : String(v))}
            yFormat={(v) => (typeof v === "number" ? fmtBps(v, { signed: false, decimals: 0 }) : String(v))}
            xLabel="Daily intents volume, held flat"
            yLabel="Net take rate"
            flagLabel="Net supply deflationary"
            colorLow={COLORS.surface2}
            colorHigh={SERIES_COLORS[2]}
            highlight={hl}
            height={340}
            className="min-w-[30rem]"
          />
        </div>
        <dl className="space-y-4 text-[13.5px] leading-relaxed">
          <div>
            <dt className="text-muted">Live operating point (ink border)</dt>
            <dd className="tnum text-ink">
              {fmtUsdCompact(op.daily_volume_usd)} a day at {fmtBps(op.net_take_bps, { signed: false, decimals: 2 })} net
              {hl ? (
                <span className="block text-[12.5px] text-muted">
                  Nearest cell {fmtUsdCompact(hm.x[hl[1]])}/day × {fmtBps(hm.y[hl[0]], { signed: false, decimals: 0 })}: {fmtUsdCompact(opValue)}
                </span>
              ) : null}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Net take</dt>
            <dd className="tnum text-ink">
              Gross {fmtBps(cal?.blended_gross_take_bps, { signed: false, decimals: 2 })} × buyback share {fmtPct(cal?.alpha_capture, { decimals: 1 })}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Against today&apos;s {fmtUsdCompact(current)} FDV</dt>
            <dd className="text-ink">{reachesCurrent ? "At least one cell in the grid reaches the current market value." : "No cell in the grid reaches the current market value."}</dd>
          </div>
          {portCheck.heatmap_flag_mismatches > 0 ? (
            <div>
              <dt className="text-amber">Stale flags</dt>
              <dd className="text-muted">{fmtInt(portCheck.heatmap_flag_mismatches)} stored deflation flag(s) disagree with the browser recomputation; the FDV values agree. Re-run make reproduce to refresh them.</dd>
            </div>
          ) : null}
        </dl>
      </div>
      <MethodNote className="mt-6">
        <p>
          Each cell runs the deterministic model with volume and net take constant for the horizon: buyback share folded into the net take, zero growth, zero compression, zero price drift, {regimeName} issuance. Confidential share {fmtPct(hm.confidential_share_used, { decimals: 1 })} of each column. Basis: {hm.basis}. The snapshot key is named <code>fdv_p50</code>, but the cells are deterministic, not Monte Carlo medians.
        </p>
        <p>
          Browser recomputation: {Number.isFinite(portCheck.heatmap_max_rel_error) ? `${fmtInt(portCheck.heatmap_cells)} of ${fmtInt(total)} cells reproduced, max relative error ${portCheck.heatmap_max_rel_error.toExponential(1)}` : "could not recompute the grid"}. Fields: <code>sotp.sensitivity_heatmap</code> (<code>x</code>, <code>y</code>, <code>fdv_p50</code>, <code>net_deflation</code>, <code>confidential_share_used</code>), operating point from <code>sotp.calibration.v_pub_30d_usd</code> + <code>v_conf_30d_usd</code> and <code>net_take_start_bps</code>.
        </p>
      </MethodNote>
    </Card>
  );
}
