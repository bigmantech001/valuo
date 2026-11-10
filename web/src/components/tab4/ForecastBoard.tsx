"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, Table, type Column } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
import { fmtBlock, fmtBps, fmtHash, fmtInt, fmtPct, fmtUsd, fmtUtc } from "@/lib/format";
import type { ForecastBoardResponse } from "@/lib/forecast";
import { explorerAccountUrl, explorerBlockUrl } from "@/lib/manifestIndex";
import { REGIME_NAME } from "./fmt";

type Row = ForecastBoardResponse["forecasts"][number];

export interface ForecastBoardProps {
  /** bump to refetch (after a publish) */
  refreshKey: number;
  /** account just published from: read straight from social.near so it shows before the indexer catches up */
  account: string | null;
  /** manifest.snapshot_sha256 of the snapshot on this page */
  currentSnapshotSha256: string | null;
}

/**
 * Every forecast stored under <account>/valuo/forecast/* on social.near, newest write first, with its score against
 * the latest snapshot's NEAR price. Shows only what the API read from SocialDB; an empty list is reported as empty.
 */
export function ForecastBoard({ refreshKey, account, currentSnapshotSha256 }: ForecastBoardProps) {
  const [data, setData] = useState<ForecastBoardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [manual, setManual] = useState(0);

  const load = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/forecasts${account ? `?account=${encodeURIComponent(account)}` : ""}`, { cache: "no-store", signal });
      const body = (await res.json()) as ForecastBoardResponse;
      if (!res.ok) throw new Error(body.error ?? `HTTP ${res.status}`);
      setData(body);
    } catch (e) {
      if (signal.aborted) return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [account]);

  useEffect(() => {
    const c = new AbortController();
    void load(c.signal);
    return () => c.abort();
  }, [load, refreshKey, manual]);

  const realized = data?.realized ?? null;
  const rows = data?.forecasts ?? [];

  const columns: Column<Row>[] = [
    {
      key: "account",
      header: "Account",
      render: (r) => (
        <a href={explorerAccountUrl(r.account)} target="_blank" rel="noreferrer" className="block max-w-[11rem] truncate font-mono text-[12.5px] text-accent hover:underline" title={r.account}>
          {r.account}
        </a>
      ),
    },
    {
      key: "block",
      header: "Written",
      render: (r) => (
        <div className="whitespace-nowrap">
          {r.block_height ? (
            <a href={explorerBlockUrl(r.block_height)} target="_blank" rel="noreferrer" className="tnum text-accent hover:underline" title="Block at which SocialDB recorded the write">
              {fmtBlock(r.block_height)}
            </a>
          ) : (
            <span className="text-dim">block n/a</span>
          )}
          <div className="text-[12px] text-dim">{fmtUtc(r.value.created_at)}</div>
        </div>
      ),
    },
    { key: "target", header: "Target", numeric: true, render: (r) => fmtUsd(r.value.price_target_usd, { decimals: 3 }) },
    {
      key: "horizon",
      header: "Horizon",
      render: (r) =>
        r.score.status === "resolved" ? (
          <div className="whitespace-nowrap">
            <Badge variant="ok">Resolved</Badge> <span className="tnum">{r.value.horizon}</span>
          </div>
        ) : (
          <div className="whitespace-nowrap">
            <span className="tnum">Resolves on {r.value.horizon}</span>
            {Number.isFinite(r.score.days_to_horizon) ? <div className="tnum text-[12px] text-dim">in {fmtInt(r.score.days_to_horizon)} days</div> : null}
          </div>
        ),
    },
    {
      key: "score",
      header: "Score",
      numeric: true,
      title: "Resolved: target / realized − 1. Open: target / latest snapshot price − 1 (distance, not a score).",
      render: (r) => {
        const e = r.score.error_pct;
        if (e === null) return <span className="text-dim">n/a</span>;
        return r.score.status === "resolved" ? (
          <span className={cn("tnum font-medium", Math.abs(e) <= 0.1 ? "text-emerald" : "text-ink")} title={`scored on the snapshot price ${r.score.scored_days_after_horizon ?? 0} days after the horizon`}>
            {fmtPct(e, { decimals: 1, signed: true })} error
          </span>
        ) : (
          <span className="tnum text-muted">{fmtPct(e, { decimals: 0, signed: true })} vs spot</span>
        );
      },
    },
    { key: "model", header: "Model price", numeric: true, title: "Deterministic implied price at the model horizon for the stored settings", render: (r) => (r.value.model.implied_price_usd === null ? <span className="text-dim">n/a</span> : <span>{fmtUsd(r.value.model.implied_price_usd, { decimals: 3 })}{r.value.model.horizon_months ? <span className="text-[12px] text-dim"> M{r.value.model.horizon_months}</span> : null}</span>) },
    {
      key: "settings",
      header: "Settings",
      render: (r) => {
        const s = r.value.settings;
        return (
          <div className="tnum whitespace-nowrap text-[12.5px] leading-snug text-muted">
            <div>
              g {fmtPct(s.growth_yoy, { decimals: 0, signed: true })}, τ {fmtBps(s.tau_pub_bps, { signed: false, decimals: 1 })}, α {fmtPct(s.alpha_capture, { decimals: 1 })}
            </div>
            <div>
              conf {fmtPct(s.conf_share_target, { decimals: 0 })} at {fmtBps(s.tau_conf_bps, { signed: false, decimals: 0 })}
            </div>
            <div>{REGIME_NAME[s.regime] ?? s.regime}</div>
          </div>
        );
      },
    },
    {
      key: "snapshot",
      header: "Against",
      render: (r) => (
        <div className="whitespace-nowrap">
          <span className="font-mono text-[12px]" title={r.value.snapshot_sha256}>
            {fmtHash(r.value.snapshot_sha256, 8)}
          </span>
          <div className="mt-0.5 flex gap-1">
            {currentSnapshotSha256 && r.value.snapshot_sha256 === currentSnapshotSha256 ? <Badge variant="neutral">This snapshot</Badge> : null}
            {r.verified_onchain ? (
              <Badge variant="verified-chain" title="Read directly from social.near over NEAR RPC">
                On-chain
              </Badge>
            ) : (
              <Badge variant="warn" title="Listed by the indexer; the direct social.near read for this account failed or was skipped in this refresh">
                Indexer only
              </Badge>
            )}
          </div>
        </div>
      ),
    },
  ];

  const resolved = data?.resolved_count ?? 0;
  const confirmed = rows.filter((r) => r.verified_onchain).length;
  const listed = `${fmtInt(rows.length)} forecast${rows.length === 1 ? "" : "s"}${confirmed === rows.length ? " read from social.near" : `, ${fmtInt(confirmed)} confirmed by a direct social.near read`}`;
  const ix = data?.sources.indexer;

  return (
    <Card
      kicker="Read from social.near"
      title="Forecast board"
      subtitle="Every forecast published under */valuo/forecast/* on NEAR SocialDB, newest write first. A forecast is scored once the latest snapshot's price date reaches its horizon; until then the board shows how far the target is from the latest price."
      actions={
        <Button size="sm" variant="secondary" onClick={() => setManual((n) => n + 1)} loading={loading} disabled={loading}>
          Refresh
        </Button>
      }
      footer={
        data ? (
          <span>
            Read {fmtUtc(data.fetched_at)} (cached up to {data.cache_s} s). Discovery: {ix?.ok ? `${ix.url}, ${fmtInt(ix.accounts)} accounts` : `indexer unavailable (${ix?.error ?? "unknown error"})`}; confirmation: social.near <code className="font-mono text-[11.5px]">get</code> over {data.sources.rpc.url}
            {data.sources.rpc.failed_accounts ? `, ${fmtInt(data.sources.rpc.failed_accounts)} account reads failed` : ""}
            {data.sources.rpc.not_on_chain ? `, ${fmtInt(data.sources.rpc.not_on_chain)} indexer entries not found on social.near and dropped` : ""}
            {data.sources.rpc.unverified_reason ? `, ${data.sources.rpc.unverified_reason}` : ""}
            {data.rejected_entries ? `. ${fmtInt(data.rejected_entries)} malformed entries ignored` : ""}.
          </span>
        ) : null
      }
    >
      {error ? (
        <p className="text-[13.5px] text-crimson">The board could not be read: {error}</p>
      ) : !data ? (
        <p className="text-[13.5px] text-muted">Reading social.near…</p>
      ) : (
        <div className="space-y-4">
          <p className="text-[13.5px] leading-relaxed text-muted">
            {rows.length === 0 ? (
              <>No forecasts are stored under <code className="font-mono text-[12px]">*/valuo/forecast/*</code> on social.near yet. The first one published above will be the first row.</>
            ) : resolved === 0 ? (
              <>
                {listed}; none has reached its horizon, so none is scored yet.
                {realized ? ` The distance column compares each target with the latest snapshot price, ${fmtUsd(realized.price_usd, { decimals: 3 })} as of ${fmtUtc(realized.as_of)}; that is not a score.` : " The snapshot has no NEAR price, so no distance is shown."}
              </>
            ) : (
              <>
                {listed}; {fmtInt(resolved)} resolved; mean absolute error of resolved forecasts {fmtPct(data.mean_abs_error_pct_resolved, { decimals: 1 })} against the snapshot price {realized ? `${fmtUsd(realized.price_usd, { decimals: 3 })} as of ${fmtUtc(realized.as_of)}` : "n/a"}.
              </>
            )}
            {data.sources.extra_account_error ? <span className="text-amber"> Direct read of {data.sources.extra_account} failed: {data.sources.extra_account_error}.</span> : null}
          </p>
          {rows.length ? <Table columns={columns} rows={rows} rowKey={(r) => `${r.account}/${r.key}`} maxHeight="32rem" /> : null}
        </div>
      )}
      <MethodNote className="mt-6">
        <p>
          A wildcard-account <code>get</code> on social.near (<code>[&quot;*/valuo/forecast/*&quot;]</code>) exceeds the view-call gas limit on mainnet, so <code>/api/forecasts</code> lists accounts through the public SocialDB indexer (<code>api.near.social/get</code>, same key syntax), then re-reads each account from <code>social.near</code> over NEAR RPC with <code>with_block_height</code>. Where that read succeeds, the board shows what the chain returned (&quot;On-chain&quot;) and drops indexer entries the chain does not hold; where it fails, the indexer&apos;s entries are shown as &quot;Indexer only&quot;.
        </p>
        <p>
          Values are user-written. The API keeps only entries whose key is a UTC timestamp, whose schema is <code>valuo-forecast/1</code>, and whose numbers parse inside fixed bounds; everything else is dropped and counted. Text is rendered as text, never as HTML.
        </p>
        <p>
          Scoring uses only the snapshot: realized price = <code>intents_forensics.price.current_usd</code> at <code>price.fetched_at</code>. Resolved when that date is on or after the horizon; error = target / realized − 1. The snapshot has no daily price history, so a forecast whose horizon passed before the latest snapshot is scored on the latest snapshot price, and the gap in days is shown on hover.
        </p>
      </MethodNote>
    </Card>
  );
}
