import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { MethodNote } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
import { fmtInt, fmtUsd } from "@/lib/format";
import { buildManifestIndex } from "@/lib/manifestIndex";
import type { Manifest, Snapshot } from "@/lib/types";
import { corridorText, dedupeWarnings, resolveRefs, sourceLabel, splitWarning, stageLabel } from "./derive";
import { Panel, SubHead } from "./parts";

/** "across/quote:eth_usdc_sol_usdc:50000" -> "Across, ETH USDC to SOL USDC, $50,000"; anything else passes through. */
function failedHead(head: string, snapshot: Snapshot): { text: string; humanised: boolean } {
  const m = /^([a-z_]+)\/quote:([a-z0-9_]+):(\d+)$/.exec(head);
  if (!m) return { text: head, humanised: false };
  const corridor = snapshot.execution_bench?.corridors?.find((c) => c.corridor_id === m[2]);
  return { text: `${sourceLabel(m[1])} quote, ${corridor ? corridorText(corridor.label) : m[2]}, ${fmtUsd(Number(m[3]), { decimals: 0 })}`, humanised: true };
}

/**
 * Every warning the pipeline recorded (snapshot.warnings plus the Monte Carlo calibration
 * warnings), followed by the raw fetches that failed. Failures are kept, never substituted: a 4xx
 * from a venue is itself a measurement (e.g. "No liquidity available").
 */
export function Caveats({ snapshot, manifest, className }: { snapshot: Snapshot; manifest: Manifest | null; className?: string }) {
  const index = buildManifestIndex(manifest);
  const warnings = dedupeWarnings(snapshot.warnings, snapshot.sotp?.calibration?.warnings);
  const failed = snapshot.provenance_summary?.failed ?? [];
  const summary = snapshot.provenance_summary;
  const assumptions = (snapshot.assumptions ?? []).filter((a) => a.source === "assumption");

  const corridors = snapshot.execution_bench?.corridors ?? [];
  const humaniseIds = (text: string) => corridors.reduce((t, c) => t.split(c.corridor_id).join(corridorText(c.label)), text);

  const lede =
    warnings.length || failed.length
      ? `The pipeline recorded ${fmtInt(warnings.length)} ${warnings.length === 1 ? "warning" : "warnings"} and ${fmtInt(failed.length)} failed ${failed.length === 1 ? "fetch" : "fetches"} in this run. Read them before quoting any figure above.`
      : "The pipeline recorded no warnings and every raw fetch returned successfully in this run.";

  return (
    <section id="caveats" className={cn("space-y-4", className)}>
      <SubHead title="Caveats">{lede}</SubHead>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="min-w-0">
          <h4 className="mb-2 text-[14px] font-medium text-ink">
            Pipeline warnings <span className="tnum font-normal text-dim">({fmtInt(warnings.length)})</span>
          </h4>
          <Panel>
            {warnings.length ? (
              <ul className="divide-y divide-border">
                {warnings.map((w) => {
                  const { stage, message } = splitWarning(w);
                  return (
                    <li key={w} className="px-4 py-3">
                      <div className="text-[12.5px] text-dim">{stageLabel(stage)}</div>
                      <p className="mt-0.5 text-[13.5px] leading-snug text-ink">{humaniseIds(message)}</p>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="px-4 py-3 text-[13.5px] text-muted">No warnings recorded in this snapshot.</p>
            )}
          </Panel>
        </div>
        <div className="min-w-0">
          <h4 className="mb-2 text-[14px] font-medium text-ink">
            Failed raw fetches <span className="tnum font-normal text-dim">({fmtInt(failed.length)}, recorded, not substituted)</span>
          </h4>
          <Panel>
            {failed.length ? (
              <ul className="divide-y divide-border">
                {failed.map((f) => {
                  const recs = resolveRefs(f, index);
                  const sep = f.indexOf(": ");
                  const head = failedHead(sep > 0 ? f.slice(0, sep) : f, snapshot);
                  const tail = sep > 0 ? f.slice(sep + 2) : null;
                  return (
                    <li key={f} className="px-4 py-3">
                      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                        {head.humanised ? <span className="text-[13.5px] text-ink">{head.text}</span> : <code className="break-all font-mono text-[12px] text-ink">{head.text}</code>}
                        {recs.map((r) => (
                          <ProvenanceBadge key={`${r.source}/${r.name}`} record={r} />
                        ))}
                      </div>
                      {tail ? <p className="mt-0.5 break-words text-[12.5px] leading-snug text-muted">{tail}</p> : null}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="px-4 py-3 text-[13.5px] text-muted">Every raw fetch in this run returned 2xx.</p>
            )}
          </Panel>
        </div>
      </div>
      <p className="max-w-4xl text-[13px] leading-relaxed text-muted">
        {fmtInt(assumptions.length)} inputs are labelled as assumptions, each with a default, a range and a justification; they drive the SOTP tab sliders and are never presented as measured.
        {summary ? ` ${fmtInt(summary.ok)} of ${fmtInt(summary.records)} raw payloads returned successfully across ${fmtInt(Object.keys(summary.sources ?? {}).length)} sources.` : null}
      </p>
      <MethodNote>
        <p>
          Warnings: <code>snapshot.warnings</code> and <code>sotp.calibration.warnings</code>, deduplicated, in pipeline order. Failed fetches: <code>provenance_summary.failed</code>, each named by its manifest record. Assumptions: entries in <code>snapshot.assumptions</code> with <code>source: assumption</code>.
        </p>
      </MethodNote>
    </section>
  );
}
