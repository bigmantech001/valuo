"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface ToggleOption<T extends string> {
  value: T;
  label: ReactNode;
  /** hover text (e.g. the regime's daily issuance) */
  hint?: string;
  disabled?: boolean;
}

export interface ToggleProps<T extends string> {
  options: ToggleOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label?: ReactNode;
  size?: "sm" | "md";
  className?: string;
}

/** Segmented control (radio semantics) for regime / scenario switches. */
export function Toggle<T extends string>({ options, value, onChange, label, size = "sm", className }: ToggleProps<T>) {
  return (
    <div className={cn("inline-flex flex-col gap-1", className)}>
      {label ? <span className="text-[13px] text-muted first-letter:uppercase">{label}</span> : null}
      <div role="radiogroup" aria-label={typeof label === "string" ? label : undefined} className="inline-flex rounded-md border border-border-strong bg-surface p-0.5">
        {options.map((o, i) => {
          const selected = o.value === value;
          return (
            <button
              key={o.value}
              type="button"
              role="radio"
              aria-checked={selected}
              title={o.hint}
              disabled={o.disabled}
              onClick={() => onChange(o.value)}
              className={cn(
                "whitespace-nowrap rounded-[5px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 disabled:cursor-not-allowed disabled:opacity-40",
                size === "sm" ? "px-3 py-1 text-[13px]" : "px-3.5 py-1.5 text-[14px]",
                i > 0 && "ml-0.5",
                selected ? "bg-ink text-surface" : "text-muted hover:bg-surface-2 hover:text-ink",
              )}
            >
              {o.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
