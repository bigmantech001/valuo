"""Chain Signatures (v1.signer) audit: window parsing, rate/trend math, null safety, claim grading (offline).

``nearblocks_v1_signer_txns.json`` is a recorded NearBlocks ``/v1/account/v1.signer/txns?per_page=25`` page
(2026-11-10, long ``args`` strings trimmed); ``nearblocks_v1_signer_count.json`` is the recorded ``txns/count``
body. They test parsing only; nothing here is shown to users.
"""
from __future__ import annotations

import asyncio
import copy
import json
import math
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from valuo import config
from valuo import reproduce as rp
from valuo.collectors import chain_signatures as cs_mod
from valuo.memo_generator import _chain_signatures_paragraph
from valuo.provenance import ProvenanceLedger

DAY_NS = 86_400 * 10 ** 9
HEAD_NS = int(datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc).timestamp()) * 10 ** 9


@pytest.fixture
def page(load_fixture) -> dict[str, Any]:
    return load_fixture("nearblocks_v1_signer_txns.json")


def _rows(n: int, n_sign: int, newest_ns: int, gap_s: float, *, caller: str = "omni.bridge.near", burnt: int = 10 ** 21) -> list[dict[str, Any]]:
    """Synthetic receipts shaped like the live page: newest first, ``n_sign`` sign actions, the rest respond."""
    out = []
    for i in range(n):
        method = "sign" if i < n_sign else "respond"
        out.append({
            "receipt_id": f"r{newest_ns}-{i}", "predecessor_account_id": caller if method == "sign" else "mpc-node.near",
            "receiver_account_id": "v1.signer", "block_timestamp": str(newest_ns - int(i * gap_s * 1e9)),
            "receipt_outcome": {"tokens_burnt": burnt, "status": True},
            "actions": [{"action": "FUNCTION_CALL", "method": method, "deposit": 1 if method == "sign" else 0}],
        })
    return out


def _window(kind: str, newest_ns: int, sign_per_day: float, **extra: Any) -> dict[str, Any]:
    # 101 receipts, 1 s apart -> receipt rate 86,400/day; sign share chosen to hit sign_per_day.
    n = 101
    n_sign = round(sign_per_day / 86400 * n)
    w = cs_mod.summarize_window(_rows(n, n_sign, newest_ns, 1.0))
    assert w is not None
    w.update({"kind": kind, **extra})
    return w


# ----------------------------------------------------------------------------- parsing
def test_summarize_window_parses_the_recorded_page(page):
    w = cs_mod.summarize_window(page["txns"])
    assert w is not None
    assert w["n_receipts"] == 25 and w["n_sign"] == 8 and w["n_sign_success"] == 8 and w["n_respond"] == 9
    assert w["method_mix"]["sign"] == 8 and w["method_mix"]["(no actions)"] == 1
    assert w["span_s"] == pytest.approx(26.991330843, abs=1e-6)
    assert w["sign_per_day"] == pytest.approx(24 / 26.991330843 * 8 / 25 * 86400, rel=1e-9)
    assert w["deposits_yocto"] == [1] * 8
    assert w["callers"] == {"omni.bridge.near": 2, "fast-auth.near": 2, "zcash-connector.bridge.near": 2,
                            "kernel-zec.meteor-vaults.near": 1, "kernel-usdc.meteor-vaults.near": 1}
    # receipt_outcome null (first row) counts as zero gas, never as a crash
    assert w["gas_burnt_near"] == pytest.approx(12894241739969100000000 / 1e24)


def test_summarize_window_dedupes_and_is_null_safe(page):
    rows = page["txns"]
    assert cs_mod.summarize_window(rows + copy.deepcopy(rows))["n_receipts"] == 25
    assert cs_mod.summarize_window(None) is None
    assert cs_mod.summarize_window({"txns": rows}) is None
    assert cs_mod.summarize_window(rows[:1]) is None
    assert cs_mod.summarize_window([{"receipt_id": "a"}, {"receipt_id": "b", "block_timestamp": "x"}]) is None
    same = [{**rows[1], "receipt_id": "a"}, {**rows[1], "receipt_id": "b"}]  # zero span -> no rate
    w = cs_mod.summarize_window(same)
    assert w is not None and w["sign_per_day"] is None and w["receipts_per_day"] is None


def test_count_fixture_shape(load_fixture):
    body = load_fixture("nearblocks_v1_signer_count.json")
    assert int(body["txns"][0]["count"]) == 26_391_885


# ----------------------------------------------------------------------------- math
def test_log_linear_trend_recovers_exponential_growth():
    g = 0.002  # ln-rate per day
    pts = [(-d, 1000 * math.exp(-g * d)) for d in (0, 4, 8, 12, 16, 20)]
    t = cs_mod.log_linear_trend(pts)
    assert t is not None and t["slope_ln_per_day"] == pytest.approx(g)
    assert t["growth_30d"] == pytest.approx(math.exp(30 * g) - 1)
    assert cs_mod._growth_status(t) == "growing"  # zero residual: sign of the slope decides
    noisy = [(-d, r * f) for (d, r), f in zip([(d, 1000.0) for d in (0, 4, 8, 12, 16, 20)], (1.3, 0.7, 1.2, 0.8, 1.25, 0.75))]
    tn = cs_mod.log_linear_trend([(-d, r) for d, r in noisy])
    assert tn is not None and abs(tn["t_stat"]) < 2 and cs_mod._growth_status(tn) == "inconclusive"
    assert tn["growth_30d_ci90"][0] < tn["growth_30d"] < tn["growth_30d_ci90"][1]
    assert cs_mod.log_linear_trend([(0, 1.0), (-1, 2.0)]) is None
    assert cs_mod.log_linear_trend([(0, 0.0), (-1, -1.0), (-2, None)]) is None  # type: ignore[list-item]


def test_caller_shares_hhi_bounds():
    one = cs_mod.caller_shares({"a": 10})
    assert one["hhi"] == pytest.approx(10_000) and one["top"][0]["share"] == 1.0
    even = cs_mod.caller_shares({"a": 5, "b": 5, "c": 5, "d": 5})
    assert even["hhi"] == pytest.approx(2_500)
    assert cs_mod.caller_shares({})["hhi"] is None and cs_mod.caller_shares({})["bridge_share"] is None
    mixed = cs_mod.caller_shares({"omni.bridge.near": 4, "btc-connector.bridge.near": 2, "fast-auth.near": 3, "bridge.near.evil": 1})
    assert mixed["bridge_share"] == pytest.approx(0.6)


def test_sample_plan_shape():
    plan = cs_mod.sample_plan(HEAD_NS)
    level = [p for p in plan if p["kind"] == "level"]
    mid = [p for p in plan if p["kind"] == "midnight"]
    assert [p["offset_h"] for p in level] == [21.0, 63.0, 105.0, 147.0]
    assert {p["offset_h"] % 24 for p in level} == {21.0, 15.0, 9.0, 3.0}  # four different times of day
    assert [p["before_date"] for p in mid] == ["2026-11-10", "2026-11-06", "2026-11-02", "2026-10-29", "2026-10-25", "2026-10-21", "2026-10-17", "2026-10-13"]


def test_aggregate_strata_weights_and_trend_uses_midnight_series_only():
    rate_recent, rate_old = 20_000.0, 10_000.0
    wins = [_window("level", HEAD_NS - int(d * DAY_NS), rate_recent) for d in (1, 2.5, 4, 6)]
    wins += [_window("midnight", HEAD_NS - int(d * DAY_NS), rate_recent if d < 7 else rate_old) for d in (0.5, 4.5)]
    wins += [_window("midnight", HEAD_NS - int(d * DAY_NS), rate_old) for d in (8.5, 12.5, 16.5, 20.5, 24.5, 28.5)]
    agg = cs_mod.aggregate_windows(wins, head_ns=HEAD_NS)
    r7, r_old = agg["sign_per_day_7d"], agg["sign_per_day_7_30d"]
    assert agg["windows_7d"] == 6 and agg["windows_7_30d"] == 6 and agg["windows_ok"] == 12
    assert r7 == pytest.approx(rate_recent, rel=0.03) and r_old == pytest.approx(rate_old, rel=0.03)
    assert agg["sign_per_day_30d"] == pytest.approx(7 / 30 * r7 + 23 / 30 * r_old)
    assert agg["trend_windows"] == 8 and agg["trend"]["growth_30d"] > 0
    assert agg["callers"]["top"][0]["account_id"] == "omni.bridge.near" and agg["callers"]["hhi"] == pytest.approx(10_000)
    assert agg["deposit_yocto_median"] == 1.0 and agg["deposit_near_mean"] == pytest.approx(1e-24)
    # gas: every receipt burns 1e21 yocto = 0.001 NEAR; per sign = 0.001 x receipts / signs
    assert agg["gas_near_per_sign"] == pytest.approx(0.001 * agg["receipts_sampled"] / agg["sign_receipts_sampled"])
    assert agg["gas_near_per_day_30d"] == pytest.approx(0.001 * 86400)  # 1 receipt/s x 0.001 NEAR


def test_aggregate_null_safety():
    empty = cs_mod.aggregate_windows([], head_ns=HEAD_NS)
    assert empty["windows_ok"] == 0 and empty["sign_per_day_7d"] is None and empty["sign_per_day_30d"] is None
    assert empty["trend"] is None and empty["growth_status"] == "not_measured" and empty["gas_near_per_sign"] is None
    only_recent = cs_mod.aggregate_windows([_window("level", HEAD_NS - DAY_NS, 5000.0)], head_ns=HEAD_NS)
    assert only_recent["sign_per_day_7d"] is not None and only_recent["sign_per_day_7d_se"] is None
    assert only_recent["sign_per_day_30d"] is None  # one stratum missing -> no 30d figure, never a partial one


def test_attach_context_prices_and_handles_nulls():
    class Sink:
        storage_bytes, storage_locked_near, growth_locked_near_per_day, state_block_height = 1_164_178, 11.64178, None, 223_000_000

    cs = {"deposit_near_mean": 1e-24, "sign_per_day_30d": 10_000.0, "gas_near_per_sign": 0.002, "gas_near_per_day_30d": 20.0}
    out = cs_mod.attach_context(dict(cs), storage_sink=Sink(), near_price_usd=3.5)
    assert out["gas_usd_per_sign"] == pytest.approx(0.007) and out["gas_usd_per_day_30d"] == pytest.approx(70.0)
    assert out["storage"]["storage_locked_near"] == 11.64178 and out["storage_locked_usd"] == pytest.approx(11.64178 * 3.5)
    assert out["deposit_near_per_day_30d"] == pytest.approx(1e-20)
    bare = cs_mod.attach_context({}, storage_sink=None, near_price_usd=None)
    assert bare["storage"] is None and bare["gas_usd_per_day_30d"] is None and bare["deposit_near_per_day_30d"] is None
    assert any("storage" in m for m in bare["not_measured"])
    assert cs_mod.attach_context(None) is None
    assert cs_mod.attach_context({"gas_near_per_sign": 1.0}, near_price_usd=float("nan"))["gas_usd_per_sign"] is None


# ----------------------------------------------------------------------------- collector against a mock transport
def _mock_handler(page: dict[str, Any], count: dict[str, Any], *, nearblocks_ok: bool = True):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "nearblocks" in url:
            if not nearblocks_ok:
                return httpx.Response(429, json={"message": "You have exceeded your API request limit."})
            if url.split("?")[0].endswith("/count"):
                return httpx.Response(200, json=count)
            params = dict(request.url.params)
            if "before_date" in params:
                newest = int(datetime.fromisoformat(params["before_date"]).replace(tzinfo=timezone.utc).timestamp()) * 10 ** 9 - 10 ** 9
            else:
                newest = HEAD_NS - (223_900_000 - int(params["before_block"])) * 500_000_000
            shift = newest - max(int(r["block_timestamp"]) for r in page["txns"])
            rows = [{**r, "block_timestamp": str(int(r["block_timestamp"]) + shift)} for r in page["txns"]]
            return httpx.Response(200, json={"cursor": "1", "txns": rows})
        body = json.loads(request.content)
        if body["method"] == "block":
            p = body["params"]
            h = 223_900_000 if "finality" in p else int(p["block_id"])
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body.get("id"), "result": {"header": {"height": h, "timestamp_nanosec": str(HEAD_NS - (223_900_000 - h) * 500_000_000)}}})
        if body["method"] == "EXPERIMENTAL_protocol_config":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body.get("id"), "result": {"runtime_config": {"transaction_costs": {"burnt_gas_reward": [0, 1]}}}})
        return httpx.Response(404, json={})
    return handler


def _run(handler, tmp_path) -> tuple[dict[str, Any], list[str], ProvenanceLedger]:
    ledger = ProvenanceLedger(raw_dir=tmp_path / "raw")
    warnings: list[str] = []

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await cs_mod.collect_chain_signatures(client, ledger, warnings, delay_s=0)

    return asyncio.run(go()), warnings, ledger


def test_collector_end_to_end_on_mock_transport(page, load_fixture, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "NEARBLOCKS_API_KEY", None)
    out, warnings, ledger = _run(_mock_handler(page, load_fixture("nearblocks_v1_signer_count.json")), tmp_path)
    assert out["status"] == "measured" and out["cumulative_receipts"] == 26_391_885 and out["burnt_gas_reward"] == 0.0
    assert out["seconds_per_block"] == pytest.approx(0.5) and out["windows_ok"] == 12
    assert out["sign_per_day_7d"] is not None and out["sign_per_day_30d"] is not None and out["trend_windows"] == 8
    assert out["growth_status"] in {"growing", "declining", "inconclusive"}
    assert "fee_note" in out and "1 yoctoNEAR" in out["fee_note"]
    assert all("deposits_yocto" not in w and "callers" not in w for w in out["windows"])
    names = {r.name for r in ledger.by_source("nearblocks")}
    assert "txns:v1.signer:count" in names and "txns:v1.signer:before_date:2026-11-10" in names
    assert any(n.startswith("txns:v1.signer:before_block:") for n in names)
    assert warnings == []
    json.dumps(out, allow_nan=False)  # snapshot-safe


def test_collector_failure_is_warning_and_nulls(page, load_fixture, tmp_path, monkeypatch):
    monkeypatch.setattr(cs_mod, "_RETRY_KW", {"retries": 0})
    real_sleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda *_a, **_k: real_sleep(0))  # skip RPC/HTTP backoff waits
    out, warnings, _ = _run(_mock_handler(page, load_fixture("nearblocks_v1_signer_count.json"), nearblocks_ok=False), tmp_path)
    assert out["status"] == "unavailable" and out["cumulative_receipts"] is None and out["sign_per_day_30d"] is None
    assert any("txns/count unavailable" in w for w in warnings) and any("sample windows failed" in w for w in warnings)

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    out2, warnings2, _ = _run(broken, tmp_path)
    assert out2["windows_ok"] == 0
    assert out2["status"] in {"unavailable", "count_only"} and out2["sign_per_day_7d"] is None and out2["trend"] is None and warnings2
    assert set(cs_mod.aggregate_windows([], head_ns=0)) <= set(out2)  # stable shape: every rate key present, null


# ----------------------------------------------------------------------------- scorecard claim + memo
def _cs(**upd: Any) -> dict[str, Any]:
    base = {
        "status": "measured", "sign_per_day_7d": 20_000.0, "sign_per_day_30d": 15_000.0, "windows_ok": 12, "receipts_sampled": 1200,
        "trend": {"n": 8, "slope_ln_per_day": 0.01, "slope_se": 0.003, "t_stat": 3.3, "growth_30d": 0.35, "growth_30d_ci90": [0.1, 0.6]},
        "growth_status": "growing", "callers": {"n_sign_sampled": 380, "n_callers": 9, "hhi": 2700.0,
                                                "top": [{"account_id": "omni.bridge.near", "sign_receipts": 150, "share": 150 / 380}]},
        "gas_near_per_sign": 0.0022, "storage": {"storage_locked_near": 11.6}, "fee_note": "fee note", "cumulative_receipts": 26_391_885,
    }
    base.update(upd)
    return base


def test_claim_grades_follow_the_measurement():
    assert rp.chain_signatures_claim(_cs()).status == "DERIVED"
    flat = rp.chain_signatures_claim(_cs(growth_status="inconclusive", trend={"n": 8, "slope_ln_per_day": 0.001, "t_stat": 0.4, "growth_30d": 0.03}))
    assert flat.status == "NOT_SUPPORTED" and "inconclusive" in flat.value
    down = rp.chain_signatures_claim(_cs(growth_status="declining", trend={"n": 8, "slope_ln_per_day": -0.02, "t_stat": -3.0, "growth_30d": -0.45}))
    assert down.status == "NOT_SUPPORTED"
    count_only = rp.chain_signatures_claim({"status": "count_only", "cumulative_receipts": 26_391_885})
    assert count_only.status == "VERIFIED_LIVE_API" and "growth not measured" in count_only.value
    nothing = rp.chain_signatures_claim({"status": "unavailable", "cumulative_receipts": None, "not_measured": ["x"]})
    assert nothing.status == "NOT_SUPPORTED"
    assert rp.chain_signatures_claim(_cs(cumulative_receipts=0, trend=None, sign_per_day_30d=None)).status == "NOT_SUPPORTED"


def test_scorecard_appends_claim_only_when_given():
    from tests.test_reproduce import _committed_snapshot  # same committed-snapshot loader the scorecard tests use

    snap = _committed_snapshot()
    args = (snap.near_rpc, snap.execution_bench, snap.intents_forensics, snap.supply_physics, snap.sotp, snap.comps, None)
    without = rp.build_evidence_scorecard(*args)
    with_cs = rp.build_evidence_scorecard(*args, chain_signatures=_cs())
    assert len(with_cs) == len(without) + 1 and with_cs[-1].claim == rp.CHAIN_SIGNATURES_CLAIM


def test_memo_paragraph_null_safe():
    from tests.test_reproduce import _committed_snapshot

    snap = _committed_snapshot()
    assert _chain_signatures_paragraph(snap) is None or isinstance(_chain_signatures_paragraph(snap), str)
    s2 = snap.model_copy(deep=True)
    s2.chain_signatures = _cs(deposit_yocto_median=1.0, gas_near_per_day_30d=30.0, burnt_gas_reward=0.0)  # type: ignore[attr-defined]
    par = _chain_signatures_paragraph(s2)
    assert par is not None and "20,000 sign requests/day" in par and "omni.bridge.near" in par and "n/a" not in par.split("NearBlocks counts")[0][:40]
    s2.chain_signatures = {"status": "unavailable", "not_measured": ["sign rate / trend: no sample window returned"]}  # type: ignore[attr-defined]
    assert "not measured" in _chain_signatures_paragraph(s2)


def test_sampling_budget_stops_the_loop(page, load_fixture, tmp_path):
    ledger = ProvenanceLedger(raw_dir=tmp_path / "raw")
    warnings: list[str] = []

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler(page, load_fixture("nearblocks_v1_signer_count.json")))) as client:
            return await cs_mod.collect_chain_signatures(client, ledger, warnings, delay_s=0, budget_s=-1)

    out = asyncio.run(go())
    assert out["windows_ok"] == 0 and out["status"] == "count_only" and any("sampling budget" in w for w in warnings)


def test_interleaved_order_covers_both_strata_early():
    plan = cs_mod.interleaved(cs_mod.sample_plan(HEAD_NS))
    assert len(plan) == 12 and {id(p) for p in plan} == {id(p) for p in plan}
    first4 = plan[:4]
    # today's midnight, a 7-day level anchor, the oldest midnight (days 7-30 stratum), another level anchor
    assert [p["kind"] for p in first4] == ["midnight", "level", "midnight", "level"]
    assert first4[0]["before_date"] == "2026-11-10" and first4[2]["before_date"] == "2026-10-13"
    assert sorted(p.get("before_date", "") for p in plan if p["kind"] == "midnight") == sorted(
        p["before_date"] for p in cs_mod.sample_plan(HEAD_NS) if p["kind"] == "midnight")


def test_retry_pass_recovers_rate_limited_windows(page, load_fixture, tmp_path, monkeypatch):
    """Windows that exhaust the 429 ladder in pass 1 are fetched again in pass 2 and counted."""
    monkeypatch.setattr(cs_mod, "_RETRY_KW", {"retries": 0})
    base = _mock_handler(page, load_fixture("nearblocks_v1_signer_count.json"))
    seen: dict[str, int] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "nearblocks" in url and not url.split("?")[0].endswith("/count"):
            seen[url] = seen.get(url, 0) + 1
            if seen[url] == 1 and len(seen) % 3 == 0:  # every third window is refused once
                return httpx.Response(429, json={"message": "You have exceeded your API request limit."})
        return base(request)

    out, warnings, ledger = _run(handler, tmp_path)
    assert out["windows_ok"] == 12 and out["windows_planned"] == 12
    names = [r.name for r in ledger.by_source("nearblocks")]
    assert len(names) == len(set(names)) and sum(n.endswith(":retry") for n in names) == 4
    assert out["sign_per_day_30d"] is not None and out["trend_windows"] == 8
    assert any("retry pass recovered 4 of 4" in w for w in warnings)
    assert not any("sample windows failed" in w for w in warnings)
    newest = [w["newest_ns"] for w in out["windows"]]
    assert newest == sorted(newest, reverse=True)
