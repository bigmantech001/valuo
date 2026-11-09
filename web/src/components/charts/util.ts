import { fmtCompact } from "@/lib/format";

/** Shared geometry helpers for the hand-rolled SVG charts. Pure functions, no DOM. */

export interface Margin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export const DEFAULT_MARGIN: Margin = { top: 12, right: 16, bottom: 28, left: 56 };

export interface BaseChartProps {
  /** accessible title rendered as <title> (required: screen readers and hover) */
  title: string;
  /** longer accessible description rendered as <desc> */
  description?: string;
  /** viewBox width/height; the SVG scales to its container width */
  width?: number;
  height?: number;
  className?: string;
}

export function extent(values: ArrayLike<number>): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (!Number.isFinite(v)) continue;
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  if (lo === Infinity) return [0, 1];
  if (lo === hi) return lo === 0 ? [0, 1] : [lo - Math.abs(lo) * 0.1, hi + Math.abs(hi) * 0.1];
  return [lo, hi];
}

/** Pad a domain by `pct` on each side, keeping 0 inside when `includeZero`. */
export function padDomain([lo, hi]: [number, number], pct = 0.05, includeZero = false): [number, number] {
  const span = hi - lo || 1;
  let a = lo - span * pct;
  let b = hi + span * pct;
  if (includeZero) {
    a = Math.min(a, 0);
    b = Math.max(b, 0);
  }
  return [a, b];
}

export function scaleLinear(domain: [number, number], range: [number, number]): (v: number) => number {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v: number) => r0 + (v - d0) * k;
}

/** "Nice" tick values spanning the domain (d3-style step of 1/2/5 x 10^n). */
export function niceTicks([lo, hi]: [number, number], count = 5): number[] {
  if (!(hi > lo)) return [lo];
  const rawStep = (hi - lo) / Math.max(1, count);
  const mag = 10 ** Math.floor(Math.log10(rawStep));
  const norm = rawStep / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const start = Math.ceil(lo / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= hi + step * 1e-9; v += step) ticks.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  return ticks;
}

export type Point = [number, number];

export function linePath(points: Point[]): string {
  let d = "";
  let pen = false;
  for (const [x, y] of points) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      pen = false;
      continue;
    }
    d += `${pen ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
    pen = true;
  }
  return d;
}

/** Closed band between an upper and a lower series (same x positions). */
export function areaPath(upper: Point[], lower: Point[]): string {
  const up = linePath(upper);
  const down = [...lower].reverse().map(([x, y]) => `L${x.toFixed(2)},${y.toFixed(2)}`).join("");
  return up && down ? `${up}${down}Z` : "";
}

export function defaultTickFormat(v: number): string {
  return fmtCompact(v);
}

/** Deterministic id-safe slug for <title>/<desc> ids (no useId: charts render on the server too). */
export function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

/** Interpolate two hex colours (t in [0,1]). */
export function mixHex(a: string, b: string, t: number): string {
  const pa = hexToRgb(a);
  const pb = hexToRgb(b);
  const k = Math.min(1, Math.max(0, t));
  const c = pa.map((x, i) => Math.round(x + (pb[i] - x) * k));
  return `#${c.map((x) => x.toString(16).padStart(2, "0")).join("")}`;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Axis tick text (viewBox units; charts render near 1:1 at their default widths). */
export const AXIS_FONT = 11;
/** Direct labels and in-chart values. */
export const LABEL_FONT = 12;

/** Inline style shared by every chart <svg>: inherit the page font (Inter) and use tabular figures. */
export const SVG_STYLE = { fontFamily: "inherit", fontVariantNumeric: "tabular-nums" } as const;

/** WCAG relative luminance of a hex colour. */
export function luminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((c) => {
    const x = c / 255;
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Contrast ratio between two hex colours (1..21). */
export function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/** Of the candidate text colours, the one with the highest contrast on `bg`. */
export function readableOn(bg: string, candidates: string[]): string {
  return candidates.reduce((best, c) => (contrast(c, bg) > contrast(best, bg) ? c : best), candidates[0]);
}

/**
 * Nudge label y positions apart so no two are closer than `gap` (keeps order). Used for
 * direct end-of-line labels that would otherwise overprint when series converge.
 */
export function spreadLabels(ys: number[], gap: number, lo = -Infinity, hi = Infinity): number[] {
  const idx = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y);
  for (let k = 1; k < idx.length; k++) if (idx[k].y - idx[k - 1].y < gap) idx[k].y = idx[k - 1].y + gap;
  const over = idx.length ? idx[idx.length - 1].y - hi : 0;
  if (over > 0) for (const e of idx) e.y -= over;
  for (let k = 0; k < idx.length; k++) if (idx[k].y < lo) idx[k].y = lo + k * gap;
  const out = new Array<number>(ys.length);
  for (const e of idx) out[e.i] = e.y;
  return out;
}
