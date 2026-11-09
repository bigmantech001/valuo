import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Badge, QuoteStatusBadge, Stat, Table, type Column } from "@/components/ui";
import { StatGrid } from "@/components/ui/Section";
import { getCorridor } from "@/lib/corridors";
import { cn } from "@/lib/cn";
import { fmtBps, fmtBytes, fmtInt, fmtMs, fmtNum, fmtSeconds, fmtUsd, fmtUtc } from "@/lib/format";
import { recordStatusLabel } from "@/lib/manifestIndex";
import type { LiveBenchmarkRequest, LiveBenchmarkResponse, RawRecord, VenueQuote } from "@/lib/types";
import {
  TONE_TEXT,
  VENUE_SHORT,
  feeTotalUsd,
  frictionOf,
  headroomBasisLabel,
  headroomMissingReason,
  oneclickAdvantageBps,
  priceBasisLabel,
  reconstructPostBodies,
  signTone,
  statusText,
  truncate,
  venueShort,
} from "./benchUtil";
import { VenueLabel } from "./VenueLabel";

/** The snapshot cell for the same corridor x clip, so a live race can be read against the reproducible run. */
export interface SnapshotCellRef {
  corridor_id: string;
  clip_usd: number;
  headroom_bps: number | null;
  headroom_basis: string | null;
  best_competitor: string | null;
  oneclick_rank: number | null;
  n_venues_ok: number;
  ran_at_utc: string;
}

export interface RaceResultProps {
  request: LiveBenchmarkRequest;
  response: LiveBenchmarkResponse;
  /** browser round-trip to /api/live-benchmark */
  clientMs: number | null;
  snapshotCell: SnapshotCellRef | null;
}

interface QRow {
  q: VenueQuote;
  record: RawRecord | null;
  /** 1Click advantage over this venue, bps (positive = 1Click delivers more) */
  adv: number | null;
  most: boolean;
}

function PayloadBlock({ title, json, note }: { title: string; json: unknown; note?: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border">
      <div className="border-b border-border px-3 py-1.5 text-[12.5px] text-muted">{title}</div>
      <pre className="overflow-x-auto bg-surface-2/50 px-3 py-2 font-mono text-[11.5px] leading-relaxed text-ink">{JSON.stringify(json, null, 2)}</pre>
      {note ? <div className="border-t border-border px-3 py-1.5 text-[12px] text-dim">{note}</div> : null}
    </div>
  );
}

function rawOut(q: VenueQuote): bigint | null {
  return q.status === "ok" && q.amount_out_raw && /^\d+$/.test(q.amount_out_raw) ? BigInt(q.amount_out_raw) : null;
}

/** One finished live race: key figures, the venue comparison table, then the raw records and payloads. */
export function RaceResult({ request, response, clientMs, snapshotCell }: RaceResultProps) {
  const corridor = response.corridor;
  const basis = response.ranking_basis;
  const recordBySha = new Map(response.records.map((r) => [r.sha256, r] as const));
  const adv = oneclickAdvantageBps(response.quotes);
  const outs = response.quotes.map(rawOut).filter((v): v is bigint => v !== null);
  const maxOut = outs.length ? outs.reduce((a, b) => (b > a ? b : a)) : null;
  const rows: QRow[] = response.quotes.map((q) => ({
    q,
    record: recordBySha.get(q.raw_record_sha256) ?? null,
    adv: adv.get(q.venue) ?? null,
    most: maxOut !== null && rawOut(q) === maxOut,
  }));
  const def = getCorridor(response.corridor_id);
  const posts = def ? reconstructPostBodies(def, corridor, response.clip_usd) : [];
  const priceBasis = response.price_basis ?? null;
  const headroom = response.headroom_bps ?? null;

  const quoteColumns: Column<QRow>[] = [
    {
      key: "venue",
      header: "Venue",
      render: (r) => (
        <div className="flex flex-col gap-0.5">
          <VenueLabel venue={r.q.venue} className="text-ink" />
          {r.q.route_tool && r.q.route_tool !== r.q.venue ? <span className="pl-3.5 text-[12px] text-dim">{r.q.route_tool}</span> : null}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => (
        <div className="flex flex-col items-start gap-1">
          <QuoteStatusBadge status={r.q.status} title={r.q.error_message ?? undefined} />
          {r.q.routes_via_near_intents ? (
            <Badge variant="warn" title={`LI.FI tool "${r.q.route_tool ?? "near"}" resells NEAR Intents execution; not an independent price`}>
              Via NEAR Intents
            </Badge>
          ) : null}
        </div>
      ),
    },
    {
      key: "out",
      header: `Amount out (${corridor.destination.symbol})`,
      numeric: true,
      render: (r) =>
        r.q.status === "ok" ? (
          <div className="flex flex-col items-end gap-0.5">
            <span className="tnum text-ink">{fmtNum(r.q.amount_out_formatted, { decimals: corridor.destination.decimals })}</span>
            {r.most ? <span className="text-[12px] text-muted">Most delivered</span> : null}
          </div>
        ) : (
          <span className="inline-block max-w-[16rem] text-left text-[12.5px] leading-snug text-muted" title={r.q.error_message ?? undefined}>
            {r.q.declared ? "Declared unsupported: " : null}
            {r.q.error_message ? truncate(r.q.error_message, 90) : "No message returned"}
          </span>
        ),
    },
    {
      key: "adv",
      header: "1Click vs venue",
      numeric: true,
      title: "(1Click output - this venue's output) / this venue's output, in bps of destination units; positive = 1Click delivers more",
      render: (r) =>
        r.q.venue === "1click" ? (
          <span className="text-dim">Reference</span>
        ) : r.adv === null ? (
          <span className="text-[12.5px] text-dim">{r.q.status !== "ok" ? "n/a" : "No 1Click quote"}</span>
        ) : (
          <span className={cn("tnum font-medium", TONE_TEXT[signTone(r.adv)])}>{fmtBps(r.adv, { decimals: 2 })}</span>
        ),
    },
    {
      key: "cost",
      header: "All-in cost",
      numeric: true,
      title: `Input less output, in bps of input, on ${basis === "raw" ? "raw units" : "USD legs"}`,
      render: (r) => {
        const f = r.q.status === "ok" ? frictionOf(r.q, basis) : null;
        return f === null ? <span className="text-dim">n/a</span> : <span className="tnum">{fmtBps(f, { signed: false, decimals: 2 })}</span>;
      },
    },
    {
      key: "fees",
      header: "Itemised fees",
      numeric: true,
      render: (r) => {
        const t = feeTotalUsd(r.q);
        const items = Object.entries(r.q.fee_breakdown_usd ?? {});
        return t === null ? (
          <span className="text-dim">n/a</span>
        ) : (
          <span className="tnum" title={items.map(([k, v]) => `${k}: ${fmtUsd(v, { decimals: 4 })}`).join("\n")}>
            {fmtUsd(t, { decimals: 2 })}
          </span>
        );
      },
    },
    { key: "time", header: "Est. time", numeric: true, render: (r) => <span className="tnum">{r.q.status === "ok" ? fmtSeconds(r.q.time_estimate_s) : <span className="text-dim">n/a</span>}</span> },
    {
      key: "gap",
      header: "USD mark gap",
      numeric: true,
      title: "Venue-implied destination price vs the race's common price, in bps",
      render: (r) => {
        const gap = response.venue_oracle_gap_bps?.[r.q.venue] ?? r.q.venue_oracle_gap_bps;
        return typeof gap === "number" ? <span className="tnum">{fmtBps(gap, { decimals: 1 })}</span> : <span className="text-dim">n/a</span>;
      },
    },
    {
      key: "src",
      header: "Source",
      render: (r) => (
        <div className="flex flex-col gap-0.5 text-[12.5px]">
          {r.record ? <ProvenanceBadge record={r.record} /> : <span className="text-dim">{r.q.declared ? "No HTTP exchange" : "n/a"}</span>}
          <span className="tnum text-dim">{fmtMs(r.q.latency_ms)}</span>
        </div>
      ),
    },
  ];

  const recordColumns: Column<RawRecord>[] = [
    { key: "source", header: "Source", render: (r) => <span className="text-ink">{r.source}</span> },
    { key: "name", header: "Record", render: (r) => <span className="break-all font-mono text-[12px] text-ink">{r.name}</span> },
    { key: "method", header: "Method", render: (r) => r.method },
    { key: "status", header: "HTTP", render: (r) => <span className={r.ok ? "text-ink" : "text-crimson"}>{recordStatusLabel(r)}</span> },
    { key: "bytes", header: "Bytes", numeric: true, render: (r) => <span className="tnum">{fmtBytes(r.bytes)}</span> },
    { key: "latency", header: "Latency", numeric: true, render: (r) => <span className="tnum">{fmtMs(r.latency_ms)}</span> },
    { key: "sha", header: "SHA-256 (hover for URL)", render: (r) => <ProvenanceBadge record={r} /> },
  ];

  return (
    <div className="flex flex-col gap-5">
      <StatGrid cols={4}>
        <Stat
          label="1Click headroom"
          value={headroom}
          format={(v) => fmtBps(v, { decimals: 2 })}
          tone={signTone(headroom)}
          hint={
            headroom === null
              ? headroomMissingReason(response)
              : `vs ${venueShort(response.best_competitor)}; 1Click ranks ${response.oneclick_rank ?? "n/a"} of ${fmtInt(response.n_venues_ok)}`
          }
        />
        <Stat
          label="Committed snapshot, same cell"
          value={snapshotCell ? snapshotCell.headroom_bps : null}
          format={(v) => fmtBps(v, { decimals: 2 })}
          tone={signTone(snapshotCell?.headroom_bps ?? null)}
          hint={snapshotCell ? `vs ${venueShort(snapshotCell.best_competitor)}, run ${fmtUtc(snapshotCell.ran_at_utc)}` : "No matching cell in the loaded snapshot"}
        />
        <Stat label="Server time" value={response.total_latency_ms} format={(v) => fmtMs(v)} hint={clientMs === null ? undefined : `${fmtMs(clientMs)} browser round trip`} />
        <Stat
          label="Run at"
          value={<span className="text-[18px]">{fmtUtc(response.ran_at_utc, { seconds: true })}</span>}
          hint={`${fmtInt(response.n_venues_ok)} venues quoted; ${fmtInt(response.records.length)} raw records hashed`}
        />
      </StatGrid>

      <div>
        <Table columns={quoteColumns} rows={rows} rowKey={(r) => r.q.venue} stickyHeader={false} dense={false} emptyText="No venue quotes returned" />
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12.5px] text-muted">
          <span>Headroom basis: {headroomBasisLabel(response.headroom_basis)}</span>
          <span>Cost basis: {basis === "raw" ? "raw units" : "USD legs"}</span>
          <span
            title={
              priceBasis?.source
                ? `Destination ${priceBasis.dest_price_usd ?? "n/a"} USD, origin ${priceBasis.origin_price_usd ?? "n/a"} USD per unit${priceBasis.n_venue_oracles ? `; median of ${fmtInt(priceBasis.n_venue_oracles)} venue marks` : ""}`
                : "No common USD price could be established; USD costs are as each venue returned them"
            }
          >
            Price basis: {priceBasisLabel(priceBasis?.source ?? null)}
          </span>
          {!response.token_list_ok ? (
            <Badge variant="warn" dot>
              Token list failed
            </Badge>
          ) : null}
          {response.oracle_gap_exceeds_headroom ? (
            <Badge variant="warn" dot title="A USD-leg comparison would be decided by price disagreement between venues, so headroom is read on destination units">
              Price gap exceeds headroom
            </Badge>
          ) : null}
        </div>
      </div>

      <details className="group rounded-md border border-border">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-[13px] text-muted hover:text-ink [&::-webkit-details-marker]:hidden">
          <span aria-hidden className="text-dim transition-transform group-open:rotate-90">
            &#8250;
          </span>
          Raw records ({fmtInt(response.records.length)}) and request payloads
        </summary>
        <div className="flex flex-col gap-3 border-t border-border px-4 py-4">
          <Table columns={recordColumns} rows={response.records} rowKey={(r) => `${r.source}:${r.name}:${r.sha256}`} stickyHeader={false} emptyText="No records" />
          <PayloadBlock title="POST /api/live-benchmark (browser to server)" json={request} />
          {response.records.map((r) => (
            <PayloadBlock
              key={`${r.source}:${r.name}:${r.sha256}`}
              title={`${r.method} ${r.source} / ${r.name}`}
              json={{ url: r.url, request_body_sha256: r.request_body_sha256 ?? null, http_status: r.http_status ?? null, response_sha256: r.sha256, response_bytes: r.bytes, fetched_at_utc: r.fetched_at_utc, error: r.error ?? null }}
            />
          ))}
          {posts.map((p) => (
            <PayloadBlock key={p.venue} title={`${VENUE_SHORT[p.venue]} ${p.method} body (reconstructed)`} json={p.body} note={p.note} />
          ))}
          {response.quotes.some((q) => q.status !== "ok") ? (
            <ul className="list-disc space-y-1 pl-5 text-[12.5px] text-muted">
              {response.quotes
                .filter((q) => q.status !== "ok")
                .map((q) => (
                  <li key={q.venue}>
                    {venueShort(q.venue)}: {statusText(q.status)}
                    {q.error_code ? ` (${q.error_code})` : ""}. {q.error_message ?? "No message returned."}
                  </li>
                ))}
            </ul>
          ) : null}
        </div>
      </details>
    </div>
  );
}
