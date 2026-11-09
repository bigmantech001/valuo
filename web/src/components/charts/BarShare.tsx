import { cn } from "@/lib/cn";
import { fmtPct } from "@/lib/format";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, slug, type BaseChartProps } from "./util";

export interface BarShareItem {
  label: string;
  /** share in [0,1] or any non-negative magnitude (scaled to `max`) */
  value: number;
  color?: string;
  /** small grey text after the label (e.g. caller class) */
  sublabel?: string;
  /** makes the label a link (e.g. NearBlocks address) */
  href?: string;
}

export interface BarShareProps extends BaseChartProps {
  items: BarShareItem[];
  /** scale maximum; defaults to max(1, max value) for shares or max value otherwise */
  max?: number;
  valueFormat?: (v: number) => string;
  rowHeight?: number;
  labelWidth?: number;
  valueWidth?: number;
}

/** Horizontal share bars (caller concentration, venue mix). One row per item; height adapts. */
export function BarShare({ title, description, items, max, valueFormat = (v) => fmtPct(v, { decimals: 1 }), rowHeight = 22, labelWidth = 200, valueWidth = 64, width = 640, className }: BarShareProps) {
  const top = 6;
  const height = top + items.length * rowHeight + 6;
  const vmax = max ?? Math.max(1e-9, ...items.map((i) => i.value));
  const barX = labelWidth + 8;
  const barW = Math.max(10, width - barX - valueWidth - 8);
  const id = slug(title);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className={cn("block h-auto w-full", className)} style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      {description ? <desc>{description}</desc> : null}
      {items.map((it, i) => {
        const y = top + i * rowHeight;
        const w = Math.max(0, Math.min(1, it.value / vmax)) * barW;
        const color = it.color ?? SERIES_COLORS[0];
        const label = (
          <text x={labelWidth} y={y + rowHeight / 2} dy="0.32em" textAnchor="end" fontSize={LABEL_FONT} fill={COLORS.ink}>
            {it.label.length > 28 ? `${it.label.slice(0, 27)}…` : it.label}
            {it.sublabel ? (
              <tspan fill={COLORS.dim} fontSize={AXIS_FONT}>
                {` ${it.sublabel}`}
              </tspan>
            ) : null}
          </text>
        );
        return (
          <g key={`${it.label}-${i}`}>
            {it.href ? (
              <a href={it.href} target="_blank" rel="noreferrer">
                {label}
              </a>
            ) : (
              label
            )}
            <rect x={barX} y={y + 4} width={barW} height={rowHeight - 8} rx={1.5} fill={COLORS.surface2} />
            <rect x={barX} y={y + 4} width={w} height={rowHeight - 8} rx={1.5} fill={color} fillOpacity={0.8}>
              <title>{`${it.label}: ${valueFormat(it.value)}`}</title>
            </rect>
            <text x={barX + barW + 8} y={y + rowHeight / 2} dy="0.32em" fontSize={LABEL_FONT} fill={COLORS.ink}>
              {valueFormat(it.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
