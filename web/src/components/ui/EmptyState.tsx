import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface EmptyStateProps {
  title: ReactNode;
  children?: ReactNode;
  /** shell commands shown in a code block */
  commands?: string[];
  className?: string;
}

/** Instructional empty state; used when artifacts are missing or a section is pending. */
export function EmptyState({ title, children, commands, className }: EmptyStateProps) {
  return (
    <div className={cn("rounded-lg border border-dashed border-border-strong bg-surface px-6 py-6", className)}>
      <h3 className="font-serif text-lg font-medium text-ink">{title}</h3>
      {children ? <div className="mt-2 max-w-2xl text-[13.5px] leading-relaxed text-muted">{children}</div> : null}
      {commands && commands.length ? (
        <pre className="mt-4 overflow-x-auto rounded-md bg-ink px-4 py-3 font-mono text-[12.5px] leading-relaxed text-surface">
          {commands.join("\n")}
        </pre>
      ) : null}
    </div>
  );
}
