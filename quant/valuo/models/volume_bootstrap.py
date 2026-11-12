"""Block-bootstrap volume engine: a second, parallel volume process tested next to the SOTP GBM.

The walk-forward backtest (``valuo.models.backtest``) rejects the GBM's P10-P90 band. This module supplies a
non-parametric alternative and nothing else; the valuation keeps the GBM and no headline number moves.

Method (stationary bootstrap, Politis and Romano 1994):
  * data: realized daily log-changes ln(V_t / V_{t-1}) of NEAR Intents volume over the trailing ``LOOKBACK_DAYS``
    days up to and including the origin (the window the GBM's sigma uses); non-positive pairs are skipped;
  * resampling: blocks start at a uniformly drawn day, run for a Geometric(1/b) number of days and wrap around
    the end of the window (circular), so a resampled path is stationary and keeps the within-block ordering of
    the data: its fat tails and its short-range autocorrelation;
  * mean block length b: the automatic selector of Politis and White (2004) with the Patton, Politis and White
    (2009) correction, computed on the same lookback and capped at min(3 sqrt(n), n/3). The rule was fixed from
    the autocorrelation of the series, before any coverage number was computed: daily volume carries
    day-to-day noise that reverses (the 30-day log-change variance is under a tenth of 30 x the daily
    variance), so the textbook n^(1/3) rule would chain short blocks and overstate horizon variance. The
    n^(1/3) result is still reported as a sensitivity so the dependence on block length is visible;
  * path count: ``N_PATHS`` = 10,000, the valuation Monte Carlo's default; seed 20261114 mixed with the origin
    timestamp, so an origin's forecast does not depend on which other origins are scored.

Two drift conventions are scored:
  * ``resampled`` (headline): each path continues the realized daily series from the origin day,
    V_{t+d} = V_t exp(sum of d resampled log-changes); the forecast 30-day volume at horizon H days is the sum of
    days H-29..H of the path. Drift is whatever the lookback held. No registry input, no look-ahead.
  * ``registry`` (shape only): the resampled log-changes are demeaned and the forecast is rescaled so its mean
    equals the live GBM's mean, the trailing 30-day sum x (1+g)^(days/365.25). Same starting volume and expected path as the live model;
    only the shape of the distribution differs. This is the form that can be fed to the valuation Monte Carlo.

Limits: about 20 origins, overlapping beyond one month, so a pass is weak evidence; the bootstrap can only draw
changes that occurred in the lookback, so it cannot forecast a regime the last year did not contain; with a mean
block near the cap the lookback holds only a handful of independent blocks; the origin-day anchor of the
``resampled`` form carries one day's noise. Nothing here is tuned to hit 80%: with about 20 origins any tuning
of block length, lookback or path count on coverage would be overfitting.

Pure numpy, no network, no file IO.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from valuo.models.sotp_valuation import (
    DAYS_PER_MONTH,
    REGIME_GLIDEPATH,
    _in,
    _issuance_path,
    _value_paths,
    compound_issuance,
    percentiles,
    simulate_paths,
)

__all__ = [
    "SEED", "N_PATHS", "LOOKBACK_DAYS", "WINDOW_DAYS", "MIN_CHANGES", "BLOCK_RULES", "METHOD", "CAVEATS",
    "daily_log_changes", "optimal_block_length", "rule_of_thumb_block_length", "mean_block_length",
    "stationary_bootstrap_indices", "bootstrap_log_paths", "forecast_at_origin", "fdv_effect", "memo_markdown",
]

SEED: int = 20261114
N_PATHS: int = 10_000          # the valuation Monte Carlo's default path count
LOOKBACK_DAYS: int = 365       # same trailing window as the GBM's sigma (backtest.SIGMA_LOOKBACK_DAYS)
WINDOW_DAYS: int = 30          # the live model's 30-day volume window
MIN_CHANGES: int = 30          # fewer daily log-changes than this: no forecast
BLOCK_RULES: tuple[str, ...] = ("politis_white", "rule_of_thumb")
_CHUNK: int = 2_000            # paths per chunk on long horizons (bounds memory)

METHOD: str = (
    "Stationary block bootstrap (Politis-Romano: geometric block lengths, circular wrap) of realized daily log-changes of volume "
    f"over the trailing {LOOKBACK_DAYS} days up to the origin. Mean block length: Politis-White (2004) automatic selector with the "
    "Patton-Politis-White (2009) correction on that lookback, capped at min(3 sqrt(n), n/3); rule fixed from the series' "
    f"autocorrelation before any coverage was computed. {N_PATHS:,} paths (the valuation Monte Carlo's count), seed {SEED} mixed "
    "with the origin timestamp. Each path continues the daily series from the origin day; the forecast is the sum of the last "
    f"{WINDOW_DAYS} days of the path at the horizon, scored against the same realized 30-day sums as the GBM."
)

CAVEATS: tuple[str, ...] = (
    "Nothing in the bootstrap is tuned to reach 80% coverage. With about 20 origins, choosing block length, lookback or path "
    "count by coverage would be overfitting; the block rule and path count were fixed first and the n^(1/3) block rule is shown "
    "only as a sensitivity.",
    "Low power: the exact binomial test on about 20 one-month origins accepts a wide range of true coverage, and 3- and 6-month "
    "forecasts overlap, so a pass is weak evidence of calibration, not proof.",
    "A bootstrap can only replay changes that occurred in the lookback. It widens the band where the past year was volatile and "
    "cannot anticipate a regime the lookback did not contain.",
    "Daily volume carries day-to-day noise that reverses. Blocks shorter than that reversal overstate horizon variance, so part "
    "of any coverage gain can come from a wider band, not a better-shaped one; the band-width ratio is reported for that reason.",
    "The path starts at the origin day's volume, one noisy observation, and the registry-drift form holds the mean path fixed, so "
    "a wider distribution mechanically lowers its median. Both are stated properties of the design, not fitted choices.",
    "No second design was tried after these results. Resampling changes of the 30-day sum instead of daily volume would remove "
    "the day-to-day noise, but choosing between engine designs on about 20 origins is the tuning this test rules out; it is "
    "left as a stated next test.",
    "The valuation still runs on the GBM. The bootstrap is a parallel variant; no headline figure uses it.",
)


# ---------------------------------------------------------------------------- data and block length
def daily_log_changes(values: Sequence[float] | np.ndarray, lookback_days: int = LOOKBACK_DAYS) -> np.ndarray:
    """ln(V_t / V_{t-1}) over the last ``lookback_days`` values; pairs with a non-positive or non-finite value are skipped."""
    v = np.asarray(values, dtype=float)[-int(lookback_days):]
    if v.size < 2:
        return np.empty(0)
    prev, cur = v[:-1], v[1:]
    ok = np.isfinite(prev) & np.isfinite(cur) & (prev > 0) & (cur > 0)
    return np.log(cur[ok] / prev[ok])


def rule_of_thumb_block_length(n: int) -> float:
    """Textbook mean block length n^(1/3) (sensitivity only)."""
    return max(1.0, float(n) ** (1.0 / 3.0))


def optimal_block_length(x: Sequence[float] | np.ndarray) -> float:
    """Politis-White (2004) automatic mean block length for the stationary bootstrap, Patton-Politis-White (2009) form.

    b = (2 G^2 / D)^(1/3) n^(1/3) with G = sum_k lambda(k/M) |k| R(k), D = 2 g(0)^2, g(0) = sum_k lambda(k/M) R(k), where R is
    the sample autocovariance, lambda the flat-top kernel and M twice the first lag after which K_N consecutive
    autocorrelations are inside +/- 2 sqrt(log10(n)/n). Clipped to [1, ceil(min(3 sqrt(n), n/3))].
    """
    a = np.asarray(x, dtype=float)
    n = int(a.size)
    if n < 8:
        return 1.0
    eps = a - a.mean()
    var = float(eps @ eps) / n
    if not var > 0.0:
        return 1.0
    b_max = float(math.ceil(min(3.0 * math.sqrt(n), n / 3.0)))
    kn = max(5, int(math.ceil(math.sqrt(math.log10(n)))))
    m_max = int(math.ceil(math.sqrt(n))) + kn
    top = min(n - 1, m_max + kn)
    acv = np.array([float(eps[k:] @ eps[: n - k]) / n for k in range(top + 1)])
    rho = np.abs(acv / var)
    crit = 2.0 * math.sqrt(math.log10(n) / n)
    m_hat: int | None = None
    for m in range(1, m_max + 1):
        if m + kn > top:
            break
        if bool(np.all(rho[m + 1: m + kn + 1] < crit)):
            m_hat = m
            break
    big_m = min(2 * m_hat, m_max) if m_hat is not None else m_max
    big_m = max(1, min(big_m, top))
    g = 0.0
    lr = float(acv[0])
    for k in range(1, big_m + 1):
        lam = 1.0 if k / big_m <= 0.5 else 2.0 * (1.0 - k / big_m)
        g += 2.0 * k * lam * float(acv[k])
        lr += 2.0 * lam * float(acv[k])
    d_sb = 2.0 * lr * lr
    if not d_sb > 0.0:
        return b_max
    b = (2.0 * g * g / d_sb) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    if not math.isfinite(b):
        return b_max
    return float(min(max(b, 1.0), b_max))


def mean_block_length(changes: np.ndarray, rule: str = "politis_white") -> float:
    if rule == "politis_white":
        return optimal_block_length(changes)
    if rule == "rule_of_thumb":
        return rule_of_thumb_block_length(int(changes.size))
    raise ValueError(f"unknown block rule {rule!r}")


# ---------------------------------------------------------------------------- resampling
def stationary_bootstrap_indices(n: int, n_paths: int, n_steps: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """(n_paths, n_steps) indices into a length-``n`` series: geometric block lengths with mean ``mean_block``, circular wrap."""
    if n < 1 or n_paths < 1 or n_steps < 1:
        raise ValueError("n, n_paths and n_steps must be >= 1")
    p = 1.0 / max(float(mean_block), 1.0)
    new = rng.random((n_paths, n_steps)) < p
    new[:, 0] = True
    starts = rng.integers(0, n, size=int(new.sum()), dtype=np.int64)
    block_id = np.cumsum(new.ravel()) - 1                      # every row opens a block, so ids never leak across rows
    pos = np.arange(n_steps, dtype=np.int64)
    last = np.maximum.accumulate(np.where(new, pos[None, :], 0), axis=1)
    return (starts[block_id].reshape(n_paths, n_steps) + pos[None, :] - last) % n


def bootstrap_log_paths(changes: np.ndarray, n_steps: int, *, mean_block: float, n_paths: int, rng: np.random.Generator) -> np.ndarray:
    """Cumulative sums of block-resampled ``changes``: (n_paths, n_steps) log growth since the origin."""
    idx = stationary_bootstrap_indices(int(changes.size), n_paths, n_steps, mean_block, rng)
    return np.cumsum(changes[idx], axis=1)


def _exp(x: np.ndarray) -> np.ndarray:
    return np.exp(np.clip(x, -700.0, 700.0))


def _window_sum(level: np.ndarray, end_day: int, window: int) -> np.ndarray:
    """Sum of path days end_day-window+1 .. end_day (1-based days; column d-1 holds day d)."""
    lo = max(0, end_day - window)
    return level[:, lo:end_day].sum(axis=1)


def forecast_at_origin(
    values: Sequence[float] | np.ndarray,
    *,
    origin_ts: int,
    horizon_days: Sequence[int],
    growth_yoy: float | None = None,
    block_rule: str = "politis_white",
    n_paths: int = N_PATHS,
    seed: int = SEED,
    lookback_days: int = LOOKBACK_DAYS,
    window_days: int = WINDOW_DAYS,
) -> dict[str, Any] | None:
    """Bootstrap forecast of 30-day volume at each horizon (days), from ``values`` = daily volume up to and including the origin.

    Returns sorted sample arrays per horizon under both drift conventions (``registry`` is None without ``growth_yoy``), or
    None when the origin has fewer than ``window_days`` days, a non-positive last day or window, or fewer than ``MIN_CHANGES``
    usable log-changes. Deterministic in (seed, origin_ts, block_rule); reads nothing after the origin.
    """
    v = np.asarray(values, dtype=float)
    hs = sorted({int(h) for h in horizon_days if int(h) >= 1})
    if v.size < window_days or not hs:
        return None
    v30 = float(v[-window_days:].sum())
    last_day = float(v[-1])
    if not (v30 > 0.0 and last_day > 0.0 and math.isfinite(v30)):
        return None
    changes = daily_log_changes(v, lookback_days)
    if changes.size < MIN_CHANGES:
        return None
    b = mean_block_length(changes, block_rule)
    rng = np.random.default_rng([int(seed), int(origin_ts), BLOCK_RULES.index(block_rule)])
    s = bootstrap_log_paths(changes, hs[-1], mean_block=b, n_paths=int(n_paths), rng=rng)
    level = _exp(s)
    mu = float(changes.mean())
    level_c = _exp(s - mu * np.arange(1, hs[-1] + 1, dtype=float)[None, :]) if growth_yoy is not None else None
    out: dict[str, Any] = {
        "origin_ts": int(origin_ts), "v0_30d_usd": v30, "last_day_usd": last_day, "n_changes": int(changes.size),
        "mean_block_days": b, "block_rule": block_rule, "daily_mean_log_change": mu,
        "daily_sigma": float(changes.std(ddof=1)), "n_paths": int(n_paths), "horizons": {},
    }
    for h in hs:
        resampled = np.sort(last_day * _window_sum(level, h, window_days))
        registry = None
        if level_c is not None and growth_yoy is not None and growth_yoy > -1.0:
            x = _window_sum(level_c, h, window_days)
            registry = np.sort(v30 * (1.0 + growth_yoy) ** (h / (12.0 * DAYS_PER_MONTH)) * x / x.mean())
        out["horizons"][h] = {"resampled": resampled, "registry": registry}
    return out


# ---------------------------------------------------------------------------- valuation effect (FDV)
def _monthly_relative_paths(
    changes: np.ndarray, horizon_months: int, *, mean_block: float, n_paths: int, rng: np.random.Generator, scale: float = 1.0,
) -> np.ndarray:
    """(n_paths, H) monthly means of exp(scale x demeaned resampled log path), each month normalised to mean 1 over paths."""
    edges = [int(round(m * DAYS_PER_MONTH)) for m in range(horizon_months + 1)]
    n_days = edges[-1]
    trend = float(changes.mean()) * np.arange(1, n_days + 1, dtype=float)[None, :]
    out = np.empty((n_paths, horizon_months))
    for lo in range(0, n_paths, _CHUNK):
        hi = min(n_paths, lo + _CHUNK)
        s = bootstrap_log_paths(changes, n_days, mean_block=mean_block, n_paths=hi - lo, rng=rng)
        level = _exp(scale * (s - trend))
        for m in range(horizon_months):
            out[lo:hi, m] = level[:, edges[m]: edges[m + 1]].mean(axis=1)
    return out / out.mean(axis=0, keepdims=True)


def _revalue(inputs: Mapping[str, Any], sim: Mapping[str, Any], v_pub: np.ndarray, v_conf: np.ndarray) -> dict[str, Any]:
    """``sotp_valuation._value_paths`` with the arguments ``simulate_paths`` passes, on caller-supplied volume paths.

    Price, take-rate and issuance paths are the base run's. With ``sim``'s own volume paths this returns the base FDV
    bit for bit (``tests/test_volume_bootstrap.py``), which is what makes the bootstrap run a like-for-like swap.
    """
    horizon = int(inputs["horizon_months"])
    total_supply = float(inputs["total_supply"])
    issuance = compound_issuance(np.asarray(_issuance_path(inputs, horizon), dtype=float), total_supply)
    price0 = float(inputs["price_usd"])
    return _value_paths(
        v_pub=v_pub, v_conf=v_conf, v_pub0=float(_in(inputs, "v_pub_usd_day", "v_pub_daily_usd")),
        tau_pub_bps=sim["tau_pub"], tau_conf_bps=sim["tau_conf"], price=sim["price"],
        alpha=float(inputs["alpha_capture"]), discount_rate=float(inputs["discount_rate"]),
        terminal_multiple=float(inputs["terminal_multiple"]), conf_haircut=float(inputs["conf_haircut"]),
        gas_burn_near_day0=float(inputs["gas_burn_usd_day"]) / price0,
        state_lock_near_day0=float(inputs["state_lock_near_day"]),
        issuance_near_month=issuance, total_supply=total_supply,
    )


def _p3(arr: np.ndarray, denom: float = 1.0) -> dict[str, float]:
    q = np.quantile(np.asarray(arr, dtype=float), [0.10, 0.50, 0.90])
    return {"p10": float(q[0] / denom), "p50": float(q[1] / denom), "p90": float(q[2] / denom)}


def fdv_effect(snapshot: Mapping[str, Any], values: Sequence[float] | np.ndarray, *, origin_ts: int, seed: int = SEED) -> dict[str, Any]:
    """FDV percentiles when the valuation Monte Carlo's volume paths come from the bootstrap instead of the GBM.

    The base run is rebuilt from the snapshot (same inputs, seed and path count) and must reproduce
    ``sotp.fdv_percentiles``. The bootstrap run keeps the base price, take-rate and issuance paths and the base expected
    volume path (each month is normalised so E[V_t] = V_0 (1+g)^t, the mean-matching convention of ``simulate_paths``); only
    the dispersion of volume around that path changes: demeaned daily log-changes from the trailing lookback, block
    resampled, averaged within each month. The confidential leg uses an independent draw scaled by the model's
    ``confidential_sigma_multiplier``. ``sotp_valuation.py`` is not modified and nothing here writes back to ``sotp``.
    """
    from valuo.models.market_implied import inputs_from_snapshot  # local: market_implied is a sibling derived model

    sotp = snapshot.get("sotp") or {}
    cal = sotp.get("calibration") or {}
    if not sotp or not cal:
        return {"computed": False, "reason": "snapshot.sotp is absent"}
    inputs = inputs_from_snapshot(snapshot)
    conf_mult = float(cal.get("confidential_sigma_multiplier") or 1.0)
    inputs.update({
        "sigma_volume_monthly": float(cal["sigma_volume_monthly"]), "sigma_price_monthly": float(cal["sigma_price_monthly"]),
        "confidential_sigma_multiplier": conf_mult,
    })
    mc_seed, n_paths = int(sotp.get("seed") or seed), int(sotp.get("n_paths") or N_PATHS)
    horizon = int(inputs["horizon_months"])
    sim = simulate_paths(inputs, seed=mc_seed, n_paths=n_paths)
    base = percentiles(sim["fdv"])
    stored = sotp.get("fdv_percentiles") or {}
    reproduced = bool(stored) and all(
        isinstance(stored.get(k), (int, float)) and math.isclose(base[k], float(stored[k]), rel_tol=1e-9) for k in ("p10", "p50", "p90")
    )
    identity = bool(np.array_equal(_revalue(inputs, sim, sim["v_pub"], sim["v_conf"])["fdv"], sim["fdv"]))

    changes = daily_log_changes(values)
    if changes.size < MIN_CHANGES:
        return {"computed": False, "reason": f"{changes.size} daily log-changes in the lookback, fewer than {MIN_CHANGES}"}
    b = optimal_block_length(changes)
    v_pub0 = float(_in(inputs, "v_pub_usd_day", "v_pub_daily_usd"))
    v_conf0 = float(_in(inputs, "v_conf_usd_day", "v_conf_daily_usd"))
    t = np.arange(1, horizon + 1, dtype=float)[None, :]
    rng_pub = np.random.default_rng([int(seed), int(origin_ts), 10])
    rng_conf = np.random.default_rng([int(seed), int(origin_ts), 11])
    v_pub = v_pub0 * (1.0 + float(inputs["growth_monthly_pub"])) ** t * _monthly_relative_paths(
        changes, horizon, mean_block=b, n_paths=n_paths, rng=rng_pub)
    if v_conf0 > 0:
        v_conf = v_conf0 * (1.0 + float(inputs["growth_monthly_conf"])) ** t * _monthly_relative_paths(
            changes, horizon, mean_block=b, n_paths=n_paths, rng=rng_conf, scale=conf_mult)
    else:
        v_conf = np.zeros_like(v_pub)
    alt = percentiles(_revalue(inputs, sim, v_pub, v_conf)["fdv"])
    current = float(sotp.get("current_fdv_usd") or 0.0)
    return {
        "computed": True,
        "base_engine": "gbm", "variant_engine": "block_bootstrap (registry drift, mean-matched)",
        "seed_mc": mc_seed, "seed_bootstrap": int(seed), "n_paths": n_paths, "horizon_months": horizon,
        "mean_block_days": b, "n_changes": int(changes.size), "regime": str(inputs.get("regime", REGIME_GLIDEPATH)),
        "base_reproduces_snapshot": reproduced, "revalue_identity_holds": identity,
        "gbm": {k: base[k] for k in ("p10", "p50", "p90")},
        "block_bootstrap": {k: alt[k] for k in ("p10", "p50", "p90")},
        "ratio_to_gbm": {k: (alt[k] / base[k] if base[k] > 0 else None) for k in ("p10", "p50", "p90")},
        "current_fdv_usd": current or None,
        "gbm_p50_to_current": base["p50"] / current if current > 0 else None,
        "block_bootstrap_p50_to_current": alt["p50"] / current if current > 0 else None,
        "terminal_public_volume_ratio_to_start": {
            "gbm": _p3(sim["v_pub"][:, -1], v_pub0) if v_pub0 > 0 else None,
            "block_bootstrap": _p3(v_pub[:, -1], v_pub0) if v_pub0 > 0 else None,
        },
        "method": (
            "Base Monte Carlo rebuilt from the snapshot (same inputs, seed, path count). Bootstrap run: same price, take-rate and "
            "issuance paths and the same expected volume path; monthly volume = V_0 (1+g)^t x monthly mean of exp(demeaned "
            "block-resampled daily log path), normalised to mean 1 per month. Only the dispersion of volume changes."
        ),
    }


# ---------------------------------------------------------------------------- memo
def _fmt_pct(x: Any) -> str:
    return "n/a" if not isinstance(x, (int, float)) else f"{x * 100:.0f}%"


def _fmt_p(x: Any) -> str:
    return "n/a" if not isinstance(x, (int, float)) else ("<0.001" if x < 0.0005 else f"{x:.3f}" if x < 0.01 else f"{x:.2f}")


def _fmt_x(x: Any) -> str:
    return "n/a" if not isinstance(x, (int, float)) else f"{x:.2f}x"


def _fmt_usd(x: Any) -> str:
    if not isinstance(x, (int, float)):
        return "n/a"
    a = abs(x)
    if a >= 1e9:
        return f"${x / 1e9:,.2f}B"
    if a >= 1e6:
        return f"${x / 1e6:,.0f}M"
    return f"${x:,.0f}"


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]], align: Sequence[str]) -> str:
    sep = ["---:" if a == "r" else ":---" for a in align]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    lines.append("")
    return "\n".join(lines)


def _verdict_text(ok: Any) -> str:
    return "80% not rejected" if ok is True else "80% rejected" if ok is False else "not scored"


def _triple(d: Any, fmt: Any = _fmt_x) -> str:
    if not isinstance(d, Mapping):
        return "n/a"
    return f"{fmt(d.get('p10'))} / {fmt(d.get('p50'))} / {fmt(d.get('p90'))}"


def memo_markdown(data: Mapping[str, Any], snap_dict: Mapping[str, Any]) -> str:
    """Memo sub-section from ``snapshot.backtest``: coverage of both engines side by side, the headline, the valuation effect."""
    engines = data.get("engines")
    comparison = data.get("comparison") or {}
    if not isinstance(engines, Mapping) or not isinstance(engines.get("block_bootstrap"), Mapping):
        reason = data.get("engines_error")
        return "The block-bootstrap engine was not computed in this run" + (f" ({reason})." if reason else ".")
    gbm, bb = engines.get("gbm") or {}, engines["block_bootstrap"]
    target = engines.get("target_coverage", 0.8)
    parts: list[str] = []
    if comparison.get("headline"):
        parts.append(str(comparison["headline"]))

    def _row(label: str, h: str, s: Mapping[str, Any], ok: Any, width: Any) -> list[str]:
        return [
            label, f"{h}m", str(s.get("n", 0)), f"{s.get('inside', 0)}/{s.get('n', 0)}", _fmt_pct(s.get("coverage_p10_p90")),
            _fmt_p(s.get("binom_p_vs_80")), f"{s.get('below_p10', 0)} / {s.get('above_p90', 0)}",
            _fmt_x(s.get("median_ratio_realized_to_p50")), "n/a" if not isinstance(width, (int, float)) else f"{width:.2f}",
            _verdict_text(ok),
        ]

    per = comparison.get("per_horizon") or {}
    rows: list[list[str]] = []
    series: list[tuple[str, Mapping[str, Any]]] = [("GBM, registry drift (valuation engine)", gbm), ("Block bootstrap, resampled drift", bb)]
    variants = bb.get("variants") or {}
    if isinstance(variants.get("registry_drift"), Mapping):
        series.append(("Block bootstrap, registry drift (shape only)", variants["registry_drift"]))
    if isinstance(variants.get("rule_of_thumb_blocks"), Mapping):
        series.append(("Sensitivity: bootstrap, n^(1/3) blocks", variants["rule_of_thumb_blocks"]))
    for label, eng in series:
        by_h = eng.get("by_horizon") or {}
        flags = (eng.get("calibrated") or {}).get("per_horizon") or {}
        widths = eng.get("median_band_width_log") or {}
        for h, s in by_h.items():
            if isinstance(s, Mapping) and s.get("n"):
                rows.append(_row(label, str(h), s, flags.get(h), widths.get(h)))
    parts.append(_md_table(
        ["Engine", "Horizon", "n", "Inside", "Coverage", "Binomial p vs 80%", "Below P10 / above P90", "Realized / median", "Band width, ln(P90/P10)", "Verdict"],
        rows, ["l", "r", "r", "r", "r", "r", "r", "r", "r", "l"],
    ))
    blocks = bb.get("mean_block_days") or {}
    parts.append(
        f"Target coverage {_fmt_pct(target)}; verdict rule: {engines.get('rule', 'exact two-sided binomial test, p >= 0.10')}. "
        f"Bootstrap: {bb.get('n_paths', N_PATHS):,} paths per origin, seed {bb.get('seed', SEED)}, mean block length "
        f"{blocks.get('min', float('nan')):.0f} to {blocks.get('max', float('nan')):.0f} days across origins (median {blocks.get('median', float('nan')):.0f}). "
        + " ".join(
            f"At {h} month{'s' if str(h) != '1' else ''} the bootstrap band is {_fmt_x(p.get('band_width_ratio_bootstrap_to_gbm'))} the GBM band in log width."
            for h, p in per.items() if isinstance(p, Mapping) and p.get("band_width_ratio_bootstrap_to_gbm") is not None
        )
    )
    power = comparison.get("power_1m")
    if isinstance(power, Mapping) and power.get("n"):
        parts.append(
            f"Power at one month (n = {power['n']}): the test accepts {power.get('accept_min')} to {power.get('accept_max')} forecasts inside the band. "
            f"A model whose true coverage is 60% would be rejected {_fmt_pct(power.get('reject_prob_if_true_60'))} of the time and one at 70% only "
            f"{_fmt_pct(power.get('reject_prob_if_true_70'))} of the time, so a pass does not separate a calibrated engine from a mildly miscalibrated one."
        )
    ve = data.get("valuation_effect")
    if isinstance(ve, Mapping):
        vol = ve.get("volume_12m")
        if isinstance(vol, Mapping):
            parts.append(
                f"Valuation effect, volume. The valuation uses the GBM; this is unchanged. From the latest origin ({vol.get('origin_date')}, "
                f"trailing 30-day volume {_fmt_usd(vol.get('current_30d_usd'))}), 30-day volume 12 months ahead as a multiple of current, P10 / P50 / P90: "
                f"GBM {_triple(vol.get('gbm'))}; bootstrap with the same expected path {_triple(vol.get('block_bootstrap_registry_drift'))}; "
                f"bootstrap with its own resampled drift {_triple(vol.get('block_bootstrap_resampled_drift'))}."
            )
        fdv = ve.get("fdv")
        if isinstance(fdv, Mapping) and fdv.get("computed"):
            parts.append(
                f"Valuation effect, FDV. Feeding bootstrap volume paths (same expected path, same price, take-rate and issuance paths, "
                f"{fdv.get('n_paths', 0):,} paths) through the Monte Carlo gives FDV P10 / P50 / P90 of {_triple(fdv.get('block_bootstrap'), _fmt_usd)} "
                f"against the base {_triple(fdv.get('gbm'), _fmt_usd)} ({_triple(fdv.get('ratio_to_gbm'))} of base). "
                + ("The base run reproduces `sotp.fdv_percentiles` exactly. " if fdv.get("base_reproduces_snapshot") else
                   "The rebuilt base run does not match `sotp.fdv_percentiles` to 1e-9; treat the comparison as indicative. ")
                + "The bootstrap run holds the mean volume path fixed, so its lower median is the convexity cost of a wider distribution. "
                "These are variant figures; no headline number uses them."
            )
        elif isinstance(fdv, Mapping):
            parts.append(f"Valuation effect, FDV: not computed ({fdv.get('reason', 'unavailable')}).")
        if ve.get("headline"):
            parts.append(str(ve["headline"]))
    caveats = bb.get("caveats") or []
    if caveats:
        parts.append("Caveats:\n" + "\n".join(f"- {c}" for c in caveats))
    return "\n\n".join(parts)
