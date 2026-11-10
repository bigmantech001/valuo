import { fmtNear, fmtNum, fmtPct, fmtUsdCompact } from "@/lib/format";
import { extractSupplyInputs } from "@/lib/supplyClient";
import { Stat } from "@/components/ui/Stat";
import { MethodNote, SectionIntro, StatGrid } from "@/components/ui/Section";
import { AgentScaleCalculator } from "@/components/tab3/AgentScaleCalculator";
import { BreakevenPanel } from "@/components/tab3/BreakevenPanel";
import { ChainSignaturesPanel } from "@/components/tab3/ChainSignaturesPanel";
import { InputsPanel } from "@/components/tab3/InputsPanel";
import { IssuanceCard } from "@/components/tab3/IssuanceCard";
import { validatePort } from "@/components/tab3/portCheck";
import { REF_DEXS_VOLUME, REF_HOLDERS_REVENUE, refBlock } from "@/components/tab3/provenanceRefs";
import { RegimeLab } from "@/components/tab3/RegimeLab";
import { SinkAudit } from "@/components/tab3/SinkAudit";
import { ValidatorBudget } from "@/components/tab3/ValidatorBudget";
import type { TabProps } from "./types";

function finite(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

const times = (v: number) => `${fmtNum(v, { decimals: 1 })}×`;

/**
 * Tab 3: token supply physics and the NEP state-lock sink.
 * Server component: extracts the model inputs from `supply_physics.inputs`, verifies the TS port
 * against the stored Python trajectories, and lays the chapter out top to bottom: finding, key
 * figures, regime lab (client), issuance and breakeven, storage-lock audit, agent-scale calculator,
 * validator budget, then the model inputs. Every figure is read from the snapshot; nothing is defaulted.
 */
export function Tab3Supply({ snapshot }: TabProps) {
  const sp = snapshot?.supply_physics ?? null;
  const rpc = snapshot?.near_rpc ?? null;
  const fx = snapshot?.intents_forensics ?? null;

  const { inputs, missing } = extractSupplyInputs(sp, rpc);
  const portChecks = inputs ? validatePort(sp, inputs) : [];
  const regimeLabels: Record<string, string> = {};
  for (const r of sp?.regimes ?? []) regimeLabels[r.key] = r.label;

  const vol30 = fx?.volume?.["30d"] ?? null;
  const currentDailyVolumeUsd = typeof vol30 === "number" && Number.isFinite(vol30) ? vol30 / 30 : null;
  const intents = rpc?.tracked_sinks?.find((s) => s.account_id === "intents.near") ?? null;

  const issuance = sp?.current_daily_issuance_near ?? null;
  const nominalDaily = rpc?.gross_daily_issuance_near ?? null;
  const sinks = sp?.current_daily_sinks_near ?? null;
  const sinksTotal = sinks && finite(sinks.total) ? sinks.total : null;
  const net = sp?.current_net_float_change_near_day ?? (finite(issuance) && finite(sinksTotal) ? issuance - sinksTotal : null);
  const coverage = sp?.sink_coverage_ratio ?? null;
  const epoch = rpc?.epoch_issuance?.epoch_start_height ?? null;
  const beSq = sp?.breakeven_daily_volume_usd?.status_quo ?? null;
  const beGlide = sp?.breakeven_daily_volume_usd?.svrn_glidepath ?? null;
  const multSq = finite(beSq) && finite(currentDailyVolumeUsd) && currentDailyVolumeUsd > 0 ? beSq / currentDailyVolumeUsd : null;
  const multGlide = finite(beGlide) && finite(currentDailyVolumeUsd) && currentDailyVolumeUsd > 0 ? beGlide / currentDailyVolumeUsd : null;
  const issuanceGap = finite(issuance) && finite(nominalDaily) && nominalDaily !== 0 ? issuance / nominalDaily - 1 : null;
  const kbPerNear = finite(rpc?.storage_near_per_kb) && rpc!.storage_near_per_kb > 0 ? 1 / rpc!.storage_near_per_kb : null;

  let headline = "Daily issuance against buybacks, gas burn and storage lock";
  if (finite(coverage) && finite(issuance) && finite(net)) {
    headline =
      net > 0
        ? `Sinks offset ${fmtPct(coverage, { decimals: 1 })} of the ${fmtNear(issuance)} minted per day; the float grows by about ${fmtNear(net)} a day`
        : `Sinks absorb ${fmtPct(coverage, { decimals: 1 })} of the ${fmtNear(issuance)} minted per day; the float shrinks by about ${fmtNear(-net)} a day`;
  }

  return (
    <div className="space-y-12">
      <div className="space-y-6">
        <SectionIntro eyebrow="Supply physics" title={headline}>
          <p>
            Four flows set the change in circulating NEAR. Epoch issuance adds supply; open-market buybacks funded by NEAR Intents fees, gas burn, and storage staking
            {finite(kbPerNear) ? ` (1 NEAR locked per ${fmtNum(kbPerNear, { decimals: 0 })} KB of contract state)` : ""} remove it. Each flow is measured from mainnet RPC or DefiLlama, then projected over{" "}
            {finite(inputs?.horizon_months) ? `${inputs!.horizon_months} months` : "the model horizon"} under the live {fmtPct(rpc?.max_inflation_rate, { decimals: 2 })} cap and the proposed SVRN glidepath to{" "}
            {fmtPct(rpc?.svrn_target_inflation_used, { decimals: 2 })}.
          </p>
        </SectionIntro>

        <StatGrid cols={4}>
          <Stat
            label="Measured issuance"
            value={issuance}
            format={(v) => fmtNear(v)}
            unit="per day"
            delta={finite(issuanceGap) ? { value: fmtPct(issuanceGap, { decimals: 2, signed: true }), label: `vs nominal ${fmtNear(nominalDaily)}` } : undefined}
            provenance={refBlock(epoch)}
          />
          <Stat
            label="Total sinks"
            value={sinksTotal}
            format={(v) => fmtNear(v)}
            unit="per day"
            hint={finite(coverage) ? `${fmtPct(coverage, { decimals: 1 })} of issuance; buybacks are ${sinks && finite(sinksTotal) && sinksTotal > 0 ? fmtPct(sinks.buyback / sinksTotal, { decimals: 0 }) : "n/a"} of it` : undefined}
            provenance={REF_HOLDERS_REVENUE}
          />
          <Stat
            label="Net float change"
            value={net}
            format={(v) => fmtNear(v, { signed: true })}
            unit="per day"
            tone={finite(net) ? (net > 0 ? "crimson" : "emerald") : "neutral"}
            hint={finite(net) ? (net > 0 ? "Issuance minus sinks; the float is growing" : "Issuance minus sinks; the float is shrinking") : undefined}
          />
          <Stat
            label="Breakeven volume, status quo"
            value={beSq}
            format={(v) => fmtUsdCompact(v)}
            unit="per day"
            delta={finite(multSq) ? { value: times(multSq), tone: multSq <= 1 ? "emerald" : "crimson", label: `today's ${fmtUsdCompact(currentDailyVolumeUsd)}/day` } : undefined}
            hint={finite(beGlide) ? `SVRN glidepath: ${fmtUsdCompact(beGlide)}/day${finite(multGlide) ? `, ${times(multGlide)} today` : ""}` : undefined}
            provenance={REF_DEXS_VOLUME}
          />
        </StatGrid>
      </div>

      <RegimeLab inputs={inputs} missing={missing} regimeLabels={regimeLabels} portChecks={portChecks} epochStartHeight={epoch} currentDailyVolumeUsd={currentDailyVolumeUsd} />

      <div className="grid grid-cols-[minmax(0,1fr)] gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <IssuanceCard rpc={rpc} />
        <BreakevenPanel sp={sp} fx={fx} rpc={rpc} regimeLabels={regimeLabels} />
      </div>

      <SinkAudit rpc={rpc} sp={sp} />

      <ChainSignaturesPanel
        cs={snapshot?.chain_signatures ?? null}
        dailyIssuanceNear={sp?.current_daily_issuance_near ?? null}
        networkGasBurnNearPerDay={sinks && finite(sinks.gas_burn) ? sinks.gas_burn : null}
      />

      <AgentScaleCalculator
        storageNearPerKb={rpc?.storage_near_per_kb ?? null}
        kbAssumption={sp?.inputs?.kb_per_agent_vault ?? null}
        dailyIssuanceNear={sp?.current_daily_issuance_near ?? null}
        totalSupplyNear={sp?.inputs?.total_supply_near?.value ?? rpc?.total_supply_near ?? null}
        intentsLockedNear={intents?.storage_locked_near ?? null}
        rows={Array.isArray(sp?.agent_scale_table) ? sp.agent_scale_table : []}
      />

      <ValidatorBudget rpc={rpc} rows={sp?.staking_yield_table ?? null} regimeLabels={regimeLabels} />

      <InputsPanel sp={sp} rpc={rpc} />

      <MethodNote summary="Method and sources for the headline figures">
        <p>
          Measured issuance is <code>supply_physics.current_daily_issuance_near</code>, the epoch-boundary supply jump annualised by measured epoch time and divided by 365.25. Nominal is{" "}
          <code>near_rpc.gross_daily_issuance_near</code> = <code>max_inflation_rate × total_supply / 365.25</code>.
        </p>
        <p>
          Total sinks is <code>supply_physics.current_daily_sinks_near.total</code> = buyback + gas burn + state-lock growth. Coverage is <code>supply_physics.sink_coverage_ratio</code> = sinks / issuance; net
          float change is <code>supply_physics.current_net_float_change_near_day</code> = issuance − sinks.
        </p>
        <p>
          Breakeven volume is <code>supply_physics.breakeven_daily_volume_usd</code> per regime. Today&apos;s volume is <code>intents_forensics.volume.30d / 30</code>
          {finite(vol30) ? ` (${fmtUsdCompact(vol30)} trailing 30 days)` : ""}.
        </p>
      </MethodNote>
    </div>
  );
}
