"use client";

import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { fmtNum } from "@/lib/format";
import type { Tone } from "@/lib/theme";

export interface SliderMarker {
  value: number;
  label: string;
  tone?: Tone;
}

export interface SliderProps {
  label: ReactNode;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  /** value -> readout text (default 2-decimal number) */
  format?: (v: number) => string;
  /** reference tick on the track, e.g. the live measured competitive ceiling */
  marker?: SliderMarker | null;
  description?: ReactNode;
  disabled?: boolean;
  id?: string;
  className?: string;
}

const MARKER_TONE: Record<Tone, string> = {
  neutral: "bg-muted text-muted",
  emerald: "bg-emerald text-emerald",
  amber: "bg-amber text-amber",
  crimson: "bg-crimson text-crimson",
  accent: "bg-accent text-accent",
};

/** Range input with a tabular readout and an optional measured-value marker. */
export function Slider({ label, value, min, max, step, onChange, format = (v) => fmtNum(v), marker, description, disabled, id, className }: SliderProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const pct = (v: number) => (max === min ? 0 : Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100)));
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={inputId} className="text-[13.5px] text-ink first-letter:uppercase">
          {label}
        </label>
        <output htmlFor={inputId} className="tnum text-[14px] font-medium text-ink">
          {format(value)}
        </output>
      </div>
      <div className="relative pt-1">
        {marker && marker.value >= min && marker.value <= max ? (
          <div className="pointer-events-none absolute -top-0.5 z-10 flex -translate-x-1/2 flex-col items-center" style={{ left: `${pct(marker.value)}%` }} aria-hidden>
            <span className={cn("block h-3 w-px", MARKER_TONE[marker.tone ?? "amber"].split(" ")[0])} />
          </div>
        ) : null}
        <input
          id={inputId}
          type="range"
          className="valuo-range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-valuetext={format(value)}
        />
      </div>
      <div className="tnum flex justify-between text-[12px] text-dim">
        <span>{format(min)}</span>
        {marker && marker.value >= min && marker.value <= max ? (
          <span className={cn("text-[12px]", MARKER_TONE[marker.tone ?? "amber"].split(" ")[1])}>
            {marker.label}: {format(marker.value)}
          </span>
        ) : null}
        <span>{format(max)}</span>
      </div>
      {description ? <div className="text-[12.5px] leading-snug text-muted">{description}</div> : null}
    </div>
  );
}
