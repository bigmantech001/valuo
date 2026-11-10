import Link from "next/link";
import { fmtInt } from "@/lib/format";
import { artifactPaths, computeIntegrity, loadArtifacts } from "@/lib/snapshot";
import { ManifestProvider } from "@/components/provenance/ManifestContext";
import { ProvenanceBar } from "@/components/provenance/ProvenanceBar";
import { Tab1Thesis, Tab2Execution, Tab3Supply, Tab4Sotp, Tab5BearCase } from "@/components/tabs";
import { readWorkflowSchedules, Tab6History } from "@/components/tab6";
import { loadHistory } from "@/lib/history";
import { EmptyState } from "@/components/ui/EmptyState";
import { Tabs } from "@/components/ui/Tabs";

export const dynamic = "force-dynamic";

/** Small count chip for the sidebar (like a notification count, but for evidence). */
function NavCount({ children, tone = "neutral", title }: { children: React.ReactNode; tone?: "neutral" | "crimson"; title?: string }) {
  return (
    <span title={title} className={tone === "crimson" ? "tnum rounded-full bg-crimson/10 px-2 py-0.5 text-[11.5px] text-crimson" : "tnum rounded-full bg-surface-2 px-2 py-0.5 text-[11.5px] text-muted"}>
      {children}
    </span>
  );
}

const railLink = "flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] text-muted transition-colors hover:bg-surface-2/60 hover:text-ink";

/**
 * /terminal - the six-tab Investment Committee terminal (tab 6 reads artifacts/history/summary.json).
 * Server component: loads artifacts/latest_snapshot.json + manifest.json, renders the
 * provenance bar and the five tabs. With no snapshot it renders the reproduction instructions.
 * The marketing/landing page lives at "/" and links here via "Launch app".
 */
export default async function TerminalPage() {
  const [{ snapshot, manifest }, history, schedules] = await Promise.all([loadArtifacts(), loadHistory(), readWorkflowSchedules()]);
  const integrity = snapshot ? await computeIntegrity(manifest) : null;
  const paths = artifactPaths();

  const barSnapshot = snapshot
    ? { generated_at_utc: snapshot.generated_at_utc, near_rpc: snapshot.near_rpc, schema_version: snapshot.schema_version, valuo_version: snapshot.valuo_version, seed: snapshot.seed }
    : null;

  return (
    <ManifestProvider manifest={manifest}>
      <ProvenanceBar snapshot={barSnapshot} manifest={manifest} initialIntegrity={integrity} />
      <main className="mx-auto w-full max-w-none px-6 lg:px-[5vw] pb-24 pt-6">
        {/* Page-level heading for screen-reader navigation; the visible brand lives in the provenance bar. */}
        <h1 className="sr-only">Valuo NEAR Investment Committee terminal</h1>
        {snapshot ? (
          <Tabs
            variant="sidebar"
            railTitle="IC terminal"
            railFooter={
              <div className="flex flex-col">
                <a href="/api/snapshot?format=memo" download className={railLink}>
                  Download IC memo
                </a>
                <a href="/api/snapshot?format=json" download className={railLink}>
                  Snapshot JSON
                </a>
                <Link href="/" className={railLink}>
                  Overview
                </Link>
              </div>
            }
            tabs={[
              { id: "thesis", kicker: "01", label: "Thesis & evidence", content: <Tab1Thesis snapshot={snapshot} manifest={manifest} /> },
              { id: "execution", kicker: "02", label: "Execution alpha", content: <Tab2Execution snapshot={snapshot} manifest={manifest} /> },
              { id: "supply", kicker: "03", label: "Supply physics", content: <Tab3Supply snapshot={snapshot} manifest={manifest} /> },
              { id: "sotp", kicker: "04", label: "SOTP & Monte Carlo", content: <Tab4Sotp snapshot={snapshot} manifest={manifest} /> },
              { id: "bear", kicker: "05", label: "Bear case", badge: typeof snapshot.bear_case?.triggers_breached === "number" ? <NavCount tone={snapshot.bear_case.triggers_breached > 0 ? "crimson" : "neutral"} title="Falsification triggers breached / graded">{snapshot.bear_case.triggers_breached}/{snapshot.bear_case.triggers_evaluated ?? "?"}</NavCount> : undefined, content: <Tab5BearCase snapshot={snapshot} manifest={manifest} /> },
              { id: "history", kicker: "06", label: "History", badge: history.summary ? <NavCount title="Canonical daily snapshots recorded">{history.summary.snapshots.n_records}</NavCount> : undefined, content: <Tab6History history={history} snapshot={snapshot} schedules={schedules} /> },
            ]}
          />
        ) : (
          <EmptyState
            title="No snapshot yet. Run the pipeline to generate one."
            commands={["cd Valuo", "make reproduce        # or: cd quant && uv run python -m valuo.reproduce", "make dev              # then reload this page"]}
          >
            <p>
              The terminal shows only numbers that exist in <code className="font-mono text-[12.5px] text-ink">artifacts/latest_snapshot.json</code> and are hashed in{" "}
              <code className="font-mono text-[12.5px] text-ink">artifacts/manifest.json</code>. Nothing is mocked, so without those files there is nothing to show.
            </p>
            <p className="mt-2">
              Looked for <code className="break-all font-mono text-[12.5px] text-ink">{paths.snapshot}</code>. If your artifacts live elsewhere, set <code className="font-mono text-[12.5px] text-ink">VALUO_ARTIFACTS_DIR</code> in the process environment or the repo-root{" "}
              <code className="font-mono text-[12.5px] text-ink">.env</code>. With <code className="font-mono text-[12.5px] text-ink">VALUO_ALLOW_REPRODUCE=1</code> the bar above also offers a button that re-runs the pipeline from the browser.
            </p>
          </EmptyState>
        )}
      </main>
      <footer className="border-t border-border bg-surface">
        <div className="mx-auto flex max-w-none flex-wrap items-baseline justify-between gap-x-8 gap-y-2 px-6 lg:px-[5vw] py-6 text-[13px] text-muted">
          <p className="max-w-xl">
            <Link href="/" className="font-serif text-[15px] text-ink hover:text-accent">
              Valuo
            </Link>
            <span className="ml-2">Judged on evidence, not conviction: every figure traces to a SHA-256-hashed raw payload, and every assumption is labeled.</span>
          </p>
          <p className="tnum text-dim">
            {snapshot
              ? [`Schema ${snapshot.schema_version}`, `Valuo ${snapshot.valuo_version}`, `seed ${snapshot.seed ?? "n/a"}`, `run time ${fmtInt(snapshot.runtime_s)} s`, manifest ? `${fmtInt(manifest.records.length)} raw records` : null]
                  .filter(Boolean)
                  .join(" · ")
              : "No snapshot loaded"}
          </p>
        </div>
      </footer>
    </ManifestProvider>
  );
}
