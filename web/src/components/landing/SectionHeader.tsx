import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { SectionIntro } from "@/components/ui/Section";

/** Page container shared by every landing section: 1240px column, hairline rule above. */
export function LandingSection({ id, children, className, muted = false }: { id?: string; children: ReactNode; className?: string; muted?: boolean }) {
  return (
    <section id={id} className={cn("scroll-mt-16 border-t border-border", muted ? "bg-surface" : null)}>
      <div className={cn("mx-auto max-w-none px-6 lg:px-[5vw] py-20 sm:py-24", className)}>{children}</div>
    </section>
  );
}

/** Numbered section opening: "2 · Questions", serif headline, one or two sentences of lede. */
export function SectionHeader({ number, eyebrow, title, lede, aside }: { number?: string; eyebrow: string; title: ReactNode; lede?: ReactNode; aside?: ReactNode }) {
  return (
    <SectionIntro
      eyebrow={
        <span>
          {number ? <span className="tnum text-muted">{number}</span> : null}
          {number ? <span aria-hidden className="px-2 text-border-strong">/</span> : null}
          {eyebrow}
        </span>
      }
      title={title}
      aside={aside}
    >
      {lede}
    </SectionIntro>
  );
}

/** Small accent text link, used for "Open in the terminal" style links. */
export function TextLink({ href, children, download, className }: { href: string; children: ReactNode; download?: boolean; className?: string }) {
  return (
    <a href={href} download={download || undefined} className={cn("inline-flex items-center gap-1 text-[14px] text-accent underline-offset-4 hover:underline", className)}>
      {children}
    </a>
  );
}
