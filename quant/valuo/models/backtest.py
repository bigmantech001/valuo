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

from valuo import assumptions as A
from valuo.collectors.intents_forensics import _chart_points, volume_volatility
from valuo.models.sotp_valuation import DAYS_PER_MONTH, _sigmas
from valuo.schemas import Assumption

__all__ = [
    "HORIZONS_MONTHS", "STEP_DAYS", "WINDOW_DAYS", "SIGMA_LOOKBACK_DAYS", "TARGET_COVERAGE", "PIT_BINS",
    "NOT_TESTED", "forecast_at_origin", "lognormal_bands", "run_backtest", "backtest_from_raw", "load_dexs_chart",
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
) -> dict[str, Any]:
    """Rolling-origin backtest of the volume engine on a daily USD chart [[unix_s, usd], ...]. Pure.

    ``as_of_ts`` drops days that were not complete at that instant (the partial current UTC day). Origins start
    at the first day where the live calibration has a measured monthly sigma (two monthly returns, 90 days) and
    step back from the last complete day every ``step_days``.
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
    return run_backtest(chart, growth_yoy=A.value("public_volume_growth_yoy", reg), assumptions=reg, as_of_ts=as_of, source=source, source_sha256=sha)
