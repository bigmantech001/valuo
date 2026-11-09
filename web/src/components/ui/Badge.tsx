import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import type { EvidenceStatus, QuoteStatus } from "@/lib/types";

export type BadgeVariant =
  | "verified-chain"
  | "verified-api"
  | "derived"
  | "assumption"
  | "not-supported"
  | "ok"
  | "warn"
  | "error"
  | "neutral"
  | "info"
  | "accent";

export interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  title?: string;
  /** leading status dot */
  dot?: boolean;
  size?: "xs" | "sm";
  /** let a long informational badge wrap instead of forcing one line (default: nowrap, for short status chips) */
  wrap?: boolean;
  className?: string;
}

const STYLES: Record<BadgeVariant, string> = {
  "verified-chain": "bg-emerald/10 text-emerald",
  "verified-api": "bg-emerald/10 text-emerald",
  derived: "bg-surface-2 text-ink",
  assumption: "bg-amber/10 text-amber",
  "not-supported": "bg-crimson/10 text-crimson",
  ok: "bg-emerald/10 text-emerald",
  warn: "bg-amber/10 text-amber",
  error: "bg-crimson/10 text-crimson",
  neutral: "bg-surface-2 text-muted",
  info: "bg-surface-2 text-ink",
  accent: "bg-accent/10 text-accent",
};

const DOT: Record<BadgeVariant, string> = {
  "verified-chain": "bg-emerald",
  "verified-api": "bg-emerald",
  derived: "bg-ink",
  assumption: "bg-amber",
  "not-supported": "bg-crimson",
  ok: "bg-emerald",
  warn: "bg-amber",
  error: "bg-crimson",
  neutral: "bg-muted",
  info: "bg-ink",
  accent: "bg-accent",
};

/** Small sentence-case status label on a tinted ground; reserve it for statuses, not decoration. */
export function Badge({ variant = "neutral", children, title, dot = false, size = "xs", wrap = false, className }: BadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-full font-medium first-letter:uppercase",
        wrap ? "whitespace-normal text-left" : "whitespace-nowrap",
        size === "xs" ? "px-2 py-0.5 text-[11.5px]" : "px-2.5 py-0.5 text-[12.5px]",
        STYLES[variant],
        className,
      )}
    >
      {dot ? <span className={cn("inline-block h-1.5 w-1.5 shrink-0 rounded-full", DOT[variant])} aria-hidden /> : null}
      {children}
    </span>
  );
}

export function evidenceStatusVariant(status: EvidenceStatus): BadgeVariant {
  switch (status) {
    case "VERIFIED_ON_CHAIN":
      return "verified-chain";
    case "VERIFIED_LIVE_API":
      return "verified-api";
    case "DERIVED":
      return "derived";
    case "ASSUMPTION":
      return "assumption";
    case "NOT_SUPPORTED":
      return "not-supported";
  }
}

export function evidenceStatusLabel(status: EvidenceStatus): string {
  switch (status) {
    case "VERIFIED_ON_CHAIN":
      return "Verified on-chain";
    case "VERIFIED_LIVE_API":
      return "Verified via live API";
    case "DERIVED":
      return "Derived";
    case "ASSUMPTION":
      return "Assumption";
    case "NOT_SUPPORTED":
      return "Not supported";
  }
}

export function quoteStatusVariant(status: QuoteStatus): BadgeVariant {
  switch (status) {
    case "ok":
      return "ok";
    case "no_liquidity":
      return "warn";
    case "unsupported_route":
      return "not-supported";
    case "error":
      return "error";
    case "skipped":
      return "neutral";
  }
}

export function quoteStatusLabel(status: QuoteStatus): string {
  const s = status.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Convenience: an evidence-status badge in one call. */
export function EvidenceBadge({ status, className }: { status: EvidenceStatus; className?: string }) {
  return (
    <Badge variant={evidenceStatusVariant(status)} dot className={className}>
      {evidenceStatusLabel(status)}
    </Badge>
  );
}

export function QuoteStatusBadge({ status, title, className }: { status: QuoteStatus; title?: string; className?: string }) {
  return (
    <Badge variant={quoteStatusVariant(status)} dot title={title} className={className}>
      {quoteStatusLabel(status)}
    </Badge>
  );
}
