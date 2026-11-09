import { LineChart } from "@/components/charts";
import { Badge, Stat } from "@/components/ui";
import { StatGrid } from "@/components/ui/Section";
import { fmtBps, fmtCompact, fmtMonth, fmtNear, fmtNearCompact, fmtNum, fmtPct, fmtUsd, fmtUsdCompact } from "@/lib/format";
import type { SotpInputs, SotpResult } from "@/lib/quantClient";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import type { DeterministicBase, RegimeKey, SotpCalibration } from "@/lib/types";
import { REGIME_NAME } from "./fmt";

export interface DeterministicReadoutProps {
  result: SotpResult;
  inputs: SotpInputs;
  base: DeterministicBase | null | undefined;
  cal: SotpCalibration;
  regime: RegimeKey;
  windowDays: number;
}

const pctS = (v: number) => fmtPct(v, { decimals: 1, signed: true });
const bps2 = (v: number) => fmtBps(v, { signed: false, decimals: 2 });

/** Live outputs for the current slider state: FDV and price up top, the engine split, then the supply and take paths. */
export function DeterministicReadout({ result: r, inputs, base, cal, regime, windowDays }: DeterministicReadoutProps) {
  const H = r.horizon_months;
  const current = cal.current_fdv_usd;
  const vsBaseRaw = base && base.fdv_total > 0 ? r.fdv_total / base.fdv_total - 1 : null;
  // Snap floating-point residuals (the TS port differs from the Python base by ~1e-16) to an exact zero.
  const vsBase = vsBaseRaw !== null && Math.abs(vsBaseRaw) < 1e-9 ? 0 : vsBaseRaw;
  const vsCurrent = current > 0 ? r.fdv_total / current - 1 : null;
  const vsSpot = cal.price_usd > 0 ? r.implied_price / cal.price_usd - 1 : null;
  const coverage = r.cum_issuance_near > 0 ? 1 - r.net_float_change_cum_near / r.cum_issuance_near : null;
  const vPub = inputs.v_pub_usd_day ?? 0;
  const vConf = inputs.v_conf_usd_day ?? 0;
  const month0Fees = ((vPub * inputs.tau_pub_bps + vConf * inputs.tau_conf_bps) / 1e4) * windowDays;
  const feeGap = cal.gross_fees_30d_usd > 0 ? month0Fees / cal.gross_fees_30d_usd - 1 : null;
  const months = Array.from({ length: H }, (_, i) => i + 1);
  const regimeName = REGIME_NAME[regime] ?? regime;

  const engines = [
    { key: "e1", name: "Engine 1, public clearinghouse", value: r.engine_clearinghouse, assumption: false, color: SERIES_COLORS[0], note: `PV ${fmtUsdCompact(r.pv_public)}, terminal ${fmtUsdCompact(r.tv_public)}` },
    { key: "e2", name: "Engine 2, confidential flow", value: r.engine_confidential, assumption: true, color: SERIES_COLORS[1], note: `PV ${fmtUsdCompact(r.pv_confidential)}, terminal ${fmtUsdCompact(r.tv_confidential)}, ${fmtNum(inputs.conf_haircut, { decimals: 2 })} multiple haircut` },
    { key: "e3", name: "Engine 3, monetary premium", value: r.engine_monetary, assumption: true, color: SERIES_COLORS[2], note: `Gas burn PV ${fmtUsdCompact(r.pv_gas_burn)}, state-lock demand ${fmtUsdCompact(r.pv_state_lock)}; not a cash flow` },
  ];

  return (
    <div className="flex flex-col gap-6">
      <StatGrid cols={3}>
        <Stat
          label="FDV under these inputs"
          value={r.fdv_total}
          format={fmtUsdCompact}
          size="lg"
          delta={vsBase === null ? undefined : vsBase === 0 ? { value: "Equal to", label: "the snapshot run" } : { value: pctS(vsBase), label: "vs the snapshot run", tone: "neutral" }}
        />
        <Stat
          label={`Implied price at month ${H}`}
          value={r.implied_price}
          format={(v) => fmtUsd(v, { decimals: 3 })}
          size="lg"
          delta={vsSpot === null ? undefined : { value: pctS(vsSpot), label: `vs spot ${fmtUsd(cal.price_usd)}`, tone: vsSpot >= 0 ? "emerald" : "crimson" }}
        />
        <Stat
          label="Vs current FDV"
          value={vsCurrent}
          format={pctS}
          size="lg"
          tone={vsCurrent === null ? "neutral" : vsCurrent >= 0 ? "emerald" : "crimson"}
          hint={`Current FDV ${fmtUsdCompact(current)}`}
        />
      </StatGrid>

      <div>
        <h3 className="mb-2 text-[13.5px] font-medium text-ink">Contribution by engine</h3>
        <ul className="divide-y divide-border border-y border-border">
          {engines.map((e) => {
            const share = r.fdv_total > 0 ? e.value / r.fdv_total : null;
            return (
              <li key={e.key} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 py-2.5 sm:grid-cols-[minmax(0,19rem)_minmax(0,1fr)_auto]">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13.5px] text-ink">
                    <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: e.color }} />
                    {e.name}
                    {e.assumption ? <Badge variant="assumption">Assumption</Badge> : null}
                  </div>
                  <div className="tnum mt-0.5 text-[12px] leading-snug text-dim">{e.note}</div>
                </div>
                <div className="order-last col-span-2 h-1.5 overflow-hidden rounded-full bg-surface-2 sm:order-none sm:col-span-1" aria-hidden>
                  <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(1, share ?? 0)) * 100}%`, background: e.color }} />
                </div>
                <div className="tnum text-right text-[13.5px] text-ink">
                  {fmtUsdCompact(e.value)}
                  <span className="ml-2 inline-block w-12 text-muted">{share === null ? "n/a" : fmtPct(share, { decimals: 0 })}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <StatGrid cols={4}>
        <Stat
          size="sm"
          label="Supply crossover"
          value={
            <span className="inline-flex flex-wrap items-center gap-2">
              <Badge variant={r.net_deflation ? "ok" : "warn"} dot>
                {r.net_deflation ? "Crosses" : "No crossover"}
              </Badge>
              {r.net_deflation ? <span className="tnum text-[15px]">{fmtMonth(r.crossover_month)}</span> : null}
            </span>
          }
          hint={`${regimeName}; snapshot run: ${fmtMonth(base?.crossover_month ?? null)}`}
        />
        <Stat size="sm" label={`Sinks as a share of issuance`} value={coverage} format={(v) => fmtPct(v, { decimals: 1 })} hint={`Net float ${fmtNearCompact(r.net_float_change_cum_near, { signed: true })} over ${H} months`} />
        <Stat size="sm" label={`Holder revenue, ${H} months`} value={r.cum_holder_revenue_usd} format={fmtUsdCompact} hint={`Snapshot run ${fmtUsdCompact(base?.cum_holder_revenue_usd)}`} />
        <Stat
          size="sm"
          label={`Month-0 fees vs measured`}
          value={feeGap}
          format={pctS}
          tone={feeGap !== null && Math.abs(feeGap) > 0.005 ? "amber" : "neutral"}
          hint={`${fmtUsdCompact(month0Fees)} vs ${fmtUsdCompact(cal.gross_fees_30d_usd)} over ${windowDays} days`}
        />
      </StatGrid>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <figure className="min-w-0">
          <figcaption className="mb-1 text-[13px] text-ink">
            Net change in float per month, NEAR
            <span className="block text-[12px] text-dim">Issuance less buybacks, gas burn and state lock; {regimeName}</span>
          </figcaption>
          <LineChart
            title={`Net float change per month under ${regimeName}`}
            description="issuance minus buyback minus gas burn minus state lock, NEAR per month; a value at or below zero is the crossover"
            series={[{ name: "Net float change", values: r.monthly_net_float_change_near, color: r.net_deflation ? COLORS.emerald : COLORS.crimson, area: true }]}
            x={months}
            xFormat={(m) => `M${Math.round(m)}`}
            yFormat={(v) => fmtCompact(v, { signed: true })}
            markers={r.crossover_month ? [{ x: r.crossover_month, label: `Crossover M${r.crossover_month}`, color: COLORS.emerald }] : []}
            zeroLine
            legend={false}
            width={340}
            height={230}
            margin={{ left: 58, right: 8 }}
            pointLimit={0}
          />
        </figure>
        <figure className="min-w-0">
          <figcaption className="mb-1 text-[13px] text-ink">
            Take rate paths, bps
            <span className="tnum block text-[12px] text-dim">
              Public {bps2(inputs.tau_pub_bps)} to {bps2(r.monthly_tau_pub_bps[H - 1])}; confidential {bps2(inputs.tau_conf_bps)} to {bps2(r.monthly_tau_conf_bps[H - 1])}
            </span>
          </figcaption>
          <LineChart
            title="Public and confidential take-rate paths"
            description="tau_t = floor + (tau_0 - floor) x (1 - lambda)^t"
            series={[
              { name: "Public", values: r.monthly_tau_pub_bps, color: SERIES_COLORS[0] },
              { name: "Confidential", values: r.monthly_tau_conf_bps, color: SERIES_COLORS[1] },
              { name: "Floor", values: months.map(() => inputs.tau_floor_bps), color: COLORS.dim, dashed: true },
            ]}
            x={months}
            xFormat={(m) => `M${Math.round(m)}`}
            yFormat={(v) => fmtNum(v, { decimals: 0 })}
            width={340}
            height={230}
            margin={{ left: 58, right: 8 }}
            pointLimit={0}
          />
        </figure>
      </div>
      <p className="tnum text-[12px] leading-snug text-dim">
        Supply at month {H}: {fmtNearCompact(r.supply_at_horizon_used)} used for the price ({regimeName}); the model&apos;s internal float is {fmtNearCompact(r.supply_at_horizon_internal)}. Cumulative issuance {fmtNearCompact(r.cum_issuance_near)}, buybacks {fmtNearCompact(r.cum_buyback_near)}, net {fmtNear(r.net_float_change_cum_near, { signed: true })}.
      </p>
    </div>
  );
}
