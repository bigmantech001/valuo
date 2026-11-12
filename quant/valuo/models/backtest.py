"""Out-of-sample backtest of the SOTP volume engine (docs/MODEL_DESIGN.md section 4.11).

The volume GBM drives the clearinghouse and confidential engines, so it is the part of the valuation a track
record can test. For each historical origin t (every ``step_days`` days, anchored at the last complete day of the
DefiLlama ``dexs/near-intents`` daily chart), the model is calibrated with ONLY the days up to and including t,
exactly as the live run calibrates it:

  * starting volume V_0 = the 30-day sum ending at t / 30 (``build_inputs``: ``v_pub_usd_day = v_30d / window_days``);
  * volume sigma = ``intents_forensics.volume_volatility`` on the trailing 365 days up to t, passed through
    ``sotp_valuation._sigmas`` (same fallback chain: monthly sigma, else daily x sqrt(30), else the labeled
    ``volume_sigma_monthly_fallback``);
  * drift = the labeled ``public_volume_growth_yoy`` the run used, converted to monthly as ``build_inputs`` does,
    with the mean-matching (Ito) GBM of ``simulate_paths``:
        log V_h ~ Normal(log V_0 + h (ln(1+g) - sigma^2/2), sigma^2 h).

The marginal of that GBM at month h is lognormal, so the P10/P50/P90 bands and the PIT value are computed in closed
form (no Monte Carlo noise; ``tests/test_backtest.py`` checks the closed form against ``simulate_paths`` itself).
The forecast 30-day volume at month h is 30 x V_h and is compared with the realized 30-day sum ending
round(h x 365.25/12) days after t.

What this does NOT test: the fee take rate and its compression, holder capture alpha, the confidential share and its
drift to target, the terminal multiple, the discount rate, price, or supply. It tests one engine input, the volume
distribution, on total NEAR Intents volume (the DefiLlama chart is the total; the live model splits it into public
and confidential legs with the same sigma).

A second variant replaces the registry drift with the trailing mean monthly log return measured up to t
(``volume_monthly_mean_log_return``), so a reader can see whether the registry growth assumption (set with the full
history in view) helps or hurts. The live-model variant is the headline.

A second ENGINE is scored next to the GBM under the same protocol (``with_engines=True``, the default of
``backtest_from_raw``): a stationary block bootstrap of realized daily log-changes
(``valuo.models.volume_bootstrap``). It adds the keys ``engines``, ``comparison`` and ``valuation_effect``; every
existing key keeps its meaning and value, and the valuation keeps the GBM. ``bootstrap_claim`` grades it.

Pure: no network, no file IO. ``backtest_from_raw`` is the thin loader used by ``reproduce.py``.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from types import SimpleNamespace
from typing import Any

import numpy as np

from valuo import assumptions as A
from valuo.collectors.intents_forensics import _chart_points, volume_volatility
from valuo.models import volume_bootstrap as vb
from valuo.models.sotp_valuation import DAYS_PER_MONTH, _sigmas
from valuo.schemas import Assumption

__all__ = [
    "HORIZONS_MONTHS", "STEP_DAYS", "WINDOW_DAYS", "SIGMA_LOOKBACK_DAYS", "TARGET_COVERAGE", "PIT_BINS",
    "NOT_TESTED", "forecast_at_origin", "lognormal_bands", "run_backtest", "backtest_from_raw", "load_dexs_chart",
    "bootstrap_claim", "FORWARD_HORIZON_MONTHS",
]

# Backtest design (methodology, not model inputs).
HORIZONS_MONTHS: tuple[int, ...] = (1, 3, 6)
STEP_DAYS: int = 30            # one origin per 30 days, anchored at the last complete day (same anchor as volume_volatility)
WINDOW_DAYS: int = 30          # the live model's 30-day volume window
SIGMA_LOOKBACK_DAYS: int = 365  # volume_volatility(days=365), the live default
TARGET_COVERAGE: float = 0.80  # nominal P10-P90 coverage
PIT_BINS: int = 5
_Z90 = 1.2815515655446004      # Phi^-1(0.9)
_Z95 = 1.6448536269514722      # Phi^-1(0.95), for the 90% Wilson interval
DEXS_RAW_NAME = "defillama__dexs_near-intents.json"
FORWARD_HORIZON_MONTHS: int = 12  # valuation-effect horizon: 30-day volume 12 months after the latest origin

NOT_TESTED: tuple[str, ...] = (
    "fee take rate (public and confidential) and its compression toward the floor",
    "holder capture ratio alpha",
    "confidential share of volume and its drift to the target share",
    "terminal FDV/revenue multiple and discount rate",
    "NEAR price and supply paths",
)


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _iso_day(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _wilson(k: int, n: int, z: float = _Z95) -> list[float] | None:
    if n <= 0:
        return None
    p = k / n
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def _binom_two_sided_p(k: int, n: int, p: float) -> float | None:
    """Exact two-sided binomial p-value (sum of outcomes no more likely than k)."""
    if n <= 0:
        return None
    pmf = [math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(n + 1)]
    ref = pmf[k] * (1 + 1e-9)
    return min(1.0, sum(q for q in pmf if q <= ref))


def forecast_at_origin(
    history: Sequence[tuple[int, float]],
    *,
    growth_yoy: float,
    horizons: Sequence[int] = HORIZONS_MONTHS,
    assumptions: Mapping[str, Assumption] | None = None,
    drift: str = "registry",
) -> dict[str, Any] | None:
    """Calibrate on ``history`` (every point up to and including the origin, nothing later) and return the
    lognormal 30-day-volume forecast per horizon. None when there are fewer than ``WINDOW_DAYS`` points.

    ``drift = "registry"`` is the live model (labeled public_volume_growth_yoy); ``"measured"`` uses the trailing
    mean monthly log return as the median drift (ln(1+g) = mean_log_return + sigma^2/2), no registry input.
    """
    if len(history) < WINDOW_DAYS:
        return None
    values = [v for _, v in history]
    v30 = sum(values[-WINDOW_DAYS:])
    if v30 <= 0:
        return None
    vol = volume_volatility([[t, v] for t, v in history], days=SIGMA_LOOKBACK_DAYS)
    warns: list[str] = []
    sig = _sigmas(SimpleNamespace(volatility=vol), warns, assumptions)  # type: ignore[arg-type]
    sigma = float(sig["sigma_volume_monthly"])
    if drift == "registry":
        if growth_yoy <= -1.0:
            raise ValueError("public_volume_growth_yoy must be > -1")
        g_month = (1.0 + growth_yoy) ** (1.0 / 12.0) - 1.0  # as build_inputs
        log_g = math.log1p(g_month)
    elif drift == "measured":
        mlr = vol.get("volume_monthly_mean_log_return")
        if mlr is None:
            return None
        log_g = float(mlr) + 0.5 * sigma * sigma
    else:
        raise ValueError(f"unknown drift {drift!r}")
    v0_day = v30 / WINDOW_DAYS
    out: dict[str, Any] = {
        "origin_ts": history[-1][0], "origin_date": _iso_day(history[-1][0]), "v0_30d_usd": v30,
        "sigma_volume_monthly": sigma, "sigma_volume_source": sig["sigma_volume_source"],
        "sigma_volume_measured": sig["sigma_volume_measured"], "sigma_n_monthly_returns": vol.get("volume_monthly_n_obs"),
        "log_growth_monthly": log_g, "history_days": len(history), "horizons": {},
    }
    for h in horizons:
        out["horizons"][int(h)] = lognormal_bands(v0_day, sigma, log_g, int(h))
    return out


def lognormal_bands(v0_day: float, sigma: float, log_g: float, h: int) -> dict[str, float]:
    """Law of 30 x V_h under simulate_paths' mean-matching GBM: log V_h ~ N(log V_0 + h (log_g - sigma^2/2), sigma^2 h)."""
    mu = math.log(v0_day * WINDOW_DAYS) + h * (log_g - 0.5 * sigma * sigma)
    sd = sigma * math.sqrt(h)
    return {
        "mu_log": mu, "sd_log": sd,
        "p10": math.exp(mu - _Z90 * sd), "p50": math.exp(mu), "p90": math.exp(mu + _Z90 * sd),
        "mean": math.exp(mu + 0.5 * sd * sd),
    }


def _horizon_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0, "coverage_p10_p90": None, "coverage_ci90_wilson": None, "binom_p_vs_80": None, "below_p10": 0, "above_p90": 0,
                "below_p10_share": None, "above_p90_share": None, "median_log_error": None, "mean_log_error": None,
                "median_abs_log_error": None, "median_ratio_realized_to_p50": None, "share_realized_above_p50": None,
                "pit_hist": [0] * PIT_BINS}
    inside = sum(1 for r in rows if r["inside"])
    below = sum(1 for r in rows if r["realized_30d_usd"] < r["p10"])
    above = sum(1 for r in rows if r["realized_30d_usd"] > r["p90"])
    le = [r["log_error"] for r in rows]
    hist = [0] * PIT_BINS
    for r in rows:
        hist[min(PIT_BINS - 1, int(r["pit"] * PIT_BINS))] += 1
    mle = median(le)
    return {
        "n": n, "inside": inside, "coverage_p10_p90": inside / n, "coverage_ci90_wilson": _wilson(inside, n),
        "binom_p_vs_80": _binom_two_sided_p(inside, n, TARGET_COVERAGE),
        "below_p10": below, "above_p90": above, "below_p10_share": below / n, "above_p90_share": above / n,
        "median_log_error": mle, "mean_log_error": sum(le) / n, "median_abs_log_error": median(abs(x) for x in le),
        "median_ratio_realized_to_p50": math.exp(mle), "share_realized_above_p50": sum(1 for x in le if x > 0) / n,
        "pit_hist": hist,
    }


def _run_variant(points: list[tuple[int, float]], origins: list[int], *, growth_yoy: float, horizons: Sequence[int],
                 assumptions: Mapping[str, Assumption] | None, drift: str) -> dict[str, Any]:
    last = len(points) - 1
    rows: list[dict[str, Any]] = []
    for i in origins:
        fc = forecast_at_origin(points[: i + 1], growth_yoy=growth_yoy, horizons=horizons, assumptions=assumptions, drift=drift)
        if fc is None:
            continue
        for h in horizons:
            j = i + int(round(h * DAYS_PER_MONTH))
            if j > last:
                continue
            realized = sum(v for _, v in points[j - WINDOW_DAYS + 1: j + 1])
            if realized <= 0:
                continue
            q = fc["horizons"][int(h)]
            z = (math.log(realized) - q["mu_log"]) / q["sd_log"] if q["sd_log"] > 0 else 0.0
            rows.append({
                "origin_date": fc["origin_date"], "target_date": _iso_day(points[j][0]), "h": int(h),
                "v0_30d_usd": fc["v0_30d_usd"], "sigma_volume_monthly": fc["sigma_volume_monthly"],
                "sigma_volume_measured": fc["sigma_volume_measured"], "sigma_n_monthly_returns": fc["sigma_n_monthly_returns"],
                "log_growth_monthly": fc["log_growth_monthly"],
                "p10": q["p10"], "p50": q["p50"], "p90": q["p90"], "mean": q["mean"],
                "realized_30d_usd": realized, "inside": q["p10"] <= realized <= q["p90"],
                "log_error": math.log(realized / q["p50"]), "pit": _phi(z),
            })
    by_h = {str(h): _horizon_stats([r for r in rows if r["h"] == h]) for h in horizons}
    return {"drift": drift, "rows": rows, "by_horizon": by_h}


def run_backtest(
    chart: Any,
    *,
    growth_yoy: float,
    assumptions: Mapping[str, Assumption] | None = None,
    horizons: Sequence[int] = HORIZONS_MONTHS,
    step_days: int = STEP_DAYS,
    as_of_ts: int | None = None,
    source: str = "defillama:dexs/near-intents totalDataChart",
    source_sha256: str | None = None,
    with_engines: bool = False,
) -> dict[str, Any]:
    """Rolling-origin backtest of the volume engine on a daily USD chart [[unix_s, usd], ...]. Pure.

    ``as_of_ts`` drops days that were not complete at that instant (the partial current UTC day). Origins start
    at the first day where the live calibration has a measured monthly sigma (two monthly returns, 90 days) and
    step back from the last complete day every ``step_days``.

    ``with_engines`` also scores the block-bootstrap engine on the same origins and targets and adds ``engines``,
    ``comparison`` and ``valuation_effect``. It never changes the keys above it and never raises: on a fault those
    three keys are null and ``engines_error`` says why.
    """
    reg = assumptions if assumptions is not None else A.ASSUMPTIONS
    points = _chart_points(chart)
    if as_of_ts is not None:
        points = [p for p in points if p[0] + 86400 <= as_of_ts]
    gaps = sum(1 for a, b in zip(points, points[1:], strict=False) if b[0] - a[0] != 86400)
    base: dict[str, Any] = {
        "method": (
            "Rolling-origin out-of-sample test of the SOTP volume GBM. At each origin the model is calibrated only on days up to the "
            "origin (V_0 = trailing 30-day volume / 30; sigma = volume_volatility over the trailing 365 days via sotp _sigmas; drift = "
            "the run's public_volume_growth_yoy with the Ito correction) and the lognormal law of 30-day volume at month h is compared "
            "with the realized 30-day sum ending round(h x 30.44) days later. Closed-form quantiles of the model's own GBM; no simulation."
        ),
        "source": source, "source_sha256": source_sha256, "growth_yoy_used": growth_yoy,
        "horizons_months": [int(h) for h in horizons], "step_days": step_days, "window_days": WINDOW_DAYS,
        "sigma_lookback_days": SIGMA_LOOKBACK_DAYS, "target_coverage": TARGET_COVERAGE, "pit_bins": PIT_BINS,
        "n_days": len(points), "n_gaps": gaps,
        "first_day": _iso_day(points[0][0]) if points else None, "last_day": _iso_day(points[-1][0]) if points else None,
        "not_tested": list(NOT_TESTED),
        "caveats": [
            "Forecasts at h = 3 and 6 months from monthly origins overlap, so their errors are serially correlated: the effective sample "
            "is smaller than n and the binomial interval is too narrow for those horizons.",
            "public_volume_growth_yoy is a registry assumption chosen with the full history in view; the 'measured drift' variant removes "
            "that look-ahead by using only the trailing mean monthly log return.",
            "The series is total NEAR Intents volume; the live model splits it into public and confidential legs with the same sigma, "
            "so the split itself is not tested.",
        ],
    }
    if gaps:
        base["caveats"].append(f"The chart has {gaps} non-daily step(s); windows are counted in points, as volume_volatility does.")
    # first origin with a measured monthly sigma: volume_volatility needs >= 90 points for two monthly returns
    first = 3 * WINDOW_DAYS - 1
    last = len(points) - 1
    origins = sorted(i for i in range(last, first - 1, -step_days))
    live = _run_variant(points, origins, growth_yoy=growth_yoy, horizons=horizons, assumptions=reg, drift="registry")
    measured = _run_variant(points, origins, growth_yoy=growth_yoy, horizons=horizons, assumptions=reg, drift="measured")
    base.update({
        "n_origins": len({r["origin_date"] for r in live["rows"]}),
        "first_origin": live["rows"][0]["origin_date"] if live["rows"] else None,
        "last_origin": live["rows"][-1]["origin_date"] if live["rows"] else None,
        "rows": live["rows"], "by_horizon": live["by_horizon"],
        "variants": {"measured_drift": {"by_horizon": measured["by_horizon"], "rows": measured["rows"]}},
    })
    # Neutral split at the middle origin (no date chosen by eye): does calibration differ early vs late in the sample?
    dates = sorted({r["origin_date"] for r in live["rows"]})
    if len(dates) >= 4:
        cut = dates[len(dates) // 2]
        base["by_period"] = {
            "split_origin_date": cut,
            "rule": "origins before vs from the middle origin date",
            "early": {str(h): _horizon_stats([r for r in live["rows"] if r["h"] == h and r["origin_date"] < cut]) for h in horizons},
            "late": {str(h): _horizon_stats([r for r in live["rows"] if r["h"] == h and r["origin_date"] >= cut]) for h in horizons},
        }
    base["calibrated"] = _verdict(live["by_horizon"])
    base["headline"] = _headline(base)
    if with_engines:
        try:
            base.update(_engines_block(points, origins, live, growth_yoy=growth_yoy, horizons=horizons, assumptions=reg))
        except Exception as exc:  # noqa: BLE001 - the variant engine must never cost the run its base backtest
            base.update({"engines": None, "comparison": None, "valuation_effect": None, "engines_error": f"{type(exc).__name__}: {exc}"})
    return base


def _verdict(by_h: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Calibrated at a horizon when the exact binomial test does not reject 80% coverage at the 10% level."""
    per = {}
    for h, s in by_h.items():
        p = s.get("binom_p_vs_80")
        per[h] = None if p is None else bool(p >= 0.10)
    evaluated = [v for v in per.values() if v is not None]
    return {"per_horizon": per, "all": bool(evaluated) and all(evaluated), "rule": "exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10"}


def _pct(x: Any) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _headline(bt: Mapping[str, Any]) -> str:
    parts = []
    for h, s in (bt.get("by_horizon") or {}).items():
        if s.get("n"):
            parts.append(f"{h}m {s['inside']}/{s['n']} ({_pct(s['coverage_p10_p90'])})")
    s1 = (bt.get("by_horizon") or {}).get("1") or {}
    bias = s1.get("median_ratio_realized_to_p50")
    bias_txt = "" if bias is None else (
        f"; at 1 month the median realized/forecast-median ratio is {bias:.2f}x ("
        + ("the model under-predicts" if bias > 1 else "the model over-predicts" if bias < 1 else "no bias") + ")"
    )
    return f"P10-P90 coverage (target 80%): {', '.join(parts) or 'no scored forecasts'}{bias_txt}."


# ---------------------------------------------------------------------------- second engine: block bootstrap
_BOOT_ROW_MODES: tuple[str, ...] = ("resampled", "registry")


def _bootstrap_rows(points: list[tuple[int, float]], origins: list[int], *, growth_yoy: float, horizons: Sequence[int],
                    block_rule: str) -> tuple[dict[str, list[dict[str, Any]]], list[float]]:
    """Score the bootstrap on the GBM's origins and targets. Rows per drift convention, plus the mean block length per origin."""
    last = len(points) - 1
    values = np.array([v for _, v in points], dtype=float)
    days = {int(h): int(round(h * DAYS_PER_MONTH)) for h in horizons}
    rows: dict[str, list[dict[str, Any]]] = {m: [] for m in _BOOT_ROW_MODES}
    blocks: list[float] = []
    for i in origins:
        need = [d for d in days.values() if i + d <= last]
        if not need:
            continue
        fc = vb.forecast_at_origin(values[: i + 1], origin_ts=points[i][0], horizon_days=need, growth_yoy=growth_yoy, block_rule=block_rule)
        if fc is None:
            continue
        blocks.append(float(fc["mean_block_days"]))
        for h, d in days.items():
            j = i + d
            if j > last:
                continue
            realized = sum(v for _, v in points[j - WINDOW_DAYS + 1: j + 1])
            if realized <= 0:
                continue
            for mode in _BOOT_ROW_MODES:
                smp = fc["horizons"][d][mode]
                if smp is None:
                    continue
                p10, p50, p90 = (float(x) for x in np.quantile(smp, [0.10, 0.50, 0.90]))
                rows[mode].append({
                    "origin_date": _iso_day(points[i][0]), "target_date": _iso_day(points[j][0]), "h": h,
                    "v0_30d_usd": fc["v0_30d_usd"], "last_day_usd": fc["last_day_usd"], "n_changes": fc["n_changes"],
                    "mean_block_days": fc["mean_block_days"],
                    "p10": p10, "p50": p50, "p90": p90, "mean": float(smp.mean()),
                    "realized_30d_usd": realized, "inside": p10 <= realized <= p90,
                    "log_error": math.log(realized / p50),
                    "pit": (float(np.searchsorted(smp, realized, side="right")) + 0.5) / (smp.size + 1.0),
                })
    return rows, blocks


def _band_widths(rows: list[dict[str, Any]], horizons: Sequence[int]) -> dict[str, float | None]:
    """Median ln(P90 / P10) per horizon: the sharpness of the band (a wider band covers more for a trivial reason)."""
    out: dict[str, float | None] = {}
    for h in horizons:
        w = [math.log(r["p90"] / r["p10"]) for r in rows if r["h"] == h and r["p10"] > 0]
        out[str(h)] = median(w) if w else None
    return out


def _scored(rows: list[dict[str, Any]], horizons: Sequence[int]) -> dict[str, Any]:
    by_h = {str(h): _horizon_stats([r for r in rows if r["h"] == h]) for h in horizons}
    return {"by_horizon": by_h, "calibrated": _verdict(by_h), "median_band_width_log": _band_widths(rows, horizons)}


def _block_summary(blocks: list[float]) -> dict[str, float] | None:
    return {"min": min(blocks), "median": median(blocks), "max": max(blocks)} if blocks else None


def _test_power(n: int, target: float = TARGET_COVERAGE, level: float = 0.10) -> dict[str, Any] | None:
    """What the exact binomial test can and cannot see at sample size n: its acceptance region and its rejection rates."""
    if n <= 0:
        return None
    pvals = [_binom_two_sided_p(k, n, target) for k in range(n + 1)]
    accept = [k for k, p in enumerate(pvals) if p is not None and p >= level]

    def _reject_prob(c: float) -> float:
        return sum(math.comb(n, k) * c**k * (1 - c) ** (n - k) for k in range(n + 1) if k not in accept)

    return {
        "n": n, "level": level, "accept_min": min(accept) if accept else None, "accept_max": max(accept) if accept else None,
        "reject_prob_if_true_60": _reject_prob(0.60), "reject_prob_if_true_70": _reject_prob(0.70),
        "reject_prob_if_true_80": _reject_prob(target),
    }


def _cov_text(by_h: Mapping[str, Mapping[str, Any]]) -> str:
    p_txt = lambda p: "<0.01" if p < 0.005 else f"{p:.2f}"  # noqa: E731
    parts = [f"{h}m {s['inside']}/{s['n']} ({_pct(s['coverage_p10_p90'])}, p {p_txt(s['binom_p_vs_80'])})" for h, s in by_h.items() if s.get("n")]
    return ", ".join(parts) or "no scored forecasts"


def _comparison(gbm: Mapping[str, Any], boot: Mapping[str, Any]) -> dict[str, Any]:
    g_by, b_by = gbm["by_horizon"], boot["by_horizon"]
    g_flag, b_flag = gbm["calibrated"]["per_horizon"], boot["calibrated"]["per_horizon"]
    per: dict[str, Any] = {}
    for h in b_by:
        gw, bw = (gbm["median_band_width_log"] or {}).get(h), (boot["median_band_width_log"] or {}).get(h)
        per[h] = {
            **{name: {
                "n": s.get("n", 0), "inside": s.get("inside", 0), "coverage_p10_p90": s.get("coverage_p10_p90"),
                "binom_p_vs_80": s.get("binom_p_vs_80"), "calibrated": flag.get(h),
                "median_ratio_realized_to_p50": s.get("median_ratio_realized_to_p50"),
                "below_p10": s.get("below_p10", 0), "above_p90": s.get("above_p90", 0),
            } for name, s, flag in (("gbm", g_by.get(h) or {}, g_flag), ("block_bootstrap", b_by[h], b_flag))},
            "band_width_ratio_bootstrap_to_gbm": (bw / gw) if (gw and bw) else None,
        }
    scored = [h for h, s in b_by.items() if s.get("n")]
    ok = [h for h in scored if b_flag.get(h) is True]
    rejected = [h for h in scored if b_flag.get(h) is False]
    over = [h for h in rejected if b_by[h]["coverage_p10_p90"] > TARGET_COVERAGE]
    under = [h for h in rejected if h not in over]
    g_scored = [h for h, s in g_by.items() if s.get("n")]
    g_rejected = [h for h in g_scored if g_flag.get(h) is False]
    first = scored[0] if scored else None
    n1 = b_by[first]["n"] if first else 0
    ratios = [per[h]["band_width_ratio_bootstrap_to_gbm"] for h in scored if per[h]["band_width_ratio_bootstrap_to_gbm"] is not None]
    width = "" if not ratios else (
        f"{min(ratios):.1f}x" if max(ratios) - min(ratios) < 0.05 else f"{min(ratios):.1f}x to {max(ratios):.1f}x"
    ) + " the GBM's log width"
    b_txt, g_txt = _cov_text(b_by), _cov_text(g_by)
    months = lambda hs: " and ".join(f"{h}m" for h in hs)  # noqa: E731
    gbm_side = (
        f"the GBM is rejected at {len(g_rejected)} of {len(g_scored)} horizons ({g_txt})" if g_rejected
        else f"the GBM is not rejected ({g_txt})"
    )
    if not scored:
        outcome, headline = "not_scored", "The block bootstrap produced no scored forecasts, so it neither answers nor repeats the GBM's failure."
    elif not rejected:
        outcome = "bootstrap_passes_low_power"
        headline = (
            f"Block-bootstrap P10-P90 coverage is not rejected against {_pct(TARGET_COVERAGE)} at any scored horizon ({b_txt}) while {gbm_side}; "
            f"with {n1} origins and overlapping forecasts beyond one month the test has low power, so this is weak evidence of calibration"
            + (f", and the bootstrap band is {width}" if width else "") + "."
        )
    else:
        outcome = "bootstrap_fails" if not ok else "bootstrap_mixed"
        why = []
        if over:
            why.append(f"over-coverage at {months(over)}")
        if under:
            why.append(f"under-coverage at {months(under)}")
        passes = "" if not ok else (
            f"; the pass at {months(ok)} rests on {' and '.join(str(b_by[h]['n']) for h in ok)} overlapping forecasts, which is weak evidence"
            if all(h != "1" for h in ok) else f"; the pass at {months(ok)} rests on about {n1} origins, which is weak evidence"
        )
        wide = "" if not width else (
            f"; its band is {width}, so it covers by being wide, not by being sharp" if over and not under else f"; its band is {width}"
        )
        headline = (
            f"The block bootstrap does not repair the volume engine: P10-P90 coverage ({b_txt}) is rejected against {_pct(TARGET_COVERAGE)} for "
            f"{' and '.join(why)}{passes}{wide}; {gbm_side}"
            + (", so the two engines bracket realized dispersion and neither is calibrated." if over and not under and g_rejected else ".")
        )
    return {
        "headline": headline, "outcome": outcome,
        "failure_direction": None if not rejected else "over_coverage" if not under else "under_coverage" if not over else "both",
        "per_horizon": per, "power_1m": _test_power(n1) if first else None,
        "power_horizon_months": int(first) if first else None,
        "same_sample": all((g_by.get(h) or {}).get("n") == b_by[h].get("n") for h in b_by),
    }


def _ratios(q: Mapping[str, float], denom: float) -> dict[str, float]:
    return {f"{k}": float(q[k]) / denom for k in ("p10", "p50", "p90", "mean")}


def _forward_volume_effect(points: list[tuple[int, float]], *, growth_yoy: float, assumptions: Mapping[str, Assumption] | None) -> dict[str, Any] | None:
    """30-day volume ``FORWARD_HORIZON_MONTHS`` after the latest complete day, as multiples of the current 30-day volume, per engine."""
    h = FORWARD_HORIZON_MONTHS
    fc = forecast_at_origin(points, growth_yoy=growth_yoy, horizons=[h], assumptions=assumptions)
    if fc is None:
        return None
    v30 = float(fc["v0_30d_usd"])
    d = int(round(h * DAYS_PER_MONTH))
    boot = vb.forecast_at_origin([v for _, v in points], origin_ts=points[-1][0], horizon_days=[d], growth_yoy=growth_yoy)
    out: dict[str, Any] = {
        "origin_date": fc["origin_date"], "current_30d_usd": v30, "horizon_months": h, "horizon_days": d,
        "gbm": {**_ratios(fc["horizons"][h], v30), "sigma_volume_monthly": fc["sigma_volume_monthly"], "drift": "registry"},
        "block_bootstrap_registry_drift": None, "block_bootstrap_resampled_drift": None,
        "unit": "multiple of the current trailing 30-day volume",
    }
    if boot is not None:
        for key, mode in (("block_bootstrap_registry_drift", "registry"), ("block_bootstrap_resampled_drift", "resampled")):
            smp = boot["horizons"][d][mode]
            if smp is not None:
                q = np.quantile(smp, [0.10, 0.50, 0.90])
                out[key] = {"p10": float(q[0]) / v30, "p50": float(q[1]) / v30, "p90": float(q[2]) / v30, "mean": float(smp.mean()) / v30}
        out.update({"mean_block_days": boot["mean_block_days"], "n_changes": boot["n_changes"], "last_day_usd": boot["last_day_usd"],
                    "daily_mean_log_change": boot["daily_mean_log_change"]})
    return out


def _valuation_headline(ve: Mapping[str, Any], comparison: Mapping[str, Any] | None = None) -> str:
    """One sentence: what swapping the engine does to the forward distribution, and how far to trust it given the backtest."""
    vol = ve.get("volume_12m") or {}
    g, b = vol.get("gbm"), vol.get("block_bootstrap_registry_drift")
    if not (isinstance(g, Mapping) and isinstance(b, Mapping)):
        return "The valuation uses the GBM; the bootstrap's forward volume band could not be computed in this run."

    def spread(q: Mapping[str, float]) -> float:
        return math.log(q["p90"] / q["p10"])

    rel = spread(b) / spread(g) if spread(g) > 0 else float("nan")
    txt = (
        f"The valuation uses the GBM. At the same expected path the bootstrap puts 30-day volume 12 months out at "
        f"{b['p10']:.2f}x / {b['p50']:.2f}x / {b['p90']:.2f}x of current (P10 / P50 / P90) against the GBM's "
        f"{g['p10']:.2f}x / {g['p50']:.2f}x / {g['p90']:.2f}x, a band {rel:.1f}x as wide in log terms"
    )
    fdv = ve.get("fdv") or {}
    if fdv.get("computed"):
        r = fdv["ratio_to_gbm"]
        txt += f"; through the same Monte Carlo FDV P10 / P50 / P90 becomes {r['p10']:.2f}x / {r['p50']:.2f}x / {r['p90']:.2f}x of the base"
    else:
        txt += "; the FDV effect is not computed"
    outcome = (comparison or {}).get("outcome")
    direction = (comparison or {}).get("failure_direction")
    if direction == "over_coverage":
        txt += (
            ". The backtest rejects the bootstrap for over-coverage, so read this as a stress bound on volume dispersion (with the mean "
            "path held fixed, a wider distribution lowers the median), not as a better central estimate"
        )
    elif outcome == "bootstrap_passes_low_power":
        txt += ". The bootstrap is not rejected out of sample but on a small sample, so this is a variant to weigh, not a replacement"
    elif outcome in ("bootstrap_fails", "bootstrap_mixed"):
        txt += ". The backtest rejects the bootstrap as well, so this is a sensitivity, not a better estimate"
    return txt + "."


def _engines_block(points: list[tuple[int, float]], origins: list[int], live: Mapping[str, Any], *, growth_yoy: float,
                   horizons: Sequence[int], assumptions: Mapping[str, Assumption] | None) -> dict[str, Any]:
    """``engines`` (GBM as already scored, block bootstrap and its variants), ``comparison`` and ``valuation_effect``."""
    rows, blocks = _bootstrap_rows(points, origins, growth_yoy=growth_yoy, horizons=horizons, block_rule="politis_white")
    rot_rows, rot_blocks = _bootstrap_rows(points, origins, growth_yoy=growth_yoy, horizons=horizons, block_rule="rule_of_thumb")
    gbm = {
        "label": "GBM with measured sigma and registry drift (the engine the valuation uses)", "drift": "registry",
        "used_by_valuation": True, "by_horizon": live["by_horizon"], "calibrated": _verdict(live["by_horizon"]),
        "median_band_width_log": _band_widths(live["rows"], horizons),
    }
    boot = {
        "label": "Stationary block bootstrap of daily log-changes, resampled drift", "drift": "resampled",
        "used_by_valuation": False, "method": vb.METHOD, "block_length_rule": "politis_white", "n_paths": vb.N_PATHS,
        "seed": vb.SEED, "lookback_days": vb.LOOKBACK_DAYS, "mean_block_days": _block_summary(blocks),
        **_scored(rows["resampled"], horizons), "rows": rows["resampled"],
        "variants": {
            "registry_drift": {
                "label": "Block bootstrap, demeaned and rescaled to the GBM's expected path (shape only; the form fed to the Monte Carlo)",
                **_scored(rows["registry"], horizons),
            },
            "rule_of_thumb_blocks": {
                "label": "Sensitivity: mean block length n^(1/3) instead of the Politis-White selector (resampled drift)",
                "mean_block_days": _block_summary(rot_blocks), **_scored(rot_rows["resampled"], horizons),
            },
        },
        "caveats": list(vb.CAVEATS),
    }
    ve: dict[str, Any] = {
        "engine_used_by_valuation": "gbm",
        "volume_12m": _forward_volume_effect(points, growth_yoy=growth_yoy, assumptions=assumptions),
        "fdv": {"computed": False, "reason": "needs the snapshot's SOTP inputs; computed by backtest_from_raw"},
    }
    comparison = _comparison(gbm, boot)
    ve["headline"] = _valuation_headline(ve, comparison)
    return {
        "engines": {"target_coverage": TARGET_COVERAGE, "rule": gbm["calibrated"]["rule"], "gbm": gbm, "block_bootstrap": boot},
        "comparison": comparison, "valuation_effect": ve, "engines_error": None,
    }


def bootstrap_claim(bt: Mapping[str, Any]) -> dict[str, Any] | None:
    """Scorecard row for the block-bootstrap engine: DERIVED only when its coverage is not rejected at every scored horizon.

    Fields claim / status / value / source / confidence / note. None when the engine was not computed.
    """
    engines = bt.get("engines")
    if not isinstance(engines, Mapping) or not isinstance(engines.get("block_bootstrap"), Mapping):
        return None
    boot, gbm = engines["block_bootstrap"], engines.get("gbm") or {}
    b_by, g_by = boot.get("by_horizon") or {}, gbm.get("by_horizon") or {}
    scored = [h for h, s in b_by.items() if s.get("n")]
    flags = (boot.get("calibrated") or {}).get("per_horizon") or {}
    ok = bool(scored) and all(flags.get(h) is True for h in scored)
    per = (bt.get("comparison") or {}).get("per_horizon") or {}
    first = scored[0] if scored else None
    ratio = (per.get(first) or {}).get("band_width_ratio_bootstrap_to_gbm") if first else None
    shape = ((boot.get("variants") or {}).get("registry_drift") or {}).get("by_horizon") or {}
    power = (bt.get("comparison") or {}).get("power_1m") or {}
    value = (
        f"block bootstrap {_cov_text(b_by)}; GBM {_cov_text(g_by)}; bootstrap at the GBM's expected path (shape only) {_cov_text(shape)}"
        + ("" if ratio is None else f"; bootstrap band {ratio:.1f}x the GBM's log width at {first}m")
        + f"; {bt.get('n_origins', 0)} monthly origins {bt.get('first_origin')} to {bt.get('last_origin')}"
    )
    sha = f" sha256 {str(bt['source_sha256'])[:12]}..." if bt.get("source_sha256") else ""
    note = (
        "Inside P10-P90 against an 80% target, exact two-sided binomial p. Low power: "
        + (f"at n = {power['n']} the test accepts {power.get('accept_min')} to {power.get('accept_max')} hits and rejects a 70%-coverage engine only "
           f"{_pct(power.get('reject_prob_if_true_70'))} of the time; " if power.get("n") else "")
        + "3m and 6m forecasts overlap. Block length (Politis-White) and path count were fixed before coverage was computed; nothing is tuned. "
        "The valuation still uses the GBM; this row grades a parallel variant and tests the volume distribution only."
    )
    return {
        "claim": "A block-bootstrap volume engine (fat tails, autocorrelation) is calibrated out of sample where GBM is not",
        "status": "DERIVED" if ok else "NOT_SUPPORTED",
        "value": value,
        "source": f"{bt.get('source')}{sha}; valuo.models.volume_bootstrap (seed {boot.get('seed')}, {boot.get('n_paths')} paths per origin)",
        "confidence": "low",
        "note": note,
    }


# ---------------------------------------------------------------------------- loader for reproduce.py
def load_dexs_chart(raw_dir: Path | None, snapshot: Mapping[str, Any]) -> tuple[Any, str, str | None]:
    """(chart, source, sha256): the full DefiLlama dexs chart from the run's persisted raw payload when present,
    else the 365-day volume column of ``intents_forensics.fees.daily_series`` already in the snapshot."""
    if raw_dir is not None:
        path = Path(raw_dir) / DEXS_RAW_NAME
        if path.is_file():
            data = path.read_bytes()
            chart = (json.loads(data) or {}).get("totalDataChart")
            if isinstance(chart, list) and chart:
                return chart, f"defillama:dexs/near-intents totalDataChart (raw/{DEXS_RAW_NAME})", hashlib.sha256(data).hexdigest()
    fees = (snapshot.get("intents_forensics") or {}).get("fees") or {}
    series = fees.get("daily_series") or []
    cols = fees.get("daily_series_columns") or ["ts_unix_s", "fees_usd", "revenue_usd", "volume_usd"]
    iv = cols.index("volume_usd") if "volume_usd" in cols else 3
    chart = [[r[0], r[iv]] for r in series if isinstance(r, (list, tuple)) and len(r) > iv]
    return chart, "intents_forensics.fees.daily_series volume column (365 days; raw dexs payload not found)", None


def backtest_from_raw(snapshot: Mapping[str, Any], raw_dir: Path | None = None) -> dict[str, Any]:
    """Run the backtest for a snapshot dict: growth and fallback assumptions are the ones the run recorded."""
    reg = dict(A.ASSUMPTIONS)
    for a in snapshot.get("assumptions") or []:
        key = a.get("key") if isinstance(a, Mapping) else getattr(a, "key", None)
        if key in reg:
            reg[key] = Assumption.model_validate(a) if isinstance(a, Mapping) else a
    chart, source, sha = load_dexs_chart(raw_dir, snapshot)
    as_of = None
    gen = snapshot.get("generated_at_utc")
    if isinstance(gen, str):
        try:
            as_of = int(datetime.fromisoformat(gen.replace("Z", "+00:00")).timestamp())
        except ValueError:
            as_of = None
    bt = run_backtest(chart, growth_yoy=A.value("public_volume_growth_yoy", reg), assumptions=reg, as_of_ts=as_of, source=source,
                      source_sha256=sha, with_engines=True)
    ve = bt.get("valuation_effect")
    if isinstance(ve, dict):
        # FDV under bootstrap volume paths: a separate code path that reads the snapshot and never writes to sotp.
        try:
            points = [p for p in _chart_points(chart) if as_of is None or p[0] + 86400 <= as_of]
            ve["fdv"] = vb.fdv_effect(snapshot, [v for _, v in points], origin_ts=points[-1][0])
        except Exception as exc:  # noqa: BLE001 - never fatal; the volume-distribution effect above still stands
            ve["fdv"] = {"computed": False, "reason": f"{type(exc).__name__}: {exc}"}
        ve["headline"] = _valuation_headline(ve, bt.get("comparison"))
    return bt
