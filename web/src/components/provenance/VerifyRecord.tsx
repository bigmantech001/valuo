"use client";

import { Badge } from "@/components/ui/Badge";
import { fmtBytes, fmtInt, fmtMs, fmtUtc } from "@/lib/format";
import type { RawRecord } from "@/lib/types";
import { fmtNumericChange, sha256HexBrowser, type RawHashResult, type RefetchRefusal, type RefetchResponse } from "@/lib/verify";

/* ------------------------------------------------------------------------------------------- actions */

/** Fetch the stored raw bytes for a record from /api/raw and SHA-256 them in this browser. */
export async function rehashInBrowser(r: RawRecord, signal?: AbortSignal): Promise<RawHashResult> {
  const base = { source: r.source, name: r.name, expected: r.sha256 };
  if (!r.raw_path) {
    return { ...base, actual: null, bytes: null, matches: null, error: "No bytes were stored: the request failed before a response arrived." };
  }
  try {
    const res = await fetch(`/api/raw?source=${encodeURIComponent(r.source)}&name=${encodeURIComponent(r.name)}`, { cache: "no-store", signal });
    if (!res.ok) {
      const msg = await res.json().then((j: { error?: string }) => j.error, () => null);
      return { ...base, actual: null, bytes: null, matches: null, error: msg ?? `HTTP ${res.status} from /api/raw` };
    }
    const buf = await res.arrayBuffer();
    const actual = await sha256HexBrowser(buf);
    return { ...base, actual, bytes: buf.byteLength, matches: actual === r.sha256 };
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    return { ...base, actual: null, bytes: null, matches: null, error: e instanceof Error ? e.message : String(e) };
  }
}

export type RefetchOutcome = { ok: true; data: RefetchResponse } | { ok: false; error: string };

export async function refetchLive(r: RawRecord): Promise<RefetchOutcome> {
  try {
    const res = await fetch("/api/refetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: r.source, name: r.name }),
      cache: "no-store",
    });
    const json = (await res.json()) as RefetchResponse | RefetchRefusal;
    if (!res.ok) return { ok: false, error: (json as RefetchRefusal).error ?? `HTTP ${res.status}` };
    return { ok: true, data: json as RefetchResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) };
  }
}

/**
 * Whether /api/refetch can re-issue this record exactly. GET: the recorded URL. POST: only NEAR JSON-RPC, whose
 * body the server rebuilds and checks against request_body_sha256; quote POST bodies are stored only as a hash.
 */
export function refetchSupport(r: RawRecord): { ok: true } | { ok: false; reason: string } {
  const m = r.method.toUpperCase();
  if (m === "GET") return { ok: true };
  if (m === "POST" && r.source.startsWith("near_rpc")) return { ok: true };
  if (m === "POST") return { ok: false, reason: "The request body was not stored (only its SHA-256), so this POST cannot be re-issued exactly. Use the live quote race instead." };
  return { ok: false, reason: `${m} requests are not re-fetched.` };
}

/* ---------------------------------------------------------------------------------------- result views */

function HashLine({ label, hash }: { label: string; hash: string | null }) {
  return (
    <>
      <dt className="text-muted">{label}</dt>
      <dd className="break-all font-mono text-[11.5px] leading-snug text-ink">{hash ?? "n/a"}</dd>
    </>
  );
}

/** Outcome of re-hashing the stored bytes in the browser. */
export function RehashResultView({ result, superseded }: { result: RawHashResult; superseded?: boolean }) {
  if (result.matches === null) {
    return (
      <div className="rounded-md border border-border bg-surface-2/60 px-3 py-2 text-[12.5px] leading-snug text-muted">
        Not checked: {result.error ?? "no bytes"}
      </div>
    );
  }
  return (
    <div className={result.matches ? "rounded-md border border-emerald/30 bg-emerald/5 px-3 py-2" : "rounded-md border border-crimson/30 bg-crimson/5 px-3 py-2"}>
      <div className={result.matches ? "text-[12.5px] font-medium text-emerald" : "text-[12.5px] font-medium text-crimson"}>
        {result.matches ? "Matches the manifest" : "Does not match"}
        <span className="ml-1.5 font-normal text-muted">
          {fmtBytes(result.bytes)} hashed in this browser
        </span>
      </div>
      <dl className="mt-1.5 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-[12px]">
        <HashLine label="Manifest" hash={result.expected} />
        <HashLine label="Browser" hash={result.actual} />
      </dl>
      {!result.matches && superseded ? (
        <p className="mt-1.5 text-[12px] leading-snug text-muted">A later fetch of the same record overwrote this raw file; the latest row for this name is the one the file should match.</p>
      ) : null}
    </div>
  );
}

/** Outcome of re-issuing the original request now and comparing with the stored body. */
export function RefetchResultView({ outcome }: { outcome: RefetchOutcome }) {
  if (!outcome.ok) {
    return <div className="rounded-md border border-crimson/30 bg-crimson/5 px-3 py-2 text-[12.5px] leading-snug text-crimson">Live fetch refused or failed: {outcome.error}</div>;
  }
  const d = outcome.data;
  if (d.sha256 === null) {
    return <div className="rounded-md border border-crimson/30 bg-crimson/5 px-3 py-2 text-[12.5px] leading-snug text-crimson">Live fetch failed: {d.error ?? "no response"}</div>;
  }
  const diff = d.diff_summary;
  return (
    <div className="rounded-md border border-border bg-surface-2/60 px-3 py-2 text-[12.5px] leading-snug">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Badge variant={d.status !== null && d.status >= 200 && d.status < 300 ? "neutral" : "error"} size="xs">
          HTTP {d.status ?? "n/a"}
        </Badge>
        <span className={d.changed ? "font-medium text-ink" : "font-medium text-emerald"}>
          {d.changed ? "Changed since the snapshot" : "Byte-identical to the stored payload"}
        </span>
        <span className="tnum text-muted">
          {fmtBytes(d.bytes)} · {fmtMs(d.latency_ms)} · {fmtUtc(d.fetched_at, { seconds: true })}
        </span>
      </div>
      <dl className="mt-1.5 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-[12px]">
        <HashLine label="Stored" hash={d.stored_sha256} />
        <HashLine label="Live now" hash={d.sha256} />
      </dl>
      {d.request_body_verified ? <p className="mt-1.5 text-[12px] text-muted">JSON-RPC body rebuilt from the record name; it hashes to the manifest&apos;s request_body_sha256.</p> : null}
      {d.note ? <p className="mt-1 text-[12px] text-muted">{d.note}.</p> : null}
      {d.error ? <p className="mt-1 text-[12px] text-crimson">{d.error}</p> : null}
      {diff ? <DiffView diff={diff} storedAt={d.stored_fetched_at} /> : null}
    </div>
  );
}

function DiffView({ diff, storedAt }: { diff: NonNullable<RefetchResponse["diff_summary"]>; storedAt: string }) {
  if (diff.kind === "non-json") return <p className="mt-1.5 text-[12px] text-muted">Body is not JSON on one side; no structural diff.</p>;
  const nothing = !diff.added_keys.length && !diff.removed_keys.length && !diff.changed_numeric_total && !diff.array_length_changes.length && !diff.changed_other_total;
  return (
    <div className="mt-2 border-t border-border pt-1.5 text-[12px]">
      <div className="text-muted">Stored {fmtUtc(storedAt)} → live now</div>
      {nothing ? <p className="mt-1 text-muted">No structural change within depth {diff.max_depth}: only formatting, ordering or deep values differ.</p> : null}
      {diff.added_keys.length ? (
        <p className="mt-1">
          <span className="text-muted">Keys added:</span> <span className="font-mono text-[11.5px]">{diff.added_keys.join(", ")}</span>
        </p>
      ) : null}
      {diff.removed_keys.length ? (
        <p className="mt-1">
          <span className="text-muted">Keys removed:</span> <span className="font-mono text-[11.5px]">{diff.removed_keys.join(", ")}</span>
        </p>
      ) : null}
      {diff.changed_numeric.length ? (
        <ul className="mt-1 space-y-0.5">
          {diff.changed_numeric.map((c) => (
            <li key={c.path} className="tnum font-mono text-[11.5px] text-ink" title={fmtNumericChange(c)}>
              <span className="break-all">{c.path}</span> <span className="whitespace-nowrap">{fmtNumericChange({ ...c, path: "" }).trim()}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {diff.array_length_changes.length ? (
        <ul className="mt-1 space-y-0.5">
          {diff.array_length_changes.map((c) => (
            <li key={`len:${c.path}`} className="tnum break-all font-mono text-[11.5px] text-muted">
              {c.path} length {fmtInt(c.old)} → {fmtInt(c.new)}
            </li>
          ))}
        </ul>
      ) : null}
      {diff.changed_numeric_total > diff.changed_numeric.length || diff.changed_other_total || diff.truncated ? (
        <p className="mt-1 text-muted">
          {diff.changed_numeric_total > diff.changed_numeric.length ? `${fmtInt(diff.changed_numeric_total)} numeric fields changed in total. ` : ""}
          {diff.changed_other_total ? `${fmtInt(diff.changed_other_total)} text fields changed. ` : ""}
          {diff.truncated ? `Compared to depth ${diff.max_depth} and the first 50 items of each array.` : ""}
        </p>
      ) : null}
    </div>
  );
}
