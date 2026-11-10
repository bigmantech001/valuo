import type { ReactNode } from "react";
import { fmtBlock, fmtInt, fmtUtc } from "@/lib/format";
import { MODULE_LABEL, type LandingData } from "./landingData";
import { LandingSection, SectionHeader } from "./SectionHeader";

const COMMANDS: Array<{ cmd: string; note: string }> = [
  { cmd: "make reproduce", note: "live RPC audit, quote matrix, forensics, seeded Monte Carlo; writes snapshot, manifest and memo" },
  { cmd: "make test", note: "accounting identities, HHI bounds, Monte Carlo determinism, manifest hashes" },
  { cmd: "make dev", note: "the terminal, served from web/" },
];

/**
 * Split "execution_bench: text" into a human module name and the message, and swap a leading
 * corridor id ("eth_usdc_btc $500: ...") for the corridor's label. The message is otherwise verbatim.
 */
function splitWarning(w: string, corridors: Record<string, string>): { module: string | null; text: string } {
  const m = /^([a-z_]+):\s+(.*)$/s.exec(w);
  if (!m) return { module: null, text: w };
  let text = m[2];
  const id = /^([a-z0-9_]+)(?=\s)/.exec(text)?.[1];
  if (id && corridors[id]) text = corridors[id].replace(/\s*->\s*/g, " \u2192 ") + text.slice(id.length);
  else if (/^[a-z]+[\s:,]/.test(text)) text = text.charAt(0).toUpperCase() + text.slice(1);
  return { module: MODULE_LABEL[m[1]] ?? m[1], text };
}

/** Reproduction commands, the integrity facts of the committed snapshot, and the caveats it carries. */
export function Reproduce({ data }: { data: LandingData | null }) {
  const corridors = Object.fromEntries((data?.bench?.corridors ?? []).map((c) => [c.id, c.label]));
  return (
    <LandingSection id="reproduce">
      <SectionHeader
        number="7"
        eyebrow="Reproduce"
        title="Re-run every number in about a minute"
        lede="No paid API keys. Python 3.11 or later with uv, and Node 18 or later for the terminal. The pipeline exits non-zero if the on-chain or forensics collectors fail; a venue that returns no quote is recorded as such, never substituted."
      />

      <div className="mt-12 grid gap-12 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="min-w-0">
          <pre className="overflow-x-auto rounded-lg bg-ink px-6 py-5 font-mono text-[13px] leading-[1.9] text-surface">
            <span className="text-surface/50"># from the repository root</span>
            {"\n"}
            {COMMANDS.map((c) => (
              <span key={c.cmd}>
                <span className="text-surface/50">$ </span>
                {c.cmd}
                {"\n"}
              </span>
            ))}
            {"\n"}
            <span className="text-surface/50"># equivalent to make reproduce</span>
            {"\n"}
            <span className="text-surface/50">$ </span>cd quant &amp;&amp; uv run python -m valuo.reproduce
          </pre>
          <dl className="mt-6 space-y-2 text-[14.5px] leading-relaxed">
            {COMMANDS.map((c) => (
              <div key={c.cmd} className="grid grid-cols-[minmax(0,1fr)] gap-x-6 sm:grid-cols-[9rem_minmax(0,1fr)]">
                <dt className="font-mono text-[13px] text-ink">{c.cmd}</dt>
                <dd className="text-muted">{c.note.charAt(0).toUpperCase() + c.note.slice(1)}.</dd>
              </div>
            ))}
          </dl>
          {data ? (
            <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-[14.5px]">
              <a href="/api/snapshot?format=json" download className="text-accent underline-offset-4 hover:underline">
                Download the snapshot (JSON)
              </a>
              <a href="/api/snapshot?format=memo" download className="text-accent underline-offset-4 hover:underline">
                Download the IC memo (Markdown)
              </a>
            </div>
          ) : null}
        </div>

        <div className="min-w-0">
          <h3 className="font-serif text-[22px] font-medium text-ink">Committed snapshot</h3>
          {data ? (
            <dl className="mt-5 divide-y divide-border border-y border-border text-[14px]">
              <Row k="Generated" v={fmtUtc(data.generatedAtUtc, { seconds: true })} />
              <Row k="Pinned block" v={fmtBlock(data.provenance.manifestBlock ?? data.chain.block)} />
              <Row k="Raw payloads" v={`${fmtInt(data.provenance.records)} hashed, ${fmtInt(data.provenance.failures)} error responses kept`} />
              <Row k="Pipeline runtime" v={`${fmtInt(data.runtimeS)} s`} />
              <Row k="Engine version" v={data.valuoVersion} />
              <Row k="Snapshot SHA-256" v={<span className="break-all font-mono text-[12px] leading-relaxed">{data.provenance.snapshotSha256 ?? "n/a"}</span>} />
            </dl>
          ) : (
            <p className="mt-5 text-[15px] text-muted">No snapshot on disk.</p>
          )}
          <p className="mt-4 text-[13.5px] leading-relaxed text-muted">
            To verify offline, <code className="font-mono text-[12.5px] text-ink">shasum -a 256 artifacts/latest_snapshot.json</code> must equal{" "}
            <code className="font-mono text-[12.5px] text-ink">snapshot_sha256</code> in the manifest. The terminal recomputes it on load.
          </p>
        </div>
      </div>

      {data && data.warnings.length ? (
        <div className="mt-16 max-w-[62rem]">
          <h3 className="font-serif text-[22px] font-medium text-ink">Caveats carried by this snapshot</h3>
          <p className="mt-2 text-[14.5px] text-muted">
            {fmtInt(data.warnings.length)} warnings raised by the pipeline, printed as recorded.
          </p>
          <ol className="mt-6 divide-y divide-border border-y border-border">
            {data.warnings.map((w, i) => {
              const { module, text } = splitWarning(w, corridors);
              return (
                <li key={i} className="grid grid-cols-[minmax(0,1fr)] gap-x-6 gap-y-1 py-3 text-[14px] leading-relaxed sm:grid-cols-[11rem_minmax(0,1fr)]">
                  <span className="text-ink">{module ?? "Pipeline"}</span>
                  <span className="min-w-0 break-words text-muted">{text}</span>
                </li>
              );
            })}
          </ol>
        </div>
      ) : null}
    </LandingSection>
  );
}

function Row({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_minmax(0,1fr)] gap-4 py-2.5">
      <dt className="text-muted">{k}</dt>
      <dd className="tnum min-w-0 text-ink">{v}</dd>
    </div>
  );
}
