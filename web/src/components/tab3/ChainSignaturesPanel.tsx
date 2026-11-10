import { fmtBytes, fmtInt, fmtNear, fmtNum, fmtPct, fmtUsd, fmtUsdCompact, fmtUtc, NA } from "@/lib/format";
import { explorerAccountUrl, explorerBlockUrl } from "@/lib/manifestIndex";
import type { ChainSignatures, ChainSignaturesWindow } from "@/lib/types";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { Stat } from "@/components/ui/Stat";
import { Table, type Column } from "@/components/ui/Table";
import { refViewAccount } from "./provenanceRefs";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

const LINK = "text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent";
const CONTRACT = "v1.signer";
const REF_COUNT = { source: "nearblocks", name: `txns:${CONTRACT}:count` } as const;
const REF_PROTOCOL = { source: "near_rpc", name: "chain_signatures:protocol_config" } as const;

type CallerRow = { account_id: string; sign_receipts: number; share: number };

const STATUS_TEXT: Record<string, string> = {
  growing: "growing",
  declining: "declining",
  inconclusive: "no significant trend",
  not_measured: "trend not measured",
};

/**
 * Chain Signatures (MPC signer `v1.signer`): sign-request rate and trend from time-stratified
 * NearBlocks windows, what a request pays (deposit and gas), who calls it, and the storage lock.
 * Reads `snapshot.chain_signatures` only; renders an empty state when the audit is absent or failed.
 */
export function ChainSignaturesPanel({
  cs,
  dailyIssuanceNear,
  networkGasBurnNearPerDay,
}: {
  cs: ChainSignatures | null | undefined;
  dailyIssuanceNear: number | null | undefined;
  /** `supply_physics.current_daily_sinks_near.gas_burn`: network-wide burn from supply drift */
  networkGasBurnNearPerDay?: number | null;
}) {
  const intro = (
    <SectionIntro eyebrow="Second usage engine" title={headline(cs)}>
      <p>
        Chain Signatures lets a NEAR account sign transactions for other chains through the MPC network. Each request is one <code className="font-mono text-[14px]">sign</code> receipt on{" "}
        <a href={explorerAccountUrl(CONTRACT)} target="_blank" rel="noreferrer" className={LINK}>
          {CONTRACT}
        </a>
        . The rate below is sampled from NearBlocks receipt pages, so it is an estimate with a standard error, not an exact count.
      </p>
    </SectionIntro>
  );

  if (!cs || cs.status === "unavailable" || !cs.status) {
    return (
      <div className="space-y-6">
        {intro}
        <EmptyState title="Chain Signatures not measured in this snapshot">
          {cs?.not_measured?.length ? cs.not_measured.join("; ") : "The snapshot has no chain_signatures section (older run, or the audit failed). Re-run the pipeline to measure it."}
        </EmptyState>
      </div>
    );
  }

  const trend = cs.trend ?? null;
  const reward = finite(cs.burnt_gas_reward) ? cs.burnt_gas_reward : null;
  const gasDay = cs.gas_near_per_day_30d;
  const burntDay = finite(gasDay) ? gasDay * (1 - (reward ?? 0)) : null;
  const issuanceShare = finite(burntDay) && finite(dailyIssuanceNear) && dailyIssuanceNear > 0 ? burntDay / dailyIssuanceNear : null;
  const burnShare = finite(burntDay) && finite(networkGasBurnNearPerDay) && networkGasBurnNearPerDay > 0 ? burntDay / networkGasBurnNearPerDay : null;
  const windows: ChainSignaturesWindow[] = Array.isArray(cs.windows) ? cs.windows : [];
  const callers: CallerRow[] = Array.isArray(cs.callers?.top) ? cs.callers!.top : [];
  const storage = cs.storage ?? null;
  const ci = trend?.growth_30d_ci90;

  const windowColumns: Column<ChainSignaturesWindow>[] = [
    { key: "kind", header: "Anchor", render: (w) => <span className="text-muted">{w.kind === "midnight" ? "00:00 UTC" : w.kind === "level" ? "block height" : (w.kind ?? NA)}</span> },
    {
      key: "before",
      header: "Before",
      render: (w) =>
        finite(w.before_block) ? (
          <a href={explorerBlockUrl(w.before_block)} target="_blank" rel="noreferrer" className={`tnum ${LINK}`}>
            {`#${fmtInt(w.before_block)}`}
          </a>
        ) : (
          <span className="tnum">{w.before_date ?? NA}</span>
        ),
    },
    { key: "time", header: "Newest receipt (UTC)", render: (w) => <span className="text-muted">{fmtUtc(w.newest_time_utc ?? null)}</span> },
    { key: "span", header: "Span", numeric: true, render: (w) => `${fmtNum(w.span_s, { decimals: 0 })} s` },
    { key: "n", header: "Receipts", numeric: true, render: (w) => fmtInt(w.n_receipts) },
    { key: "sign", header: "Sign", numeric: true, render: (w) => fmtInt(w.n_sign) },
    { key: "rate", header: "Sign / day", numeric: true, render: (w) => <span className="text-ink">{fmtInt(w.sign_per_day ?? null)}</span> },
    {
      key: "record",
      header: "Source",
      render: (w) => (
        <ProvenanceBadge source="nearblocks" name={finite(w.before_block) ? `txns:${CONTRACT}:before_block:${w.before_block}` : `txns:${CONTRACT}:before_date:${w.before_date ?? ""}`} />
      ),
    },
  ];

  const callerColumns: Column<CallerRow>[] = [
    {
      key: "account",
      header: "Caller",
      render: (c) => (
        <a href={explorerAccountUrl(c.account_id)} target="_blank" rel="noreferrer" className={`inline-block max-w-[22rem] truncate align-bottom ${LINK}`} title={c.account_id}>
          {c.account_id}
        </a>
      ),
    },
    { key: "n", header: "Sign receipts", numeric: true, render: (c) => fmtInt(c.sign_receipts) },
    { key: "share", header: "Share", numeric: true, render: (c) => <span className="text-ink">{fmtPct(c.share, { decimals: 1 })}</span> },
  ];

  return (
    <div className="space-y-6">
      {intro}
      <Card
        title="Sign requests on v1.signer"
        subtitle={`${fmtInt(cs.windows_ok ?? 0)} sample windows, ${fmtInt(cs.receipts_sampled ?? 0)} receipts, ${fmtInt(cs.sign_receipts_sampled ?? 0)} sign requests over the trailing 30 days${cs.head_time_utc ? `, to ${fmtUtc(cs.head_time_utc)}` : ""}.`}
        actions={<ProvenanceBadge source={REF_COUNT.source} name={REF_COUNT.name} label="Cumulative count" />}
        footer={
          <span>
            {cs.fee_note ?? "Deposit attached to sign() as reported by NearBlocks."}
            {" "}Gas from these receipts is already inside the L1 gas-burn sink measured from supply drift; it is shown here to size the engine, not added to the sinks.
          </span>
        }
      >
        <div className="space-y-6">
          <StatGrid cols={4}>
            <Stat
              label="Sign requests, last 7 days"
              value={cs.sign_per_day_7d}
              format={(v) => fmtInt(v)}
              unit="per day"
              hint={finite(cs.sign_per_day_7d_se) ? `SE ${fmtInt(cs.sign_per_day_7d_se)}, ${fmtInt(cs.windows_7d ?? 0)} windows` : undefined}
            />
            <Stat
              label="Sign requests, last 30 days"
              value={cs.sign_per_day_30d}
              format={(v) => fmtInt(v)}
              unit="per day"
              hint={finite(cs.sign_per_day_30d_se) ? `SE ${fmtInt(cs.sign_per_day_30d_se)}, day-weighted strata` : undefined}
            />
            <Stat
              label="Trend, per 30 days"
              value={trend ? trend.growth_30d : null}
              format={(v) => fmtPct(v, { decimals: 0, signed: true })}
              tone={cs.growth_status === "growing" ? "emerald" : cs.growth_status === "declining" ? "crimson" : "neutral"}
              hint={
                trend
                  ? `${STATUS_TEXT[cs.growth_status ?? ""] ?? cs.growth_status}; t = ${fmtNum(trend.t_stat ?? null, { decimals: 2 })}${ci ? `, 90% CI ${fmtPct(ci[0], { decimals: 0, signed: true })} to ${fmtPct(ci[1], { decimals: 0, signed: true })}` : ""}`
                  : "Too few 00:00 UTC windows for a fit"
              }
            />
            <Stat
              label="Cumulative receipts"
              value={cs.cumulative_receipts ?? null}
              format={(v) => fmtInt(v)}
              hint="All methods (sign, respond, callbacks), NearBlocks index"
              provenance={REF_COUNT}
            />
          </StatGrid>

          <StatGrid cols={4}>
            <Stat
              label="Gas per request"
              value={cs.gas_near_per_sign}
              format={(v) => fmtNear(v, { decimals: 4 })}
              hint={finite(cs.gas_usd_per_sign) ? `${fmtUsd(cs.gas_usd_per_sign, { decimals: 4 })} at ${fmtUsd(cs.near_price_usd ?? null)}; sign + respond + callback` : undefined}
            />
            <Stat
              label="Gas burnt by v1.signer receipts"
              value={burntDay}
              format={(v) => fmtNear(v, { decimals: 1 })}
              unit="per day"
              hint={
                finite(issuanceShare)
                  ? `${finite(burnShare) ? `${fmtPct(burnShare, { decimals: 1 })} of network gas burn, ` : ""}${fmtPct(issuanceShare, { decimals: 2 })} of issuance; ${fmtUsdCompact(cs.gas_usd_per_day_30d ?? null)}/day`
                  : finite(cs.gas_usd_per_day_30d)
                    ? `${fmtUsdCompact(cs.gas_usd_per_day_30d)}/day gross`
                    : undefined
              }
              provenance={REF_PROTOCOL}
            />
            <Stat
              label="Deposit per request"
              value={cs.deposit_yocto_median ?? null}
              format={(v) => `${fmtInt(v)} yocto`}
              hint={finite(cs.deposit_usd_per_day_30d) ? `${fmtUsd(cs.deposit_usd_per_day_30d, { decimals: 2 })}/day to the signer at the 30d rate` : "Median of sampled sign() actions"}
            />
            <Stat
              label="Storage lock"
              value={storage?.storage_locked_near ?? null}
              format={(v) => fmtNear(v, { decimals: 1 })}
              hint={storage ? `${fmtBytes(storage.storage_bytes ?? null)} of state${finite(cs.storage_locked_usd) ? `, ${fmtUsdCompact(cs.storage_locked_usd)}` : ""}` : "v1.signer not in tracked sinks"}
              provenance={refViewAccount(CONTRACT)}
            />
          </StatGrid>

          <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
            <Table<CallerRow>
              columns={callerColumns}
              rows={callers}
              rowKey={(c) => c.account_id}
              caption={`Top callers of sign()${finite(cs.callers?.hhi ?? null) ? `; HHI ${fmtInt(cs.callers!.hhi)} across ${fmtInt(cs.callers!.n_callers)} callers` : ""}${finite(cs.callers?.bridge_share ?? null) ? `; ${fmtPct(cs.callers!.bridge_share, { decimals: 0 })} from *.bridge.near` : ""}`}
              emptyText="No sign requests in the sampled windows"
            />
            <Table<ChainSignaturesWindow>
              columns={windowColumns}
              rows={windows}
              rowKey={(w, i) => `${w.before_block ?? w.before_date ?? ""}-${i}`}
              caption="Sample windows (newest 100 receipts before each anchor)"
              emptyText="No sample window returned"
              maxHeight="22rem"
            />
          </div>
        </div>
      </Card>

      <MethodNote summary="Method and sources for Chain Signatures">
        <p>{cs.method ?? NA}</p>
        <p>
          Each window is one NearBlocks <code>/v1/account/v1.signer/txns?per_page=100</code> page, anchored either <code>before_block=H</code> (four heights in the last 7 days, 42 h apart, so they fall at different times of day) or{" "}
          <code>before_date=YYYY-MM-DD</code> (the newest receipts before 00:00 UTC, every 4 days back to 28 days). Receipt rate = <code>(n − 1) / span</code>; sign rate = receipt rate × share of receipts whose action is{" "}
          <code>sign</code>. The 30-day rate weights the last-7-day and 7-30-day means by 7/30 and 23/30; the older stratum is sampled at 00:00 UTC only. The trend is an OLS fit of <code>ln(sign rate)</code> on time over the 00:00 UTC
          series, so every point is the same time of day; growth = <code>exp(30 × slope) − 1</code>, graded growing only when t ≥ 2. NearBlocks&apos; <code>method=sign</code> filter times out on this account, its count endpoint
          rejects date filters, and deep <code>before_block</code> queries time out, so exact daily counts are not available key-free.
        </p>
        <p>
          Gas is <code>receipt_outcome.tokens_burnt</code> summed over every receipt in the windows; the share the contract keeps is <code>burnt_gas_reward</code> from the live protocol config ({finite(reward) ? fmtPct(reward, { decimals: 0 }) : NA}). Storage is the{" "}
          <code>near_rpc.tracked_sinks</code> row for v1.signer. Fields: <code>chain_signatures.*</code>.
          {cs.not_measured?.length ? ` Not measured this run: ${cs.not_measured.join("; ")}.` : ""}
        </p>
      </MethodNote>
    </div>
  );
}

function headline(cs: ChainSignatures | null | undefined): string {
  if (!cs || !finite(cs.sign_per_day_30d)) return "Chain Signatures: usage not measured in this snapshot";
  const rate = `${fmtInt(cs.sign_per_day_30d)} sign requests a day`;
  if (cs.growth_status === "growing" && cs.trend) return `Chain Signatures handles about ${rate}, growing ${fmtPct(cs.trend.growth_30d, { decimals: 0 })} per 30 days`;
  if (cs.growth_status === "declining" && cs.trend) return `Chain Signatures handles about ${rate}, down ${fmtPct(-cs.trend.growth_30d, { decimals: 0 })} per 30 days`;
  return `Chain Signatures handles about ${rate}; the 30-day sample shows no significant trend`;
}
