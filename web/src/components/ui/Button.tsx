import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "accent";
export type ButtonSize = "xs" | "sm" | "md";

const VARIANT: Record<ButtonVariant, string> = {
  primary: "border-ink bg-ink text-surface hover:bg-ink/85",
  secondary: "border-border-strong bg-surface text-ink hover:border-ink/40 hover:bg-surface-2",
  ghost: "border-transparent bg-transparent text-muted hover:text-ink",
  danger: "border-crimson/40 bg-surface text-crimson hover:bg-crimson/5",
  accent: "border-accent bg-accent text-surface hover:bg-accent/90",
};

const SIZE: Record<ButtonSize, string> = {
  xs: "px-2.5 py-1 text-[12.5px]",
  sm: "px-3 py-1.5 text-[13.5px]",
  md: "px-4 py-2 text-[14.5px]",
};

const BASE = "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md border font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 disabled:cursor-not-allowed disabled:opacity-50";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
}

export function Button({ variant = "secondary", size = "sm", loading = false, leftIcon, className, children, disabled, type = "button", ...rest }: ButtonProps) {
  return (
    <button type={type} disabled={disabled || loading} aria-busy={loading || undefined} className={cn(BASE, VARIANT[variant], SIZE[size], className)} {...rest}>
      {loading ? <span aria-hidden className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" /> : leftIcon}
      {children}
    </button>
  );
}

export interface LinkButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leftIcon?: ReactNode;
}

/** Anchor styled as a button (downloads, external explorer links). */
export function LinkButton({ variant = "secondary", size = "sm", leftIcon, className, children, ...rest }: LinkButtonProps) {
  return (
    <a className={cn(BASE, VARIANT[variant], SIZE[size], className)} {...rest}>
      {leftIcon}
      {children}
    </a>
  );
}
