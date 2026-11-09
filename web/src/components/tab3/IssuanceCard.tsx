import { fmtHash, fmtInt, fmtNear, fmtNearCompact, fmtNum, fmtPct, fmtUtc, NA } from "@/lib/format";
import { explorerBlockUrl } from "@/lib/manifestIndex";
import type { EpochIssuanceJump, NearOnchainTruth } from "@/lib/types";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Card } from "@/components/ui/Card";
import { MethodNote } from "@/components/ui/Section";
import { Table, type Column } from "@/components/ui/Table";
import { DefinitionList, type DefinitionRow } from "./DefinitionList";
import { REF_PROTOCOL_CONFIG, refBlock, refPredBlock } from "./provenanceRefs";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/**
 * Measured issuance: the supply jump at each epoch boundary read from block headers, annualised by
 * the measured epoch wall time, against the nominal `max_inflation_rate x total_supply`.
 */
export function IssuanceCard({ rpc }: { rpc: NearOnchainTruth | null | undefined }) {
  const ep = rpc?.epoch_issuance ?? null;
  const epochRef = refBlock(ep?.epoch_start_height);
  const nominalAnnual = ep?.nominal_annual_issuance_near ?? null;
  const measuredAnnual = ep?.implied_annual_issuance_near ?? null;
  const gap = finite(measuredAnnual) && finite(nominalAnnual) ? measuredAnnual - nominalAnnual : null;
  const gapPct = finite(gap) && finite(nominalAnnual) && nominalAnnual !== 0 ? gap / nominalAnnual : null;
  const measuredDaily = rpc?.measured_daily_issuance_near ?? (finite(measuredAnnual) ? measuredAnnual / 365.25 : null);
  const nominalDaily = rpc?.gross_daily_issuance_near ?? null;
  const burn = ep?.net_burn_per_epoch_near ?? null;
  const burnPerDay = finite(burn) && finite(ep?.epochs_per_year) ? (-burn * ep!.epochs_per_year!) / 365.25 : null;
  const jumps: EpochIssuanceJump[] = Array.isArray(ep?.jumps) ? ep!.jumps : [];
  const tsFor = (height: number): string | null => {
    if (!ep) return null;
    if (height === ep.epoch_start_height) return ep.epoch_start_timestamp_utc ?? null;
    if (height === ep.prev_epoch_start_height) return ep.prev_epoch_start_timestamp_utc ?? null;
    return null;
  };

  const columns: Column<EpochIssuanceJump>[] = [
    {
      key: "height",
      header: "Epoch start block",
      render: (j) => (
        <a href={explorerBlockUrl(j.height)} target="_blank" rel="noreferrer" className="tnum text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent" title={j.hash}>
          {`#${fmtInt(j.height)}`}
        </a>
      ),
    },
    { key: "ts", header: "Time (UTC)", render: (j) => <span className="text-muted">{fmtUtc(tsFor(j.height))}</span> },
    { key: "minted", header: "Minted", numeric: true, render: (j) => fmtNear(j.minted_near, { decimals: 2 }) },
    {
      key: "records",
      header: "Source",
      render: (j) => {
        const a = refBlock(j.height);
        return a ? <ProvenanceBadge source={a.source} name={a.name} /> : null;
      },
    },
  ];

  const capOk = finite(ep?.implied_annual_inflation_rate) && finite(rpc?.max_inflation_rate);
  const rows: DefinitionRow[] = ep
    ? [
        { key: "daily", term: "Measured daily issuance", note: "The model's issuance base", value: finite(measuredDaily) ? `${fmtNear(measuredDaily)}/day` : NA },
        { key: "nominal-daily", term: "Nominal daily issuance", note: `${fmtPct(rpc?.max_inflation_rate, { decimals: 2 })} cap × total supply`, value: finite(nominalDaily) ? `${fmtNear(nominalDaily)}/day` : NA },
        {
          key: "svrn-daily",
          term: `Daily issuance at the SVRN ${fmtPct(rpc?.svrn_target_inflation_used, { decimals: 2 })} target`,
          note: "Assumed governance target",
          value: finite(rpc?.gross_daily_issuance_svrn_near) ? `${fmtNear(rpc!.gross_daily_issuance_svrn_near)}/day` : NA,
        },
        { key: "minted", term: "Minted per epoch", note: finite(ep.prev_minted_per_epoch_near) ? `Previous epoch ${fmtNear(ep.prev_minted_per_epoch_near, { decimals: 1 })}` : undefined, value: fmtNear(ep.minted_per_epoch_near, { decimals: 1 }) },
        {
          key: "duration",
          term: "Epoch duration",
          note: finite(ep.avg_block_time_s) ? `${fmtNum(ep.avg_block_time_s, { decimals: 3 })} s blocks over ${fmtInt(rpc?.epoch_length_blocks)} blocks` : undefined,
          value: finite(ep.epoch_duration_hours) ? `${fmtNum(ep.epoch_duration_hours, { decimals: 2 })} h` : NA,
        },
        { key: "annual", term: "Measured annual issuance", note: finite(ep.epochs_per_year) ? `${fmtNum(ep.epochs_per_year, { decimals: 1 })} epochs a year` : undefined, value: fmtNearCompact(measuredAnnual) },
        {
          key: "gap",
          term: "Measured minus nominal",
          note: finite(gapPct) ? `${fmtPct(gapPct, { signed: true, decimals: 2 })} of nominal` : undefined,
          value: fmtNearCompact(gap, { signed: true }),
        },
        {
          key: "inflation",
          term: "Implied annual inflation",
          note: `Protocol cap ${fmtPct(rpc?.max_inflation_rate, { decimals: 2 })}`,
          value: fmtPct(ep.implied_annual_inflation_rate, { decimals: 3 }),
          valueClassName: capOk && ep.implied_annual_inflation_rate! > rpc!.max_inflation_rate ? "text-crimson" : undefined,
        },
        {
          key: "burn",
          term: "Net burn within the epoch",
          note: finite(burnPerDay) ? `About ${fmtNear(burnPerDay)}/day of gas burned` : "Negative means gas burned",
          value: fmtNear(burn, { decimals: 1, signed: true }),
        },
      ]
    : [];

  return (
    <Card
      title="Measured issuance"
      subtitle="nearcore mints once per epoch. The supply jump at each epoch boundary, annualised by measured epoch time, is the issuance the model uses."
      actions={epochRef ? <ProvenanceBadge source={epochRef.source} name={epochRef.name} /> : null}
    >
      {!ep ? (
        <p className="text-[13.5px] text-muted">The collector did not measure an epoch boundary in this snapshot, so there is no measured issuance to show.</p>
      ) : (
        <div className="space-y-6">
          <DefinitionList rows={rows} />
          <Table<EpochIssuanceJump> columns={columns} rows={jumps} rowKey={(j) => String(j.height)} caption="Epoch boundaries read" emptyText="No epoch-boundary jumps recorded" />
          <MethodNote>
            <p>{ep.method_note ?? <code>near_rpc.epoch_issuance.method_note</code>}</p>
            <p>
              Minted = <code>total_supply(epoch start) − total_supply(previous block)</code>; epochs per year = <code>365.25 × 24 / epoch_duration_hours</code>; measured annual ={" "}
              <code>minted_per_epoch × epochs_per_year</code>; nominal annual = <code>max_inflation_rate × total_supply</code>. Fields: <code>near_rpc.epoch_issuance</code>,{" "}
              <code>near_rpc.measured_daily_issuance_near</code>, <code>near_rpc.gross_daily_issuance_near</code>, <code>near_rpc.gross_daily_issuance_svrn_near</code>.
            </p>
            <div>
              Epoch {finite(rpc?.epoch_height) ? fmtInt(rpc!.epoch_height) : NA}, epoch id <code>{fmtHash(rpc?.epoch_id, 12)}</code>, {fmtInt(rpc?.epoch_length_blocks)} blocks per epoch, protocol v
              {fmtInt(rpc?.protocol_version)}. Gas burn is read from the block before each epoch start:{" "}
              {jumps.map((j) => {
                const b = refPredBlock(j.height);
                return b ? <ProvenanceBadge key={j.height} source={b.source} name={b.name} label={`#${fmtInt(j.height)} predecessor`} className="mr-2" /> : null;
              })}
              Inflation cap: <ProvenanceBadge source={REF_PROTOCOL_CONFIG.source} name={REF_PROTOCOL_CONFIG.name} label="protocol config" />.
            </div>
          </MethodNote>
        </div>
      )}
    </Card>
  );
}
