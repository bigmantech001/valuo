"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Phone/tablet navigation (below the lg breakpoint): a burger in the sticky top bar opens a left drawer
 * with a dimmed backdrop. The drawer closes on the backdrop, the Close button, Esc, and whenever the
 * owner calls close() after a navigation. Desktop (lg and up) never renders the burger or the backdrop.
 */
interface DrawerState {
  open: boolean;
  setOpen: (v: boolean) => void;
  toggle: () => void;
}

const DrawerContext = createContext<DrawerState | null>(null);

export function DrawerProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const toggle = useCallback(() => setOpen((o) => !o), []);
  const value = useMemo(() => ({ open, setOpen, toggle }), [open, toggle]);
  return <DrawerContext.Provider value={value}>{children}</DrawerContext.Provider>;
}

/** The shared drawer state, or a local one when no provider is mounted. */
export function useDrawer(): DrawerState {
  const ctx = useContext(DrawerContext);
  const [open, setOpen] = useState(false);
  const local = useMemo(() => ({ open, setOpen, toggle: () => setOpen((o) => !o) }), [open]);
  return ctx ?? local;
}

export function BurgerButton({ open, onClick, controls, className }: { open: boolean; onClick: () => void; controls: string; className?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={open}
      aria-controls={controls}
      aria-label={open ? "Close menu" : "Open menu"}
      className={cn(
        "inline-flex h-10 w-10 shrink-0 flex-col items-center justify-center gap-[4.5px] rounded-lg border border-border bg-surface text-ink lg:hidden",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        className,
      )}
    >
      <span className={cn("h-[1.5px] w-4 bg-current transition-transform duration-200", open && "translate-y-[6px] rotate-45")} />
      <span className={cn("h-[1.5px] w-4 bg-current transition-opacity duration-200", open && "opacity-0")} />
      <span className={cn("h-[1.5px] w-4 bg-current transition-transform duration-200", open && "-translate-y-[6px] -rotate-45")} />
    </button>
  );
}

/**
 * Backdrop + Esc handling + body scroll lock for a drawer whose panel the caller renders (so the same DOM can
 * be a static sidebar on desktop). Below lg only.
 */
export function DrawerChrome({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const mq = window.matchMedia("(min-width: 1024px)");
    const onResize = () => {
      if (mq.matches) onClose();
    };
    window.addEventListener("keydown", onKey);
    mq.addEventListener("change", onResize);
    const prev = document.body.style.overflow;
    if (!mq.matches) document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      mq.removeEventListener("change", onResize);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);
  return (
    <button
      type="button"
      tabIndex={-1}
      aria-label="Close menu"
      onClick={onClose}
      className={cn(
        "fixed inset-0 z-[45] bg-ink/40 transition-opacity duration-200 lg:hidden",
        open ? "opacity-100" : "pointer-events-none opacity-0",
      )}
    />
  );
}

/** Classes that turn a panel into the left drawer below lg (pass `open`); lg and up get `desktop` instead. */
export function drawerPanelClass(open: boolean, desktop: string): string {
  return cn(
    "max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-50 max-lg:h-[100dvh] max-lg:w-[min(88vw,320px)] max-lg:overflow-y-auto",
    "max-lg:border-r max-lg:border-border max-lg:bg-surface max-lg:px-3 max-lg:pt-3 max-lg:pb-[calc(12px+env(safe-area-inset-bottom))]",
    "max-lg:transition-[transform,visibility] max-lg:duration-200 max-lg:ease-[cubic-bezier(.2,.7,.2,1)]",
    open ? "max-lg:translate-x-0 max-lg:shadow-[20px_0_60px_rgba(22,21,15,0.18)]" : "max-lg:-translate-x-full max-lg:invisible",
    desktop,
  );
}

/** Head row inside the drawer (below lg only): title + Close. Focuses Close when the drawer opens. */
export function DrawerHead({ title, open, onClose }: { title: ReactNode; open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    if (open && !window.matchMedia("(min-width: 1024px)").matches) ref.current?.focus();
  }, [open]);
  return (
    <div className="mb-2 flex items-center justify-between border-b border-border pb-3 pl-1 lg:hidden">
      <span className="font-serif text-[20px] leading-none text-ink">{title}</span>
      <button
        ref={ref}
        type="button"
        onClick={onClose}
        className="inline-flex h-9 items-center rounded-lg border border-border px-3 text-[13.5px] text-muted hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        Close
      </button>
    </div>
  );
}
