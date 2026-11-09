import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Badge, Card, Stat, Table, Tooltip, type Column } from "@/components/ui";
import { MethodNote, StatGrid } from "@/components/ui/Section";
import { fmtInt, fmtNum, fmtUsdCompact, fmtUtc } from "@/lib/format";
import type { PeerComp, PeerComps, SotpValuation } from "@/lib/types";
import { mult } from "./fmt";
import { REF, peerFeesRef, peerRevenueRef } from "./refs";

type Group = "peer" | "near_component" | "near_combined";
type Row = PeerComp & { group: Group };

const GROUP_LABEL: Record<Group, string> = { peer: "Peer", near_component: "NEAR component", near_combined: "NEAR combined" };

function Definition({ row }: { row: Row }) {
  const rev = row.revenue_methodology;
  const fees = row.fees_methodology;
  if (!rev && !fees) return <span className="text-dim">n/a</span>;
  return (
    <Tooltip
      wide
      side="left"
      content={
        <div className="flex flex-col gap-1.5">
          {fees ? (
            <div>
              <span className="text-muted">Fees: </span>
              {fees}
            </div>
          ) : null}
          {rev ? (
            <div>
              <span className="text-muted">Revenue: </span>
              {rev}
            </div>
          ) : null}
        </div>
      }
    >
      <span tabIndex={0} className="cursor-help text-[12.5px] text-muted underline decoration-dotted underline-offset-2 hover:text-ink">
        Definition
      </span>
    </Tooltip>
  );
}

/** Peer comps: DefiLlama fees / revenue (30d, annualized) and FDV multiples for SOL, ETH, HYPE vs NEAR L1 + NEAR Intents. */
export function PeerCompsTable({ comps, sotp }: { comps: PeerComps | null | undefined; sotp: SotpValuation }) {
  if (!comps) {
    return (
      <Card title="Peer multiples">
        <p className="text-[13.5px] text-muted">Not available: the comps collector failed (DefiLlama or CoinGecko); see the snapshot warnings.</p>
      </Card>
    );
  }
  const cal = sotp.calibration;
  const rows: Row[] = [
    ...(comps.peers ?? []).map((p) => ({ ...p, group: "peer" as Group })),
    ...(comps.near_components ?? []).map((p) => ({ ...p, group: "near_component" as Group })),
    ...(comps.near_combined ? [{ ...comps.near_combined, group: "near_combined" as Group }] : []),
  ];
  const columns: Column<Row>[] = [
    {
      key: "asset",
      header: "Asset",
      render: (r) => (
        <div className="min-w-[10rem]">
          <div className="text-ink">
            <span className="font-medium">{r.symbol}</span> <span className="text-muted">{r.label ?? r.slug}</span>
          </div>
          <div className="text-[12px] text-dim">{GROUP_LABEL[r.group]}</div>
        </div>
      ),
    },
    { key: "fees30", header: "Fees, 30 days", numeric: true, render: (r) => fmtUsdCompact(r.fees_30d_usd) },
    { key: "rev30", header: "Revenue, 30 days", numeric: true, render: (r) => fmtUsdCompact(r.revenue_30d_usd) },
    { key: "revA", header: "Revenue, annualized", numeric: true, render: (r) => fmtUsdCompact(r.annualized_revenue_usd) },
    { key: "fees1y", header: "Fees, trailing year", numeric: true, render: (r) => fmtUsdCompact(r.fees_1y_usd) },
    { key: "fdv", header: "FDV", numeric: true, render: (r) => fmtUsdCompact(r.fdv_usd) },
    { key: "f2f", header: "FDV / fees", numeric: true, render: (r) => mult(r.fdv_to_fees) },
    { key: "f2r", header: "FDV / revenue", numeric: true, render: (r) => <span className="font-medium text-ink">{mult(r.fdv_to_revenue)}</span> },
    { key: "def", header: "Revenue basis", render: (r) => <Definition row={r} /> },
    {
      key: "src",
      header: "Source",
      render: (r) => {
        const slug = r.group === "near_combined" ? (r.components ?? ["near-intents"])[0] : r.slug;
        return <ProvenanceBadge {...peerRevenueRef(slug)} label="DefiLlama" />;
      },
    },
  ];

  const raw = cal?.terminal_multiple_raw;
  const used = cal?.terminal_multiple_used;
  const floor = sotp.inputs?.terminal_multiple_floor?.value;
  const cap = sotp.inputs?.terminal_multiple_cap?.value;
  const clipped = cal?.terminal_multiple_clipped === true;
  const cgOk = comps.fetch_status?.coingecko_markets_ok === true;
  const nFees = comps.fetch_status?.defillama_fees_ok?.length ?? 0;

  return (
    <Card
      title="Peer multiples"
      subtitle={
        clipped
          ? `Peers trade at a median ${mult(raw)} FDV to annualized revenue, far outside the model's ${mult(floor, { decimals: 0 })} to ${mult(cap, { decimals: 0 })} guardrail; the terminal value uses ${mult(used)}.`
          : `Peers trade at a median ${mult(raw)} FDV to annualized revenue, inside the model's ${mult(floor, { decimals: 0 })} to ${mult(cap, { decimals: 0 })} guardrail; the terminal value uses it as is.`
      }
      actions={
        !cgOk || nFees === 0 ? (
          <Badge variant="error" dot>
            {!cgOk ? "CoinGecko fetch failed" : "No DefiLlama fee series"}
          </Badge>
        ) : null
      }
    >
      <div className="space-y-6">
        <StatGrid cols={3}>
          <Stat label="Median FDV / revenue, excl. NEAR" value={comps.median_fdv_to_revenue_ex_near} format={(v) => mult(v)} hint={`${fmtInt(comps.n_peers_in_revenue_median)} peers`} />
          <Stat label="Median FDV / fees, excl. NEAR" value={comps.median_fdv_to_fees_ex_near} format={(v) => mult(v)} hint={`${fmtInt(comps.n_peers_in_fees_median)} peers`} />
          <Stat
            label={
              <span className="inline-flex flex-wrap items-center gap-2">
                Terminal multiple used
                {clipped ? (
                  <Badge variant="warn" dot>
                    Clipped
                  </Badge>
                ) : null}
              </span>
            }
            value={used}
            format={(v) => mult(v)}
            hint={clipped ? "Set to the cap; L1 revenue multiples are a poor comp for a clearinghouse fee stream" : "Peer median, inside the guardrail"}
          />
        </StatGrid>
        <Table<Row> columns={columns} rows={rows} rowKey={(r) => `${r.group}:${r.slug}`} rowClassName={(r) => (r.group === "peer" ? undefined : "bg-surface-2/60")} />
      </div>
      <MethodNote className="mt-6">
        <p>
          Revenue follows each protocol&apos;s DefiLlama definition (hover &quot;Definition&quot;): burned base fees for ETH, user base fees for SOL, Assistance Fund buybacks for HYPE, swept revenue wallets for NEAR Intents. Annualized = 30-day total × 365 / 30{comps.annualization ? ` (${comps.annualization})` : ""}. FDV from CoinGecko <code>fully_diluted_valuation</code>. Fetched {fmtUtc(comps.fetched_at_utc, { seconds: true })}; CoinGecko {cgOk ? "ok" : "failed"}, DefiLlama {fmtInt(nFees)} fee series.
        </p>
        <p>
          Additional per-row figures: {rows.map((r) => `${r.symbol} ${r.label ?? r.slug} annualized fees ${fmtUsdCompact(r.annualized_fees_usd)}, price ${r.price_usd === null || r.price_usd === undefined ? "n/a" : `$${fmtNum(r.price_usd, { decimals: r.price_usd < 10 ? 3 : 2 })}`}`).join("; ")}.
        </p>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
          Raw payloads:
          {rows.flatMap((r) => (r.group === "near_combined" ? [] : [<ProvenanceBadge key={`f-${r.slug}`} {...peerFeesRef(r.slug)} label={`fees ${r.slug}`} />]))}
          <ProvenanceBadge {...REF.coingeckoMarkets} label="CoinGecko markets" />
        </p>
        <p>
          Fields: <code>comps.peers</code>, <code>comps.near_components</code>, <code>comps.near_combined</code>, <code>comps.median_fdv_to_revenue_ex_near</code>, <code>comps.median_fdv_to_fees_ex_near</code>, <code>sotp.calibration.terminal_multiple_raw</code> / <code>_used</code>, <code>sotp.inputs.terminal_multiple_floor</code> / <code>_cap</code>.
        </p>
      </MethodNote>
    </Card>
  );
}
