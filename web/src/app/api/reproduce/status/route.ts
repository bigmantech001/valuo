import { NextRequest, NextResponse } from "next/server";
import { getJob, listJobs, reproduceEnabled, runningJob } from "@/lib/reproduceJobs";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/reproduce/status?id=<job id>  -> { job }
 * GET /api/reproduce/status              -> { job: running job or most recent, enabled }
 */
export async function GET(req: NextRequest): Promise<Response> {
  const id = req.nextUrl.searchParams.get("id");
  if (id) {
    const job = getJob(id);
    if (!job) return NextResponse.json({ error: `unknown job ${id}` }, { status: 404 });
    return NextResponse.json({ job, enabled: reproduceEnabled() }, { headers: { "Cache-Control": "no-store" } });
  }
  const jobs = listJobs();
  const job = runningJob() ?? jobs[jobs.length - 1] ?? null;
  return NextResponse.json({ job, enabled: reproduceEnabled() }, { headers: { "Cache-Control": "no-store" } });
}
