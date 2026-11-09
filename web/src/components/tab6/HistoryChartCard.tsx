import type { ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { fmtUtc } from "@/lib/format";
import { fmtSpan, plural, spanMs } from "./derive";
import { TimeChart, type TimeChartProps } from "./TimeChart";

export interface RunCount {
  n: number;
  first: string | null;
  last: string | null;
  /** "run" / "race" */
  unit: string;
  /** "per day" / "per hour" from the workflow schedule; null when it could not be read */
  cadence: string | null;
  /** "daily job" / "hourly job" */
  job: string;
}

/** The plain sample-size line under each chart; with one run it says so instead of implying a trend. */
export function RunNote({ runs }: { runs: RunCount }) {
  const { n, unit, cadence, job } = runs;
  const adds = cadence ? `the ${job} adds one ${cadence}` : `the ${job} adds more once it runs`;
  if (n === 0) return <>No {unit}s recorded yet; {adds}.</>;
  if (n === 1) return <>1 {unit} recorded so far ({fmtUtc(runs.first)}); {adds}.</>;
  return (
    <>
      {plural(n, unit)} from {fmtUtc(runs.first)} to {fmtUtc(runs.last)} ({fmtSpan(spanMs(runs.first, runs.last))}); {adds}.
    </>
  );
}

/** Card with a TimeChart, or an explicit n/a line when the series has no measured value. */
export function HistoryChartCard({ kicker, title, subtitle, chart, runs, measured, missingReason, footnote }: {
  kicker: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  chart: TimeChartProps;
  runs: RunCount;
  /** number of non-null observations across the plotted series */
  measured: number;
  missingReason: string;
  footnote?: ReactNode;
}) {
  return (
    <Card
      kicker={kicker}
      title={title}
      subtitle={subtitle}
      footer={
        <>
          <RunNote runs={runs} />
          {footnote ? <> {footnote}</> : null}
        </>
      }
    >
      {measured > 0 ? (
        <TimeChart {...chart} />
      ) : (
        <p className="py-10 text-center text-[13.5px] text-muted">
          <span className="text-dim">n/a</span>: {missingReason}
        </p>
      )}
    </Card>
  );
}
