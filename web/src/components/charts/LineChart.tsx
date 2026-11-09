import { cn } from "@/lib/cn";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, DEFAULT_MARGIN, defaultTickFormat, extent, linePath, niceTicks, padDomain, scaleLinear, slug, type BaseChartProps, type Margin, type Point } from "./util";

export interface LineSeries {
  name: string;
  values: number[];
  color?: string;
  dashed?: boolean;
  strokeWidth?: number;
  /** fill the area between the line and zero */
  area?: boolean;
}

export interface LineMarker {
  /** x value (same units as `x`) */
  x: number;
  label: string;
  color?: string;
}

export interface LineChartProps extends BaseChartProps {
  series: LineSeries[];
  /** x values shared by all series; defaults to 0..n-1 */
  x?: number[];
  xFormat?: (x: number) => string;
  yFormat?: (y: number) => string;
  yDomain?: [number, number];
  /** force 0 into the y domain (default true) */
  includeZero?: boolean;
  /** draw a horizontal line at y = 0 */
  zeroLine?: boolean;
  markers?: LineMarker[];
  legend?: boolean;
  xTicks?: number;
  yTicks?: number;
  margin?: Partial<Margin>;
  /** draw point circles with <title> tooltips when the series is short (default 48 points) */
  pointLimit?: number;
}

/** Multi-series line chart on a fixed viewBox; scales to the container width. */
export function LineChart({
  title,
  description,
  series,
  x,
  xFormat = (v) => String(Math.round(v)),
  yFormat = defaultTickFormat,
  yDomain,
  includeZero = true,
  zeroLine = true,
  markers = [],
  legend = true,
  xTicks = 6,
  yTicks = 5,
  width = 640,
  height = 280,
  margin,
  pointLimit = 48,
  className,
}: LineChartProps) {
  const m: Margin = { ...DEFAULT_MARGIN, ...margin };
  // Room for the legend row under the x-axis labels.
  if (legend && series.length) m.bottom += 16;
  const n = Math.max(0, ...series.map((s) => s.values.length));
  const xs = x ?? Array.from({ length: n }, (_, i) => i);
  const all = series.flatMap((s) => s.values).filter(Number.isFinite);
  const yd = yDomain ?? padDomain(extent(all), 0.06, includeZero);
  const xd: [number, number] = xs.length ? extent(xs) : [0, 1];
  const sx = scaleLinear(xd, [m.left, width - m.right]);
  const sy = scaleLinear(yd, [height - m.bottom, m.top]);
  const yT = niceTicks(yd, yTicks);
  const xT = niceTicks(xd, xTicks).filter((t) => t >= xd[0] && t <= xd[1]);
  const id = slug(title);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className={cn("block h-auto w-full", className)} style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      {description ? <desc>{description}</desc> : null}
      {/* grid + y axis */}
      {yT.map((t) => (
        <g key={`y${t}`}>
          <line x1={m.left} x2={width - m.right} y1={sy(t)} y2={sy(t)} stroke={t === 0 && zeroLine ? COLORS.borderStrong : COLORS.border} strokeWidth={1} />
          <text x={m.left - 8} y={sy(t)} dy="0.32em" textAnchor="end" fontSize={AXIS_FONT} fill={COLORS.dim}>
            {yFormat(t)}
          </text>
        </g>
      ))}
      {/* x axis */}
      <line x1={m.left} x2={width - m.right} y1={height - m.bottom} y2={height - m.bottom} stroke={COLORS.borderStrong} strokeWidth={1} />
      {xT.map((t) => (
        <text key={`x${t}`} x={sx(t)} y={height - m.bottom + 15} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.dim}>
          {xFormat(t)}
        </text>
      ))}
      {/* markers */}
      {markers.map((mk, i) => (
        <g key={`mk${i}`}>
          <line x1={sx(mk.x)} x2={sx(mk.x)} y1={m.top} y2={height - m.bottom} stroke={mk.color ?? COLORS.muted} strokeDasharray="3 3" />
          <text x={sx(mk.x) + 4} y={m.top + 11} fontSize={AXIS_FONT} fill={mk.color ?? COLORS.muted}>
            {mk.label}
          </text>
        </g>
      ))}
      {/* series */}
      {series.map((s, si) => {
        const color = s.color ?? SERIES_COLORS[si % SERIES_COLORS.length];
        const pts: Point[] = s.values.map((v, i) => [sx(xs[i] ?? i), sy(v)]);
        const d = linePath(pts);
        const zeroY = sy(Math.max(yd[0], Math.min(yd[1], 0)));
        return (
          <g key={s.name}>
            {s.area && d ? <path d={`${d}L${pts[pts.length - 1]?.[0].toFixed(2)},${zeroY.toFixed(2)}L${pts[0]?.[0].toFixed(2)},${zeroY.toFixed(2)}Z`} fill={color} fillOpacity={0.1} /> : null}
            <path d={d} fill="none" stroke={color} strokeWidth={s.strokeWidth ?? 1.75} strokeDasharray={s.dashed ? "5 4" : undefined} strokeLinejoin="round" />
            {s.values.length <= pointLimit
              ? s.values.map((v, i) =>
                  Number.isFinite(v) ? (
                    <circle key={i} cx={pts[i][0]} cy={pts[i][1]} r={2.2} fill={color}>
                      <title>{`${s.name} @ ${xFormat(xs[i] ?? i)}: ${yFormat(v)}`}</title>
                    </circle>
                  ) : null,
                )
              : null}
          </g>
        );
      })}
      {/* legend: one row of key + name, spaced by the length of each name so entries never overprint */}
      {legend
        ? (() => {
            let cursor = m.left;
            return series.map((s, si) => {
              const color = s.color ?? SERIES_COLORS[si % SERIES_COLORS.length];
              const lx = cursor;
              cursor += 22 + s.name.length * LABEL_FONT * 0.56 + 18;
              return (
                <g key={`lg${s.name}`} transform={`translate(${lx}, ${height - 4})`}>
                  <line x1={0} x2={16} y1={-4} y2={-4} stroke={color} strokeWidth={2} strokeDasharray={s.dashed ? "4 3" : undefined} />
                  <text x={22} y={0} fontSize={LABEL_FONT} fill={COLORS.muted}>
                    {s.name}
                  </text>
                </g>
              );
            });
          })()
        : null}
    </svg>
  );
}
