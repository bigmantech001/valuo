import type { ReactNode } from "react";
import { LineChart, type LineMarker, type LineSeries } from "@/components/charts/LineChart";
import { Card, Stat } from "@/components/ui";
import { MethodNote, StatGrid } from "@/components/ui/Section";
import {
  feePoolDayIndex,
  feePoolDayLabel,
  feePoolRollingPoints,
  type FeePoolPoint,
  type FeePoolProtocol,
  type FeePoolShare as FeePoolShareData,
  type FeePoolTrend,
} from "@/lib/feePool";
import { fmtHash, fmtInt, fmtNum, fmtPct, fmtUsdCompact, fmtUtc } from "@/lib/format";
import { COLORS, SERIES_COLORS, type Tone } from "@/lib/theme";

export interface FeePoolShareProps {
  /** `snapshot.fee_pool_share`; absent in snapshots written before the collector landed */
  data: FeePoolShareData | null | undefined;
}

const LINK = "text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent";
const TH = "border-b border-ink/80 px-2 py-2 text-[12.5px] font-medium text-muted";

function pp(v: number | null | undefined, decimals = 2): string {
  return typeof v === "number" && Number.isFinite(v) ? `${fmtNum(v, { decimals, signed: true })} pp` : "n/a";
}

function signTone(v: number | null | undefined): Tone {
  if (typeof v !== "number" || !Number.isFinite(v) || v === 0) return "neutral";
  return v > 0 ? "emerald" : "crimson";
}

/** "-9.59 to -3.81" from a 90% interval in percentage points, or "n/a". */
function ciText(ci: [number, number] | null | undefined): string {
  return ci && Number.isFinite(ci[0]) && Number.isFinite(ci[1]) ? `${fmtNum(ci[0], { decimals: 2, signed: true })} to ${fmtNum(ci[1], { decimals: 2, signed: true })}` : "n/a";
}

function directionText(t: FeePoolTrend | null | undefined): string {
  if (!t || t.status !== "measured" || !t.direction) return "not measured";
  if (t.direction === "flat") return "no trend shown";
  return t.excludes_zero ? `${t.direction}, interval excludes zero` : t.direction;
}

function httpsUrl(u: string | null | undefined): string | null {
  return typeof u === "string" && u.startsWith("https://") ? u : null;
}

/** Render `backticked` spans of collector prose as <code>. */
function withCode(text: string): ReactNode {
  return text.split("`").map((part, i) => (i % 2 === 1 ? <code key={i}>{part}</code> : part));
}

function Heading({ title, children }: { title: ReactNode; children?: ReactNode }) {
  return (
    <div className="max-w-3xl">
      <h3 className="font-serif text-[24px] font-medium leading-tight text-ink">{title}</h3>
      {children ? <p className="mt-2 text-[15px] leading-relaxed text-muted">{children}</p> : null}
    </div>
  );
}

/** Level tile for one read-out date: the share then, and how far the latest share sits from it. */
function ShareThen({ label, point, change, exRelay }: { label: string; point: FeePoolPoint | null | undefined; change: number | null | undefined; exRelay: FeePoolPoint | null | undefined }) {
  return (
    <Stat
      label={label}
      value={point?.share ?? null}
      format={(v) => fmtPct(v, { decimals: 1 })}
      delta={typeof change === "number" ? { value: pp(change, 1), tone: signTone(change), label: "from then to now" } : undefined}
      hint={point ? `30 days to ${point.date}${exRelay ? `; ${fmtPct(exRelay.share, { decimals: 1 })} with Relay excluded` : ""}` : "Window too short for this look-back"}
    />
  );
}

function TrendRow({ label, t }: { label: ReactNode; t: FeePoolTrend | null | undefined }) {
  const ok = Boolean(t && t.status === "measured");
  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="px-2 py-2 pl-0 align-top text-ink">{label}</td>
      <td className="tnum px-2 py-2 text-right align-top text-ink">{ok ? pp(t?.slope_pp_per_30d) : "n/a"}</td>
      <td className="tnum whitespace-nowrap px-2 py-2 text-right align-top">{ok ? ciText(t?.ci90_pp_per_30d) : "n/a"}</td>
      <td className="tnum px-2 py-2 text-right align-top">{ok && typeof t?.r2 === "number" ? fmtNum(t.r2, { decimals: 2 }) : "n/a"}</td>
      <td className="tnum px-2 py-2 text-right align-top">{ok ? fmtInt(t?.n_points ?? null) : "n/a"}</td>
      <td className="px-2 py-2 pr-0 align-top">{ok ? directionText(t) : (t?.note ?? "not measured")}</td>
    </tr>
  );
}

/**
 * NEAR Intents' share of the fees collected by the cross-chain routers DefiLlama covers
 * (`fee_pool_share`): the rolling 30-day share over the common window with the ex-Relay line,
 * the per-protocol 30-day fee table, the now / 30d / 90d / window-start read-out with the
 * Newey-West trend interval, and each adapter's own fee definition. Renders nothing when the
 * snapshot does not carry the section.
 */
export function FeePoolShare({ data }: FeePoolShareProps) {
  if (!data) return null;

  if (data.status !== "measured" || !data.share?.now) {
    return (
      <section className="space-y-6">
        <Heading title="Fee-pool share against competing routers was not measured in this run">
          {(data.note ?? "The DefiLlama fee series needed for a common window were not available").replace(/\.?\s*$/, ".")} No share figure is shown; nothing is substituted.
        </Heading>
        {data.unavailable?.length ? (
          <p className="max-w-3xl text-[13.5px] leading-relaxed text-muted">
            Unavailable: {data.unavailable.map((u) => `${u.name} (${u.reason})`).join("; ")}.
          </p>
        ) : null}
      </section>
    );
  }

  const share = data.share;
  const now = share.now as FeePoolPoint;
  const ex = data.share_ex_relay ?? null;
  const w = data.window ?? null;
  const rank = data.rank ?? null;
  const pool = data.pool_label ? `${data.pool_label} ` : "";
  const focus = data.focus_slug ?? "near-intents";
  const protocols = [...data.protocols].sort((a, b) => (a.rank_30d ?? 1e9) - (b.rank_30d ?? 1e9));
  const maxShare = Math.max(1e-9, ...protocols.map((p) => p.share_30d ?? 0));
  const days = data.rolling_days ?? data.rolling?.window_days ?? 30;

  // Rolling series: both lines are shares in percent, so they sit on one axis.
  const pts = feePoolRollingPoints(data.rolling).filter((p) => p.share !== null && feePoolDayIndex(p.date) !== null);
  const xs = pts.map((p) => feePoolDayIndex(p.date) as number);
  const hasEx = pts.length > 0 && pts.every((p) => p.share_ex_relay !== null);
  const series: LineSeries[] = [{ name: `Share of the ${pool}pool`, values: pts.map((p) => (p.share as number) * 100), color: SERIES_COLORS[0], strokeWidth: 2 }];
  if (hasEx) series.push({ name: "Share with Relay excluded", values: pts.map((p) => (p.share_ex_relay as number) * 100), color: SERIES_COLORS[1], dashed: true });

  // Headroom above the highest point so the marker label clears the lines; capped at 100%.
  const yTop = Math.min(100, Math.ceil((Math.max(0, ...series.flatMap((sr) => sr.values)) * 1.12) / 10) * 10);

  // Mark the date on which the largest competing fee series peaked: the share moves with that denominator.
  const peak = protocols.filter((p) => p.slug !== focus && typeof p.fees_30d_peak_usd === "number").sort((a, b) => (b.fees_30d_peak_usd as number) - (a.fees_30d_peak_usd as number))[0];
  const peakDay = feePoolDayIndex(peak?.fees_30d_peak_date);
  const markers: LineMarker[] = [];
  if (peak && peakDay !== null && xs.length > 1 && peakDay > xs[0] && (peakDay - xs[0]) / (xs[xs.length - 1] - xs[0]) < 0.8) {
    markers.push({ x: peakDay, label: `${peak.label} fee peak` });
  }

  const startPt = share.window_start ?? null;
  const moved = startPt ? `${fmtPct(startPt.share, { decimals: 1 })} to ${fmtPct(now.share, { decimals: 1 })}` : fmtPct(now.share, { decimals: 1 });
  const chartTitle = startPt
    ? `NEAR Intents' rolling ${days}-day fee share went from ${moved}${share.low && share.high ? `, ranging ${fmtPct(share.low.share, { decimals: 1 })} to ${fmtPct(share.high.share, { decimals: 1 })}` : ""}`
    : `NEAR Intents' rolling ${days}-day fee share stands at ${moved}`;
  const direction = data.trend?.status === "measured" ? data.trend.direction : null;
  const title = `NEAR Intents collects ${fmtPct(now.share, { decimals: 1 })} of the ${pool}cross-chain fee pool${rank?.near_intents ? `, rank ${rank.near_intents} of ${rank.of}` : ""}${
    direction === "falling" ? ", and its share is falling" : direction === "rising" ? ", and its share is rising" : direction === "flat" ? ", with no share trend shown" : ""
  }`;
  const otherRobustness = (data.robustness ?? []).filter((r) => r.key !== "ex_relay");

  return (
    <section className="space-y-6">
      <Heading title={title}>{data.headline}</Heading>

      <StatGrid cols={4}>
        <Stat
          label={`Share of ${days}-day fees, latest`}
          value={now.share}
          format={(v) => fmtPct(v, { decimals: 1 })}
          hint={
            <>
              {days} days to {now.date}
              {rank?.reference && rank.near_intents ? `; rank ${rank.near_intents} of ${rank.of}, ${rank.reference.relation ?? "behind"} ${rank.reference.name} at ${fmtPct(rank.reference.share_30d, { decimals: 1 })}` : ""}
              {ex?.now ? `; ${fmtPct(ex.now.share, { decimals: 1 })} with Relay excluded` : ""}
            </>
          }
        />
        <ShareThen label="30 days earlier" point={share.d30_ago} change={share.change_pp_30d} exRelay={ex?.d30_ago} />
        <ShareThen label="90 days earlier" point={share.d90_ago} change={share.change_pp_90d} exRelay={ex?.d90_ago} />
        <ShareThen label="Start of the common window" point={share.window_start} change={share.change_pp_window} exRelay={ex?.window_start} />
      </StatGrid>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-2">
        <Card
          kicker={`Rolling ${days}-day share, ${fmtInt(pts.length)} daily points`}
          title={chartTitle}
          subtitle={
            <>
              NEAR Intents&apos; fees over the trailing {days} days divided by the same sum across the pool, in percent.
              {hasEx ? " The dashed line drops Relay from the denominator, because its adapter counts integrator app fees and swap costs." : ""}
              {markers.length && peak ? ` The marker is the day ${peak.label}'s ${days}-day fees peaked at ${fmtUsdCompact(peak.fees_30d_peak_usd)}.` : ""}
            </>
          }
          footer={
            share.low && share.high ? (
              <>
                Low {fmtPct(share.low.share, { decimals: 1 })} on {share.low.date}; high {fmtPct(share.high.share, { decimals: 1 })} on {share.high.date}. The path is not a line; read the slope below as average drift, not a
                forecast.
              </>
            ) : undefined
          }
        >
          {pts.length > 1 ? (
            <LineChart
              title={chartTitle}
              description={`Rolling ${days}-day fee share of NEAR Intents from ${pts[0].date} to ${pts[pts.length - 1].date}, in percent of the ${pool}pool${hasEx ? ", with a second line excluding Relay" : ""}.`}
              series={series}
              x={xs}
              xFormat={(d) => feePoolDayLabel(d)}
              yFormat={(v) => `${fmtNum(v, { decimals: 0 })}%`}
              yDomain={yTop > 0 ? [0, yTop] : undefined}
              markers={markers}
              legend
              xTicks={5}
              height={300}
            />
          ) : (
            <p className="text-[13px] text-dim">The snapshot carries no rolling share series.</p>
          )}
        </Card>

        <Card
          kicker={`${days} days to ${w?.end ?? now.date}`}
          title={
            rank?.leader && rank.leader.slug !== focus
              ? `${rank.leader.name} collects ${fmtPct(rank.leader.share_30d, { decimals: 1 })} of the pool; NEAR Intents ${fmtPct(now.share, { decimals: 1 })}`
              : `NEAR Intents leads the pool at ${fmtPct(now.share, { decimals: 1 })}`
          }
          subtitle={`Fees as each DefiLlama adapter defines them, summed over the same ${days} days. Pool total ${fmtUsdCompact(data.pool_30d_usd ?? null)}.`}
        >
          <div className="w-full overflow-x-auto valuo-scroll">
            <table className="w-full min-w-[30rem] border-collapse text-[13.5px]">
              <thead>
                <tr>
                  <th scope="col" className={`${TH} w-10 pl-0 text-left`}>
                    Rank
                  </th>
                  <th scope="col" className={`${TH} text-left`}>
                    Protocol
                  </th>
                  <th scope="col" className={`${TH} text-right`}>
                    {days}-day fees
                  </th>
                  <th scope="col" className={`${TH} w-[34%] text-left`}>
                    Share of pool
                  </th>
                  <th scope="col" className={`${TH} pr-0 text-right`}>
                    90-day fees
                  </th>
                </tr>
              </thead>
              <tbody>
                {protocols.map((p) => {
                  const isFocus = p.slug === focus;
                  return (
                    <tr key={p.slug} className={`border-b border-border last:border-b-0 ${isFocus ? "bg-surface-2/60" : ""}`}>
                      <td className="tnum px-2 py-2 pl-0 align-top text-muted">{fmtInt(p.rank_30d)}</td>
                      <td className={`px-2 py-2 align-top text-ink ${isFocus ? "font-semibold" : ""}`}>
                        {p.label}
                        {p.name && p.name !== p.label ? <div className="text-[12px] font-normal text-dim">{p.name}</div> : null}
                      </td>
                      <td className={`tnum px-2 py-2 text-right align-top text-ink ${isFocus ? "font-semibold" : ""}`}>{fmtUsdCompact(p.fees_30d_usd)}</td>
                      <td className="px-2 py-2 align-top">
                        <div className="flex items-center gap-2">
                          <div className="h-2.5 flex-1 rounded-sm bg-surface-2">
                            <div className="h-2.5 rounded-sm" style={{ width: `${((p.share_30d ?? 0) / maxShare) * 100}%`, backgroundColor: isFocus ? SERIES_COLORS[0] : COLORS.dim }} />
                          </div>
                          <span className={`tnum w-12 text-right text-ink ${isFocus ? "font-semibold" : ""}`}>{fmtPct(p.share_30d, { decimals: 1 })}</span>
                        </div>
                      </td>
                      <td className="tnum px-2 py-2 pr-0 text-right align-top">{fmtUsdCompact(p.fees_90d_usd)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Card
        kicker="Linear trend of the share, percentage points per 30 days"
        title={
          data.trend?.status === "measured"
            ? `Share trend ${pp(data.trend.slope_pp_per_30d)} per 30 days, 90% interval ${ciText(data.trend.ci90_pp_per_30d)}`
            : "Share trend not measured on this window"
        }
        subtitle="Ordinary least squares on time with a Newey-West 90% interval. A share gain is claimed only when the slope is positive and the interval excludes zero."
      >
        <div className="w-full overflow-x-auto valuo-scroll">
          <table className="w-full min-w-[36rem] border-collapse text-[13.5px] text-muted">
            <thead>
              <tr>
                <th scope="col" className={`${TH} pl-0 text-left`}>
                  Series
                </th>
                <th scope="col" className={`${TH} text-right`}>
                  Slope
                </th>
                <th scope="col" className={`${TH} text-right`}>
                  90% interval
                </th>
                <th scope="col" className={`${TH} text-right`}>
                  R&sup2;
                </th>
                <th scope="col" className={`${TH} text-right`}>
                  Points
                </th>
                <th scope="col" className={`${TH} pr-0 text-left`}>
                  Reading
                </th>
              </tr>
            </thead>
            <tbody>
              <TrendRow label={`Rolling ${days}-day share, ${pool}pool`} t={data.trend} />
              {data.trend_ex_relay ? <TrendRow label={`Rolling ${days}-day share, Relay excluded`} t={data.trend_ex_relay} /> : null}
              {otherRobustness.map((r) => (
                <TrendRow
                  key={r.key}
                  label={
                    <>
                      Rolling {days}-day share, {r.label.charAt(0).toLowerCase() + r.label.slice(1)}
                      <div className="text-[12px] text-dim">
                        share {fmtPct(r.share_now, { decimals: 1 })} now against {fmtPct(r.share_window_start, { decimals: 1 })} at the start
                      </div>
                    </>
                  }
                  t={r.trend}
                />
              ))}
              {data.trend_daily_cross_check ? <TrendRow label="Daily share, no overlap (cross-check)" t={data.trend_daily_cross_check} /> : null}
            </tbody>
          </table>
        </div>
      </Card>

      {data.read ? <p className="max-w-3xl border-l-2 border-border-strong pl-4 text-[15px] leading-relaxed text-ink">{data.read}</p> : null}

      <MethodNote summary={`What each adapter counts as fees (${fmtInt(protocols.length)} DefiLlama adapters)`}>
        <dl className="space-y-2.5">
          {protocols.map((p: FeePoolProtocol) => {
            const url = httpsUrl(p.methodology_url);
            return (
              <div key={p.slug}>
                <dt className="text-ink">
                  {p.name} <code>{p.slug}</code>
                </dt>
                <dd>
                  {p.methodology_fees ?? "The adapter publishes no fee definition."}{" "}
                  <span className="tnum text-dim">
                    {fmtInt(p.n_days)} days from {p.first_day ?? "n/a"}
                    {p.sha256 ? `; payload sha256 ${fmtHash(p.sha256, 10)}` : ""}
                    {url ? "; " : ""}
                  </span>
                  {url ? (
                    <a href={url} target="_blank" rel="noreferrer" className={LINK}>
                      adapter source
                    </a>
                  ) : null}
                </dd>
              </div>
            );
          })}
        </dl>
      </MethodNote>

      <MethodNote summary="Method, window and limits">
        <p>
          <span className="text-ink">Source.</span> <code>GET https://api.llama.fi/summary/fees/&lt;slug&gt;?dataType=dailyFees</code> for {protocols.map((p) => p.slug).join(", ")}; snapshot section <code>fee_pool_share</code>
          {data.fetched_at_utc ? `, fetched ${fmtUtc(data.fetched_at_utc)}` : ""}.
        </p>
        {w ? (
          <p>
            <span className="text-ink">Window.</span> {w.start} to {w.end}, {fmtInt(w.n_days)} days{w.limited_by_name ? `, starting on ${w.limited_by_name}'s first day` : ""}. {w.rule ? `Rule: ${w.rule}.` : ""}
            {w.excluded_trailing_days.length ? ` Excluded: ${w.excluded_trailing_days.map((d) => `${d.date} (${d.reason})`).join("; ")}.` : ""}
          </p>
        ) : null}
        {data.trend?.method ? (
          <p>
            <span className="text-ink">Trend.</span> {data.trend.method}.
          </p>
        ) : null}
        {(data.caveats ?? []).map((c, i) => (
          <p key={i}>
            <span className="text-ink">Limit {i + 1}.</span> {withCode(c)}
          </p>
        ))}
        {data.unavailable?.length ? (
          <p>
            <span className="text-ink">Not included.</span> {data.unavailable.map((u) => `${u.name} (${u.reason})`).join("; ")}.
          </p>
        ) : null}
        {data.warnings?.length ? (
          <p>
            <span className="text-ink">Collector warnings.</span> {data.warnings.join("; ")}.
          </p>
        ) : null}
      </MethodNote>
    </section>
  );
}
