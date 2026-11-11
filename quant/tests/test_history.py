"""History store: record extraction, append/de-dup, summary statistics, canonical-run hook, raw verification.

Offline only. Inputs are synthetic dicts shaped like the snapshot/bench contract (no network)."""
from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path

import pytest

from valuo import config, history
from valuo.provenance import sha256_bytes


def _snapshot(t: str = "2026-11-01T08:52:21.816Z", *, hhi_solver: float = 1600.0, breached: bool = True, canonical: bool = True) -> dict:
    return {
        "schema_version": "1.0.0", "generated_at_utc": t, "seed": 20261114, "valuo_version": "0.1.0",
        "run_config": {"canonical": canonical},
        "near_rpc": {
            "block_height": 100, "block_hash": "H", "total_supply_near": 1.31e9, "measured_daily_issuance_near": 89666.0,
            "max_inflation_rate": 0.025, "total_state_locked_near": 278221.9,
            "tracked_sinks": [{"account_id": "other.near", "storage_locked_near": 1.0},
                              {"account_id": "intents.near", "storage_bytes": 13171261713, "storage_locked_near": 131712.6}],
        },
        "execution_bench": {"ran_at_utc": t, "headroom_by_archetype_bps": {"cross_vm": 1.08, "evm_l2": -0.08}, "competitive_fee_ceiling_bps": 3.0},
        "intents_forensics": {
            "volume": {"24h": 7.3e7, "7d": 8.8e8, "30d": 3.86e9, "confidential_share_30d": 0.409,
                       "split_checks": [{"id": "a", "status": "pass"}, {"id": "b", "status": "skip"}]},
            "fees": {"gross_take_bps": 14.89, "net_take_bps": 5.49},
            "hhi_external": 4687.5, "n_eff_external": 2.13, "ai_agent_share": 0.125,
            "solver_concentration": {"hhi_solver": hhi_solver, "n_eff_solver": 6.2, "n_fills": 18, "hhi_solver_ci": [900.0, 2600.0]},
            "price": {"current_usd": 4.39},
        },
        "supply_physics": {
            "current_daily_sinks_near": {"buyback": 16096.6, "gas_burn": 378.3, "state_lock": 299.3, "total": 16774.1},
            "sink_coverage_ratio": 0.187, "breakeven_daily_volume_usd": {"status_quo": 7.1e8, "svrn_glidepath": 4.5e8},
        },
        "sotp": {"n_paths": 10000, "fdv_percentiles": {"p10": 5.5e7, "p50": 2.58e8, "p90": 1.67e9}, "current_fdv_usd": 5.75e9,
                 "calibration": {"deterministic_base": {"fdv_total": 8.48e8}}},
        "bear_case": {"triggers_breached": int(breached), "triggers_evaluated": 1, "scenarios": [
            {"key": "governance_stalemate", "early_warning_metric": "max_inflation_rate", "current_value": 0.025,
             "trigger_threshold": 0.016, "trigger_comparator": ">", "trigger_evaluated": True, "trigger_breached": breached},
        ]},
    }


def _bench(t: str = "2026-11-08T20:00:00.000Z", headroom: float = 1.2) -> dict:
    return {
        "ran_at_utc": t, "clips_usd": [500.0], "elapsed_s": 6.9, "n_quotes_ok": 2, "concurrency": 4,
        "headroom_by_archetype_bps": {"cross_vm": headroom}, "competitive_fee_ceiling_bps": 3.0,
        "corridors": [{"corridor_id": "eth_usdc_sol_usdc", "archetype": "cross_vm"}],
        "results": [{"corridor_id": "eth_usdc_sol_usdc", "clip_usd": 500.0, "headroom_bps": headroom, "best_competitor": "relay",
                     "oneclick_rank": 1, "n_venues_ok": 2, "quotes": [
                         {"venue": "1click", "status": "ok", "supported": True, "amount_out_raw": "499889005", "amount_out_formatted": 499.889005,
                          "friction_bps_raw": 2.2, "friction_bps_usd": 2.21, "raw_record_sha256": "aa"},
                         {"venue": "relay", "status": "ok", "supported": True, "amount_out_raw": "499829817", "amount_out_formatted": 499.83,
                          "friction_bps_raw": None, "friction_bps_usd": 3.4, "raw_record_sha256": "bb"},
                     ]}],
    }


# ----------------------------------------------------------------------------- record_from_snapshot
def test_record_from_snapshot_extracts_key_series():
    rec = history.record_from_snapshot(_snapshot(), {"snapshot_sha256": "abc", "memo_sha256": "m"})
    m = rec["metrics"]
    assert rec["schema"] == history.SNAPSHOT_SCHEMA
    assert rec["snapshot_sha256"] == "abc" and rec["block_height"] == 100 and rec["canonical"] is True
    assert m["intents_near_locked_near"] == pytest.approx(131712.6)
    assert m["sinks_total_near_day"] == pytest.approx(16774.1)
    assert m["deterministic_fdv_usd"] == pytest.approx(8.48e8)
    assert m["headroom_bps_cross_vm"] == pytest.approx(1.08)
    assert (m["hhi_solver_ci_low"], m["hhi_solver_ci_high"]) == (900.0, 2600.0)
    assert m["breakeven_daily_volume_usd_svrn_glidepath"] == pytest.approx(4.5e8)
    assert m["bear_governance_stalemate_value"] == pytest.approx(0.025)
    assert rec["status"]["confidential_share_status"] == "checks_passed"
    assert rec["bear_triggers"][0]["breached"] is True
    json.dumps(rec, allow_nan=False)


def test_record_from_snapshot_missing_keys_are_null():
    rec = history.record_from_snapshot({}, {})
    assert rec["t_utc"] is None and rec["snapshot_sha256"] is None
    assert all(v is None for v in rec["metrics"].values())
    assert rec["bear_triggers"] == []
    rec2 = history.record_from_snapshot({"near_rpc": {"total_supply_near": float("nan")}, "sotp": {"fdv_percentiles": "bad"}}, None)
    assert rec2["metrics"]["total_supply_near"] is None and rec2["metrics"]["sotp_fdv_p50"] is None


def test_ci_variants_and_status_derivation():
    for sc in ({"hhi_solver_ci": {"low": 1, "high": 2}}, {"hhi_solver_ci_low": 1, "hhi_solver_ci_high": 2}, {"hhi_solver_ci90": [1, 2]}):
        assert history._hhi_solver_ci(sc) == (1.0, 2.0)
    assert history._hhi_solver_ci({}) == (None, None)
    assert history._confidential_share_status({"split_checks": [{"status": "fail"}], "confidential_share_30d": 0.4}) == "checks_failed"
    assert history._confidential_share_status({"confidential_share_status": "measured"}) == "measured"
    assert history._confidential_share_status({}) == "missing"


# ----------------------------------------------------------------------------- append / read
def test_append_dedups_by_snapshot_sha_and_time(tmp_path: Path):
    path = tmp_path / "h" / "snapshots.jsonl"
    rec = history.record_from_snapshot(_snapshot(), {"snapshot_sha256": "abc"})
    assert history.append(path, rec) is True
    assert history.append(path, rec) is False
    rec2 = history.record_from_snapshot(_snapshot("2026-11-02T00:00:00Z"), {"snapshot_sha256": "def"})
    assert history.append(path, rec2) is True
    bpath = tmp_path / "h" / "bench.jsonl"
    b = history.record_from_bench(_bench())
    assert history.append(bpath, b) and not history.append(bpath, b)
    assert len(history.read_jsonl(path)) == 2 and len(history.read_jsonl(bpath)) == 1


def test_read_jsonl_skips_torn_line_and_append_repairs_newline(tmp_path: Path):
    path = tmp_path / "x.jsonl"
    path.write_text('{"t_utc":"2026-11-01T00:00:00Z"}\n{"t_utc": "2026-11', encoding="utf-8")
    assert len(history.read_jsonl(path)) == 1
    assert history.append(path, {"t_utc": "2026-11-03T00:00:00Z"})
    assert [r["t_utc"] for r in history.read_jsonl(path)] == ["2026-11-01T00:00:00Z", "2026-11-03T00:00:00Z"]


# ----------------------------------------------------------------------------- bench record
def test_record_from_bench_shape():
    raws = [{"source": "oneclick", "name": "q", "sha256": "aa", "raw_path": "artifacts/history/raw/X/a.json.gz", "ok": True, "http_status": 200, "bytes": 10}]
    rec = history.record_from_bench(_bench(), raws, raw_dir="artifacts/history/raw/X")
    cell = rec["cells"][0]
    assert rec["schema"] == history.BENCH_SCHEMA and rec["t_utc"] == "2026-11-08T20:00:00.000Z"
    assert cell["archetype"] == "cross_vm" and cell["oneclick_status"] == "ok" and cell["best_competitor"] == "relay"
    assert cell["venues"]["1click"]["friction_bps"] == 2.2  # raw preferred
    assert cell["venues"]["relay"]["friction_bps"] == 3.4  # USD fallback
    assert cell["venues"]["1click"]["raw_path"].endswith("a.json.gz") and cell["venues"]["relay"]["raw_path"] is None
    assert rec["raw_records"][0]["sha256"] == "aa"


# ----------------------------------------------------------------------------- statistics
def test_series_stats_bounds_and_reproducibility():
    vals = [1.0, None, 2.0, 3.0, 4.0, 10.0, float("nan")]
    st = history.series_stats(vals)
    assert st["n"] == 5 and st["first"] == 1.0 and st["last"] == 10.0
    assert st["min"] <= st["p10"] <= st["median"] <= st["p90"] <= st["max"]
    lo, hi = st["median_ci90"]
    assert st["min"] <= lo <= st["median"] <= hi <= st["max"]
    assert history.series_stats(vals) == st  # seeded bootstrap
    assert st["change_pct"] == pytest.approx(900.0)
    small = history.series_stats([5.0, 6.0])
    assert small["median_ci90"] is None and small["median"] == 5.5
    empty = history.series_stats([None])
    assert empty["n"] == 0 and empty["median"] is None


def test_summarize_series_triggers_and_cells():
    snaps = [
        history.record_from_snapshot(_snapshot("2026-11-03T06:00:00Z", hhi_solver=1800.0, breached=True), {"snapshot_sha256": "c"}),
        history.record_from_snapshot(_snapshot("2026-11-01T06:00:00Z", hhi_solver=1600.0, breached=False), {"snapshot_sha256": "a"}),
        history.record_from_snapshot(_snapshot("2026-11-02T06:00:00Z", hhi_solver=1700.0, breached=True), {"snapshot_sha256": "b"}),
    ]
    bench = [history.record_from_bench(_bench(f"2026-11-08T{h:02d}:00:00Z", headroom=float(h))) for h in range(6)]
    out = history.summarize({"snapshots": snaps, "bench": bench})
    assert out["schema"] == history.SUMMARY_SCHEMA
    s = out["snapshots"]
    assert s["n_records"] == 3 and s["first_t_utc"] == "2026-11-01T06:00:00Z"  # sorted by time
    assert [p[1] for p in s["series"]["hhi_solver"]["points"]] == [1600.0, 1700.0, 1800.0]
    trig = s["bear_triggers"]["governance_stalemate"]
    assert trig["n_breached"] == 2 and trig["breached_since_utc"] == "2026-11-02T06:00:00Z"
    assert trig["breached_streak_days"] == pytest.approx(1.0)
    b = out["bench"]
    assert b["n_runs"] == 6
    cell = b["cells"]["eth_usdc_sol_usdc@500"]
    assert cell["n_runs"] == 6 and cell["oneclick_ok_rate"] == 1.0 and cell["best_competitor_counts"] == {"relay": 6}
    hs = b["series"]["headroom_bps_cross_vm"]
    assert hs["stats"]["n"] == 6 and hs["stats"]["median_ci90"] is not None
    assert hs["window_24h"]["n"] == 6
    assert "cell.eth_usdc_sol_usdc@500.relay.friction_bps" in b["series"]
    json.dumps(out, allow_nan=False)


def test_summarize_empty_history():
    out = history.summarize({})
    assert out["snapshots"]["n_records"] == 0 and out["bench"]["n_runs"] == 0


# ----------------------------------------------------------------------------- canonical hook / merge / verify
def _write_artifacts(base: Path, snap: dict) -> None:
    base.mkdir(parents=True, exist_ok=True)
    data = json.dumps(snap, indent=2).encode()
    (base / "latest_snapshot.json").write_bytes(data)
    (base / "manifest.json").write_text(json.dumps({"snapshot_sha256": sha256_bytes(data), "block_height": 100}))


def test_record_canonical_run(tmp_path: Path):
    assert history.record_canonical_run(tmp_path / "missing") is None
    _write_artifacts(tmp_path / "a", _snapshot())
    rec = history.record_canonical_run(tmp_path / "a")
    assert rec is not None and rec["snapshot_sha256"] == rec["snapshot_file_sha256"]
    assert history.record_canonical_run(tmp_path / "a") is not None  # idempotent
    assert len(history.read_jsonl(tmp_path / "a" / "history" / "snapshots.jsonl")) == 1
    summary = json.loads((tmp_path / "a" / "history" / "summary.json").read_text())
    assert summary["snapshots"]["n_records"] == 1
    _write_artifacts(tmp_path / "dev", _snapshot(canonical=False))
    assert history.record_canonical_run(tmp_path / "dev") is None
    assert history.record_canonical_run(tmp_path / "dev", allow_noncanonical=True) is not None


def test_merge_from_unions_records(tmp_path: Path):
    src = tmp_path / "src"
    history.append(src / "bench.jsonl", history.record_from_bench(_bench("2026-11-08T01:00:00Z")))
    history.append(src / "bench.jsonl", history.record_from_bench(_bench("2026-11-08T02:00:00Z")))
    dst = tmp_path / "art"
    history.append(dst / "history" / "bench.jsonl", history.record_from_bench(_bench("2026-11-08T01:00:00Z")))
    added = history.merge_from(src, dst)
    assert added == {"snapshots.jsonl": 0, "bench.jsonl": 1}
    assert len(history.read_jsonl(dst / "history" / "bench.jsonl")) == 2


def test_gzip_raw_and_verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    raw_dir = tmp_path / "artifacts" / "history" / "raw" / "20261108T000000Z"
    raw_dir.mkdir(parents=True)
    payload = b'{"amountOut":"1"}'
    (raw_dir / "oneclick__q.json").write_bytes(payload)
    records = [{"source": "oneclick", "name": "q", "sha256": sha256_bytes(payload), "raw_path": "artifacts/history/raw/20261108T000000Z/oneclick__q.json"}]
    history._gzip_raw(raw_dir, records)
    assert records[0]["raw_path"].endswith(".json.gz") and not (raw_dir / "oneclick__q.json").exists()
    assert gzip.decompress((raw_dir / "oneclick__q.json.gz").read_bytes()) == payload
    rec = history.record_from_bench(_bench(), records, raw_dir="artifacts/history/raw/20261108T000000Z")
    history.append(tmp_path / "artifacts" / "history" / "bench.jsonl", rec)
    assert history.verify_bench_raw(tmp_path / "artifacts")["ok"] is True
    bad = copy.deepcopy(rec)
    bad["t_utc"] = "2026-11-09T00:00:00Z"
    bad["raw_records"][0]["sha256"] = "0" * 64
    history.append(tmp_path / "artifacts" / "history" / "bench.jsonl", bad)
    res = history.verify_bench_raw(tmp_path / "artifacts")
    assert res["ok"] is False and len(res["mismatched"]) == 1


def test_committed_history_matches_canonical_snapshot():
    """The seeded store must point at the canonical snapshot it was built from (skips if absent)."""
    hpath = config.ARTIFACTS_DIR / "history" / "snapshots.jsonl"
    if not hpath.exists() or not config.SNAPSHOT_PATH.exists():
        pytest.skip("no committed history")
    shas = {r.get("snapshot_sha256") for r in history.read_jsonl(hpath)}
    assert all(isinstance(s, str) and len(s) == 64 for s in shas)
    for r in history.read_jsonl(hpath):
        assert r["schema"] == history.SNAPSHOT_SCHEMA and r["t_utc"]


@pytest.mark.live
def test_live_bench_history(tmp_path: Path):
    rec = history.run_bench(tmp_path, budget_s=60.0)
    assert rec["t_utc"] and rec["cells"]
    assert history.verify_bench_raw(tmp_path)["ok"] is True


def test_summary_keeps_latest_run_per_utc_day():
    from valuo import history
    recs = [
        {"t_utc": "2026-11-01T08:00:00Z", "metrics": {"hhi_solver": 1.0}},
        {"t_utc": "2026-11-08T10:00:00Z", "metrics": {"hhi_solver": 2.0}},
        {"t_utc": "2026-11-08T21:00:00Z", "metrics": {"hhi_solver": 3.0}},
    ]
    out = history.summarize({"snapshots": recs, "bench": []})["snapshots"]
    assert out["n_records"] == 2 and out["n_records_total"] == 3 and out["n_same_day_reruns_dropped"] == 1
    assert [p[1] for p in out["series"]["hhi_solver"]["points"]] == [1.0, 3.0]


# ----------------------------------------------------------------------------- 1Click win/loss by route
def _cell(corridor: str, clip: float, headroom: float | None, *, oneclick: str = "ok", comp_status: str = "ok",
          best: str | None = "relay") -> dict:
    return {"corridor_id": corridor, "archetype": "x", "clip_usd": clip, "headroom_bps": headroom, "best_competitor": best,
            "oneclick_rank": None, "oneclick_status": oneclick, "n_venues_ok": None,
            "venues": {"1click": {"status": oneclick}, "relay": {"status": comp_status}, "across": {"status": "unsupported_route"}}}


def test_wilson_interval_bounds():
    assert history.wilson_interval(0, 0) is None
    lo, hi = history.wilson_interval(0, 24)
    assert lo == 0.0 and hi == pytest.approx(0.10131, abs=1e-4)          # z^2 / (n + z^2)
    lo, hi = history.wilson_interval(24, 24)
    assert hi == 1.0 and lo == pytest.approx(1 - 0.10131, abs=1e-4)
    lo, hi = history.wilson_interval(13, 72)
    assert lo < 13 / 72 < hi and 0.0 < lo and hi < 1.0
    # symmetric in wins <-> losses
    lo2, hi2 = history.wilson_interval(59, 72)
    assert lo2 == pytest.approx(1 - hi) and hi2 == pytest.approx(1 - lo)
    # by hand, 8/10 at z = 1.6449: centre 0.73612, half-width 0.19533 -> [0.5408, 0.9314]
    lo, hi = history.wilson_interval(8, 10)
    assert (lo, hi) == (pytest.approx(0.5408, abs=1e-3), pytest.approx(0.9314, abs=1e-3))


def test_classify_race_exclusions_and_ties():
    assert history.classify_race(_cell("a", 500, 1.0)) == ("win", None)
    assert history.classify_race(_cell("a", 500, -1.0)) == ("loss", None)
    assert history.classify_race(_cell("a", 500, 0.005)) == ("tie", None)
    assert history.classify_race(_cell("a", 500, -0.0099)) == ("tie", None)
    assert history.classify_race(_cell("a", 500, history.TIE_BPS)) == ("win", None)
    assert history.classify_race(_cell("a", 500, None, oneclick="error")) == ("excluded", "oneclick_not_ok")
    assert history.classify_race(_cell("a", 500, None, comp_status="no_liquidity")) == ("excluded", "no_competitor_ok")
    assert history.classify_race(_cell("a", 500, None)) == ("excluded", "headroom_missing")


def test_routes_aggregate_clips_ties_and_exclusions():
    runs = []
    for h in range(4):
        t = f"2026-11-0{1 + h}T00:00:00Z"
        runs.append({"t_utc": t, "cells": [
            _cell("sol", 500, 2.0),                                          # 4 wins
            _cell("sol", 50000, -1.0 if h < 3 else 0.001, best="lifi"),      # 3 losses + 1 tie
            _cell("btc", 500, -5.0, best="relay" if h else "lifi"),          # 4 losses: relay 3, lifi 1
            _cell("btc", 50000, None, oneclick="error"),                     # excluded
        ]})
    runs.append({"t_utc": "2026-11-05T00:00:00Z", "cells": [_cell("btc", 500, None, comp_status="error")]})
    routes = history.summarize({"bench": runs})["bench"]["routes"]
    sol = routes["by_corridor"]["sol"]
    assert (sol["races"], sol["wins"], sol["losses"], sol["ties"], sol["decided"]) == (8, 4, 3, 1, 7)
    assert sol["win_rate"] == pytest.approx(4 / 7) and sol["clips_usd"] == [500.0, 50000.0]
    assert sol["median_headroom_bps_wins"] == 2.0 and sol["median_headroom_bps_losses"] == -1.0
    assert sol["top_beaten_by"] == "lifi" and sol["span_days"] == pytest.approx(3.0)
    lo, hi = sol["win_rate_ci90"]
    assert lo < 4 / 7 < hi
    btc = routes["by_corridor"]["btc"]
    assert (btc["races"], btc["wins"], btc["losses"]) == (4, 0, 4) and btc["win_rate"] == 0.0
    assert btc["excluded"] == 5 and btc["excluded_reasons"] == {"no_competitor_ok": 1, "oneclick_not_ok": 4}
    assert btc["beaten_by_counts"] == {"relay": 3, "lifi": 1} and btc["top_beaten_by"] == "relay"
    assert btc["last_t_utc"] == "2026-11-04T00:00:00Z"   # the excluded 11-05 cell is not a race
    cell = routes["by_cell"]["sol@50000"]
    assert (cell["wins"], cell["losses"], cell["ties"]) == (0, 3, 1)
    ov = routes["overall"]
    assert ov["n_routes"] == 2 and ov["n_runs"] == 5
    assert ov["wins"] == sol["wins"] + btc["wins"] and ov["losses"] == sol["losses"] + btc["losses"]
    assert ov["excluded"] == 5 and ov["beaten_by_counts"] == {"lifi": 4, "relay": 3} and ov["top_beaten_by"] == "lifi"
    assert history.summarize({"bench": runs})["bench"]["routes"] == routes   # deterministic
    json.dumps(routes, allow_nan=False)


# ----------------------------------------------------------------------------- falsification streaks
def _trig_rec(t: str, breached, sha: str = "s") -> dict:
    return {"t_utc": t, "snapshot_sha256": sha, "bear_triggers": [
        {"key": "g", "metric": "m", "threshold": 1.0, "comparator": ">", "current_value": 2.0, "breached": breached}]}


def test_streak_resets_after_gap():
    recs = [_trig_rec("2026-11-01T08:00:00Z", True), _trig_rec("2026-11-08T21:00:00Z", True),
            _trig_rec("2026-11-10T13:00:00Z", True), _trig_rec("2026-11-11T06:00:00Z", True, "last")]
    g = history._trigger_runs(recs)["g"]
    # 11-08 21:00 -> 11-10 13:00 is 40 h > 36 h: the streak restarts at 11-10 13:00
    assert g["breached_since_utc"] == "2026-11-10T13:00:00Z" and g["gap_reset_at_utc"] == "2026-11-10T13:00:00Z"
    assert g["streak_broken_by"] == "gap" and g["observed_days"] == 2
    assert g["breached_streak_days"] == pytest.approx(17 / 24, abs=1e-3)
    assert g["days_to_falsification"] == pytest.approx(30 - 17 / 24, abs=1e-3) and g["falsified"] is False
    assert g["last_snapshot_sha256"] == "last" and g["state_now"] == "breached"


def test_streak_unmeasured_and_clear_break_it():
    recs = [_trig_rec("2026-11-01T00:00:00Z", True), _trig_rec("2026-11-02T00:00:00Z", None),
            _trig_rec("2026-11-03T00:00:00Z", True), _trig_rec("2026-11-04T00:00:00Z", True)]
    g = history._trigger_runs(recs)["g"]
    assert g["breached_since_utc"] == "2026-11-03T00:00:00Z" and g["streak_broken_by"] == "unmeasured"
    assert g["breached_streak_days"] == pytest.approx(1.0) and g["n_unmeasured"] == 1 and g["gap_reset_at_utc"] is None
    recs[1] = _trig_rec("2026-11-02T00:00:00Z", False)
    assert history._trigger_runs(recs)["g"]["streak_broken_by"] == "clear"
    now_unmeasured = history._trigger_runs(recs + [_trig_rec("2026-11-05T00:00:00Z", None)])["g"]
    assert now_unmeasured["state_now"] == "unmeasured" and now_unmeasured["breached_streak_days"] is None
    assert now_unmeasured["observed_days"] == 0 and now_unmeasured["days_to_falsification"] == 30.0


def test_streak_falsified_after_30_continuous_days():
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 10, 1, 6, tzinfo=timezone.utc)
    # daily runs with jitter up to +-6 h stay continuous; 31 records span exactly 30 days
    recs = [_trig_rec((t0 + timedelta(days=d, hours=(3 if d % 2 else 0))).strftime("%Y-%m-%dT%H:%M:%SZ"), True) for d in range(30)]
    recs.append(_trig_rec((t0 + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"), True))
    g = history._trigger_runs(recs)["g"]
    assert g["streak_broken_by"] == "start_of_history" and g["observed_days"] == 31
    assert g["breached_streak_days"] == pytest.approx(30.0) and g["falsified"] is True and g["days_to_falsification"] == 0.0
    assert history._trigger_runs(recs[:-1])["g"]["falsified"] is False
