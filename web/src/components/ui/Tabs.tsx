"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { DrawerChrome, DrawerHead, drawerPanelClass, useDrawer } from "./MobileDrawer";

export interface TabDef {
  id: string;
  label: ReactNode;
  /** small numeral / section code shown before the label (e.g. "01") */
  kicker?: ReactNode;
  /** optional trailing chip */
  badge?: ReactNode;
  content: ReactNode;
}

export interface TabsProps {
  tabs: TabDef[];
  defaultTabId?: string;
  /** keep the active tab in `location.hash` (default true) */
  syncHash?: boolean;
  onChange?: (id: string) => void;
  className?: string;
  /** "strip" = horizontal underline tabs; "sidebar" = sticky left rail on lg+, strip below lg */
  variant?: "strip" | "sidebar";
  /** sidebar heading (small caps) */
  railTitle?: ReactNode;
  /** extra links under a divider at the bottom of the sidebar */
  railFooter?: ReactNode;
}

/**
 * Accessible tab strip with URL-hash state. All panels stay mounted (hidden with the `hidden`
 * attribute) so client state inside a tab - slider positions, a finished quote race - survives
 * switching. Server-rendered content can be passed in `content`.
 */
export function Tabs({ tabs, defaultTabId, syncHash = true, onChange, className, variant = "strip", railTitle = "Sections", railFooter }: TabsProps) {
  const ids = tabs.map((t) => t.id);
  const fallback = defaultTabId && ids.includes(defaultTabId) ? defaultTabId : ids[0];
  const [active, setActive] = useState<string>(fallback);
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (!syncHash) return;
    const readHash = () => {
      const h = window.location.hash.replace(/^#/, "");
      if (h && ids.includes(h)) setActive(h);
    };
    readHash();
    window.addEventListener("hashchange", readHash);
    return () => window.removeEventListener("hashchange", readHash);
    // ids is derived from props; a stable join avoids re-subscribing on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [syncHash, ids.join("|")]);

  const select = useCallback(
    (id: string) => {
      setActive(id);
      onChange?.(id);
      if (syncHash && typeof window !== "undefined" && window.location.hash !== `#${id}`) {
        // pushState (not location.hash=) so the browser does not scroll to an element with that id.
        window.history.pushState(null, "", `#${id}`);
      }
    },
    [onChange, syncHash],
  );

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = index;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    select(tabs[next].id);
    buttonRefs.current[next]?.focus();
  };

  const [collapsed, setCollapsed] = useState(false);
  const drawer = useDrawer();
  const panels = tabs.map((t) => (
    <div key={t.id} role="tabpanel" id={`panel-${t.id}`} aria-labelledby={`tab-${t.id}`} hidden={t.id !== active} className={variant === "sidebar" ? "lg:pt-0" : "pt-8"}>
      {t.content}
    </div>
  ));

  if (variant === "sidebar") {
    const current = tabs.find((t) => t.id === active);
    const pick = (id: string) => {
      select(id);
      if (drawer.open) {
        drawer.setOpen(false);
        window.scrollTo({ top: 0 });
      }
    };
    return (
      <div className={cn("flex flex-col lg:grid lg:items-start lg:gap-8", collapsed ? "lg:grid-cols-[64px_minmax(0,1fr)]" : "lg:grid-cols-[248px_minmax(0,1fr)]", className)}>
        <DrawerChrome open={drawer.open} onClose={() => drawer.setOpen(false)} />
        <nav id="terminal-sections" aria-label="Terminal sections" className={drawerPanelClass(drawer.open, "min-w-0 lg:sticky lg:top-28")}>
          <DrawerHead title="Sections" open={drawer.open} onClose={() => drawer.setOpen(false)} />
          <div className="lg:rounded-xl lg:border lg:border-border lg:bg-surface lg:p-2.5 lg:shadow-[0_1px_2px_rgba(22,21,15,0.04)]">
            <div className={cn("hidden items-center border-b border-border pb-2.5 pt-1 lg:flex", collapsed ? "justify-center" : "justify-between pl-2.5")}>
              {collapsed ? null : <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-dim">{railTitle}</span>}
              <button
                type="button"
                onClick={() => setCollapsed((c) => !c)}
                aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                aria-expanded={!collapsed}
                className="grid h-7 w-7 place-items-center rounded-md border border-border text-[13px] text-muted transition-colors hover:border-border-strong hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <span aria-hidden>{collapsed ? "\u203A" : "\u2039"}</span>
              </button>
            </div>
            <div role="tablist" aria-label="Terminal sections" aria-orientation="vertical" className="flex flex-col gap-1 lg:mt-2">
              {tabs.map((t, i) => {
                const selected = t.id === active;
                return (
                  <button
                    key={t.id}
                    ref={(el) => {
                      buttonRefs.current[i] = el;
                    }}
                    role="tab"
                    type="button"
                    id={`tab-${t.id}`}
                    aria-selected={selected}
                    aria-controls={`panel-${t.id}`}
                    tabIndex={selected ? 0 : -1}
                    title={collapsed && typeof t.label === "string" ? t.label : undefined}
                    onClick={() => pick(t.id)}
                    onKeyDown={(e) => onKeyDown(e, i)}
                    className={cn(
                      "group relative flex min-h-11 shrink-0 items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2.5 text-[15px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent lg:min-h-0 lg:text-[14.5px]",
                      collapsed && "lg:justify-center lg:px-0",
                      selected ? "bg-surface-2 text-ink" : "text-muted hover:bg-surface-2/60 hover:text-ink",
                    )}
                  >
                    <span aria-hidden className={cn("absolute left-0 top-2 h-[calc(100%-16px)] w-[2px] rounded-full", selected ? "bg-accent" : "bg-transparent")} />
                    {t.kicker ? <span className={cn("tnum text-[12px]", selected ? "text-accent" : "text-dim")}>{t.kicker}</span> : null}
                    <span className={cn(collapsed && "lg:hidden")}>{t.label}</span>
                    {t.badge ? <span className={cn("ml-auto", collapsed && "lg:hidden")}>{t.badge}</span> : null}
                  </button>
                );
              })}
            </div>
            {railFooter ? (
              <div className={cn("mt-2 border-t border-border pt-2", collapsed && "lg:hidden")} onClick={() => drawer.setOpen(false)}>
                {railFooter}
              </div>
            ) : null}
          </div>
        </nav>
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => drawer.setOpen(true)}
            aria-controls="terminal-sections"
            aria-expanded={drawer.open}
            className="mb-6 flex min-h-11 w-full items-center gap-3 rounded-lg border border-border bg-surface px-3 text-left lg:hidden"
          >
            {current?.kicker ? <span className="tnum text-[12px] text-accent">{current.kicker}</span> : null}
            <span className="min-w-0 flex-1 truncate text-[15px] text-ink">{current?.label}</span>
            <span className="shrink-0 text-[13px] text-muted">All sections</span>
          </button>
          {panels}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col", className)}>
      <div role="tablist" aria-label="Terminal sections" className="valuo-scroll flex items-stretch gap-6 overflow-x-auto border-b border-border">
        {tabs.map((t, i) => {
          const selected = t.id === active;
          return (
            <button
              key={t.id}
              ref={(el) => {
                buttonRefs.current[i] = el;
              }}
              role="tab"
              type="button"
              id={`tab-${t.id}`}
              aria-selected={selected}
              aria-controls={`panel-${t.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => select(t.id)}
              onKeyDown={(e) => onKeyDown(e, i)}
              className={cn(
                "group relative flex shrink-0 items-center gap-2 py-3 text-[14.5px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                selected ? "text-ink" : "text-muted hover:text-ink",
              )}
            >
              {t.kicker ? <span className={cn("tnum text-[12px]", selected ? "text-muted" : "text-dim")}>{t.kicker}</span> : null}
              <span className="whitespace-nowrap">{t.label}</span>
              {t.badge}
              <span aria-hidden className={cn("absolute inset-x-0 -bottom-px h-[2px]", selected ? "bg-ink" : "bg-transparent")} />
            </button>
          );
        })}
      </div>
      {panels}
    </div>
  );
}
