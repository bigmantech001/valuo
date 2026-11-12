import type { ReactNode } from "react";
import { AXIS_FONT, LABEL_FONT, SVG_STYLE, scaleLinear, slug } from "@/components/charts";
import { ProvenanceBadge } from "@/components/provenance/ProvenanceBadge";
import { FigureList, Panel, SubHead, type FigureItem } from "@/components/tab1/parts";
import { Table, type Column } from "@/components/ui";
import { MethodNote } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
import { fmtInt, fmtUsdCompact, NA } from "@/lib/format";
import { COLORS, withAlpha } from "@/lib/theme";
import type { PeerComps } from "@/lib/types";
import type { WidePeer, WidePeers } from "@/lib/widePeers";
import { mult } from "./fmt";

function fin(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/** Multiple with one decimal below 10x (none for whole numbers) and none above: 2.9×, 8×, 538×, 4,025×. */
function mx(v: number | null | undefined): string {
  return fin(v) ? mult(v, { decimals: Math.abs(v) < 10 && !Number.isInteger(v) ? 1 : 0 }) : NA;
}

/** Share in [0, 1] -> "13th percentile". */
function pctile(share: number | null | undefined): string {
  if (!fin(share)) return NA;
  const n = Math.round(share * 100);
  const tens = n % 100;
  const suffix = tens >= 11 && tens <= 13 ? "th" : n % 10 === 1 ? "st" : n % 10 === 2 ? "nd" : n % 10 === 3 ? "rd" : "th";
  return `${n}${suffix} percentile`;
}

/** Share of `values` at or below `v` (the pipeline's percentile definition). */
function shareAtOrBelow(v: number, values: number[]): number | null {
  return values.length ? values.filter((x) => x <= v).length / values.length : null;
}

function capitalise(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

// --------------------------------------------------------------------------- strip plot
interface RefMark {
  key: string;
  value: number;
  label: string;
  color: string;
  dashed: boolean;
}

interface StripProps {
  title: string;
  description: string;
  peers: WidePeer[];
  median: number | null;
  p25: number | null;
  p75: number | null;
  ci: [number, number] | null;
  marks: RefMark[];
}

const STRIP_W = 640;
const PAD_X = 18;
const DOT_R = 4.5;
const BAND_H = 58;
const LABEL_ROW_H = 16;
const DODGE = [0, -11, 11, -22, 22];

/**
 * One-axis strip plot of FDV / revenue on a log scale. Each peer is a dot (hollow when flagged),
 * the interquartile range is the shaded band, the median a solid rule, the bootstrap interval of
 * the median a bar under the band; NEAR and the model's cap and floor are labelled rules.
 */
function MultipleStrip({ title, description, peers, median, p25, p75, ci, marks }: StripProps) {
  const values = [...peers.map((p) => p.fdv_to_revenue), ...marks.map((m) => m.value)].filter((v) => fin(v) && v > 0);
  if (!values.length) return null;
  const lo = Math.floor(Math.log10(Math.min(...values)));
  const hiRaw = Math.ceil(Math.log10(Math.max(...values)));
  const hi = hiRaw > lo ? hiRaw : lo + 1;
  const sx = scaleLinear([lo, hi], [PAD_X, STRIP_W - PAD_X]);
  const x = (v: number) => sx(Math.log10(v));
  const decades: number[] = [];
  for (let e = lo; e <= hi; e++) decades.push(10 ** e);

  // Reference labels: centred on their rule, kept inside the frame, moved down a row when they would overprint.
  const rowsRight: number[] = [];
  const placed = [...marks]
    .sort((a, b) => a.value - b.value)
    .map((m) => {
      const w = m.label.length * 6.6 + 4;
      const x0 = Math.min(STRIP_W - 4 - w, Math.max(4, x(m.value) - w / 2));
      let row = rowsRight.findIndex((right) => x0 >= right + 8);
      if (row === -1) row = rowsRight.length;
      rowsRight[row] = x0 + w;
      return { ...m, x0, row };
    });
  const nRows = Math.max(1, rowsRight.length);
  const bandTop = 6 + nRows * LABEL_ROW_H + 6;
  const cy = bandTop + BAND_H / 2;
  const axisY = bandTop + BAND_H + 4;
  const height = axisY + 44;

  // Dots: deterministic dodge so near-equal multiples stay individually hoverable.
  const taken: { x: number; off: number }[] = [];
  const dots = [...peers]
    .filter((p) => fin(p.fdv_to_revenue) && p.fdv_to_revenue > 0)
    .sort((a, b) => a.fdv_to_revenue - b.fdv_to_revenue)
    .map((p) => {
      const px = x(p.fdv_to_revenue);
      const off = DODGE.find((o) => !taken.some((t) => t.off === o && Math.abs(t.x - px) < DOT_R * 2 + 1)) ?? 0;
      taken.push({ x: px, off });
      return { p, px, py: cy + off };
    });

  const id = slug(title);
  const medianLabel = fin(median) ? `Median ${mx(median)}${fin(p25) && fin(p75) ? `, middle half ${mx(p25)} to ${mx(p75)}` : ""}` : null;
  const medianW = medianLabel ? medianLabel.length * 6.6 : 0;
  const medianX0 = fin(median) ? Math.min(STRIP_W - 4 - medianW, Math.max(4, x(median) - medianW / 2)) : 0;

  return (
    <svg viewBox={`0 0 ${STRIP_W} ${height}`} role="img" aria-labelledby={`${id}-title`} className="block h-auto w-full" style={SVG_STYLE}>
      <title id={`${id}-title`}>{title}</title>
      <desc>{description}</desc>
      {decades.map((d) => (
        <g key={d}>
          <line x1={x(d)} y1={bandTop} x2={x(d)} y2={axisY} stroke={COLORS.border} strokeWidth={1} />
          <text x={x(d)} y={axisY + 15} textAnchor={d === decades[0] ? "start" : d === decades[decades.length - 1] ? "end" : "middle"} fontSize={AXIS_FONT} fill={COLORS.dim}>
            {`${fmtInt(d)}×`}
          </text>
        </g>
      ))}
      <line x1={PAD_X} y1={axisY} x2={STRIP_W - PAD_X} y2={axisY} stroke={COLORS.borderStrong} strokeWidth={1} />
      {fin(p25) && fin(p75) && p25 > 0 ? (
        <rect x={x(p25)} y={bandTop + 2} width={Math.max(1, x(p75) - x(p25))} height={BAND_H - 4} fill={withAlpha(COLORS.dim, 0.16)}>
          <title>{`Interquartile range: ${mx(p25)} to ${mx(p75)}`}</title>
        </rect>
      ) : null}
      {ci && fin(ci[0]) && fin(ci[1]) && ci[0] > 0 ? (
        <line x1={x(ci[0])} y1={axisY - 1.5} x2={x(ci[1])} y2={axisY - 1.5} stroke={COLORS.ink} strokeWidth={3}>
          <title>{`Bootstrap 90% interval of the median: ${mx(ci[0])} to ${mx(ci[1])}`}</title>
        </line>
      ) : null}
      {fin(median) && median > 0 ? <line x1={x(median)} y1={bandTop} x2={x(median)} y2={axisY + 20} stroke={COLORS.ink} strokeWidth={1.5} /> : null}
      {placed.map((m) => {
        const ly = 6 + m.row * LABEL_ROW_H + 11;
        return (
          <g key={m.key}>
            <line x1={x(m.value)} y1={ly + 4} x2={x(m.value)} y2={axisY} stroke={m.color} strokeWidth={1.5} strokeDasharray={m.dashed ? "4 3" : undefined} />
            <text x={m.x0 + 2} y={ly} fontSize={LABEL_FONT} fontWeight={500} fill={m.color} stroke={COLORS.surface} strokeWidth={3} paintOrder="stroke">
              {m.label}
            </text>
          </g>
        );
      })}
      {dots.map(({ p, px, py }) => {
        const flagged = p.flags.length > 0;
        return (
          <circle key={p.slug} cx={px} cy={py} r={DOT_R} fill={flagged ? COLORS.surface : COLORS.muted} stroke={flagged ? COLORS.muted : COLORS.surface} strokeWidth={flagged ? 1.5 : 1}>
            <title>{`${p.chain}${p.symbol ? ` (${p.symbol.toUpperCase()})` : ""}: ${mx(p.fdv_to_revenue)}. FDV ${fmtUsdCompact(p.fdv_usd)}, 30-day revenue ${fmtUsdCompact(p.revenue_30d_usd)}${flagged ? `. Flagged: ${p.flags.join("; ")}` : ""}`}</title>
          </circle>
        );
      })}
      {medianLabel ? (
        <text x={medianX0} y={axisY + 34} fontSize={LABEL_FONT} fontWeight={500} fill={COLORS.ink}>
          {medianLabel}
        </text>
      ) : null}
    </svg>
  );
}

function LegendItem({ children, swatch }: { children: ReactNode; swatch: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <svg width={18} height={12} viewBox="0 0 18 12" aria-hidden className="shrink-0">
        {swatch}
      </svg>
      {children}
    </span>
  );
}

// --------------------------------------------------------------------------- table rows
type Kind = "peer" | "near" | "near_combined" | "cap" | "floor";

interface Row {
  key: string;
  kind: Kind;
  label: string;
  symbol?: string | null;
  sub?: string | null;
  flags?: string[];
  revenue_30d_usd?: number | null;
  fdv_usd?: number | null;
  multiple: number;
}

/**
 * Wider peer set: FDV to annualised 30-day revenue for the top revenue chains with their own
 * token, with NEAR and the model's terminal multiple cap and floor placed in the distribution.
 * Reads `wide_peers` (and `comps.near_combined` for the multiple the model values NEAR on).
 * Additive: nothing here feeds the valuation. The headline, reading, rules and caveats are the
 * pipeline's own sentences.
 */
export function WidePeerSet({ data, comps }: { data: WidePeers | null | undefined; comps?: PeerComps | null }) {
  if (!data || !Array.isArray(data.peers) || !data.peers.length || !data.distribution) return null;
  const d = data.distribution;
  const peers = data.peers.filter((p) => fin(p.fdv_to_revenue));
  const multiples = peers.map((p) => p.fdv_to_revenue);
  const n = fin(data.n_peers) ? data.n_peers : peers.length;
  const cap = fin(data.terminal_multiple_cap) ? data.terminal_multiple_cap : null;
  const floor = fin(data.terminal_multiple_floor) ? data.terminal_multiple_floor : null;
  const nearL1 = fin(data.near?.fdv_to_revenue) ? data.near.fdv_to_revenue : null;
  const combined = comps?.near_combined;
  const nearCombined = fin(combined?.fdv_to_revenue) ? combined.fdv_to_revenue : null;
  const nearCombinedShare = fin(nearCombined) ? shareAtOrBelow(nearCombined, multiples) : null;
  const threePeer = fin(comps?.median_fdv_to_revenue_ex_near) ? comps.median_fdv_to_revenue_ex_near : data.model_three_peer?.median_fdv_to_revenue ?? null;
  const exf = data.ex_flagged;

  // The pipeline headline is "finding; context". The finding is the title, the rest the lede.
  const cut = data.headline.indexOf("; ");
  const titleText = cut > 0 ? data.headline.slice(0, cut) : data.headline;
  const ledeText = cut > 0 ? capitalise(data.headline.slice(cut + 2)) : null;

  const marks: RefMark[] = [];
  if (fin(floor) && floor > 0) marks.push({ key: "floor", value: floor, label: `Model floor ${mx(floor)}`, color: COLORS.ink, dashed: true });
  if (fin(cap) && cap > 0) marks.push({ key: "cap", value: cap, label: `Model cap ${mx(cap)}`, color: COLORS.ink, dashed: true });
  if (fin(nearCombined) && nearCombined > 0) marks.push({ key: "near_combined", value: nearCombined, label: `NEAR L1 + Intents ${mx(nearCombined)}`, color: COLORS.accent, dashed: false });
  if (fin(nearL1) && nearL1 > 0) marks.push({ key: "near", value: nearL1, label: `NEAR L1 only ${mx(nearL1)}`, color: COLORS.accent, dashed: false });

  const rows: Row[] = peers.map((p) => ({
    key: `peer-${p.slug}`,
    kind: "peer" as Kind,
    label: p.chain,
    symbol: p.symbol,
    sub: `Rank ${fmtInt(p.rank_by_revenue)} by revenue`,
    flags: p.flags,
    revenue_30d_usd: p.revenue_30d_usd,
    fdv_usd: p.fdv_usd,
    multiple: p.fdv_to_revenue,
  }));
  if (fin(nearL1)) {
    rows.push({
      key: "near",
      kind: "near",
      label: "NEAR, L1 gas revenue only",
      sub: fin(data.near.rank_by_revenue) ? `Rank ${fmtInt(data.near.rank_by_revenue)} of ${fmtInt(data.near.n_chains_ranked)} by revenue. Not counted in the set` : "Not counted in the set",
      revenue_30d_usd: data.near.revenue_30d_usd,
      fdv_usd: data.near.fdv_usd,
      multiple: nearL1,
    });
  }
  if (fin(nearCombined)) {
    rows.push({ key: "near_combined", kind: "near_combined", label: "NEAR, L1 + Intents", sub: "The basis the model values NEAR on. Not counted in the set", revenue_30d_usd: combined?.revenue_30d_usd, fdv_usd: combined?.fdv_usd, multiple: nearCombined });
  }
  if (fin(cap)) rows.push({ key: "cap", kind: "cap", label: "Model terminal multiple cap", sub: "Assumption, from the run's registry", multiple: cap });
  if (fin(floor)) rows.push({ key: "floor", kind: "floor", label: "Model terminal multiple floor", sub: "Assumption, from the run's registry", multiple: floor });
  rows.sort((a, b) => a.multiple - b.multiple);

  const isModel = (r: Row) => r.kind === "cap" || r.kind === "floor";
  const isNear = (r: Row) => r.kind === "near" || r.kind === "near_combined";
  const columns: Column<Row>[] = [
    {
      key: "chain",
      header: "Chain",
      render: (r) => (
        <div>
          <div className={cn(isNear(r) ? "font-medium text-accent" : isModel(r) ? "font-medium text-ink" : "text-ink")}>
            {r.symbol && r.symbol.toUpperCase() !== r.label.toUpperCase() ? <span className="font-medium">{r.symbol.toUpperCase()} </span> : null}
            <span className={r.symbol && r.symbol.toUpperCase() !== r.label.toUpperCase() ? "text-muted" : undefined}>{r.label}</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 text-[12px] text-dim">
            {r.sub ? <span>{r.sub}</span> : null}
            {r.flags?.length ? (
              <span title={r.flags.join(" ")} className="cursor-help underline decoration-dotted underline-offset-2">
                Flagged
              </span>
            ) : null}
          </div>
        </div>
      ),
    },
    { key: "rev", header: "30-day revenue", numeric: true, render: (r) => (isModel(r) ? <span className="text-dim">{NA}</span> : fmtUsdCompact(r.revenue_30d_usd)) },
    { key: "fdv", header: "FDV", numeric: true, render: (r) => (isModel(r) ? <span className="text-dim">{NA}</span> : fmtUsdCompact(r.fdv_usd)) },
    { key: "mult", header: "FDV / revenue", numeric: true, render: (r) => <span className={cn(r.kind !== "peer" && "font-semibold", isNear(r) ? "text-accent" : r.kind !== "peer" ? "text-ink" : undefined)}>{mx(r.multiple)}</span> },
  ];

  const boot = d.bootstrap;
  const figures: FigureItem[] = [
    { key: "n", label: "Peers in the set", sub: `Top ${fmtInt(data.n_peers_target)} by 30-day revenue with their own token, of ${fmtInt(data.n_chains_ranked)} chains with revenue`, value: fmtInt(n) },
    {
      key: "median",
      label: "Median FDV / revenue",
      sub: d.median_ci90 ? `Bootstrap 90% interval ${mx(d.median_ci90[0])} to ${mx(d.median_ci90[1])}${boot ? ` (${fmtInt(boot.n_resamples)} resamples, seed ${boot.seed})` : ""}` : null,
      value: mx(d.median),
    },
    { key: "iqr", label: "Interquartile range", sub: "25th to 75th percentile", value: `${mx(d.p25)} to ${mx(d.p75)}` },
    { key: "range", label: "Lowest to highest", value: `${mx(d.min)} to ${mx(d.max)}` },
    { key: "cap", label: `Model cap, ${mx(cap)}`, sub: `${fmtInt(data.n_peers_at_or_below_cap)} of ${fmtInt(n)} peers trade at or below it`, value: pctile(data.cap_percentile) },
    { key: "floor", label: `Model floor, ${mx(floor)}`, sub: `${fmtInt(data.n_peers_at_or_below_floor)} of ${fmtInt(n)} peers trade at or below it`, value: pctile(data.floor_percentile) },
    { key: "near", label: `NEAR on L1 gas revenue only, ${mx(nearL1)}`, sub: `${fmtInt(data.near?.n_peers_at_or_below)} of ${fmtInt(n)} peers trade at or below it`, value: pctile(data.near?.percentile) },
  ];
  if (fin(nearCombined)) figures.push({ key: "near_combined", label: `NEAR on L1 + Intents revenue, ${mx(nearCombined)}`, sub: "The multiple the model uses; no peer row has an equivalent", value: pctile(nearCombinedShare) });
  if (exf && fin(exf.median)) {
    figures.push({ key: "exf", label: "Median without flagged rows", sub: `${fmtInt(exf.n_peers)} peers; cap at the ${pctile(exf.cap_percentile)}`, value: mx(exf.median) });
  }
  if (fin(threePeer)) figures.push({ key: "three", label: "Three-peer median the model uses", sub: "Solana, Ethereum, Hyperliquid", value: mx(threePeer) });

  const flagged = peers.filter((p) => p.flags.length);
  const stripTitle = titleText;
  const stripDesc = `FDV to annualised 30-day revenue on a log axis for ${fmtInt(n)} chain tokens. Median ${mx(d.median)}, interquartile range ${mx(d.p25)} to ${mx(d.p75)}, range ${mx(d.min)} to ${mx(d.max)}. Model floor ${mx(floor)}, model cap ${mx(cap)}, NEAR on L1 gas revenue ${mx(nearL1)}${fin(nearCombined) ? `, NEAR on L1 plus Intents revenue ${mx(nearCombined)}` : ""}.`;

  return (
    <section id="wide-peers" className="space-y-6">
      <SubHead
        title={titleText}
        aside={
          <>
            <ProvenanceBadge source={data.sources?.revenue?.source ?? "defillama"} name={data.sources?.revenue?.name ?? "overview:fees:dailyRevenue"} />
            <ProvenanceBadge source={data.sources?.fdv?.source ?? "coingecko"} name={data.sources?.fdv?.name ?? "coins_markets_wide"} />
          </>
        }
      >
        {ledeText ? <p>{ledeText}</p> : null}
        <p className={cn(ledeText && "mt-2")}>A wider set than the three peers the model uses, ranked by revenue before any multiple was computed. It does not feed the valuation.</p>
      </SubHead>

      <Panel className="px-4 py-4">
        <div className="valuo-scroll overflow-x-auto">
          {/* Inline: the phone rule `main :where(div) { min-width: 0 }` is unlayered and beats the min-w utility. */}
          <div style={{ minWidth: "34rem" }}>
            <MultipleStrip title={stripTitle} description={stripDesc} peers={peers} median={d.median} p25={d.p25} p75={d.p75} ci={d.median_ci90} marks={marks} />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[12.5px] text-muted">
          <LegendItem swatch={<circle cx={9} cy={6} r={4.5} fill={COLORS.muted} />}>Peer chain token</LegendItem>
          <LegendItem swatch={<circle cx={9} cy={6} r={4} fill={COLORS.surface} stroke={COLORS.muted} strokeWidth={1.5} />}>Flagged peer, kept in the distribution</LegendItem>
          <LegendItem swatch={<rect x={1} y={1} width={16} height={10} fill={withAlpha(COLORS.dim, 0.16)} />}>Interquartile range</LegendItem>
          <LegendItem swatch={<line x1={1} y1={6} x2={17} y2={6} stroke={COLORS.ink} strokeWidth={3} />}>Bootstrap 90% interval of the median</LegendItem>
          <LegendItem swatch={<line x1={9} y1={0} x2={9} y2={12} stroke={COLORS.ink} strokeWidth={1.5} strokeDasharray="4 3" />}>Model cap and floor</LegendItem>
          <LegendItem swatch={<line x1={9} y1={0} x2={9} y2={12} stroke={COLORS.accent} strokeWidth={1.5} />}>NEAR</LegendItem>
        </div>
        <p className="mt-2 text-[12.5px] leading-relaxed text-dim">FDV divided by annualised 30-day revenue, log scale. Hover a dot for the chain.</p>
      </Panel>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <Panel className="valuo-scroll self-start overflow-x-auto px-2 py-1">
          <div style={{ minWidth: "30rem" }}>
            <Table<Row>
              columns={columns}
              rows={rows}
              rowKey={(r) => r.key}
              rowClassName={(r) => (r.kind === "peer" ? undefined : "bg-surface-2/70")}
              dense={false}
              stickyHeader={false}
              caption="Lowest multiple first. NEAR and the model's cap and floor are placed where they fall."
            />
          </div>
        </Panel>
        <Panel className="self-start px-5 py-1">
          <FigureList items={figures} />
        </Panel>
      </div>

      <p className="max-w-4xl text-[14.5px] leading-relaxed text-ink">{data.reading}</p>

      {data.caveats?.length ? (
        <div className="rounded-md border border-amber/30 bg-amber/5 px-4 py-3">
          <div className="text-[13.5px] font-medium text-amber">Limits of this comparison</div>
          <ul className="mt-1.5 list-disc space-y-1 pl-5 text-[13.5px] leading-relaxed text-muted marker:text-dim">
            {data.caveats.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <MethodNote summary="Inclusion rules, excluded chains and sources">
        <p>Basis: {data.basis}. {data.annualization}. Percentile: {data.percentile_definition}.</p>
        {data.inclusion_rules?.length ? (
          <ul className="list-disc space-y-1 pl-5 marker:text-dim">
            {data.inclusion_rules.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        ) : null}
        <p>
          {data.excluded?.length
            ? `Excluded inside the cut (${fmtInt(data.excluded.length)}): ${data.excluded.map((e) => `${e.chain}, rank ${fmtInt(e.rank_by_revenue)} with ${fmtUsdCompact(e.revenue_30d_usd)} of 30-day revenue (${e.reason})`).join("; ")}.`
            : "No chain inside the cut was excluded."}{" "}
          {fmtInt(data.n_chains_below_cut)} lower-revenue chains fall below the cut and are not listed.
        </p>
        {flagged.length ? (
          <p>
            Flagged rows ({fmtInt(flagged.length)}): {flagged.map((p) => `${p.chain}: ${p.flags.join(" ")}`).join("; ")}.{" "}
            {exf && fin(exf.median) ? `Without them: ${fmtInt(exf.n_peers)} peers, median ${mx(exf.median)}, quartiles ${mx(exf.p25)} to ${mx(exf.p75)}, ${fmtInt(exf.n_peers_at_or_below_cap)} at or below the cap.` : ""}
          </p>
        ) : null}
        <p>
          Cap {mx(cap)} and floor {mx(floor)}: {data.cap_source ?? "assumptions registry"} (<code>wide_peers.terminal_multiple_cap</code>, <code>wide_peers.terminal_multiple_floor</code>). {data.near?.basis}
        </p>
        {data.model_three_peer ? (
          <p>
            Three-peer contrast: {data.model_three_peer.label}, {mx(threePeer)}. {capitalise(data.model_three_peer.basis)}
          </p>
        ) : null}
        <p>
          Fields: <code>wide_peers.peers[]</code>, <code>wide_peers.distribution</code>, <code>wide_peers.near</code>, <code>wide_peers.ex_flagged</code>, <code>wide_peers.excluded[]</code>.{boot ? ` Bootstrap: ${boot.method}.` : ""}
        </p>
      </MethodNote>
    </section>
  );
}
