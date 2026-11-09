import Link from "next/link";
import { fmtInt, fmtUsdCompact } from "@/lib/format";
import { numberWord, type LandingData } from "./landingData";
import { LandingSection, SectionHeader } from "./SectionHeader";

/**
 * The six terminal tabs with one-line descriptions and deep links. Model constants in the copy
 * (path count, clip sizes) are read from the snapshot so the text cannot drift from the run.
 */
export function TerminalPreview({ data }: { data: LandingData | null }) {
  const paths = data ? `${fmtInt(data.sotp.nPaths)}-path` : "seeded";
  const clips = data?.bench?.corridors[0]?.clipsUsd.length ? data.bench.corridors[0].clipsUsd.map((c) => fmtUsdCompact(c, { decimals: 0 })).join(", ") : "three clip sizes";
  const tabs = [
    { id: "thesis", title: "Thesis and evidence", body: "The verdict in numbers, the causal chain from execution spread to valuation multiple, and the graded claims." },
    { id: "execution", title: "Execution and solvers", body: `Run a live quote race against Relay, LI.FI and Across at ${clips}; corridor matrix; caller and solver concentration.` },
    { id: "supply", title: "Supply physics", body: "Issuance under the current cap, the SVRN glidepath or a custom cap, set against measured sinks." },
    { id: "sotp", title: `Valuation and ${paths} Monte Carlo`, body: "Adjust growth, take rate, confidential share and buyback ratio; fan chart, engine breakdown, peer comparables." },
    { id: "bear", title: "Bear case", body: "Stress scenarios, their drawdown on fair value, and the early-warning triggers to check each week." },
    { id: "history", title: "History", body: "Time series of cross-VM headroom, trigger status and valuation, built from the scheduled daily and hourly runs." },
  ];

  return (
    <LandingSection id="terminal">
      <SectionHeader
        number="6"
        eyebrow="The terminal"
        title={`${numberWord(tabs.length)} tabs, every figure traced to a payload`}
        lede="Each number in the terminal links to the raw response it was read from, with its SHA-256 hash and fetch time. The header checks the snapshot's block against the live chain head."
        aside={
          <Link href="/terminal" className="inline-flex items-center rounded-md bg-ink px-4 py-2 text-[14.5px] font-medium text-surface transition-colors hover:bg-ink/85">
            Open the terminal
          </Link>
        }
      />

      <ol className="mt-12 border-t border-border-strong">
        {tabs.map((t, i) => (
          <li key={t.id} className="border-b border-border">
            <Link
              href={`/terminal#${t.id}`}
              className="group grid items-baseline gap-x-8 gap-y-1 py-5 transition-colors sm:grid-cols-[2.5rem_minmax(0,18rem)_minmax(0,1fr)]"
            >
              <span className="tnum font-serif text-[18px] text-dim">{String(i + 1).padStart(2, "0")}</span>
              <span className="font-serif text-[20px] font-medium text-ink group-hover:text-accent">{t.title}</span>
              <span className="text-[15px] leading-relaxed text-muted">{t.body}</span>
            </Link>
          </li>
        ))}
      </ol>
    </LandingSection>
  );
}
