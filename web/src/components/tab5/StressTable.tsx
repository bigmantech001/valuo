import { cn } from "@/lib/cn";
import { fmtMonth, fmtPct, fmtUsd, fmtUsdCompact, NA } from "@/lib/format";
import type { BearCase } from "@/lib/types";
import { Card, Table, type Column } from "@/components/ui";
import { buildStressRows, fmtPerturbation, perturbationLabel, prose, type StressRow } from "./bearData";

/** The perturbed inputs of a row in plain words; inputs the engine has no slot for are struck through. */
function WhatChanges({ row }: { row: StressRow }) {
  const entries = Object.entries(row.perturbations);
  if (!entries.length) return <span className="text-dim">Nothing; measured inputs and default assumptions</span>;
  const unapplied = new Set(row.unapplied);
  return (
    <ul className="space-y-0.5">
      {entries.map(([k, v]) => {
        const skipped = unapplied.has(k);
        const reached = row.applied[k];
        return (
          <li
            key={k}
            className={cn("text-[13px] leading-snug", skipped ? "text-dim line-through decoration-dim/60" : "text-ink")}
            title={skipped ? `${k}: the deterministic engine has no input for this key; listed but not applied` : reached && reached !== k ? `${k} → model input ${reached}` : `${k}: applied`}
          >
            <span className="text-muted">{perturbationLabel(k)}</span> <span className="tnum whitespace-nowrap">{fmtPerturbation(k, v)}</span>
          </li>
        );
      })}
      {row.unapplied.length ? (
        <li className="pt-0.5 text-[12px] text-dim" title="perturbation keys the deterministic engine has no input for">
          Struck-through {row.unapplied.length === 1 ? "input is" : "inputs are"} listed but not applied (no engine input)
        </li>
      ) : null}
    </ul>
  );
}

/** Signed change, coloured by sign: the sign is the point of this column. */
function Change({ v, reference }: { v: number | null; reference: boolean }) {
  if (reference) return <span className="text-dim">Base</span>;
  if (v === null) return <span className="text-dim">{NA}</span>;
  const tone = v < 0 ? "text-crimson" : v > 0 ? "text-emerald" : "text-muted";
  return <span className={cn("tnum font-medium", tone)}>{fmtPct(v, { decimals: 1, signed: true })}</span>;
}

function Crossover({ v }: { v: number | null | undefined }) {
  if (v === undefined) return <span className="text-dim" title="crossover month absent from the snapshot: not computed for this row">{NA}</span>;
  return <span className={cn("tnum", v === null ? "text-muted" : "text-ink")}>{fmtMonth(v, { quarter: v !== null })}</span>;
}

/**
 * Stress table: base row, each scenario, the combined-worst row. The value column is the
 * deterministic SOTP at median inputs (the model's `sotp_fdv_p50`), never a Monte Carlo percentile.
 */
export function StressTable({ bear }: { bear: BearCase }) {
  const rows = buildStressRows(bear);
  const hasMc = rows.some((r) => r.mcFdv !== null);
  const hasExMonetary = rows.some((r) => r.fdvExMonetary !== null);
  const nScen = (bear.scenarios ?? []).length;

  const columns: Column<StressRow>[] = [
    {
      key: "scenario",
      header: "Scenario",
      width: "34%",
      render: (r) => (
        <div className="max-w-[28rem]">
          <div className="text-[14px] font-medium leading-snug text-ink">{r.title}</div>
          {r.narrative ? <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{prose(r.narrative)}</p> : null}
          {r.kind === "combined" ? <p className="mt-1 text-[12.5px] leading-relaxed text-muted">Every perturbation applied together; where two scenarios set the same input, the value worse for the thesis wins.</p> : null}
          {r.kind === "base" ? <p className="mt-1 text-[12.5px] leading-relaxed text-muted">The snapshot&apos;s measured inputs and default assumptions. Every change below is measured against this row.</p> : null}
        </div>
      ),
    },
    { key: "changes", header: "What changes", width: "22%", render: (r) => <WhatChanges row={r} /> },
    {
      key: "fdv",
      header: "Value (FDV)",
      title: "Deterministic SOTP at the perturbed inputs; not the Monte Carlo P50",
      numeric: true,
      render: (r) => (
        <div>
          <span className={cn("tnum text-ink", r.kind !== "scenario" && "font-medium")}>{fmtUsdCompact(r.fdv)}</span>
          {hasExMonetary && r.fdvExMonetary !== null ? (
            <div className="tnum mt-0.5 whitespace-nowrap text-[12px] text-dim" title="Value without Engine 3 (gas burn and state-lock demand proxy)">
              {fmtUsdCompact(r.fdvExMonetary)} ex-monetary
            </div>
          ) : null}
        </div>
      ),
    },
    { key: "drawdown", header: "Change vs base", title: "Scenario value / base value − 1", numeric: true, render: (r) => <Change v={r.drawdown} reference={r.kind === "base"} /> },
    ...(hasMc
      ? [
          {
            key: "mc",
            header: "Monte Carlo median",
            title: "Seeded Monte Carlo median at the perturbed inputs, when computed",
            numeric: true,
            render: (r: StressRow) => (
              <div>
                <span className="tnum text-ink">{fmtUsdCompact(r.mcFdv)}</span>
                {r.kind !== "base" ? (
                  <div className="text-[12px]">
                    <Change v={r.mcDrawdown} reference={false} />
                  </div>
                ) : null}
              </div>
            ),
          } satisfies Column<StressRow>,
        ]
      : []),
    {
      key: "price",
      header: "Implied price",
      title: "Value / NEAR supply at the horizon; its change differs from the value change only when a scenario changes horizon supply",
      numeric: true,
      render: (r) => (
        <div>
          <span className="tnum text-ink">{fmtUsd(r.price, { decimals: 3 })}</span>
          {r.kind !== "base" && r.priceDrawdown !== null ? (
            <div className="mt-0.5 text-[12px]">
              <Change v={r.priceDrawdown} reference={false} />
            </div>
          ) : null}
        </div>
      ),
    },
    { key: "crossover", header: "Supply crossover", title: "First month in which issuance is at or below sinks; none = not within the 36-month horizon", numeric: true, render: (r) => <Crossover v={r.crossover} /> },
  ];

  return (
    <Card
      title={`${nScen} stress scenarios and the combined worst case`}
      subtitle="Each row re-prices the same deterministic valuation with the inputs in the second column changed."
      padded={false}
    >
      <Table<StressRow>
        columns={columns}
        rows={rows}
        rowKey={(r) => r.key}
        dense={false}
        stickyHeader={false}
        rowClassName={(r) => (r.kind === "combined" ? "bg-surface-2/60" : undefined)}
        emptyText="No stress scenarios in this snapshot"
      />
    </Card>
  );
}
