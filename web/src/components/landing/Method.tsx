import { fmtBytes, fmtInt, fmtPct, fmtUsdCompact } from "@/lib/format";
import { confidentialBand, confidentialIsAssumed, confidentialIsEstimated, type LandingData } from "./landingData";
import { LandingSection, SectionHeader } from "./SectionHeader";

const SOURCE_LABEL: Record<string, { label: string; what: string }> = {
  near_rpc: { label: "NEAR mainnet RPC", what: "Block, protocol config, validators, contract storage, epoch-boundary supply" },
  near_rpc_archival: { label: "NEAR archival RPC", what: "Historical contract storage, for state-lock growth" },
  oneclick: { label: "NEAR Intents 1Click", what: "Token universe and dry executable quotes" },
  relay: { label: "Relay", what: "Competitor quotes" },
  lifi: { label: "LI.FI", what: "Competitor quotes from an aggregator" },
  across: { label: "Across", what: "Competitor fees; non-EVM routes return unsupported" },
  nearstats: { label: "NearStats", what: "Public and confidential volume, price history" },
  nearblocks: { label: "NearBlocks", what: "intents.near receipts and caller classes" },
  defillama: { label: "DefiLlama", what: "Fees, revenue, holder revenue, volume, peers" },
  coingecko: { label: "CoinGecko", what: "Peer FDV and market cap" },
};

const STEPS = [
  {
    title: "Collect",
    body: "Four collectors query public, zero-key endpoints. Every response, including error bodies such as “no liquidity” or “route not enabled”, is hashed with SHA-256 and timestamped.",
  },
  {
    title: "Measure",
    body: "Issuance is read from supply jumps at epoch boundaries, not from the nominal formula. State-lock growth comes from archival state; take rates from aligned daily fee and volume series.",
  },
  {
    title: "Model",
    body: "Supply physics under two issuance regimes, a three-engine sum-of-the-parts valuation with a seeded Monte Carlo, solves for what the market price requires of each input, and falsification scenarios on the same engine.",
  },
  {
    title: "Publish",
    body: "One command regenerates the snapshot, the manifest of payload hashes and the IC memo. The terminal and this page render only what those files contain.",
  },
];

/** How the numbers are produced: pipeline steps, sources in this snapshot, reproducibility guarantees. */
export function Method({ data }: { data: LandingData | null }) {
  const sources = data ? Object.entries(data.provenance.sources).sort((a, b) => b[1] - a[1]) : [];
  const facts: Array<{ k: string; v: string }> = [
    { k: "No paid keys", v: "Every endpoint is public. Optional keys in .env only raise rate limits." },
    { k: "No filled-in data", v: "A failed fetch leaves a null and a warning; nothing is backfilled with a typical value." },
    {
      k: "Labelled assumptions",
      v: data
        ? `${fmtInt(data.assumptionsCount)} inputs the data cannot pin down (glidepath, discount rate, confidential take) carry a default, a range and a justification.`
        : "Inputs the data cannot pin down carry a default, a range and a justification.",
    },
    {
      k: "Fixed seed",
      v: data
        ? `Seed ${data.seed}: the ${fmtInt(data.sotp.nPaths)}-path simulation reproduces bit for bit for the same snapshot.`
        : "The simulation reproduces bit for bit for the same snapshot.",
    },
    ...(data && confidentialIsAssumed(data.volume)
      ? [
          {
            k: "Fallbacks labelled",
            v: `Confidential share: NearStats reported ${fmtPct(data.volume.confidentialShareReported, { decimals: 4 })} of volume against ${fmtUsdCompact(data.volume.confidentialTvl)} of confidential TVL, which fails the plausibility check, so this run uses the ${fmtPct(data.volume.confidentialShare30d, { decimals: 0 })} registry assumption and grades the claim as an assumption.`,
          },
        ]
      : data && confidentialIsEstimated(data.volume)
        ? [
            {
              k: "Estimates labelled",
              v: `Confidential share: NearStats reported ${fmtPct(data.volume.confidentialShareReported, { decimals: 4 })} of volume against ${fmtUsdCompact(data.volume.confidentialTvl)} of confidential TVL, which fails the plausibility check, so this run estimates the share on-chain from Confidential Intents Treasury flows over the last 24 hours: ${fmtPct(data.volume.confidentialShare30d, { decimals: 1 })}${confidentialBand(data.volume) ? ` (${confidentialBand(data.volume)})` : ""}. The claim is graded derived, not verified.`,
            },
          ]
        : []),
    { k: "Negatives kept", v: "Corridors where 1Click trails, clipped multiples, unverified TVL and thin samples are printed, not filtered." },
  ];

  return (
    <LandingSection id="method">
      <SectionHeader
        number="3"
        eyebrow="Method"
        title="Collect, measure, model, publish"
        lede="The engine is a small Python package; the terminal is a reader of its artifacts. Anyone can re-run the chain and compare the manifest hash for hash."
      />

      <ol className="mt-14 grid gap-x-10 gap-y-10 border-t border-border-strong pt-10 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s, i) => (
          <li key={s.title} className="min-w-0">
            <div className="tnum font-serif text-[22px] leading-none text-dim">{i + 1}</div>
            <h3 className="mt-3 text-[16px] font-semibold text-ink">{s.title}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-muted">{s.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-16 grid gap-14 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="min-w-0">
          <h3 className="font-serif text-[22px] font-medium text-ink">Sources in this snapshot</h3>
          {data ? (
            <>
              <div className="mt-5 overflow-x-auto">
                <table className="w-full text-[14px]">
                  <thead>
                    <tr className="border-b border-border-strong text-left text-[13px] text-muted">
                      <th className="py-2 pr-4 font-medium">Source</th>
                      <th className="py-2 pr-4 font-medium">What it provides</th>
                      <th className="py-2 text-right font-medium">Payloads</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {sources.map(([k, n]) => (
                      <tr key={k} className="align-top">
                        <td className="py-2.5 pr-4 text-ink sm:whitespace-nowrap">{SOURCE_LABEL[k]?.label ?? k}</td>
                        <td className="py-2.5 pr-4 text-muted">{SOURCE_LABEL[k]?.what ?? ""}</td>
                        <td className="tnum py-2.5 text-right text-ink">{fmtInt(n)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-border-strong text-[13px]">
                      <td className="py-2.5 pr-4 text-ink">Total</td>
                      <td className="py-2.5 pr-4 text-muted">
                        {fmtBytes(data.provenance.bytes)}; {fmtInt(data.provenance.failures)} error responses kept as evidence
                      </td>
                      <td className="tnum py-2.5 text-right text-ink">{fmtInt(data.provenance.records)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </>
          ) : (
            <p className="mt-5 text-[15px] text-muted">No snapshot loaded.</p>
          )}
        </div>

        <div className="min-w-0">
          <h3 className="font-serif text-[22px] font-medium text-ink">Reproducibility</h3>
          <dl className="mt-5 divide-y divide-border border-y border-border">
            {facts.map((f) => (
              <div key={f.k} className="grid grid-cols-[minmax(0,1fr)] gap-1 py-3.5 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-6">
                <dt className="text-[14px] font-medium text-ink">{f.k}</dt>
                <dd className="text-[14.5px] leading-relaxed text-muted">{f.v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </LandingSection>
  );
}
