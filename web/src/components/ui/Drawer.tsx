"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: "md" | "lg" | "xl";
  side?: "right" | "left";
}

const WIDTH = { md: "max-w-md", lg: "max-w-2xl", xl: "max-w-5xl" } as const;

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Slide-over panel with overlay; Escape and overlay click close it; body scroll is locked while open.
 * Focus management for the modal dialog: on open, focus moves to the close button (the panel itself when
 * nothing is focusable), Tab / Shift+Tab cycle inside the panel, and on close focus returns to the element
 * that opened the drawer. Without this, aria-modal leaves keyboard users on the covered page.
 */
export function Drawer({ open, onClose, title, subtitle, children, footer, width = "lg", side = "right" }: DrawerProps) {
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  // Latest onClose without re-running the focus effect when a parent passes a new arrow function each render.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    (closeRef.current ?? panelRef.current)?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab" || !panelRef.current) return;
      const panel = panelRef.current;
      const nodes = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!nodes.length) {
        e.preventDefault();
        panel.focus();
        return;
      }
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      const active = document.activeElement;
      const inside = active instanceof Node && panel.contains(active);
      if (e.shiftKey && (active === first || !inside)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (active === last || !inside)) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
      opener?.focus();
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[100] flex" role="presentation">
      <button type="button" aria-label="Close" tabIndex={-1} onClick={onClose} className="absolute inset-0 cursor-default bg-ink/25" />
      <aside
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        className={cn(
          "relative flex h-full w-full flex-col border-border bg-surface shadow-[0_0_40px_rgba(22,21,15,0.12)] outline-none",
          WIDTH[width],
          side === "right" ? "ml-auto border-l" : "mr-auto border-r",
        )}
      >
        <header className="flex items-start justify-between gap-6 border-b border-border px-6 pb-4 pt-5">
          <div className="min-w-0">
            {title ? <h2 className="font-serif text-[22px] font-medium leading-tight text-ink">{title}</h2> : null}
            {subtitle ? <div className="mt-1.5 text-[13.5px] leading-relaxed text-muted">{subtitle}</div> : null}
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-[13px] text-muted transition-colors hover:border-border-strong hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
            aria-label="Close panel (Escape)"
          >
            <span aria-hidden className="text-[15px] leading-none">&times;</span>
            Close
          </button>
        </header>
        <div className="valuo-scroll flex-1 overflow-auto px-6 py-5">{children}</div>
        {footer ? <footer className="border-t border-border bg-surface-2/50 px-6 py-3 text-[13px] leading-relaxed text-muted">{footer}</footer> : null}
      </aside>
    </div>
  );
}
