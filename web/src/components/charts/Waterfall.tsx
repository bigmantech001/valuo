import { cn } from "@/lib/cn";
import { COLORS, SERIES_COLORS } from "@/lib/theme";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, DEFAULT_MARGIN, defaultTickFormat, niceTicks, padDomain, scaleLinear, slug, type BaseChartProps, type Margin } from "./util";

export interface WaterfallStep {
  label: string;
  value: number;
  color?: string;
  /** small text under the label (e.g. "assumption-heavy") */
  sublabel?: string;
}

export interface WaterfallProps extends BaseChartProps {
  steps: WaterfallStep[];
  /** final bar from 0 to the running total (default label "Total") */
  total?: { label: string; color?: string } | null;
  valueFormat?: (v: number) => string;
  /** horizontal reference line (e.g. current FDV) */
  reference?: { y: number; label: string; color?: string } | null;
  margin?: Partial<Margin>;
}

/** SOTP waterfall: each engine's contribution stacks from the previous running total. */
export function Waterfall({ title, description, steps, total = { label: "Total" }, valueFormat = defaultTickFormat, reference = null, width = 640, height = 300, margin, className }: WaterfallProps) {
  const m: Margin = { ...DEFAULT_MARGIN, bottom: 46, ...margin };
  const bars: Array<{ label: string; sublabel?: string; start: number; end: number; color: string; isTotal: boolean; value: number }> = [];
  let running = 0;
  for (const s of steps) {
    const start = running;
    const end = running + s.value;
    bars.push({ label: s.label, sublabel: s.sublabel, start, end, color: s.color ?? (s.value >= 0 ? SERIES_COLORS[0] : COLORS.crimson), isTotal: false, value: s.value });
    running = end;
  }
  if (total) bars.push({ label: total.label, start: 0, end: running, color: total.color ?? COLORS.ink, isTotal: true, value: running });
  const ys = bars.flatMap((b) => [b.start, b.end]).concat(reference ? [reference.y] : []);
  const yd = padDomain([Math.min(0, ...ys), Math.max(0, ...ys)], 0.08, true);
  const sy = scaleLinear(yd, [height - m.bottom, m.top]);
  const n = bars.length;
  const slot = (width - m.left - m.right) / Math.max(1, n);
  const bw = Math.min(72, slot * 0.6);
  const yT = niceTicks(yd, 5);
  const id = slug(title);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className={cn("block h-auto w-full", className)} style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      {description ? <desc>{description}</desc> : null}
      {yT.map((t) => (
        <g key={`y${t}`}>
          <line x1={m.left} x2={width - m.right} y1={sy(t)} y2={sy(t)} stroke={t === 0 ? COLORS.borderStrong : COLORS.border} />
          <text x={m.left - 8} y={sy(t)} dy="0.32em" textAnchor="end" fontSize={AXIS_FONT} fill={COLORS.dim}>
            {valueFormat(t)}
          </text>
        </g>
      ))}
      {bars.map((b, i) => {
        const x = m.left + i * slot + (slot - bw) / 2;
        const y0 = sy(Math.max(b.start, b.end));
        const h = Math.max(1, Math.abs(sy(b.start) - sy(b.end)));
        const next = bars[i + 1];
        return (
          <g key={`${b.label}-${i}`}>
            <rect x={x} y={y0} width={bw} height={h} rx={1.5} fill={b.color} fillOpacity={b.isTotal ? 0.9 : 0.75}>
              <title>{`${b.label}: ${valueFormat(b.value)}${b.isTotal ? "" : ` (running ${valueFormat(b.end)})`}`}</title>
            </rect>
            {next && !b.isTotal ? <line x1={x + bw} x2={m.left + (i + 1) * slot + (slot - bw) / 2} y1={sy(b.end)} y2={sy(b.end)} stroke={COLORS.borderStrong} strokeDasharray="2 2" /> : null}
            <text x={x + bw / 2} y={y0 - 6} textAnchor="middle" fontSize={LABEL_FONT} fontWeight={b.isTotal ? 600 : 500} fill={COLORS.ink}>
              {valueFormat(b.value)}
            </text>
            <text x={x + bw / 2} y={height - m.bottom + 16} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.muted}>
              {b.label}
            </text>
            {b.sublabel ? (
              <text x={x + bw / 2} y={height - m.bottom + 30} textAnchor="middle" fontSize={AXIS_FONT - 0.5} fill={COLORS.dim}>
                {b.sublabel}
              </text>
            ) : null}
          </g>
        );
      })}
      {reference ? (
        <g>
          <line x1={m.left} x2={width - m.right} y1={sy(reference.y)} y2={sy(reference.y)} stroke={reference.color ?? COLORS.muted} strokeDasharray="4 3" />
          <text x={width - m.right} y={sy(reference.y) - 5} textAnchor="end" fontSize={AXIS_FONT} fill={reference.color ?? COLORS.muted}>
            {reference.label}
          </text>
        </g>
      ) : null}
    </svg>
  );
}
