import { cn } from "@/lib/cn";

/**
 * The Valuo mark: five bars forming a V, the lowest one in the accent colour. Ink bars use currentColor so the
 * mark follows the text colour it sits in (ink on canvas, canvas on ink). Same geometry as src/app/icon.svg.
 */
export function LogoMark({ className, title }: { className?: string; title?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={cn("shrink-0", className)} role={title ? "img" : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      <rect x="5" y="7" width="6" height="34" rx="2" fill="currentColor" />
      <rect x="13.5" y="17" width="6" height="24" rx="2" fill="currentColor" />
      <rect x="22" y="29" width="6" height="12" rx="2" fill="var(--color-accent)" />
      <rect x="30.5" y="17" width="6" height="24" rx="2" fill="currentColor" />
      <rect x="39" y="7" width="6" height="34" rx="2" fill="currentColor" />
    </svg>
  );
}
