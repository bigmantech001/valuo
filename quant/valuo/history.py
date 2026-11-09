"""History store: turns single snapshots and quote races into append-only time series.

Files (all under ``artifacts/history/``, committed to the repository):

- ``snapshots.jsonl``  one compact record per canonical pipeline run (``record_from_snapshot``), de-duplicated by
  ``snapshot_sha256``. Seeded from the canonical ``artifacts/latest_snapshot.json``; no earlier point is invented.
- ``bench.jsonl``      one record per standalone quote race (``python -m valuo.history bench``), de-duplicated by
  ``t_utc``. Every venue response is persisted gzip-compressed under ``raw/<YYYYMMDDTHHMMSSZ>/`` and the record keeps
  the SHA-256 of the exact *uncompressed* response bytes (verify with ``gunzip -c f.json.gz | shasum -a 256`` or
  ``python -m valuo.history verify``).
- ``summary.json``     series + robust statistics per metric for the web History view (``summarize``).

CLI::

    uv run python -m valuo.history snapshot   # append from artifacts/latest_snapshot.json + manifest.json
    uv run python -m valuo.history bench      # live quote race -> bench.jsonl + raw/<utc>/ + summary.json
    uv run python -m valuo.history summary    # rebuild summary.json
    uv run python -m valuo.history verify     # re-hash every raw payload referenced by bench.jsonl
    uv run python -m valuo.history merge --from DIR   # union DIR/{snapshots,bench}.jsonl into the store (CI rebase)

Missing snapshot keys become null; nothing is substituted.
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import math
import shutil
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from valuo import config
from valuo.provenance import ProvenanceLedger, sha256_bytes, sha256_file, utc_now_iso

__all__ = [
    "SNAPSHOT_SCHEMA", "BENCH_SCHEMA", "SUMMARY_SCHEMA", "HISTORY_DIRNAME",
    "history_dir", "record_from_snapshot", "record_from_bench", "append", "read_jsonl",
    "series_stats", "summarize", "write_summary", "record_canonical_run", "run_bench", "verify_bench_raw",
    "merge_from", "main",
]

SNAPSHOT_SCHEMA = "valuo.history.snapshot/1"
BENCH_SCHEMA = "valuo.history.bench/1"
SUMMARY_SCHEMA = "valuo.history.summary/1"
HISTORY_DIRNAME = "history"
BOOTSTRAP_RESAMPLES = 2000
CI_MIN_N = 5  # below this a percentile CI of the median is not reported (null)
# Hourly quote races: modest concurrency for free endpoints (the canonical pipeline uses 8).
BENCH_CONCURRENCY = 4
BENCH_BUDGET_S = 60.0


# ----------------------------------------------------------------------------- paths / getters
def history_dir(artifacts_dir: Path | str | None = None) -> Path:
    base = Path(artifacts_dir).expanduser().resolve() if artifacts_dir is not None else config.ARTIFACTS_DIR
    return base / HISTORY_DIRNAME


def _get(obj: Any, *path: str | int) -> Any:
    """Nested lookup; any missing key / wrong type returns None."""
    cur = obj
    for key in path:
        if isinstance(cur, Mapping) and isinstance(key, str):
            cur = cur.get(key)
        elif isinstance(cur, Sequence) and not isinstance(cur, (str, bytes)) and isinstance(key, int):
            cur = cur[key] if -len(cur) <= key < len(cur) else None
        else:
            return None
        if cur is None:
            return None
    return cur


def _num(value: Any) -> float | None:
    """Finite float or None (bools are not numbers here)."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _first_num(obj: Any, *paths: tuple[str | int, ...]) -> float | None:
    for path in paths:
        value = _num(_get(obj, *path))
        if value is not None:
            return value
    return None


def _ci_pair(value: Any) -> tuple[float | None, float | None]:
    """Accepts [lo, hi], {"low"/"lo"/"p05"/"p025": .., "high"/"hi"/"p95"/"p975": ..}."""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
        return _num(value[0]), _num(value[1])
    if isinstance(value, Mapping):
        lo = next((_num(value[k]) for k in ("low", "lo", "lower", "p05", "p025", "p5", "p2_5") if k in value), None)
        hi = next((_num(value[k]) for k in ("high", "hi", "upper", "p95", "p975", "p97_5") if k in value), None)
        return lo, hi
    return None, None


def _hhi_solver_ci(sc: Any) -> tuple[float | None, float | None]:
    """Find an HHI_solver confidence interval if the forensics collector published one (field name not fixed yet)."""
    if not isinstance(sc, Mapping):
        return None, None
    for key in ("hhi_solver_ci", "hhi_solver_ci90", "hhi_solver_ci95", "hhi_solver_bootstrap_ci", "hhi_ci"):
        lo, hi = _ci_pair(sc.get(key))
        if lo is not None or hi is not None:
            return lo, hi
    for lo_key, hi_key in (("hhi_solver_ci_low", "hhi_solver_ci_high"), ("hhi_solver_ci_lo", "hhi_solver_ci_hi"),
                           ("hhi_solver_p05", "hhi_solver_p95"), ("hhi_solver_p10", "hhi_solver_p90")):
        if lo_key in sc or hi_key in sc:
            return _num(sc.get(lo_key)), _num(sc.get(hi_key))
    boot = sc.get("bootstrap")
    if isinstance(boot, Mapping):
        return _hhi_solver_ci({f"hhi_solver_{k}" if not str(k).startswith("hhi") else k: v for k, v in boot.items()})
    return None, None


def _confidential_share_status(volume: Any) -> str | None:
    """Explicit status when the collector publishes one, else derived from split_checks (fail > pass > skip)."""
    if not isinstance(volume, Mapping):
        return None
    for key in ("confidential_share_status", "split_status", "confidential_status"):
        value = volume.get(key)
        if isinstance(value, str) and value:
            return value
    checks = volume.get("split_checks")
    if isinstance(checks, list) and checks:
        statuses = [str(c.get("status")) for c in checks if isinstance(c, Mapping) and c.get("status") is not None]
        if any(s not in ("pass", "skip") for s in statuses):
            return "checks_failed"
        if any(s == "pass" for s in statuses):
            return "checks_passed"
    if _num(volume.get("confidential_share_30d")) is None:
        return "missing"
    return None


def _tracked_sink(near_rpc: Any, account_id: str) -> Mapping[str, Any] | None:
    for sink in _get(near_rpc, "tracked_sinks") or []:
        if isinstance(sink, Mapping) and sink.get("account_id") == account_id:
            return sink
    return None


# ----------------------------------------------------------------------------- snapshot -> record
def record_from_snapshot(snapshot: Mapping[str, Any], manifest: Mapping[str, Any] | None = None, *,
                         snapshot_file_sha256: str | None = None) -> dict[str, Any]:
    """Pure: compact history record from a parsed snapshot and its manifest. Missing keys -> null.

    ``metrics`` is a flat {name: float|null} map so the summary can treat every series alike; categorical
    state (statuses, trigger breaches) lives in ``status`` and ``bear_triggers``.
    """
    s = snapshot if isinstance(snapshot, Mapping) else {}
    m = manifest if isinstance(manifest, Mapping) else {}
    rpc = s.get("near_rpc") or {}
    bench = s.get("execution_bench") or {}
    forensics = s.get("intents_forensics") or {}
    volume = forensics.get("volume") if isinstance(forensics, Mapping) else None
    fees = forensics.get("fees") if isinstance(forensics, Mapping) else None
    solver = forensics.get("solver_concentration") if isinstance(forensics, Mapping) else None
    supply = s.get("supply_physics") or {}
    sotp = s.get("sotp") or {}
    bear = s.get("bear_case") or {}
    intents_sink = _tracked_sink(rpc, "intents.near")
    ci_lo, ci_hi = _hhi_solver_ci(solver)

    metrics: dict[str, float | None] = {
        "near_price_usd": _first_num(forensics, ("price", "current_usd")),
        "total_supply_near": _num(_get(rpc, "total_supply_near")),
        "measured_daily_issuance_near": _num(_get(rpc, "measured_daily_issuance_near")),
        "max_inflation_rate": _num(_get(rpc, "max_inflation_rate")),
        "total_staked_near": _num(_get(rpc, "total_staked_near")),
        "sinks_total_near_day": _num(_get(supply, "current_daily_sinks_near", "total")),
        "sinks_buyback_near_day": _num(_get(supply, "current_daily_sinks_near", "buyback")),
        "sinks_gas_burn_near_day": _num(_get(supply, "current_daily_sinks_near", "gas_burn")),
        "sinks_state_lock_near_day": _num(_get(supply, "current_daily_sinks_near", "state_lock")),
        "sink_coverage_ratio": _num(_get(supply, "sink_coverage_ratio")),
        "net_float_change_near_day": _num(_get(supply, "current_net_float_change_near_day")),
        "intents_near_storage_bytes": _num(_get(intents_sink, "storage_bytes")),
        "intents_near_locked_near": _num(_get(intents_sink, "storage_locked_near")),
        "total_state_locked_near": _num(_get(rpc, "total_state_locked_near")),
        "volume_24h_usd": _num(_get(volume, "24h")),
        "volume_7d_usd": _num(_get(volume, "7d")),
        "volume_30d_usd": _num(_get(volume, "30d")),
        "confidential_share_30d": _num(_get(volume, "confidential_share_30d")),
        "volume_30d_vs_record_drawdown": _num(_get(volume, "drawdown_from_30d_record")),
        "gross_take_bps": _num(_get(fees, "gross_take_bps")),
        "net_take_bps": _num(_get(fees, "net_take_bps")),
        "competitive_fee_ceiling_bps": _num(_get(bench, "competitive_fee_ceiling_bps")),
        "hhi_external": _num(_get(forensics, "hhi_external")),
        "n_eff_external": _num(_get(forensics, "n_eff_external")),
        "hhi_solver": _num(_get(solver, "hhi_solver")),
        "hhi_solver_ci_low": ci_lo,
        "hhi_solver_ci_high": ci_hi,
        "n_eff_solver": _num(_get(solver, "n_eff_solver")),
        "solver_fills_sampled": _num(_get(solver, "n_fills")),
        "ai_agent_share": _num(_get(forensics, "ai_agent_share")),
        "sotp_fdv_p10": _num(_get(sotp, "fdv_percentiles", "p10")),
        "sotp_fdv_p50": _num(_get(sotp, "fdv_percentiles", "p50")),
        "sotp_fdv_p90": _num(_get(sotp, "fdv_percentiles", "p90")),
        "deterministic_fdv_usd": _first_num(sotp, ("deterministic_fdv_usd",), ("deterministic_base", "fdv_total"),
                                            ("calibration", "deterministic_base", "fdv_total")),
        "current_fdv_usd": _num(_get(sotp, "current_fdv_usd")),
        "upside_p50_pct": _num(_get(sotp, "upside_p50_pct")),
        "terminal_multiple_used": _num(_get(sotp, "calibration", "terminal_multiple_used")),
        "breakeven_daily_volume_usd_status_quo": _num(_get(supply, "breakeven_daily_volume_usd", "status_quo")),
        "breakeven_daily_volume_usd_svrn_glidepath": _num(_get(supply, "breakeven_daily_volume_usd", "svrn_glidepath")),
    }
    headroom = _get(bench, "headroom_by_archetype_bps")
    if isinstance(headroom, Mapping):
        for archetype, value in sorted(headroom.items()):
            metrics[f"headroom_bps_{archetype}"] = _num(value)

    triggers: list[dict[str, Any]] = []
    for sc in _get(bear, "scenarios") or []:
        if not isinstance(sc, Mapping):
            continue
        triggers.append({
            "key": sc.get("key"),
            "metric": sc.get("early_warning_metric"),
            "current_value": _num(sc.get("current_value")),
            "threshold": _num(sc.get("trigger_threshold")),
            "comparator": sc.get("trigger_comparator"),
            "evaluated": sc.get("trigger_evaluated"),
            "breached": sc.get("trigger_breached"),
            "secondary_metric": sc.get("secondary_metric"),
            "secondary_value": _num(sc.get("secondary_value")),
            "secondary_threshold": _num(sc.get("secondary_threshold")),
            "secondary_breached": sc.get("secondary_breached"),
            "scenario_fdv_usd": _num(sc.get("sotp_fdv_p50")),
        })
        if sc.get("key"):
            metrics[f"bear_{sc['key']}_value"] = _num(sc.get("current_value"))

    run_config = s.get("run_config") if isinstance(s.get("run_config"), Mapping) else {}
    return {
        "schema": SNAPSHOT_SCHEMA,
        "t_utc": s.get("generated_at_utc") or m.get("generated_at_utc"),
        "block_height": _get(rpc, "block_height") if _get(rpc, "block_height") is not None else m.get("block_height"),
        "block_hash": _get(rpc, "block_hash") or m.get("block_hash"),
        "snapshot_sha256": m.get("snapshot_sha256") or snapshot_file_sha256,
        "snapshot_file_sha256": snapshot_file_sha256,
        "memo_sha256": m.get("memo_sha256"),
        "schema_version": s.get("schema_version"),
        "valuo_version": s.get("valuo_version"),
        "seed": s.get("seed"),
        "n_paths": _get(sotp, "n_paths"),
        "canonical": run_config.get("canonical"),
        "bench_ran_at_utc": _get(bench, "ran_at_utc"),
        "metrics": metrics,
        "status": {
            "confidential_share_status": _confidential_share_status(volume),
            "confidential_share_assumed": _get(sotp, "calibration", "confidential_share_assumed"),
            "confidential_tvl_source_status": _get(forensics, "confidential_tvl_source_status"),
            "terminal_multiple_clipped": _get(sotp, "calibration", "terminal_multiple_clipped"),
            "solver_sample_thin": next((sc.get("sample_thin") for sc in _get(bear, "scenarios") or []
                                        if isinstance(sc, Mapping) and sc.get("key") == "solver_cartelization"), None),
            "execution_bench_present": bool(bench),
        },
        "bear_triggers": triggers,
        "bear_triggers_breached": _get(bear, "triggers_breached"),
        "bear_triggers_evaluated": _get(bear, "triggers_evaluated"),
    }


# ----------------------------------------------------------------------------- bench -> record
def _quote_raw_paths(records: Iterable[Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in records:
        sha = getattr(r, "sha256", None) if not isinstance(r, Mapping) else r.get("sha256")
        path = getattr(r, "raw_path", None) if not isinstance(r, Mapping) else r.get("raw_path")
        if sha and path:
            out[sha] = path
    return out


def record_from_bench(bench: Mapping[str, Any], raw_records: Sequence[Mapping[str, Any]] = (), *,
                      raw_dir: str | None = None) -> dict[str, Any]:
    """Pure: compact bench.jsonl record from an ExecutionBenchmark dump plus its ledger records."""
    b = bench if isinstance(bench, Mapping) else {}
    archetypes = {c.get("corridor_id"): c.get("archetype") for c in b.get("corridors") or [] if isinstance(c, Mapping)}
    paths = _quote_raw_paths(raw_records)
    cells: list[dict[str, Any]] = []
    for res in b.get("results") or []:
        if not isinstance(res, Mapping):
            continue
        venues: dict[str, Any] = {}
        oneclick_status = None
        for q in res.get("quotes") or []:
            if not isinstance(q, Mapping) or not q.get("venue"):
                continue
            friction_raw = _num(q.get("friction_bps_raw"))
            sha = q.get("raw_record_sha256")
            venues[q["venue"]] = {
                "status": q.get("status"),
                "supported": q.get("supported"),
                "amount_out_raw": q.get("amount_out_raw"),
                "amount_out": _num(q.get("amount_out_formatted")),
                "friction_bps": friction_raw if friction_raw is not None else _num(q.get("friction_bps_usd")),
                "friction_bps_usd": _num(q.get("friction_bps_usd")),
                "time_estimate_s": _num(q.get("time_estimate_s")),
                "route_tool": q.get("route_tool"),
                "error_code": q.get("error_code"),
                "raw_sha256": sha,
                "raw_path": paths.get(sha) if sha else None,
            }
            if q["venue"] == "1click":
                oneclick_status = q.get("status")
        cells.append({
            "corridor_id": res.get("corridor_id"),
            "archetype": res.get("archetype") or archetypes.get(res.get("corridor_id")),
            "clip_usd": _num(res.get("clip_usd")),
            "headroom_bps": _num(res.get("headroom_bps")),
            "best_competitor": res.get("best_competitor"),
            "oneclick_rank": res.get("oneclick_rank"),
            "oneclick_status": oneclick_status,
            "n_venues_ok": res.get("n_venues_ok"),
            "venues": venues,
        })
    raws = [{
        "source": r.get("source"), "name": r.get("name"), "http_status": r.get("http_status"), "ok": r.get("ok"),
        "sha256": r.get("sha256"), "bytes": r.get("bytes"), "raw_path": r.get("raw_path"),
    } for r in raw_records if isinstance(r, Mapping)]
    return {
        "schema": BENCH_SCHEMA,
        "t_utc": b.get("ran_at_utc"),
        "elapsed_s": _num(b.get("elapsed_s")),
        "clips_usd": b.get("clips_usd"),
        "concurrency": b.get("concurrency"),
        "n_quotes_ok": b.get("n_quotes_ok"),
        "token_list_ok": b.get("token_list_ok"),
        "token_list_sha256": b.get("token_list_sha256"),
        "headroom_by_archetype_bps": {k: _num(v) for k, v in (b.get("headroom_by_archetype_bps") or {}).items()},
        "competitive_fee_ceiling_bps": _num(b.get("competitive_fee_ceiling_bps")),
        "raw_dir": raw_dir,
        "raw_encoding": "gzip; sha256 is over the uncompressed response bytes",
        "cells": cells,
        "raw_records": raws,
    }


# ----------------------------------------------------------------------------- JSONL store
def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    """All parseable records (a torn last line from an interrupted write is skipped, not fatal)."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _dedup_key(record: Mapping[str, Any]) -> str | None:
    if record.get("schema") == SNAPSHOT_SCHEMA and record.get("snapshot_sha256"):
        return f"sha:{record['snapshot_sha256']}"
    t = record.get("t_utc")
    return f"t:{t}" if t else None


def append(path: Path | str, record: Mapping[str, Any]) -> bool:
    """Append one compact JSON line unless a record with the same snapshot sha (or t_utc) exists. True if written."""
    p = Path(path)
    key = _dedup_key(record)
    if key is not None and any(_dedup_key(r) == key for r in read_jsonl(p)):
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    prefix = ""
    if p.exists() and p.stat().st_size > 0:
        with open(p, "rb") as fh:
            fh.seek(-1, 2)
            if fh.read(1) != b"\n":
                prefix = "\n"
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(prefix + line + "\n")
    return True


# ----------------------------------------------------------------------------- statistics
def _parse_t(t: Any) -> datetime | None:
    if not isinstance(t, str):
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None


def series_stats(values: Sequence[float | None], *, seed: int | None = None) -> dict[str, Any]:
    """n, first/last, min/max, mean, median, P10/P90, and a seeded percentile-bootstrap 90% CI of the median."""
    vals = [v for v in (_num(x) for x in values) if v is not None]
    n = len(vals)
    if n == 0:
        return {"n": 0, "first": None, "last": None, "min": None, "max": None, "mean": None, "median": None,
                "p10": None, "p90": None, "change_abs": None, "change_pct": None,
                "median_ci90": None, "ci_method": None}
    arr = np.asarray(vals, dtype=float)
    first, last = vals[0], vals[-1]
    ci = None
    method = None
    if n >= CI_MIN_N:
        rng = np.random.default_rng(config.SEED if seed is None else seed)
        idx = rng.integers(0, n, size=(BOOTSTRAP_RESAMPLES, n))
        medians = np.median(arr[idx], axis=1)
        ci = [float(np.percentile(medians, 5)), float(np.percentile(medians, 95))]
        method = f"percentile bootstrap of the median, {BOOTSTRAP_RESAMPLES} resamples, seed {config.SEED if seed is None else seed}"
    return {
        "n": n, "first": first, "last": last,
        "min": float(arr.min()), "max": float(arr.max()), "mean": float(arr.mean()),
        "median": float(np.median(arr)), "p10": float(np.percentile(arr, 10)), "p90": float(np.percentile(arr, 90)),
        "change_abs": last - first if n > 1 else None,
        "change_pct": ((last - first) / abs(first) * 100.0) if n > 1 and first != 0 else None,
        "median_ci90": ci, "ci_method": method,
    }


def _series_block(points: list[tuple[str, float | None]]) -> dict[str, Any]:
    return {"points": [[t, v] for t, v in points], "stats": series_stats([v for _, v in points])}


def _window(points: list[tuple[str, float | None]], end: datetime | None, hours: float) -> list[float | None]:
    if end is None:
        return []
    out = []
    for t, v in points:
        dt = _parse_t(t)
        if dt is not None and (end - dt).total_seconds() <= hours * 3600:
            out.append(v)
    return out


def _sorted_by_t(records: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted((r for r in records if _parse_t(r.get("t_utc")) is not None), key=lambda r: _parse_t(r["t_utc"]))


def _trigger_runs(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Per bear trigger: value/breach points, and the current consecutive-breach streak (falsification needs 30 days)."""
    by_key: dict[str, list[tuple[str, Any, Any]]] = {}
    meta: dict[str, dict[str, Any]] = {}
    for r in records:
        for trig in r.get("bear_triggers") or []:
            if not isinstance(trig, Mapping) or not trig.get("key"):
                continue
            by_key.setdefault(trig["key"], []).append((r["t_utc"], _num(trig.get("current_value")), trig.get("breached")))
            meta[trig["key"]] = {k: trig.get(k) for k in ("metric", "threshold", "comparator")}
    out: dict[str, Any] = {}
    for key, pts in by_key.items():
        streak_start = None
        for t, _v, breached in reversed(pts):
            if breached is True:
                streak_start = t
            else:
                break
        last_t = _parse_t(pts[-1][0])
        start_dt = _parse_t(streak_start)
        out[key] = {
            **meta[key],
            "points": [[t, v, b] for t, v, b in pts],
            "n_runs": len(pts),
            "n_breached": sum(1 for _t, _v, b in pts if b is True),
            "breached_now": pts[-1][2],
            "breached_since_utc": streak_start,
            "breached_streak_days": round((last_t - start_dt).total_seconds() / 86400.0, 3) if last_t and start_dt else None,
            "falsification_rule": "thesis falsified if a trigger holds for 30 consecutive days",
        }
    return out


def latest_per_utc_day(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Keep the last record of each UTC day (sorted by time).

    The snapshot series is a daily series: re-runs on the same day (manual reruns, methodology fixes) would
    otherwise plot as a vertical stack of points that mix code versions. snapshots.jsonl keeps every record;
    only the summary is thinned, and it reports how many records it dropped.
    """
    by_day: dict[str, Mapping[str, Any]] = {}
    for r in _sorted_by_t(records):
        by_day[_parse_t(r["t_utc"]).strftime("%Y-%m-%d")] = r
    return [by_day[d] for d in sorted(by_day)]


def _summarize_snapshots(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    all_recs = _sorted_by_t(records)
    recs = latest_per_utc_day(all_recs)
    names: list[str] = []
    for r in recs:
        for k in (r.get("metrics") or {}):
            if k not in names:
                names.append(k)
    series = {k: _series_block([(r["t_utc"], _num((r.get("metrics") or {}).get(k))) for r in recs]) for k in names}
    return {
        "n_records": len(recs),
        "n_records_total": len(all_recs),
        "n_same_day_reruns_dropped": len(all_recs) - len(recs),
        "dedup_rule": "latest canonical run per UTC day; snapshots.jsonl keeps every run",
        "first_t_utc": recs[0]["t_utc"] if recs else None,
        "last_t_utc": recs[-1]["t_utc"] if recs else None,
        "block_heights": [[r["t_utc"], r.get("block_height")] for r in recs],
        "snapshot_sha256": [[r["t_utc"], r.get("snapshot_sha256")] for r in recs],
        "series": series,
        "status": [[r["t_utc"], r.get("status")] for r in recs],
        "bear_triggers": _trigger_runs(recs),
    }


def _cell_id(cell: Mapping[str, Any]) -> str:
    clip = _num(cell.get("clip_usd"))
    return f"{cell.get('corridor_id')}@{int(clip) if clip is not None else 'na'}"


def _summarize_bench(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    recs = _sorted_by_t(records)
    last_dt = _parse_t(recs[-1]["t_utc"]) if recs else None
    series_pts: dict[str, list[tuple[str, float | None]]] = {}
    cells: dict[str, dict[str, Any]] = {}

    def add(name: str, t: str, v: Any) -> None:
        series_pts.setdefault(name, []).append((t, _num(v)))

    for r in recs:
        t = r["t_utc"]
        for arch, v in (r.get("headroom_by_archetype_bps") or {}).items():
            add(f"headroom_bps_{arch}", t, v)
        add("competitive_fee_ceiling_bps", t, r.get("competitive_fee_ceiling_bps"))
        add("n_quotes_ok", t, r.get("n_quotes_ok"))
        for cell in r.get("cells") or []:
            if not isinstance(cell, Mapping):
                continue
            cid = _cell_id(cell)
            info = cells.setdefault(cid, {
                "corridor_id": cell.get("corridor_id"), "archetype": cell.get("archetype"), "clip_usd": _num(cell.get("clip_usd")),
                "n_runs": 0, "oneclick_status_counts": {}, "best_competitor_counts": {}, "oneclick_rank_counts": {},
                "venue_status_counts": {},
            })
            info["n_runs"] += 1
            st = str(cell.get("oneclick_status"))
            info["oneclick_status_counts"][st] = info["oneclick_status_counts"].get(st, 0) + 1
            bc = str(cell.get("best_competitor"))
            info["best_competitor_counts"][bc] = info["best_competitor_counts"].get(bc, 0) + 1
            rk = str(cell.get("oneclick_rank"))
            info["oneclick_rank_counts"][rk] = info["oneclick_rank_counts"].get(rk, 0) + 1
            add(f"cell.{cid}.headroom_bps", t, cell.get("headroom_bps"))
            for venue, vq in (cell.get("venues") or {}).items():
                if not isinstance(vq, Mapping):
                    continue
                vs = info["venue_status_counts"].setdefault(venue, {})
                vs[str(vq.get("status"))] = vs.get(str(vq.get("status")), 0) + 1
                add(f"cell.{cid}.{venue}.friction_bps", t, vq.get("friction_bps"))
    for info in cells.values():
        ok = info["oneclick_status_counts"].get("ok", 0)
        info["oneclick_ok_rate"] = ok / info["n_runs"] if info["n_runs"] else None
        rank1 = info["oneclick_rank_counts"].get("1", 0)
        info["oneclick_rank1_rate"] = rank1 / info["n_runs"] if info["n_runs"] else None
    series: dict[str, Any] = {}
    for name, pts in series_pts.items():
        block = _series_block(pts)
        block["window_24h"] = series_stats(_window(pts, last_dt, 24))
        block["window_7d"] = series_stats(_window(pts, last_dt, 24 * 7))
        series[name] = block
    return {
        "n_runs": len(recs),
        "first_t_utc": recs[0]["t_utc"] if recs else None,
        "last_t_utc": recs[-1]["t_utc"] if recs else None,
        "series": series,
        "cells": cells,
    }


def summarize(history: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    """``history`` = {"snapshots": [...], "bench": [...]} -> summary.json payload (see module docstring)."""
    return {
        "schema": SUMMARY_SCHEMA,
        "generated_at_utc": utc_now_iso(),
        "seed": config.SEED,
        "ci_method": (f"90% percentile-bootstrap CI of the median ({BOOTSTRAP_RESAMPLES} resamples, seed {config.SEED}); "
                      f"null when n < {CI_MIN_N}"),
        "snapshots": _summarize_snapshots(history.get("snapshots") or []),
        "bench": _summarize_bench(history.get("bench") or []),
    }


def write_summary(artifacts_dir: Path | str | None = None) -> Path:
    """Rebuild ``artifacts/history/summary.json`` from the JSONL files; returns its path."""
    hdir = history_dir(artifacts_dir)
    hdir.mkdir(parents=True, exist_ok=True)
    payload = summarize({"snapshots": read_jsonl(hdir / "snapshots.jsonl"), "bench": read_jsonl(hdir / "bench.jsonl")})
    path = hdir / "summary.json"
    path.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return path


# ----------------------------------------------------------------------------- canonical-run hook
def record_canonical_run(artifacts_dir: Path | str | None = None, *, allow_noncanonical: bool = False) -> dict[str, Any] | None:
    """Append the snapshot in ``artifacts_dir`` to ``<artifacts_dir>/history/snapshots.jsonl`` and refresh summary.json.

    Returns the record (also when it was already present), or None when the snapshot is missing or the run was
    not canonical (``run_config.canonical`` false) and ``allow_noncanonical`` is not set. Never raises on bad input.
    """
    base = Path(artifacts_dir).expanduser().resolve() if artifacts_dir is not None else config.ARTIFACTS_DIR
    snap_path, man_path = base / "latest_snapshot.json", base / "manifest.json"
    if not snap_path.exists():
        return None
    snapshot = json.loads(snap_path.read_bytes())
    manifest = json.loads(man_path.read_bytes()) if man_path.exists() else {}
    if not allow_noncanonical and _get(snapshot, "run_config", "canonical") is False:
        return None
    record = record_from_snapshot(snapshot, manifest, snapshot_file_sha256=sha256_file(snap_path))
    append(history_dir(base) / "snapshots.jsonl", record)
    write_summary(base)
    return record


# ----------------------------------------------------------------------------- bench CLI
def _stamp(t: str | None = None) -> str:
    dt = _parse_t(t) if t else None
    return (dt or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")


def _gzip_raw(raw_dir: Path, records: list[dict[str, Any]]) -> None:
    """Compress each persisted payload to <name>.gz (mtime 0, deterministic) and point raw_path at it."""
    for r in records:
        rel = r.get("raw_path")
        if not rel:
            continue
        p = Path(rel) if Path(rel).is_absolute() else config.REPO_ROOT / rel
        if not p.exists():
            continue
        data = p.read_bytes()
        gz = p.with_name(p.name + ".gz")
        with open(gz, "wb") as fh, gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as z:
            z.write(data)
        p.unlink()
        r["raw_path"] = (Path(rel).with_name(Path(rel).name + ".gz")).as_posix()


def run_bench(artifacts_dir: Path | str | None = None, *, budget_s: float = BENCH_BUDGET_S,
              concurrency: int = BENCH_CONCURRENCY, refresh_summary: bool = True) -> dict[str, Any]:
    """Live quote race (all corridors x clips) -> raw/<utc>/*.json.gz + bench.jsonl record (+ summary.json)."""
    from valuo.collectors.execution_bench import collect_execution_bench

    hdir = history_dir(artifacts_dir)
    stamp = _stamp()
    raw_dir = hdir / "raw" / stamp
    ledger = ProvenanceLedger(raw_dir=raw_dir, persist_raw=True)
    bench = asyncio.run(collect_execution_bench(ledger, budget_s=budget_s, concurrency=concurrency))
    records = ledger.records_as_dicts()
    if raw_dir.exists():
        _gzip_raw(raw_dir, records)
    rel_raw = config.repo_relative(raw_dir) or str(raw_dir)
    record = record_from_bench(bench.model_dump(mode="json"), records, raw_dir=rel_raw)
    record["warnings"] = list(ledger.warnings)
    if not append(hdir / "bench.jsonl", record):
        shutil.rmtree(raw_dir, ignore_errors=True)
    if refresh_summary:
        write_summary(artifacts_dir)
    return record


def verify_bench_raw(artifacts_dir: Path | str | None = None) -> dict[str, Any]:
    """Re-hash every raw payload referenced by bench.jsonl (gunzip first). Returns counts and mismatches."""
    checked, missing, bad = 0, [], []
    for rec in read_jsonl(history_dir(artifacts_dir) / "bench.jsonl"):
        for r in rec.get("raw_records") or []:
            rel, sha = r.get("raw_path"), r.get("sha256")
            if not rel or not sha:
                continue
            p = Path(rel) if Path(rel).is_absolute() else config.REPO_ROOT / rel
            if not p.exists():
                missing.append(rel)
                continue
            data = gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()
            checked += 1
            if sha256_bytes(data) != sha:
                bad.append(rel)
    return {"checked": checked, "missing": missing, "mismatched": bad, "ok": not missing and not bad}


def merge_from(source_dir: Path | str, artifacts_dir: Path | str | None = None) -> dict[str, int]:
    """Union records from ``source_dir/{snapshots,bench}.jsonl`` into the store (dedup); used by CI after a rebase."""
    src = Path(source_dir)
    hdir = history_dir(artifacts_dir)
    added = {}
    for name in ("snapshots.jsonl", "bench.jsonl"):
        added[name] = sum(1 for rec in read_jsonl(src / name) if append(hdir / name, rec))
    return added


def _fmt_bps(v: Any) -> str:
    v = _num(v)
    return "-" if v is None else f"{v:+.2f}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m valuo.history", description="Valuo history store")
    parser.add_argument("--artifacts", default=None, help="artifacts directory (default: repo artifacts/)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_snap = sub.add_parser("snapshot", help="append the current latest_snapshot.json to snapshots.jsonl")
    p_snap.add_argument("--allow-noncanonical", action="store_true")
    p_bench = sub.add_parser("bench", help="run a live quote race and append it to bench.jsonl")
    p_bench.add_argument("--budget", type=float, default=BENCH_BUDGET_S)
    p_bench.add_argument("--concurrency", type=int, default=BENCH_CONCURRENCY)
    sub.add_parser("summary", help="rebuild summary.json")
    sub.add_parser("verify", help="re-hash raw payloads referenced by bench.jsonl")
    p_merge = sub.add_parser("merge", help="union another history dir's JSONL files into this store")
    p_merge.add_argument("--from", dest="source", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "snapshot":
        rec = record_canonical_run(args.artifacts, allow_noncanonical=args.allow_noncanonical)
        if rec is None:
            print("no canonical snapshot to record (missing, or run_config.canonical is false)", file=sys.stderr)
            return 1
        print(f"snapshot {rec['t_utc']} block {rec['block_height']} sha256 {str(rec['snapshot_sha256'])[:16]}... "
              f"-> {history_dir(args.artifacts) / 'snapshots.jsonl'}")
        return 0
    if args.cmd == "bench":
        rec = run_bench(args.artifacts, budget_s=args.budget, concurrency=args.concurrency)
        print(f"bench {rec['t_utc']} quotes ok {rec['n_quotes_ok']} elapsed {rec['elapsed_s']} s raw {rec['raw_dir']}")
        for cell in rec["cells"]:
            print(f"  {_cell_id(cell):<28} headroom {_fmt_bps(cell['headroom_bps']):>8} bps  best {cell['best_competitor'] or '-':<7}"
                  f" 1click {cell['oneclick_status']}")
        for w in rec.get("warnings") or []:
            print(f"  warning: {w}")
        return 0
    if args.cmd == "summary":
        print(write_summary(args.artifacts))
        return 0
    if args.cmd == "verify":
        res = verify_bench_raw(args.artifacts)
        print(json.dumps(res, indent=1))
        return 0 if res["ok"] else 1
    if args.cmd == "merge":
        added = merge_from(args.source, args.artifacts)
        write_summary(args.artifacts)
        print(json.dumps(added))
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
