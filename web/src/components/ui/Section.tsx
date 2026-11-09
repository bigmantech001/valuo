import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Opening of a tab or a major section: a short context line, the finding stated as a serif
 * headline, and one or two sentences of lede. The headline should be a claim the numbers below
 * support ("1Click delivers more than the best competitor on cross-VM routes"), not a label.
 */
export function SectionIntro({ eyebrow, title, children, aside, className }: { eyebrow?: ReactNode; title: ReactNode; children?: ReactNode; aside?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-x-10 gap-y-4", className)}>
      <div className="min-w-0 max-w-3xl flex-1 basis-[28rem]">
        {eyebrow ? <div className="mb-2 text-[13px] text-dim first-letter:uppercase">{eyebrow}</div> : null}
        <h2 className="font-serif text-[30px] font-medium leading-[1.15] tracking-[-0.01em] text-ink sm:text-[34px]">{title}</h2>
        {children ? <div className="mt-3 text-[15.5px] leading-relaxed text-muted">{children}</div> : null}
      </div>
      {aside ? <div className="flex flex-wrap items-center gap-2">{aside}</div> : null}
    </div>
  );
}

/** Ruled grid of Stat tiles: hairline separators, rounded outer frame. */
export function StatGrid({ children, cols = 4, className }: { children: ReactNode; cols?: 2 | 3 | 4; className?: string }) {
  const grid = cols === 2 ? "sm:grid-cols-2" : cols === 3 ? "sm:grid-cols-2 lg:grid-cols-3" : "sm:grid-cols-2 lg:grid-cols-4";
  return <div className={cn("grid gap-px overflow-hidden rounded-lg border border-border bg-border", grid, className)}>{children}</div>;
}

/**
 * Collapsed "Method and sources" note: where formulas, snapshot field paths, sample sizes and
 * caveats go, so the body text carries findings and the method stays one click away.
 */
export function MethodNote({ summary = "Method and sources", children, defaultOpen = false, className }: { summary?: ReactNode; children: ReactNode; defaultOpen?: boolean; className?: string }) {
  return (
    <details open={defaultOpen} className={cn("group rounded-md border border-border bg-surface-2/60 text-[13px] text-muted", className)}>
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-[13px] text-muted hover:text-ink [&::-webkit-details-marker]:hidden">
        <span aria-hidden className="inline-block text-dim transition-transform group-open:rotate-90">
          &#8250;
        </span>
        {summary}
      </summary>
      <div className="space-y-2 border-t border-border px-4 py-3 leading-relaxed [&_code]:font-mono [&_code]:text-[12px] [&_code]:text-ink">{children}</div>
    </details>
  );
}
