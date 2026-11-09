import { NextRequest, NextResponse } from "next/server";
import { CORRIDORS, CORRIDOR_IDS, DEFAULT_CLIPS_USD, toCorridor } from "@/lib/corridors";
import { benchmarkAddresses, runLiveBenchmark, venueTimeoutMs } from "@/lib/liveBenchmark";
import type { LiveBenchmarkRequest } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** Clips above this are refused: dry quotes for absurd sizes only measure venue limits. */
const MAX_CLIP_USD = 10_000_000;
const MIN_CLIP_USD = 1;

/**
 * POST /api/live-benchmark  { corridor_id, clip_usd }
 * Fires the 1Click / Relay / LI.FI / Across quote requests concurrently with the exact payloads
 * documented in docs/LIVE_ENDPOINT_FACTS.md sections 2-3 and returns a CorridorClipResult plus
 * the per-venue RawRecords (sha256 of each raw response). Nothing is cached or synthesised.
 */
export async function POST(req: NextRequest): Promise<Response> {
  let body: Partial<LiveBenchmarkRequest>;
  try {
    body = (await req.json()) as Partial<LiveBenchmarkRequest>;
  } catch {
    return NextResponse.json({ error: "body must be JSON {corridor_id, clip_usd}" }, { status: 400 });
  }
  const corridorId = typeof body.corridor_id === "string" ? body.corridor_id : "";
  if (!CORRIDOR_IDS.includes(corridorId)) {
    return NextResponse.json({ error: `corridor_id must be one of ${CORRIDOR_IDS.join(", ")}` }, { status: 400 });
  }
  const clip = typeof body.clip_usd === "number" ? body.clip_usd : Number(body.clip_usd);
  if (!Number.isFinite(clip) || clip < MIN_CLIP_USD || clip > MAX_CLIP_USD) {
    return NextResponse.json({ error: `clip_usd must be a number in [${MIN_CLIP_USD}, ${MAX_CLIP_USD}]` }, { status: 400 });
  }
  try {
    const result = await runLiveBenchmark(corridorId, clip);
    return NextResponse.json(result, { status: 200, headers: { "Cache-Control": "no-store" } });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/** GET /api/live-benchmark -> corridor catalogue for the selector (no quotes are fetched). */
export async function GET(): Promise<Response> {
  const addresses = benchmarkAddresses();
  return NextResponse.json(
    {
      corridors: CORRIDORS.map((c) => ({ ...toCorridor(c), same_asset: c.same_asset, venue_notes: c.venue_notes })),
      clips_usd: DEFAULT_CLIPS_USD,
      max_clip_usd: MAX_CLIP_USD,
      venue_timeout_ms: venueTimeoutMs(),
      recipients: addresses,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
