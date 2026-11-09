import { fmtMultiple } from "@/lib/format";

/** Multiple with a typographic times sign: 60 -> "60.0×". */
export function mult(v: number | null | undefined, opts: { decimals?: number } = {}): string {
  return fmtMultiple(v, opts).replace(/x$/, "×");
}

/** Human names for the two issuance regimes (snapshot keys stay in MethodNotes). */
export const REGIME_NAME: Record<string, string> = { status_quo: "Status quo", svrn_glidepath: "SVRN glidepath" };
