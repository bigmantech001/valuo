"use client";

import { useMemo, useState } from "react";
import { fmtCompact, fmtInt, fmtNear, fmtNum, fmtPct, NA } from "@/lib/format";
import { agentLockNear } from "@/lib/supplyClient";
import type { AgentScaleRow, Assumption } from "@/lib/types";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { Card } from "@/components/ui/Card";
import { MethodNote } from "@/components/ui/Section";
import { Slider } from "@/components/ui/Slider";
import { Table, type Column } from "@/components/ui/Table";
import { DefinitionList } from "./DefinitionList";
import { REF_PROTOCOL_CONFIG, refViewAccount } from "./provenanceRefs";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

export interface AgentScaleCalculatorProps {
  /** near_rpc.storage_near_per_kb (0.01 at 1e19 yocto/byte) */
  storageNearPerKb: number | null;
  /** supply_physics.inputs.kb_per_agent_vault */
  kbAssumption: Assumption | null;
  /** supply_physics.current_daily_issuance_near */
  dailyIssuanceNear: number | null;
  /** supply_physics.inputs.total_supply_near */
  totalSupplyNear: number | null;
  /** intents.near storage_locked_near today, for scale */
  intentsLockedNear: number | null;
  rows: AgentScaleRow[];
}

const LOG_MIN = 5; // 1e5 agents
const LOG_MAX = 7; // 1e7 agents

/**
 * AI-agent scale calculator: `locked = agents x kb_per_agent x storage_near_per_kb`. Agents on a
 * log slider (1e5..1e7), KB per agent over the labelled assumption's range. The snapshot's own
 * grid (`supply_physics.agent_scale_table`) is listed in the method note for the fixed reference points.
 */
export function AgentScaleCalculator({ storageNearPerKb, kbAssumption, dailyIssuanceNear, totalSupplyNear, intentsLockedNear, rows }: AgentScaleCalculatorProps) {
  const kbMin = finite(kbAssumption?.low) ? kbAssumption!.low : 5;
  const kbMax = finite(kbAssumption?.high) ? kbAssumption!.high : 50;
  const [logAgents, setLogAgents] = useState<number>(6);
  const [kb, setKb] = useState<number>(finite(kbAssumption?.value) ? kbAssumption!.value : kbMin);

  const agents = useMemo(() => Math.round(10 ** logAgents), [logAgents]);
  const locked = finite(storageNearPerKb) ? agentLockNear(agents, kb, storageNearPerKb) : null;
  const daysAbsorbed = finite(locked) && finite(dailyIssuanceNear) && dailyIssuanceNear > 0 ? locked / dailyIssuanceNear : null;
  const share = finite(locked) && finite(totalSupplyNear) && totalSupplyNear > 0 ? locked / totalSupplyNear : null;
  const vsIntents = finite(locked) && finite(intentsLockedNear) && intentsLockedNear > 0 ? locked / intentsLockedNear : null;
  const intentsRef = refViewAccount("intents.near");

  const columns: Column<AgentScaleRow>[] = [
    { key: "agents", header: "Agents", numeric: true, render: (r) => fmtCompact(r.agents) },
    { key: "kb", header: "KB per agent", numeric: true, render: (r) => `${fmtNum(r.kb_per_agent, { decimals: 0 })}${r.is_default_kb ? " (default)" : ""}` },
    { key: "locked", header: "NEAR locked", numeric: true, render: (r) => fmtNear(r.locked_near) },
    { key: "days", header: "Days of issuance", numeric: true, render: (r) => (finite(r.days_of_issuance_absorbed) ? fmtNum(r.days_of_issuance_absorbed, { decimals: 2 }) : NA) },
    { key: "share", header: "Share of supply", numeric: true, render: (r) => (finite(r.share_of_supply) ? fmtPct(r.share_of_supply, { decimals: 4 }) : NA) },
  ];

  return (
    <Card
      title="What agent vaults would lock"
      subtitle="If each AI agent holds its own account or sub-vault, its state pays the same storage stake. The size per agent is an assumption, not a measurement."
      actions={<ProvenanceBadge source={REF_PROTOCOL_CONFIG.source} name={REF_PROTOCOL_CONFIG.name} label="Storage price" />}
    >
      <div className="grid grid-cols-[minmax(0,1fr)] gap-x-10 gap-y-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Slider label="Agent accounts" value={logAgents} min={LOG_MIN} max={LOG_MAX} step={0.01} onChange={setLogAgents} format={(v) => fmtCompact(Math.round(10 ** v))} description="Log scale" />
          <Slider
            label="State per agent"
            value={kb}
            min={kbMin}
            max={kbMax}
            step={1}
            onChange={setKb}
            format={(v) => `${fmtNum(v, { decimals: 0 })} KB`}
            marker={finite(kbAssumption?.value) ? { value: kbAssumption!.value, label: "Default", tone: "amber" } : null}
            description="Range from the assumption registry"
          />
        </div>
        <div aria-live="polite">
          <DefinitionList
            rows={[
              { key: "locked", term: "NEAR locked", note: finite(locked) ? `${fmtInt(agents)} agents × ${fmtNum(kb, { decimals: 0 })} KB` : "Storage price missing from the snapshot", value: fmtNear(locked) },
              { key: "days", term: "Days of issuance absorbed", note: finite(dailyIssuanceNear) ? `At ${fmtNear(dailyIssuanceNear)} minted per day` : undefined, value: fmtNum(daysAbsorbed, { decimals: 2 }) },
              { key: "share", term: "Share of total supply", value: fmtPct(share, { decimals: 4 }) },
              { key: "intents", term: "Relative to intents.near today", note: finite(intentsLockedNear) ? `${fmtNear(intentsLockedNear)} locked` : undefined, value: finite(vsIntents) ? `${fmtNum(vsIntents, { decimals: 2 })}×` : NA },
            ]}
          />
          <p className="mt-3 text-[13px] leading-relaxed text-muted">
            This is a one-time lock, not a recurring sink: it absorbs issuance once, when the state is created.
          </p>
        </div>
      </div>

      <MethodNote className="mt-6" summary="Method and the pipeline's fixed grid">
        <p>
          Locked = <code>agents × kb_per_agent × storage_near_per_kb</code>
          {finite(storageNearPerKb) ? ` (${fmtNum(storageNearPerKb, { decimals: 2 })} NEAR per KB)` : " (storage price not available)"}. KB per agent is <code>supply_physics.inputs.kb_per_agent_vault</code>:{" "}
          {kbAssumption?.justification ?? "assumption row missing from the snapshot"}
        </p>
        <div>
          Scale reference: <ProvenanceBadge source={intentsRef.source} name={intentsRef.name} label="intents.near view_account" />. Grid from <code>supply_physics.agent_scale_table</code>:
        </div>
        <Table<AgentScaleRow> columns={columns} rows={Array.isArray(rows) ? rows : []} rowKey={(r) => `${r.agents}-${r.kb_per_agent}`} emptyText="No agent scale grid in this snapshot" maxHeight="16rem" />
      </MethodNote>
    </Card>
  );
}
