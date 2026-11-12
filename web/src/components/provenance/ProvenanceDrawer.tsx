"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { fmtBytes, fmtHash, fmtInt, fmtMs, fmtUtc } from "@/lib/format";
import { buildManifestIndex, recordStatusLabel } from "@/lib/manifestIndex";
import type { Integrity, Manifest, RawRecord } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Table, type Column } from "@/components/ui/Table";
import type { RawHashResult } from "@/lib/verify";
import { sourceName } from "./ProvenanceBadge";
import { RefetchResultView, RehashResultView, refetchLive, refetchSupport, rehashInBrowser, type RefetchOutcome } from "./VerifyRecord";

export interface ProvenanceDrawerProps {
  open: boolean;
  onClose: () => void;
  manifest: Manifest | null;
  /** snapshot-file sha256 recomputed by /api/snapshot, compared with the manifest */
  integrity?: Integrity | null;
}

type StatusFilter = "all" | "ok" | "failed";

const CONTROL = "rounded-md border border-border bg-surface px-2 py-1 text-[13px] text-ink focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/30";

/** The SHA-256 of a record in mono; click copies the full hash. */
function HashCell({ hash }: { hash: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="font-mono text-[12px] text-ink hover:text-accent"
      title={`${hash}\nClick to copy`}
      onClick={() => {
        navigator.clipboard?.writeText(hash).then(
          () => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
          },
          () => undefined,
        );
      }}
    >
      {copied ? "Copied" : fmtHash(hash, 12)}
    </button>
  );
}

/** One plain sentence on whether the snapshot file still matches the hash the manifest recorded. */
function IntegrityStatement({ manifest, integrity }: { manifest: Manifest; integrity: Integrity | null | undefined }) {
  const matches = integrity?.matches;
  const tone = matches === true ? "border-emerald/30 bg-emerald/5" : matches === false ? "border-crimson/30 bg-crimson/5" : "border-border bg-surface-2/60";
  return (
    <div className={cn("rounded-lg border px-5 py-4", tone)}>
      <div className="flex flex-wrap items-center gap-2">
        {matches === true ? (
          <Badge variant="ok" dot size="sm">
            Integrity check passed
          </Badge>
        ) : matches === false ? (
          <Badge variant="error" dot size="sm">
            Integrity check failed
          </Badge>
        ) : (
          <Badge variant="neutral" dot size="sm">
            Integrity not checked
          </Badge>
        )}
      </div>
      <p className="mt-2 text-[14px] leading-relaxed text-ink">
        {matches === true
          ? "The snapshot file on disk hashes to exactly the SHA-256 recorded in the manifest: the numbers in this terminal are the numbers the pipeline wrote."
          : matches === false
            ? "The snapshot file on disk does not hash to the SHA-256 recorded in the manifest: it was edited or regenerated after the manifest was written. Re-run the pipeline before relying on these numbers."
            : "The server did not recompute the snapshot hash for this page load, so the match against the manifest is unknown."}
      </p>
      <dl className="mt-3 grid gap-x-6 gap-y-2 text-[12.5px] sm:grid-cols-[max-content_1fr]">
        <dt className="text-muted">Recorded in manifest</dt>
        <dd className="break-all font-mono text-[12px] text-ink">{manifest.snapshot_sha256}</dd>
        <dt className="text-muted">Recomputed from file</dt>
        <dd className="break-all font-mono text-[12px] text-ink">{integrity?.snapshot_sha256_file ?? "Not checked"}</dd>
        <dt className="text-muted">NEAR block</dt>
        <dd className="break-all font-mono text-[12px] text-muted">
          {fmtInt(manifest.block_height)} · {manifest.block_hash}
        </dd>
        <dt className="text-muted">Snapshot file</dt>
        <dd className="break-all font-mono text-[12px] text-muted">{manifest.snapshot_path}</dd>
      </dl>
    </div>
  );
}

function HashTally({ tally, total, running }: { tally: { match: number; mismatch: number; skipped: number; checked: number }; total: number; running: boolean }) {
  const hashed = tally.match + tally.mismatch;
  const tone = tally.mismatch ? "text-crimson" : tally.match ? "text-emerald" : "text-muted";
  return (
    <p className="tnum mt-3 text-[14px] leading-relaxed" role="status" aria-live="polite">
      <span className={cn("font-medium", tone)}>
        {fmtInt(tally.match)} of {fmtInt(hashed)} payloads match
      </span>
      <span className="text-muted">
        {tally.mismatch ? `; ${fmtInt(tally.mismatch)} do not match the manifest` : ""}
        {tally.skipped ? `; ${fmtInt(tally.skipped)} not checked (no stored bytes)` : ""}
        {running ? `; ${fmtInt(total - tally.checked)} still to hash` : tally.checked < total ? `; ${fmtInt(total - tally.checked)} of ${fmtInt(total)} records not yet checked` : "."}
      </span>
    </p>
  );
}

function RowResults({
  record,
  index,
  hashes,
  live,
  latest,
}: {
  record: RawRecord;
  index: number | undefined;
  hashes: Record<number, RawHashResult>;
  live: Record<number, RefetchOutcome>;
  latest: RawRecord | null;
}) {
  if (index === undefined) return null;
  const h = hashes[index];
  const l = live[index];
  if (!h && !l) return null;
  return (
    <div className="mt-2 space-y-2">
      {h ? <RehashResultView result={h} superseded={latest !== null && latest !== record} /> : null}
      {l ? <RefetchResultView outcome={l} /> : null}
    </div>
  );
}

/** Full manifest: every raw HTTP/RPC exchange behind the snapshot, with its SHA-256. */
export function ProvenanceDrawer({ open, onClose, manifest, integrity }: ProvenanceDrawerProps) {
  const index = useMemo(() => buildManifestIndex(manifest), [manifest]);

  // Deep link: ?verify=1 opens the drawer, ?verify=rehash also re-hashes every payload. Handled here so the
  // header button (ProvenanceBar) keeps owning the normal open state.
  const [linked, setLinked] = useState<"open" | "rehash" | null>(null);
  useEffect(() => {
    const v = new URLSearchParams(window.location.search).get("verify");
    if (v === "1" || v === "open" || v === "rehash") setLinked(v === "rehash" ? "rehash" : "open"); // read the URL once after hydration
  }, []);
  const isOpen = open || linked !== null;
  const close = useCallback(() => {
    if (linked !== null) {
      setLinked(null);
      const url = new URL(window.location.href);
      url.searchParams.delete("verify");
      window.history.replaceState(window.history.state, "", url);
    }
    onClose();
  }, [linked, onClose]);

  // Results are keyed by the record's position in manifest.records (a (source, name) pair can repeat).
  const position = useMemo(() => new Map(index.records.map((r, i) => [r, i] as const)), [index]);
  const [hashes, setHashes] = useState<Record<number, RawHashResult>>({});
  const [hashing, setHashing] = useState<Record<number, boolean>>({});
  const [live, setLive] = useState<Record<number, RefetchOutcome>>({});
  const [fetching, setFetching] = useState<Record<number, boolean>>({});
  const [bulk, setBulk] = useState<{ done: number; total: number; running: boolean } | null>(null);
  const bulkAbort = useRef<AbortController | null>(null);

  useEffect(() => {
    // New manifest (pipeline re-run): earlier results no longer describe these rows.
    setHashes({});
    setLive({});
    setBulk(null);
    bulkAbort.current?.abort();
  }, [manifest?.snapshot_sha256, manifest?.generated_at_utc]);
  useEffect(() => () => bulkAbort.current?.abort(), []);

  const rehashOne = useCallback(async (r: RawRecord) => {
    const i = position.get(r);
    if (i === undefined) return;
    setHashing((h) => ({ ...h, [i]: true }));
    try {
      const res = await rehashInBrowser(r);
      setHashes((h) => ({ ...h, [i]: res }));
    } finally {
      setHashing((h) => ({ ...h, [i]: false }));
    }
  }, [position]);

  const fetchOne = useCallback(async (r: RawRecord) => {
    const i = position.get(r);
    if (i === undefined) return;
    setFetching((f) => ({ ...f, [i]: true }));
    try {
      const res = await refetchLive(r);
      setLive((l) => ({ ...l, [i]: res }));
    } finally {
      setFetching((f) => ({ ...f, [i]: false }));
    }
  }, [position]);

  const rehashAll = useCallback(async () => {
    bulkAbort.current?.abort();
    const ctrl = new AbortController();
    bulkAbort.current = ctrl;
    const all = index.records;
    let done = 0;
    setBulk({ done: 0, total: all.length, running: true });
    let next = 0;
    const worker = async () => {
      while (next < all.length && !ctrl.signal.aborted) {
        const i = next++;
        try {
          const res = await rehashInBrowser(all[i], ctrl.signal);
          if (ctrl.signal.aborted) return;
          setHashes((h) => ({ ...h, [i]: res }));
        } catch {
          return; // aborted
        }
        done++;
        setBulk({ done, total: all.length, running: true });
      }
    };
    await Promise.all(Array.from({ length: 4 }, worker));
    if (!ctrl.signal.aborted) setBulk({ done, total: all.length, running: false });
  }, [index]);

  useEffect(() => {
    if (linked === "rehash" && index.size && bulk === null) void rehashAll();
  }, [linked, index, bulk, rehashAll]);

  const tally = useMemo(() => {
    const vals = Object.values(hashes);
    return {
      match: vals.filter((v) => v.matches === true).length,
      mismatch: vals.filter((v) => v.matches === false).length,
      skipped: vals.filter((v) => v.matches === null).length,
      checked: vals.length,
    };
  }, [hashes]);
  const [source, setSource] = useState<string>("all");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");

  const rows = useMemo(() => {
    let list = index.search(query);
    if (source !== "all") list = list.filter((r) => r.source === source);
    if (status === "ok") list = list.filter((r) => r.ok);
    if (status === "failed") list = list.filter((r) => !r.ok);
    return list;
  }, [index, query, source, status]);

  const nFailed = index.failures().length;

  // Five columns so the table fits the panel without horizontal scrolling: source sits above the record name,
  // size under the HTTP status, and verification results expand under the record.
  const columns: Column<RawRecord>[] = [
    {
      key: "name",
      header: "Source and record",
      render: (r) => (
        <div className="min-w-[15rem] max-w-[24rem]">
          <div className="text-[12.5px] text-muted">{sourceName(r.source)}</div>
          <div className="break-all font-mono text-[12px] text-ink">{r.name}</div>
          {r.method === "GET" ? (
            <a href={r.url} target="_blank" rel="noreferrer" className="mt-0.5 block truncate text-[12px] text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent" title={`${r.method} ${r.url}`}>
              {r.method} {r.url.replace(/^https?:\/\//, "")}
            </a>
          ) : (
            // A POST endpoint opened in a browser tab returns 404/405; show it as text. "Fetch live and compare" replays the request.
            <span className="mt-0.5 block truncate text-[12px] text-muted" title={`${r.method} ${r.url}`}>
              {r.method} {r.url.replace(/^https?:\/\//, "")}
            </span>
          )}
          {r.error ? <div className="mt-0.5 text-[12px] leading-snug text-crimson">{r.error}</div> : null}
          <RowResults record={r} index={position.get(r)} hashes={hashes} live={live} latest={index.get(r.source, r.name)} />
        </div>
      ),
    },
    {
      key: "status",
      header: "Status and size",
      render: (r) => (
        <div className="whitespace-nowrap">
          <Badge variant={r.ok ? "ok" : "error"} dot title={r.error ?? undefined}>
            {r.ok ? recordStatusLabel(r) : recordStatusLabel(r).replace(/^FAIL/, "Failed")}
          </Badge>
          <div className="tnum mt-1 text-[12.5px] text-muted">{fmtBytes(r.bytes)}</div>
        </div>
      ),
    },
    {
      key: "sha256",
      header: "SHA-256",
      title: "SHA-256 of the exact raw response bytes; equals `shasum -a 256 <raw_path>`. Click to copy.",
      render: (r) => <HashCell hash={r.sha256} />,
    },
    {
      key: "fetched",
      header: "Fetched (UTC)",
      numeric: true,
      render: (r) => {
        const [date, time] = fmtUtc(r.fetched_at_utc, { seconds: true }).replace(" UTC", "").split(" ");
        return (
          <div className="whitespace-nowrap" title={`${r.fetched_at_utc}, ${fmtMs(r.latency_ms)}`}>
            <div>{date}</div>
            <div className="text-[12.5px] text-muted">{time}</div>
          </div>
        );
      },
    },
    {
      key: "verify",
      header: "Verify",
      render: (r) => {
        const i = position.get(r) ?? -1;
        const support = refetchSupport(r);
        return (
          <div className="flex flex-col items-stretch gap-1.5">
            <Button size="xs" onClick={() => void rehashOne(r)} loading={hashing[i]} disabled={!r.raw_path} title={r.raw_path ? "Download the stored bytes and SHA-256 them in this browser" : "No bytes were stored for this record"}>
              Re-hash in browser
            </Button>
            <Button size="xs" onClick={() => void fetchOne(r)} loading={fetching[i]} disabled={!support.ok} title={support.ok ? "Re-issue the original request now and compare with the stored payload" : support.reason}>
              Fetch live and compare
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <Drawer
      open={isOpen}
      onClose={close}
      width="xl"
      title="Verify sources"
      subtitle={
        manifest ? (
          <span className="tnum">
            {fmtInt(manifest.records.length)} raw records behind this snapshot, manifest written {fmtUtc(manifest.generated_at_utc)} at NEAR block {fmtInt(manifest.block_height)}
            {manifest.failures ? `; ${fmtInt(manifest.failures)} failed and are shown as failed, not filled in.` : "; none failed."}
          </span>
        ) : (
          "No manifest.json was found. Run make reproduce to generate one."
        )
      }
      footer={
        <p>
          Verify offline: <code className="font-mono text-[12px] text-ink">shasum -a 256 artifacts/latest_snapshot.json</code> must print{" "}
          <code className="break-all font-mono text-[12px] text-ink">{manifest?.snapshot_sha256 ?? "the manifest's snapshot_sha256"}</code>, and each{" "}
          <code className="font-mono text-[12px] text-ink">artifacts/raw/&lt;source&gt;__&lt;name&gt;.json</code> must hash to its row above.
        </p>
      }
    >
      <div className="space-y-6">
        {manifest ? <IntegrityStatement manifest={manifest} integrity={integrity} /> : null}

        {manifest ? (
          <section aria-labelledby="prov-browser" className="rounded-lg border border-border px-5 py-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 max-w-[40rem]">
                <h3 id="prov-browser" className="font-serif text-[18px] font-medium text-ink">
                  Check it in your browser
                </h3>
                <p className="mt-1 text-[13.5px] leading-relaxed text-muted">
                  Re-hash downloads each stored response exactly as written to <code className="font-mono text-[12px] text-ink">artifacts/raw</code> and computes SHA-256 here with WebCrypto, so the comparison does not depend on the server&apos;s word.
                  Fetch live re-issues the original request now (GET URLs as recorded; NEAR RPC bodies rebuilt and checked against their recorded hash) and shows what changed since the snapshot.
                </p>
              </div>
              <Button variant="primary" size="sm" onClick={() => void rehashAll()} loading={bulk?.running} disabled={!index.size}>
                {bulk?.running ? `Hashing ${fmtInt(bulk.done)} of ${fmtInt(bulk.total)}` : "Re-hash all"}
              </Button>
            </div>
            {tally.checked ? <HashTally tally={tally} total={index.size} running={!!bulk?.running} /> : null}
          </section>
        ) : null}

        <section aria-labelledby="prov-records" className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h3 id="prov-records" className="font-serif text-[18px] font-medium text-ink">
              Raw records
            </h3>
            <span className="tnum text-[13px] text-muted">
              {fmtInt(rows.length)} of {fmtInt(index.size)} shown
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[13px]">
            <label className="flex items-center gap-2 text-muted">
              Source
              <select value={source} onChange={(e) => setSource(e.target.value)} className={CONTROL}>
                <option value="all">All sources ({index.size})</option>
                {index.sources().map((s) => (
                  <option key={s} value={s}>
                    {sourceName(s)} ({index.bySource(s).length})
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-muted">
              Status
              <select value={status} onChange={(e) => setStatus(e.target.value as StatusFilter)} className={CONTROL}>
                <option value="all">All</option>
                <option value="ok">OK</option>
                <option value="failed">Failed ({nFailed})</option>
              </select>
            </label>
            <label className="flex min-w-[14rem] flex-1 items-center gap-2 text-muted">
              <span className="sr-only">Search records</span>
              <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name, URL or SHA-256 prefix" className={cn(CONTROL, "w-full placeholder:text-dim")} />
            </label>
          </div>
          <Table columns={columns} rows={rows} rowKey={(r, i) => `${r.source}:${r.name}:${i}`} emptyText={manifest ? "No records match these filters" : "No manifest"} maxHeight="58vh" />
        </section>
      </div>
    </Drawer>
  );
}
