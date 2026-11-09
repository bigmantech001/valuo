import { cn } from "@/lib/cn";
import { COLORS } from "@/lib/theme";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, spreadLabels, DEFAULT_MARGIN, areaPath, defaultTickFormat, extent, linePath, niceTicks, padDomain, scaleLinear, slug, type BaseChartProps, type Margin, type Point } from "./util";

export interface FanChartProps extends BaseChartProps {
  p10: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p90: number[];
  /** x values (months); defaults to 1..n */
  months?: number[];
  color?: string;
  xFormat?: (m: number) => string;
  yFormat?: (v: number) => string;
  includeZero?: boolean;
  /** horizontal reference (e.g. current FDV) */
  reference?: { y: number; label: string; color?: string } | null;
  markers?: Array<{ x: number; label: string; color?: string }>;
  margin?: Partial<Margin>;
  xTicks?: number;
  yTicks?: number;
}

/** Percentile fan (P10-P90 outer band, P25-P75 inner band, P50 line) over a monthly horizon. */
export function FanChart({
  title,
  description,
  p10,
  p25,
  p50,
  p75,
  p90,
  months,
  color = COLORS.accent,
  xFormat = (m) => `M${m}`,
  yFormat = defaultTickFormat,
  includeZero = false,
  reference = null,
  markers = [],
  width = 640,
  height = 300,
  margin,
  xTicks = 6,
  yTicks = 5,
  className,
}: FanChartProps) {
  const m: Margin = { ...DEFAULT_MARGIN, ...margin };
  const n = p50.length;
  const xs = months ?? Array.from({ length: n }, (_, i) => i + 1);
  const yd = padDomain(extent([...p10, ...p90, ...(reference ? [reference.y] : [])]), 0.06, includeZero);
  const xd = extent(xs);
  const sx = scaleLinear(xd, [m.left, width - m.right]);
  const sy = scaleLinear(yd, [height - m.bottom, m.top]);
  const pts = (arr: number[]): Point[] => arr.map((v, i) => [sx(xs[i] ?? i), sy(v)]);
  const yT = niceTicks(yd, yTicks);
  const xT = niceTicks(xd, xTicks).filter((t) => t >= xd[0] && t <= xd[1]);
  const id = slug(title);
  const last = n - 1;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className={cn("block h-auto w-full", className)} style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      {description ? <desc>{description}</desc> : null}
      {yT.map((t) => (
        <g key={`y${t}`}>
          <line x1={m.left} x2={width - m.right} y1={sy(t)} y2={sy(t)} stroke={COLORS.border} />
          <text x={m.left - 8} y={sy(t)} dy="0.32em" textAnchor="end" fontSize={AXIS_FONT} fill={COLORS.dim}>
            {yFormat(t)}
          </text>
        </g>
      ))}
      <line x1={m.left} x2={width - m.right} y1={height - m.bottom} y2={height - m.bottom} stroke={COLORS.borderStrong} />
      {xT.map((t) => (
        <text key={`x${t}`} x={sx(t)} y={height - m.bottom + 15} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.dim}>
          {xFormat(t)}
        </text>
      ))}
      <path d={areaPath(pts(p90), pts(p10))} fill={color} fillOpacity={0.1}>
        <title>P10-P90 band</title>
      </path>
      <path d={areaPath(pts(p75), pts(p25))} fill={color} fillOpacity={0.2}>
        <title>P25-P75 band</title>
      </path>
      <path d={linePath(pts(p10))} fill="none" stroke={color} strokeOpacity={0.35} strokeWidth={1} />
      <path d={linePath(pts(p90))} fill="none" stroke={color} strokeOpacity={0.35} strokeWidth={1} />
      <path d={linePath(pts(p50))} fill="none" stroke={COLORS.ink} strokeWidth={2}>
        <title>P50</title>
      </path>
      {reference ? (
        <g>
          <line x1={m.left} x2={width - m.right} y1={sy(reference.y)} y2={sy(reference.y)} stroke={reference.color ?? COLORS.muted} strokeDasharray="4 3" />
          <text x={width - m.right} y={sy(reference.y) - 5} textAnchor="end" fontSize={AXIS_FONT} fill={reference.color ?? COLORS.muted}>
            {reference.label}
          </text>
        </g>
      ) : null}
      {markers.map((mk, i) => (
        <g key={i}>
          <line x1={sx(mk.x)} x2={sx(mk.x)} y1={m.top} y2={height - m.bottom} stroke={mk.color ?? COLORS.muted} strokeDasharray="3 3" />
          <text x={sx(mk.x) + 4} y={m.top + 11} fontSize={AXIS_FONT} fill={mk.color ?? COLORS.muted}>
            {mk.label}
          </text>
        </g>
      ))}
      {n > 0
        ? (() => {
            const ends: Array<[string, number]> = [
              ["P90", p90[last]],
              ["P75", p75[last]],
              ["P50", p50[last]],
              ["P25", p25[last]],
              ["P10", p10[last]],
            ];
            // Direct labels at the right edge, nudged apart so converging percentiles never overprint.
            const ys = spreadLabels(
              ends.map(([, v]) => sy(v)),
              LABEL_FONT + 1,
              m.top,
              height - m.bottom,
            );
            return ends.map(([lab, v], i) => (
              <text key={lab} x={sx(xs[last]) + 6} y={ys[i]} dy="0.32em" fontSize={AXIS_FONT} fontWeight={lab === "P50" ? 600 : 400} fill={lab === "P50" ? COLORS.ink : COLORS.muted}>
                {lab} {yFormat(v)}
              </text>
            ));
          })()
        : null}
    </svg>
  );
}
