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
}

/**
 * Accessible tab strip with URL-hash state. All panels stay mounted (hidden with the `hidden`
 * attribute) so client state inside a tab - slider positions, a finished quote race - survives
 * switching. Server-rendered content can be passed in `content`.
 */
export function Tabs({ tabs, defaultTabId, syncHash = true, onChange, className }: TabsProps) {
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
    if (e.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    select(tabs[next].id);
    buttonRefs.current[next]?.focus();
  };

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
      {tabs.map((t) => (
        <div key={t.id} role="tabpanel" id={`panel-${t.id}`} aria-labelledby={`tab-${t.id}`} hidden={t.id !== active} className="pt-8">
          {t.content}
        </div>
      ))}
    </div>
  );
}
