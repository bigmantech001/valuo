import { Badge, Stat } from "@/components/ui";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { fmtInt, fmtNearCompact, fmtNum, fmtPct, fmtPctPoints, fmtUsd, fmtUsdCompact } from "@/lib/format";
import type { SotpValuation } from "@/lib/types";
import { REF } from "./refs";
import { mult } from "./fmt";

export interface VerdictStripProps {
  sotp: SotpValuation;
  totalSupplyNear: number | null;
}

function finite(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

/** Tab opening: the Monte Carlo result stated as a sentence, then the four figures that frame it. */
export function VerdictStrip({ sotp, totalSupplyNear }: VerdictStripProps) {
  const fdv = sotp.fdv_percentiles;
  const cal = sotp.calibration;
  const current = finite(sotp.current_fdv_usd);
  const upside = finite(sotp.upside_p50_pct);
  // Mean-matching GBM: deterministic_base is the EXPECTED path; the P50 sits below it (sotp.calibration.gbm_convention).
  const detFdv = finite(cal?.deterministic_base?.fdv_total);
  const mcMean = finite(cal?.mc_mean_fdv);
  const p10 = finite(fdv?.p10);
  const p50 = finite(fdv?.p50);
  const p90 = finite(fdv?.p90);
  const volMean = finite(cal?.volume_terminal_mean_usd_day);
  const volMedian = finite(cal?.volume_terminal_median_usd_day);
  const volRatio = finite(cal?.volume_mean_to_median_horizon) ?? (volMean !== null && volMedian ? volMean / volMedian : null);
  const sigmaVol = finite(cal?.sigma_volume_monthly);
  const sigmaVolN = finite(cal?.sigma_volume_monthly_n_obs);
  const H = sotp.horizon_months;
  const rawMult = finite(cal?.terminal_multiple_raw);
  const usedMult = finite(cal?.terminal_multiple_used);
  const clipped = cal?.terminal_multiple_clipped === true;
  const discountSource = sotp.inputs?.discount_rate?.source;

  const p90VsCurrent = p90 !== null && current ? p90 / current - 1 : null;
  const headline =
    p50 !== null && upside !== null && current !== null ? (
      <>
        The median Monte Carlo path values NEAR at {fmtUsdCompact(p50)}, {fmtPctPoints(Math.abs(upside), { decimals: 1 })} {upside >= 0 ? "above" : "below"} its current {fmtUsdCompact(current)} FDV
      </>
    ) : (
      <>Monte Carlo valuation of NEAR from modelled holder revenue</>
    );

  return (
    <div className="space-y-8">
      <SectionIntro eyebrow={`Sum-of-the-parts valuation, ${fmtInt(sotp.n_paths)} seeded paths over ${fmtInt(H)} months`} title={headline}>
        <p>
          The P10 to P90 range is {fmtUsdCompact(p10)} to {fmtUsdCompact(p90)}
          {p90VsCurrent !== null && p90VsCurrent < 0 ? `; even the 90th-percentile path sits ${fmtPct(Math.abs(p90VsCurrent), { decimals: 0 })} below today's market value` : p90VsCurrent !== null ? `; the 90th-percentile path sits ${fmtPct(p90VsCurrent, { decimals: 0 })} above today's market value` : ""}
          . The median falls below the expected path ({fmtUsdCompact(detFdv)}) because volume shocks are lognormal
          {volRatio !== null ? `: by month ${fmtInt(H)} mean daily volume is ${fmtNum(volRatio, { decimals: 1 })}× the median` : ""}. Engines 2 and 3 rest on assumptions rather than measured fee series, so their contribution is the least reliable part of the total.
        </p>
      </SectionIntro>

      <StatGrid cols={4}>
        <Stat
          label="Median FDV vs current"
          value={upside}
          format={(v) => fmtPctPoints(v, { signed: true })}
          tone={upside === null ? "neutral" : upside >= 0 ? "emerald" : "crimson"}
          hint={`P50 ${fmtUsdCompact(p50)} against ${fmtUsdCompact(current)} today`}
          provenance={REF.blockFinal}
        />
        <Stat label="Expected-path FDV" value={detFdv} format={fmtUsdCompact} hint={`Deterministic mean path; Monte Carlo mean ${fmtUsdCompact(mcMean)}`} />
        <Stat
          label={
            <span className="inline-flex flex-wrap items-center gap-2">
              Terminal multiple
              {clipped ? (
                <Badge variant="warn" dot>
                  Clipped
                </Badge>
              ) : null}
            </span>
          }
          value={usedMult}
          format={(v) => mult(v)}
          hint={clipped ? `Raw peer median ${mult(rawMult)} FDV / revenue, capped` : `Peer median FDV / revenue, inside the guardrails`}
          provenance={REF.coingeckoMarkets}
        />
        <Stat
          label={
            <span className="inline-flex flex-wrap items-center gap-2">
              Discount rate
              {discountSource === "assumption" ? <Badge variant="assumption">Assumption</Badge> : null}
            </span>
          }
          value={sotp.discount_rate}
          format={(v) => fmtPct(v, { decimals: 0 })}
          hint={`Annual, applied to ${fmtInt(H)} months of cash flow and the terminal value`}
        />
      </StatGrid>

      <MethodNote>
        <p>
          FDV per path = E1 + E2 + E3, each the present value of {fmtInt(H)} months of modelled flow plus a terminal value at the horizon, discounted at {fmtPct(sotp.discount_rate, { decimals: 0 })}. Seed {fmtInt(sotp.seed)}, {fmtInt(sotp.n_paths)} paths; GBM shocks on public volume, confidential volume and price; take rates follow a deterministic path because no measured dispersion exists.
        </p>
        <p>
          Current FDV {fmtUsdCompact(current)} = spot {fmtUsd(cal?.price_usd)} × on-chain total supply {fmtNearCompact(totalSupplyNear)} at the snapshot block. Median vs expected: P50 {fmtUsdCompact(p50)}
          {p50 !== null && detFdv ? ` is ${fmtPct(p50 / detFdv, { decimals: 1 })} of the expected path` : ""}. Public volume at M{fmtInt(H)}: mean {fmtUsdCompact(volMean)} per day vs median {fmtUsdCompact(volMedian)} per day
          {sigmaVol !== null ? ` (monthly σ ${fmtNum(sigmaVol, { decimals: 3 })}${sigmaVolN !== null ? `, n = ${fmtInt(sigmaVolN)}` : ""})` : ""}; the median path sits below the mean by exp(−σ²t / 2).
        </p>
        <p>
          Fields: <code>sotp.fdv_percentiles</code>, <code>sotp.upside_p50_pct</code>, <code>sotp.current_fdv_usd</code>, <code>sotp.calibration.deterministic_base.fdv_total</code>, <code>sotp.calibration.mc_mean_fdv</code>, <code>sotp.calibration.volume_terminal_mean_usd_day</code>, <code>sotp.calibration.volume_terminal_median_usd_day</code>, <code>sotp.calibration.terminal_multiple_raw</code> / <code>_used</code> / <code>_clipped</code>, <code>sotp.inputs.discount_rate</code>.
        </p>
      </MethodNote>
    </div>
  );
}
