"use client";

import { useEffect, useState, type ReactNode } from "react";
import { fmtAgo, fmtInt, fmtNear, fmtNum, fmtPct } from "@/lib/format";
import { fmtTimes, minus, type SupplyReading, type SupplyTickerData } from "./landingData";
import { TextLink } from "./SectionHeader";

const DAY_MS = 86_400_000;
const TICK_MS = 100;
const TICK_REDUCED_MS = 1000;
const POLL_MS = 60_000;

const T = ({ children }: { children: ReactNode }) => <span className="tnum text-ink">{children}</span>;
const f3 = (v: number) => fmtNum(v, { decimals: 3 });
const perDay = (v: number) => `${fmtNear(v)} a day`;
const signedNear = (v: number) => minus(fmtNear(v, { signed: true }));

function fmtElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")} s`;
  return `${Math.floor(s / 3600)} h ${String(Math.floor((s % 3600) / 60)).padStart(2, "0")} min`;
}

/**
 * Milliseconds since mount, recomputed from the clock on every tick (never incremented), so the value is
 * right after a background tab or a sleep. 0 on the server and on the first client render. Ticks every
 * 100 ms, once a second under prefers-reduced-motion, and not at all while the tab is hidden.
 */
function useElapsedMs(): number {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const arrived = Date.now();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let timer: ReturnType<typeof setInterval> | undefined;
    const update = () => setElapsed(Date.now() - arrived);
    const stop = () => {
      if (timer) clearInterval(timer);
      timer = undefined;
    };
    const start = () => {
      stop();
      if (document.visibilityState !== "visible") return;
      timer = setInterval(update, reduced.matches ? TICK_REDUCED_MS : TICK_MS);
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") update();
      start();
    };
    start();
    reduced.addEventListener("change", start);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      reduced.removeEventListener("change", start);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);
  return elapsed;
}

function parseReading(j: unknown): SupplyReading | null {
  if (!j || typeof j !== "object") return null;
  const o = j as Record<string, unknown>;
  const { block_height: h, total_supply_near: s, block_timestamp_utc: ts, fetched_at_utc: at } = o;
  if (typeof h !== "number" || !Number.isFinite(h) || typeof s !== "number" || !Number.isFinite(s) || s <= 0) return null;
  if (typeof ts !== "string" || !Number.isFinite(Date.parse(ts)) || typeof at !== "string") return null;
  return { block_height: h, total_supply_near: s, block_timestamp_utc: ts, fetched_at_utc: at };
}

/**
 * The current total supply through GET /api/supply (the server calls NEAR RPC; the browser does not).
 * At most one request a minute, none while the tab is hidden. A failed poll keeps the last good
 * reading, which stays true because it is printed with its block height.
 */
function useSupplyReading(): { reading: SupplyReading | null; failed: boolean } {
  const [reading, setReading] = useState<SupplyReading | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let stopped = false;
    let parked = false;
    let lastAt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const schedule = (ms: number) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(run, ms);
    };
    const run = async () => {
      if (stopped) return;
      if (document.visibilityState !== "visible") {
        parked = true;
        return;
      }
      parked = false;
      lastAt = Date.now();
      let next: SupplyReading | null = null;
      try {
        const r = await fetch("/api/supply", { cache: "no-store", signal: AbortSignal.timeout(8000) });
        next = r.ok ? parseReading(await r.json()) : null;
      } catch {
        next = null;
      }
      if (stopped) return;
      if (next) setReading(next);
      setFailed(next === null);
      schedule(POLL_MS);
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible" && parked) schedule(Math.max(0, lastAt + POLL_MS - Date.now()));
    };
    schedule(0);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);
  return { reading, failed };
}

/**
 * "Since you arrived" strip under the hero: NEAR minted against NEAR bought back, burned and state-locked
 * since the page loaded, projected at the snapshot's measured per-day rates, next to one live on-chain
 * total-supply reading. Every rate is read from supply_physics; the ratio and the bar are computed from them.
 */
export function SupplyTicker({ ticker }: { ticker: SupplyTickerData | null }) {
  // No rates in the snapshot: no strip, and no timers or polling either.
  return ticker ? <Strip t={ticker} /> : null;
}

function Strip({ t }: { t: SupplyTickerData }) {
  const elapsedMs = useElapsedMs();
  const { reading, failed } = useSupplyReading();
  const days = elapsedMs / DAY_MS;
  const covered = t.coverageRatio >= 1;
  const mintedPerRemoved = t.sinksDaily > 0 ? t.issuanceDaily / t.sinksDaily : null;
  const netDaily = t.netFloatDaily ?? t.issuanceDaily - t.sinksDaily;
  const offsetShare = Math.min(1, Math.max(0, t.sinksDaily / t.issuanceDaily));

  return (
    <section id="supply-ticker" aria-labelledby="supply-ticker-title" className="bg-surface">
      <div className="mx-auto grid max-w-none grid-cols-[minmax(0,1fr)] gap-x-16 gap-y-10 px-6 py-14 sm:py-16 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:px-[5vw]">
        <div className="min-w-0 max-w-[38rem]">
          <div className="mb-2 text-[13px] text-dim">Supply, since you arrived</div>
          <h2 id="supply-ticker-title" className="font-serif text-[26px] font-medium leading-[1.2] tracking-[-0.01em] text-ink sm:text-[30px]">
            {mintedPerRemoved === null ? (
              <>No NEAR is being removed against {perDay(t.issuanceDaily)} minted.</>
            ) : covered ? (
              <>
                About <span className="tnum">{fmtNum(1 / mintedPerRemoved, { decimals: 1 })}</span> NEAR removed for each NEAR minted.
              </>
            ) : (
              <>
                About <span className="tnum">{fmtNum(mintedPerRemoved, { decimals: 1 })}</span> NEAR minted for each NEAR removed.
              </>
            )}
          </h2>
          <p className="mt-3 text-[15.5px] leading-relaxed text-muted">
            {covered ? (
              <>
                Buybacks, gas burn and storage locks cover <T>{fmtPct(t.coverageRatio, { decimals: 1 })}</T> of measured issuance, past the <T>100%</T> at which the float stops growing: it
                shrinks by about <T>{fmtNear(Math.abs(netDaily))}</T> a day.
              </>
            ) : (
              <>
                Buybacks, gas burn and storage locks cover <T>{fmtPct(t.coverageRatio, { decimals: 1 })}</T> of measured issuance, so the float grows by about{" "}
                <T>{fmtNear(netDaily)}</T> a day. It stops growing only at <T>100%</T> coverage
                {t.breakevenTimesVolume !== null ? (
                  <>
                    , which needs <T>{fmtTimes(t.breakevenTimesVolume)}</T> today&apos;s Intents volume at the current inflation cap
                  </>
                ) : null}
                . As measured, this cuts against the bull case.
              </>
            )}
          </p>
          <p className="mt-3 text-[13px] leading-snug text-dim">
            The counters are projected at the measured daily rates, not a live reading. Rates are from the snapshot at block <span className="tnum">{fmtInt(t.snapshotBlock)}</span>.
          </p>
          <TextLink href="/terminal#supply" className="mt-4">
            See the supply model
          </TextLink>
        </div>

        <div className="min-w-0">
          <dl className="grid grid-cols-[minmax(0,1fr)] gap-x-10 gap-y-8 sm:grid-cols-2">
            <div className="min-w-0">
              <dt className="text-[14px] text-muted">Minted since you arrived</dt>
              <dd className="mt-2 flex flex-wrap items-baseline gap-x-2">
                <span className="tnum text-[34px] font-medium leading-none tracking-tight text-ink sm:text-[38px]">{f3(t.issuanceDaily * days)}</span>
                <span className="text-[13px] text-muted">NEAR</span>
              </dd>
              <dd className="mt-3 text-[13px] leading-snug text-dim">
                <Row label="Measured issuance" value={perDay(t.issuanceDaily)} />
                <Row label="Time on this page" value={fmtElapsed(elapsedMs)} />
              </dd>
            </div>
            <div className="min-w-0 sm:border-l sm:border-border sm:pl-10">
              <dt className="text-[14px] text-muted">Removed since you arrived</dt>
              <dd className="mt-2 flex flex-wrap items-baseline gap-x-2">
                <span className="tnum text-[34px] font-medium leading-none tracking-tight text-ink sm:text-[38px]">{f3(t.sinksDaily * days)}</span>
                <span className="text-[13px] text-muted">NEAR</span>
              </dd>
              <dd className="mt-3 text-[13px] leading-snug text-dim">
                <Row label={`Buyback, ${perDay(t.buybackDaily)}`} value={f3(t.buybackDaily * days)} />
                <Row label={`Gas burn, ${perDay(t.gasBurnDaily)}`} value={f3(t.gasBurnDaily * days)} />
                <Row label={`State lock, ${perDay(t.stateLockDaily)}`} value={f3(t.stateLockDaily * days)} />
              </dd>
            </div>
          </dl>

          <figure className="mt-8" aria-label={`Removed is ${fmtPct(offsetShare, { decimals: 1 })} of minted`}>
            <div className="flex h-2.5 w-full gap-0.5">
              {offsetShare > 0 ? (
                <div
                  className="h-full shrink-0 rounded-[4px] bg-accent"
                  style={{ width: `${Math.max(0.6, offsetShare * 100)}%` }}
                  title={`Removed: ${fmtPct(offsetShare, { decimals: 1 })} of minted`}
                />
              ) : null}
              {offsetShare < 1 ? <div className="h-full min-w-0 flex-1 rounded-[4px] bg-ink" title={`Not offset: ${fmtPct(1 - offsetShare, { decimals: 1 })} of minted`} /> : null}
            </div>
            <figcaption className="mt-2.5 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 text-[13px] leading-snug text-muted">
              <span className="inline-flex items-baseline gap-2">
                <span aria-hidden className="inline-block size-2 shrink-0 rounded-[2px] bg-accent" />
                <span>
                  Removed, <T>{fmtPct(offsetShare, { decimals: 1 })}</T> of minted
                </span>
              </span>
              <span className="inline-flex items-baseline gap-2">
                <span aria-hidden className="inline-block size-2 shrink-0 rounded-[2px] bg-ink" />
                <span>
                  Not offset, <T>{fmtPct(1 - offsetShare, { decimals: 1 })}</T>: net float growth
                </span>
              </span>
            </figcaption>
            <p className="mt-1.5 text-[13px] leading-snug text-dim">The bar is everything minted, to scale. The float stops growing when the removed share reaches 100%.</p>
          </figure>

          <LiveSupply ticker={t} reading={reading} failed={failed} />
        </div>
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-baseline justify-between gap-4 py-0.5">
      <span className="min-w-0">{label}</span>
      <span className="tnum shrink-0 text-ink">{value}</span>
    </span>
  );
}

/**
 * The on-chain check on the projection: total supply now against total supply at the snapshot block. The
 * difference is mint landed at epoch boundaries less gas burned in between, so it is compared with the
 * snapshot's (issuance - gas burn) rate over the same hours and with the number of epoch mints since.
 */
function LiveSupply({ ticker: t, reading, failed }: { ticker: SupplyTickerData; reading: SupplyReading | null; failed: boolean }) {
  const frame = "mt-7 border-t border-border pt-4 text-[13px] leading-relaxed text-dim";
  if (!reading) {
    return <p className={frame}>{failed ? "Live reading unavailable (NEAR RPC did not answer). The projection above does not depend on it." : "Reading on-chain total supply from NEAR RPC…"}</p>;
  }

  const hours = (Date.parse(reading.block_timestamp_utc) - Date.parse(t.snapshotBlockTsUtc)) / 3_600_000;
  const past = Number.isFinite(hours) && hours > 0 && reading.block_height > t.snapshotBlock;
  const delta = reading.total_supply_near - t.snapshotTotalSupply;
  const span = fmtAgo(hours * 3600).replace(/ ago$/, "");
  const implied = ((t.issuanceDaily - t.gasBurnDaily) * hours) / 24;
  const epochs =
    t.epochStartHeight !== null && t.epochLengthBlocks !== null && t.epochLengthBlocks > 0
      ? Math.floor((reading.block_height - t.epochStartHeight) / t.epochLengthBlocks) - Math.floor((t.snapshotBlock - t.epochStartHeight) / t.epochLengthBlocks)
      : null;
  const stepped = epochs !== null && epochs > 0 && t.mintedPerEpoch !== null ? epochs * t.mintedPerEpoch - (t.gasBurnDaily * hours) / 24 : null;

  return (
    <div className={frame}>
      <p className="flex items-baseline gap-2">
        <span aria-hidden className={`relative top-[-1px] inline-block size-2 shrink-0 rounded-full ${failed ? "bg-border-strong" : "bg-emerald"}`} />
        <span>
          On-chain total supply at block <T>{fmtInt(reading.block_height)}</T>: <T>{fmtNear(reading.total_supply_near, { decimals: 2 })}</T>
          {past ? (
            <>
              ; <T>{signedNear(delta)}</T> since the snapshot ({span} ago).
            </>
          ) : (
            <>. The RPC node&apos;s final block is not past the snapshot block, so there is no change to compare yet.</>
          )}
          {failed ? " Last poll failed; this is the most recent reading." : null}
        </span>
      </p>
      {past ? (
        <p className="mt-1.5">
          The snapshot&apos;s rates imply <T>{signedNear(implied)}</T> over the same {span} (issuance less gas burn).{" "}
          {epochs === null ? (
            <>NEAR mints once per epoch, so the on-chain figure moves in steps and the two need not agree between mints.</>
          ) : epochs === 0 ? (
            <>
              NEAR mints once per epoch{t.epochHours !== null ? <> (about <T>{fmtNum(t.epochHours, { decimals: 1 })}</T> h)</> : null} and no mint has landed since the snapshot, so the
              on-chain change so far is gas burned.
            </>
          ) : (
            <>
              NEAR mints once per epoch{t.epochHours !== null ? <> (about <T>{fmtNum(t.epochHours, { decimals: 1 })}</T> h)</> : null}, so the on-chain figure moves in steps:{" "}
              <T>{fmtInt(epochs)}</T> epoch {epochs === 1 ? "mint has" : "mints have"} landed since the snapshot
              {stepped !== null && stepped > 0 ? (
                <>
                  , which at the snapshot&apos;s <T>{fmtNear(t.mintedPerEpoch)}</T> per epoch less gas burn implies <T>{signedNear(stepped)}</T>; the measured change is{" "}
                  <T>{fmtPct(delta / stepped, { decimals: 1 })}</T> of that
                </>
              ) : null}
              .
            </>
          )}
        </p>
      ) : null}
    </div>
  );
}
