"use client";

import { cn } from "@/lib/cn";
import { fmtBytes, fmtMs, fmtUtc } from "@/lib/format";
import { recordStatusLabel } from "@/lib/manifestIndex";
import type { RawRecord } from "@/lib/types";
import { Tooltip } from "@/components/ui/Tooltip";
import { useManifestIndex } from "./ManifestContext";

export interface ProvenanceRef {
  source: string;
  name: string;
}

export type ProvenanceBadgeProps = ({ record: RawRecord } | ProvenanceRef) & {
  /** override the chip text (default: the record source) */
  label?: string;
  size?: "xs" | "sm";
  className?: string;
};

/** Display names for manifest sources. */
export const SOURCE_NAME: Record<string, string> = {
  near_rpc: "NEAR RPC",
  near_rpc_archival: "NEAR archival RPC",
  nearstats: "NearStats",
  defillama: "DefiLlama",
  nearblocks: "NearBlocks",
  oneclick: "1Click",
  "1click": "1Click",
  relay: "Relay",
  lifi: "LI.FI",
  across: "Across",
  coingecko: "CoinGecko",
};

export function sourceName(source: string): string {
  return SOURCE_NAME[source] ?? source;
}

/**
 * Quiet source attribution under or beside a figure: the source name in small grey type with a
 * dotted underline. Hover or focus shows the raw-payload record (URL, SHA-256, bytes, latency,
 * fetch time). Accepts a RawRecord directly or a (source, name) pair resolved against the
 * manifest in context. A failed fetch is marked in red; a missing record says so.
 */
export function ProvenanceBadge(props: ProvenanceBadgeProps) {
  const index = useManifestIndex();
  const record: RawRecord | null = "record" in props ? props.record : index.get(props.source, props.name);
  const wantedName = "record" in props ? props.record.name : props.name;
  const wantedSource = "record" in props ? props.record.source : props.source;
  const size = props.size ?? "xs";
  const text = size === "xs" ? "text-[12px]" : "text-[13px]";

  if (!record) {
    return (
      <Tooltip wide content={<div>No manifest record for {sourceName(wantedSource)} / <span className="font-mono text-[11.5px]">{wantedName}</span>. This value cannot be traced to a raw payload in this snapshot.</div>}>
        <span tabIndex={0} className={cn("inline-flex cursor-help items-center gap-1 text-dim", text, props.className)}>
          source not recorded
        </span>
      </Tooltip>
    );
  }

  return (
    <Tooltip wide content={<RecordDetails record={record} />}>
      <span
        tabIndex={0}
        className={cn(
          "inline-flex cursor-help items-center gap-1 whitespace-nowrap underline decoration-dotted underline-offset-[3px]",
          record.ok ? "text-dim decoration-border-strong hover:text-muted" : "text-crimson decoration-crimson/50",
          text,
          props.className,
        )}
      >
        {props.label ?? sourceName(record.source)}
        {record.ok ? null : <span className="no-underline"> (failed)</span>}
      </span>
    </Tooltip>
  );
}

/** Record details as phrasing content (spans), so a source link stays valid inside a paragraph. */
export function RecordDetails({ record }: { record: RawRecord }) {
  return (
    <span className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12px]">
      <span className="text-muted">Source</span>
      <span className="font-medium text-ink">{sourceName(record.source)}</span>
      <span className="text-muted">Record</span>
      <span className="break-all font-mono text-[11.5px] text-ink">{record.name}</span>
      <span className="text-muted">Status</span>
      <span className={record.ok ? "text-emerald" : "text-crimson"}>
        {recordStatusLabel(record)}
        {record.error ? <span className="ml-1 text-crimson">{record.error}</span> : null}
      </span>
      <span className="text-muted">SHA-256</span>
      <span className="break-all font-mono text-[11.5px] text-ink" title={record.sha256}>
        {record.sha256}
      </span>
      <span className="text-muted">Size</span>
      <span className="tnum">{fmtBytes(record.bytes)}</span>
      <span className="text-muted">Latency</span>
      <span className="tnum">{fmtMs(record.latency_ms)}{record.attempts && record.attempts > 1 ? ` (${record.attempts} attempts)` : ""}</span>
      <span className="text-muted">Fetched</span>
      <span className="tnum">{fmtUtc(record.fetched_at_utc, { seconds: true })}</span>
      <span className="text-muted">Request</span>
      <span className="break-all">
        <a href={record.url} target="_blank" rel="noreferrer" className="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent">
          {record.method} {record.url}
        </a>
      </span>
      {record.raw_path ? (
        <>
          <span className="text-muted">Raw file</span>
          <span className="break-all font-mono text-[11.5px] text-muted">{record.raw_path}</span>
        </>
      ) : null}
      {record.note ? (
        <>
          <span className="text-muted">Note</span>
          <span className="text-muted">{record.note}</span>
        </>
      ) : null}
    </span>
  );
}
