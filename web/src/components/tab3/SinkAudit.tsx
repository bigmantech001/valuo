import { fmtBytes, fmtInt, fmtNear, fmtNum, fmtPct, fmtUtc, NA } from "@/lib/format";
import { explorerAccountUrl, explorerBlockUrl } from "@/lib/manifestIndex";
import type { ContractSinkSnapshot, NearOnchainTruth, SinkHistoryPoint, SupplyPhysics } from "@/lib/types";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Card } from "@/components/ui/Card";
import { MethodNote, StatGrid } from "@/components/ui/Section";
import { Stat } from "@/components/ui/Stat";
import { Table, type Column } from "@/components/ui/Table";
import { REF_PROTOCOL_CONFIG, refSinkHistoryPoint, refStateLockGrowth, refViewAccount } from "./provenanceRefs";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

type HistoryRow = SinkHistoryPoint & { account_id: string; sink: ContractSinkSnapshot; delta_bytes: number | null; delta_days: number | null };

const LINK = "text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent";

/**
 * NEP storage-staking sink: `storage_usage` bytes x `storage_amount_per_byte` (1e19 yocto = 1 NEAR
 * per 100 KB) locked on each tracked account, with archival history where it was fetched.
 */
export function SinkAudit({ rpc, sp }: { rpc: NearOnchainTruth | null | undefined; sp: SupplyPhysics | null | undefined }) {
  const sinks: ContractSinkSnapshot[] = Array.isArray(rpc?.tracked_sinks) ? rpc!.tracked_sinks : [];
  const measuredSet = new Set(rpc?.measured_state_lock_growth_sinks ?? []);
  const growthRef = refStateLockGrowth(rpc);
  const dailyIssuance = sp?.current_daily_issuance_near ?? null;
  const growth = rpc?.measured_state_lock_growth_near_per_day ?? null;
  const growthShare = finite(growth) && finite(dailyIssuance) && dailyIssuance > 0 ? growth / dailyIssuance : null;
  const nearPerKb = rpc?.storage_near_per_kb ?? null;
  const kbPerNear = finite(nearPerKb) && nearPerKb > 0 ? 1 / nearPerKb : null;
  const intents = sinks.find((s) => s.account_id === "intents.near") ?? null;
  const measuredList = [...measuredSet];

  const history: HistoryRow[] = sinks.flatMap((s) => {
    const pts = Array.isArray(s.history) ? [...s.history].sort((a, b) => b.days_before_now - a.days_before_now) : [];
    return pts.map((p, i) => ({
      ...p,
      account_id: s.account_id,
      sink: s,
      delta_bytes: i > 0 ? p.storage_bytes - pts[i - 1].storage_bytes : null,
      delta_days: i > 0 ? pts[i - 1].days_before_now - p.days_before_now : null,
    }));
  });

  const sinkColumns: Column<ContractSinkSnapshot>[] = [
    {
      key: "account",
      header: "Account",
      render: (s) => (
        <span className="flex min-w-[11rem] flex-col">
          <a href={explorerAccountUrl(s.account_id)} target="_blank" rel="noreferrer" className={LINK}>
            {s.account_id}
          </a>
          <span className="max-w-[22rem] truncate text-[12px] text-dim" title={s.code_hash ? `${s.label} (code hash ${s.code_hash})` : s.label}>
            {s.has_contract ? s.label : `${s.label}${s.label ? "; " : ""}no contract code`}
          </span>
        </span>
      ),
    },
    { key: "bytes", header: "State size", numeric: true, render: (s) => <span title={`${fmtInt(s.storage_bytes)} bytes`}>{fmtBytes(s.storage_bytes)}</span> },
    { key: "locked", header: "NEAR locked", numeric: true, render: (s) => <span className="text-ink">{fmtNear(s.storage_locked_near)}</span> },
    {
      key: "growth",
      header: "Growth per day",
      numeric: true,
      render: (s) =>
        finite(s.growth_locked_near_per_day) ? (
          <span title={`${fmtBytes(s.growth_bytes_per_day)} of state per day`}>{fmtNear(s.growth_locked_near_per_day, { decimals: 1, signed: true })}</span>
        ) : (
          <span className="text-dim">Not measured</span>
        ),
    },
    {
      key: "window",
      header: "Window",
      numeric: true,
      render: (s) => (finite(s.growth_window_days) ? `${fmtNum(s.growth_window_days, { decimals: 1 })} days` : <span className="text-dim">{NA}</span>),
    },
    {
      key: "record",
      header: "Source",
      render: (s) => {
        const r = refViewAccount(s.account_id);
        return <ProvenanceBadge source={r.source} name={r.name} />;
      },
    },
  ];

  const historyColumns: Column<HistoryRow>[] = [
    { key: "account", header: "Account", render: (h) => <span className="text-ink">{h.account_id}</span> },
    {
      key: "block",
      header: "Block",
      render: (h) => (
        <a href={explorerBlockUrl(h.block_height)} target="_blank" rel="noreferrer" className={`tnum ${LINK}`}>
          {`#${fmtInt(h.block_height)}`}
        </a>
      ),
    },
    { key: "ts", header: "Time (UTC)", render: (h) => <span className="text-muted">{fmtUtc(h.timestamp_utc)}</span> },
    { key: "days", header: "Days before snapshot", numeric: true, render: (h) => fmtNum(h.days_before_now, { decimals: 2 }) },
    { key: "bytes", header: "State size", numeric: true, render: (h) => <span title={`${fmtInt(h.storage_bytes)} bytes`}>{fmtBytes(h.storage_bytes)}</span> },
    {
      key: "delta",
      header: "Change vs prior",
      numeric: true,
      render: (h) =>
        finite(h.delta_bytes) ? (
          <span title={finite(h.delta_days) && h.delta_days > 0 ? `${fmtBytes(h.delta_bytes / h.delta_days)} per day` : undefined}>{`${h.delta_bytes >= 0 ? "+" : "−"}${fmtBytes(Math.abs(h.delta_bytes))}`}</span>
        ) : (
          <span className="text-dim">Oldest point</span>
        ),
    },
    {
      key: "record",
      header: "Source",
      render: (h) => {
        const ref = refSinkHistoryPoint(h.sink, h.block_height, h.days_before_now);
        return <ProvenanceBadge source={ref.source} name={ref.name} />;
      },
    },
  ];

  return (
    <Card
      title="Storage-lock sink"
      subtitle={`Contract state must be backed by staked NEAR${finite(kbPerNear) ? ` at 1 NEAR per ${fmtNum(kbPerNear, { decimals: 0 })} KB` : ""}. That NEAR cannot circulate while the state exists, so state growth on busy contracts is a supply sink.`}
      actions={<ProvenanceBadge source={REF_PROTOCOL_CONFIG.source} name={REF_PROTOCOL_CONFIG.name} label="Storage price" />}
      footer={
        <span>
          {measuredList.length
            ? `Growth is measured from archival reads on ${measuredList.join(" and ")}; other accounts get no growth credit.`
            : rpc?.archival_available
              ? "Archival RPC was available but no account has a growth measurement; the model credits no storage-lock growth."
              : `Archival RPC was ${rpc?.archival_attempted ? "unavailable" : "not queried"}, so the model credits no storage-lock growth.`}
          {rpc?.missing_accounts?.length ? ` Accounts not found: ${rpc.missing_accounts.join(", ")}.` : ""}
          {" wrap.near's balance is user deposits, not a sink; escrow.ai.near is a caller of intents.near, not a contract."}
        </span>
      }
    >
      <div className="space-y-6">
        <StatGrid cols={3}>
          <Stat label="NEAR locked in tracked state" value={rpc?.total_state_locked_near} format={(v) => fmtNear(v)} hint={`Across ${fmtInt(sinks.length)} tracked accounts`} />
          <Stat
            label="Measured lock growth"
            value={growth}
            format={(v) => fmtNear(v, { decimals: 1, signed: true })}
            unit="per day"
            hint={finite(growthShare) ? `${fmtPct(growthShare, { decimals: 2 })} of daily issuance` : "Archival history not fetched"}
            provenance={growthRef}
          />
          <Stat
            label="intents.near alone"
            value={intents?.storage_locked_near ?? null}
            format={(v) => fmtNear(v)}
            hint={intents ? `${fmtBytes(intents.storage_bytes)} of state` : undefined}
            provenance={refViewAccount("intents.near")}
          />
        </StatGrid>

        <Table<ContractSinkSnapshot>
          columns={sinkColumns}
          rows={sinks}
          rowKey={(s) => s.account_id}
          caption={`Tracked accounts at block ${fmtInt(rpc?.block_height)}`}
          emptyText="No tracked accounts in this snapshot"
          rowClassName={(s) => (measuredSet.has(s.account_id) ? undefined : "text-muted")}
        />

        <MethodNote summary="Method, sources and archival readings">
          <p>
            NEAR locked = <code>view_account.storage_usage × storage_amount_per_byte</code> (
            {finite(rpc?.storage_amount_per_byte_yocto) ? <code>{rpc!.storage_amount_per_byte_yocto.toExponential(0)}</code> : NA} yoctoNEAR per byte). Growth per day is the change in{" "}
            <code>storage_usage</code> between archival reads over the window, times the same price. Fields: <code>near_rpc.tracked_sinks</code>, <code>near_rpc.total_state_locked_near</code>,{" "}
            <code>near_rpc.measured_state_lock_growth_near_per_day</code>, <code>near_rpc.measured_state_lock_growth_sinks</code>.
          </p>
          <p>
            Archival RPC {rpc?.archival_available ? "available" : "unavailable"}
            {rpc?.archival_attempted ? "" : " (not attempted)"}. Readings behind the growth measurement:
          </p>
          <Table<HistoryRow>
            columns={historyColumns}
            rows={history}
            rowKey={(h) => `${h.account_id}@${h.block_height}`}
            emptyText="No archival history in this snapshot (archival RPC unavailable or skipped)"
          />
        </MethodNote>
      </div>
    </Card>
  );
}
