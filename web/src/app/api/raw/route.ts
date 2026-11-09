import { NextRequest, NextResponse } from "next/server";
import { clientIp, createLimiter, tooManyRequests } from "@/lib/rateLimit";
import { VerifyError, findRecord, readRawBytes } from "@/lib/verifyServer";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/raw?source=<source>&name=<record name>
 * Streams the exact stored response bytes for a manifest record (artifacts/raw/<source>__<name>.json), so the
 * browser can SHA-256 them itself and compare with the manifest. The file path comes only from the manifest's
 * raw_path and must resolve inside artifacts/raw. 404 for unknown records or records without stored bytes.
 */
// "Re-hash all" reads every manifest record (~80 files) in one burst, so the per-IP allowance is generous.
const limit = createLimiter({ perIp: 300, global: 1500, windowMs: 5 * 60_000 });

export async function GET(req: NextRequest): Promise<Response> {
  const decision = limit(clientIp(req));
  if (!decision.ok) return tooManyRequests(decision, "raw-file");
  const sp = req.nextUrl.searchParams;
  try {
    const { record } = await findRecord(sp.get("source"), sp.get("name"));
    const bytes = await readRawBytes(record);
    return new Response(new Uint8Array(bytes), {
      status: 200,
      headers: {
        // octet-stream so no layer re-encodes or pretty-prints the body; the digest is over these bytes.
        "Content-Type": "application/octet-stream",
        "Content-Length": String(bytes.length),
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Valuo-Manifest-Sha256": record.sha256,
        "X-Valuo-Raw-Path": record.raw_path ?? "",
      },
    });
  } catch (e) {
    if (e instanceof VerifyError) return NextResponse.json({ error: e.message }, { status: e.status });
    return NextResponse.json({ error: "could not read raw file" }, { status: 500 });
  }
}
