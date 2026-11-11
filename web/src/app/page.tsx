import Link from "next/link";
import { fmtInt, fmtUtc } from "@/lib/format";
import { loadArtifacts } from "@/lib/snapshot";
import { loadHistory } from "@/lib/history";
import { ManifestProvider } from "@/components/provenance/ManifestContext";
import { BearPreview, Findings, Hero, LandingNav, Method, Questions, Reproduce, Scorecard, TerminalPreview, buildLandingData } from "@/components/landing";

export const dynamic = "force-dynamic";

/**
 * "/" - the landing page, laid out as the front pages of a research report. Server component: it
 * reads the same artifacts as the terminal. With no snapshot, sections that need data are omitted
 * or render their empty states.
 */
export default async function LandingPage() {
  const [{ snapshot, manifest }, history] = await Promise.all([loadArtifacts(), loadHistory()]);
  const data = snapshot ? buildLandingData(snapshot, manifest) : null;
  // Hourly scheduler races: median cross-VM headroom per run (artifacts/history/summary.json).
  const headroomHistory = (history.summary?.bench.series.headroom_bps_cross_vm?.points ?? [])
    .map((p) => p[1])
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));

  return (
    <ManifestProvider manifest={manifest}>
      <LandingNav />
      <main>
        <Hero data={data} headroomHistory={headroomHistory} />
        {data ? <Findings data={data} /> : null}
        <Questions data={data} />
        <Method data={data} />
        {data ? <Scorecard data={data} /> : null}
        {data ? <BearPreview data={data} /> : null}
        <TerminalPreview data={data} />
        <Reproduce data={data} />
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-none flex-wrap items-center justify-between gap-x-8 gap-y-2 px-6 lg:px-[5vw] py-8 text-[13px] text-dim">
          <span>Valuo, for the NEAR Hackathon investment thesis track. Not investment advice: a reproducible model with labelled assumptions.</span>
          <span className="flex flex-wrap items-center gap-x-5 gap-y-1">
            <span className="tnum">{data ? `Block ${fmtInt(data.chain.block)}, ${fmtUtc(data.generatedAtUtc)}` : "No snapshot loaded"}</span>
            <Link href="/terminal" className="text-accent underline-offset-4 hover:underline">
              Open the terminal
            </Link>
          </span>
        </div>
      </footer>
    </ManifestProvider>
  );
}
