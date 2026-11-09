import { cn } from "@/lib/cn";
import { COLORS } from "@/lib/theme";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, defaultTickFormat, mixHex, readableOn, slug, type BaseChartProps } from "./util";

export interface HeatmapProps extends BaseChartProps {
  /** column headers (e.g. daily volume USD) */
  x: Array<number | string>;
  /** row headers (e.g. net take bps) */
  y: Array<number | string>;
  /** values[rowIndex][colIndex] (rows = y, columns = x) */
  values: number[][];
  /** flags[rowIndex][colIndex]: true -> emerald border (e.g. net-deflationary cell) */
  flags?: boolean[][];
  cellFormat?: (v: number) => string;
  xFormat?: (x: number | string) => string;
  yFormat?: (y: number | string) => string;
  xLabel?: string;
  yLabel?: string;
  /** colour ramp endpoints (default surface -> accent) */
  colorLow?: string;
  colorHigh?: string;
  /** label for the flag legend (default "net deflationary") */
  flagLabel?: string;
  /** highlight cell (row, col) with a thicker ink border (e.g. the live measured operating point) */
  highlight?: [number, number] | null;
  /** optional key entry for the highlighted cell (drawn next to the flag key) */
  highlightLabel?: string;
}

/** 5x5 (or any) grid heatmap with in-cell labels; flagged cells get an emerald border. */
export function Heatmap({
  title,
  description,
  x,
  y,
  values,
  flags,
  cellFormat = defaultTickFormat,
  xFormat = (v) => (typeof v === "number" ? defaultTickFormat(v) : v),
  yFormat = (v) => (typeof v === "number" ? defaultTickFormat(v) : v),
  xLabel,
  yLabel,
  colorLow = COLORS.surface2,
  colorHigh = COLORS.accent,
  flagLabel = "net deflationary",
  highlight = null,
  highlightLabel,
  width = 640,
  height = 320,
  className,
}: HeatmapProps) {
  const left = 84;
  const top = 30;
  const bottom = 40;
  const right = 12;
  const cols = x.length;
  const rows = y.length;
  const cw = (width - left - right) / Math.max(1, cols);
  const ch = (height - top - bottom) / Math.max(1, rows);
  const flat = values.flat().filter(Number.isFinite);
  const lo = Math.min(...flat);
  const hi = Math.max(...flat);
  const t = (v: number) => (hi === lo ? 0.5 : (v - lo) / (hi - lo));
  const id = slug(title);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className={cn("block h-auto w-full", className)} style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      {description ? <desc>{description}</desc> : null}
      {x.map((xv, ci) => (
        <text key={`x${ci}`} x={left + ci * cw + cw / 2} y={top - 10} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.muted}>
          {xFormat(xv)}
        </text>
      ))}
      {y.map((yv, ri) => (
        <text key={`y${ri}`} x={left - 8} y={top + ri * ch + ch / 2} dy="0.32em" textAnchor="end" fontSize={AXIS_FONT} fill={COLORS.muted}>
          {yFormat(yv)}
        </text>
      ))}
      {values.map((row, ri) =>
        row.map((v, ci) => {
          const flagged = flags?.[ri]?.[ci] === true;
          const hl = highlight && highlight[0] === ri && highlight[1] === ci;
          const fill = Number.isFinite(v) ? mixHex(colorLow, colorHigh, t(v)) : COLORS.surface;
          // Pick ink or white per cell by WCAG contrast against the actual fill, not a fixed cut-off.
          const textFill = Number.isFinite(v) ? readableOn(fill, [COLORS.ink, COLORS.surface]) : COLORS.dim;
          const inset = hl ? 2 : flagged ? 1.5 : 1;
          return (
            <g key={`c${ri}-${ci}`}>
              <rect
                x={left + ci * cw + inset}
                y={top + ri * ch + inset}
                width={cw - 2 * inset}
                height={ch - 2 * inset}
                rx={1.5}
                fill={fill}
                stroke={hl ? COLORS.ink : flagged ? COLORS.emerald : COLORS.surface}
                strokeWidth={hl ? 2.5 : flagged ? 2 : 1}
              >
                <title>{`${yLabel ?? "y"} ${yFormat(y[ri])}, ${xLabel ?? "x"} ${xFormat(x[ci])}: ${Number.isFinite(v) ? cellFormat(v) : "n/a"}${flagged ? ` (${flagLabel})` : ""}`}</title>
              </rect>
              <text x={left + ci * cw + cw / 2} y={top + ri * ch + ch / 2} dy="0.32em" textAnchor="middle" fontSize={LABEL_FONT} fontWeight={hl ? 600 : 400} fill={textFill}>
                {Number.isFinite(v) ? cellFormat(v) : "n/a"}
              </text>
            </g>
          );
        }),
      )}
      {xLabel ? (
        <text x={left + (width - left - right) / 2} y={height - 22} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.muted}>
          {xLabel}
        </text>
      ) : null}
      {yLabel ? (
        <text transform={`translate(12, ${top + (height - top - bottom) / 2}) rotate(-90)`} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.muted}>
          {yLabel}
        </text>
      ) : null}
      {flags ? (
        <g transform={`translate(${left}, ${height - 8})`}>
          <rect x={0} y={-9} width={12} height={9} rx={1} fill="none" stroke={COLORS.emerald} strokeWidth={2} />
          <text x={18} y={0} fontSize={AXIS_FONT} fill={COLORS.muted}>
            {flagLabel}
          </text>
          {highlight && highlightLabel ? (
            <g transform={`translate(${Math.min(width - right - 150, 30 + flagLabel.length * AXIS_FONT * 0.56)}, 0)`}>
              <rect x={0} y={-9} width={12} height={9} rx={1} fill="none" stroke={COLORS.ink} strokeWidth={2} />
              <text x={18} y={0} fontSize={AXIS_FONT} fill={COLORS.muted}>
                {highlightLabel}
              </text>
            </g>
          ) : null}
        </g>
      ) : null}
    </svg>
  );
}
