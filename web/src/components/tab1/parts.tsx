import type { ReactNode } from "react";
import { ProvenanceBadge, type ProvenanceRef } from "@/components/provenance/ProvenanceBadge";
import { cn } from "@/lib/cn";
import type { Tone } from "@/lib/theme";

/** Text colour for a figure whose sign is the point; everything else stays ink. */
export const SIGN_TEXT: Record<Tone, string> = { neutral: "text-ink", emerald: "text-emerald", amber: "text-amber", crimson: "text-crimson", accent: "text-ink" };

/** Sub-section heading inside the tab (h3 under the tab's h2), with an optional one- or two-sentence lede. */
export function SubHead({ id, title, children, aside, className }: { id?: string; title: ReactNode; children?: ReactNode; aside?: ReactNode; className?: string }) {
  return (
    <div id={id} className={cn("flex flex-wrap items-end justify-between gap-x-8 gap-y-3 border-t border-border-strong pt-5", className)}>
      <div className="min-w-0 max-w-3xl flex-1 basis-[22rem]">
        <h3 className="font-serif text-[23px] font-medium leading-tight text-ink">{title}</h3>
        {children ? <div className="mt-2 text-[15px] leading-relaxed text-muted">{children}</div> : null}
      </div>
      {aside ? <div className="flex flex-wrap items-center gap-x-4 gap-y-2">{aside}</div> : null}
    </div>
  );
}

/** White panel around a table or chart. */
export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("min-w-0 rounded-lg border border-border bg-surface", className)}>{children}</div>;
}

export interface FigureItem {
  key: string;
  label: ReactNode;
  value: ReactNode;
  tone?: Tone;
  /** one short clause under the value */
  sub?: ReactNode;
  prov?: ProvenanceRef | null;
  /** status badge beside the value (clipped, assumption, thin sample) */
  badge?: ReactNode;
}

/** Definition list of figures: label left, value right, ruled rows. */
export function FigureList({ items, className }: { items: FigureItem[]; className?: string }) {
  return (
    <dl className={cn("divide-y divide-border", className)}>
      {items.map((it) => (
        <div key={it.key} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 py-2.5">
          <dt className="min-w-0 text-[14px] leading-snug text-muted">
            {it.label}
            {it.sub ? <div className="mt-0.5 text-[12.5px] leading-snug text-dim">{it.sub}</div> : null}
          </dt>
          <dd className="flex flex-col items-end gap-1 text-right">
            <span className="inline-flex flex-wrap items-center justify-end gap-2">
              {it.badge}
              <span className={cn("tnum text-[15px] font-medium", SIGN_TEXT[it.tone ?? "neutral"])}>{it.value}</span>
            </span>
            {it.prov ? <ProvenanceBadge source={it.prov.source} name={it.prov.name} /> : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}
