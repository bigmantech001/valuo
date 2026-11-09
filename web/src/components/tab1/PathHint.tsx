import type { ReactNode } from "react";
import { Tooltip } from "@/components/ui";

/**
 * Source marker for a model output that has no single raw payload behind it (a Monte Carlo
 * percentile, a solved breakeven). The snapshot path is not printed as body text: it sits in a
 * hover/focus tooltip on a small "source" marker, so an auditor can still open
 * `artifacts/latest_snapshot.json` and find the number. Optional children render as a short
 * plain-language note before the marker.
 */
export function PathHint({
  path,
  children,
  label = "source",
  caption = "Snapshot field in artifacts/latest_snapshot.json",
}: {
  path: string;
  children?: ReactNode;
  /** visible marker text */
  label?: string;
  /** first line of the tooltip */
  caption?: string;
}) {
  return (
    <span className="inline-flex items-baseline gap-1.5 text-[12.5px] leading-snug text-dim">
      {children ? <span className="text-muted">{children}</span> : null}
      <Tooltip
        side="top"
        wide
        content={
          <span className="block">
            <span className="mb-1 block text-muted">{caption}</span>
            <code className="break-all font-mono text-[11.5px] text-ink">{path}</code>
          </span>
        }
      >
        <button type="button" aria-label={`${caption}: ${path}`} className="cursor-help border-b border-dotted border-dim/70 text-[12px] leading-none text-dim hover:text-ink focus-visible:text-ink focus-visible:outline-none">
          {label}
        </button>
      </Tooltip>
    </span>
  );
}
