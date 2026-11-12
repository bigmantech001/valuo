"""Take-rate compression series (valuo/models/take_rate_series.py): rolling take, trend, elasticity, tail rule, fallback, claim."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from valuo import config
from valuo.models import take_rate_series as trs
from valuo.schemas import EvidenceClaim

SEED = 20261114
DAY = 86400
T0 = 1_700_000_000 // DAY * DAY
FLOOR, TRIGGER = 0.5, 3.0


def _charts(n: int, take_bps, volume, *, net_share: float = 0.3, holders_from: int | None = None):
    """Four DefiLlama-style charts from per-day callables take_bps(i) and volume(i)."""
    fees, rev, hold, vol = [], [], [], []
    for i in range(n):
        ts, v = T0 + i * DAY, float(volume(i))
        f = v * float(take_bps(i)) / 1e4
        r = f * net_share
        fees.append([ts, f])
        rev.append([ts, r])
        hold.append([ts, r if holders_from is not None and i >= holders_from else 0.0])
        vol.append([ts, v])
    return fees, rev, hold, vol


def _measure(charts, **kw):
    kw.setdefault("floor_bps", FLOOR)
    kw.setdefault("trigger_net_bps", TRIGGER)
    kw.setdefault("as_of", date(2100, 1, 1))
    return trs.measure_take_rate_series(*charts, **kw)


def _noisy_volume(n: int) -> list[float]:
    rng = np.random.default_rng(SEED)
    return list(5e7 * np.exp(np.cumsum(0.002 + 0.08 * rng.standard_normal(n))))


def test_constant_take_recovers_zero_trend() -> None:
    vols = _noisy_volume(500)
    out = _measure(_charts(500, lambda i: 12.0, lambda i: vols[i], holders_from=200))
    assert out["status"] == "measured" and out["n_days"] == 500 and out["n_rolling_points"] == 471 and out["n_gaps"] == 0
    assert out["columns"] == trs.SERIES_COLUMNS and all(len(r) == len(trs.SERIES_COLUMNS) for r in out["series"])
    assert all(r[1] == pytest.approx(12.0, abs=1e-4) and r[2] == pytest.approx(3.6, abs=1e-4) for r in out["series"])
    for key in ("trailing_365d", "trailing_180d", "full_history"):
        t = out["trend"][key]
        assert t["status"] == "measured" and abs(t["change_per_year_pct"]) < 1e-6
        assert t["ci90_pct"][1] >= 0.0 and not t["ci_excludes_zero"]
    assert out["trend"]["trailing_365d"]["n_points"] == 365 and out["trend"]["trailing_365d"]["hac_lag_days"] >= 30
    claim = trs.scorecard_claim(out)
    assert claim is not None and claim["status"] == "DERIVED"
    assert "includes zero" in out["headline"]


def test_null_size_block_check_is_near_nominal_and_hac_on_overlapping_points_is_not() -> None:
    """Trendless take with AR(1) noise like the live residuals (rho ~0.5, sd ~0.25): how often does each 90% interval
    exclude zero? Nominal is 10%. The Newey-West interval on overlapping rolling points over-rejects; the
    non-overlapping check does not. This is why both are published and the caveats say which one to trust."""
    reps, n, rho, sd = 150, 394, 0.5, 0.25
    hac = blk = 0
    for k in range(reps):
        e = np.random.default_rng(SEED + k).standard_normal(n)
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = rho * x[i - 1] + sd * math.sqrt(1 - rho * rho) * e[i]
        cs = np.cumsum(np.insert(12.0 * np.exp(x), 0, 0.0))
        pts = [(T0 + i * DAY, float(v)) for i, v in enumerate((cs[30:] - cs[:-30]) / 30.0)]
        t = trs._log_trend(pts, trs.TREND_HAC_LAG_DAYS)
        assert abs(t["log_slope_per_year"]) < 0.5
        hac += bool(t["ci_excludes_zero"])
        blk += bool(trs._block_trend(pts)["ci_excludes_zero"])
    assert blk / reps < 0.20, blk / reps
    assert hac / reps > 0.20, hac / reps  # under-coverage of the HAC interval, documented not hidden


def test_known_decay_recovers_slope() -> None:
    k = 0.5  # ln-units per year; with constant volume the rolling mean of an exponential decays at the same rate
    out = _measure(_charts(500, lambda i: 20.0 * math.exp(-k * i / 365.0), lambda i: 8e7))
    for key in ("trailing_365d", "trailing_180d", "full_history"):
        t = out["trend"][key]
        assert t["log_slope_per_year"] == pytest.approx(-k, abs=1e-9)
        assert t["change_per_year_pct"] == pytest.approx(math.expm1(-k) * 100.0, abs=1e-6)
        assert t["ci_excludes_zero"] and t["ci90_pct"][1] < 0 and t["direction"] == "falling"
    blk = out["trend"]["block_check_365d"]
    assert blk["status"] == "measured" and blk["n_blocks"] == 13 and blk["change_per_year_pct"] == pytest.approx(math.expm1(-k) * 100.0, abs=1e-6)
    assert [x["hac_lag_days"] for x in out["trend"]["lag_sensitivity_365d"]] == list(trs.LAG_SENSITIVITY_DAYS)
    claim = trs.scorecard_claim(out)
    assert claim is not None and claim["status"] == "NOT_SUPPORTED" and "excludes zero" in claim["value"]
    assert out["trend"]["block_check_agrees"] is True
    assert "compressed" in out["headline"] and "against the bull case" in out["investor_read"]


def test_rolling_take_and_window_table_are_pooled_sums() -> None:
    vols = _noisy_volume(400)
    fees, rev, hold, vol = _charts(400, lambda i: 10.0 + 5.0 * math.sin(i / 20.0), lambda i: vols[i], holders_from=100)
    out = _measure((fees, rev, hold, vol))
    f30, v30 = sum(x[1] for x in fees[-30:]), sum(x[1] for x in vol[-30:])
    assert out["latest"]["gross_take_bps"] == pytest.approx(f30 / v30 * 1e4, rel=1e-12)
    assert out["latest"]["avg_daily_volume_usd"] == pytest.approx(v30 / 30, rel=1e-12)
    assert out["series"][-1][0] == fees[-1][0] and out["series"][0][0] == fees[29][0]
    w = {x["label"]: x for x in out["windows"]}
    assert [x["label"] for x in out["windows"]] == [lab for lab, _, _ in trs.WINDOWS]
    assert w["last 30d"]["gross_take_bps"] == pytest.approx(out["latest"]["gross_take_bps"], rel=1e-12)
    f, v = sum(x[1] for x in fees[-360:-330]), sum(x[1] for x in vol[-360:-330])
    assert w["330-360d ago"]["n_days"] == 30 and w["330-360d ago"]["gross_take_bps"] == pytest.approx(f / v * 1e4, rel=1e-12)
    assert w["330-360d ago"]["avg_daily_volume_usd"] == pytest.approx(v / 30, rel=1e-12)
    short = _measure(_charts(100, lambda i: 10.0, lambda i: 1e7))
    assert {x["label"]: x["n_days"] for x in short["windows"]}["150-180d ago"] == 0
    assert short["trend"]["trailing_365d"]["status"] == "insufficient_data"
    assert trs.scorecard_claim(short)["status"] == "NOT_SUPPORTED"  # type: ignore[index]


def test_unsettled_trailing_day_and_partial_day_excluded() -> None:
    fees, rev, hold, vol = _charts(200, lambda i: 10.0, lambda i: 1e7)
    rev[-1][1] = fees[-1][1] * 2.0   # revenue above fees on the newest day: fee figure not final
    rev[50][1] = fees[50][1] * 2.0   # an interior day like that stays (only the tail is trimmed)
    out = _measure((fees, rev, hold, vol))
    last_iso = datetime.fromtimestamp(fees[-1][0], tz=timezone.utc).date().isoformat()
    prev_iso = datetime.fromtimestamp(fees[-2][0], tz=timezone.utc).date().isoformat()
    assert out["excluded_unsettled_days"] == [last_iso] and out["last_day"] == prev_iso and out["n_days"] == 199
    assert out["series"][-1][0] == fees[-2][0]
    # a point dated on the run date is a partial day and is dropped without being listed as unsettled
    clean = _charts(200, lambda i: 10.0, lambda i: 1e7)
    as_of = datetime.fromtimestamp(clean[0][-1][0], tz=timezone.utc).date()
    out2 = _measure(clean, as_of=as_of)
    assert out2["excluded_unsettled_days"] == [] and out2["last_day"] == prev_iso and out2["as_of_utc"] == as_of.isoformat()


def test_elasticity_recovered_and_zero_days_counted() -> None:
    vols = _noisy_volume(400)
    # fees = c * V^0.8  ->  take = c * V^-0.2: elasticity of take to volume is -0.2
    fees, rev, hold, vol = _charts(400, lambda i: 1e4 * 3.0 * vols[i] ** -0.2, lambda i: vols[i])
    for i in (5, 6, 390):
        fees[i][1] = 0.0
        rev[i][1] = 0.0
    out = _measure((fees, rev, hold, vol))
    e = out["elasticity"]["full_history"]
    assert e["status"] == "measured" and e["elasticity"] == pytest.approx(-0.2, abs=1e-9)
    assert e["n_dropped_zero_fee_or_volume"] == 3 and e["n_days"] == 397 and e["ci_excludes_zero"] and e["r2"] == pytest.approx(1.0, abs=1e-9)
    assert out["elasticity"]["trailing_365d"]["n_dropped_zero_fee_or_volume"] == 1
    flat = _measure(_charts(200, lambda i: 10.0, lambda i: 1e7))  # no variation in volume: not measurable, no crash
    assert flat["elasticity"]["full_history"]["status"] == "insufficient_data"


def test_regime_break_read_from_data_and_floor_counts() -> None:
    # gross 20 bps then 10 bps; holders revenue starts on day 250; net share 0.2 -> net 4 bps then 2 bps
    charts = _charts(500, lambda i: 20.0 if i < 250 else 10.0, lambda i: 5e7, net_share=0.2, holders_from=250)
    out = _measure(charts, floor_bps=12.5, trigger_net_bps=3.1)
    rb = out["regime_break"]
    assert rb["ts_unix_s"] == T0 + 250 * DAY and rb["date"] == datetime.fromtimestamp(T0 + 250 * DAY, tz=timezone.utc).date().isoformat()
    assert rb["before"]["n_days"] == 250 and rb["after"]["n_days"] == 250
    assert rb["before"]["gross_take_bps"] == pytest.approx(20.0) and rb["after"]["gross_take_bps"] == pytest.approx(10.0)
    assert rb["before"]["holder_take_bps"] == pytest.approx(0.0) and rb["after"]["holder_take_bps"] == pytest.approx(2.0)
    assert rb["before_trailing_365d"]["n_days"] == 115
    fl = out["floor_read"]
    roll_y = out["series"][-365:]
    assert fl["n_points"] == 365
    assert fl["gross_below_floor"] == sum(1 for r in roll_y if r[1] < 12.5) > 200
    assert fl["net_below_trigger"] == sum(1 for r in roll_y if r[2] < 3.1) > 200
    assert fl["min_gross"]["bps"] == pytest.approx(10.0) and fl["min_net"]["bps"] == pytest.approx(2.0)
    assert fl["since_regime_break"]["n_points"] == 221 and fl["since_regime_break"]["net_below_trigger"] == 221
    claim = trs.scorecard_claim(out)
    assert claim is not None and claim["status"] == "NOT_SUPPORTED"  # latest 10 bps is under the 12.5 bps floor used here
    no_h = _measure((charts[0], charts[1], None, charts[3]))
    assert no_h["holders_available"] is False and no_h["regime_break"]["date"] is None and no_h["latest"]["holder_take_bps"] is None
    assert all(r[3] is None for r in no_h["series"]) and no_h["floor_read"]["since_regime_break"] is None


def test_malformed_rows_and_gaps_are_skipped_and_reported() -> None:
    fees, rev, hold, vol = _charts(200, lambda i: 10.0, lambda i: 1e7)
    fees[10] = ["bad", None]
    vol.append("junk")
    del rev[100]  # one day missing from the join -> one gap; windows spanning it are skipped
    out = _measure((fees, rev, hold, vol))
    assert out["n_days"] == 198 and out["n_gaps"] == 2 and out["n_rolling_skipped"] > 0
    assert any("malformed fees" in w for w in out["data_warnings"]) and any("malformed volume" in w for w in out["data_warnings"])
    assert all(r[1] == pytest.approx(10.0) for r in out["series"])
    empty = _measure(([], [], [], []))
    assert empty["status"] == "insufficient_data" and empty["series"] == [] and trs.scorecard_claim(empty)["status"] == "NOT_SUPPORTED"  # type: ignore[index]
    assert "not measured" in trs.memo_markdown(empty, {})


def test_claim_logic() -> None:
    assert trs.scorecard_claim(None) is None

    def data(ci_hi: float, latest: float, floor: float = 0.5) -> dict:
        return {
            "status": "measured", "source": "x",
            "latest": {"gross_take_bps": latest, "date": "2026-11-10"}, "year_ago": {"gross_take_bps": 16.0, "date": "2025-11-11"},
            "trend": {"trailing_365d": {"status": "measured", "change_per_year_pct": ci_hi - 10.0, "ci90_pct": [ci_hi - 20.0, ci_hi],
                                        "ci_excludes_zero": ci_hi < 0, "hac_lag_days": 60, "n_points": 365}},
            "floor_read": {"public_take_floor_bps": floor, "gross_below_floor": 0, "n_points": 365},
        }

    assert trs.scorecard_claim(data(0.0, 15.0))["status"] == "DERIVED"  # type: ignore[index]
    assert trs.scorecard_claim(data(5.0, 15.0))["status"] == "DERIVED"  # type: ignore[index]
    assert trs.scorecard_claim(data(-0.1, 15.0))["status"] == "NOT_SUPPORTED"  # type: ignore[index]
    assert trs.scorecard_claim(data(5.0, 0.5))["status"] == "NOT_SUPPORTED"  # type: ignore[index]  # at the floor, not above it
    for c in (trs.scorecard_claim(data(5.0, 15.0)), trs.scorecard_claim(data(-5.0, 15.0))):
        assert c is not None and c["claim"] == trs.CLAIM
        EvidenceClaim(**c)  # the fields and the status vocabulary the scorecard accepts


def test_raw_dir_payloads_are_hashed_and_used(tmp_path: Path) -> None:
    charts = _charts(420, lambda i: 14.0, lambda i: 6e7, holders_from=300)
    shas = {}
    for key, chart in zip(("fees", "revenue", "holders", "volume"), charts):
        data = json.dumps({"totalDataChart": chart}).encode()
        (tmp_path / trs.RAW_FILES[key][0]).write_bytes(data)
        shas[key] = hashlib.sha256(data).hexdigest()
    gen = datetime.fromtimestamp(T0 + 421 * DAY, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    out = trs.run_take_rate_series({"generated_at_utc": gen, "assumptions": [{"key": "public_take_floor_bps", "value": 1.25}]}, tmp_path)
    assert out["source_mode"] == "raw" and {s["key"]: s["sha256"] for s in out["sources"]} == shas
    assert [s["record"] for s in out["sources"]] == [v[1] for v in trs.RAW_FILES.values()]
    assert out["floor_read"]["public_take_floor_bps"] == 1.25           # the value the run recorded
    assert out["floor_read"]["bear_fee_race_trigger_net_take_bps"] == 3.0  # registry default when the snapshot lacks it
    assert out["regime_break"]["ts_unix_s"] == T0 + 300 * DAY and out["n_days"] == 420
    json.dumps(out, allow_nan=False)
    # volume payload missing -> falls back to the snapshot (here empty) without raising
    (tmp_path / trs.RAW_FILES["volume"][0]).unlink()
    fb = trs.run_take_rate_series({"generated_at_utc": gen}, tmp_path)
    assert fb["status"] == "insufficient_data" and fb["source_mode"] == "snapshot_fallback" and fb["data_warnings"]


def test_fallback_on_committed_snapshot_and_memo() -> None:
    snap_path = config.ARTIFACTS_DIR / "latest_snapshot.json"
    if not snap_path.is_file():
        pytest.skip("artifacts/latest_snapshot.json not present")
    snap = json.loads(snap_path.read_text())
    out = trs.run_take_rate_series(snap, None)
    assert out["status"] == "measured" and out["source_mode"] == "snapshot_fallback" and out["holders_available"] is False
    assert out["n_days"] >= 300 and out["n_rolling_points"] == out["n_days"] - trs.ROLLING_DAYS + 1 - out["n_rolling_skipped"]
    assert all(r[3] is None and r[1] >= 0 and r[4] > 0 for r in out["series"])
    assert 0.0 < out["latest"]["gross_take_bps"] < 200.0 and out["latest"]["net_take_bps"] <= out["latest"]["gross_take_bps"]
    assert out["trend"]["trailing_365d"]["status"] == "measured"
    json.dumps(out, allow_nan=False)
    assert out == trs.run_take_rate_series(snap, None)  # deterministic
    claim = trs.scorecard_claim(out)
    assert claim is not None and claim["status"] in ("DERIVED", "NOT_SUPPORTED")
    EvidenceClaim(**claim)
    md = trs.memo_markdown(out, snap)
    assert md.startswith(out["headline"]) and "| Window |" in md and "Elasticity to volume" in md and "Limits:" in md
    assert "—" not in md
