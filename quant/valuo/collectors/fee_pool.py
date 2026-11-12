"""Fee-pool share: NEAR Intents' share of the fees paid to six cross-chain routers, and whether it is moving.

Question: is NEAR Intents gaining or losing share of cross-chain routing fees against Relay, Across, deBridge,
Chainflip and THORChain? The execution benchmark compares quotes; this module compares who collects the money.

Data: DefiLlama ``GET /summary/fees/<slug>?dataType=dailyFees`` (key-free), one call per protocol, each recorded in
the ``ProvenanceLedger`` as ``defillama / fee_pool:<slug>:dailyFees``. Fields read: ``name``, ``total30d``,
``totalDataChart`` ([[unix_s, usd], ...]), ``methodology.Fees`` (or the child protocols' when the slug is a parent).

THORChain uses the slug ``thorchain-dex`` (swap, outbound and affiliate fees). The slug ``thorchain`` is DefiLlama's
chain adapter: it reports only the 0.02 RUNE native transaction fee, which is not a routing fee.

Method (``build_fee_pool``, pure, no network):

    series_p        = daily fees of protocol p, leading zero days trimmed, rows with a non-finite or negative value skipped
    provisional     = each series' newest point and any day dated today (UTC): DefiLlama updates the newest day intraday
    window          = days from max_p(first day) to min_p(last settled day) on which every included protocol has a point;
                      a trailing day that is zero or missing for any protocol is cut as well (at most MAX_TRAILING_CUT)
    fees30_p(t)     = sum of series_p over the 30 window days ending at t
    share(t)        = fees30_NI(t) / sum_p fees30_p(t)
    share_ex_relay  = the same with Relay left out of the denominator (Relay's adapter counts integrator app fees)
    trend           = OLS of share (percentage points) on time (30-day units) over the rolling points, Newey-West
                      standard error with HAC_LAG_DAYS Bartlett lags, 90% interval = slope +/- Z90 * se

A protocol whose fetch fails, whose payload has no usable chart, or whose series ends more than STALE_DAYS before the
freshest one is listed under ``unavailable`` with the reason and the share is computed over the rest.

Limits, all repeated in ``caveats``:
- Fee share is not volume share. DefiLlama's bridge-volume API is paid, so no volume-side comparison is made.
- Each adapter defines "fees" differently (the adapter text is carried per protocol), so the pool sums unlike quantities.
- The common window is as short as the youngest series (Relay); the trend is a few months of data, not a cycle.
- Routers outside DefiLlama's fee coverage (LI.FI and others) are absent, so "the pool" is these protocols only.
- Rolling 30-day points overlap by 29 days. The HAC lag is twice the rolling window to cover that; the daily,
  non-overlapping share trend is reported next to it as a cross-check.
- A linear trend summarises a path that need not be linear; R^2, the low and the high of the share are published with it.
- A run of zero-fee days inside the window is kept as reported; a protocol with a run of ZERO_RUN_DAYS or more is
  flagged and a robustness share excluding it is published, since the run may be an adapter gap.
"""
from __future__ import annotations

import asyncio
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from valuo import config
from valuo.models.volume_growth import Z90, _ols_hac
from valuo.provenance import ProvenanceLedger, fetch_json, utc_now_iso

__all__ = [
    "PROTOCOLS", "FOCUS_SLUG", "ROLLING_DAYS", "HAC_LAG_DAYS", "build_fee_pool", "collect_fee_pool", "scorecard_claim",
    "memo_markdown", "parse_daily_fees", "fees_methodology",
]


@dataclass(frozen=True)
class ProtocolSpec:
    slug: str
    label: str


FOCUS_SLUG = "near-intents"
RELAY_SLUG = "relay"
PROTOCOLS: tuple[ProtocolSpec, ...] = (
    ProtocolSpec(FOCUS_SLUG, "NEAR Intents"),
    ProtocolSpec(RELAY_SLUG, "Relay"),
    ProtocolSpec("across", "Across"),
    ProtocolSpec("debridge", "deBridge"),
    ProtocolSpec("chainflip", "Chainflip"),
    ProtocolSpec("thorchain-dex", "THORChain"),  # not "thorchain": that slug is the chain's native tx fee only
)
DATA_TYPE = "dailyFees"
SOURCE = "defillama"
ROLLING_DAYS = 30
HAC_LAG_DAYS = 60  # 2 x ROLLING_DAYS: Bartlett weights at lag 30 would halve the weight on overlap-induced autocorrelation
DAILY_HAC_LAG_DAYS = 30
TREND_MIN_POINTS = 60
STALE_DAYS = 7
MAX_TRAILING_CUT = 7
ZERO_RUN_DAYS = 7
SURGE_MULTIPLE = 5.0  # a competitor whose peak 30-day fees are this many times its window median gets a caveat
_CONCURRENCY = 3  # api.llama.fi is shared with comps and forensics in the same run
_DAY_S = 86400
_COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}


# ----------------------------------------------------------------------------- payload parsing
def _record_name(slug: str) -> str:
    return f"fee_pool:{slug}:{DATA_TYPE}"


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def _iso(day: int) -> str:
    return (date(1970, 1, 1) + timedelta(days=day)).isoformat()


def parse_daily_fees(payload: Any) -> tuple[dict[int, float], int]:
    """``totalDataChart`` -> ({days since epoch (UTC): usd}, rows skipped as malformed).

    A row is skipped when it is not a pair, its timestamp is not a finite number or its value is non-finite or
    negative. Two rows on one UTC day keep the later one (the earlier counts as skipped).
    """
    chart = payload.get("totalDataChart") if isinstance(payload, Mapping) else None
    out: dict[int, float] = {}
    skipped = 0
    if not isinstance(chart, list):
        return out, skipped
    for row in chart:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            skipped += 1
            continue
        ts, val = _finite(row[0]), _finite(row[1])
        if ts is None or val is None or ts < 0 or val < 0:
            skipped += 1
            continue
        day = int(ts // _DAY_S)
        if day in out:
            skipped += 1
        out[day] = val
    return out, skipped


def fees_methodology(payload: Any) -> str | None:
    """The adapter's own definition of "Fees": ``methodology.Fees``, else the child protocols' joined, else None."""
    if not isinstance(payload, Mapping):
        return None
    meth = payload.get("methodology")
    if isinstance(meth, Mapping) and isinstance(meth.get("Fees"), str) and meth["Fees"].strip():
        return meth["Fees"].strip()
    parts: list[str] = []
    children = payload.get("childProtocols")
    for child in children if isinstance(children, list) else []:
        cm = child.get("methodology") if isinstance(child, Mapping) else None
        if isinstance(cm, Mapping) and isinstance(cm.get("Fees"), str) and cm["Fees"].strip():
            name = child.get("displayName") or child.get("name")
            parts.append(f"{name}: {cm['Fees'].strip()}" if isinstance(name, str) and name else cm["Fees"].strip())
    return " / ".join(parts) or None


def _longest_zero_run(values: Sequence[float]) -> tuple[int, int | None]:
    """(length, start index) of the longest run of zero values; (0, None) when there is none."""
    best, best_start, run = 0, None, 0
    for i, v in enumerate(values):
        run = run + 1 if v <= 0 else 0
        if run > best:
            best, best_start = run, i - run + 1
    return best, best_start


# ----------------------------------------------------------------------------- maths
def _trend(dates: Sequence[int], shares: Sequence[float | None], lag: int, basis: str) -> dict[str, Any]:
    """Linear trend of a share series in percentage points per 30 days with a Newey-West 90% interval."""
    pts = [(d, s) for d, s in zip(dates, shares) if s is not None]
    out: dict[str, Any] = {
        "status": "insufficient_data", "basis": basis, "n_points": len(pts), "hac_lag_days": lag,
        "slope_pp_per_30d": None, "se_pp_per_30d": None, "ci90_pp_per_30d": None, "excludes_zero": None, "direction": None, "r2": None,
        "method": (f"OLS of {basis} (percentage points) on time; slope per 30 days; 90% interval = slope +/- {Z90:.3f} x "
                   f"Newey-West standard error with {lag} Bartlett lags"),
    }
    if len(pts) < TREND_MIN_POINTS:
        out["note"] = f"{len(pts)} points; at least {TREND_MIN_POINTS} needed"
        return out
    xs = [(d - pts[0][0]) / 30.0 for d, _ in pts]
    ys = [s * 100.0 for _, s in pts]
    if max(ys) - min(ys) < 1e-12:  # a constant share: slope 0 by construction, no interval to estimate
        out.update({"status": "measured", "slope_pp_per_30d": 0.0, "se_pp_per_30d": 0.0, "ci90_pp_per_30d": [0.0, 0.0],
                    "excludes_zero": False, "direction": "flat", "first_day": _iso(pts[0][0]), "last_day": _iso(pts[-1][0])})
        return out
    a, b, se = _ols_hac(xs, ys, lag)
    my = sum(ys) / len(ys)
    sst = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - sum((y - a - b * x) ** 2 for x, y in zip(xs, ys)) / sst
    lo, hi = b - Z90 * se, b + Z90 * se
    excludes = lo > 0 or hi < 0
    out.update({
        "status": "measured", "slope_pp_per_30d": b, "se_pp_per_30d": se, "ci90_pp_per_30d": [lo, hi],
        "excludes_zero": excludes, "direction": ("rising" if lo > 0 else "falling") if excludes else "flat", "r2": r2,
        "first_day": _iso(pts[0][0]), "last_day": _iso(pts[-1][0]),
    })
    return out


def _rolling(values: Sequence[float], k: int) -> list[float]:
    """Trailing k-point sums, one per index from k-1 on."""
    out: list[float] = []
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= k:
            acc -= values[i - k]
        if i >= k - 1:
            out.append(max(acc, 0.0))
    return out


def _share_series(roll: Mapping[str, Sequence[float]], pool: Sequence[str], n: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(n):
        total = sum(roll[s][i] for s in pool)
        out.append(roll[FOCUS_SLUG][i] / total if total > 0 else None)
    return out


def _readout(dates: Sequence[int], shares: Sequence[float | None]) -> dict[str, Any]:
    """Share at the last rolling point, 30 and 90 days before it, and at the first rolling point."""
    by_day = dict(zip(dates, shares))
    last = dates[-1]

    def at(day: int) -> dict[str, Any] | None:
        return {"date": _iso(day), "share": by_day[day]} if by_day.get(day) is not None else None

    now, d30, d90, start = at(last), at(last - 30), at(last - 90), at(dates[0])
    seen = [(s, d) for d, s in zip(dates, shares) if s is not None]
    low, high = (min(seen), max(seen)) if seen else (None, None)

    def change(ref: dict[str, Any] | None) -> float | None:
        return (now["share"] - ref["share"]) * 100.0 if now and ref else None

    return {
        "now": now, "d30_ago": d30, "d90_ago": d90, "window_start": start,
        "low": {"date": _iso(low[1]), "share": low[0]} if low else None, "high": {"date": _iso(high[1]), "share": high[0]} if high else None,
        "change_pp_30d": change(d30), "change_pp_90d": change(d90), "change_pp_window": change(start),
        "days_start_to_now": last - dates[0],
    }


def _pct(x: float | None, decimals: int = 1) -> str:
    return "n/a" if x is None else f"{x * 100:.{decimals}f}%"


def _usd(x: float | None) -> str:
    if x is None:
        return "n/a"
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.2f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:,.1f}K"
    return f"${x:,.0f}"


def _trend_txt(tr: Mapping[str, Any]) -> str:
    if tr.get("status") != "measured":
        return "trend not estimated (" + str(tr.get("note") or "insufficient data") + ")"
    lo, hi = tr["ci90_pp_per_30d"]
    return f"{tr['slope_pp_per_30d']:+.2f} pp per 30 days, 90% interval {lo:+.2f} to {hi:+.2f}"


def _empty(status: str, unavailable: list[dict[str, str]], warnings: list[str], note: str) -> dict[str, Any]:
    return {
        "status": status, "note": note, "source": f"{SOURCE}: summary/fees/<slug>?dataType={DATA_TYPE}", "focus_slug": FOCUS_SLUG,
        "requested": [p.slug for p in PROTOCOLS], "included": [], "unavailable": unavailable, "protocols": [], "window": None,
        "rolling": None, "share": None, "share_ex_relay": None, "rank": None, "trend": None, "trend_ex_relay": None,
        "trend_daily_cross_check": None, "robustness": [], "headline": f"Fee-pool share not measured: {note}",
        "read": None, "caveats": [], "warnings": warnings,
    }


def build_fee_pool(
    charts: Mapping[str, Any],
    *,
    records: Mapping[str, Mapping[str, Any]] | None = None,
    failures: Mapping[str, str] | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Shares, ranks and the share trend from DefiLlama fee summaries keyed by slug. Pure: no network, no clock when ``as_of`` is given.

    ``charts[slug]`` is the parsed summary payload (None or absent when the fetch failed; ``failures[slug]`` then carries the
    reason). ``records[slug]`` may carry ``record`` / ``sha256`` / ``fetched_at_utc`` for provenance. ``status`` is
    "measured", "insufficient_data" (common window shorter than the rolling window) or "unavailable" (no NEAR Intents series
    or no competitor).
    """
    records, failures = records or {}, failures or {}
    today = ((as_of or datetime.now(timezone.utc).date()) - date(1970, 1, 1)).days
    warnings: list[str] = []
    unavailable: list[dict[str, str]] = []
    label = {p.slug: p.label for p in PROTOCOLS}
    series: dict[str, dict[int, float]] = {}
    meta: dict[str, dict[str, Any]] = {}
    newest: dict[str, int] = {}

    def drop(slug: str, reason: str) -> None:
        unavailable.append({"slug": slug, "name": label[slug], "reason": reason})
        warnings.append(f"{slug} left out of the fee pool: {reason}")

    for spec in PROTOCOLS:
        payload = charts.get(spec.slug)
        if not isinstance(payload, Mapping):
            drop(spec.slug, failures.get(spec.slug) or "no payload")
            continue
        days, skipped = parse_daily_fees(payload)
        if skipped:
            warnings.append(f"{spec.slug}: {skipped} malformed, negative or duplicate chart rows skipped")
        positive = [d for d, v in days.items() if v > 0]
        if not positive:
            drop(spec.slug, "payload has no positive daily fee point")
            continue
        first = min(positive)
        days = {d: v for d, v in days.items() if d >= first}
        newest[spec.slug] = max(days)
        settled = {d: v for d, v in days.items() if d < newest[spec.slug] and d < today}
        if not settled:
            drop(spec.slug, "no settled day (only a provisional newest point)")
            continue
        series[spec.slug] = settled
        name = payload.get("name")
        rec = records.get(spec.slug) or {}
        meta[spec.slug] = {
            "slug": spec.slug, "name": name if isinstance(name, str) and name else spec.label, "label": spec.label,
            "category": payload.get("category") if isinstance(payload.get("category"), str) else None,
            "first_day": _iso(first), "last_day": _iso(max(settled)), "newest_point_day": _iso(newest[spec.slug]),
            "n_days": len(settled), "defillama_total30d": _finite(payload.get("total30d")),
            "methodology_fees": fees_methodology(payload),
            "methodology_url": payload.get("methodologyURL") if isinstance(payload.get("methodologyURL"), str) else None,
            "record": rec.get("record"), "sha256": rec.get("sha256"), "fetched_at_utc": rec.get("fetched_at_utc"),
        }

    # A series that stopped updating would end the window early for every protocol: leave it out instead.
    if series:
        freshest = max(max(s) for s in series.values())
        for slug in [s for s in series if max(series[s]) < freshest - STALE_DAYS]:
            drop(slug, f"stale: last settled day {_iso(max(series[slug]))} is {freshest - max(series[slug])} days behind {_iso(freshest)}")
            del series[slug], meta[slug]

    if FOCUS_SLUG not in series:
        return _empty("unavailable", unavailable, warnings, "no usable NEAR Intents fee series")
    if len(series) < 2:
        return _empty("unavailable", unavailable, warnings, "no competitor fee series available")

    included = [p.slug for p in PROTOCOLS if p.slug in series]
    start = max(min(series[s]) for s in included)
    end = min(max(series[s]) for s in included)
    excluded: list[dict[str, str]] = []
    cut = 0
    while end >= start and cut < MAX_TRAILING_CUT:
        bad = [s for s in included if series[s].get(end, 0.0) <= 0]
        if not bad:
            break
        excluded.append({"date": _iso(end), "reason": "zero or missing for " + ", ".join(bad)})
        end -= 1
        cut += 1
    last_point = max(newest[s] for s in included)
    for day in range(end + 1 + cut, last_point + 1):
        prov = [s for s in included if newest[s] == day]
        absent = [s for s in included if day not in series[s] and newest[s] != day]
        why = []
        if day >= today:
            why.append("dated today (UTC), partial")
        if prov:
            why.append("provisional newest point of " + ", ".join(prov))
        if absent:
            why.append("not yet published for " + ", ".join(absent))
        excluded.append({"date": _iso(day), "reason": "; ".join(why) or "after the last day settled for every protocol"})
    excluded.sort(key=lambda e: e["date"])

    window_days = [d for d in range(start, end + 1) if all(d in series[s] for s in included)]
    missing = (end - start + 1 - len(window_days)) if end >= start else 0
    if missing:
        warnings.append(f"{missing} calendar days inside the common window lack a point for some protocol and are skipped")
    limiting = max(included, key=lambda s: min(series[s]))
    window = {
        "start": _iso(start) if window_days else None, "end": _iso(end) if window_days else None, "n_days": len(window_days),
        "missing_days": missing, "limited_by": limiting, "limited_by_name": meta[limiting]["name"],
        "excluded_trailing_days": excluded,
        "rule": ("days from the latest first day to the earliest last settled day on which every included protocol has a point; "
                 "each series' newest point and any day dated today (UTC) are provisional and left out; a trailing day that is "
                 "zero or missing for any protocol is cut"),
    }
    pool_word = _COUNT_WORDS.get(len(included), str(len(included)))
    base = {
        "source": f"{SOURCE}: summary/fees/<slug>?dataType={DATA_TYPE}", "focus_slug": FOCUS_SLUG,
        "requested": [p.slug for p in PROTOCOLS], "included": included, "unavailable": unavailable, "window": window,
        "pool_label": f"{pool_word}-protocol", "rolling_days": ROLLING_DAYS,
    }
    if len(window_days) < ROLLING_DAYS:
        out = _empty("insufficient_data", unavailable, warnings,
                     f"common window is {len(window_days)} days; {ROLLING_DAYS} needed for one rolling point")
        out.update(base)
        return out

    daily = {s: [series[s][d] for d in window_days] for s in included}
    roll = {s: _rolling(daily[s], ROLLING_DAYS) for s in included}
    roll_days = window_days[ROLLING_DAYS - 1:]
    n = len(roll_days)
    share = _share_series(roll, included, n)
    ex_relay_pool = [s for s in included if s != RELAY_SLUG]
    has_relay = RELAY_SLUG in included and len(ex_relay_pool) >= 2
    share_ex = _share_series(roll, ex_relay_pool, n) if has_relay else [None] * n
    pool_usd = [sum(roll[s][i] for s in included) for i in range(n)]
    rows = [
        [_iso(roll_days[i]), None if share[i] is None else round(share[i], 6), None if share_ex[i] is None else round(share_ex[i], 6),
         round(pool_usd[i], 2), *(round(roll[s][i], 2) for s in included)]
        for i in range(n)
    ]

    # per-protocol table, ranked by aligned 30-day fees
    fees30 = {s: roll[s][-1] for s in included}
    pool30 = sum(fees30.values())
    order = sorted(included, key=lambda s: (-fees30[s], s))
    protocols: list[dict[str, Any]] = []
    for rank, slug in enumerate(order, start=1):
        zeros = sum(1 for v in daily[slug] if v <= 0)
        run, run_at = _longest_zero_run(daily[slug])
        peak_i = max(range(n), key=lambda i: roll[slug][i])
        protocols.append({
            **meta[slug], "rank_30d": rank, "fees_30d_usd": fees30[slug],
            "fees_90d_usd": sum(daily[slug][-90:]) if len(window_days) >= 90 else None,
            "share_30d": fees30[slug] / pool30 if pool30 > 0 else None,
            "fees_30d_window_start_usd": roll[slug][0], "fees_30d_peak_usd": roll[slug][peak_i], "fees_30d_peak_date": _iso(roll_days[peak_i]),
            "fees_30d_median_usd": sorted(roll[slug])[n // 2],
            "n_days_in_window": len(window_days), "zero_days_in_window": zeros, "longest_zero_run_days": run,
            "zero_run_start": _iso(window_days[run_at]) if run_at is not None else None,
            "zero_run_end": _iso(window_days[run_at + run - 1]) if run_at is not None else None,
        })
    by_slug = {p["slug"]: p for p in protocols}
    ni = by_slug[FOCUS_SLUG]
    leader = protocols[0]
    other = protocols[1] if leader["slug"] == FOCUS_SLUG else leader
    rank = {
        "near_intents": ni["rank_30d"], "of": len(included),
        "leader": {"slug": leader["slug"], "name": leader["name"], "share_30d": leader["share_30d"], "fees_30d_usd": leader["fees_30d_usd"]},
        "reference": {"slug": other["slug"], "name": other["name"], "share_30d": other["share_30d"], "fees_30d_usd": other["fees_30d_usd"],
                      "relation": "ahead of" if leader["slug"] == FOCUS_SLUG else "behind"},
    }

    read = _readout(roll_days, share)
    read_ex = _readout(roll_days, share_ex) if has_relay else None
    trend = _trend(roll_days, share, HAC_LAG_DAYS, f"rolling {ROLLING_DAYS}-day share")
    trend_ex = _trend(roll_days, share_ex, HAC_LAG_DAYS, f"rolling {ROLLING_DAYS}-day share ex-Relay") if has_relay else None
    daily_share: list[float | None] = []
    for i in range(len(window_days)):
        total = sum(daily[s][i] for s in included)
        daily_share.append(daily[FOCUS_SLUG][i] / total if total > 0 else None)
    trend_daily = _trend(window_days, daily_share, DAILY_HAC_LAG_DAYS, "daily share (no overlap)")

    # robustness pools: ex-Relay (adapter scope) and ex any protocol with a long zero run (possible adapter gap)
    robustness: list[dict[str, Any]] = []

    def add_robust(key: str, text: str, excl: list[str]) -> None:
        pool = [s for s in included if s not in excl]
        if FOCUS_SLUG in excl or len(pool) < 2:
            return
        sh = _share_series(roll, pool, n)
        ro = _readout(roll_days, sh)
        robustness.append({
            "key": key, "label": text, "excluded": excl, "share_now": (ro["now"] or {}).get("share"),
            "share_window_start": (ro["window_start"] or {}).get("share"), "change_pp_window": ro["change_pp_window"],
            "trend": _trend(roll_days, sh, HAC_LAG_DAYS, f"rolling {ROLLING_DAYS}-day share, {text}"),
        })

    if has_relay:
        add_robust("ex_relay", "Relay excluded", [RELAY_SLUG])
    gappy = [s for s in included if s != FOCUS_SLUG and by_slug[s]["longest_zero_run_days"] >= ZERO_RUN_DAYS]
    if gappy:
        add_robust("ex_zero_run", "excluding " + ", ".join(by_slug[s]["name"] for s in gappy) + " (zero-fee run in the window)", gappy)

    # ------------------------------------------------------------------ prose
    now_s, start_s = (read["now"] or {}).get("share"), (read["window_start"] or {}).get("share")
    if trend["status"] == "measured":
        lo, hi = trend["ci90_pp_per_30d"]
        verdict = (f"the linear trend ({trend['slope_pp_per_30d']:+.2f} pp per 30 days, 90% interval {lo:+.2f} to {hi:+.2f}) is "
                   + ("not distinguishable from flat" if trend["direction"] == "flat" else f"{trend['direction']}, with the interval excluding zero"))
    else:
        verdict = "the window is too short to estimate a trend"
    headline = (
        f"NEAR Intents takes {_pct(ni['share_30d'])} of the {pool_word}-protocol cross-chain fee pool over the 30 days to {window['end']}, "
        f"rank {ni['rank_30d']} of {len(included)} {rank['reference']['relation']} {rank['reference']['name']} at {_pct(rank['reference']['share_30d'])}; "
        f"its rolling 30-day share moved from {_pct(start_s)} to {_pct(now_s)} over {read['days_start_to_now']} days "
        f"(low {_pct(read['low']['share'])} on {read['low']['date']}, high {_pct(read['high']['share'])} on {read['high']['date']}) and {verdict}."
    )
    direction = trend.get("direction")
    if direction == "rising":
        read_txt = ("Supports the bull case on this measure: NEAR Intents is taking a growing share of the fees these routers collect. "
                    "It is overturned if the share trend's 90% interval comes to include zero or the share falls back below its level "
                    f"at the start of the window ({_pct(start_s)}).")
    elif direction == "falling":
        read_txt = ("Cuts against the bull case: NEAR Intents is losing share of the fees these routers collect, so fee growth has to come "
                    "from the pool growing, not from share capture. It is overturned by a positive share trend whose 90% interval excludes zero.")
    else:
        read_txt = ("Neither a share gain nor a share loss is shown, so the thesis cannot claim NEAR Intents is winning the fee pool; "
                    "its fee growth has to come from the pool growing. A share trend whose 90% interval excludes zero, in either direction, "
                    "would change this reading.")
    if rank["near_intents"] > 1:
        read_txt += f" {leader['name']} collects {leader['fees_30d_usd'] / max(ni['fees_30d_usd'], 1e-9):.1f}x NEAR Intents' fees under its own adapter's definition."
    read_txt += (f" NEAR Intents' own 30-day fees went from {_usd(ni['fees_30d_window_start_usd'])} to {_usd(ni['fees_30d_usd'])} over the window; "
                 f"the pool went from {_usd(pool_usd[0])} to {_usd(pool_usd[-1])}.")
    if read_ex and trend_ex and trend_ex["status"] == "measured":
        read_txt += (f" With Relay excluded the share is {_pct((read_ex['now'] or {}).get('share'))} against "
                     f"{_pct((read_ex['window_start'] or {}).get('share'))} at the start of the window ({_trend_txt(trend_ex)}).")

    caveats = [
        "Fee share is not volume share: a router charging more per dollar routed has a larger fee share at the same volume. "
        "DefiLlama's bridge-volume API is paid, so no volume-side comparison is made here.",
        "Adapter fee definitions differ, so the pool sums unlike quantities; each adapter's own text is quoted next to its protocol "
        "(`protocols[].methodology_fees`). The ex-Relay share is published because Relay's adapter counts integrator app fees and swap costs.",
        f"The common window is {window['n_days']} days ({window['start']} to {window['end']}), set by {window['limited_by_name']}'s first day; "
        "the trend describes these months only.",
        "Routers outside DefiLlama's fee coverage (LI.FI and other aggregators) are absent, so the pool is these "
        f"{pool_word} protocols, not the cross-chain market.",
        f"Rolling 30-day points overlap by 29 days; the interval uses a Newey-West error with {HAC_LAG_DAYS} lags, and the daily "
        "non-overlapping share trend is reported as a cross-check.",
        "THORChain is measured by DefiLlama's `thorchain-dex` adapter (swap, outbound and affiliate fees); the `thorchain` slug is the "
        "chain's native transaction fee and is not a routing fee.",
    ]
    if trend["status"] == "measured" and trend["r2"] is not None:
        caveats.append(
            f"The share path is not a line: it ranged from {_pct(read['low']['share'])} ({read['low']['date']}) to {_pct(read['high']['share'])} "
            f"({read['high']['date']}) and the linear trend explains {trend['r2']:.0%} of its variance. Read the slope as the average drift "
            "over the window, not as a forecast.")
    for p in protocols:
        if p["slug"] != FOCUS_SLUG and p["fees_30d_median_usd"] > 0 and p["fees_30d_peak_usd"] >= SURGE_MULTIPLE * p["fees_30d_median_usd"]:
            caveats.append(
                f"{p['name']}'s 30-day fees peaked at {_usd(p['fees_30d_peak_usd'])} on {p['fees_30d_peak_date']}, "
                f"{p['fees_30d_peak_usd'] / p['fees_30d_median_usd']:.1f}x its window median of {_usd(p['fees_30d_median_usd'])}. NEAR Intents' share "
                "around that date moves with that surge in the denominator, not with a change in its own fees. Whether the surge is "
                "user-paid routing fees or an adapter artefact cannot be settled from this endpoint.")
    for slug in gappy:
        p = by_slug[slug]
        caveats.append(
            f"{p['name']} reports zero fees on {p['zero_days_in_window']} days of the window (longest run {p['longest_zero_run_days']} days, "
            f"{p['zero_run_start']} to {p['zero_run_end']}). The zeros are kept as reported; if they are an adapter gap, the other "
            "protocols' shares are overstated for rolling windows that include those days. See the robustness share excluding it.")
    if unavailable:
        caveats.append("Left out of this run: " + "; ".join(f"{u['name']} ({u['reason']})" for u in unavailable)
                       + f". Shares are over the remaining {pool_word} protocols.")

    return {
        "status": "measured", **base,
        "protocols": protocols,
        "pool_30d_usd": pool30,
        "rolling": {"window_days": ROLLING_DAYS, "columns": ["date", "share", "share_ex_relay", "pool_30d_usd", *included], "rows": rows},
        "share": read, "share_ex_relay": read_ex, "rank": rank,
        "trend": trend, "trend_ex_relay": trend_ex, "trend_daily_cross_check": trend_daily, "robustness": robustness,
        "headline": headline, "read": read_txt, "caveats": caveats, "warnings": warnings,
    }


# ----------------------------------------------------------------------------- live collection
async def collect_fee_pool(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, args: Any = None, log: Any = None, events: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Fetch the six fee summaries through the ledger and build the fee-pool view (EXTRA_COLLECTORS signature).

    Starts immediately (no quote venue, no NearBlocks). A failed slug is a warning and an ``unavailable`` entry; the
    function returns a dict in every case so the reason is visible in the snapshot.
    """
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def one(slug: str) -> tuple[str, Any, Any]:
        async with sem:
            parsed, record = await fetch_json(
                client, ledger, source=SOURCE, name=_record_name(slug), method="GET",
                url=f"{config.DEFILLAMA_API_BASE}/summary/fees/{slug}", params={"dataType": DATA_TYPE},
            )
        return slug, parsed, record

    results = await asyncio.gather(*(one(p.slug) for p in PROTOCOLS))
    charts: dict[str, Any] = {}
    records: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}
    for slug, parsed, record in results:
        records[slug] = {"record": f"{SOURCE}/{record.name}", "sha256": record.sha256, "fetched_at_utc": record.fetched_at_utc}
        if record.ok and isinstance(parsed, Mapping):
            charts[slug] = parsed
        else:
            failures[slug] = f"fetch failed ({record.error or f'HTTP {record.http_status}'})"[:200]
    out = build_fee_pool(charts, records=records, failures=failures)
    out["fetched_at_utc"] = utc_now_iso()
    for message in out.get("warnings") or []:
        ledger.warn(f"fee_pool: {message}")
    if out["status"] != "measured":
        ledger.warn(f"fee_pool: {out.get('note')}; fee_pool_share carries no share")
    if callable(log):
        log(f"fee_pool: status {out['status']}, {len(out['included'])} of {len(PROTOCOLS)} protocols, "
            f"NEAR Intents share {_pct(((out.get('share') or {}).get('now') or {}).get('share'))}")
    return out


# ----------------------------------------------------------------------------- scorecard + memo
def scorecard_claim(data: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Scorecard row. DERIVED only when the share trend is positive and its 90% interval excludes zero; else NOT_SUPPORTED."""
    if not isinstance(data, Mapping):
        return None
    claim = "NEAR Intents is gaining share of cross-chain routing fees"
    source = f"{SOURCE} summary/fees dailyFees: " + ", ".join(data.get("included") or data.get("requested") or [])
    note = ("Fee share, not volume share; adapter fee definitions differ; the pool is the protocols DefiLlama covers. "
            "A share trend is DERIVED from live fee series, never VERIFIED.")
    if data.get("status") != "measured":
        return {"claim": claim, "status": "NOT_SUPPORTED", "value": f"not measured: {data.get('note') or data.get('status')}",
                "source": source, "confidence": "none", "note": note}
    trend, share, rank, window = data["trend"], data["share"], data["rank"], data["window"]
    gaining = trend.get("status") == "measured" and trend.get("direction") == "rising"
    ref = rank["reference"]
    value = (
        f"{_pct((share.get('now') or {}).get('share'))} of the {data.get('pool_label')} fee pool (30 days to {window['end']}), "
        f"rank {rank['near_intents']} of {rank['of']} {ref['relation']} {ref['name']} at {_pct(ref['share_30d'])}; "
        f"share at window start {_pct((share.get('window_start') or {}).get('share'))} ({window['n_days']}-day common window); "
        f"trend {_trend_txt(trend)}"
    )
    ex = data.get("trend_ex_relay")
    if isinstance(ex, Mapping) and ex.get("status") == "measured":
        value += f"; ex-Relay {_pct(((data.get('share_ex_relay') or {}).get('now') or {}).get('share'))}, trend {_trend_txt(ex)}"
    if not gaining:
        value += " (share gain not shown)" if trend.get("direction") != "falling" else " (share is falling)"
    return {"claim": claim, "status": "DERIVED" if gaining else "NOT_SUPPORTED", "value": value, "source": source,
            "confidence": "medium" if gaining else "low", "note": note}


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], align: Sequence[str]) -> str:
    sep = ["---:" if a == "r" else ":---" for a in align]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    lines.append("")
    return "\n".join(lines)


def _short(text: str | None, limit: int = 150) -> str:
    if not text:
        return "not published by the adapter"
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def memo_markdown(data: Mapping[str, Any], snap_dict: Mapping[str, Any] | None = None) -> str:
    """Memo sub-section: headline, per-protocol table, share read-out, trend, caveats."""
    if data.get("status") != "measured":
        lines = [f"Not measured in this run: {data.get('note') or data.get('status')}."]
        if data.get("unavailable"):
            lines.append("Unavailable: " + "; ".join(f"{u['name']} ({u['reason']})" for u in data["unavailable"]) + ".")
        return "\n\n".join(lines)
    window, share, trend = data["window"], data["share"], data["trend"]
    parts = [f"**{data['headline']}**", data.get("read") or ""]
    parts.append(_md_table(
        ["Rank", "Protocol", "30d fees", "Share", "90d fees", "Days of data", "Fee definition (adapter text)"],
        [[p["rank_30d"], f"**{p['name']}**" if p["slug"] == FOCUS_SLUG else p["name"], _usd(p["fees_30d_usd"]), _pct(p["share_30d"]),
          _usd(p["fees_90d_usd"]), p["n_days"], _short(p.get("methodology_fees"))] for p in data["protocols"]],
        ["r", "l", "r", "r", "r", "r", "l"],
    ))
    ex = data.get("share_ex_relay") or {}

    def cell(block: Mapping[str, Any], key: str) -> str:
        pt = block.get(key)
        return f"{_pct(pt['share'])} ({pt['date']})" if pt else "n/a"

    rows = [["All included protocols", cell(share, "now"), cell(share, "d30_ago"), cell(share, "d90_ago"), cell(share, "window_start")]]
    if ex:
        rows.append(["Relay excluded", cell(ex, "now"), cell(ex, "d30_ago"), cell(ex, "d90_ago"), cell(ex, "window_start")])
    parts.append(_md_table(["NEAR Intents rolling 30d share", "Now", "30 days ago", "90 days ago", "Window start"], rows, ["l", "r", "r", "r", "r"]))
    trend_lines = [f"Trend of the rolling share: {_trend_txt(trend)} ({trend.get('n_points')} points, Newey-West {trend.get('hac_lag_days')} lags"
                   + (f", R^2 {trend['r2']:.2f}" if isinstance(trend.get("r2"), float) else "") + ")."]
    if isinstance(data.get("trend_ex_relay"), Mapping):
        trend_lines.append(f"Relay excluded: {_trend_txt(data['trend_ex_relay'])}.")
    if isinstance(data.get("trend_daily_cross_check"), Mapping):
        trend_lines.append(f"Daily share, no overlap: {_trend_txt(data['trend_daily_cross_check'])}.")
    for r in data.get("robustness") or []:
        if r.get("key") != "ex_relay":
            trend_lines.append(f"{r['label'][:1].upper()}{r['label'][1:]}: share {_pct(r.get('share_now'))} now against {_pct(r.get('share_window_start'))} at window start, trend {_trend_txt(r['trend'])}.")
    parts.append(" ".join(trend_lines))
    excl = window.get("excluded_trailing_days") or []
    parts.append(
        f"Window: {window['start']} to {window['end']} ({window['n_days']} days common to all {len(data['included'])} protocols, set by "
        f"{window['limited_by_name']}'s first day)."
        + (f" Trailing days left out as not final: {', '.join(e['date'] for e in excl)}." if excl else "")
        + f" Source: DefiLlama `summary/fees/<slug>?dataType={DATA_TYPE}`; records `{SOURCE}/fee_pool:<slug>:{DATA_TYPE}` in the manifest."
    )
    parts.append("Limits:\n\n" + "\n".join(f"- {c}" for c in data.get("caveats") or []))
    return "\n\n".join(p for p in parts if p)
