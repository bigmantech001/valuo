"""Tests for the reproduce.py integration helpers that do not need the network.

Covers: canonical vs dev output routing, raw/ pruning against the manifest, the README findings splice, the
competitive-ceiling label, and (when artifacts exist) the generated README findings block itself.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from valuo import config
from valuo import reproduce as rp
from valuo.memo_generator import (
    README_FINDINGS_END,
    README_FINDINGS_START,
    render_readme_findings,
)
from valuo.provenance import sha256_bytes
from valuo.schemas import ExecutionBenchmark, Manifest, RawRecord, Snapshot

_H = "ab" * 32


# ----------------------------------------------------------------------------- output routing
def test_default_args_are_canonical_and_write_to_artifacts():
    args = rp.parse_args([])
    assert args.is_default_run is True and args.out_dir == config.ARTIFACTS_DIR
    assert args.nearblocks_delay is None  # the collector reads VALUO_NEARBLOCKS_PAGE_DELAY_S unless the flag is given


@pytest.mark.parametrize(
    "argv",
    [
        ["--skip-bench"], ["--paths", "2000"], ["--paths", "20000"], ["--seed", "7"], ["--horizon", "12"], ["--preset", "bear"], ["--no-archival"],
        ["--clips", "500"], ["--nearblocks-pages", "2"], ["--nearblocks-pages", "12"], ["--bench-budget", "10"],
    ],
)
def test_non_default_runs_go_to_artifacts_dev(argv: list[str]):
    args = rp.parse_args(argv)
    assert args.is_default_run is False
    assert args.out_dir == config.ARTIFACTS_DIR / rp.DEV_SUBDIR


def test_pacing_and_placement_flags_keep_the_run_canonical():
    # These change neither the data sampled nor the model: the canonical artifacts/ is still the target.
    for argv in (["--nearblocks-delay", "1.5"], ["--quiet"], ["--no-duckdb"], ["--nearblocks-pages", str(rp.DEFAULT_NEARBLOCKS_PAGES)], ["--bench-budget", "45"]):
        assert rp.parse_args(argv).is_default_run is True, argv


def test_out_flag_overrides_routing(tmp_path: Path):
    args = rp.parse_args(["--out", str(tmp_path / "somewhere")])
    assert args.out_dir == (tmp_path / "somewhere").resolve() and args.is_default_run is True
    args = rp.parse_args(["--skip-bench", "--out", str(tmp_path)])
    assert args.out_dir == tmp_path.resolve()
    paths = config.artifact_paths(tmp_path)
    assert paths["raw"] == tmp_path.resolve() / "raw" and paths["snapshot"].name == "latest_snapshot.json"


def test_nearblocks_delay_flag_and_validation():
    assert rp.parse_args(["--nearblocks-delay", "0.3"]).nearblocks_delay == 0.3
    with pytest.raises(SystemExit):
        rp.parse_args(["--nearblocks-delay", "-1"])


def test_config_as_dict_has_no_absolute_local_path():
    d = config.as_dict()
    assert d["artifacts_dir"] in ("artifacts", "<outside repository>") or not str(d["artifacts_dir"]).startswith("/")
    assert config.repo_relative(config.REPO_ROOT / "artifacts") == "artifacts"
    assert config.repo_relative(Path("/definitely/not/in/repo")) is None


# ----------------------------------------------------------------------------- raw/ pruning
def _manifest(records: list[RawRecord]) -> Manifest:
    return Manifest(generated_at_utc="2026-11-01T00:00:00.000Z", block_height=1, block_hash="h", snapshot_sha256=_H,
                    snapshot_path="artifacts/latest_snapshot.json", records=records, sources={}, failures=0)


def test_prune_raw_dir_deletes_only_unreferenced_files_inside_raw(tmp_path: Path):
    raw = tmp_path / "raw"
    raw.mkdir()
    keep = raw / "near_rpc__block_final.json"
    stale = raw / "oneclick__quote_old.json"
    keep.write_bytes(b"{}")
    stale.write_bytes(b"{}")
    (raw / "sub").mkdir()
    (raw / "sub" / "nested.json").write_bytes(b"{}")
    outside = tmp_path / "latest_snapshot.json"
    outside.write_bytes(b"{}")
    rec = RawRecord(source="near_rpc", name="block_final", url="u", method="POST", ok=True, http_status=200, fetched_at_utc="t",
                    latency_ms=1.0, bytes=2, sha256=sha256_bytes(b"{}"), raw_path=str(keep))
    deleted = rp.prune_raw_dir(raw, _manifest([rec]))
    assert deleted == ["oneclick__quote_old.json"]
    assert keep.exists() and not stale.exists() and (raw / "sub" / "nested.json").exists() and outside.exists()
    assert rp.prune_raw_dir(tmp_path / "missing", _manifest([rec])) == []


# ----------------------------------------------------------------------------- README splice
def test_update_readme_findings_replaces_only_the_marked_block(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text(f"# Title\n\nintro\n\n{README_FINDINGS_START}\nold\n{README_FINDINGS_END}\n\ntail\n", encoding="utf-8")
    block = f"{README_FINDINGS_START}\nnew block\n{README_FINDINGS_END}"
    assert rp.update_readme_findings(readme, block) is True
    text = readme.read_text(encoding="utf-8")
    assert text == f"# Title\n\nintro\n\n{block}\n\ntail\n"
    assert rp.update_readme_findings(readme, block) is True and readme.read_text(encoding="utf-8") == text  # idempotent
    plain = tmp_path / "plain.md"
    plain.write_text("no markers here\n", encoding="utf-8")
    assert rp.update_readme_findings(plain, block) is False and plain.read_text(encoding="utf-8") == "no markers here\n"
    assert rp.update_readme_findings(tmp_path / "absent.md", block) is False


def test_repo_readme_carries_the_findings_markers_and_no_stale_spec_numbers():
    text = (config.REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert text.count(README_FINDINGS_START) == 1 and text.count(README_FINDINGS_END) == 1
    outside = text.split(README_FINDINGS_START)[0] + text.split(README_FINDINGS_END)[1]
    for stale in ("392", "129,607", "89,654", "$35.8B", "$10.41B", "$160M", "BTC -> USDC", "1.31B"):
        assert stale not in outside, stale
    for corridor in ("ETH USDC -> SOL USDC", "ETH USDC -> native BTC", "Base USDC -> Arbitrum USDC"):
        assert corridor in text, corridor


# ----------------------------------------------------------------------------- ceiling label
def test_competitive_ceiling_note_names_the_binding_venue():
    # The ceiling is the median over cross-VM cells of the BEST competitor's friction, so the lowest per-venue median is
    # the binding one and every other venue is labeled not binding (LI.FI's 25 bps fixed fee is not the ceiling).
    bench = ExecutionBenchmark(ran_at_utc="t", clips_usd=[500.0], corridors=[], results=[],
                               competitor_friction_by_venue_bps={"lifi": {"median": 25.0, "n": 2, "values": [25.0, 25.0]}, "relay": {"median": 3.004, "n": 2, "values": [3.0, 3.008]}})
    assert rp.competitive_ceiling_note(bench) == "Relay 3.0 bps (n=2) binding, LI.FI 25.0 bps (n=2) not binding"
    assert rp.competitive_ceiling_note(None) is None
    assert rp.competitive_ceiling_note(ExecutionBenchmark(ran_at_utc="t", clips_usd=[], corridors=[], results=[])) is None


# ----------------------------------------------------------------------------- findings block against the committed artifacts
def test_render_readme_findings_from_committed_snapshot():
    snap_path, man_path = config.SNAPSHOT_PATH, config.MANIFEST_PATH
    if not snap_path.exists() or not man_path.exists():
        pytest.skip("artifacts absent; run `make reproduce` first")
    snapshot = Snapshot.model_validate_json(snap_path.read_bytes())
    manifest = Manifest.model_validate_json(man_path.read_bytes())
    block = render_readme_findings(snapshot, manifest)
    assert block.startswith(README_FINDINGS_START) and block.rstrip().endswith(README_FINDINGS_END)
    assert f"block {snapshot.near_rpc.block_height:,}" in block and manifest.snapshot_sha256 in block
    assert "| Finding | Value | Basis |" in block
    for label in ("Gross take / net take / capture ratio", "SOTP FDV P10 / P50 / P90", "Deposit/caller HHI / solver HHI"):
        assert label in block, label
    # The committed README must carry exactly this block (reproduce rewrites it on every canonical run).
    readme = (config.REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert block in readme


# ----------------------------------------------------------------------------- evidence scorecard: grade follows the value
def _committed_snapshot() -> Snapshot:
    if not config.SNAPSHOT_PATH.exists():
        pytest.skip("artifacts absent; run `make reproduce` first")
    return Snapshot.model_validate_json(config.SNAPSHOT_PATH.read_bytes())


def _card(snap: Snapshot, forensics=None) -> dict[str, object]:
    claims = rp.build_evidence_scorecard(snap.near_rpc, snap.execution_bench, forensics or snap.intents_forensics, snap.supply_physics,
                                         snap.sotp, snap.comps, None)
    return {c.claim: c for c in claims}


def _claim_by_prefix(card: dict, prefix: str):
    return next(c for k, c in card.items() if k.startswith(prefix))


def test_scorecard_confidential_share_grade_follows_value_and_status():
    snap = _committed_snapshot()
    base = snap.intents_forensics
    conf = "Confidential (dark-pool) execution"

    def with_volume(**upd):
        f = base.model_copy(deep=True)
        f.volume = {**f.volume, **upd}
        return f

    measured = _claim_by_prefix(_card(snap, with_volume(confidential_share_30d=0.41, confidential_share_status="measured")), conf)
    assert measured.status == "VERIFIED_LIVE_API" and "41.0%" in measured.value
    tiny = _claim_by_prefix(_card(snap, with_volume(confidential_share_30d=6.6e-11, confidential_share_status="measured")), conf)
    assert tiny.status == "NOT_SUPPORTED" and "materiality" in tiny.value  # 0% is never VERIFIED
    fb = _claim_by_prefix(_card(snap, with_volume(confidential_share_30d=0.40, confidential_share_30d_reported=6.6e-11,
                                                  confidential_share_status="implausible_fallback",
                                                  confidential_share_reason=["share_below_floor", "stream_ok"])), conf)
    assert fb.status == "ASSUMPTION" and "NOT MEASURED" in fb.value and fb.confidence == "none"
    gone = _claim_by_prefix(_card(snap, with_volume(confidential_share_30d=None, confidential_share_status="unavailable")), conf)
    assert gone.status == "NOT_SUPPORTED"
    # Legacy snapshots without the status field: a numeric share is graded as measured, by value.
    legacy = _claim_by_prefix(_card(snap, with_volume(confidential_share_30d=0.02, confidential_share_status=None)), conf)
    assert legacy.status == "NOT_SUPPORTED"


def test_scorecard_solver_grade_uses_measurement_status_and_ci():
    snap = _committed_snapshot()
    base = snap.intents_forensics
    solver = "Solver concentration on intents.near"

    def with_solvers(**upd):
        f = base.model_copy(deep=True)
        f.solver_concentration = {**(f.solver_concentration or {}), **upd}
        return f

    ok = _claim_by_prefix(_card(snap, with_solvers(hhi_solver=5761.0, n_eff_solver=1.74, n_fills=32, n_fills_attributed=34,
                                                   measurement_status="measured", hhi_solver_ci90=[4521.0, 7285.0],
                                                   n_fills_atomic=2, n_fills_hub_legs=30)), solver)
    assert ok.status == "VERIFIED_LIVE_API" and "90% CI 4,521-7,285" in ok.value and "entirely above" in ok.value
    small = _claim_by_prefix(_card(snap, with_solvers(hhi_solver=3000.0, n_fills=12, n_fills_attributed=14, measurement_status="measured",
                                                      hhi_solver_ci90=[2400.0, 3900.0])), solver)
    assert small.status == "DERIVED" and "straddles" in small.value
    thin = _claim_by_prefix(_card(snap, with_solvers(hhi_solver=6250.0, n_fills=4, n_fills_attributed=4, measurement_status="thin")), solver)
    assert thin.status == "NOT_SUPPORTED" and thin.value.startswith("not measured")
    none = _claim_by_prefix(_card(snap, with_solvers(hhi_solver=None, n_fills=0, n_fills_attributed=0, measurement_status="not_measured")), solver)
    assert none.status == "NOT_SUPPORTED"


def test_scorecard_other_claims_never_verify_a_zero():
    snap = _committed_snapshot()
    f = snap.intents_forensics.model_copy(deep=True)
    f.ai_agent_share = 0.0
    f.confidential_tvl_usd = 0.0
    card = _card(snap, f)
    assert _claim_by_prefix(card, "Deposit/caller concentration").status == "NOT_SUPPORTED"
    assert _claim_by_prefix(card, "Confidential TVL backs").status == "NOT_SUPPORTED"
    s2 = snap.model_copy(deep=True)
    s2.sotp.calibration = {**(s2.sotp.calibration or {}), "alpha_capture": 0.0}
    assert _claim_by_prefix(_card(s2), "Buyback capture alpha").status == "NOT_SUPPORTED"


# ----------------------------------------------------------------------------- derived views (market_implied / sensitivity / relative_value)
def test_attach_derived_models_populates_keys_and_records_timings():
    snap = _committed_snapshot().model_copy(deep=True)
    timings: dict[str, float] = {}
    warnings = rp.attach_derived_models(snap, timings)
    assert warnings == []
    assert set(timings) == {"market_implied", "sensitivity", "relative_value"}
    assert snap.market_implied["solves"] and snap.sensitivity["rows"] and snap.relative_value["coverage"]
    dumped = rp.sanitize_json(snap.model_dump(mode="json"))
    assert isinstance(dumped["market_implied"]["headline"], str)


def test_attach_derived_models_failure_nulls_the_key_and_warns(monkeypatch: pytest.MonkeyPatch):
    snap = _committed_snapshot().model_copy(deep=True)

    def boom(_snapshot):
        raise ValueError("synthetic failure")

    monkeypatch.setattr(rp, "DERIVED_MODELS", (("market_implied", boom), *rp.DERIVED_MODELS[1:]))
    warnings = rp.attach_derived_models(snap, {})
    assert snap.market_implied is None and snap.sensitivity is not None
    assert len(warnings) == 1 and "market_implied failed (ValueError: synthetic failure)" in warnings[0]
    assert warnings[0] in snap.warnings


# ----------------------------------------------------------------------------- IC memo: reframed thesis first, conditional wording
def _memo_snapshot() -> Snapshot:
    snap = _committed_snapshot().model_copy(deep=True)
    rp.attach_derived_models(snap, {})
    return snap


def test_memo_leads_with_model_vs_market_and_market_implied_sections():
    from valuo.memo_generator import SEC, render_memo

    memo = render_memo(_memo_snapshot(), None)
    order = [f"## {SEC['summary']}. Executive summary", f"## {SEC['market']}. What the market is pricing",
             f"## {SEC['believe']}. What you have to believe", f"## {SEC['relval']}. Relative value",
             f"## {SEC['bear']}. Bear case", f"## {SEC['score']}. Evidence scorecard", f"## {SEC['provenance']}. Data provenance"]
    pos = [memo.index(h) for h in order]
    assert pos == sorted(pos)
    summary = memo[pos[0]:pos[1]]
    assert "**Model value vs market value.**" in summary and "**Conclusion.**" in summary and "Evidence quality flags" in summary
    assert summary.index("Model value vs market value") < summary.index("What the market is pricing") < summary.index("Conclusion")
    for word in ("revolutionize", "delve", "seamless", "unlocking"):
        assert word not in memo.lower()


def test_memo_conclusion_follows_the_sign_of_the_gap():
    from valuo.memo_generator import _conclusion

    snap = _memo_snapshot()
    mi = dict(snap.market_implied)
    above = _conclusion(snap, {**mi, "gap_multiple": 0.8})
    assert "at or above the market FDV" in above
    if mi["gap_multiple"] > 1:
        assert "at or above" not in _conclusion(snap, mi)


def test_memo_survives_null_derived_models():
    from valuo.memo_generator import render_memo, render_readme_findings

    snap = _committed_snapshot().model_copy(deep=True)
    snap.market_implied = snap.sensitivity = snap.relative_value = None
    memo = render_memo(snap, None)
    assert "market_implied is null" in memo and "`sensitivity` is null" in memo and "`relative_value` is null" in memo
    assert "market_implied null this run" in render_readme_findings(snap, None)
