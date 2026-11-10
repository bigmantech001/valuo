"use client";

import { useCallback, useState } from "react";
import { ForecastBoard } from "./ForecastBoard";
import { ForecastPublisher, type ScenarioSnapshot } from "./ForecastPublisher";
import { SotpSliders, type SotpSlidersProps } from "./SotpSliders";

export interface ScenarioWithForecastProps extends SotpSlidersProps {
  snapshotSha256: string | null;
  snapshotGeneratedAt: string | null;
  spotUsd: number | null;
}

/**
 * The scenario panel followed by "Publish your forecast" and the forecast board. Returns a fragment so the three
 * cards sit in the parent's vertical rhythm exactly where the scenario panel alone used to.
 */
export function ScenarioWithForecast({ snapshotSha256, snapshotGeneratedAt, spotUsd, ...sliderProps }: ScenarioWithForecastProps) {
  const [scenario, setScenario] = useState<ScenarioSnapshot | null>(null);
  const [published, setPublished] = useState<{ account: string | null; n: number }>({ account: null, n: 0 });
  const onPublished = useCallback((account: string) => setPublished((p) => ({ account, n: p.n + 1 })), []);
  return (
    <>
      <SotpSliders {...sliderProps} onScenarioChange={setScenario} />
      <div className="space-y-8">
        <ForecastPublisher
          scenario={scenario}
          horizonMonths={sliderProps.slice.sotp.horizon_months}
          snapshotSha256={snapshotSha256}
          snapshotGeneratedAt={snapshotGeneratedAt}
          spotUsd={spotUsd}
          onPublished={onPublished}
        />
        <ForecastBoard refreshKey={published.n} account={published.account} currentSnapshotSha256={snapshotSha256} />
      </div>
    </>
  );
}
