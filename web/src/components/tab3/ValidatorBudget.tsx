import { fmtInt, fmtNear, fmtNearCompact, fmtPct } from "@/lib/format";
import { explorerAccountUrl } from "@/lib/manifestIndex";
import type { NearOnchainTruth, StakingYieldRow } from "@/lib/types";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Card } from "@/components/ui/Card";
import { MethodNote, StatGrid } from "@/components/ui/Section";
import { Stat } from "@/components/ui/Stat";
import { Table, type Column } from "@/components/ui/Table";
import { REF_BLOCK_FINAL, REF_HOLDERS_REVENUE, REF_PROTOCOL_CONFIG, REF_VALIDATORS } from "./provenanceRefs";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function Signed({ v }: { v: number | null | undefined }) {
  if (!finite(v)) return <span className="text-dim">n/a</span>;
  return <span className={v > 0 ? "text-emerald" : v < 0 ? "text-crimson" : "text-ink"}>{fmtPct(v, { decimals: 2, signed: true })}</span>;
}

const SHORT_REGIME: Record<string, string> = { status_quo: "Status quo", svrn_glidepath: "SVRN glidepath" };

export interface ValidatorBudgetProps {
  rpc: NearOnchainTruth | null | undefined;
  rows: StakingYieldRow[] | null | undefined;
  /** regime key -> label from supply_physics.regimes */
  regimeLabels: Record<string, string>;
}

/**
 * Validator security budget: live stake and validator set, the treasury share of issuance, and
 * the per-regime yield table. real = nominal - inflation; the buyback accrual is float removed per
 * unit of supply and accrues to every holder, staked or not.
 */
export function ValidatorBudget({ rpc, rows, regimeLabels }: ValidatorBudgetProps) {
  const table: StakingYieldRow[] = Array.isArray(rows) ? rows : [];
  const treasury = rpc?.protocol_reward_rate ?? null;
  const validatorShare = finite(treasury) ? 1 - treasury : null;

  const columns: Column<StakingYieldRow>[] = [
    { key: "regime", header: "Regime", render: (r) => <span className="text-ink" title={regimeLabels[r.regime]}>{SHORT_REGIME[r.regime] ?? regimeLabels[r.regime] ?? r.regime}</span> },
    { key: "inflation", header: "Terminal inflation", numeric: true, render: (r) => fmtPct(r.inflation_rate, { decimals: 2 }) },
    { key: "nominal", header: "Nominal staking APR", numeric: true, render: (r) => fmtPct(r.nominal_staking_apr, { decimals: 2 }) },
    { key: "real", header: "Real staking APR", numeric: true, render: (r) => <Signed v={r.real_staking_apr} /> },
    { key: "accrual", header: "Buyback accrual", numeric: true, render: (r) => fmtPct(r.buyback_accrual_apr, { decimals: 2, signed: true }) },
    { key: "realbb", header: "Real APR with buybacks", numeric: true, render: (r) => <Signed v={r.real_staking_apr_with_buyback} /> },
    { key: "nonstaker", header: "Non-staker real return", numeric: true, render: (r) => <Signed v={r.real_non_staker_apr} /> },
    { key: "daily", header: "Daily issuance", numeric: true, render: (r) => fmtNear(r.daily_issuance_near) },
  ];

  const statusQuo = table.find((r) => r.regime === "status_quo");
  const glide = table.find((r) => r.regime === "svrn_glidepath");
  const nominalDrop = statusQuo && glide ? glide.nominal_staking_apr - statusQuo.nominal_staking_apr : null;
  const realDrop = statusQuo && glide ? glide.real_staking_apr_with_buyback - statusQuo.real_staking_apr_with_buyback : null;

  return (
    <Card
      title="Validator security budget"
      subtitle="Who is paid from issuance, and what a holder keeps after dilution under each regime's terminal rate."
      actions={<ProvenanceBadge source={REF_VALIDATORS.source} name={REF_VALIDATORS.name} label="Validators" />}
    >
      <div className="space-y-6">
        <StatGrid cols={4}>
          <Stat label="Active validators" value={rpc?.active_validator_count} format={(v) => fmtInt(v)} />
          <Stat label="Total staked" value={rpc?.total_staked_near} format={(v) => fmtNearCompact(v)} hint={finite(rpc?.staked_supply_ratio) ? `${fmtPct(rpc!.staked_supply_ratio, { decimals: 2 })} of supply` : undefined} provenance={REF_BLOCK_FINAL} />
          <Stat
            label="Treasury share of issuance"
            value={treasury}
            format={(v) => fmtPct(v, { decimals: 2 })}
            hint={finite(validatorShare) ? `Validators receive ${fmtPct(validatorShare, { decimals: 2 })}` : undefined}
            provenance={REF_PROTOCOL_CONFIG}
          />
          <Stat label="Nominal staking APR, live cap" value={rpc?.nominal_staking_apr_current} format={(v) => fmtPct(v, { decimals: 2 })} />
        </StatGrid>

        {statusQuo && glide && finite(nominalDrop) && finite(realDrop) ? (
          <p className="max-w-4xl text-[14.5px] leading-relaxed text-muted">
            Cutting the cap to {fmtPct(glide.inflation_rate, { decimals: 2 })} changes nominal validator APR by{" "}
            <span className="tnum text-ink">{fmtPct(nominalDrop, { decimals: 2, signed: true })}</span> and a staker&apos;s real return with buybacks by{" "}
            <span className="tnum text-ink">{fmtPct(realDrop, { decimals: 2, signed: true })}</span>. An unstaked holder&apos;s real return moves from <Signed v={statusQuo.real_non_staker_apr} /> to{" "}
            <Signed v={glide.real_non_staker_apr} />.
          </p>
        ) : (
          <p className="text-[13.5px] text-muted">The staking table lacks one of the two snapshot regimes, so there is no comparison.</p>
        )}

        <Table<StakingYieldRow> columns={columns} rows={table} rowKey={(r) => r.regime} caption="Yields at each regime's terminal inflation rate" emptyText="No staking yield table in this snapshot" />

        <MethodNote>
          <p>
            Nominal APR = <code>inflation × (1 − treasury) / staked_ratio</code>; real = nominal − inflation; buyback accrual = <code>buyback NEAR/day × 365.25 / total supply</code>; non-staker real return =
            −inflation + buyback accrual. Buybacks are open-market purchases funded by NEAR Intents holders revenue, not burns, and accrue to every holder.
          </p>
          <p>
            Treasury share is <code>protocol_reward_rate</code>
            {rpc?.protocol_treasury_account ? (
              <>
                {", paid to "}
                <a href={explorerAccountUrl(rpc.protocol_treasury_account)} target="_blank" rel="noreferrer" className="text-accent underline decoration-accent/40 underline-offset-2">
                  {rpc.protocol_treasury_account}
                </a>
              </>
            ) : null}
            . Fields: <code>supply_physics.staking_yield_table</code>, <code>near_rpc.active_validator_count</code>, <code>near_rpc.total_staked_near</code>, <code>near_rpc.staked_supply_ratio</code>,{" "}
            <code>near_rpc.nominal_staking_apr_current</code>.
          </p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            Sources: <ProvenanceBadge source={REF_VALIDATORS.source} name={REF_VALIDATORS.name} label="Validator set" />
            <ProvenanceBadge source={REF_BLOCK_FINAL.source} name={REF_BLOCK_FINAL.name} label="Total supply" />
            <ProvenanceBadge source={REF_HOLDERS_REVENUE.source} name={REF_HOLDERS_REVENUE.name} label="Buyback revenue" />
          </div>
        </MethodNote>
      </div>
    </Card>
  );
}
