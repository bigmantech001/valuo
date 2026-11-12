"""Take-rate compression series: has NEAR Intents' realized take (fees / volume) fallen as volume grew?

Inputs are the four DefiLlama daily charts every run already fetches and hashes (``artifacts/raw/``):
``fees/near-intents`` dailyFees (gross), dailyRevenue (net, NEAR's captured share), dailyHoldersRevenue (the part routed
to the buyback) and ``dexs/near-intents`` (volume). No new endpoint. When the raw directory is not available the model
falls back to the 365-day ``intents_forensics.fees.daily_series`` in the snapshot (no holders column, so holder take is
null there).

Method
  * Days are the inner join of the charts on the unix day stamp. The unsettled-tail rule is the collector's own
    (``intents_forensics.aligned_window_sums``): a point dated today (UTC) is partial and dropped, and up to
    ``MAX_UNSETTLED_TAIL_DAYS`` trailing days whose revenue exceeds fees are left out and listed.
  * Rolling take over ``ROLLING_DAYS`` consecutive days: sum(fees) / sum(volume) x 1e4 bps (gross), the same with
    revenue (net) and holders revenue (holder). A window that is not 30 consecutive calendar days is skipped.
  * Trend: OLS of ln(rolling gross take) on time in years; change per year = exp(slope) - 1; 90% interval from a
    Newey-West standard error with ``TREND_HAC_LAG_DAYS`` Bartlett lags. Consecutive rolling points share 29 of 30 days,
    so the lag is set to twice the window; plain OLS errors would be far too narrow. Reported for the trailing 365 days
    (the graded figure), the trailing 180 days (is it still going on?) and the full history. Two robustness reads sit next
    to the trailing-365d figure and are never used for grading: the same interval at other HAC lags, and an OLS on the
    non-overlapping 30-day windows only (about 13 points, Student-t interval).
  * Elasticity: OLS of ln(daily gross take) on ln(daily volume), Newey-West interval (``ELASTICITY_HAC_LAG_DAYS``).
    Days with zero fees or zero volume are dropped and counted.
  * Regime break: the first day with holders revenue > 0, read from the data, with the pooled take before and after.
  * Floor read: how many trailing-365d rolling points sat below the registry's ``public_take_floor_bps`` (gross) and
    ``bear_fee_race_trigger_net_take_bps`` (net), and the minimum reached.

Limits
  * The fee chart starts with a ramp from zero (mid-2025), so the full-history trend measures the fee switch being
    turned on, not competition. The trailing-365d figures are the ones to read.
  * "Fees" is DefiLlama's adapter definition (protocol fee plus the affiliate fee each frontend keeps); "revenue" is
    booked when NEAR is swept into the revenue wallets, so net take is lumpy and can exceed fees on single days.
  * Volume sits in the denominator of the daily take, so noise in volume biases the elasticity toward negative values.
  * A trend whose interval includes zero is "no decline detected at this sample size", not proof of a floor.
  * The Newey-West interval on overlapping rolling points under-covers (a trendless simulated series is flagged roughly three
    times as often as the nominal 10%; see the size test). It is the graded figure because a too-narrow interval can only
    fail the claim more often, never pass it; the non-overlapping check is published beside it as the stricter read.

Pure given its inputs: no network; the only file IO is reading the run's raw payloads in ``load_charts``.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from scipy.stats import t as student_t

from valuo import assumptions as A
from valuo.collectors.intents_forensics import MAX_UNSETTLED_TAIL_DAYS, _chart_points, _ts_date, aligned_window_sums
from valuo.models.volume_growth import HAC_LAG_DAYS, Z90, _ols_hac

__all__ = [
    "ROLLING_DAYS", "TREND_HAC_LAG_DAYS", "ELASTICITY_HAC_LAG_DAYS", "TRAILING_DAYS", "MIN_TREND_POINTS", "WINDOWS",
    "SERIES_COLUMNS", "CLAIM", "load_charts", "measure_take_rate_series", "run_take_rate_series", "scorecard_claim",
    "memo_markdown",
]

ROLLING_DAYS = 30
TREND_HAC_LAG_DAYS = 2 * ROLLING_DAYS          # rolling points overlap by 29 days: Bartlett weight at lag 29 is still ~0.5
ELASTICITY_HAC_LAG_DAYS = HAC_LAG_DAYS          # daily points, same lag as the volume-growth fit
TRAILING_DAYS = 365
RECENT_DAYS = 180
MIN_TREND_POINTS = 90
MIN_BLOCKS = 6
LAG_SENSITIVITY_DAYS: tuple[int, ...] = (30, 120)
DAY_S = 86_400
_SLOPE_EPS = 1e-9  # ln-units per year
# (label, days-ago end, days-ago start): the window covers settled days [n - start, n - end)
WINDOWS: tuple[tuple[str, int, int], ...] = (
    ("last 30d", 0, 30), ("30-60d ago", 30, 60), ("60-90d ago", 60, 90), ("150-180d ago", 150, 180), ("330-360d ago", 330, 360),
)
SERIES_COLUMNS = ["ts_unix_s", "gross_take_bps", "net_take_bps", "holder_take_bps", "avg_daily_volume_usd"]
FLOOR_KEY = "public_take_floor_bps"
TRIGGER_KEY = "bear_fee_race_trigger_net_take_bps"
CLAIM = "NEAR Intents' realized gross take rate is not trending to zero as volume grows"

# chart key -> (raw file name, manifest record "source/name")
RAW_FILES: dict[str, tuple[str, str]] = {
    "fees": ("defillama__fees_near-intents_dailyFees.json", "defillama/fees:near-intents:dailyFees"),
    "revenue": ("defillama__fees_near-intents_dailyRevenue.json", "defillama/fees:near-intents:dailyRevenue"),
    "holders": ("defillama__fees_near-intents_dailyHoldersRevenue.json", "defillama/fees:near-intents:dailyHoldersRevenue"),
    "volume": ("defillama__dexs_near-intents.json", "defillama/dexs:near-intents"),
}
CAVEATS: tuple[str, ...] = (
    "Early history mixes fee regimes: the DefiLlama fee chart ramps from zero in mid-2025 and net revenue is zero until the first "
    "sweep, so the full-history trend measures fees being switched on. Read the trailing-365d figures.",
    "Fees, revenue and holders revenue follow DefiLlama's near-intents adapter definitions: gross fees include the affiliate fee each "
    "frontend keeps; revenue is NEAR swept into the revenue wallets and is booked on the sweep day, so net take is lumpy and can "
    "exceed fees on single days. An adapter revision restates the whole series.",
    "Rolling 30-day points overlap (29 of 30 days shared), so about 12 independent observations sit in a year. A Newey-West "
    "interval on such points is too narrow at this sample size: in the seeded null simulation in quant/tests/test_take_rate_series.py "
    "a trendless series is flagged well above the nominal 10% of the time. The non-overlapping 30-day check (Student-t) stays near "
    "its nominal size and is the stricter read: treat a trend as established only when both intervals exclude zero. An interval "
    "that includes zero means no decline was detected, not that none exists.",
    "The elasticity regresses fees/volume on volume: noise in daily volume enters both sides and pushes the estimate negative.",
)


def _iso(ts: int) -> str:
    return _ts_date(ts).isoformat()


def _bps(num: float | None, den: float) -> float | None:
    return None if num is None or den <= 0 else num / den * 1e4


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None else round(x, nd)


# ----------------------------------------------------------------------------- loading
def load_charts(raw_dir: Path | None, snapshot: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], str, list[str]]:
    """(charts, sources, mode, warnings). ``charts`` maps fees / revenue / holders / volume to a ``totalDataChart`` list.

    mode "raw": the run's persisted DefiLlama payloads, each with its sha256 (holders is optional). mode
    "snapshot_fallback": the 365-day ``intents_forensics.fees.daily_series`` (no holders column).
    """
    warns: list[str] = []
    charts: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    if raw_dir is not None:
        for key, (fname, record) in RAW_FILES.items():
            path = Path(raw_dir) / fname
            if not path.is_file():
                warns.append(f"take_rate_series: raw/{fname} not found")
                continue
            data = path.read_bytes()
            try:
                payload = json.loads(data)
            except ValueError as exc:
                warns.append(f"take_rate_series: raw/{fname} is not JSON ({exc})")
                continue
            chart = payload.get("totalDataChart") if isinstance(payload, Mapping) else None
            if not isinstance(chart, list) or not chart:
                warns.append(f"take_rate_series: raw/{fname} has no totalDataChart")
                continue
            charts[key] = chart
            sources.append({"key": key, "record": record, "raw_path": f"raw/{fname}", "sha256": hashlib.sha256(data).hexdigest(), "rows": len(chart)})
        if all(k in charts for k in ("fees", "revenue", "volume")):
            return charts, sources, "raw", warns
        warns.append("take_rate_series: raw fee/revenue/volume payloads incomplete; using the snapshot's 365-day daily_series")
    fees = (snapshot.get("intents_forensics") or {}).get("fees") or {}
    series = fees.get("daily_series") or []
    cols = fees.get("daily_series_columns") or ["ts_unix_s", "fees_usd", "revenue_usd", "volume_usd"]
    try:
        it, i_f, i_r, i_v = (cols.index(c) for c in ("ts_unix_s", "fees_usd", "revenue_usd", "volume_usd"))
    except ValueError:
        warns.append(f"take_rate_series: daily_series_columns {cols} lacks a needed column")
        return {}, [], "snapshot_fallback", warns
    width = max(it, i_f, i_r, i_v) + 1
    rows = [r for r in series if isinstance(r, (list, tuple)) and len(r) >= width]
    if len(rows) != len(series):
        warns.append(f"take_rate_series: {len(series) - len(rows)} malformed daily_series row(s) skipped")
    charts = {
        "fees": [[r[it], r[i_f]] for r in rows], "revenue": [[r[it], r[i_r]] for r in rows], "volume": [[r[it], r[i_v]] for r in rows],
    }
    sources = [{"key": "fees,revenue,volume", "record": "snapshot:intents_forensics.fees.daily_series", "raw_path": None, "sha256": None, "rows": len(rows)}]
    return charts, sources, "snapshot_fallback", warns


def _threshold(snapshot: Mapping[str, Any], key: str) -> float:
    """The value the run recorded in ``snapshot.assumptions`` for ``key``, else the registry default."""
    for a in snapshot.get("assumptions") or []:
        if isinstance(a, Mapping) and a.get("key") == key:
            try:
                v = float(a.get("value"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                break
            if math.isfinite(v):
                return v
    return float(A.value(key))


# ----------------------------------------------------------------------------- statistics
def _log_trend(points: Sequence[tuple[int, float]], lag: int) -> dict[str, Any]:
    """OLS of ln(take) on years with a Newey-West 90% interval. ``points`` are (ts, take_bps) in time order."""
    pos = [(t, v) for t, v in points if v > 0]
    out: dict[str, Any] = {
        "status": "insufficient_data", "n_points": len(pos), "n_dropped_nonpositive": len(points) - len(pos), "hac_lag_days": lag,
        "first_day": _iso(pos[0][0]) if pos else None, "last_day": _iso(pos[-1][0]) if pos else None,
        "start_bps": pos[0][1] if pos else None, "end_bps": pos[-1][1] if pos else None,
        "log_slope_per_year": None, "log_slope_se_hac": None, "change_per_year_pct": None, "ci90_pct": None, "ci_excludes_zero": None,
        "direction": None,
    }
    if len(pos) < MIN_TREND_POINTS or pos[-1][0] == pos[0][0]:
        out["note"] = f"{len(pos)} positive rolling points; at least {MIN_TREND_POINTS} needed"
        return out
    xs = [(t - pos[0][0]) / DAY_S / 365.0 for t, _ in pos]
    ys = [math.log(v) for _, v in pos]
    _a, b, se = _ols_hac(xs, ys, lag)
    if abs(b) < _SLOPE_EPS:  # a flat series fits a slope of float-noise size; do not let its sign decide anything
        b = 0.0
    lo, hi = math.expm1(b - Z90 * se) * 100.0, math.expm1(b + Z90 * se) * 100.0
    excl = lo > 0.0 or hi < 0.0
    out.update({
        "status": "measured", "log_slope_per_year": b, "log_slope_se_hac": se, "change_per_year_pct": math.expm1(b) * 100.0,
        "ci90_pct": [lo, hi], "ci_excludes_zero": excl,
        "direction": ("falling" if hi < 0.0 else "rising") if excl else "no significant trend",
    })
    return out


def _block_trend(points: Sequence[tuple[int, float]]) -> dict[str, Any]:
    """Cross-check without overlap: OLS of ln(take) on years over every ``ROLLING_DAYS``-th rolling point counted back
    from the last one (disjoint windows), with a Student-t 90% interval on n - 2 degrees of freedom."""
    if not points:
        return {"status": "insufficient_data", "n_blocks": 0, "change_per_year_pct": None, "ci90_pct": None, "ci_excludes_zero": None}
    last = points[-1][0]
    blk = [(t, v) for t, v in points if (last - t) % (ROLLING_DAYS * DAY_S) == 0 and v > 0]
    out: dict[str, Any] = {
        "status": "insufficient_data", "n_blocks": len(blk), "change_per_year_pct": None, "ci90_pct": None, "ci_excludes_zero": None,
        "method": f"OLS of ln(take) on time over non-overlapping {ROLLING_DAYS}-day windows, Student-t 90% interval (n - 2 df)",
    }
    if len(blk) < MIN_BLOCKS:
        return out
    xs = [(t - blk[0][0]) / DAY_S / 365.0 for t, _ in blk]
    ys = [math.log(v) for _, v in blk]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    se = math.sqrt(sum((y - a - b * x) ** 2 for x, y in zip(xs, ys)) / (n - 2) / sxx)
    q = float(student_t.ppf(0.95, n - 2))
    lo, hi = math.expm1(b - q * se) * 100.0, math.expm1(b + q * se) * 100.0
    out.update({"status": "measured", "change_per_year_pct": math.expm1(b) * 100.0, "ci90_pct": [lo, hi], "ci_excludes_zero": lo > 0.0 or hi < 0.0})
    return out


def _elasticity(days: Sequence[tuple[int, float, float]], lag: int) -> dict[str, Any]:
    """OLS of ln(daily gross take) on ln(daily volume). ``days`` are (ts, fees, volume) in time order."""
    ok = [(t, f, v) for t, f, v in days if f > 0 and v > 0]
    out: dict[str, Any] = {
        "status": "insufficient_data", "n_days": len(ok), "n_dropped_zero_fee_or_volume": len(days) - len(ok), "hac_lag_days": lag,
        "first_day": _iso(ok[0][0]) if ok else None, "last_day": _iso(ok[-1][0]) if ok else None,
        "elasticity": None, "se_hac": None, "ci90": None, "ci_excludes_zero": None, "r2": None,
    }
    if len(ok) < MIN_TREND_POINTS:
        out["note"] = f"{len(ok)} days with fees and volume above zero; at least {MIN_TREND_POINTS} needed"
        return out
    xs = [math.log(v) for _, _, v in ok]
    ys = [math.log(f / v * 1e4) for _, f, v in ok]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx, syy = sum((x - mx) ** 2 for x in xs), sum((y - my) ** 2 for y in ys)
    if sxx <= 1e-12:
        out["note"] = "daily volume has no variation in the window"
        return out
    a, b, se = _ols_hac(xs, ys, lag)
    sse = sum((y - a - b * x) ** 2 for x, y in zip(xs, ys))
    lo, hi = b - Z90 * se, b + Z90 * se
    out.update({
        "status": "measured", "elasticity": b, "se_hac": se, "ci90": [lo, hi], "ci_excludes_zero": lo > 0.0 or hi < 0.0,
        "r2": (1.0 - sse / syy) if syy > 0 else None,
    })
    return out


def _pooled(rows: Sequence[tuple[int, float, float, float | None, float]]) -> dict[str, Any]:
    """Pooled (volume-weighted) take over ``rows`` = (ts, fees, revenue, holders | None, volume)."""
    if not rows:
        return {"n_days": 0, "start_date": None, "end_date": None, "gross_take_bps": None, "net_take_bps": None,
                "holder_take_bps": None, "avg_daily_volume_usd": None}
    f, r, v = sum(x[1] for x in rows), sum(x[2] for x in rows), sum(x[4] for x in rows)
    h = sum(x[3] for x in rows if x[3] is not None) if all(x[3] is not None for x in rows) else None
    return {
        "n_days": len(rows), "start_date": _iso(rows[0][0]), "end_date": _iso(rows[-1][0]),
        "gross_take_bps": _bps(f, v), "net_take_bps": _bps(r, v), "holder_take_bps": _bps(h, v),
        "avg_daily_volume_usd": v / len(rows),
    }


def _min_point(points: Sequence[tuple[int, float | None]]) -> dict[str, Any] | None:
    vals = [(v, t) for t, v in points if v is not None]
    if not vals:
        return None
    v, t = min(vals)
    return {"bps": v, "date": _iso(t)}


def _max_point(points: Sequence[tuple[int, float | None]]) -> dict[str, Any] | None:
    vals = [(v, t) for t, v in points if v is not None]
    if not vals:
        return None
    v, t = max(vals)
    return {"bps": v, "date": _iso(t)}


# ----------------------------------------------------------------------------- the model
def measure_take_rate_series(
    fees_chart: Any,
    revenue_chart: Any,
    holders_chart: Any,
    volume_chart: Any,
    *,
    floor_bps: float,
    trigger_net_bps: float,
    as_of: date | None = None,
    sources: Sequence[Mapping[str, Any]] = (),
    source_mode: str = "raw",
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    """Rolling take series, window table, trend, elasticity, regime break and floor read from the four daily charts.

    ``holders_chart`` may be None/empty (holder take and the regime break are then null). ``as_of`` is the run date
    (UTC): a point dated ``as_of`` or later is a partial day. ``status`` is "measured" or "insufficient_data".
    """
    warns = list(warnings)
    parsed: dict[str, dict[int, float]] = {}
    for name, chart in (("fees", fees_chart), ("revenue", revenue_chart), ("holders", holders_chart), ("volume", volume_chart)):
        pts = _chart_points(chart)
        n_raw = len(chart) if isinstance(chart, list) else 0
        if n_raw != len(pts):
            warns.append(f"take_rate_series: {n_raw - len(pts)} malformed {name} row(s) skipped")
        parsed[name] = dict(pts)
    fees, rev, hrev, vol = parsed["fees"], parsed["revenue"], parsed["holders"], parsed["volume"]
    has_holders = bool(hrev)

    # The collector's own rule decides which trailing days are partial or unsettled.
    win = aligned_window_sums(fees_chart, revenue_chart, holders_chart, volume_chart, days=10**9, as_of=as_of)
    common = set(fees) & set(rev) & set(vol)
    if has_holders:
        common &= set(hrev)
    end_iso = win.get("window_end_utc")
    kept = sorted(t for t in common if end_iso is not None and _iso(t) <= end_iso)
    negative = [t for t in kept if fees[t] < 0 or rev[t] < 0 or vol[t] < 0 or (has_holders and hrev[t] < 0)]
    if negative:
        warns.append(f"take_rate_series: {len(negative)} day(s) with a negative fee, revenue or volume figure skipped")
        neg = set(negative)
        kept = [t for t in kept if t not in neg]
    rows: list[tuple[int, float, float, float | None, float]] = [
        (t, fees[t], rev[t], hrev[t] if has_holders else None, vol[t]) for t in kept
    ]
    n = len(rows)
    n_gaps = sum(1 for a, b in zip(kept, kept[1:]) if b - a != DAY_S)

    base: dict[str, Any] = {
        "status": "insufficient_data",
        "method": (
            f"Inner join of the DefiLlama near-intents daily charts (gross fees, revenue, holders revenue, dexs volume). Rolling "
            f"{ROLLING_DAYS}-day take = sum(fees) / sum(volume) x 1e4 bps over {ROLLING_DAYS} consecutive settled days (net uses revenue, "
            f"holder uses holders revenue). Trend = OLS of ln(rolling gross take) on time in years, change per year = exp(slope) - 1, "
            f"90% CI from a Newey-West standard error with a {TREND_HAC_LAG_DAYS}-day Bartlett lag (twice the window, because "
            f"consecutive rolling points share {ROLLING_DAYS - 1} of {ROLLING_DAYS} days). Elasticity = OLS of ln(daily gross take) on "
            f"ln(daily volume), Newey-West {ELASTICITY_HAC_LAG_DAYS}-day lag, days with zero fees or volume dropped. Trailing days "
            f"dated on or after the run date, and up to {MAX_UNSETTLED_TAIL_DAYS} trailing days with revenue above fees, are excluded."
        ),
        "source": "; ".join(
            f"{s.get('record')}" + (f" sha256 {str(s['sha256'])[:12]}..." if s.get("sha256") else "") for s in sources
        ) or "none",
        "sources": [dict(s) for s in sources], "source_mode": source_mode, "holders_available": has_holders,
        "as_of_utc": as_of.isoformat() if as_of else None,
        "rolling_window_days": ROLLING_DAYS, "trailing_days": TRAILING_DAYS,
        "n_days": n, "first_day": _iso(kept[0]) if kept else None, "last_day": _iso(kept[-1]) if kept else None, "n_gaps": n_gaps,
        "excluded_unsettled_days": list(win.get("excluded_unsettled_days") or []),
        "columns": list(SERIES_COLUMNS), "series": [], "n_rolling_points": 0, "n_rolling_skipped": 0,
        "latest": None, "year_ago": None, "range_trailing_365d": None, "windows": [],
        "trend": {"trailing_365d": None, "trailing_180d": None, "full_history": None, "lag_sensitivity_365d": [], "block_check_365d": None,
                  "block_check_agrees": None},
        "elasticity": {"trailing_365d": None, "full_history": None},
        "regime_break": None, "floor_read": None,
        "headline": "Take-rate history not measured: fewer than 30 aligned settled days in the DefiLlama charts.",
        "investor_read": None, "caveats": list(CAVEATS), "data_warnings": warns,
    }
    if n < ROLLING_DAYS:
        return base

    # ---- rolling 30-day take (prefix sums; a window must be ROLLING_DAYS consecutive calendar days)
    pf, pr, ph, pv = [0.0], [0.0], [0.0], [0.0]
    for _t, f, r, h, v in rows:
        pf.append(pf[-1] + f)
        pr.append(pr[-1] + r)
        ph.append(ph[-1] + (h or 0.0))
        pv.append(pv[-1] + v)
    roll: list[tuple[int, float, float, float | None, float]] = []  # (ts, gross, net, holder, avg daily volume)
    skipped = 0
    for i in range(ROLLING_DAYS - 1, n):
        j = i - ROLLING_DAYS + 1
        vsum = pv[i + 1] - pv[j]
        if rows[i][0] - rows[j][0] != (ROLLING_DAYS - 1) * DAY_S or vsum <= 0:
            skipped += 1
            continue
        roll.append((
            rows[i][0], (pf[i + 1] - pf[j]) / vsum * 1e4, (pr[i + 1] - pr[j]) / vsum * 1e4,
            ((ph[i + 1] - ph[j]) / vsum * 1e4) if has_holders else None, vsum / ROLLING_DAYS,
        ))
    base["n_rolling_skipped"] = skipped
    if not roll:
        return base
    base["series"] = [[t, _r(g), _r(nt), _r(h), round(av, 0)] for t, g, nt, h, av in roll]
    base["n_rolling_points"] = len(roll)

    last_ts = roll[-1][0]
    cut = last_ts - TRAILING_DAYS * DAY_S
    roll_y = [p for p in roll if p[0] > cut]
    rows_y = [x for x in rows if x[0] > rows[-1][0] - TRAILING_DAYS * DAY_S]

    def point(p: tuple[int, float, float, float | None, float]) -> dict[str, Any]:
        return {"date": _iso(p[0]), "ts_unix_s": p[0], "gross_take_bps": p[1], "net_take_bps": p[2], "holder_take_bps": p[3],
                "avg_daily_volume_usd": p[4]}

    latest, first_y = roll[-1], roll_y[0]
    base["latest"] = point(latest)
    base["year_ago"] = {**point(first_y), "days_before_latest": (latest[0] - first_y[0]) // DAY_S}
    base["range_trailing_365d"] = {
        "n_points": len(roll_y), "gross_min": _min_point([(p[0], p[1]) for p in roll_y]), "gross_max": _max_point([(p[0], p[1]) for p in roll_y]),
        "gross_min_180d": _min_point([(p[0], p[1]) for p in roll_y if p[0] > last_ts - 180 * DAY_S]),
    }

    # ---- window table (pooled take over 30 settled days, by position from the last settled day)
    for label, end_ago, start_ago in WINDOWS:
        sl = rows[n - start_ago: n - end_ago] if n >= start_ago else []
        base["windows"].append({"label": label, "days_ago_from": end_ago, "days_ago_to": start_ago, **_pooled(sl)})

    # ---- trend and elasticity
    gross_y = [(p[0], p[1]) for p in roll_y]
    base["trend"] = {
        "trailing_365d": _log_trend(gross_y, TREND_HAC_LAG_DAYS),
        "trailing_180d": _log_trend([x for x in gross_y if x[0] > last_ts - RECENT_DAYS * DAY_S], TREND_HAC_LAG_DAYS),
        "full_history": _log_trend([(p[0], p[1]) for p in roll], TREND_HAC_LAG_DAYS),
        # robustness reads for the trailing-365d figure (reported, never graded)
        "lag_sensitivity_365d": [
            {"hac_lag_days": lag, "ci90_pct": tr["ci90_pct"], "ci_excludes_zero": tr["ci_excludes_zero"]}
            for lag in LAG_SENSITIVITY_DAYS for tr in [_log_trend(gross_y, lag)] if tr["status"] == "measured"
        ],
        "block_check_365d": _block_trend(gross_y),
    }
    t365, blk = base["trend"]["trailing_365d"], base["trend"]["block_check_365d"]
    # True when the non-overlapping check reaches the same verdict (excludes zero on the same side, or both include zero)
    base["trend"]["block_check_agrees"] = (
        None if t365["status"] != "measured" or blk["status"] != "measured"
        else (blk["ci_excludes_zero"] and (blk["ci90_pct"][1] < 0) == (t365["ci90_pct"][1] < 0)) if t365["ci_excludes_zero"]
        else not blk["ci_excludes_zero"]
    )
    base["elasticity"] = {
        "trailing_365d": _elasticity([(x[0], x[1], x[4]) for x in rows_y], ELASTICITY_HAC_LAG_DAYS),
        "full_history": _elasticity([(x[0], x[1], x[4]) for x in rows], ELASTICITY_HAC_LAG_DAYS),
    }

    # ---- regime break: first day with holders revenue > 0, read from the data
    first_rev = next((x[0] for x in rows if x[2] > 0), None)
    break_ts = next((x[0] for x in rows if x[3] is not None and x[3] > 0), None) if has_holders else None
    if break_ts is not None:
        before, after = [x for x in rows if x[0] < break_ts], [x for x in rows if x[0] >= break_ts]
        before_y = [x for x in before if x[0] > rows[-1][0] - TRAILING_DAYS * DAY_S]
        base["regime_break"] = {
            "date": _iso(break_ts), "ts_unix_s": break_ts, "definition": "first aligned day with dailyHoldersRevenue > 0",
            "first_revenue_day": _iso(first_rev) if first_rev is not None else None,
            "before": _pooled(before), "before_trailing_365d": _pooled(before_y), "after": _pooled(after),
        }
    else:
        base["regime_break"] = {
            "date": None, "ts_unix_s": None, "definition": "first aligned day with dailyHoldersRevenue > 0",
            "first_revenue_day": _iso(first_rev) if first_rev is not None else None,
            "before": None, "before_trailing_365d": None, "after": None,
            "note": "holders revenue chart not available in this input" if not has_holders else "no day with holders revenue above zero",
        }

    # ---- floor read over the trailing-365d rolling points
    since = [p for p in roll_y if break_ts is not None and p[0] - (ROLLING_DAYS - 1) * DAY_S >= break_ts]
    base["floor_read"] = {
        FLOOR_KEY: floor_bps, TRIGGER_KEY: trigger_net_bps, "n_points": len(roll_y),
        "gross_below_floor": sum(1 for p in roll_y if p[1] < floor_bps),
        "net_below_trigger": sum(1 for p in roll_y if p[2] < trigger_net_bps),
        "min_gross": _min_point([(p[0], p[1]) for p in roll_y]), "min_net": _min_point([(p[0], p[2]) for p in roll_y]),
        "latest_gross_above_floor": latest[1] > floor_bps, "latest_net_above_trigger": latest[2] >= trigger_net_bps,
        "since_regime_break": {
            "n_points": len(since), "net_below_trigger": sum(1 for p in since if p[2] < trigger_net_bps),
            "min_net": _min_point([(p[0], p[2]) for p in since]),
            "definition": "rolling windows that start on or after the regime-break day",
        } if break_ts is not None else None,
    }

    base["status"] = "measured"
    base["headline"] = _headline(base)
    base["investor_read"] = _investor_read(base)
    return base


def _usd_m(x: float | None) -> str:
    return "n/a" if x is None else f"${x / 1e6:,.0f}M"


def _trend_txt(t: Mapping[str, Any]) -> str:
    lo, hi = t["ci90_pct"]
    return f"{t['change_per_year_pct']:+.0f}% per year (90% CI {lo:+.0f}% to {hi:+.0f}%)"


def _headline(d: Mapping[str, Any]) -> str:
    latest, ago = d["latest"], d["year_ago"]
    t, t180 = d["trend"]["trailing_365d"], d["trend"]["trailing_180d"]
    span = f"{ago['days_before_latest']} days earlier" if ago["days_before_latest"] < TRAILING_DAYS - 1 else "a year earlier"
    level = (
        f"the rolling {ROLLING_DAYS}-day rate is {latest['gross_take_bps']:.1f} bps on {latest['date']} against {ago['gross_take_bps']:.1f} bps "
        f"{span}, while average daily volume went from {_usd_m(ago['avg_daily_volume_usd'])} to {_usd_m(latest['avg_daily_volume_usd'])}"
    )
    if t.get("status") != "measured":
        return f"Gross take has too few rolling points for a trend: {level}."
    tail = f"the trailing-365d log-linear trend is {_trend_txt(t)}"
    if not t["ci_excludes_zero"]:
        return f"Gross take shows no statistically significant compression over the trailing year: {level}; {tail}, which includes zero."
    if t["ci90_pct"][1] >= 0:
        return f"Gross take rose over the trailing year: {level}; {tail}, which excludes zero."
    if d["trend"].get("block_check_agrees") is False:
        return (
            f"Gross-take compression is not established: {level}; {tail}, which excludes zero, but the non-overlapping check does not confirm it."
        )
    s = f"Gross take compressed over the trailing year: {level}; {tail}, which excludes zero"
    if t180.get("status") == "measured":
        if t180["ci_excludes_zero"] and t180["ci90_pct"][1] < 0:
            return s + f", and the trailing-{RECENT_DAYS}d trend, {_trend_txt(t180)}, shows it continuing."
        return s + f", and the trailing-{RECENT_DAYS}d trend, {_trend_txt(t180)}, does not show the decline continuing."
    return s + "."


def _investor_read(d: Mapping[str, Any]) -> str:
    t, t180 = d["trend"]["trailing_365d"], d["trend"]["trailing_180d"]
    fl, latest, ago = d["floor_read"], d["latest"], d["year_ago"]
    net = (
        f" NEAR's captured (net) take went from {ago['net_take_bps']:.1f} bps to {latest['net_take_bps']:.1f} bps over the same span and sat under "
        f"the {fl[TRIGGER_KEY]:g} bps fee-race trigger on {fl['net_below_trigger']} of {fl['n_points']} trailing rolling points."
    )
    if t.get("status") != "measured":
        return (
            "The series is too short to grade a trend, so the fee-compression leg of the bear case is neither confirmed nor refuted here. "
            f"A trailing-365d trend interval wholly below zero, or a rolling gross take under the {fl[FLOOR_KEY]:g} bps model floor, would confirm it." + net
        )
    if t["ci_excludes_zero"] and t["ci90_pct"][1] < 0:
        recent = ""
        if t180.get("status") == "measured":
            cont = t180["ci_excludes_zero"] and t180["ci90_pct"][1] < 0
            recent = (
                f" The trailing-{RECENT_DAYS}d trend is {_trend_txt(t180)}: the decline "
                + ("is still running." if cont else "is not visible in the last six months.")
            )
        blk = d["trend"].get("block_check_365d") or {}
        agrees = d["trend"].get("block_check_agrees")
        check = (
            "" if blk.get("status") != "measured" else
            f" (non-overlapping check: {blk['change_per_year_pct']:+.0f}% per year, 90% CI {blk['ci90_pct'][0]:+.0f}% to {blk['ci90_pct'][1]:+.0f}%, "
            f"{'also excludes zero' if agrees else 'does not exclude zero, so the decline is not established'})"
        )
        return (
            f"This cuts against the bull case: gross take fell at {abs(t['change_per_year_pct']):.0f}% per year over the trailing year with an "
            f"interval that excludes zero{check}, so the claim that pricing power has held while volume grew is not supported by the fee history; "
            f"the level is still {latest['gross_take_bps'] / fl[FLOOR_KEY]:.0f}x the {fl[FLOOR_KEY]:g} bps model floor." + recent
            + " A trailing-365d interval that includes zero again would overturn this read; a 180d interval wholly below zero would show "
            "compression still in progress." + net
        )
    return (
        "The fee-compression leg of the bear case is not in the data: gross take shows no statistically significant decline over the "
        f"trailing year of volume growth. A trailing-365d trend interval wholly below zero, or a rolling gross take under the "
        f"{fl[FLOOR_KEY]:g} bps model floor, would overturn this read." + net
    )


def run_take_rate_series(snap_dict: Mapping[str, Any], raw_dir: Path | None = None) -> dict[str, Any]:
    """RAW_DERIVED_MODELS entry: load the run's raw DefiLlama charts (else the snapshot's daily series) and measure."""
    charts, sources, mode, warns = load_charts(raw_dir, snap_dict)
    as_of: date | None = None
    gen = snap_dict.get("generated_at_utc")
    if isinstance(gen, str):
        try:
            as_of = datetime.fromisoformat(gen.replace("Z", "+00:00")).astimezone(timezone.utc).date()
        except ValueError:
            as_of = None
    return measure_take_rate_series(
        charts.get("fees"), charts.get("revenue"), charts.get("holders"), charts.get("volume"),
        floor_bps=_threshold(snap_dict, FLOOR_KEY), trigger_net_bps=_threshold(snap_dict, TRIGGER_KEY),
        as_of=as_of, sources=sources, source_mode=mode, warnings=warns,
    )


# ----------------------------------------------------------------------------- scorecard
def scorecard_claim(data: Any) -> dict[str, str] | None:
    """Graded row for the evidence scorecard (fields of ``EvidenceClaim``); None when there is no data dict.

    A decline counts as significant only when BOTH tests agree: the trailing-365d Newey-West 90% CI upper bound is below
    zero and, when it could be measured, so is the Student-t interval on non-overlapping 30-day windows (the Newey-West
    test on overlapping rolling points over-rejects, so it is not trusted alone). DERIVED needs no significant decline AND
    a latest rolling-30d gross take above ``public_take_floor_bps``; otherwise NOT_SUPPORTED.
    """
    if not isinstance(data, Mapping):
        return None
    src = str(data.get("source") or "defillama near-intents daily charts")
    note = (
        "Graded on the trailing-365d trend only: a decline is counted when the Newey-West 90% interval and the non-overlapping-window "
        "Student-t interval both sit below zero; DERIVED needs no such decline and a latest rolling take above the model floor. "
        "Gross take includes affiliate fees kept by frontends; NEAR's captured share is the net / holder take. Rolling points overlap, so "
        "an interval that includes zero is not proof of a floor. The full-history trend is not used (fee ramp from zero in 2025)."
    )
    t = (data.get("trend") or {}).get("trailing_365d") or {}
    latest = (data.get("latest") or {}).get("gross_take_bps")
    fl = data.get("floor_read") or {}
    floor = fl.get(FLOOR_KEY)
    if data.get("status") != "measured" or t.get("status") != "measured" or latest is None or floor is None:
        return {"claim": CLAIM, "status": "NOT_SUPPORTED", "value": "not measured: too few aligned days for a trailing-365d trend",
                "source": src, "confidence": "none", "note": note}
    lo, hi = t["ci90_pct"]
    blk0 = (data.get("trend") or {}).get("block_check_365d") or {}
    block_agrees = blk0.get("status") != "measured" or blk0["ci90_pct"][1] < 0.0
    ok = not (hi < 0.0 and block_agrees) and latest > floor
    ago = data.get("year_ago") or {}
    value = (
        f"rolling 30d gross take {latest:.2f} bps on {(data.get('latest') or {}).get('date')} vs {ago.get('gross_take_bps', float('nan')):.2f} bps on "
        f"{ago.get('date')}; trend {t['change_per_year_pct']:+.1f}%/yr, 90% CI {lo:+.1f}% to {hi:+.1f}% "
        f"({'excludes' if t['ci_excludes_zero'] else 'includes'} zero; Newey-West {t['hac_lag_days']}d lag, {t['n_points']} overlapping points); "
        f"floor {floor:g} bps, {fl.get('gross_below_floor')} of {fl.get('n_points')} trailing points below it"
    )
    blk = (data.get("trend") or {}).get("block_check_365d") or {}
    if blk.get("status") == "measured":
        value += (
            f"; non-overlapping 30d windows (n={blk['n_blocks']}) {blk['change_per_year_pct']:+.1f}%/yr, Student-t 90% CI "
            f"{blk['ci90_pct'][0]:+.1f}% to {blk['ci90_pct'][1]:+.1f}%"
        )
    t180 = (data.get("trend") or {}).get(f"trailing_{RECENT_DAYS}d") or {}
    if t180.get("status") == "measured":
        value += f"; trailing {RECENT_DAYS}d trend {t180['change_per_year_pct']:+.1f}%/yr, CI {t180['ci90_pct'][0]:+.1f}% to {t180['ci90_pct'][1]:+.1f}%"
    return {"claim": CLAIM, "status": "DERIVED" if ok else "NOT_SUPPORTED", "value": value, "source": src,
            "confidence": "medium" if ok else "low", "note": note}


# ----------------------------------------------------------------------------- memo
def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], align: Sequence[str]) -> str:
    """GitHub-flavoured table in memo_generator._table's style (kept local: memo_generator imports this module)."""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---:" if a == "r" else ":---" for a in align) + " |"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    lines.append("")
    return "\n".join(lines)


def _f(x: Any, nd: int = 2) -> str:
    return f"{x:,.{nd}f}" if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else "n/a"


def memo_markdown(data: Mapping[str, Any], snap_dict: Mapping[str, Any]) -> str:  # noqa: ARG001 - signature fixed by EXTRA_SECTIONS
    """Memo sub-section: headline, window table, trend and elasticity lines, regime break, floor read, caveats."""
    if data.get("status") != "measured":
        return str(data.get("headline") or "Take-rate history not measured in this run.")
    parts: list[str] = [str(data["headline"])]
    rows = [
        [w["label"], f"{w['start_date']} to {w['end_date']}" if w.get("n_days") else "n/a", _f(w.get("gross_take_bps")),
         _f(w.get("net_take_bps")), _f(w.get("holder_take_bps")), _usd_m(w.get("avg_daily_volume_usd"))]
        for w in data.get("windows") or []
    ]
    parts.append(_md_table(["Window", "Days (UTC)", "Gross take (bps)", "Net take (bps)", "Holder take (bps)", "Avg daily volume"],
                           rows, ["l", "l", "r", "r", "r", "r"]))
    lines: list[str] = []
    for key, label in (("trailing_365d", "Trend, trailing 365 days"), (f"trailing_{RECENT_DAYS}d", f"Trend, trailing {RECENT_DAYS} days"),
                       ("full_history", "Trend, full history")):
        t = (data.get("trend") or {}).get(key) or {}
        if t.get("status") == "measured":
            lo, hi = t["ci90_pct"]
            lines.append(
                f"**{label}** ({t['first_day']} to {t['last_day']}, {t['n_points']} rolling points): {t['change_per_year_pct']:+.1f}% per year, "
                f"90% CI {lo:+.1f}% to {hi:+.1f}% ({'excludes' if t['ci_excludes_zero'] else 'includes'} zero; Newey-West, {t['hac_lag_days']}-day lag)."
                + (" Dominated by the 2025 fee ramp from zero; not a competition signal." if key == "full_history" else "")
            )
        else:
            lines.append(f"**{label}**: not measured ({t.get('note') or 'insufficient data'}).")
    tr = data.get("trend") or {}
    rob: list[str] = [
        f"{x['hac_lag_days']}-day lag {x['ci90_pct'][0]:+.1f}% to {x['ci90_pct'][1]:+.1f}%" for x in tr.get("lag_sensitivity_365d") or [] if x.get("ci90_pct")
    ]
    blk = tr.get("block_check_365d") or {}
    if blk.get("status") == "measured":
        rob.append(
            f"{blk['n_blocks']} non-overlapping 30-day windows {blk['change_per_year_pct']:+.1f}% per year, Student-t 90% CI "
            f"{blk['ci90_pct'][0]:+.1f}% to {blk['ci90_pct'][1]:+.1f}%"
        )
    if rob:
        lines.append("**Robustness of the trailing-365d trend** (reported, not graded): " + "; ".join(rob) + ".")
    for key, label in (("trailing_365d", "Elasticity to volume, trailing 365 days"), ("full_history", "Elasticity to volume, full history")):
        e = (data.get("elasticity") or {}).get(key) or {}
        if e.get("status") == "measured":
            lo, hi = e["ci90"]
            lines.append(
                f"**{label}** ({e['n_days']} days, {e['n_dropped_zero_fee_or_volume']} dropped for zero fees or volume): a 1% rise in daily volume "
                f"goes with a {e['elasticity']:+.2f}% change in daily gross take, 90% CI {lo:+.2f} to {hi:+.2f} "
                f"({'excludes' if e['ci_excludes_zero'] else 'includes'} zero; R2 {_f(e.get('r2'))})."
            )
        else:
            lines.append(f"**{label}**: not measured ({e.get('note') or 'insufficient data'}).")
    rb = data.get("regime_break") or {}
    if rb.get("date"):
        b, b_y, a = rb.get("before") or {}, rb.get("before_trailing_365d") or {}, rb.get("after") or {}
        lines.append(
            f"**Regime break** ({rb['definition']}): {rb['date']}. Pooled gross take {_f(b.get('gross_take_bps'))} bps over the {b.get('n_days')} days before "
            f"({_f(b_y.get('gross_take_bps'))} bps over the {b_y.get('n_days')} of those inside the trailing year) and {_f(a.get('gross_take_bps'))} bps over the "
            f"{a.get('n_days')} days since; net take {_f(b_y.get('net_take_bps'))} bps before (trailing year) and {_f(a.get('net_take_bps'))} bps since."
        )
    else:
        lines.append(f"**Regime break**: not identified ({rb.get('note') or 'no holders revenue data'}).")
    rng = data.get("range_trailing_365d") or {}
    if rng.get("gross_max") and rng.get("gross_min"):
        lines.append(
            f"**Range, trailing {rng.get('n_points')} rolling points**: gross take high {_f(rng['gross_max'].get('bps'))} bps ({rng['gross_max'].get('date')}), "
            f"low {_f(rng['gross_min'].get('bps'))} bps ({rng['gross_min'].get('date')})."
        )
    fl = data.get("floor_read") or {}
    if fl:
        mg, mn = fl.get("min_gross") or {}, fl.get("min_net") or {}
        sb = fl.get("since_regime_break") or {}
        lines.append(
            f"**Floor read** (trailing {fl.get('n_points')} rolling points): gross take was below the {fl[FLOOR_KEY]:g} bps model floor on "
            f"{fl.get('gross_below_floor')} of them (minimum {_f(mg.get('bps'))} bps, {mg.get('date')}); net take was below the {fl[TRIGGER_KEY]:g} bps "
            f"fee-race trigger on {fl.get('net_below_trigger')} (minimum {_f(mn.get('bps'))} bps, {mn.get('date')})"
            + (f", and on {sb.get('net_below_trigger')} of the {sb.get('n_points')} windows that start after the regime break." if sb.get("n_points") else ".")
        )
    parts.append("\n".join(f"- {x}" for x in lines))
    if data.get("investor_read"):
        parts.append(f"**Read.** {data['investor_read']}")
    excl = data.get("excluded_unsettled_days") or []
    parts.append(
        f"Data: {data.get('n_days')} aligned settled days {data.get('first_day')} to {data.get('last_day')} ({data.get('source_mode')}); "
        + (f"unsettled trailing day(s) excluded: {', '.join(excl)}. " if excl else "no unsettled trailing day. ")
        + f"Source: {data.get('source')}."
    )
    parts.append("Limits:\n" + "\n".join(f"- {c}" for c in data.get("caveats") or []))
    return "\n\n".join(parts)
