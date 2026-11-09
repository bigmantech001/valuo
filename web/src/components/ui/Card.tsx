import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import type { Tone } from "@/lib/theme";

export interface CardProps {
  /** short context line above the title (section number, "Live", ...) */
  kicker?: ReactNode;
  title?: ReactNode;
  subtitle?: ReactNode;
  /** right-aligned header slot: buttons, a status badge */
  actions?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
  /**
   * Kept for API compatibility. Cards no longer carry a coloured stripe: colour is reserved for
   * the sign of a number, so the tone is ignored.
   */
  tone?: Tone;
  padded?: boolean;
  className?: string;
  bodyClassName?: string;
  id?: string;
}

/**
 * White panel with a hairline border and a serif title; the base unit of every tab.
 * The header wraps: on narrow viewports the actions drop under the title.
 */
export function Card({ kicker, title, subtitle, actions, footer, children, padded = true, className, bodyClassName, id }: CardProps) {
  const hasHeader = kicker || title || subtitle || actions;
  return (
    <section id={id} className={cn("flex min-w-0 flex-col rounded-lg border border-border bg-surface", className)}>
      {hasHeader ? (
        <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2 px-5 pb-3 pt-4">
          <div className="min-w-0 flex-1 basis-64">
            {kicker ? <div className="mb-1 text-[12px] text-dim first-letter:uppercase">{kicker}</div> : null}
            {title ? <h2 className="font-serif text-[21px] font-medium leading-tight text-ink">{title}</h2> : null}
            {subtitle ? <p className="mt-1 max-w-3xl text-[13.5px] leading-relaxed text-muted">{subtitle}</p> : null}
          </div>
          {actions ? <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={cn("min-w-0 flex-1", padded && "px-5 pb-5", padded && !hasHeader && "pt-5", bodyClassName)}>{children}</div>
      {footer ? <footer className="border-t border-border px-5 py-3 text-[12.5px] leading-relaxed text-muted">{footer}</footer> : null}
    </section>
  );
}
