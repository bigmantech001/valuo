import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  /** wider panel for provenance records */
  wide?: boolean;
  className?: string;
}

const SIDE: Record<NonNullable<TooltipProps["side"]>, string> = {
  top: "bottom-full left-1/2 mb-1.5 -translate-x-1/2",
  bottom: "top-full left-1/2 mt-1.5 -translate-x-1/2",
  left: "right-full top-1/2 mr-1.5 -translate-y-1/2",
  right: "left-full top-1/2 ml-1.5 -translate-y-1/2",
};

/**
 * CSS-only hover/focus tooltip (no JS, works inside server components). Make the child
 * focusable (button/link/tabIndex=0) to get keyboard access via :focus-within.
 */
export function Tooltip({ content, children, side = "top", wide = false, className }: TooltipProps) {
  return (
    <span className={cn("group/tt relative inline-flex", className)}>
      {children}
      <span
        role="tooltip"
        className={cn(
          "pointer-events-none absolute z-50 hidden rounded-md border border-border bg-surface px-3 py-2.5 text-left text-[12.5px] font-normal normal-case leading-snug tracking-normal text-ink shadow-[0_8px_24px_rgba(22,21,15,0.12)]",
          // display:none until hover/focus, so a closed tooltip never widens the page on small screens
          "group-hover/tt:block group-focus-within/tt:block",
          wide ? "w-[24rem] max-w-[90vw]" : "w-max max-w-[20rem]",
          SIDE[side],
        )}
      >
        {content}
      </span>
    </span>
  );
}
