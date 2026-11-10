"""Out-of-sample volume backtest (valuo/models/backtest.py): calibration math, no look-ahead, closed form vs the MC."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from valuo import config
from valuo.models import backtest as bt
from valuo.models.sotp_valuation import simulate_paths

SEED = 20261114
DAY = 86400
T0 = 1_700_000_000 // DAY * DAY


def _gbm_monthly_chart(n_months: int, *, sigma: float, growth_yoy: float, seed: int = SEED, v0_day: float = 1e7) -> list[list[float]]:
    """Daily chart whose 30-day blocks follow the model's own monthly GBM (constant daily volume within a block)."""
    rng = np.random.default_rng(seed)
    log_g = math.log1p((1.0 + growth_yoy) ** (1.0 / 12.0) - 1.0)
    logs = math.log(v0_day) + np.cumsum(log_g - 0.5 * sigma * sigma + sigma * rng.standard_normal(n_months))
    chart: list[list[float]] = []
    for k, lv in enumerate(logs):
        for d in range(30):
            chart.append([T0 + (k * 30 + d) * DAY, float(math.exp(lv))])
    return chart


def test_known_gbm_is_calibrated_near_80pct() -> None:
    chart = _gbm_monthly_chart(400, sigma=0.35, growth_yoy=0.30)
    res = bt.run_backtest(chart, growth_yoy=0.30)
    for h in ("1", "3", "6"):
        s = res["by_horizon"][h]
        assert s["n"] > 300
        # sigma is re-estimated from 11 trailing monthly returns at every origin, so slight under-coverage is expected
        assert 0.70 <= s["coverage_p10_p90"] <= 0.88, (h, s["coverage_p10_p90"])
        assert abs(s["median_log_error"]) < 0.15 * math.sqrt(int(h))
        assert sum(s["pit_hist"]) == s["n"]
    assert res["n_gaps"] == 0


def test_misspecified_drift_shows_bias() -> None:
    # True growth 300% YoY, model told 30%: realized volume sits above the forecast median.
    chart = _gbm_monthly_chart(200, sigma=0.30, growth_yoy=3.0)
    res = bt.run_backtest(chart, growth_yoy=0.30)
    s = res["by_horizon"]["6"]
    assert s["median_log_error"] > 0.3
    assert s["above_p90"] > s["below_p10"]
    assert "under-predicts" in res["headline"]


def test_no_look_ahead() -> None:
    chart = _gbm_monthly_chart(60, sigma=0.35, growth_yoy=0.30)
    base = bt.run_backtest(chart, growth_yoy=0.30)
    cut_ts = chart[len(chart) // 2][0]
    future_mutated = [[t, v * (1000.0 if t > cut_ts else 1.0)] for t, v in chart]
    mutated = bt.run_backtest(future_mutated, growth_yoy=0.30)
    a = {(r["origin_date"], r["h"]): r for r in base["rows"]}
    b = {(r["origin_date"], r["h"]): r for r in mutated["rows"]}
    checked = 0
    for key, r in a.items():
        origin_ts = int(np.datetime64(r["origin_date"]).astype("datetime64[s]").astype(int))
        if origin_ts <= cut_ts:
            for f in ("p10", "p50", "p90", "sigma_volume_monthly", "v0_30d_usd"):
                assert b[key][f] == r[f], (key, f)
            checked += 1
    assert checked > 10
    # and the forecast itself only sees the slice it is given
    hist = [(int(t), float(v)) for t, v in chart[:400]]
    f1 = bt.forecast_at_origin(hist, growth_yoy=0.30)
    f2 = bt.forecast_at_origin(hist, growth_yoy=0.30)
    assert f1 == f2 and f1 is not None and f1["origin_ts"] == hist[-1][0]


def test_partial_day_dropped_and_short_series() -> None:
    chart = _gbm_monthly_chart(5, sigma=0.3, growth_yoy=0.3)
    last_ts = chart[-1][0]
    res = bt.run_backtest(chart, growth_yoy=0.3, as_of_ts=last_ts + DAY // 2)
    assert res["n_days"] == len(chart) - 1
    empty = bt.run_backtest(chart[:60], growth_yoy=0.3)
    assert empty["rows"] == [] and empty["by_horizon"]["1"]["n"] == 0


def test_binomial_and_wilson_helpers() -> None:
    assert bt._binom_two_sided_p(8, 10, 0.8) == pytest.approx(1.0)
    assert bt._binom_two_sided_p(2, 20, 0.8) < 1e-6
    lo, hi = bt._wilson(16, 20)
    assert lo < 0.8 < hi


def test_closed_form_matches_simulate_paths() -> None:
    """The lognormal bands equal the percentiles of the live simulate_paths public-volume leg (same GBM)."""
    snap_path = config.ARTIFACTS_DIR / "latest_snapshot.json"
    if not snap_path.is_file():
        pytest.skip("no canonical snapshot to build simulate_paths inputs from")
    from valuo.models.market_implied import inputs_from_snapshot

    snap = json.loads(Path(snap_path).read_text())
    cal = snap["sotp"]["calibration"]
    inputs = inputs_from_snapshot(snap)
    inputs.update({
        "sigma_volume_monthly": cal["sigma_volume_monthly"], "sigma_price_monthly": cal["sigma_price_monthly"],
        "confidential_sigma_multiplier": cal.get("confidential_sigma_multiplier") or 1.0,
    })
    sigma = float(inputs["sigma_volume_monthly"])
    v0_day = float(inputs["v_pub_usd_day"])
    log_g = math.log1p(float(inputs["growth_monthly_pub"]))
    sim = simulate_paths(inputs, seed=SEED, n_paths=40_000)
    for h in (1, 3, 6):
        cf = bt.lognormal_bands(v0_day, sigma, log_g, h)
        mc = np.percentile(sim["v_pub"][:, h - 1] * bt.WINDOW_DAYS, [10, 50, 90])
        np.testing.assert_allclose(mc, [cf["p10"], cf["p50"], cf["p90"]], rtol=0.03)
    # forecast_at_origin converts the registry growth exactly as build_inputs does
    growth_yoy = (1.0 + float(inputs["growth_monthly_pub"])) ** 12 - 1.0
    hist = [(T0 + i * DAY, 1e7 * (1.0 + 0.01 * (i % 7))) for i in range(400)]
    fc = bt.forecast_at_origin(hist, growth_yoy=growth_yoy)
    assert fc is not None and fc["log_growth_monthly"] == pytest.approx(log_g, rel=1e-12)
