/**
 * Theme tokens as TypeScript constants for hand-rolled SVG charts, which cannot read
 * Tailwind utilities for `fill` / `stroke`. Values mirror `src/app/globals.css` exactly.
 */
export const COLORS = {
  canvas: "#FBFAF7",
  surface: "#FFFFFF",
  surface2: "#F4F2EC",
  border: "#E6E2D8",
  borderStrong: "#CFC9BB",
  ink: "#16150F",
  muted: "#5B584F",
  dim: "#8A8679",
  emerald: "#1F7A4D",
  amber: "#9A6A00",
  crimson: "#B3261E",
  accent: "#1F4FBF",
} as const;

export type Tone = "neutral" | "emerald" | "amber" | "crimson" | "accent";

export const TONE_COLOR: Record<Tone, string> = {
  neutral: COLORS.muted,
  emerald: COLORS.emerald,
  amber: COLORS.amber,
  crimson: COLORS.crimson,
  accent: COLORS.accent,
};

/**
 * Ordered categorical palette for multi-series charts. Muted, print-safe hues that stay
 * distinguishable for common colour-vision deficiencies; the sign colours (emerald/crimson)
 * are deliberately not in it, so a series colour is never read as "good" or "bad".
 */
export const SERIES_COLORS: readonly string[] = ["#1F4FBF", "#C2702B", "#2F7F72", "#7A4E9C", "#8A8679", "#16150F"];

/** Venue colours used by the quote race and spread matrix (1Click carries the accent). */
export const VENUE_COLORS: Record<string, string> = {
  "1click": SERIES_COLORS[0],
  relay: SERIES_COLORS[1],
  lifi: SERIES_COLORS[2],
  across: SERIES_COLORS[3],
};

/** Hex colour -> rgba() string with the given alpha, for fills behind strokes. */
export function withAlpha(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
