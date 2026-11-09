import { NextRequest, NextResponse } from "next/server";
import { clientIp, createLimiter, tooManyRequests } from "@/lib/rateLimit";
import { VerifyError, assertAllowedUrl, findRecord, refetchRecord } from "@/lib/verifyServer";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * POST /api/refetch  {source, name[, url]}
 * Re-issues a manifest record's original request now (10 s timeout) and returns
 * {status, bytes, sha256, fetched_at, changed, diff_summary, ...}. Only the recorded URL is ever requested,
 * and only when its host appears in the manifest (HTTPS). An optional `url` must be on an allowlisted host
 * and equal the recorded URL; it exists so a client can assert which URL it expects. POST records are
 * re-issued only for NEAR JSON-RPC, whose body is rebuilt and checked against request_body_sha256.
 * Rate limited in memory (20 per IP, 120 overall, per 5 minutes); over the limit -> 429 with Retry-After.
 */
// Each call makes one outbound request to a third-party API: 20 per IP and 120 in total per 5 minutes.
const limit = createLimiter({ perIp: 20, global: 120, windowMs: 5 * 60_000 });

export async function POST(req: NextRequest): Promise<Response> {
  const decision = limit(clientIp(req));
  if (!decision.ok) return tooManyRequests(decision, "re-fetch");
  let payload: { source?: unknown; name?: unknown; url?: unknown };
  try {
    payload = (await req.json()) as typeof payload;
  } catch {
    return NextResponse.json({ error: "body must be JSON {source, name}", reason: "bad-request" }, { status: 400 });
  }
  const source = typeof payload.source === "string" ? payload.source : null;
  const name = typeof payload.name === "string" ? payload.name : null;
  try {
    const { manifest, record } = await findRecord(source, name);
    if (payload.url !== undefined) {
      if (typeof payload.url !== "string") throw new VerifyError("url must be a string", 400, "bad-request");
      assertAllowedUrl(payload.url, manifest);
      if (payload.url !== record.url) throw new VerifyError("url does not match the manifest record; only recorded URLs are re-fetched", 400, "bad-request");
    }
    const result = await refetchRecord(manifest, record);
    return NextResponse.json(result, { status: 200, headers: { "Cache-Control": "no-store" } });
  } catch (e) {
    if (e instanceof VerifyError) return NextResponse.json({ error: e.message, reason: e.reason }, { status: e.status });
    return NextResponse.json({ error: e instanceof Error ? e.message : "refetch failed" }, { status: 500 });
  }
}
