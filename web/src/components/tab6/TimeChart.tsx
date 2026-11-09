import { cn } from "@/lib/cn";
import { COLORS, SERIES_COLORS, withAlpha } from "@/lib/theme";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, areaPath, defaultTickFormat, extent, linePath, niceTicks, padDomain, scaleLinear, slug, spreadLabels, type Point } from "@/components/charts/util";

/**
 * Time-series chart for the history store: x is UTC time, points can be sparse or null, and a
 * series with a single observation renders as a dot with its value, never as an implied line.
 * Optional pieces: one shaded interval band (drawn as error bars while it has fewer than two points),
 * horizontal reference lines (a trigger threshold, 100% coverage), a zero line, and direct
 * end-of-line labels (value coloured by sign when `signColor` is set). Pure SVG, renders on the server.
 */

export type TimePoint = [string, number | null];

export interface TimeSeries {
  name: string;
  points: TimePoint[];
  color?: string;
  dashed?: boolean;
  /** colour the end label by the sign of the latest value (emerald > 0, crimson < 0) */
  signColor?: boolean;
}

export interface TimeBand {
  name: string;
  lo: TimePoint[];
  hi: TimePoint[];
  color?: string;
}

export interface RefLine {
  y: number;
  label: string;
  color?: string;
}

export interface TimeChartProps {
  title: string;
  description?: string;
  series: TimeSeries[];
  band?: TimeBand | null;
  refLines?: RefLine[];
  yFormat?: (v: number) => string;
  /** value format for end labels and point tooltips (defaults to yFormat) */
  valueFormat?: (v: number) => string;
  includeZero?: boolean;
  zeroLine?: boolean;
  width?: number;
  height?: number;
  /** points drawn as circles when a series has at most this many (default 60) */
  pointLimit?: number;
  className?: string;
}

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const STEPS = [5 * 60_000, 15 * 60_000, 30 * 60_000, HOUR, 3 * HOUR, 6 * HOUR, 12 * HOUR, DAY, 2 * DAY, 7 * DAY, 14 * DAY, 30 * DAY, 91 * DAY];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function ms(t: string): number {
  const v = Date.parse(t);
  return Number.isFinite(v) ? v : NaN;
}

function timeTicks([lo, hi]: [number, number], target: number): { ticks: number[]; step: number } {
  const span = hi - lo;
  const step = STEPS.find((s) => span / s <= target) ?? STEPS[STEPS.length - 1];
  const ticks: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) ticks.push(t);
  return { ticks, step };
}

function fmtTick(t: number, step: number): string {
  const d = new Date(t);
  const p = (n: number) => String(n).padStart(2, "0");
  const date = `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
  if (step >= DAY) return date;
  const time = `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
  return d.getUTCHours() === 0 && d.getUTCMinutes() === 0 ? date : step >= 3 * HOUR ? `${date} ${time}` : time;
}

function fmtWhen(t: number): string {
  const d = new Date(t);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())} UTC`;
}

export function TimeChart({
  title,
  description,
  series,
  band = null,
  refLines = [],
  yFormat = defaultTickFormat,
  valueFormat,
  includeZero = false,
  zeroLine = false,
  width = 640,
  height = 250,
  pointLimit = 60,
  className,
}: TimeChartProps) {
  const vf = valueFormat ?? yFormat;
  const parsed = series.map((s, i) => ({
    ...s,
    color: s.color ?? SERIES_COLORS[i % SERIES_COLORS.length],
    pts: s.points.map(([t, v]) => [ms(t), typeof v === "number" && Number.isFinite(v) ? v : NaN] as [number, number]).filter(([t]) => Number.isFinite(t)),
  }));
  const bandPts = band
    ? band.lo
        .map(([t, lo], i) => [ms(t), lo, band.hi[i]?.[1] ?? null] as const)
        .filter(([t, lo, hi]) => Number.isFinite(t) && typeof lo === "number" && typeof hi === "number")
        .map(([t, lo, hi]) => [t, lo as number, hi as number] as [number, number, number])
    : [];

  const xs = [...parsed.flatMap((s) => s.pts.map(([t]) => t)), ...bandPts.map(([t]) => t)];
  let [x0, x1] = xs.length ? [Math.min(...xs), Math.max(...xs)] : [Date.now() - DAY, Date.now()];
  // One timestamp: centre it in a 12-hour window so the axis still reads as time.
  const span = x1 - x0;
  const padX = span > 0 ? span * 0.03 : 6 * HOUR;
  x0 -= padX;
  x1 += padX;

  const ys = [...parsed.flatMap((s) => s.pts.map(([, v]) => v)), ...bandPts.flatMap(([, lo, hi]) => [lo, hi]), ...refLines.map((r) => r.y)].filter(Number.isFinite);
  // Floor the visible span at 2% of the level so quote-to-quote noise in the 5th decimal is not drawn as a trend.
  let [ylo, yhi] = extent(ys);
  const floor = Math.abs((ylo + yhi) / 2) * 0.02;
  if (yhi - ylo < floor) {
    const c = (ylo + yhi) / 2;
    ylo = c - floor / 2;
    yhi = c + floor / 2;
  }
  const yd = padDomain([ylo, yhi], 0.12, includeZero || zeroLine);
  const yT = niceTicks(yd, 5);

  // Right margin holds the end labels; size it from the longest one.
  const endLabels = parsed.map((s) => {
    const last = [...s.pts].reverse().find(([, v]) => Number.isFinite(v));
    return last ? `${s.name} ${vf(last[1])}` : "";
  });
  const longest = Math.max(0, ...endLabels.map((l) => l.length));
  const longestTick = Math.max(0, ...yT.map((t) => yFormat(t).length));
  const m = { top: 14, right: Math.min(220, 14 + longest * LABEL_FONT * 0.56), bottom: 26, left: Math.max(40, 14 + longestTick * AXIS_FONT * 0.6) };

  const sx = scaleLinear([x0, x1], [m.left, width - m.right]);
  const sy = scaleLinear(yd, [height - m.bottom, m.top]);
  const { ticks: xT, step } = timeTicks([x0, x1], Math.max(3, Math.floor((width - m.left - m.right) / 95)));
  const id = slug(title);

  const lastPoints = parsed.map((s) => [...s.pts].reverse().find(([, v]) => Number.isFinite(v)) ?? null);
  const labelYs = spreadLabels(
    lastPoints.map((p) => (p ? sy(p[1]) : 0)),
    LABEL_FONT + 3,
    m.top + 4,
    height - m.bottom - 2,
  );
  const bandColor = band?.color ?? COLORS.dim;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className={cn("block h-auto w-full", className)} style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      {description ? <desc>{description}</desc> : null}
      {yT.map((t) => (
        <g key={`y${t}`}>
          <line x1={m.left} x2={width - m.right} y1={sy(t)} y2={sy(t)} stroke={t === 0 && zeroLine ? COLORS.borderStrong : COLORS.border} strokeWidth={1} />
          <text x={m.left - 8} y={sy(t)} dy="0.32em" textAnchor="end" fontSize={AXIS_FONT} fill={COLORS.dim}>
            {yFormat(t)}
          </text>
        </g>
      ))}
      {zeroLine && yd[0] <= 0 && yd[1] >= 0 ? <line x1={m.left} x2={width - m.right} y1={sy(0)} y2={sy(0)} stroke={COLORS.muted} strokeWidth={1} /> : null}
      <line x1={m.left} x2={width - m.right} y1={height - m.bottom} y2={height - m.bottom} stroke={COLORS.borderStrong} strokeWidth={1} />
      {xT.map((t) => (
        <g key={`x${t}`}>
          <line x1={sx(t)} x2={sx(t)} y1={height - m.bottom} y2={height - m.bottom + 4} stroke={COLORS.borderStrong} />
          <text x={sx(t)} y={height - m.bottom + 16} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.dim}>
            {fmtTick(t, step)}
          </text>
        </g>
      ))}

      {/* interval band: area once it has two points, error bars before that */}
      {bandPts.length >= 2 ? (
        <path
          d={areaPath(
            bandPts.map(([t, , hi]) => [sx(t), sy(hi)] as Point),
            bandPts.map(([t, lo]) => [sx(t), sy(lo)] as Point),
          )}
          fill={withAlpha(bandColor, 0.16)}
        >
          <title>{band?.name}</title>
        </path>
      ) : (
        bandPts.map(([t, lo, hi]) => (
          <g key={`eb${t}`} stroke={bandColor} strokeWidth={1.25}>
            <title>{`${band?.name} @ ${fmtWhen(t)}: ${vf(lo)} to ${vf(hi)}`}</title>
            <line x1={sx(t)} x2={sx(t)} y1={sy(lo)} y2={sy(hi)} />
            <line x1={sx(t) - 5} x2={sx(t) + 5} y1={sy(lo)} y2={sy(lo)} />
            <line x1={sx(t) - 5} x2={sx(t) + 5} y1={sy(hi)} y2={sy(hi)} />
          </g>
        ))
      )}

      {refLines.map((r) => (
        <g key={`ref${r.label}`}>
          <line x1={m.left} x2={width - m.right} y1={sy(r.y)} y2={sy(r.y)} stroke={r.color ?? COLORS.crimson} strokeWidth={1} strokeDasharray="5 4" />
          <text x={m.left + 6} y={sy(r.y) - 5} fontSize={AXIS_FONT} fill={r.color ?? COLORS.crimson}>
            {r.label}
          </text>
        </g>
      ))}

      {parsed.map((s) => {
        const pts: Point[] = s.pts.map(([t, v]) => [sx(t), sy(v)]);
        const finiteN = s.pts.filter(([, v]) => Number.isFinite(v)).length;
        const drawDots = finiteN <= pointLimit;
        return (
          <g key={s.name}>
            {finiteN >= 2 ? <path d={linePath(pts)} fill="none" stroke={s.color} strokeWidth={1.75} strokeDasharray={s.dashed ? "5 4" : undefined} strokeLinejoin="round" /> : null}
            {s.pts.map(([t, v], i) =>
              Number.isFinite(v) && (drawDots || i === s.pts.length - 1) ? (
                <circle key={i} cx={pts[i][0]} cy={pts[i][1]} r={finiteN === 1 ? 3.6 : 2.4} fill={s.color}>
                  <title>{`${s.name} @ ${fmtWhen(t)}: ${vf(v)}`}</title>
                </circle>
              ) : null,
            )}
          </g>
        );
      })}

      {parsed.map((s, i) => {
        const lp = lastPoints[i];
        if (!lp) return null;
        const v = lp[1];
        const valueColor = s.signColor ? (v > 0 ? COLORS.emerald : v < 0 ? COLORS.crimson : COLORS.muted) : COLORS.ink;
        return (
          <text key={`end${s.name}`} x={width - m.right + 8} y={labelYs[i]} dy="0.32em" fontSize={LABEL_FONT}>
            <tspan fill={s.color}>{s.name}</tspan>
            <tspan fill={valueColor} dx={5}>
              {vf(v)}
            </tspan>
          </text>
        );
      })}
    </svg>
  );
}
