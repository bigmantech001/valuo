"use client";

import { useEffect, useRef, useState } from "react";
import { Badge, Button, Card } from "@/components/ui";
import { ARCHETYPE_LABELS, CORRIDORS, DEFAULT_CLIPS_USD, type CorridorDef } from "@/lib/corridors";
import { cn } from "@/lib/cn";
import { fmtBps, fmtInt, fmtMs, fmtUtc } from "@/lib/format";
import type { LiveBenchmarkRequest, LiveBenchmarkResponse, VenueName } from "@/lib/types";
import { TONE_TEXT, VENUE_SHORT, clipLabel, routeName, signTone, venueShort } from "./benchUtil";
import { RaceResult, type SnapshotCellRef } from "./RaceResult";
import { VenueLabel } from "./VenueLabel";

interface RaceEntry {
  id: string;
  request: LiveBenchmarkRequest;
  started_at_utc: string;
  status: "running" | "ok" | "error";
  response: LiveBenchmarkResponse | null;
  error: string | null;
  client_ms: number | null;
}

export interface LiveRaceProps {
  /** snapshot execution_bench cells (slim) for side-by-side reading; empty when the snapshot has no benchmark */
  snapshotCells: SnapshotCellRef[];
}

function corridorDef(id: string): CorridorDef | null {
  return CORRIDORS.find((c) => c.corridor_id === id) ?? null;
}

function venuesOf(def: CorridorDef | null): VenueName[] {
  if (!def) return [];
  const declared = Object.keys(def.venues_declared_unsupported) as VenueName[];
  return [...def.venues_attempted, ...declared.filter((v) => !def.venues_attempted.includes(v))];
}

const SELECT =
  "h-9 rounded-md border border-border-strong bg-surface px-3 pr-8 text-[14px] text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 disabled:opacity-50";

/** One-line summary of a race: when, route, size, outcome. */
function RaceSummary({ entry }: { entry: RaceEntry }) {
  const h = entry.response?.headroom_bps ?? null;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13.5px]">
      <span className="tnum text-muted">{fmtUtc(entry.started_at_utc, { seconds: true })}</span>
      <span className="text-ink">{routeName(entry.request.corridor_id)}</span>
      <span className="tnum text-ink">{clipLabel(entry.request.clip_usd)}</span>
      {entry.status === "running" ? (
        <Badge variant="neutral" dot>
          Running
        </Badge>
      ) : entry.status === "error" ? (
        <Badge variant="error" dot>
          Error
        </Badge>
      ) : (
        <span className={cn("tnum", TONE_TEXT[signTone(h)])} title="1Click output vs best competitor, destination units">
          {h === null ? <span className="text-dim">Headroom n/a</span> : `${fmtBps(h, { decimals: 2 })} headroom`}
          {entry.response?.best_competitor ? <span className="text-muted"> vs {venueShort(entry.response.best_competitor)}</span> : null}
        </span>
      )}
      {entry.client_ms !== null ? <span className="tnum text-dim">{fmtMs(entry.client_ms)} round trip</span> : null}
    </div>
  );
}

function RaceEntryView({ entry, snapshotCells, expanded = false }: { entry: RaceEntry; snapshotCells: SnapshotCellRef[]; expanded?: boolean }) {
  const def = corridorDef(entry.request.corridor_id);
  if (entry.status === "running") {
    return (
      <div className="rounded-md border border-border">
        <div className="border-b border-border px-4 py-3">
          <RaceSummary entry={entry} />
        </div>
        <ul className="divide-y divide-border">
          {venuesOf(def).map((v) => (
            <li key={v} className="flex items-center justify-between gap-4 px-4 py-2.5 text-[13.5px]">
              <VenueLabel venue={v} className="text-ink" />
              <span className="valuo-skeleton h-3 w-40 max-w-[50%]" aria-label="Awaiting response" />
            </li>
          ))}
        </ul>
        <p className="border-t border-border px-4 py-2 text-[12.5px] text-dim">The server answers once every venue has responded or timed out.</p>
      </div>
    );
  }
  if (entry.status === "error" || !entry.response) {
    return (
      <div className="rounded-md border border-crimson/40 px-4 py-3">
        <RaceSummary entry={entry} />
        <p className="mt-1.5 break-words text-[13px] text-crimson">{entry.error ?? "No response body"}</p>
      </div>
    );
  }
  const snap = snapshotCells.find((c) => c.corridor_id === entry.request.corridor_id && c.clip_usd === entry.request.clip_usd) ?? null;
  if (expanded) {
    return <RaceResult request={entry.request} response={entry.response} clientMs={entry.client_ms} snapshotCell={snap} />;
  }
  return (
    <details className="group rounded-md border border-border">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 [&::-webkit-details-marker]:hidden">
        <span aria-hidden className="text-dim transition-transform group-open:rotate-90">
          &#8250;
        </span>
        <RaceSummary entry={entry} />
      </summary>
      <div className="border-t border-border px-4 py-4">
        <RaceResult request={entry.request} response={entry.response} clientMs={entry.client_ms} snapshotCell={snap} />
      </div>
    </details>
  );
}

/**
 * The live quote race: route and size selectors, one button that POSTs /api/live-benchmark, the
 * latest result as a comparison table, and the earlier races of this session. Nothing is pre-filled;
 * every number on screen came back from the route.
 */
export function LiveRace({ snapshotCells }: LiveRaceProps) {
  const [corridorId, setCorridorId] = useState<string>(CORRIDORS[0].corridor_id);
  const [clipStr, setClipStr] = useState<string>(String(DEFAULT_CLIPS_USD[1]));
  const [races, setRaces] = useState<RaceEntry[]>([]);
  const [elapsedMs, setElapsedMs] = useState(0);
  const counter = useRef(0);
  const running = races.some((r) => r.status === "running");

  useEffect(() => {
    if (!running) return;
    const t0 = performance.now();
    const id = window.setInterval(() => setElapsedMs(performance.now() - t0), 100);
    return () => window.clearInterval(id);
  }, [running]);

  async function execute() {
    const request: LiveBenchmarkRequest = { corridor_id: corridorId, clip_usd: Number(clipStr) };
    counter.current += 1;
    const id = `race-${counter.current}`;
    const started = performance.now();
    setElapsedMs(0);
    setRaces((prev) => [{ id, request, started_at_utc: new Date().toISOString(), status: "running", response: null, error: null, client_ms: null }, ...prev]);
    let patch: Partial<RaceEntry>;
    try {
      const res = await fetch("/api/live-benchmark", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request), cache: "no-store" });
      const json: unknown = await res.json().catch(() => null);
      const errorField = json && typeof json === "object" && "error" in json ? (json as { error: unknown }).error : undefined;
      if (!res.ok || errorField !== undefined || !json || typeof json !== "object" || !("quotes" in json)) {
        patch = { status: "error", error: errorField !== undefined ? String(errorField) : `HTTP ${res.status}: unexpected response shape` };
      } else {
        patch = { status: "ok", response: json as LiveBenchmarkResponse };
      }
    } catch (err) {
      patch = { status: "error", error: err instanceof Error ? `${err.name}: ${err.message}` : String(err) };
    }
    const client_ms = Math.round(performance.now() - started);
    setRaces((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch, client_ms } : r)));
  }

  const def = corridorDef(corridorId) ?? CORRIDORS[0];
  const declared = Object.entries(def.venues_declared_unsupported);
  const [latest, ...history] = races;

  return (
    <Card
      title="Run the race yourself"
      subtitle="Sends the same dry quote request to 1Click, Relay, LI.FI and Across from this server, at once. Nothing is signed or sent on-chain; every raw response is hashed before it is parsed."
      actions={
        running ? (
          <Badge variant="neutral" dot>
            Running, {fmtMs(elapsedMs)}
          </Badge>
        ) : null
      }
    >
      <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
        <label className="flex min-w-0 flex-col gap-1">
          <span className="text-[13px] text-muted">Route</span>
          <select className={cn(SELECT, "max-w-full")} value={corridorId} onChange={(e) => setCorridorId(e.target.value)} disabled={running}>
            {CORRIDORS.map((c) => (
              <option key={c.corridor_id} value={c.corridor_id}>
                {ARCHETYPE_LABELS[c.archetype]}: {routeName(c.corridor_id, c.label)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[13px] text-muted">Trade size</span>
          <select className={SELECT} value={clipStr} onChange={(e) => setClipStr(e.target.value)} disabled={running}>
            {DEFAULT_CLIPS_USD.map((c) => (
              <option key={c} value={String(c)}>
                {clipLabel(c)}
              </option>
            ))}
          </select>
        </label>
        <Button variant="primary" size="md" className="h-9" onClick={execute} loading={running} disabled={running}>
          Run live quote race
        </Button>
        {races.length ? (
          <Button variant="ghost" size="sm" className="h-9" onClick={() => setRaces([])} disabled={running}>
            Clear history
          </Button>
        ) : null}
      </div>
      <p className="mt-3 max-w-3xl text-[13px] leading-relaxed text-muted">
        Venues called: {def.venues_attempted.map((v) => VENUE_SHORT[v]).join(", ")}.
        {declared.length ? ` ${declared.map(([v, why]) => `${venueShort(v)} is not quoted (${why}); the server re-checks this against Across's live chain list`).join("; ")}.` : ""}{" "}
        {def.same_asset ? "Same asset on both sides, so cost is read on raw units with no price oracle." : "Different assets, so headroom is read on destination units; USD legs use the live 1Click token-list price."}
      </p>

      <div className="mt-5">
        {latest ? (
          <RaceEntryView entry={latest} snapshotCells={snapshotCells} expanded />
        ) : (
          <div className="rounded-md border border-dashed border-border-strong px-4 py-6 text-center text-[13.5px] text-muted">
            No race run in this session. Pick a route and a trade size, then run it.
          </div>
        )}
      </div>

      {history.length ? (
        <div className="mt-6">
          <h4 className="mb-2 text-[13px] text-muted">Earlier races this session ({fmtInt(history.length)})</h4>
          <div className="flex flex-col gap-1.5">
            {history.map((e) => (
              <RaceEntryView key={e.id} entry={e} snapshotCells={snapshotCells} />
            ))}
          </div>
        </div>
      ) : null}
    </Card>
  );
}
