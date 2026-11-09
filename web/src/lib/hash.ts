import "server-only";
import { createHash } from "node:crypto";

/** sha256(b"") - the digest recorded when no bytes were received (matches provenance.EMPTY_SHA256). */
export const EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

export function sha256Hex(data: Uint8Array | string): string {
  return createHash("sha256").update(data).digest("hex");
}

/**
 * Canonical JSON identical to `provenance.canonical_json`: keys sorted recursively, compact
 * separators, UTF-8. Used so `request_body_sha256` for a POST body matches what the Python
 * collector would record for the same payload.
 */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortKeys(value));
}

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      out[key] = sortKeys((value as Record<string, unknown>)[key]);
    }
    return out;
  }
  return value;
}

export function sha256Json(value: unknown): string {
  return sha256Hex(canonicalJson(value));
}
