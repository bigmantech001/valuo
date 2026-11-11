"""Measured NEAR Intents volume growth: replaces the registry's fixed ``public_volume_growth_yoy`` with a fit.

Input is the DefiLlama ``dexs/near-intents`` daily volume chart the run already fetched and hashed
(``artifacts/raw/defillama__dexs_near-intents.json``). The estimator:

    ln V_d = a + b * t_d + e_d,   t in years, over the trailing ``WINDOW_DAYS`` days with V_d > 0
    growth = exp(b) - 1           (trend growth per year)
    90% CI = exp(b -/+ 1.645 * se_NW(b)) - 1

``se_NW`` is the Newey-West (Bartlett kernel, ``HAC_LAG_DAYS`` lags) standard error, because daily volume residuals
are strongly autocorrelated and the plain OLS error would be several times too narrow.

Two cross-checks are reported next to it, never used: trailing-30-day volume against the same 30 days a year earlier,
and the mean of the last 12 monthly log returns of 30-day volume.

Convention, stated with the number: the log-linear slope is MEDIAN (geometric) growth. The SOTP model reads
``public_volume_growth_yoy`` as EXPECTED growth (mean-matching GBM), which at the measured volume volatility is far
above the median. Feeding the median in is the conservative choice; the model's simulated median path is then below
the measured trend.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from valuo.schemas import Assumption

__all__ = ["WINDOW_DAYS", "HAC_LAG_DAYS", "MIN_POINTS", "measure_volume_growth", "measured_assumption", "apply_measured_growth"]

WINDOW_DAYS = 365
HAC_LAG_DAYS = 30
MIN_POINTS = 180
Z90 = 1.6448536269514722
KEY = "public_volume_growth_yoy"


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _clean(chart: Any) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for row in chart or []:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        try:
            t, v = float(row[0]), float(row[1])
        except (TypeError, ValueError):
            continue
        if math.isfinite(t) and math.isfinite(v):
            out.append((t, v))
    out.sort()
    return out


def _ols_hac(xs: Sequence[float], ys: Sequence[float], lag: int) -> tuple[float, float, float]:
    """(intercept, slope, Newey-West standard error of the slope) for y = a + b x."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    # slope score u_i = (x_i - mx) e_i; var(b) = S / sxx^2 with S the Bartlett-weighted long-run variance of u
    u = [(x - mx) * (y - a - b * x) for x, y in zip(xs, ys)]
    s = sum(ui * ui for ui in u)
    for lag_k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - lag_k / (lag + 1.0)
        s += 2.0 * w * sum(u[i] * u[i - lag_k] for i in range(lag_k, n))
    return a, b, math.sqrt(max(s, 0.0)) / sxx


def measure_volume_growth(chart: Any, *, window_days: int = WINDOW_DAYS, hac_lag: int = HAC_LAG_DAYS,
                          source: str | None = None, source_sha256: str | None = None) -> dict[str, Any]:
    """Trend growth of daily volume with a HAC 90% interval. ``status`` is "measured" or "insufficient_data"."""
    pts = _clean(chart)
    base: dict[str, Any] = {
        "status": "insufficient_data", "growth_yoy": None, "ci90": None, "source": source, "source_sha256": source_sha256,
        "method": (f"OLS of ln(daily volume) on time over the trailing {window_days} days (days with volume > 0); growth = exp(slope) - 1 per year; "
                   f"90% CI from a Newey-West standard error ({hac_lag}-day Bartlett lags)"),
        "convention": ("median (geometric) trend growth, used as the model's expected growth: conservative, since the mean-matching "
                       "expected growth at the measured volume volatility is higher"),
        "window_days": window_days, "hac_lag_days": hac_lag, "n_days": 0, "first_day": None, "last_day": None,
        "cross_checks": {},
    }
    if not pts:
        return base
    last_t = pts[-1][0]
    win = [(t, v) for t, v in pts if t > last_t - window_days * 86400 and v > 0]
    base.update({"n_days": len(win), "first_day": _day(win[0][0]) if win else None, "last_day": _day(last_t)})
    if len(win) < MIN_POINTS:
        base["note"] = f"{len(win)} positive days in the window; at least {MIN_POINTS} needed"
        return base
    xs = [(t - win[0][0]) / 86400.0 / 365.0 for t, _ in win]
    ys = [math.log(v) for _, v in win]
    _a, b, se = _ols_hac(xs, ys, hac_lag)
    resid_sd = math.sqrt(sum((y - _a - b * x) ** 2 for x, y in zip(xs, ys)) / max(len(xs) - 2, 1))
    base.update({
        "status": "measured", "growth_yoy": math.expm1(b), "ci90": [math.expm1(b - Z90 * se), math.expm1(b + Z90 * se)],
        "log_slope_per_year": b, "log_slope_se_hac": se, "residual_sd_log": resid_sd,
    })
    # cross-checks (reported, not used)
    vals = [v for _, v in pts]
    n = len(vals)
    if n >= 395:
        now30, ago30 = sum(vals[-30:]), sum(vals[-395:-365])
        if ago30 > 0:
            base["cross_checks"]["yoy_trailing_30d"] = {"value": now30 / ago30 - 1.0, "volume_30d_usd": now30, "volume_30d_year_ago_usd": ago30}
    if n >= 30 * 13:
        months = [sum(vals[i - 29:i + 1]) for i in range(n - 1, 28, -30)][:13][::-1]
        if all(m > 0 for m in months):
            lr = [math.log(months[i + 1] / months[i]) for i in range(len(months) - 1)]
            base["cross_checks"]["mean_monthly_log_return_12m"] = {"value": math.expm1(12.0 * sum(lr) / len(lr)), "n_months": len(lr)}
    return base


def measured_assumption(est: Mapping[str, Any], registry_entry: Assumption) -> Assumption | None:
    """The registry entry replaced by the measurement (source="measured", range = the 90% CI), or None if not measured."""
    if est.get("status") != "measured" or est.get("growth_yoy") is None or not est.get("ci90"):
        return None
    g = float(est["growth_yoy"])
    lo, hi = (float(x) for x in est["ci90"])
    if not (g > -1.0 and math.isfinite(g)):
        return None
    xc = est.get("cross_checks") or {}
    cross = "; ".join(f"{k} {v['value']:+.0%}" for k, v in xc.items() if isinstance(v, Mapping) and v.get("value") is not None)
    return registry_entry.model_copy(update={
        "value": g, "low": min(lo, g), "high": max(hi, g), "source": "measured",
        "justification": (
            f"MEASURED: trend growth of NEAR Intents daily volume, {est['first_day']} to {est['last_day']} ({est['n_days']} days, DefiLlama "
            f"dexs/near-intents): {g:+.1%}/yr, 90% CI {lo:+.1%} to {hi:+.1%} (Newey-West, {est['hac_lag_days']}-day lags). Range = that CI. "
            f"Median trend growth used as EXPECTED growth (conservative). Replaces the registry default {registry_entry.value:+.0%}."
            + (f" Cross-checks (not used): {cross}." if cross else "")
        ),
    })


def apply_measured_growth(registry: Mapping[str, Assumption], est: Mapping[str, Any]) -> tuple[dict[str, Assumption], bool]:
    """Copy of ``registry`` with ``public_volume_growth_yoy`` replaced by the measurement when there is one."""
    out = dict(registry)
    if KEY not in out:
        return out, False
    new = measured_assumption(est, out[KEY])
    if new is None:
        return out, False
    out[KEY] = new
    return out, True
