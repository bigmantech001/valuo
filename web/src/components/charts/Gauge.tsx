import { cn } from "@/lib/cn";
import { fmtInt } from "@/lib/format";
import { COLORS, withAlpha } from "@/lib/theme";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, slug, type BaseChartProps } from "./util";

export interface GaugeBand {
  from: number;
  to: number;
  color: string;
  label: string;
}

export interface GaugeThreshold {
  value: number;
  label: string;
  color?: string;
}

export interface GaugeProps extends BaseChartProps {
  value: number | null | undefined;
  min?: number;
  max?: number;
  bands?: GaugeBand[];
  thresholds?: GaugeThreshold[];
  valueFormat?: (v: number) => string;
  /** text under the value (e.g. "HHI, external callers") */
  label?: string;
}

/** US DOJ / FTC horizontal-merger thresholds: < 1,500 unconcentrated, 1,500-2,500 moderate, > 2,500 highly concentrated. */
export const HHI_BANDS: GaugeBand[] = [
  { from: 0, to: 1500, color: COLORS.emerald, label: "unconcentrated" },
  { from: 1500, to: 2500, color: COLORS.amber, label: "moderate" },
  { from: 2500, to: 10000, color: COLORS.crimson, label: "concentrated" },
];
export const HHI_THRESHOLDS: GaugeThreshold[] = [
  { value: 1500, label: "1,500" },
  { value: 2500, label: "2,500" },
];

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function polar(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  const a = (angleDeg * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
}

/** Arc from angle a0 to a1 (degrees, 180 = left, 0 = right) at radius r. */
function arcPath(cx: number, cy: number, r: number, a0: number, a1: number): string {
  const [x0, y0] = polar(cx, cy, r, a0);
  const [x1, y1] = polar(cx, cy, r, a1);
  const large = Math.abs(a0 - a1) > 180 ? 1 : 0;
  return `M${x0.toFixed(2)},${y0.toFixed(2)}A${r},${r},0,${large},1,${x1.toFixed(2)},${y1.toFixed(2)}`;
}

/** Semi-circular gauge (default HHI 0-10,000 with DOJ bands). Needle at `value`. */
export function Gauge({ title, description, value, min = 0, max = 10_000, bands = HHI_BANDS, thresholds = HHI_THRESHOLDS, valueFormat = (v) => fmtInt(v), label, width = 320, height = 190, className }: GaugeProps) {
  const cx = width / 2;
  const cy = height - 36;
  const r = Math.min(width / 2 - 24, height - 60);
  const angle = (v: number) => 180 - (Math.min(max, Math.max(min, v)) - min) / (max - min || 1) * 180;
  const id = slug(title);
  const has = typeof value === "number" && Number.isFinite(value);
  const band = has ? bands.find((b) => value >= b.from && value < b.to) ?? bands[bands.length - 1] : null;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className={cn("block h-auto w-full", className)} style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      {description ? <desc>{description}</desc> : null}
      <path d={arcPath(cx, cy, r, 180, 0)} fill="none" stroke={COLORS.surface2} strokeWidth={12} />
      {bands.map((b) => (
        <path key={b.label} d={arcPath(cx, cy, r, angle(b.from), angle(b.to))} fill="none" stroke={withAlpha(b.color, 0.45)} strokeWidth={12}>
          <title>{`${cap(b.label)}: ${valueFormat(b.from)} to ${valueFormat(b.to)}`}</title>
        </path>
      ))}
      {thresholds.map((t) => {
        const [x0, y0] = polar(cx, cy, r - 12, angle(t.value));
        const [x1, y1] = polar(cx, cy, r + 12, angle(t.value));
        const [lx, ly] = polar(cx, cy, r + 22, angle(t.value));
        return (
          <g key={t.label}>
            <line x1={x0} y1={y0} x2={x1} y2={y1} stroke={t.color ?? COLORS.muted} strokeWidth={1} />
            <text x={lx} y={ly} dy="0.32em" textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.dim}>
              {t.label}
            </text>
          </g>
        );
      })}
      {has ? (
        (() => {
          const [nx, ny] = polar(cx, cy, r - 18, angle(value));
          return (
            <g>
              <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={COLORS.ink} strokeWidth={2} strokeLinecap="round" />
              <circle cx={cx} cy={cy} r={3.5} fill={COLORS.ink} />
            </g>
          );
        })()
      ) : null}
      <text x={cx} y={cy - 22} textAnchor="middle" fontSize={24} fontWeight={500} fill={has ? COLORS.ink : COLORS.dim} stroke={COLORS.surface} strokeWidth={5} paintOrder="stroke">
        {has ? valueFormat(value) : "n/a"}
      </text>
      {has && band ? (
        <text x={cx} y={cy - 4} textAnchor="middle" fontSize={LABEL_FONT} fontWeight={500} fill={band.color} stroke={COLORS.surface} strokeWidth={4} paintOrder="stroke">
          {cap(band.label)}
        </text>
      ) : null}
      {label ? (
        <text x={cx} y={cy + 18} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.muted}>
          {cap(label)}
        </text>
      ) : null}
      <text x={cx - r} y={cy + 18} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.dim}>
        {valueFormat(min)}
      </text>
      <text x={cx + r} y={cy + 18} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.dim}>
        {valueFormat(max)}
      </text>
    </svg>
  );
}
