import { NextRequest, NextResponse } from "next/server";
import { listJobs, quantDir, reproduceEnabled, runningJob, startReproduceJob, validateArgs } from "@/lib/reproduceJobs";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const DISABLED = "reproduce endpoint disabled: start the web server with VALUO_ALLOW_REPRODUCE=1 (it spawns `uv run python -m valuo.reproduce` locally)";

/**
 * POST /api/reproduce  { args?: string[] }  -> 202 { job }
 * Spawns `uv run python -m valuo.reproduce [args]` in ../quant (non-blocking). Allowed args are
 * the CLI's own flags only. 403 unless VALUO_ALLOW_REPRODUCE=1; 409 while a job is running.
 */
export async function POST(req: NextRequest): Promise<Response> {
  if (!reproduceEnabled()) return NextResponse.json({ error: DISABLED, enabled: false }, { status: 403 });
  const running = runningJob();
  if (running) return NextResponse.json({ error: "a reproduce job is already running", job: running }, { status: 409 });

  let payload: { args?: unknown } = {};
  const text = await req.text();
  if (text.trim()) {
    try {
      payload = JSON.parse(text) as { args?: unknown };
    } catch {
      return NextResponse.json({ error: "body must be JSON {args?: string[]}" }, { status: 400 });
    }
  }
  const validated = validateArgs(payload.args);
  if ("error" in validated) return NextResponse.json({ error: validated.error }, { status: 400 });

  const job = startReproduceJob(validated.args);
  return NextResponse.json({ job }, { status: job.status === "failed" ? 500 : 202, headers: { "Cache-Control": "no-store" } });
}

/** GET /api/reproduce -> { enabled, quant_dir, jobs } */
export async function GET(): Promise<Response> {
  return NextResponse.json(
    { enabled: reproduceEnabled(), quant_dir: quantDir(), jobs: listJobs() },
    { headers: { "Cache-Control": "no-store" } },
  );
}
