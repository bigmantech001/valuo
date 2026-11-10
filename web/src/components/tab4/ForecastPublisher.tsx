"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge, Button, Card } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
import { fmtBps, fmtHash, fmtPct, fmtUsd } from "@/lib/format";
import {
  SOCIAL_CONTRACT,
  FORECAST_GAS,
  addMonthsUtc,
  buildForecastValue,
  buildSetAction,
  buildSetArgs,
  depositFor,
  forecastKey,
  validDate,
  yoctoToNear,
  type StorageBalance,
} from "@/lib/forecast";
import { explorerAccountUrl, explorerTxUrl } from "@/lib/manifestIndex";
import { activeAccountId, failureOf, loadWallet, txHashOf, type WalletHandle } from "@/lib/nearWallet";
import { REGIME_NAME } from "./fmt";
import type { SliderState } from "./sliderModel";

export interface ScenarioSnapshot {
  state: SliderState;
  implied_price: number | null;
}

export interface ForecastPublisherProps {
  scenario: ScenarioSnapshot | null;
  horizonMonths: number;
  snapshotSha256: string | null;
  snapshotGeneratedAt: string | null;
  spotUsd: number | null;
  onPublished: (account: string) => void;
}

type Status =
  | { kind: "idle" }
  | { kind: "busy"; step: string }
  | { kind: "success"; account: string; key: string; hash: string | null }
  | { kind: "error"; message: string; rejected: boolean };

const INPUT =
  "h-11 w-full min-w-0 rounded-md border border-border-strong bg-surface px-3 text-base text-ink tnum focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 disabled:opacity-50 lg:h-9 lg:text-[14px]";

const REJECT_RE = /reject|cancel|denied|declin|closed|user.*abort/i;

function errText(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  try {
    return JSON.stringify(e).slice(0, 400);
  } catch {
    return String(e);
  }
}

/**
 * "Publish your forecast": takes the scenario panel's current slider state and the model price it implies, adds the
 * visitor's own price target and resolution date, and has their wallet sign one `social.near` `set` call that stores
 * the forecast under <account>/valuo/forecast/<UTC timestamp>. Nothing is written without the wallet's approval.
 */
export function ForecastPublisher({ scenario, horizonMonths, snapshotSha256, snapshotGeneratedAt, spotUsd, onPublished }: ForecastPublisherProps) {
  const [wallet, setWallet] = useState<WalletHandle | null>(null);
  const [account, setAccount] = useState<string | null>(null);
  const [targetStr, setTargetStr] = useState<string>("");
  const [targetTouched, setTargetTouched] = useState(false);
  const [horizon, setHorizon] = useState<string>("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [connecting, setConnecting] = useState(false);

  // Defaults: target follows the model price until the visitor types one; horizon = the model horizon from today.
  const implied = scenario?.implied_price ?? null;
  useEffect(() => {
    if (!targetTouched && implied !== null && Number.isFinite(implied) && implied > 0) setTargetStr(implied.toFixed(3));
  }, [implied, targetTouched]);
  useEffect(() => {
    if (!horizon) setHorizon(addMonthsUtc(new Date(), horizonMonths));
  }, [horizon, horizonMonths]);

  // Restore a wallet session from an earlier visit without loading the selector for visitors who never connected.
  useEffect(() => {
    let cancelled = false;
    let unsub: (() => void) | null = null;
    const hasSession = typeof window !== "undefined" && Object.keys(window.localStorage).some((k) => k.startsWith("near-wallet-selector"));
    if (!hasSession) return;
    loadWallet()
      .then((w) => {
        if (cancelled) return;
        setWallet(w);
        setAccount(activeAccountId(w.selector));
        const sub = w.selector.store.observable.subscribe((s) => setAccount(s.accounts.find((a) => a.active)?.accountId ?? s.accounts[0]?.accountId ?? null));
        unsub = () => sub.unsubscribe();
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
      unsub?.();
    };
  }, []);

  const connect = useCallback(async () => {
    setConnecting(true);
    setStatus({ kind: "idle" });
    try {
      const w = wallet ?? (await loadWallet());
      if (!wallet) {
        setWallet(w);
        w.selector.store.observable.subscribe((s) => setAccount(s.accounts.find((a) => a.active)?.accountId ?? s.accounts[0]?.accountId ?? null));
      }
      w.modal.show();
    } catch (e) {
      setStatus({ kind: "error", message: `Could not load the wallet selector: ${errText(e)}`, rejected: false });
    } finally {
      setConnecting(false);
    }
  }, [wallet]);

  const disconnect = useCallback(async () => {
    if (!wallet) return;
    try {
      const w = await wallet.selector.wallet();
      await w.signOut();
    } catch (e) {
      setStatus({ kind: "error", message: `Sign-out failed: ${errText(e)}`, rejected: false });
    }
    setAccount(activeAccountId(wallet.selector));
  }, [wallet]);

  const target = Number(targetStr);
  const minDate = useMemo(() => {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() + 1);
    return d.toISOString().slice(0, 10);
  }, []);
  const maxDate = useMemo(() => addMonthsUtc(new Date(), 120), []);

  const draft = useMemo(() => {
    if (!scenario || !snapshotSha256) return { value: null, error: !snapshotSha256 ? "The manifest has no snapshot hash, so a forecast cannot reference a snapshot." : "The scenario model is not available on this snapshot." };
    if (!(Number.isFinite(target) && target > 0)) return { value: null, error: "Enter a price target above $0." };
    if (!validDate(horizon) || horizon < minDate || horizon > maxDate) return { value: null, error: `Pick a resolution date between ${minDate} and ${maxDate}.` };
    try {
      const value = buildForecastValue({
        now: new Date(),
        snapshot_sha256: snapshotSha256,
        snapshot_generated_at: snapshotGeneratedAt,
        spot_usd: spotUsd,
        price_target_usd: target,
        horizon,
        implied_price_usd: scenario.implied_price,
        horizon_months: horizonMonths,
        settings: scenario.state,
      });
      return { value, error: null as string | null };
    } catch (e) {
      return { value: null, error: errText(e) };
    }
  }, [scenario, snapshotSha256, snapshotGeneratedAt, spotUsd, target, horizon, horizonMonths, minDate, maxDate]);

  const publish = useCallback(async () => {
    if (!wallet || !account || !draft.value) return;
    const now = new Date();
    const value = { ...draft.value, created_at: now.toISOString().replace(/\.\d{3}Z$/, "Z") };
    const key = forecastKey(now);
    try {
      setStatus({ kind: "busy", step: "Reading your SocialDB storage balance" });
      const res = await fetch(`/api/forecasts?storage_for=${encodeURIComponent(account)}`, { cache: "no-store" });
      const body = (await res.json()) as { balance?: StorageBalance | null; bounds?: { min: string } | null; error?: string };
      if (!res.ok) throw new Error(body.error ?? `storage check failed (HTTP ${res.status})`);
      const args = buildSetArgs(account, key, value);
      const dep = depositFor(body.balance ?? null, body.bounds?.min ? BigInt(body.bounds.min) : null, args);
      setStatus({ kind: "busy", step: `Waiting for your wallet to approve (deposit ${yoctoToNear(dep.deposit)} NEAR)` });
      const [w, { internalActionToNaj }] = await Promise.all([wallet.selector.wallet(), import("@near-wallet-selector/core")]);
      const outcome = await w.signAndSendTransaction({ signerId: account, receiverId: SOCIAL_CONTRACT, actions: [internalActionToNaj(buildSetAction(args, dep.deposit))] });
      const failure = failureOf(outcome);
      if (failure) throw new Error(`The transaction executed but failed: ${failure}`);
      setStatus({ kind: "success", account, key, hash: txHashOf(outcome) });
      onPublished(account);
    } catch (e) {
      const msg = errText(e);
      setStatus({ kind: "error", message: msg, rejected: REJECT_RE.test(msg) });
    }
  }, [wallet, account, draft.value, onPublished]);

  const s = scenario?.state;
  const busy = status.kind === "busy";
  const presets = [
    { label: "12 months", months: 12 },
    { label: "24 months", months: 24 },
    { label: `Model horizon, ${horizonMonths} months`, months: horizonMonths },
  ];

  return (
    <Card
      kicker="On-chain, NEAR SocialDB"
      title="Publish your forecast"
      subtitle="Sign one social.near write from your own NEAR account: the scenario settings above, the model price they imply, your price target and the date it resolves. The forecast board below reads every published forecast back from the chain and scores it against snapshot prices."
      actions={
        account ? (
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <a href={explorerAccountUrl(account)} target="_blank" rel="noreferrer" className="max-w-[16rem] truncate font-mono text-[12.5px] text-accent hover:underline">
              {account}
            </a>
            <Button size="xs" variant="ghost" onClick={disconnect} disabled={busy}>
              Disconnect
            </Button>
          </div>
        ) : (
          <Badge variant="neutral">Not connected</Badge>
        )
      }
    >
      <div className="grid grid-cols-1 gap-x-10 gap-y-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="flex min-w-0 flex-col gap-5">
          <label className="flex min-w-0 flex-col gap-1">
            <span className="text-[13px] text-muted">Your NEAR price target, USD</span>
            <input
              className={INPUT}
              type="number"
              inputMode="decimal"
              min={0}
              step="0.001"
              value={targetStr}
              onChange={(e) => {
                setTargetTouched(true);
                setTargetStr(e.target.value);
              }}
              disabled={busy}
            />
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px] text-dim">
              <span className="tnum">
                Model at month {horizonMonths}: {fmtUsd(implied, { decimals: 3 })}; snapshot spot {fmtUsd(spotUsd, { decimals: 3 })}
              </span>
              {targetTouched && implied !== null ? (
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={() => {
                    setTargetTouched(false);
                    setTargetStr(implied.toFixed(3));
                  }}
                >
                  Use model price
                </Button>
              ) : null}
            </span>
          </label>
          <label className="flex min-w-0 flex-col gap-1">
            <span className="text-[13px] text-muted">Resolves on (UTC)</span>
            <input className={INPUT} type="date" min={minDate} max={maxDate} value={horizon} onChange={(e) => setHorizon(e.target.value)} disabled={busy} />
            <span className="flex flex-wrap gap-1.5 pt-1">
              {presets.map((p) => (
                <Button key={p.label} size="xs" variant="secondary" onClick={() => setHorizon(addMonthsUtc(new Date(), p.months))} disabled={busy}>
                  {p.label}
                </Button>
              ))}
            </span>
          </label>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {account ? (
              <Button variant="primary" size="md" onClick={publish} loading={busy} disabled={busy || !draft.value}>
                Sign and publish
              </Button>
            ) : (
              <Button variant="primary" size="md" onClick={connect} loading={connecting} disabled={connecting}>
                Connect NEAR wallet
              </Button>
            )}
            {account ? (
              <Button size="sm" variant="secondary" onClick={connect} disabled={busy || connecting}>
                Switch wallet
              </Button>
            ) : null}
          </div>
          {draft.error ? <p className="text-[13px] text-amber">{draft.error}</p> : null}
          <StatusLine status={status} />
        </div>

        <div className="min-w-0">
          <div className="text-[13px] text-muted">What gets written</div>
          <dl className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-5 gap-y-1.5 text-[13.5px]">
            <dt className="text-muted">Key</dt>
            <dd className="min-w-0 break-all font-mono text-[12.5px] text-ink">{account ?? "<your-account>"}/valuo/forecast/&lt;YYYYMMDDTHHMMSSZ&gt;</dd>
            <dt className="text-muted">Snapshot</dt>
            <dd className="min-w-0 break-all font-mono text-[12.5px] text-ink" title={snapshotSha256 ?? undefined}>
              {snapshotSha256 ? fmtHash(snapshotSha256, 16) : "n/a"}
            </dd>
            <dt className="text-muted">Target, horizon</dt>
            <dd className="tnum text-ink">
              {Number.isFinite(target) && target > 0 ? fmtUsd(target, { decimals: 3 }) : "n/a"} on {horizon || "n/a"}
              {spotUsd && Number.isFinite(target) && target > 0 ? <span className="text-muted"> ({fmtPct(target / spotUsd - 1, { decimals: 0, signed: true })} vs spot)</span> : null}
            </dd>
            <dt className="text-muted">Volume growth</dt>
            <dd className="tnum text-ink">{s ? fmtPct(s.growth_yoy, { decimals: 0, signed: true }) + " a year" : "n/a"}</dd>
            <dt className="text-muted">Public take</dt>
            <dd className="tnum text-ink">{s ? fmtBps(s.tau_pub_bps, { signed: false, decimals: 2 }) : "n/a"}</dd>
            <dt className="text-muted">Confidential</dt>
            <dd className="tnum text-ink">{s ? `${fmtPct(s.conf_share_target, { decimals: 1 })} share, ${fmtBps(s.tau_conf_bps, { signed: false, decimals: 2 })}` : "n/a"}</dd>
            <dt className="text-muted">Buyback share</dt>
            <dd className="tnum text-ink">{s ? fmtPct(s.alpha_capture, { decimals: 1 }) : "n/a"}</dd>
            <dt className="text-muted">Issuance</dt>
            <dd className="text-ink">{s ? (REGIME_NAME[s.regime] ?? s.regime) : "n/a"}</dd>
            <dt className="text-muted">Deposit</dt>
            <dd className="text-ink">0.01 NEAR, plus 0.02 NEAR the first time an account writes to SocialDB (storage registration). It stays in your SocialDB storage balance.</dd>
          </dl>
          {draft.value ? (
            <details className="mt-3 rounded-md border border-border bg-surface-2/60 text-[12.5px] text-muted">
              <summary className="cursor-pointer px-3 py-2 hover:text-ink">Exact value</summary>
              <pre className="valuo-scroll max-h-64 overflow-auto whitespace-pre-wrap break-all border-t border-border px-3 py-2 font-mono text-[11.5px] text-ink">{JSON.stringify(draft.value, null, 1)}</pre>
            </details>
          ) : null}
        </div>
      </div>
      <MethodNote className="mt-6">
        <p>
          One transaction from your account to <code>{SOCIAL_CONTRACT}</code>, method <code>set</code>, args <code>{"{data: {<account>: {valuo: {forecast: {<key>: <JSON string>}}}}}"}</code>, gas {Number(FORECAST_GAS) / 1e12} Tgas. SocialDB accepts writes only under the signer&apos;s own account and records the block height of every value, which the board shows. The key layout mirrors the snapshot anchors in <code>quant/valuo/anchor.py</code> (<code>&lt;account&gt;/valuo/snapshot/&lt;key&gt;</code>).
        </p>
        <p>
          Deposit: <code>storage_balance_of</code> is read first. An account without a SocialDB storage balance attaches <code>storage_balance_bounds.min</code> (0.02 NEAR on mainnet) plus 0.01 NEAR; a registered account attaches 0.01 NEAR (or 1.5 × the value&apos;s bytes × 10<sup>19</sup> yocto, if larger).
        </p>
        <p>The settings stored are the scenario panel&apos;s slider values; the model price is the panel&apos;s deterministic implied price at month {horizonMonths}. Signing in creates no access key for this site: every write is approved in your wallet.</p>
      </MethodNote>
    </Card>
  );
}

function StatusLine({ status }: { status: Status }) {
  if (status.kind === "idle") return null;
  if (status.kind === "busy") return <p className="text-[13px] text-muted">{status.step}…</p>;
  if (status.kind === "success") {
    return (
      <div className="rounded-md border border-emerald/30 bg-emerald/5 px-3 py-2 text-[13px] text-ink">
        <div className="font-medium text-emerald">Published on NEAR mainnet.</div>
        <div className="mt-1 break-all">
          Key <code className="font-mono text-[12px]">{`${status.account}/valuo/forecast/${status.key}`}</code>
        </div>
        {status.hash ? (
          <div className="mt-1 break-all">
            Transaction{" "}
            <a className="font-mono text-[12px] text-accent hover:underline" href={explorerTxUrl(status.hash)} target="_blank" rel="noreferrer">
              {status.hash}
            </a>
          </div>
        ) : (
          <div className="mt-1 text-muted">The wallet did not return a transaction hash; check your account on NearBlocks.</div>
        )}
      </div>
    );
  }
  return (
    <div className={cn("rounded-md border px-3 py-2 text-[13px]", status.rejected ? "border-border-strong bg-surface-2 text-muted" : "border-crimson/30 bg-crimson/5 text-crimson")}>
      <div className="font-medium">{status.rejected ? "The wallet did not approve the request. Nothing was written." : "The forecast was not published."}</div>
      <div className="mt-1 break-words">{status.message}</div>
    </div>
  );
}

