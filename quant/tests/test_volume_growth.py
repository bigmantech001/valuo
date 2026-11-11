"""Measured volume growth (valuo.models.volume_growth): estimator recovers known trends, CI behaves, registry swap."""
from __future__ import annotations

import math
import random

import pytest

from valuo import assumptions as A
from valuo.models.volume_growth import apply_measured_growth, measure_volume_growth

DAY = 86400
T0 = 1_700_000_000


def _chart(n_days: int, growth: float, noise: float = 0.0, seed: int = 1, v0: float = 1e8) -> list[list[float]]:
    rng = random.Random(seed)
    b = math.log1p(growth)
    return [[T0 + d * DAY, v0 * math.exp(b * d / 365.0 + rng.gauss(0.0, noise))] for d in range(n_days)]


def test_recovers_an_exact_trend_with_a_degenerate_interval():
    est = measure_volume_growth(_chart(500, 0.50))
    assert est["status"] == "measured" and est["n_days"] == 365
    assert est["growth_yoy"] == pytest.approx(0.50, rel=1e-9)
    lo, hi = est["ci90"]
    assert lo == pytest.approx(0.50, abs=1e-6) and hi == pytest.approx(0.50, abs=1e-6)


def test_noisy_trend_ci_covers_truth_and_widens_with_noise():
    narrow = measure_volume_growth(_chart(700, 0.40, noise=0.10, seed=7))
    wide = measure_volume_growth(_chart(700, 0.40, noise=0.60, seed=7))
    for est in (narrow, wide):
        lo, hi = est["ci90"]
        assert lo < est["growth_yoy"] < hi and lo < 0.40 < hi
    assert (wide["ci90"][1] - wide["ci90"][0]) > (narrow["ci90"][1] - narrow["ci90"][0])


def test_hac_interval_is_wider_than_iid_for_autocorrelated_residuals():
    rng = random.Random(3)
    e, chart = 0.0, []
    for d in range(400):
        e = 0.9 * e + rng.gauss(0.0, 0.1)  # AR(1) residuals, like daily volume
        chart.append([T0 + d * DAY, 1e8 * math.exp(math.log(1.3) * d / 365.0 + e)])
    hac = measure_volume_growth(chart, hac_lag=30)
    iid = measure_volume_growth(chart, hac_lag=0)
    assert hac["log_slope_se_hac"] > 2.0 * iid["log_slope_se_hac"]


def test_insufficient_data_and_zero_days_are_handled():
    short = measure_volume_growth(_chart(100, 0.5))
    assert short["status"] == "insufficient_data" and short["growth_yoy"] is None and "needed" in short["note"]
    assert measure_volume_growth([])["status"] == "insufficient_data"
    chart = _chart(400, 0.2)
    for row in chart[::5]:
        row[1] = 0.0  # zero-volume days are dropped from the log fit, not logged as -inf
    est = measure_volume_growth(chart)
    assert est["status"] == "measured" and est["n_days"] < 365 and est["growth_yoy"] == pytest.approx(0.2, rel=1e-6)


def test_cross_checks_present_on_long_history():
    est = measure_volume_growth(_chart(700, 0.25))
    xc = est["cross_checks"]
    assert xc["yoy_trailing_30d"]["value"] == pytest.approx(0.25, rel=1e-6)
    assert xc["mean_monthly_log_return_12m"]["value"] == pytest.approx(1.25 ** (360 / 365) - 1, rel=1e-3)


def test_apply_measured_growth_relabels_the_registry_entry():
    reg = dict(A.ASSUMPTIONS)
    est = measure_volume_growth(_chart(700, 0.60, noise=0.2, seed=5))
    out, used = apply_measured_growth(reg, est)
    a = out["public_volume_growth_yoy"]
    assert used and a.source == "measured" and a.value == est["growth_yoy"]
    assert a.low <= a.value <= a.high and (a.low, a.high) == (min(est["ci90"][0], a.value), max(est["ci90"][1], a.value))
    assert a.justification.startswith("MEASURED") and "Newey-West" in a.justification
    assert reg["public_volume_growth_yoy"].source == "assumption"  # the input registry is not mutated
    assert {k for k in out if out[k] is not reg[k]} == {"public_volume_growth_yoy"}
    same, used2 = apply_measured_growth(reg, {"status": "insufficient_data"})
    assert not used2 and same["public_volume_growth_yoy"] is reg["public_volume_growth_yoy"]
