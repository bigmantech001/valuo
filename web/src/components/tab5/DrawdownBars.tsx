import { fmtPct, NA } from "@/lib/format";
import { COLORS, withAlpha } from "@/lib/theme";
import type { BearCase } from "@/lib/types";
import { niceTicks, padDomain, scaleLinear, slug } from "@/components/charts";
import { Card } from "@/components/ui";
import { buildStressRows } from "./bearData";

interface BarRow {
  key: string;
  label: string;
  fdv: number | null;
  price: number | null;
  emphasis: boolean;
}

const WIDTH = 1100;
const LABEL_W = 330;
const VALUE_W = 130;
const ROW_H = 46;
const BAR_H = 13;
const AXIS_FONT = 12;
const LABEL_FONT = 13;

/** Sign colour: a fall is crimson, a rise emerald, zero neutral. */
function signColor(v: number): string {
  return v < 0 ? COLORS.crimson : v > 0 ? COLORS.emerald : COLORS.muted;
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

function DrawdownSvg({ rows }: { rows: BarRow[] }) {
  const width = WIDTH;
  const top = 6;
  const axisH = 26;
  const plotH = rows.length * ROW_H;
  const height = top + plotH + axisH;
  const barX = LABEL_W + 16;
  const barW = Math.max(40, width - barX - VALUE_W - 12);
  const values = rows.flatMap((r) => [r.fdv, r.price]).filter((v): v is number => v !== null);
  const domain = padDomain([Math.min(0, ...values), Math.max(0, ...values)], 0.02, true);
  const sx = scaleLinear(domain, [barX, barX + barW]);
  const ticks = niceTicks(domain, 5);
  const zero = sx(0);
  const title = "Change in value and implied price versus the deterministic base, per scenario";
  const id = slug(title);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby={`${id}-title`} className="block h-auto w-full" style={{ fontFamily: "inherit" }}>
      <title id={`${id}-title`}>{title}</title>
      <desc>For each stress scenario and the combined worst case: a solid bar for the change in deterministic value and a lighter bar for the change in implied price; zero is the base.</desc>
      {ticks.map((t) => (
        <g key={`t${t}`}>
          <line x1={sx(t)} x2={sx(t)} y1={top} y2={top + plotH} stroke={COLORS.border} />
          <text x={sx(t)} y={top + plotH + 18} textAnchor="middle" fontSize={AXIS_FONT} fill={COLORS.dim} style={{ fontVariantNumeric: "tabular-nums" }}>
            {fmtPct(t, { decimals: 0, signed: t !== 0 })}
          </text>
        </g>
      ))}
      {rows.map((r, i) => {
        const y = top + i * ROW_H;
        const bars: Array<{ v: number | null; dy: number; name: string; alpha: number }> = [
          { v: r.fdv, dy: 8, name: "Value", alpha: 0.85 },
          { v: r.price, dy: 8 + BAR_H + 3, name: "Price", alpha: 0.32 },
        ];
        return (
          <g key={r.key}>
            {i > 0 ? <line x1={0} x2={width} y1={y} y2={y} stroke={COLORS.border} strokeOpacity={0.6} /> : null}
            <text x={LABEL_W} y={y + ROW_H / 2} dy="0.32em" textAnchor="end" fontSize={LABEL_FONT} fill={COLORS.ink} fontWeight={r.emphasis ? 600 : 400}>
              {truncate(r.label, 46)}
            </text>
            {bars.map((b) => {
              const ty = y + b.dy + BAR_H / 2;
              if (b.v === null) {
                return (
                  <text key={b.name} x={barX + barW + 10} y={ty} dy="0.32em" fontSize={AXIS_FONT} fill={COLORS.dim}>
                    {b.name} {NA}
                  </text>
                );
              }
              const c = signColor(b.v);
              const x0 = Math.min(zero, sx(b.v));
              const w = Math.max(b.v === 0 ? 1.5 : 0, Math.abs(sx(b.v) - zero));
              return (
                <g key={b.name}>
                  <rect x={x0} y={y + b.dy} width={w} height={BAR_H} rx={1.5} fill={withAlpha(c, b.alpha)}>
                    <title>{`${r.label}: ${b.name.toLowerCase()} ${fmtPct(b.v, { decimals: 1, signed: true })} versus base`}</title>
                  </rect>
                  <text x={barX + barW + 10} y={ty} dy="0.32em" fontSize={AXIS_FONT} fill={b.name === "Value" ? c : COLORS.muted} style={{ fontVariantNumeric: "tabular-nums" }}>
                    <tspan fill={COLORS.dim}>{b.name} </tspan>
                    {fmtPct(b.v, { decimals: 1, signed: true })}
                  </text>
                </g>
              );
            })}
          </g>
        );
      })}
      <line x1={zero} x2={zero} y1={top} y2={top + plotH} stroke={COLORS.ink} strokeOpacity={0.55} />
    </svg>
  );
}

/** Horizontal change-versus-base bars per scenario: deterministic value (solid) and implied price (light). */
export function DrawdownBars({ bear }: { bear: BearCase }) {
  const rows: BarRow[] = buildStressRows(bear)
    .filter((r) => r.kind !== "base")
    .map((r) => ({ key: r.key, label: r.title, fdv: r.drawdown, price: r.priceDrawdown, emphasis: r.kind === "combined" }));
  const hasAny = rows.some((r) => r.fdv !== null || r.price !== null);
  return (
    <Card
      title="How far each scenario moves value and price"
      subtitle="Zero is the deterministic base. Solid bars are the change in value; light bars the change in implied price, which differs only when a scenario changes NEAR supply at the horizon."
    >
      {hasAny ? (
        <div className="overflow-x-auto valuo-scroll">
          <div className="min-w-[680px]">
            <DrawdownSvg rows={rows} />
          </div>
        </div>
      ) : (
        <p className="py-6 text-center text-[13px] text-muted">No scenario changes are recorded in this snapshot.</p>
      )}
    </Card>
  );
}
