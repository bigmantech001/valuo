import type { ReactNode } from "react";
import { Table, type Column } from "@/components/ui";
import { fmtAddress, fmtHash, fmtInt, fmtPct } from "@/lib/format";
import { explorerAccountUrl, explorerTxUrl } from "@/lib/manifestIndex";
import { COLORS } from "@/lib/theme";
import type { IntentsForensics } from "@/lib/types";
import { CALLER_CLASS_COLOR, callerClassLabel } from "./benchUtil";

export const LINK = "text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent";

export interface ShareRow {
  account_id: string;
  share: number;
  count: number;
  sublabel?: string;
  color?: string;
  example_tx_hash?: string | null;
}

/** Long implicit (64-hex / 0x) account ids are shortened for display; the link and title keep the full id. */
function accountLabel(id: string): string {
  return id.length > 30 ? fmtAddress(id, 8, 6) : id;
}

/**
 * Horizontal share bars that double as a table: account (NearBlocks link), share bar, share,
 * count, and an example transaction. Plain HTML so it reflows on narrow screens.
 */
export function ShareBars({ rows, countLabel, base, empty }: { rows: ShareRow[]; countLabel: string; base: string; empty: ReactNode }) {
  if (!rows.length) return <p className="text-[13px] text-dim">{empty}</p>;
  const max = Math.max(1e-9, ...rows.map((r) => r.share));
  return (
    <div className="w-full overflow-x-auto valuo-scroll">
      <table className="w-full min-w-[30rem] border-collapse text-[13.5px]">
        <thead>
          <tr>
            <th scope="col" className="border-b border-ink/80 px-2 py-2 pl-0 text-left text-[12.5px] font-medium text-muted">
              Account
            </th>
            <th scope="col" className="w-[38%] border-b border-ink/80 px-2 py-2 text-left text-[12.5px] font-medium text-muted">
              Share
            </th>
            <th scope="col" className="border-b border-ink/80 px-2 py-2 text-right text-[12.5px] font-medium text-muted">
              {countLabel}
            </th>
            <th scope="col" className="border-b border-ink/80 px-2 py-2 pr-0 text-right text-[12.5px] font-medium text-muted">
              Example tx
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.account_id} className="border-b border-border last:border-b-0">
              <td className="max-w-[14rem] px-2 py-2 pl-0 align-top">
                <a href={explorerAccountUrl(r.account_id, base)} target="_blank" rel="noreferrer" className={`break-all ${LINK}`} title={r.account_id}>
                  {accountLabel(r.account_id)}
                </a>
                {r.sublabel ? <div className="text-[12px] text-dim">{r.sublabel}</div> : null}
              </td>
              <td className="px-2 py-2 align-top">
                <div className="flex items-center gap-2">
                  <div className="h-2.5 flex-1 rounded-sm bg-surface-2">
                    <div className="h-2.5 rounded-sm" style={{ width: `${(r.share / max) * 100}%`, backgroundColor: r.color ?? COLORS.ink }} />
                  </div>
                  <span className="tnum w-12 text-right text-ink">{fmtPct(r.share, { decimals: 1 })}</span>
                </div>
              </td>
              <td className="tnum px-2 py-2 text-right align-top">{fmtInt(r.count)}</td>
              <td className="px-2 py-2 pr-0 text-right align-top">
                {r.example_tx_hash ? (
                  <a href={explorerTxUrl(r.example_tx_hash, base)} target="_blank" rel="noreferrer" className={`tnum ${LINK}`} title={r.example_tx_hash}>
                    {fmtHash(r.example_tx_hash, 8)}
                  </a>
                ) : (
                  <span className="text-dim">n/a</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export interface CallerBreakdownProps {
  f: IntentsForensics;
}

/** External callers of intents.near by receipt share, coloured by caller class, with NearBlocks links. */
export function CallerBreakdown({ f }: CallerBreakdownProps) {
  const base = f.explorer_base || "https://nearblocks.io";
  const rows: ShareRow[] = [...f.callers]
    .sort((a, b) => b.share - a.share || b.receipts - a.receipts)
    .map((c) => ({ account_id: c.account_id, share: c.share, count: c.receipts, sublabel: callerClassLabel(c.cls), color: CALLER_CLASS_COLOR[c.cls], example_tx_hash: c.example_tx_hash ?? null }));
  return <ShareBars rows={rows} countLabel="Receipts" base={base} empty="No external callers in the sample." />;
}

interface MethodRow {
  method: string;
  receipts: number;
  share: number | null;
}

/** Method mix over all sampled receipts (including system and self-receipts). */
export function MethodMix({ f }: { f: IntentsForensics }) {
  const methods: MethodRow[] = Object.entries(f.method_mix)
    .sort((a, b) => b[1] - a[1])
    .map(([method, receipts]) => ({ method, receipts, share: f.receipts_sampled > 0 ? receipts / f.receipts_sampled : null }));
  const total = methods.reduce((s, m) => s + m.receipts, 0);
  const cols: Column<MethodRow>[] = [
    { key: "method", header: "Method", render: (m) => <span className="font-mono text-[12.5px] text-ink">{m.method}</span> },
    { key: "receipts", header: "Receipts", numeric: true, render: (m) => fmtInt(m.receipts) },
    { key: "share", header: "Share", numeric: true, render: (m) => fmtPct(m.share, { decimals: 1 }) },
  ];
  return (
    <Table
      columns={cols}
      rows={methods}
      rowKey={(m) => m.method}
      stickyHeader={false}
      emptyText="No method data in the sample"
      footer={total !== f.receipts_sampled ? `Method counts sum to ${fmtInt(total)} against ${fmtInt(f.receipts_sampled)} receipts; some receipts carry no method.` : undefined}
    />
  );
}
