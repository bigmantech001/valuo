import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface DefinitionRow {
  key: string;
  term: ReactNode;
  value: ReactNode;
  /** one short clause under the term */
  note?: ReactNode;
  /** colour class for the value when its sign is the point */
  valueClassName?: string;
}

/** Ruled two-column list of figures: term (and an optional short note) left, tabular value right. */
export function DefinitionList({ rows, className }: { rows: DefinitionRow[]; className?: string }) {
  return (
    <dl className={cn("divide-y divide-border border-y border-border", className)}>
      {rows.map((r) => (
        <div key={r.key} className="flex items-baseline justify-between gap-6 py-2.5">
          <dt className="min-w-0 text-[13.5px] text-ink">
            {r.term}
            {r.note ? <div className="mt-0.5 text-[12.5px] leading-snug text-dim">{r.note}</div> : null}
          </dt>
          <dd className={cn("tnum shrink-0 text-right text-[14px] font-medium text-ink", r.valueClassName)}>{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}
