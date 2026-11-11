import type { ReactNode } from "react";

/** One row of the hero's key-figures panel. Shared by the server panel and the live-race row. */
export function Figure({ label, value, unit, note, source, spark }: { label: string; value: ReactNode; unit?: string; note?: ReactNode; source?: ReactNode; spark?: ReactNode }) {
  return (
    <div className="grid grid-cols-1 items-baseline gap-x-6 gap-y-1 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:px-6">
      <dt className="text-[14px] text-muted">
        {label}
        {source ? <span className="ml-2.5 align-baseline">{source}</span> : null}
      </dt>
      <dd className="sm:row-span-2 sm:self-center sm:text-right">
        <span className="tnum text-[22px] font-medium leading-none tracking-tight text-ink">{value}</span>
        {unit ? <span className="ml-1.5 text-[13px] text-muted">{unit}</span> : null}
      </dd>
      <dd className="min-w-0 text-[13px] leading-snug text-dim">{note}</dd>
      {spark ? <dd className="min-w-0 pt-1.5 sm:col-span-2">{spark}</dd> : null}
    </div>
  );
}
