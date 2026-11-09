import { EvidenceBadge, evidenceStatusLabel } from "@/components/ui/Badge";
import type { EvidenceStatus } from "@/lib/types";
import type { LandingData } from "./landingData";
import { LandingSection, SectionHeader, TextLink } from "./SectionHeader";

const ORDER: EvidenceStatus[] = ["VERIFIED_ON_CHAIN", "VERIFIED_LIVE_API", "DERIVED", "ASSUMPTION", "NOT_SUPPORTED"];

/** The evidence scorecard exactly as graded by the pipeline, as a report table. */
export function Scorecard({ data }: { data: LandingData }) {
  const counts = data.scorecard.reduce<Partial<Record<EvidenceStatus, number>>>((acc, c) => {
    acc[c.status] = (acc[c.status] ?? 0) + 1;
    return acc;
  }, {});
  const tally = ORDER.filter((s) => counts[s]).map((s) => `${counts[s]} ${evidenceStatusLabel(s).charAt(0).toLowerCase()}${evidenceStatusLabel(s).slice(1)}`);
  const notSupported = counts.NOT_SUPPORTED ?? 0;

  return (
    <LandingSection id="scorecard">
      <SectionHeader
        number="4"
        eyebrow="Evidence scorecard"
        title="Each claim graded by how it was obtained"
        lede={
          <>
            The pipeline grades its own claims: on-chain evidence ranks above a live API, which ranks above a derived figure, which ranks above an assumption. This run:{" "}
            {tally.join(", ")}.{" "}
            {notSupported
              ? `${notSupported === 1 ? "One claim the data contradicts is" : `${notSupported} claims the data contradicts are`} marked not supported rather than dropped.`
              : "No claim was contradicted by the data in this run."}
          </>
        }
      />

      <div className="mt-12 overflow-x-auto">
        <table className="w-full min-w-[46rem] text-[14px]">
          <thead>
            <tr className="border-b border-border-strong text-left text-[13px] text-muted">
              <th className="w-[44%] py-2.5 pr-8 font-medium">Claim and caveat</th>
              <th className="w-[11rem] py-2.5 pr-8 font-medium">Grade</th>
              <th className="py-2.5 font-medium">Measured value and source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border align-top">
            {data.scorecard.map((c, i) => (
              <tr key={`${i}-${c.claim}`}>
                <td className="py-5 pr-8 leading-snug text-ink">
                  {c.claim}
                  {c.note ? <div className="mt-2 text-[13px] leading-relaxed text-dim">{c.note}</div> : null}
                </td>
                <td className="py-5 pr-8">
                  <EvidenceBadge status={c.status} />
                  {c.confidence ? <div className="mt-1.5 text-[12.5px] text-dim">{c.confidence.charAt(0).toUpperCase() + c.confidence.slice(1)} confidence</div> : null}
                </td>
                <td className="py-5 leading-snug">
                  <div className="tnum text-ink">{c.value}</div>
                  {c.source ? <div className="mt-2 break-words text-[12.5px] leading-relaxed text-dim">{c.source}</div> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-6">
        <TextLink href="/terminal#thesis">Scorecard with provenance in the terminal</TextLink>
      </div>
    </LandingSection>
  );
}
