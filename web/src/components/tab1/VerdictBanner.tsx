import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { Badge, Stat, Table, type Column } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  fmtInt,
  fmtMonth,
  fmtMultiple,
  fmtNear,
  fmtNum,
  fmtPct,
  fmtPctPoints,
  fmtUsd,
  fmtUsdCompact,
  NA,
} from "@/lib/format";
import type { Tone } from "@/lib/theme";
import {
  PERCENTILE_KEYS,
  type PercentileKey,
  type Snapshot,
} from "@/lib/types";
import {
  epochBlockRef,
  isNum,
  joinAnd,
  percentiles,
  ratio,
  regimeEndpoints,
  regimeShortLabel,
  todayDailyVolume,
  toneBySign,
} from "./derive";
import { Panel, SIGN_TEXT, SubHead } from "./parts";

const DEFILLAMA_NET = {
  source: "defillama",
  name: "fees:near-intents:dailyRevenue",
};
const DEFILLAMA_HOLDERS = {
  source: "defillama",
  name: "fees:near-intents:dailyHoldersRevenue",
};
const NEARSTATS_SUMMARY = { source: "nearstats", name: "summary" };

interface PercentileRow {
  key: string;
  label: string;
  note: string | null;
  cells: Record<PercentileKey, string>;
  current: string;
  vsSpot: number | null;
}

interface RegimeRow {
  key: string;
  label: string;
  inflation: string;
  issuance: string;
  deterministic: string;
  cumulative: string;
  pCross: number | null;
  medianMonth: number | null;
  pDeflationary: number | null;
  breakeven: number | null;
  breakevenAtCeiling: number | null;
  multipleOfToday: number | null;
}

/**
 * Opening of the executive summary: the verdict as a sentence built from the snapshot, four key
 * figures, the P10 to P90 valuation table and the supply crossover by issuance regime. Colour marks
 * only the sign of a figure against spot or against breakeven.
 */
export function VerdictBanner({
  snapshot,
  lead = true,
  className,
}: {
  snapshot: Snapshot;
  /** true: opens the tab with the serif headline; false: a sub-section under the market-implied opening */
  lead?: boolean;
  className?: string;
}) {
  const sotp = snapshot.sotp;
  const fees = snapshot.intents_forensics?.fees;
  const supply = snapshot.supply_physics;
  const fdv = percentiles(sotp?.fdv_percentiles);
  const price = percentiles(sotp?.price_percentiles);
  const fdvEx = percentiles(sotp?.fdv_ex_monetary_percentiles);
  const currentFdv = isNum(sotp?.current_fdv_usd) ? sotp.current_fdv_usd : null;
  const currentPrice = isNum(sotp?.calibration?.price_usd)
    ? sotp.calibration.price_usd
    : (snapshot.intents_forensics?.price?.current_usd ?? null);
  const upside = isNum(sotp?.upside_p50_pct) ? sotp.upside_p50_pct : null;
  const today = todayDailyVolume(snapshot);
  const cal = sotp?.calibration;
  const windowText = fees?.take_rate_window ?? null;
  const windowDays = isNum(fees?.take_rate_window_days)
    ? fees.take_rate_window_days
    : null;
  const horizon = isNum(sotp?.horizon_months) ? sotp.horizon_months : null;
  const noneText =
    horizon !== null
      ? `None within ${fmtInt(horizon)} months`
      : "None within horizon";

  // Mean-matching GBM: the deterministic path is the EXPECTED path; the MC median sits below it.
  const detFdv = isNum(cal?.deterministic_base?.fdv_total)
    ? cal.deterministic_base.fdv_total
    : null;
  const mcMean = isNum(cal?.mc_mean_fdv) ? cal.mc_mean_fdv : null;
  const p50OfDet = ratio(fdv?.p50 ?? null, detFdv);
  const volMean = isNum(cal?.volume_terminal_mean_usd_day)
    ? cal.volume_terminal_mean_usd_day
    : null;
  const volMedian = isNum(cal?.volume_terminal_median_usd_day)
    ? cal.volume_terminal_median_usd_day
    : null;
  const sigmaVol = isNum(cal?.sigma_volume_monthly)
    ? cal.sigma_volume_monthly
    : null;
  const sigmaVolN = isNum(cal?.sigma_volume_monthly_n_obs)
    ? cal.sigma_volume_monthly_n_obs
    : null;

  // ------------------------------------------------------------------ headline
  let title: string;
  if (fdv && isNum(currentFdv) && isNum(upside)) {
    const dir = upside >= 0 ? "above" : "below";
    title = `The model's median value for NEAR is ${fmtUsdCompact(fdv.p50)}, ${fmtPctPoints(Math.abs(upside))} ${dir} the current ${fmtUsdCompact(currentFdv)} FDV`;
  } else if (fdv) {
    title = `The model's median value for NEAR is ${fmtUsdCompact(fdv.p50)}; the current FDV is not available in this snapshot`;
  } else {
    title = "The valuation percentiles are missing from this snapshot";
  }

  const eyebrow = sotp
    ? `Investment thesis. ${fmtInt(sotp.n_paths)} seeded Monte Carlo paths, ${fmtInt(sotp.horizon_months)}-month horizon, ${fmtPct(sotp.discount_rate, { decimals: 0 })} discount rate`
    : "Investment thesis";

  // ------------------------------------------------------------------ regimes
  const regimeRows: RegimeRow[] = (supply?.regimes ?? []).map((reg) => {
    const traj = supply?.trajectories?.find((t) => t.regime === reg.key);
    const mc =
      sotp?.crossover_month_distribution?.[
        reg.key as "status_quo" | "svrn_glidepath"
      ];
    const ends = regimeEndpoints(snapshot, reg.key);
    const breakeven = supply?.breakeven_daily_volume_usd?.[reg.key] ?? null;
    const atCeiling =
      supply?.breakeven_daily_volume_usd_at_ceiling?.[reg.key] ?? null;
    return {
      key: reg.key,
      label: regimeShortLabel(reg.key),
      inflation:
        ends.start === null
          ? NA
          : ends.start === ends.end
            ? `${fmtPct(ends.start)} inflation cap, flat`
            : `${fmtPct(ends.start)} falling to ${fmtPct(ends.end)}`,
      issuance: traj
        ? `${fmtNear(traj.daily_issuance_start)} to ${fmtNear(traj.daily_issuance_end)}`
        : NA,
      deterministic: traj
        ? fmtMonth(traj.crossover_month, { na: noneText })
        : NA,
      cumulative: traj
        ? fmtMonth(traj.cumulative_crossover_month, { na: "none" })
        : NA,
      pCross:
        mc && isNum(mc.p_crossover_within_36m)
          ? mc.p_crossover_within_36m
          : null,
      medianMonth: mc && isNum(mc.p50_month) ? mc.p50_month : null,
      pDeflationary:
        mc && isNum(mc.p_deflationary_at_horizon)
          ? mc.p_deflationary_at_horizon
          : null,
      breakeven: isNum(breakeven) ? breakeven : null,
      breakevenAtCeiling: isNum(atCeiling) ? atCeiling : null,
      multipleOfToday: ratio(breakeven, today.value),
    };
  });
  const multiples = regimeRows.map((r) => r.multipleOfToday).filter(isNum);
  const minMultiple = multiples.length ? Math.min(...multiples) : null;
  const maxMultiple = multiples.length ? Math.max(...multiples) : null;
  const above = regimeRows.filter(
    (r) => isNum(r.multipleOfToday) && r.multipleOfToday <= 1,
  );
  const below = regimeRows.filter(
    (r) => isNum(r.multipleOfToday) && r.multipleOfToday > 1,
  );

  // ------------------------------------------------------------------ percentile table
  const pctRows: PercentileRow[] = [];
  const vsSpot = (p50: number, ref: number | null) =>
    isNum(ref) && ref !== 0 ? (p50 / ref - 1) * 100 : null;
  if (fdv)
    pctRows.push(
      pctRow(
        "fdv",
        "Implied FDV",
        `Discounted, ${horizon ? `${fmtInt(horizon)}-month` : "model"} horizon`,
        fdv,
        (v) => fmtUsdCompact(v),
        currentFdv,
        isNum(upside) ? upside : vsSpot(fdv.p50, currentFdv),
      ),
    );
  if (price)
    pctRows.push(
      pctRow(
        "price",
        "Implied price per NEAR",
        null,
        price,
        (v) => fmtUsd(v, { decimals: 2 }),
        currentPrice,
        vsSpot(price.p50, currentPrice),
      ),
    );
  if (fdvEx)
    pctRows.push(
      pctRow(
        "fdv_ex",
        "Implied FDV, ex monetary engine",
        "Engines 1 and 2 only",
        fdvEx,
        (v) => fmtUsdCompact(v),
        currentFdv,
        vsSpot(fdvEx.p50, currentFdv),
      ),
    );

  const pctColumns: Column<PercentileRow>[] = [
    {
      key: "label",
      header: "Measure",
      width: "17rem",
      render: (r) => (
        <div>
          <div className="text-ink">{r.label}</div>
          {r.note ? (
            <div className="text-[12.5px] text-dim">{r.note}</div>
          ) : null}
        </div>
      ),
    },
    ...PERCENTILE_KEYS.map<Column<PercentileRow>>((k) => ({
      key: k,
      header: k.toUpperCase(),
      numeric: true,
      headerClassName: k === "p50" ? "text-ink" : undefined,
      render: (r) => (
        <span
          className={cn(
            "tnum",
            k === "p50" ? "font-semibold text-ink" : "text-ink",
          )}
        >
          {r.cells[k]}
        </span>
      ),
    })),
    {
      key: "current",
      header: "Current",
      numeric: true,
      className: "border-l border-border",
      headerClassName: "border-l border-border",
      render: (r) => <span className="tnum text-muted">{r.current}</span>,
    },
    {
      key: "vs",
      header: "Median vs current",
      numeric: true,
      render: (r) => (
        <span
          className={cn("tnum font-medium", SIGN_TEXT[toneBySign(r.vsSpot)])}
        >
          {fmtPctPoints(r.vsSpot, { signed: true })}
        </span>
      ),
    },
  ];

  const regimeColumns: Column<RegimeRow>[] = [
    {
      key: "label",
      header: "Issuance regime",
      width: "12rem",
      render: (r) => (
        <div>
          <div className="text-ink">{r.label}</div>
          <div className="text-[12.5px] text-dim">{r.inflation}</div>
        </div>
      ),
    },
    {
      key: "issuance",
      header: "Issuance per day, first to last month",
      numeric: true,
      render: (r) => <span className="tnum text-ink">{r.issuance}</span>,
    },
    {
      key: "breakeven",
      header: "Breakeven daily volume",
      numeric: true,
      render: (r) => (
        <div className="tnum">
          <div className="text-ink">{fmtUsdCompact(r.breakeven)}</div>
          {isNum(r.breakevenAtCeiling) ? (
            <div className="text-[12.5px] text-dim">
              {fmtUsdCompact(r.breakevenAtCeiling)} at the fee ceiling
            </div>
          ) : null}
        </div>
      ),
    },
    {
      key: "multiple",
      header: "Multiple of today's volume",
      numeric: true,
      render: (r) => (
        <span
          className={cn(
            "tnum font-medium",
            SIGN_TEXT[
              isNum(r.multipleOfToday)
                ? r.multipleOfToday <= 1
                  ? "emerald"
                  : "crimson"
                : "neutral"
            ],
          )}
        >
          {isNum(r.multipleOfToday)
            ? fmtMultiple(r.multipleOfToday, { decimals: 2 }).replace(/x$/, "×")
            : NA}
        </span>
      ),
    },
    {
      key: "deterministic",
      header: "Crossover on the expected path",
      width: "11.5rem",
      render: (r) => (
        <div>
          <div className="text-ink">{r.deterministic}</div>
          <div className="text-[12.5px] text-dim">
            Cumulative basis: {r.cumulative}
          </div>
        </div>
      ),
    },
    {
      key: "pcross",
      header: horizon
        ? `Chance of crossover within ${fmtInt(horizon)} months`
        : "Chance of crossover",
      numeric: true,
      render: (r) => (
        <span className="tnum text-ink">
          {fmtPct(r.pCross, { decimals: 1 })}
        </span>
      ),
    },
    {
      key: "median",
      header: "Median crossover month",
      numeric: true,
      render: (r) => (
        <span className="tnum text-ink">
          {isNum(r.medianMonth) ? fmtMonth(r.medianMonth) : NA}
        </span>
      ),
    },
    {
      key: "pdefl",
      header: horizon
        ? `Chance supply is shrinking at month ${fmtInt(horizon)}`
        : "Chance supply is shrinking at horizon",
      numeric: true,
      render: (r) => (
        <span className="tnum text-ink">
          {fmtPct(r.pDeflationary, { decimals: 1 })}
        </span>
      ),
    },
  ];

  const mcNote = sotp?.crossover_month_distribution?.note ?? null;
  const coverage = supply?.sink_coverage_ratio ?? null;
  const assumptionCount = (snapshot.assumptions ?? []).filter(
    (a) => a.source === "assumption",
  ).length;

  // ------------------------------------------------------------------ regime lede
  const regimeLede: string[] = [];
  if (isNum(today.value) && isNum(coverage))
    regimeLede.push(
      `At today's ${fmtUsdCompact(today.value)} of daily volume, buybacks, gas burn and state lock absorb ${fmtPct(coverage, { decimals: 1 })} of new issuance.`,
    );
  if (below.length)
    regimeLede.push(
      `Net supply stops growing only once daily volume reaches ${joinAnd(below.map((r) => `${fmtUsdCompact(r.breakeven)} under the ${r.label === "Status quo" ? "status quo" : r.label}`))}.`,
    );
  if (above.length)
    regimeLede.push(
      `Today's volume already clears breakeven under ${joinAnd(above.map((r) => (r.label === "Status quo" ? "the status quo" : `the ${r.label}`)))}.`,
    );

  const assumptionBadge = (
    assumptionCount ? (
            <Badge
              variant="assumption"
              title="Terminal multiple, discount rate, confidential take and growth are labelled assumptions; see the SOTP tab sliders."
            >
              {fmtInt(assumptionCount)} labelled assumptions
            </Badge>
          ) : null
  );

  return (
    <section id="verdict" className={cn("space-y-10", className)}>
      {lead ? (
        <SectionIntro
          eyebrow={eyebrow}
          title={title}
          aside={assumptionBadge}
        >
        {detFdv !== null && fdv ? (
          <p>
            The median is not the base case. Volume follows a mean-matching
            random walk, so the expected path is worth {fmtUsdCompact(detFdv)}
            {mcMean !== null
              ? ` (Monte Carlo mean ${fmtUsdCompact(mcMean)})`
              : ""}{" "}
            and the median path
            {p50OfDet !== null
              ? ` reaches ${fmtPct(p50OfDet, { decimals: 0 })} of it`
              : " sits below it"}
            . Read the P10 to P90 range below, not a single point.
          </p>
        ) : (
          <p>
            Calibration fields are missing, so the expected path cannot be
            compared with the median in this snapshot.
          </p>
        )}
        </SectionIntro>
      ) : (
        <SubHead title="What the cash-flow model values" aside={assumptionBadge}>
          <p className="mb-2">{title}.</p>
        {detFdv !== null && fdv ? (
          <p>
            The median is not the base case. Volume follows a mean-matching
            random walk, so the expected path is worth {fmtUsdCompact(detFdv)}
            {mcMean !== null
              ? ` (Monte Carlo mean ${fmtUsdCompact(mcMean)})`
              : ""}{" "}
            and the median path
            {p50OfDet !== null
              ? ` reaches ${fmtPct(p50OfDet, { decimals: 0 })} of it`
              : " sits below it"}
            . Read the P10 to P90 range below, not a single point.
          </p>
        ) : (
          <p>
            Calibration fields are missing, so the expected path cannot be
            compared with the median in this snapshot.
          </p>
        )}
        </SubHead>
      )}

      <StatGrid cols={4}>
        <Stat
          label="Median FDV against current"
          value={fmtPctPoints(upside, { signed: true })}
          tone={toneBySign(upside)}
          provenance={NEARSTATS_SUMMARY}
          hint={`${fmtUsdCompact(fdv?.p50 ?? null)} median; ${fmtUsdCompact(currentFdv)} at ${fmtUsd(currentPrice, { decimals: 2 })} spot`}
        />
        <Stat
          label="Net revenue run-rate"
          value={fmtUsdCompact(fees?.annualized_net_revenue_30d_usd ?? null)}
          unit="a year"
          provenance={DEFILLAMA_NET}
          delta={{
            value: `${fmtUsdCompact(fees?.annualized_gross_fees_30d_usd ?? null)} gross fees`,
            label: `${fmtPct(fees?.capture_ratio ?? null, { decimals: 1 })} captured`,
          }}
          hint={`Annualised from the last ${windowDays !== null ? fmtInt(windowDays) : "30"} complete days`}
        />
        <Stat
          label="Daily volume today"
          value={fmtUsdCompact(today.value)}
          unit="a day"
          provenance={today.ref}
          delta={
            isNum(minMultiple) && isNum(maxMultiple)
              ? {
                  value:
                    minMultiple === maxMultiple
                      ? `Breakeven is ${fmtNum(minMultiple, { decimals: 2 })}× this`
                      : `Breakeven is ${fmtNum(minMultiple, { decimals: 2 })}× to ${fmtNum(maxMultiple, { decimals: 2 })}× this`,
                  tone: (minMultiple <= 1 ? "emerald" : "crimson") as Tone,
                }
              : undefined
          }
          hint="Depending on the issuance regime"
        />
        <Stat
          label="Sink coverage of issuance"
          value={fmtPct(coverage, { decimals: 1 })}
          tone={
            isNum(coverage)
              ? coverage >= 1
                ? "emerald"
                : "crimson"
              : "neutral"
          }
          provenance={epochBlockRef(snapshot) ?? DEFILLAMA_HOLDERS}
          hint={`${fmtNear(supply?.current_daily_sinks_near?.total ?? null)} absorbed of ${fmtNear(supply?.current_daily_issuance_near ?? null)} issued a day`}
        />
      </StatGrid>

      <div className="space-y-4">
        <SubHead title="Valuation distribution">
          Percentiles across the seeded paths. Figures are in ink; only the last
          column is coloured, by the sign of the median against the current
          market.
        </SubHead>
        <Panel className="valuo-scroll overflow-x-auto px-2 py-1">
          <div className="min-w-[46rem]">
            <Table<PercentileRow>
              columns={pctColumns}
              rows={pctRows}
              rowKey={(r) => r.key}
              emptyText="Valuation percentiles are missing from this snapshot"
              dense={false}
            />
          </div>
        </Panel>
      </div>

      <div className="space-y-4">
        <SubHead title="Supply crossover by issuance regime">
          {regimeLede.length
            ? regimeLede.join(" ")
            : "Regime outputs are missing from this snapshot."}
        </SubHead>
        <Panel className="valuo-scroll overflow-x-auto px-2 py-1">
          <div className="min-w-[60rem]">
            <Table<RegimeRow>
              columns={regimeColumns}
              rows={regimeRows}
              rowKey={(r) => r.key}
              emptyText="Supply regimes are missing from this snapshot"
              dense={false}
            />
          </div>
        </Panel>
        <p className="max-w-4xl text-[13px] leading-relaxed text-muted">
          Crossover is the first month in which buybacks, gas burn and state
          lock absorb all new issuance. The expected path holds price at spot
          and volume flat; the chances are shares of the seeded paths.
        </p>
      </div>

      <MethodNote>
        <p>
          FDV is the present value of holder revenue plus a discounted terminal
          value, summed over three engines on each path; percentiles are taken
          over those per-path totals. Fields: <code>sotp.fdv_percentiles</code>,{" "}
          <code>sotp.price_percentiles</code>,{" "}
          <code>sotp.fdv_ex_monetary_percentiles</code> (Engines 1 and 2; Engine
          3 is a demand-flow proxy), <code>sotp.current_fdv_usd</code>,{" "}
          <code>sotp.upside_p50_pct</code>. Seed {String(sotp?.seed ?? NA)}.
        </p>
        <p>
          Expected path versus median: deterministic expected-path FDV{" "}
          {fmtUsdCompact(detFdv)} (
          <code>sotp.calibration.deterministic_base.fdv_total</code>), Monte
          Carlo mean {fmtUsdCompact(mcMean)} (
          <code>sotp.calibration.mc_mean_fdv</code>).
          {volMean !== null && volMedian !== null
            ? ` Public volume at month ${horizon !== null ? fmtInt(horizon) : NA}: mean ${fmtUsdCompact(volMean)} a day against a median of ${fmtUsdCompact(volMedian)} a day`
            : ""}
          {volMean !== null && volMedian !== null ? (
            <>
              {" "}
              (<code>sotp.calibration.volume_terminal_mean_usd_day</code>,{" "}
              <code>volume_terminal_median_usd_day</code>)
              {sigmaVol !== null
                ? `; monthly volume volatility ${fmtNum(sigmaVol, { decimals: 3 })}${sigmaVolN !== null ? ` from ${fmtInt(sigmaVolN)} monthly log returns` : ""}`
                : ""}
              . Under the mean-matching GBM the median path sits below the
              expected path by exp(−σ²t/2).
            </>
          ) : null}
        </p>
        <p>
          Run-rates: gross fees and net revenue over{" "}
          {windowText ?? "the trailing 30 days"}, annualised × 365 /{" "}
          {windowDays !== null ? fmtInt(windowDays) : "30"} (
          <code>intents_forensics.fees.annualized_gross_fees_30d_usd</code>,{" "}
          <code>intents_forensics.fees.annualized_net_revenue_30d_usd</code>).
          Net revenue is NEAR swept to its revenue wallets and directed to
          buybacks.
        </p>
        <p>
          Today&apos;s daily volume: <code>{today.path}</code>. {today.basis}.
        </p>
        <p>
          Sink coverage = (buyback + gas burn + state lock) / measured issuance
          (<code>supply_physics.sink_coverage_ratio</code>). Breakeven V* =
          (issuance − gas burn − state lock) × price / (gross take × capture) (
          <code>supply_physics.breakeven_daily_volume_usd</code>; at the
          competitive fee ceiling,{" "}
          <code>supply_physics.breakeven_daily_volume_usd_at_ceiling</code>).
          Issuance by month:{" "}
          <code>supply_physics.trajectories[].daily_issuance_start</code> /{" "}
          <code>_end</code>; expected-path crossover{" "}
          <code>supply_physics.trajectories[].crossover_month</code> and{" "}
          <code>cumulative_crossover_month</code>.
        </p>
        <p>
          Crossover chances:{" "}
          <code>
            sotp.crossover_month_distribution.&lt;regime&gt;.p_crossover_within_36m
          </code>
          , <code>p50_month</code>, <code>p_deflationary_at_horizon</code>.
          {mcNote ? ` Model note: ${mcNote}` : ""}
        </p>
      </MethodNote>
    </section>
  );
}

function pctRow(
  key: string,
  label: string,
  note: string | null,
  map: Record<PercentileKey, number>,
  fmt: (v: number) => string,
  reference: number | null,
  vsSpot: number | null,
): PercentileRow {
  const cells = {} as Record<PercentileKey, string>;
  for (const k of PERCENTILE_KEYS) {
    const v = map[k];
    cells[k] = isNum(v) ? fmt(v) : NA;
  }
  return {
    key,
    label,
    note,
    cells,
    current: isNum(reference) ? fmt(reference) : NA,
    vsSpot,
  };
}
