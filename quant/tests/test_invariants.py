"""The five mandated invariant tests (docs/MODEL_DESIGN.md section 6, QUANT_PIPELINE_SPEC section 6).

They run against the artifacts written by ``python -m valuo.reproduce`` and skip with a clear message
when ``artifacts/latest_snapshot.json`` / ``manifest.json`` are absent. No network is used: the Monte
Carlo determinism check re-runs the model on the snapshot's own inputs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from valuo import assumptions, config
from valuo.collectors.execution_bench import friction_bps
from valuo.models.sotp_valuation import run_sotp
from valuo.provenance import sha256_bytes
from valuo.schemas import Manifest, Snapshot

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _artifact_paths() -> tuple[Path, Path]:
    return config.SNAPSHOT_PATH, config.MANIFEST_PATH


@pytest.fixture(scope="module")
def artifacts() -> tuple[Snapshot, Manifest, bytes]:
    snap_path, man_path = _artifact_paths()
    if not snap_path.exists() or not man_path.exists():
        pytest.skip(
            f"artifacts absent ({snap_path}, {man_path}); run `make reproduce` "
            "(cd quant && uv run python -m valuo.reproduce) first"
        )
    raw = snap_path.read_bytes()
    snapshot = Snapshot.model_validate_json(raw)
    manifest = Manifest.model_validate_json(man_path.read_bytes())
    return snapshot, manifest, raw


# 1 ----------------------------------------------------------------------------------------------------
def test_near_rpc_ground_truth(artifacts):
    snapshot, _, _ = artifacts
    t = snapshot.near_rpc
    assert t.total_supply_near > 1_000_000_000
    assert 0 < t.max_inflation_rate <= 0.05
    intents = next((s for s in t.tracked_sinks if s.account_id == "intents.near"), None)
    assert intents is not None, "intents.near must be among the tracked sinks"
    assert intents.storage_locked_near > 50_000
    assert intents.storage_locked_near == pytest.approx(intents.storage_bytes * t.storage_amount_per_byte_yocto / 1e24, rel=1e-12)
    assert 0.25 < t.staked_supply_ratio < 0.80
    assert t.staked_supply_ratio == pytest.approx(t.total_staked_near / t.total_supply_near, rel=1e-12)
    assert t.gross_daily_issuance_near == pytest.approx(t.total_supply_near * t.max_inflation_rate / 365.25, rel=1e-12)
    ei = t.epoch_issuance
    assert ei.nominal_annual_issuance_near == pytest.approx(t.total_supply_near * t.max_inflation_rate, rel=1e-9)
    if ei.implied_annual_issuance_near is not None:
        # Measured issuance must sit within 15% of the protocol cap (epoch timing jitter, kicked-out validators).
        assert ei.implied_annual_issuance_near == pytest.approx(ei.nominal_annual_issuance_near, rel=0.15)
        assert ei.minted_per_epoch_near is not None and ei.minted_per_epoch_near > 0
        assert ei.implied_annual_issuance_near == pytest.approx(ei.minted_per_epoch_near * ei.epochs_per_year, rel=1e-9)
    # Supply physics must use the measured issuance when it exists (MODEL_DESIGN 4.1).
    sp = snapshot.supply_physics
    expected_daily = (ei.implied_annual_issuance_near if ei.implied_annual_issuance_near is not None else ei.nominal_annual_issuance_near) / 365.25
    assert sp.current_daily_issuance_near == pytest.approx(expected_daily, rel=1e-9)
    assert sp.current_daily_sinks_near["total"] == pytest.approx(
        sp.current_daily_sinks_near["buyback"] + sp.current_daily_sinks_near["gas_burn"] + sp.current_daily_sinks_near["state_lock"], rel=1e-12
    )
    assert sp.sink_coverage_ratio == pytest.approx(sp.current_daily_sinks_near["total"] / sp.current_daily_issuance_near, rel=1e-9)
    # Buyback identity: V x tau x alpha / P == holders_revenue_30d / 30 / P when the live numbers were used.
    fees, price = snapshot.intents_forensics.fees, snapshot.intents_forensics.price
    if (
        fees.get("holders_revenue_30d_usd") is not None and price.get("current_usd")
        and assumptions.value("buyback_capture_ratio_override", {a.key: a for a in snapshot.assumptions}) < 0
        and sp.inputs["near_price_usd"].value == pytest.approx(price["current_usd"])
    ):
        assert sp.current_daily_sinks_near["buyback"] == pytest.approx(fees["holders_revenue_30d_usd"] / 30.0 / price["current_usd"], rel=1e-9)


# 2 ----------------------------------------------------------------------------------------------------
def test_execution_benchmark_live_quotes(artifacts):
    snapshot, manifest, _ = artifacts
    bench = snapshot.execution_bench
    if bench is None:
        pytest.skip("execution_bench is null in this snapshot (--skip-bench); re-run `make reproduce` without --skip-bench")
    ok_quotes = [q for r in bench.results for q in r.quotes if q.status == "ok"]
    assert ok_quotes, "no venue returned an ok quote"
    for q in ok_quotes:
        assert q.amount_out_formatted is not None and q.amount_out_formatted > 0
        assert q.amount_out_raw is not None and int(q.amount_out_raw) > 0
    assert any(q.venue == "1click" for q in ok_quotes), "1Click returned no ok quote at any clip"
    competitors_ok = {q.venue for q in ok_quotes if q.venue != "1click"}
    assert len(competitors_ok) >= 2, f"need >= 2 external competitors with ok quotes, got {competitors_ok}"
    # Friction identity recomputed exactly from the stored legs.
    for r in bench.results:
        for q in r.quotes:
            if q.status != "ok":
                assert q.friction_bps_usd is None and q.friction_bps_raw is None
                continue
            if q.friction_bps_usd is not None:
                assert q.friction_bps_usd == pytest.approx((q.amount_in_usd - q.amount_out_usd) / q.amount_in_usd * 1e4, rel=1e-12, abs=1e-12)
                assert q.friction_bps_usd == pytest.approx(friction_bps(q.amount_in_usd, q.amount_out_usd), rel=1e-12, abs=1e-12)
            if q.friction_bps_raw is not None:
                in_raw, out_raw = int(q.amount_in_raw), int(q.amount_out_raw)
                assert q.friction_bps_raw == pytest.approx((in_raw - out_raw) / in_raw * 1e4, rel=1e-12, abs=1e-12)
        # Headroom identity on DESTINATION UNITS: (out_1click - out_best) / out_best x 1e4 for the identical raw input; no oracle.
        if r.headroom_bps is not None:
            assert r.headroom_basis == "dest_units"
            one = next(q for q in r.quotes if q.venue == "1click" and q.status == "ok")
            comp = [int(q.amount_out_raw) for q in r.quotes if q.venue != "1click" and q.status == "ok" and q.amount_out_raw is not None]
            assert comp and len({q.amount_in_raw for q in r.quotes if q.status == "ok"}) == 1  # every venue priced the same raw input
            best = max(comp)
            assert r.headroom_bps == pytest.approx((int(one.amount_out_raw) - best) / best * 1e4, rel=1e-12, abs=1e-12)
            assert r.oneclick_rank == 1 + sum(1 for out in comp if out > int(one.amount_out_raw))
            assert r.best_competitor == next(q.venue for q in r.quotes if q.status == "ok" and q.venue != "1click" and int(q.amount_out_raw) == best)
            # Every ok quote's USD legs in the cell are valued at ONE common price, recorded in price_basis.
            assert r.price_basis.get("source") in ("oneclick_token_list_oracle", "median_venue_oracle", None)
            prices = {getattr(q, "oracle_dest_price_usd", None) for q in r.quotes if q.status == "ok" and q.friction_bps_usd is not None}
            assert len(prices) <= 1, prices
    # Every ok quote's raw body is in the manifest under its sha256.
    shas = {rec.sha256 for rec in manifest.records}
    for q in ok_quotes:
        assert q.raw_record_sha256 in shas, f"{q.venue} quote sha {q.raw_record_sha256[:12]} missing from manifest"


# 3 ----------------------------------------------------------------------------------------------------
def test_hhi_bounds(artifacts):
    snapshot, _, _ = artifacts
    f = snapshot.intents_forensics
    assert 0 < f.hhi_external <= 10_000
    assert 0 < f.hhi_all <= 10_000
    assert f.callers, "caller list is empty"
    shares = [c.share for c in f.callers]
    assert abs(sum(shares) - 1.0) < 1e-6
    assert f.hhi_external == pytest.approx(sum((100 * s) ** 2 for s in shares), rel=1e-9)
    assert f.n_eff_external == pytest.approx(10_000 / f.hhi_external, rel=1e-9)
    receipts = sum(c.receipts for c in f.callers)
    for c in f.callers:
        assert c.share == pytest.approx(c.receipts / receipts, rel=1e-9)
    assert 0.0 <= f.ai_agent_share <= 1.0 and 0.0 <= f.bridge_share <= 1.0
    assert f.ai_agent_share == pytest.approx(sum(c.share for c in f.callers if c.cls.value == "ai_agent"), abs=1e-12)
    assert f.receipts_sampled >= receipts > 0
    ex_ai = (f.caller_sample or {}).get("hhi_external_ex_ai_agent")
    if ex_ai is not None:
        assert 0 < ex_ai <= 10_000


# 4 ----------------------------------------------------------------------------------------------------
def test_monte_carlo_determinism(artifacts):
    snapshot, _, _ = artifacts
    registry = {a.key: a for a in snapshot.assumptions}
    kwargs = dict(seed=snapshot.sotp.seed, n_paths=snapshot.sotp.n_paths, horizon_months=snapshot.sotp.horizon_months, bench=snapshot.execution_bench)
    args = (snapshot.near_rpc, snapshot.intents_forensics, snapshot.comps, snapshot.supply_physics, registry)
    a = run_sotp(*args, **kwargs)
    b = run_sotp(*args, **kwargs)
    assert a.fdv_percentiles == b.fdv_percentiles
    assert a.price_percentiles == b.price_percentiles
    assert np.allclose(a.fan_chart["fdv_p50"], b.fan_chart["fdv_p50"], atol=1e-9)
    assert a.fan_chart == b.fan_chart
    assert a.model_dump() == b.model_dump()
    # And the re-run reproduces the snapshot itself (same inputs, same seed -> same percentiles).
    for k, v in snapshot.sotp.fdv_percentiles.items():
        assert a.fdv_percentiles[k] == pytest.approx(v, rel=1e-9), k
    assert np.allclose(a.fan_chart["fdv_p50"], snapshot.sotp.fan_chart["fdv_p50"], rtol=1e-9)
    for k in ("p10", "p25", "p50", "p75", "p90"):
        assert a.fdv_percentiles[k] >= 0
    pct = [snapshot.sotp.fdv_percentiles[k] for k in ("p10", "p25", "p50", "p75", "p90")]
    assert pct == sorted(pct)
    assert snapshot.sotp.seed == snapshot.seed


# 5 ----------------------------------------------------------------------------------------------------
def test_manifest_sha256_integrity(artifacts):
    snapshot, manifest, raw = artifacts
    assert _HEX64.match(manifest.snapshot_sha256)
    assert manifest.snapshot_sha256 == sha256_bytes(raw), "manifest.snapshot_sha256 must equal sha256 of the snapshot file bytes"
    assert manifest.block_height == snapshot.near_rpc.block_height
    assert manifest.block_hash == snapshot.near_rpc.block_hash
    assert manifest.records, "manifest has no raw records"
    for rec in manifest.records:
        assert _HEX64.match(rec.sha256), f"{rec.source}/{rec.name} sha256 is not 64-char hex"
        if rec.raw_path:
            path = config.REPO_ROOT / rec.raw_path if not Path(rec.raw_path).is_absolute() else Path(rec.raw_path)
            if path.exists():
                assert sha256_bytes(path.read_bytes()) == rec.sha256, f"raw payload {rec.raw_path} does not hash to its manifest entry"
    assert manifest.failures == sum(1 for r in manifest.records if not r.ok)
    assert manifest.sources == {s: sum(1 for r in manifest.records if r.source == s) for s in sorted({r.source for r in manifest.records})}
    if manifest.memo_sha256:
        memo_path = config.MEMO_PATH
        if memo_path.exists():
            assert sha256_bytes(memo_path.read_bytes()) == manifest.memo_sha256
    # The snapshot is strict JSON (no NaN / Infinity) and round-trips.
    parsed = json.loads(raw, parse_constant=lambda c: pytest.fail(f"non-finite constant {c} in snapshot JSON"))
    assert Snapshot.model_validate(parsed).near_rpc.block_hash == manifest.block_hash
