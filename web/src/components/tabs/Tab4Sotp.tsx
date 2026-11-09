import { CalibrationPanel, REGIME_NAME, EngineWaterfall, McFanCharts, PeerCompsTable, PercentileTable, RelativeValue, SensitivityGrid, SotpSliders, VerdictStrip, WhatYouHaveToBelieve, type RegimeOption } from "@/components/tab4";
import { Card } from "@/components/ui";
import { fmtNear, fmtPct } from "@/lib/format";
import { verifyPort, type SotpSnapshotSlice } from "@/lib/quantClient";
import { REGIME_KEYS } from "@/lib/types";
import type { TabProps } from "./types";

/**
 * Tab 4: what you have to believe (one-at-a-time tornado), slider-driven deterministic SOTP, Monte Carlo fan charts and percentiles, engine waterfall,
 * relative value (peer multiples, cross-check band, security budget; legacy peer comps when absent), the 5 x 5 sensitivity heatmap and the calibration panel. Server component; only the
 * slider panel is a client component and it receives the minimal snapshot slice the model reads.
 */
export function Tab4Sotp({ snapshot, manifest }: TabProps) {
  const sotp = snapshot.sotp;
  if (!sotp) {
    return (
      <Card title="Sum-of-the-parts valuation">
        <p className="text-[13.5px] text-muted">
          Not available: the valuation stage did not run because a required live input was missing (see the snapshot warnings). Re-run <code className="font-mono text-[12px]">make reproduce</code>.
        </p>
      </Card>
    );
  }

  const slice: SotpSnapshotSlice = {
    sotp,
    near_rpc: { total_supply_near: snapshot.near_rpc?.total_supply_near },
    assumptions: (snapshot.assumptions ?? []).map((a) => ({ key: a.key, value: a.value })),
    intents_forensics: { fees: { take_rate_window_days: snapshot.intents_forensics?.fees?.take_rate_window_days } },
  };
  const portCheck = verifyPort(slice);

  const paths = sotp.calibration?.regime_inflation_paths_annual;
  const regimeOptions: RegimeOption[] = REGIME_KEYS.map((key) => {
    const reg = snapshot.supply_physics?.regimes?.find((r) => r.key === key);
    const traj = snapshot.supply_physics?.trajectories?.find((t) => t.regime === key);
    const path = paths?.[key];
    const first = Array.isArray(path) && path.length ? path[0] : null;
    const last = Array.isArray(path) && path.length ? path[path.length - 1] : null;
    const label = key === "status_quo" ? `Status quo, ${fmtPct(first, { decimals: 1 })}` : `SVRN glidepath, ${fmtPct(first, { decimals: 1 })} to ${fmtPct(last, { decimals: 1 })}`;
    const hint = `${reg?.label ?? REGIME_NAME[key] ?? key}${traj ? `; daily issuance ${fmtNear(traj.daily_issuance_start)} at M1 to ${fmtNear(traj.daily_issuance_end)} at M${sotp.horizon_months}` : ""}`;
    return { value: key, label, hint };
  });

  return (
    <div className="space-y-12">
      <VerdictStrip sotp={sotp} totalSupplyNear={snapshot.near_rpc?.total_supply_near ?? null} />
      <WhatYouHaveToBelieve sensitivity={snapshot.sensitivity} />
      <SotpSliders slice={slice} regimeOptions={regimeOptions} portCheck={portCheck} />
      <div className="space-y-8">
        <McFanCharts sotp={sotp} />
        <PercentileTable sotp={sotp} />
      </div>
      <EngineWaterfall sotp={sotp} />
      <SensitivityGrid slice={slice} portCheck={portCheck} />
      {snapshot.relative_value ? <RelativeValue data={snapshot.relative_value} /> : <PeerCompsTable comps={snapshot.comps} sotp={sotp} />}
      <CalibrationPanel snapshot={snapshot} manifest={manifest} />
    </div>
  );
}
