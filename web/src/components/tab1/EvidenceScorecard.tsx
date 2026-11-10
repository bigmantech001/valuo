import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { EvidenceBadge, evidenceStatusLabel } from "@/components/ui";
import { cn } from "@/lib/cn";
import { fmtInt } from "@/lib/format";
import { buildManifestIndex } from "@/lib/manifestIndex";
import type { EvidenceStatus, Manifest, Snapshot } from "@/lib/types";
import { resolveRefs } from "./derive";
import { Panel, SubHead } from "./parts";
import { PathHint } from "./PathHint";

const STATUS_ORDER: readonly EvidenceStatus[] = ["VERIFIED_ON_CHAIN", "VERIFIED_LIVE_API", "DERIVED", "ASSUMPTION", "NOT_SUPPORTED"];

/** Display only: the pipeline writes "A -> B"; the page shows "A → B". The stored string is unchanged. */
function arrows(t: string): string {
  return t.replace(/\s*->\s*/g, " → ");
}

function gradeLower(s: EvidenceStatus): string {
  const l = evidenceStatusLabel(s);
  return l.charAt(0).toLowerCase() + l.slice(1);
}

function confidenceText(c: string): string {
  const t = (c ?? "").trim();
  return t ? `${t.charAt(0).toUpperCase()}${t.slice(1)} confidence` : "Confidence n/a";
}

/**
 * The evidence scorecard exactly as `reproduce.py` graded it: grade, claim, the value string, the
 * pipeline's confidence and the source. Where the source string names `source/name` pairs that
 * exist in the manifest, a provenance link is attached; the full source string (hashes, block
 * heights) sits behind the "detail" marker.
 */
export function EvidenceScorecard({ snapshot, manifest, className }: { snapshot: Snapshot; manifest: Manifest | null; className?: string }) {
  const index = buildManifestIndex(manifest);
  const claims = snapshot.evidence_scorecard ?? [];

  const counts = new Map<EvidenceStatus, number>();
  for (const c of claims) counts.set(c.status, (counts.get(c.status) ?? 0) + 1);
  const breakdown = STATUS_ORDER.filter((s) => counts.has(s)).map((s) => `${fmtInt(counts.get(s) ?? 0)} ${gradeLower(s)}`);

  return (
    <section id="scorecard" className={cn("space-y-4", className)}>
      <SubHead title="Evidence scorecard">
        {claims.length
          ? `${fmtInt(claims.length)} claims, graded by how each was obtained: ${breakdown.join(", ")}. A claim the data does not support stays on the list, marked.`
          : "The evidence scorecard is empty in this snapshot."}
      </SubHead>
      {claims.length ? (
        <Panel>
          <div className="hidden grid-cols-[11rem_minmax(0,1.25fr)_minmax(0,1fr)_9rem] gap-x-6 border-b border-ink/80 px-5 py-2.5 text-[12.5px] font-medium text-muted lg:grid">
            <span>Grade</span>
            <span>Claim</span>
            <span>Measured value</span>
            <span>Source</span>
          </div>
          <ol className="divide-y divide-border">
            {claims.map((claim, i) => {
              const records = resolveRefs(claim.source ?? "", index);
              return (
                <li key={`${i}-${claim.claim}`} className="grid grid-cols-[minmax(0,1fr)] gap-x-6 gap-y-2 px-5 py-4 lg:grid-cols-[11rem_minmax(0,1.25fr)_minmax(0,1fr)_9rem]">
                  <div>
                    <EvidenceBadge status={claim.status} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[14.5px] leading-snug text-ink">{arrows(claim.claim)}</p>
                    {claim.note ? <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{arrows(claim.note)}</p> : null}
                  </div>
                  <div className="min-w-0">
                    <p className="tnum text-[13.5px] leading-snug text-ink">{arrows(claim.value)}</p>
                    <p className="mt-1 text-[12.5px] text-dim">{confidenceText(claim.confidence)}</p>
                  </div>
                  <div className="flex min-w-0 flex-row flex-wrap items-baseline gap-x-3 gap-y-1 lg:flex-col lg:items-start">
                    {records.map((rec) => (
                      <ProvenanceBadge key={`${rec.source}/${rec.name}`} record={rec} />
                    ))}
                    {claim.source ? <PathHint path={claim.source} label="detail" caption="Source as recorded by the pipeline" /> : null}
                  </div>
                </li>
              );
            })}
          </ol>
        </Panel>
      ) : null}
      <p className="text-[13px] leading-relaxed text-muted">
        Verified on-chain outranks verified via live API, which outranks derived, which outranks assumption. Grades and confidence are written by the pipeline, not by hand.
        {manifest ? ` Source links resolve against manifest.json (${fmtInt(manifest.records.length)} records, ${fmtInt(manifest.failures)} failed).` : " manifest.json is not loaded, so sources show without links."}
      </p>
    </section>
  );
}
