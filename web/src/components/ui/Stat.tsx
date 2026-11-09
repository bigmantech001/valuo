import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { fmtNum, NA } from "@/lib/format";
import type { Tone } from "@/lib/theme";
import type { RawRecord } from "@/lib/types";
import { ProvenanceBadge, type ProvenanceRef } from "@/components/provenance/ProvenanceBadge";

export interface StatDelta {
  value: ReactNode;
  tone?: Tone;
  /** e.g. "vs status quo" */
  label?: ReactNode;
}

export interface StatProps {
  label: ReactNode;
  /** number -> formatted with `format` (default fmtNum); null/undefined -> "n/a" */
  value: ReactNode | number | null | undefined;
  unit?: ReactNode;
  delta?: StatDelta;
  /** RawRecord, or {source, name} looked up in the manifest */
  provenance?: RawRecord | ProvenanceRef | null;
  tone?: Tone;
  /** one line of methodology under the value; keep it to a short clause */
  hint?: ReactNode;
  size?: "sm" | "md" | "lg";
  format?: (v: number) => string;
  className?: string;
}

/** Sign colour on the figure; the accent is reserved for links, so "accent" renders as ink. */
const VALUE_TONE: Record<Tone, string> = {
  neutral: "text-ink",
  emerald: "text-emerald",
  amber: "text-amber",
  crimson: "text-crimson",
  accent: "text-ink",
};

const DELTA_TONE: Record<Tone, string> = {
  neutral: "text-muted",
  emerald: "text-emerald",
  amber: "text-amber",
  crimson: "text-crimson",
  accent: "text-muted",
};

const VALUE_SIZE = { sm: "text-lg", md: "text-[26px]", lg: "text-4xl" } as const;

/**
 * A figure with its label, an optional change line, a one-line note and the source it was read
 * from. The source renders as a quiet text link whose tooltip carries the raw-payload record.
 */
export function Stat({ label, value, unit, delta, provenance, tone = "neutral", hint, size = "md", format, className }: StatProps) {
  const missing = value === null || value === undefined || (typeof value === "number" && !Number.isFinite(value));
  const rendered: ReactNode = missing ? NA : typeof value === "number" ? (format ?? fmtNum)(value) : value;
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5 bg-surface px-5 py-4", className)}>
      <div className="text-[13px] leading-snug text-muted first-letter:uppercase">{label}</div>
      <div className="flex items-baseline gap-1.5">
        <span
          className={cn("tnum font-medium leading-none tracking-tight", VALUE_SIZE[size], missing ? "text-dim" : VALUE_TONE[tone])}
          title={missing ? "Not available in this snapshot (fetch failed or not measured)" : undefined}
        >
          {rendered}
        </span>
        {unit && !missing ? <span className="text-sm text-muted">{unit}</span> : null}
      </div>
      {delta ? (
        <div className={cn("tnum text-[13px]", DELTA_TONE[delta.tone ?? "neutral"])}>
          {delta.value}
          {delta.label ? <span className="ml-1 text-muted">{delta.label}</span> : null}
        </div>
      ) : null}
      {hint ? <div className="text-[12.5px] leading-snug text-dim">{hint}</div> : null}
      {provenance ? (
        <div className="mt-auto pt-1">
          <ProvenanceBadge {...("sha256" in provenance ? { record: provenance } : { source: provenance.source, name: provenance.name })} />
        </div>
      ) : null}
    </div>
  );
}
