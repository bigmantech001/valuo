/**
 * Number/date formatters for the terminal. All formatters are null-safe (return `NA` for
 * null/undefined/NaN) and pin `en-US` so server and client render identical strings.
 */

export const NA = "n/a";

const intFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

function fixedFmt(decimals: number): Intl.NumberFormat {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

const FIXED: Record<number, Intl.NumberFormat> = {};
function fixed(decimals: number): Intl.NumberFormat {
  return (FIXED[decimals] ??= fixedFmt(decimals));
}

function bad(v: number | null | undefined): v is null | undefined {
  return v === null || v === undefined || !Number.isFinite(v);
}

export interface FmtOptions {
  /** decimals (default varies by formatter) */
  decimals?: number;
  /** prefix "+" for positive values */
  signed?: boolean;
  /** text for null/NaN (default "n/a") */
  na?: string;
}

function sign(v: number, signed: boolean | undefined): string {
  if (!signed) return v < 0 ? "-" : "";
  return v > 0 ? "+" : v < 0 ? "-" : "";
}

/** 49989.890495 -> "$49,989.89" */
export function fmtUsd(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  const d = opts.decimals ?? 2;
  return `${sign(v, opts.signed)}$${fixed(d).format(Math.abs(v))}`;
}

/** 5_636_000_000 -> "$5.64B"; 141_723_823 -> "$141.7M"; 2_175 -> "$2,175" */
export function fmtUsdCompact(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  return `${sign(v, opts.signed)}$${compactAbs(Math.abs(v), opts.decimals)}`;
}

/** Plain compact magnitude: 32_400_000 -> "32.4M". */
export function fmtCompact(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  return `${sign(v, opts.signed)}${compactAbs(Math.abs(v), opts.decimals)}`;
}

function compactAbs(a: number, decimals?: number): string {
  const units: Array<[number, string]> = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [div, suffix] of units) {
    if (a >= div) {
      const x = a / div;
      // 3 significant figures by default: 5.64B, 141.7M, 32.4M
      const d = decimals ?? (x >= 100 ? 1 : 2);
      return `${fixed(d).format(x)}${suffix}`;
    }
  }
  return fixed(decimals ?? (a >= 100 ? 0 : 2)).format(a);
}

/** 131353.43 -> "131,353 NEAR" (decimals default 0; pass `{decimals: 2}` for sub-unit) */
export function fmtNear(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  const d = opts.decimals ?? 0;
  return `${sign(v, opts.signed)}${fixed(d).format(Math.abs(v))} NEAR`;
}

/** Compact NEAR: 32_400_000 -> "32.4M NEAR" */
export function fmtNearCompact(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  return `${sign(v, opts.signed)}${compactAbs(Math.abs(v), opts.decimals)} NEAR`;
}

/** 1.02 -> "+1.0 bps" when signed (default signed=true, decimals=1) */
export function fmtBps(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  const d = opts.decimals ?? 1;
  const signed = opts.signed ?? true;
  return `${sign(v, signed)}${fixed(d).format(Math.abs(v))} bps`;
}

/** Ratio in, percent out: 0.025 -> "2.50%" (decimals default 2) */
export function fmtPct(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  const d = opts.decimals ?? 2;
  return `${sign(v, opts.signed)}${fixed(d).format(Math.abs(v) * 100)}%`;
}

/** Already-a-percent in: 12.3 -> "12.3%" */
export function fmtPctPoints(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  const d = opts.decimals ?? 1;
  return `${sign(v, opts.signed)}${fixed(d).format(Math.abs(v))}%`;
}

/** 222342342 -> "222,342,342" */
export function fmtInt(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  return `${sign(v, opts.signed)}${intFmt.format(Math.abs(Math.round(v)))}`;
}

/** Fixed decimals without unit: 0.64637909 -> "0.64637909" */
export function fmtNum(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  const d = opts.decimals ?? 2;
  return `${sign(v, opts.signed)}${fixed(d).format(Math.abs(v))}`;
}

/** Multiple: 18.4 -> "18.4x" */
export function fmtMultiple(v: number | null | undefined, opts: FmtOptions = {}): string {
  if (bad(v)) return opts.na ?? NA;
  return `${fixed(opts.decimals ?? 1).format(v)}x`;
}

/**
 * Model month index -> label. `fmtMonth(12)` -> "M12"; with `{quarter: true}` -> "Q4 (M12)".
 * null -> "none within horizon" (a crossover that never happens).
 */
export function fmtMonth(
  m: number | null | undefined,
  opts: { quarter?: boolean; na?: string } = {},
): string {
  if (bad(m)) return opts.na ?? "none within horizon";
  const month = Math.round(m);
  if (!opts.quarter) return `M${month}`;
  const q = Math.max(1, Math.ceil(month / 3));
  return `Q${q} (M${month})`;
}

/** Block height: 222342342 -> "#222,342,342" */
export function fmtBlock(h: number | null | undefined): string {
  if (bad(h)) return NA;
  return `#${intFmt.format(h)}`;
}

/** Hash/address prefix: "BKRbswmairy3R8HnWvyf4dQxhrajJEKCF2fLZCpF2nKq" -> "BKRbswmair..." */
export function fmtHash(h: string | null | undefined, prefix = 10): string {
  if (!h) return NA;
  return h.length <= prefix ? h : `${h.slice(0, prefix)}…`;
}

/** Middle-elide: "0xd8dA6BF2...A96045" */
export function fmtAddress(a: string | null | undefined, head = 6, tail = 4): string {
  if (!a) return NA;
  return a.length <= head + tail + 1 ? a : `${a.slice(0, head)}…${a.slice(-tail)}`;
}

/** 42 -> "42 s"; 490 -> "8.2 min"; 4200 -> "1.2 h" */
export function fmtSeconds(s: number | null | undefined): string {
  if (bad(s)) return NA;
  if (s < 90) return `${fixed(0).format(s)} s`;
  if (s < 5400) return `${fixed(1).format(s / 60)} min`;
  return `${fixed(1).format(s / 3600)} h`;
}

/** 1234.5 -> "1,235 ms"; 0.5 -> "1 ms" */
export function fmtMs(ms: number | null | undefined): string {
  if (bad(ms)) return NA;
  return `${intFmt.format(Math.max(1, Math.round(ms)))} ms`;
}

/** Bytes: 13_135_343_202 -> "13.14 GB" */
export function fmtBytes(b: number | null | undefined): string {
  if (bad(b)) return NA;
  const units = ["B", "KB", "MB", "GB", "TB"];
  let x = b;
  let i = 0;
  while (x >= 1000 && i < units.length - 1) {
    x /= 1000;
    i++;
  }
  return `${fixed(i === 0 ? 0 : 2).format(x)} ${units[i]}`;
}

/** ISO string -> "2026-10-31 01:23 UTC" (seconds optional) */
export function fmtUtc(iso: string | null | undefined, opts: { seconds?: boolean } = {}): string {
  if (!iso) return NA;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const p = (n: number) => String(n).padStart(2, "0");
  const base = `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
  return opts.seconds ? `${base}:${p(d.getUTCSeconds())} UTC` : `${base} UTC`;
}

/** Relative age: 95 -> "1.6 min ago" */
export function fmtAgo(seconds: number | null | undefined): string {
  if (bad(seconds)) return NA;
  const s = Math.max(0, seconds);
  if (s < 60) return `${fixed(0).format(s)} s ago`;
  if (s < 3600) return `${fixed(1).format(s / 60)} min ago`;
  if (s < 86400) return `${fixed(1).format(s / 3600)} h ago`;
  return `${fixed(1).format(s / 86400)} d ago`;
}

/** Raw integer string with decimals -> float (BigInt-safe for 24-dp yocto values). */
export function rawToFloat(raw: string | null | undefined, decimals: number): number | null {
  if (!raw || !/^\d+$/.test(raw)) return null;
  if (raw.length <= 15) return Number(raw) / 10 ** decimals;
  const bi = BigInt(raw);
  const base = BigInt(10) ** BigInt(decimals);
  const whole = bi / base;
  const frac = bi % base;
  return Number(whole) + Number(frac) / Number(base);
}
