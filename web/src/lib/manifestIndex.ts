import type { Manifest, RawRecord } from "./types";

/**
 * Lookup helpers over `manifest.records`. The ledger appends records in fetch order, so when a
 * (source, name) pair appears more than once the most recent record wins (same rule as
 * `ProvenanceLedger.get`). Pure functions; safe on client and server.
 */

export interface ManifestIndex {
  manifest: Manifest | null;
  records: RawRecord[];
  /** Most recent record for (source, name), else null. */
  get(source: string, name: string): RawRecord | null;
  bySource(source: string): RawRecord[];
  /** Records whose name starts with `prefix` (e.g. "quote:" or "view_account:"). */
  byNamePrefix(prefix: string, source?: string): RawRecord[];
  find(predicate: (r: RawRecord) => boolean): RawRecord[];
  /** Case-insensitive substring match over source, name, url, error. */
  search(text: string): RawRecord[];
  sources(): string[];
  failures(): RawRecord[];
  size: number;
}

export function recordKey(source: string, name: string): string {
  return `${source}\u0000${name}`;
}

export function buildManifestIndex(manifest: Manifest | null | undefined): ManifestIndex {
  const records = manifest?.records ?? [];
  const latest = new Map<string, RawRecord>();
  const bySrc = new Map<string, RawRecord[]>();
  for (const r of records) {
    latest.set(recordKey(r.source, r.name), r);
    const list = bySrc.get(r.source);
    if (list) list.push(r);
    else bySrc.set(r.source, [r]);
  }
  return {
    manifest: manifest ?? null,
    records,
    size: records.length,
    get: (source, name) => latest.get(recordKey(source, name)) ?? null,
    bySource: (source) => bySrc.get(source) ?? [],
    byNamePrefix: (prefix, source) =>
      records.filter((r) => r.name.startsWith(prefix) && (source === undefined || r.source === source)),
    find: (predicate) => records.filter(predicate),
    search: (text) => {
      const q = text.trim().toLowerCase();
      if (!q) return records;
      return records.filter(
        (r) =>
          r.source.toLowerCase().includes(q) ||
          r.name.toLowerCase().includes(q) ||
          r.url.toLowerCase().includes(q) ||
          (r.error ?? "").toLowerCase().includes(q) ||
          r.sha256.startsWith(q),
      );
    },
    sources: () => Array.from(bySrc.keys()).sort(),
    failures: () => records.filter((r) => !r.ok),
  };
}

/** Explorer link for an on-chain object, when a record or value maps to one. */
export const EXPLORER_BASE = "https://nearblocks.io";
export function explorerTxUrl(hash: string, base: string = EXPLORER_BASE): string {
  return `${base}/txns/${hash}`;
}
export function explorerAccountUrl(account: string, base: string = EXPLORER_BASE): string {
  return `${base}/address/${account}`;
}
export function explorerBlockUrl(height: number, base: string = EXPLORER_BASE): string {
  return `${base}/blocks/${height}`;
}

/** Human label for a record's HTTP outcome. */
export function recordStatusLabel(r: RawRecord): string {
  if (r.ok) return r.http_status ? `OK ${r.http_status}` : "OK";
  if (r.http_status) return `FAIL ${r.http_status}`;
  return "FAIL";
}
