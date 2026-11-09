import { NextRequest, NextResponse } from "next/server";
import { buildFreshness } from "@/lib/nearRpc";
import { computeIntegrity, loadArtifacts, readMemo, readSnapshotBytes } from "@/lib/snapshot";
import type { SnapshotApiResponse } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const MISSING = "artifacts missing: run `make reproduce` (or `cd quant && uv run python -m valuo.reproduce`)";

/**
 * GET /api/snapshot
 *   default            -> { snapshot, manifest, freshness, integrity, error }
 *   ?format=freshness  -> { freshness, integrity } only (cheap poll for the provenance bar)
 *   ?format=memo       -> artifacts/IC_MEMO.md as a Markdown download
 *   ?format=json       -> artifacts/latest_snapshot.json bytes as a download (exact bytes, so the
 *                         sha256 in manifest.json can be verified offline)
 * Freshness = one live `block` RPC call with a 5 s timeout; null fields on failure.
 */
export async function GET(req: NextRequest): Promise<Response> {
  const format = req.nextUrl.searchParams.get("format");
  const { snapshot, manifest } = await loadArtifacts();
  const block = manifest?.block_height ?? snapshot?.near_rpc.block_height ?? null;

  if (format === "memo") {
    const memo = await readMemo();
    if (!memo) return NextResponse.json({ error: MISSING }, { status: 404 });
    return new Response(memo, {
      status: 200,
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Content-Disposition": `attachment; filename="Valuo_IC_MEMO${block ? `_block_${block}` : ""}.md"`,
        "Cache-Control": "no-store",
      },
    });
  }

  if (format === "json") {
    const bytes = await readSnapshotBytes();
    if (!bytes) return NextResponse.json({ error: MISSING }, { status: 404 });
    return new Response(new Uint8Array(bytes), {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": `attachment; filename="Valuo_latest_snapshot${block ? `_block_${block}` : ""}.json"`,
        "Cache-Control": "no-store",
      },
    });
  }

  const [freshness, integrity] = await Promise.all([buildFreshness(snapshot, 5000), computeIntegrity(manifest)]);

  if (format === "freshness") {
    return NextResponse.json({ freshness, integrity, error: snapshot ? null : MISSING }, { status: 200, headers: { "Cache-Control": "no-store" } });
  }

  const body: SnapshotApiResponse = {
    snapshot,
    manifest,
    freshness,
    integrity,
    error: snapshot ? null : MISSING,
  };
  return NextResponse.json(body, { status: snapshot ? 200 : 404, headers: { "Cache-Control": "no-store" } });
}
