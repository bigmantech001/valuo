"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ReproduceJob } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";

/**
 * "Re-run reproduce" control. Hidden unless the server reports VALUO_ALLOW_REPRODUCE=1. Starts
 * `uv run python -m valuo.reproduce` through /api/reproduce, polls /api/reproduce/status, and
 * refreshes the server-rendered page when the job succeeds so the new snapshot is shown.
 */
export function ReproduceButton({ args = [] }: { args?: string[] }) {
  const router = useRouter();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [job, setJob] = useState<ReproduceJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/reproduce", { cache: "no-store" })
      .then((r) => r.json())
      .then((d: { enabled?: boolean; jobs?: ReproduceJob[] }) => {
        if (cancelled) return;
        setEnabled(Boolean(d.enabled));
        const running = d.jobs?.find((j) => j.status === "running");
        if (running) setJob(running);
      })
      .catch(() => !cancelled && setEnabled(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  }, []);

  useEffect(() => {
    if (!job || job.status !== "running") return;
    timer.current = setInterval(async () => {
      try {
        const r = await fetch(`/api/reproduce/status?id=${job.id}`, { cache: "no-store" });
        const d = (await r.json()) as { job?: ReproduceJob };
        if (d.job) {
          setJob(d.job);
          if (d.job.status !== "running") {
            stopPolling();
            if (d.job.status === "succeeded") router.refresh();
          }
        }
      } catch {
        // transient poll failure; keep polling
      }
    }, 2000);
    return stopPolling;
  }, [job, router, stopPolling]);

  const start = async () => {
    setError(null);
    try {
      const r = await fetch("/api/reproduce", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ args }) });
      const d = (await r.json()) as { job?: ReproduceJob; error?: string };
      if (!r.ok && !d.job) setError(d.error ?? `HTTP ${r.status}`);
      if (d.job) setJob(d.job);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  if (!enabled) return null;
  const running = job?.status === "running";
  const lastLine = job ? [...job.stdout_tail, ...job.stderr_tail].slice(-1)[0] : null;
  return (
    <div className="flex items-center gap-2">
      <Tooltip
        wide
        content={
          <div>
            Runs <code className="font-mono">uv run python -m valuo.reproduce{args.length ? ` ${args.join(" ")}` : ""}</code> in <code className="font-mono">quant/</code>: re-fetches NEAR mainnet state and router quotes, re-runs the seeded Monte Carlo and rewrites <code className="font-mono">artifacts/</code>. Typically 60 to 90 seconds.
          </div>
        }
      >
        <Button variant="accent" size="xs" onClick={start} loading={running} disabled={running}>
          {running ? "Re-running pipeline" : "Re-run pipeline"}
        </Button>
      </Tooltip>
      {job && !running ? (
        <Badge variant={job.status === "succeeded" ? "ok" : "error"} dot title={job.error ?? lastLine ?? undefined}>
          {job.status === "succeeded" ? "Succeeded" : job.status === "failed" ? "Failed" : job.status}
          {job.exit_code !== null ? `, exit ${job.exit_code}` : ""}
        </Badge>
      ) : null}
      {running && lastLine ? <span className="max-w-[20rem] truncate font-mono text-[12px] text-muted" title={lastLine}>{lastLine}</span> : null}
      {error ? <span className="text-[12px] text-crimson">{error}</span> : null}
    </div>
  );
}
