import { fmtBps, fmtInt, fmtNear, fmtNearCompact, fmtNum, fmtPct, fmtUsd, fmtUsdCompact } from "@/lib/format";
import type { Assumption, AssumptionSource, NearOnchainTruth, SupplyPhysics } from "@/lib/types";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Table, type Column } from "@/components/ui/Table";
import { Tooltip } from "@/components/ui/Tooltip";
import { inputPathHint, inputProvenance } from "./provenanceRefs";

/** Format an Assumption value by its declared unit (units as written by supply_physics.py). */
export function fmtByUnit(value: number | null | undefined, unit: string): string {
  switch (unit) {
    case "NEAR":
      return fmtNear(value);
    case "NEAR_per_year":
      return `${fmtNearCompact(value)}/yr`;
    case "NEAR_per_day":
      return `${fmtNear(value, { decimals: 1 })}/day`;
    case "USD":
      return fmtUsd(value);
    case "USD_per_day":
      return `${fmtUsdCompact(value)}/day`;
    case "ratio":
    case "ratio_annual":
    case "ratio_yoy":
      return fmtPct(value, { decimals: 2 });
    case "bps":
      return fmtBps(value, { signed: false, decimals: 2 });
    case "months":
      return `${fmtInt(value)} mo`;
    case "KB":
      return `${fmtNum(value, { decimals: 0 })} KB`;
    default:
      return fmtNum(value, { decimals: 4 });
  }
}

/** Display names for the `supply_physics.inputs` keys; unknown keys fall back to a cleaned-up key. */
const INPUT_NAME: Record<string, string> = {
  total_supply_near: "Total supply",
  current_max_inflation_rate: "Maximum inflation rate (live cap)",
  treasury_share: "Treasury share of issuance",
  staked_supply_ratio: "Staked share of supply",
  annual_issuance_near: "Measured annual issuance",
  issuance_realization_factor: "Measured over nominal issuance",
  near_price_usd: "NEAR price",
  daily_volume_usd: "Intents daily volume",
  gross_take_bps: "Gross take rate",
  capture_ratio: "Share of fees used for buybacks",
  gas_burn_near_per_day: "Gas burn",
  state_lock_growth_near_per_day: "Storage-lock growth",
  svrn_target_inflation: "SVRN target inflation",
  svrn_glidepath_months: "SVRN glidepath length",
  kb_per_agent_vault: "State per agent vault",
  public_volume_growth_yoy: "Volume growth per year",
  competitive_fee_ceiling_bps: "Competitive fee ceiling",
};

function inputName(key: string): string {
  if (INPUT_NAME[key]) return INPUT_NAME[key];
  const s = key.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

type Row = Assumption & { order: number };

const SOURCE_WORD: Record<AssumptionSource, string> = { measured: "measured", derived: "derived", assumption: "assumptions" };

/**
 * `supply_physics.inputs`: every scalar the model ran on, with its source class, range and the raw
 * record it came from. Measured rows carry a source link; assumptions carry an assumption label and
 * their justification on hover.
 */
export function InputsPanel({ sp, rpc }: { sp: SupplyPhysics | null | undefined; rpc: NearOnchainTruth | null | undefined }) {
  const inputs = sp?.inputs ?? {};
  const rows: Row[] = Object.values(inputs)
    .filter((a): a is Assumption => Boolean(a) && typeof a.value === "number")
    .map((a, i) => ({ ...a, order: i }));
  const counts = rows.reduce<Record<AssumptionSource, number>>(
    (acc, r) => {
      acc[r.source] = (acc[r.source] ?? 0) + 1;
      return acc;
    },
    { measured: 0, derived: 0, assumption: 0 },
  );
  const countText = (["measured", "derived", "assumption"] as const)
    .filter((k) => counts[k] > 0)
    .map((k) => `${fmtInt(counts[k])} ${k === "assumption" && counts[k] === 1 ? "assumption" : SOURCE_WORD[k]}`)
    .join(", ");

  const columns: Column<Row>[] = [
    {
      key: "key",
      header: "Input",
      render: (r) => (
        <Tooltip
          wide
          content={
            <span className="block space-y-1.5">
              <span className="block">{r.justification || "No justification recorded."}</span>
              <code className="block font-mono text-[11.5px] text-muted">{inputPathHint(r.key)}</code>
            </span>
          }
        >
          <span tabIndex={0} className="cursor-help text-ink underline decoration-border-strong decoration-dotted underline-offset-4">
            {inputName(r.key)}
          </span>
        </Tooltip>
      ),
    },
    { key: "value", header: "Value", numeric: true, render: (r) => <span className="text-ink">{fmtByUnit(r.value, r.unit)}</span> },
    {
      key: "range",
      header: "Range tested",
      numeric: true,
      render: (r) => (r.low === r.high ? <span className="text-dim">Point value</span> : <span className="text-muted">{`${fmtByUnit(r.low, r.unit)} to ${fmtByUnit(r.high, r.unit)}`}</span>),
    },
    {
      key: "record",
      header: "Source",
      render: (r) => {
        const ref = inputProvenance(r.key, rpc);
        if (r.source === "assumption") return <Badge variant="assumption">Assumption</Badge>;
        if (ref) return <ProvenanceBadge source={ref.source} name={ref.name} />;
        return <span className="text-muted">Derived</span>;
      },
    },
  ];

  return (
    <Card
      title="Model inputs"
      subtitle={`Every scalar the trajectories, breakeven volumes and staking rows were computed from${countText ? `: ${countText}` : ""}. Hover an input for its justification and snapshot field.`}
      footer={
        sp?.warnings && sp.warnings.length ? (
          <ul className="list-disc space-y-0.5 pl-4 text-amber">
            {sp.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        ) : (
          <span>The supply model raised no warnings. Missing live inputs are never backfilled; a sink without a measurement gets zero credit and a warning here.</span>
        )
      }
    >
      <Table<Row> columns={columns} rows={rows} rowKey={(r) => r.key} emptyText="No model inputs in this snapshot" />
    </Card>
  );
}
