"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";

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
  const panels = tabs.map((t) => (
    <div key={t.id} role="tabpanel" id={`panel-${t.id}`} aria-labelledby={`tab-${t.id}`} hidden={t.id !== active} className={variant === "sidebar" ? "pt-8 lg:pt-0" : "pt-8"}>
      {t.content}
    </div>
  ));

  if (variant === "sidebar") {
    return (
      <div className={cn("flex flex-col lg:grid lg:items-start lg:gap-8", collapsed ? "lg:grid-cols-[64px_minmax(0,1fr)]" : "lg:grid-cols-[248px_minmax(0,1fr)]", className)}>
        <nav aria-label="Terminal sections" className="min-w-0 lg:sticky lg:top-28">
          <div className="rounded-xl border-border lg:border lg:bg-surface lg:p-2.5 lg:shadow-[0_1px_2px_rgba(22,21,15,0.04)]">
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
            <div role="tablist" aria-label="Terminal sections" aria-orientation="vertical" className="valuo-scroll flex gap-1 overflow-x-auto border-b border-border lg:mt-2 lg:flex-col lg:overflow-visible lg:border-b-0">
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
                    onClick={() => select(t.id)}
                    onKeyDown={(e) => onKeyDown(e, i)}
                    className={cn(
                      "group relative flex shrink-0 items-center gap-3 whitespace-nowrap px-3 py-3 text-[14.5px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent lg:rounded-lg lg:py-2.5",
                      collapsed && "lg:justify-center lg:px-0",
                      selected ? "text-ink lg:bg-surface-2" : "text-muted hover:text-ink lg:hover:bg-surface-2/60",
                    )}
                  >
                    <span aria-hidden className={cn("absolute inset-x-0 -bottom-px h-[2px] lg:inset-x-auto lg:bottom-auto lg:left-0 lg:top-2 lg:h-[calc(100%-16px)] lg:w-[2px] lg:rounded-full", selected ? "bg-ink lg:bg-accent" : "bg-transparent")} />
                    {t.kicker ? <span className={cn("tnum text-[12px]", selected ? "text-accent" : "text-dim")}>{t.kicker}</span> : null}
                    <span className={cn(collapsed && "lg:hidden")}>{t.label}</span>
                    {t.badge ? <span className={cn("ml-auto", collapsed && "lg:hidden")}>{t.badge}</span> : null}
                  </button>
                );
              })}
            </div>
            {railFooter && !collapsed ? <div className="mt-2 hidden border-t border-border pt-2 lg:block">{railFooter}</div> : null}
          </div>
        </nav>
        <div className="min-w-0">{panels}</div>
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
