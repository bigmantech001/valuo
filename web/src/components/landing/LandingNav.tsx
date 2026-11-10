"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import { BurgerButton, DrawerChrome, DrawerHead, drawerPanelClass, useDrawer } from "@/components/ui/MobileDrawer";

const LINKS: Array<{ href: string; label: string }> = [
  { href: "#findings", label: "Findings" },
  { href: "#questions", label: "Questions" },
  { href: "#method", label: "Method" },
  { href: "#bear", label: "Bear case" },
  { href: "#reproduce", label: "Reproduce" },
];

/**
 * Thin sticky header: serif wordmark on the left, section anchors on the right. Below lg the anchors move
 * into a left drawer opened by a burger, with the terminal link pinned at the bottom.
 */
export function LandingNav() {
  const drawer = useDrawer();
  const close = () => drawer.setOpen(false);
  return (
    <>
    <header className="sticky top-0 z-40 border-b border-border bg-canvas/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-none items-center gap-8 px-4 sm:px-6 lg:px-[1.25vw]">
        <Link href="/" className="font-serif text-[22px] font-medium leading-none tracking-tight text-ink">
          Valuo
        </Link>
        <nav aria-label="Sections" className="ml-auto hidden items-center gap-6 lg:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="text-[14px] text-muted transition-colors hover:text-ink">
              {l.label}
            </a>
          ))}
        </nav>
        <BurgerButton open={drawer.open} onClick={drawer.toggle} controls="landing-menu" className="ml-auto" />
      </div>
    </header>
      {/* Outside the header: its backdrop-filter would make it the containing block of a fixed drawer. */}
      <DrawerChrome open={drawer.open} onClose={close} />
      <div id="landing-menu" role="dialog" aria-modal="true" aria-label="Menu" className={cn(drawerPanelClass(drawer.open, "lg:hidden"), "flex flex-col")}>
        <DrawerHead title="Valuo" open={drawer.open} onClose={close} />
        <nav aria-label="Sections" className="flex flex-col gap-1">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} onClick={close} className="flex min-h-11 items-center rounded-lg px-3 text-[15px] text-ink hover:bg-surface-2">
              {l.label}
            </a>
          ))}
        </nav>
        <Link
          href="/terminal"
          onClick={close}
          className="mt-auto flex min-h-11 items-center justify-center rounded-lg bg-ink px-4 text-[15px] font-medium text-canvas"
        >
          Open the terminal
        </Link>
      </div>
    </>
  );
}
