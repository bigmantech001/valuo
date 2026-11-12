import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** cell renderer; defaults to `String(row[accessor ?? key])` */
  render?: (row: T, index: number) => ReactNode;
  accessor?: keyof T;
  align?: "left" | "right" | "center";
  /** right-aligned tabular figures */
  numeric?: boolean;
  width?: string;
  className?: string;
  headerClassName?: string;
  /** hover text on the header */
  title?: string;
}

export interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  caption?: ReactNode;
  dense?: boolean;
  emptyText?: string;
  className?: string;
  rowClassName?: (row: T, index: number) => string | undefined;
  stickyHeader?: boolean;
  /** CSS max-height; enables vertical scroll */
  maxHeight?: string;
  footer?: ReactNode;
}

function defaultCell<T>(row: T, col: Column<T>): ReactNode {
  const v = (row as Record<string, unknown>)[(col.accessor as string | undefined) ?? col.key];
  if (v === null || v === undefined) return <span className="text-dim">n/a</span>;
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

/** Report-style table: ruled rows, sentence-case headers, tabular right-aligned numerics. */
export function Table<T>({ columns, rows, rowKey, caption, dense = true, emptyText = "no rows", className, rowClassName, stickyHeader = true, maxHeight, footer }: TableProps<T>) {
  const pad = dense ? "px-3 py-2" : "px-3 py-2.5";
  return (
    <div className={cn("w-full overflow-auto valuo-scroll", className)} style={maxHeight ? { maxHeight } : undefined}>
      <table className="w-full border-collapse text-[13.5px]">
        {caption ? (
          <caption className="pb-2 text-left text-[13px] text-muted">
            {/* Pinned to the visible width so a wide, scrolling table does not clip its caption on a phone. */}
            <span className="sticky left-0 block w-[min(100%,calc(100vw-5rem))]">{caption}</span>
          </caption>
        ) : null}
        <thead className={cn(stickyHeader && "sticky top-0 z-10")}>
          <tr className="bg-surface">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                title={c.title}
                style={c.width ? { width: c.width } : undefined}
                className={cn(
                  pad,
                  "border-b border-ink/80 text-[12.5px] font-medium text-muted",
                  c.align === "center" ? "text-center" : c.numeric || c.align === "right" ? "text-right" : "text-left",
                  c.headerClassName,
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={cn(pad, "py-4 text-center text-muted")}>
                {emptyText}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={rowKey(row, i)} className={cn("border-b border-border last:border-b-0 hover:bg-surface-2/50", rowClassName?.(row, i))}>
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={cn(
                      pad,
                      "align-top",
                      c.numeric && "tnum",
                      c.align === "center" ? "text-center" : c.numeric || c.align === "right" ? "text-right" : "text-left",
                      c.className,
                    )}
                  >
                    {c.render ? c.render(row, i) : defaultCell(row, c)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
        {footer ? (
          <tfoot>
            <tr>
              <td colSpan={columns.length} className={cn(pad, "border-t border-border text-[12.5px] leading-relaxed text-muted")}>
                {footer}
              </td>
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}
