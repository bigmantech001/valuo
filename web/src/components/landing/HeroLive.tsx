"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { fmtBps, fmtInt } from "@/lib/format";
import { Figure } from "./HeroFigure";
import { Sparkline } from "./HeroVisuals";
import { VENUE_LABEL, minus, signTone } from "./landingData";

const RPC = "https://free.rpc.fastnear.com";
const POLL_MS = 3000;

/**
 * The chain's current final block, read in the visitor's browser straight from NEAR RPC (`status`), next to the
 * snapshot's block. Polls only while the tab is visible; on failure it says so instead of guessing a height.
 */
export function LiveBlock({ snapshotBlock }: { snapshotBlock: number }) {
  const [live, setLive] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      if (document.visibilityState === "visible") {
        try {
          const r = await fetch(RPC, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", id: "valuo", method: "status", params: [] }),
            signal: AbortSignal.timeout(5000),
          });
          const j = await r.json();
          const h = j?.result?.sync_info?.latest_block_height;
          if (!stopped && typeof h === "number") {
            setLive(h);
            setFailed(false);
          }
        } catch {
          if (!stopped) setFailed(true);
        }
      }
      if (!stopped) timer = setTimeout(tick, POLL_MS);
    };
    tick();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (failed && live === null) return <div className="w-full text-[12.5px] text-dim">Live block unavailable (NEAR RPC did not answer)</div>;
  if (live === null) return <div className="w-full text-[12.5px] text-dim">Reading the live block from NEAR RPC…</div>;
  return (
    <div className="flex w-full flex-wrap items-center gap-x-2 gap-y-0.5 text-[12.5px] text-dim">
      <span className="relative flex size-2" aria-hidden>
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald opacity-50" />
        <span className="relative inline-flex size-2 rounded-full bg-emerald" />
      </span>
      <span>
        Live block <span className="tnum text-ink">{fmtInt(live)}</span>
      </span>
      <span>&middot;</span>
      <span>
        snapshot is <span className="tnum text-ink">{fmtInt(Math.max(0, live - snapshotBlock))}</span> blocks behind
      </span>
    </div>
  );
}

const CLIPS = [500, 50_000, 250_000];
const TONE = { emerald: "text-emerald", crimson: "text-crimson", neutral: "text-ink" } as const;

interface RaceResult {
  bps: number | null;
  n: number;
  venue: string | null;
  at: string;
  elapsedS: number;
}

function rangeText(xs: number[]): string {
  const lo = minus(fmtBps(Math.min(...xs), { decimals: 2, signed: true }));
  const hi = minus(fmtBps(Math.max(...xs), { decimals: 2, signed: true }));
  return lo === hi ? `all at ${lo}` : `range ${lo} to ${hi}`;
}

function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * The cross-VM headroom row with a "Race it now" button: three dry quote races ($500 / $50K / $250K) through
 * /api/live-benchmark, aggregated exactly as the pipeline does (median of the cells' headroom), so the live number
 * is comparable with the snapshot's. The hourly history is drawn behind it; a live reading is added as one point.
 */
export function LiveRaceFigure({
  corridorId,
  snapshotBps,
  snapshotVenue,
  history,
  source,
}: {
  corridorId: string | null;
  snapshotBps: number | null;
  snapshotVenue: string | null;
  history: number[];
  source: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<RaceResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const race = useCallback(async () => {
    if (!corridorId || busy) return;
    setBusy(true);
    setErr(null);
    const t0 = performance.now();
    try {
      const cells = await Promise.all(
        CLIPS.map(async (clip) => {
          const r = await fetch("/api/live-benchmark", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ corridor_id: corridorId, clip_usd: clip }),
          });
          const j = await r.json().catch(() => ({}));
          if (!r.ok) throw new Error(typeof j?.error === "string" ? j.error : `HTTP ${r.status}`);
          return j as { headroom_bps?: number | null; best_competitor?: string | null };
        }),
      );
      const vals = cells.map((c) => c.headroom_bps).filter((v): v is number => typeof v === "number" && Number.isFinite(v));
      const venues = cells.map((c) => c.best_competitor).filter((v): v is string => typeof v === "string");
      setRes({
        bps: median(vals),
        n: vals.length,
        venue: venues.length ? venues.sort((a, b) => venues.filter((v) => v === b).length - venues.filter((v) => v === a).length)[0] : null,
        at: new Date().toISOString().slice(11, 19),
        elapsedS: (performance.now() - t0) / 1000,
      });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [corridorId, busy]);

  const bps = res ? res.bps : snapshotBps;
  const venueKey = res ? res.venue : snapshotVenue;
  const venue = venueKey ? (VENUE_LABEL[venueKey] ?? venueKey) : null;
  const note = res ? (
    <>
      Live, {res.at} UTC: median of <span className="tnum">{res.n}</span> of 3 dry quotes, best competitor {venue ?? "n/a"}, answered in{" "}
      <span className="tnum">{res.elapsedS.toFixed(1)}</span> s
    </>
  ) : snapshotBps === null ? (
    "No comparable cell in the snapshot"
  ) : (
    `${snapshotBps >= 0 ? "More" : "Less"} output than the best competitor${venue ? ` (${venue})` : ""}, snapshot median of 3 sizes`
  );

  return (
    <Figure
      label="1Click headroom, cross-VM"
      source={source}
      value={<span className={cn(TONE[signTone(bps)], busy && "opacity-40")}>{bps === null ? "n/a" : minus(fmtBps(bps, { decimals: 2, signed: true }))}</span>}
      note={
        <>
          {note}
          {err ? <span className="mt-1 block text-crimson">Race failed: {err}</span> : null}
          {corridorId ? (
            <button
              type="button"
              onClick={race}
              disabled={busy}
              className="mt-2 flex items-center gap-1.5 rounded-md border border-border-strong px-2.5 py-1 text-[12.5px] text-ink transition-colors hover:bg-surface-2 disabled:cursor-wait disabled:opacity-60 max-lg:min-h-9 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
            >
              {busy ? "Racing 1Click, Relay, LI.FI and Across…" : res ? "Race again" : "Race it now"}
            </button>
          ) : null}
        </>
      }
      spark={
        history.length >= 2 ? (
          <Sparkline
            points={history}
            extra={res?.bps ?? null}
            minRange={2}
            caption={`${history.length} hourly races from the scheduler, ${rangeText(history)}${res && res.bps !== null ? "; blue dot: your live race" : ""}`}
          />
        ) : null
      }
    />
  );
}
