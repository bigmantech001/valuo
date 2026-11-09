"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { fmtAgo, fmtBlock, fmtHash, fmtInt, fmtUtc } from "@/lib/format";
import { buildManifestIndex, explorerBlockUrl } from "@/lib/manifestIndex";
import type { Freshness, Integrity, Manifest, RawRecord, Snapshot } from "@/lib/types";
import type { BadgeVariant } from "@/components/ui/Badge";
import { Button, LinkButton } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { ProvenanceDrawer } from "./ProvenanceDrawer";
import { ReproduceButton } from "./ReproduceButton";

/** The slice of the snapshot the bar needs; a full Snapshot satisfies it, but passing the slice keeps the client payload small. */
export type ProvenanceBarSnapshot = Pick<Snapshot, "generated_at_utc" | "near_rpc" | "schema_version" | "valuo_version" | "seed">;

export interface ProvenanceBarProps {
  snapshot: ProvenanceBarSnapshot | null;
  manifest: Manifest | null;
  /** server-computed values for first paint; the bar re-polls /api/snapshot?format=freshness */
  initialFreshness?: Freshness | null;
  initialIntegrity?: Integrity | null;
  /** poll interval in ms (default 60 s; 0 disables) */
  pollMs?: number;
}

/**
 * Site header for the terminal: wordmark, navigation, the source-verification drawer and the
 * memo/JSON downloads, with a second line naming the snapshot block, its time and its age
 * against the live chain head. Every figure is read from the snapshot or the freshness poll.
 */
export function ProvenanceBar({ snapshot, manifest, initialFreshness = null, initialIntegrity = null, pollMs = 60_000 }: ProvenanceBarProps) {
  const [drawer, setDrawer] = useState(false);
  const [freshness, setFreshness] = useState<Freshness | null>(initialFreshness);
  const [integrity, setIntegrity] = useState<Integrity | null>(initialIntegrity);
  const index = useMemo(() => buildManifestIndex(manifest), [manifest]);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await fetch("/api/snapshot?format=freshness", { cache: "no-store" });
        const d = (await r.json()) as { freshness?: Freshness | null; integrity?: Integrity | null };
        if (cancelled) return;
        if (d.freshness) setFreshness(d.freshness);
        if (d.integrity) setIntegrity(d.integrity);
      } catch {
        // keep the previous reading; the pill shows its own age
      }
    };
    if (!initialFreshness) void poll();
    if (!pollMs) return;
    const id = setInterval(poll, pollMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollMs, initialFreshness]);

  const rpc = snapshot?.near_rpc ?? null;
  const blockRecord = firstRecord(index.bySource("near_rpc"), ["block"]);
  const fresh = freshnessTone(freshness);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-border bg-canvas/90 backdrop-blur supports-[backdrop-filter]:bg-canvas/80">
        <div className="mx-auto flex max-w-none flex-wrap items-center gap-x-8 gap-y-2 px-6 lg:px-[1.25vw] py-3">
          <Link href="/" className="font-serif text-[22px] font-medium leading-none tracking-tight text-ink">
            Valuo
          </Link>
          <nav aria-label="Primary" className="flex items-center gap-5 text-[14px]">
            <Link href="/" className="text-muted hover:text-ink">
              Overview
            </Link>
            <Link href="/terminal" className="text-ink">
              Terminal
            </Link>
          </nav>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <ReproduceButton />
            <Button variant="secondary" size="xs" onClick={() => setDrawer(true)} disabled={!manifest} title={manifest ? `${fmtInt(manifest.records.length)} raw payloads hashed; snapshot ${fmtHash(manifest.snapshot_sha256, 12)}` : "no manifest.json"}>
              {integrity?.matches === true ? <span className="h-1.5 w-1.5 rounded-full bg-emerald" aria-hidden /> : integrity?.matches === false ? <span className="h-1.5 w-1.5 rounded-full bg-crimson" aria-hidden /> : null}
              Verify sources
            </Button>
            <LinkButton href="/api/snapshot?format=memo" download variant="primary" size="xs" aria-disabled={!snapshot} className={cn(!snapshot && "pointer-events-none opacity-50")}>
              Download IC memo
            </LinkButton>
            <LinkButton href="/api/snapshot?format=json" download variant="ghost" size="xs" aria-disabled={!snapshot} className={cn(!snapshot && "pointer-events-none opacity-50")}>
              JSON
            </LinkButton>
          </div>
        </div>
        <div className="border-t border-border/70">
          <div className="tnum mx-auto flex max-w-none flex-wrap items-center gap-x-2 gap-y-1 px-6 lg:px-[1.25vw] py-1.5 text-[12.5px] text-muted">
            {rpc ? (
              <>
                <span>
                  NEAR block{" "}
                  <a href={explorerBlockUrl(rpc.block_height)} target="_blank" rel="noreferrer" className="text-ink hover:text-accent" title={rpc.block_hash}>
                    {fmtInt(rpc.block_height)}
                  </a>
                </span>
                <Sep />
                <span>Snapshot {snapshot ? fmtUtc(snapshot.generated_at_utc) : "n/a"} UTC</span>
                <Sep />
                <Tooltip wide content={fresh.detail}>
                  <span tabIndex={0} className={cn("cursor-help", FRESH_TEXT[fresh.variant])}>
                    {fresh.text}
                  </span>
                </Tooltip>
                {blockRecord ? (
                  <>
                    <Sep />
                    <ProvenanceBadge record={blockRecord} label="read from NEAR RPC" />
                  </>
                ) : null}
              </>
            ) : (
              <span>No snapshot loaded</span>
            )}
          </div>
        </div>
      </header>
      <ProvenanceDrawer open={drawer} onClose={() => setDrawer(false)} manifest={manifest} integrity={integrity} />
    </>
  );
}

const FRESH_TEXT: Record<BadgeVariant, string> = {
  "verified-chain": "text-emerald",
  "verified-api": "text-emerald",
  derived: "text-muted",
  assumption: "text-amber",
  "not-supported": "text-crimson",
  ok: "text-emerald",
  warn: "text-amber",
  error: "text-crimson",
  neutral: "text-muted",
  info: "text-muted",
  accent: "text-accent",
};

function Sep() {
  return (
    <span aria-hidden className="text-border-strong">
      /
    </span>
  );
}

function firstRecord(records: RawRecord[], needles: string[]): RawRecord | null {
  for (const n of needles) {
    const hit = records.find((r) => r.name.toLowerCase().includes(n) || r.url.toLowerCase().includes(n));
    if (hit) return hit;
  }
  return null;
}

export function freshnessTone(f: Freshness | null): { variant: BadgeVariant; text: string; detail: string } {
  if (!f) return { variant: "neutral", text: "Checking freshness", detail: "waiting for the live head" };
  if (f.live_block === null) return { variant: "warn", text: "Live RPC unreachable", detail: `${f.rpc_endpoint}: ${f.error ?? "no answer"}` };
  const behind = f.blocks_behind;
  const secs = f.seconds_behind;
  const detail = `live head #${fmtInt(f.live_block)} (${f.rpc_endpoint}); snapshot ${behind === null ? "n/a" : `${fmtInt(behind)} blocks`} behind, ${secs === null ? "n/a" : fmtAgo(secs).replace(" ago", " old")}; checked ${fmtUtc(f.checked_at_utc, { seconds: true })}`;
  if (secs === null) return { variant: "neutral", text: `Live head ${fmtBlock(f.live_block)}`, detail };
  if (secs < 3600) return { variant: "ok", text: `Current (${fmtInt(behind)} blocks behind head)`, detail };
  if (secs < 86_400) return { variant: "warn", text: `${fmtAgo(secs).replace(" ago", " old")}, ${fmtInt(behind)} blocks behind head`, detail };
  return { variant: "error", text: `${fmtAgo(secs).replace(" ago", " old")}; run make reproduce to refresh`, detail };
}
