"use client";

import { Fragment, useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Badge, Button, Card } from "@/components/ui";
import { MethodNote, SectionIntro } from "@/components/ui/Section";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { cn } from "@/lib/cn";
import { fmtBlock, fmtHash, fmtInt, fmtMs, fmtUtc } from "@/lib/format";
import type { AnalystAttestationSummary, AnalystContextItem, AnalystEvent, AnalystStatus } from "@/lib/analyst/types";

type Phase = "idle" | "retrieving" | "reasoning" | "writing" | "done" | "error";

interface Run {
  question: string;
  phase: Phase;
  answer: string;
  meta: Extract<AnalystEvent, { type: "meta" }> | null;
  done: Extract<AnalystEvent, { type: "done" }> | null;
  error: string | null;
}

const PHASE_LABEL: Partial<Record<Phase, string>> = {
  retrieving: "Selecting snapshot facts and calling NEAR AI",
  reasoning: "Model is reasoning over the context",
  writing: "Writing",
};

function parseSse(block: string): AnalystEvent | null {
  const data = block
    .split("\n")
    .filter((l) => l.startsWith("data:"))
    .map((l) => l.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  try {
    return JSON.parse(data) as AnalystEvent;
  } catch {
    return null;
  }
}

/** Answer text with [n] markers turned into chips that jump to the cited source. */
function AnswerText({ text, items, onCite }: { text: string; items: AnalystContextItem[]; onCite: (n: number) => void }) {
  const parts: ReactNode[] = [];
  const re = /\[(\d{1,3}(?:\s*[,;–-]\s*\d{1,3})*)\]/g;
  let last = 0;
  let k = 0;
  for (const m of text.matchAll(re)) {
    const idx = m.index ?? 0;
    if (idx > last) parts.push(<Fragment key={k++}>{text.slice(last, idx)}</Fragment>);
    const nums = m[1].split(/\s*[,;]\s*/).flatMap((p) => {
      const r = /^(\d+)\s*[–-]\s*(\d+)$/.exec(p);
      if (!r) return [Number(p)];
      const out: number[] = [];
      for (let n = Number(r[1]); n <= Number(r[2]) && out.length < 20; n++) out.push(n);
      return out;
    });
    parts.push(
      <span key={k++} className="whitespace-nowrap">
        {nums.map((n) => {
          const item = items.find((i) => i.n === n);
          return (
            <button
              key={n}
              type="button"
              onClick={() => item && onCite(n)}
              title={item ? item.ref : "This number is not one of the context items"}
              className={cn(
                "tnum mx-[1px] inline-flex min-w-[1.6em] items-center justify-center rounded border px-1 align-baseline text-[11.5px] leading-[1.45]",
                item ? "border-accent/30 bg-accent/5 text-accent hover:bg-accent/10" : "border-crimson/40 bg-crimson/5 text-crimson",
              )}
            >
              {n}
            </button>
          );
        })}
      </span>,
    );
    last = idx + m[0].length;
  }
  if (last < text.length) parts.push(<Fragment key={k++}>{text.slice(last)}</Fragment>);
  return <div className="whitespace-pre-wrap break-words text-[15.5px] leading-relaxed text-ink">{parts}</div>;
}

const BASIS_LABEL: Record<AnalystContextItem["basis"], string> = {
  raw: "Traced to raw payloads",
  model: "Model output or assumption",
  memo: "IC memo prose",
};

function SourceRow({ item, memoSha, highlight, id }: { item: AnalystContextItem; memoSha: string | null; highlight: boolean; id: string }) {
  return (
    <li id={id} className={cn("scroll-mt-24 px-4 py-3 transition-colors", highlight && "bg-accent/5")}>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="tnum inline-flex min-w-[1.8em] justify-center rounded border border-border-strong px-1 text-[12px] text-ink">{item.n}</span>
        <span className="min-w-0 break-all font-mono text-[12.5px] text-ink">{item.kind === "memo" ? `IC_MEMO.md § ${item.ref}` : item.ref}</span>
        <Badge variant={item.basis === "raw" ? "verified-api" : item.basis === "memo" ? "neutral" : "derived"} size="xs">
          {BASIS_LABEL[item.basis]}
        </Badge>
      </div>
      {item.label && item.label !== item.ref && item.kind !== "memo" ? <div className="mt-1 text-[13px] text-muted">{item.label}</div> : null}
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
        {item.records.map((r) => (
          <span key={`${r.source}/${r.name}`} className="inline-flex flex-wrap items-baseline gap-1.5">
            <ProvenanceBadge source={r.source} name={r.name} label={`${r.source}/${r.name}`} />
            <span className="tnum font-mono text-[11.5px] text-dim" title={r.sha256}>
              {fmtHash(r.sha256, 12)}
            </span>
          </span>
        ))}
        {item.kind === "memo" && memoSha ? (
          <span className="font-mono text-[11.5px] text-dim" title={memoSha}>
            memo sha256 {fmtHash(memoSha, 12)}
          </span>
        ) : null}
      </div>
    </li>
  );
}

function AttestationLine({ attestation, signature }: { attestation: AnalystAttestationSummary | null; signature: Extract<AnalystEvent, { type: "done" }>["signature"] | null }) {
  const verified = signature?.status === "verified";
  return (
    <div className="space-y-1.5 text-[13px] leading-relaxed text-muted">
      <div className="flex flex-wrap items-center gap-2">
        {signature ? (
          verified ? (
            <Badge variant="ok" dot>
              Verified by NEAR AI attestation
            </Badge>
          ) : (
            <Badge variant={signature.status === "unavailable" ? "neutral" : "warn"} dot>
              Response signature {signature.status}
            </Badge>
          )
        ) : null}
        {signature ? <span>{signature.detail}</span> : null}
      </div>
      {attestation ? (
        <div>
          {attestation.error ? (
            <span className="text-amber">Attestation preflight: {attestation.error}. </span>
          ) : (
            <span>
              Attestation preflight {fmtUtc(attestation.fetched_at_utc, { seconds: true })}: report {attestation.nonce_bound ? "echoes our nonce" : "nonce not echoed"}; gateway key{" "}
              <span className="font-mono text-[11.5px] text-ink">{fmtHash(attestation.gateway_signing_address, 12)}</span>
              {attestation.model_signers.length ? (
                <>
                  , model key <span className="font-mono text-[11.5px] text-ink">{attestation.model_signers.map((m) => fmtHash(m.signing_address, 12)).join(", ")}</span>
                </>
              ) : null}
              . The Intel TDX / NVIDIA quotes in the report are not re-verified here.{" "}
            </span>
          )}
          <a href={attestation.report_url} target="_blank" rel="noreferrer" className="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent">
            Attestation report
          </a>
          {" · "}
          <a href={attestation.verify_url} target="_blank" rel="noreferrer" className="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent">
            Verify hardware quote at cloud.near.ai/verify
          </a>
        </div>
      ) : null}
      {signature?.chat_id ? (
        <div className="break-all font-mono text-[11.5px] text-dim">
          completion {signature.chat_id} · sha256(request) {fmtHash(signature.request_sha256, 12)} · sha256(response) {fmtHash(signature.response_sha256, 12)}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Tab 7: ask the IC analyst. Questions go to /api/analyst, which retrieves numbered facts from the
 * loaded snapshot and IC memo and streams NEAR AI's answer. No answer is produced in the browser or
 * without NEAR AI; with no key configured the panel says so and offers nothing else.
 */
export function AnalystPanel() {
  const [status, setStatus] = useState<AnalystStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [highlight, setHighlight] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/analyst", { cache: "no-store" })
      .then(async (r) => {
        const j = (await r.json()) as AnalystStatus & { error?: string };
        if (!alive) return;
        if (!r.ok) setStatusError(j.error ?? `HTTP ${r.status}`);
        else setStatus(j);
      })
      .catch(() => alive && setStatusError("Could not reach /api/analyst."));
    return () => {
      alive = false;
      abortRef.current?.abort();
    };
  }, []);

  const busy = run !== null && (run.phase === "retrieving" || run.phase === "reasoning" || run.phase === "writing");
  const maxChars = status?.max_question_chars ?? 600;

  const ask = useCallback(
    async (q: string) => {
      const text = q.trim();
      if (!text || busy) return;
      abortRef.current?.abort();
      const ctl = new AbortController();
      abortRef.current = ctl;
      setHighlight(null);
      setRun({ question: text, phase: "retrieving", answer: "", meta: null, done: null, error: null });
      const update = (fn: (r: Run) => Run) => setRun((r) => (r ? fn(r) : r));
      try {
        const res = await fetch("/api/analyst", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: text }), signal: ctl.signal });
        const ctype = res.headers.get("content-type") ?? "";
        if (!res.ok || !ctype.includes("text/event-stream") || !res.body) {
          let msg = `HTTP ${res.status}`;
          try {
            const j = (await res.json()) as { error?: string };
            if (j.error) msg = j.error;
          } catch {
            /* keep HTTP status */
          }
          update((r) => ({ ...r, phase: "error", error: msg }));
          return;
        }
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        let ended = false;
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          let sep: number;
          while ((sep = buf.indexOf("\n\n")) >= 0) {
            const ev = parseSse(buf.slice(0, sep));
            buf = buf.slice(sep + 2);
            if (!ev) continue;
            if (ev.type === "meta") update((r) => ({ ...r, meta: ev }));
            else if (ev.type === "reasoning") update((r) => ({ ...r, phase: r.answer ? r.phase : "reasoning" }));
            else if (ev.type === "delta") update((r) => ({ ...r, phase: "writing", answer: r.answer + ev.text }));
            else if (ev.type === "done") {
              ended = true;
              update((r) => ({ ...r, phase: "done", done: ev }));
            } else if (ev.type === "error") {
              ended = true;
              update((r) => ({ ...r, phase: "error", error: ev.error }));
            }
          }
        }
        if (!ended) update((r) => ({ ...r, phase: "error", error: "The stream ended before NEAR AI finished the answer." }));
      } catch (e) {
        if (ctl.signal.aborted) {
          update((r) => (r.phase === "done" || r.phase === "error" ? r : { ...r, phase: "error", error: "Stopped before NEAR AI finished the answer." }));
          return;
        }
        update((r) => ({ ...r, phase: "error", error: e instanceof Error ? `Request failed: ${e.message}` : "Request failed." }));
      }
    },
    [busy],
  );

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void ask(question);
  };

  const onCite = (n: number) => {
    setHighlight(n);
    document.getElementById(`analyst-src-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  const items = run?.meta?.items ?? [];
  const citedSet = new Set(run?.done?.cited ?? []);
  const citedItems = items.filter((i) => citedSet.has(i.n));
  const otherItems = items.filter((i) => !citedSet.has(i.n));
  const configured = status?.configured ?? false;

  return (
    <div className="space-y-6">
      <SectionIntro eyebrow="Ask the analyst · NEAR AI" title="Questions answered only from this snapshot, with every claim cited">
        Each question retrieves numbered facts from <code className="font-mono text-[13px] text-ink">latest_snapshot.json</code> and <code className="font-mono text-[13px] text-ink">IC_MEMO.md</code>, sends only those to a model on NEAR AI Cloud, and
        maps every citation back to its JSON path and SHA-256-hashed raw payload. If the snapshot does not contain the answer, the analyst is instructed to say so.
      </SectionIntro>

      <Card
        kicker={status ? `Model ${status.model}${status.model_source === "default" ? " (default)" : ""} · NEAR AI Cloud` : "NEAR AI Cloud"}
        title="Ask a question"
        subtitle={
          status?.snapshot_sha256 ? (
            <span>
              Grounded on snapshot <span className="font-mono text-[12px] text-ink" title={status.snapshot_sha256}>{fmtHash(status.snapshot_sha256, 12)}</span> at block {fmtBlock(status.block_height)} ({fmtInt(status.n_facts)} addressable facts, {fmtInt(status.n_memo_sections)} memo sections).
            </span>
          ) : undefined
        }
      >
        {statusError ? <p className="mb-3 text-[14px] text-crimson">{statusError}</p> : null}
        {status && !configured ? (
          <div className="mb-4 rounded-md border border-amber/40 bg-amber/5 px-4 py-3 text-[14.5px] text-ink" role="status">
            {status.message}
          </div>
        ) : null}
        <form onSubmit={onSubmit} className="space-y-3">
          <label htmlFor="analyst-question" className="sr-only">
            Question for the IC analyst
          </label>
          <textarea
            id="analyst-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value.slice(0, maxChars))}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                void ask(question);
              }
            }}
            rows={3}
            maxLength={maxChars}
            placeholder="e.g. What share of intents.near callers are AI agents?"
            disabled={!configured}
            className="block w-full resize-y rounded-md border border-border-strong bg-surface px-3 py-2 text-[16px] leading-relaxed text-ink placeholder:text-dim focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 disabled:cursor-not-allowed disabled:bg-surface-2/60 lg:text-[14.5px]"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="tnum text-[12.5px] text-dim">
              {question.length}/{maxChars}
            </span>
            <div className="flex flex-wrap items-center gap-2">
              {busy ? (
                <Button variant="ghost" onClick={() => abortRef.current?.abort()}>
                  Stop
                </Button>
              ) : null}
              <Button type="submit" variant="primary" size="md" loading={busy} disabled={!configured || !question.trim()}>
                Ask NEAR AI
              </Button>
            </div>
          </div>
        </form>
        {status?.suggestions.length ? (
          <div className="mt-4">
            <div className="mb-2 text-[12.5px] text-dim">Suggested from this snapshot</div>
            <div className="flex flex-wrap gap-2">
              {status.suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled={!configured || busy}
                  onClick={() => {
                    setQuestion(s);
                    void ask(s);
                  }}
                  className="max-w-full rounded-md border border-border bg-surface-2/60 px-3 py-1.5 text-left text-[13.5px] text-ink transition-colors hover:border-border-strong hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50 max-lg:min-h-9"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </Card>

      {run ? (
        <Card kicker="Answer" title={run.question} bodyClassName="space-y-5">
          {run.phase === "error" ? (
            <div className="rounded-md border border-crimson/30 bg-crimson/5 px-4 py-3 text-[14.5px] text-crimson" role="alert">
              {run.error}
            </div>
          ) : null}
          {run.answer ? (
            <AnswerText text={run.answer} items={items} onCite={onCite} />
          ) : busy ? (
            <div className="flex items-center gap-2 text-[14px] text-muted" aria-live="polite">
              <span aria-hidden className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
              {PHASE_LABEL[run.phase]}
            </div>
          ) : null}
          {run.answer && busy ? <div className="text-[12.5px] text-dim">{PHASE_LABEL[run.phase]}</div> : null}

          {run.meta ? (
            <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-border pt-3 text-[12.5px] text-muted">
              <span>
                Answered by <span className="font-mono text-ink">{run.meta.model}</span> on NEAR AI Cloud
              </span>
              <span>
                Grounded on snapshot <span className="font-mono text-ink" title={run.meta.snapshot_sha256 ?? undefined}>{fmtHash(run.meta.snapshot_sha256, 12)}</span> · block {fmtBlock(run.meta.block_height)} · {fmtUtc(run.meta.snapshot_generated_at_utc)}
              </span>
              {run.done ? <span className="tnum">{fmtMs(run.done.elapsed_ms)}</span> : null}
            </div>
          ) : null}

          {run.done ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-[13px] text-muted">
                <Badge variant={run.done.figure_check.ungrounded.length ? "warn" : "ok"} dot>
                  {fmtInt(run.done.figure_check.grounded)} of {fmtInt(run.done.figure_check.total)} figures found in the context
                </Badge>
                {run.done.figure_check.ungrounded.length ? <span>Not found in the context: {run.done.figure_check.ungrounded.join(", ")}</span> : null}
                {run.done.invalid_citations.length ? <Badge variant="error">Cites missing items {run.done.invalid_citations.join(", ")}</Badge> : null}
                {run.done.finish_reason && run.done.finish_reason !== "stop" ? <Badge variant="warn">finish_reason {run.done.finish_reason}</Badge> : null}
              </div>
              <AttestationLine attestation={run.meta?.attestation ?? null} signature={run.done.signature} />
            </div>
          ) : null}

          {run.meta ? (
            <div className="space-y-3">
              {run.done ? (
                <div>
                  <h3 className="mb-2 text-[13px] font-medium text-ink">Cited sources ({citedItems.length})</h3>
                  {citedItems.length ? (
                    <ul className="divide-y divide-border overflow-hidden rounded-md border border-border">
                      {citedItems.map((i) => (
                        <SourceRow key={i.n} id={`analyst-src-${i.n}`} item={i} memoSha={run.meta?.memo_sha256 ?? null} highlight={highlight === i.n} />
                      ))}
                    </ul>
                  ) : (
                    <p className="text-[13.5px] text-muted">The answer cites no context item.</p>
                  )}
                </div>
              ) : null}
              <MethodNote summary={`${run.done ? "Other context items sent" : "Context items sent"} (${run.done ? otherItems.length : items.length})`}>
                <p>
                  Retrieval is BM25 keyword scoring over snapshot JSON paths, field names, labels and the memo&apos;s section text; the top items within a size budget are sent as numbered context. Values are sent exactly as stored in the snapshot.
                </p>
                <ul className="-mx-4 divide-y divide-border border-t border-border">
                  {(run.done ? otherItems : items).map((i) => (
                    <SourceRow key={i.n} id={`analyst-src-${i.n}`} item={i} memoSha={run.meta?.memo_sha256 ?? null} highlight={highlight === i.n} />
                  ))}
                </ul>
              </MethodNote>
            </div>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
