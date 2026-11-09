import { cn } from "@/lib/cn";

export interface SkeletonProps {
  /** number of stacked bars (default 1) */
  lines?: number;
  /** CSS height per bar (default 0.75rem) */
  height?: string;
  className?: string;
}

/** Loading placeholder blocks (no text, no fake numbers). */
export function Skeleton({ lines = 1, height = "0.75rem", className }: SkeletonProps) {
  return (
    <div className={cn("flex flex-col gap-2.5", className)} aria-busy aria-live="polite">
      <span className="sr-only">Loading</span>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="valuo-skeleton w-full rounded" style={{ height, width: i === lines - 1 && lines > 1 ? "70%" : undefined }} />
      ))}
    </div>
  );
}
