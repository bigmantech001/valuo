"""Foundation tests: provenance hashing/ledger, fetch semantics, schema contract, assumptions registry."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from valuo import __version__, assumptions, config
from valuo.provenance import (
    EMPTY_SHA256,
    ProvenanceLedger,
    RawRecord,
    fetch_json,
    fetch_json_sync,
    is_gc_block_error,
    near_rpc_call,
    near_rpc_call_sync,
    rpc_error_message,
    sha256_bytes,
    sha256_json,
    utc_now_iso,
    write_raw,
)
from valuo.schemas import (
    SCHEMA_VERSION,
    Assumption,
    BearCase,
    BearScenario,
    CallerClass,
    CallerShare,
    ContractSinkSnapshot,
    Corridor,
    CorridorClipResult,
    EngineValue,
    EpochIssuanceMeasurement,
    EvidenceClaim,
    ExecutionBenchmark,
    IntentsForensics,
    Manifest,
    NearOnchainTruth,
    PeerComp,
    PeerComps,
    Regime,
    Snapshot,
    SotpValuation,
    SupplyPhysics,
    SupplyTrajectory,
    VenueQuote,
)

SHA_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
MANDATED_KEYS = {
    "svrn_target_inflation", "svrn_glidepath_months", "public_volume_growth_yoy", "confidential_share_target",
    "confidential_take_bps", "fee_compression_lambda_monthly", "confidential_compression_divisor", "discount_rate",
    "terminal_multiple_floor", "terminal_multiple_cap", "confidential_multiple_haircut", "kb_per_agent_vault",
    "state_lock_growth_fallback_near_per_day", "buyback_capture_ratio_override", "near_price_drift_annual",
}


def _raw_file(record: RawRecord) -> Path:
    assert record.raw_path is not None
    p = Path(record.raw_path)
    return p if p.is_absolute() else config.REPO_ROOT / p


def _record(**overrides) -> RawRecord:
    base = dict(
        source="near_rpc", name="block_final", url=config.NEAR_RPC_URL, method="POST", ok=True, http_status=200,
        fetched_at_utc=utc_now_iso(), latency_ms=12.5, bytes=3, sha256=SHA_ABC,
    )
    base.update(overrides)
    return RawRecord(**base)


# ----------------------------------------------------------------------------- hashing / records
def test_sha256_of_known_bytes():
    assert sha256_bytes(b"abc") == SHA_ABC
    assert sha256_bytes(b"") == EMPTY_SHA256
    # canonical JSON hash is key-order independent
    assert sha256_json({"b": 1, "a": [1, 2]}) == sha256_json({"a": [1, 2], "b": 1})


def test_raw_record_holds_sha256_and_defaults():
    rec = _record()
    assert rec.sha256 == SHA_ABC and len(rec.sha256) == 64
    assert rec.raw_path is None and rec.request_body_sha256 is None and rec.attempts == 1
    assert rec.fetched_at_utc.endswith("Z") and "T" in rec.fetched_at_utc


def test_write_raw_persists_exact_bytes(tmp_path: Path):
    path = write_raw(b"abc", source="oneclick", name="quote:eth_usdc->sol_usdc:50000", raw_dir=tmp_path)
    file = Path(path)
    assert file.is_absolute()  # tmp_path is outside the repo, so the path is absolute
    assert file.name == "oneclick__quote_eth_usdc-_sol_usdc_50000.json"
    assert file.read_bytes() == b"abc" and sha256_bytes(file.read_bytes()) == SHA_ABC


def test_ledger_summary_counts_sources_and_failures(ledger: ProvenanceLedger):
    ledger.add(_record())
    ledger.add(_record(name="protocol_config"))
    ledger.add(_record(source="oneclick", name="quote:x", ok=False, http_status=400, error="HTTP 400: No liquidity available"))
    ledger.warn("execution_bench: 1Click returned no liquidity at $250K")
    ledger.warn("execution_bench: 1Click returned no liquidity at $250K")  # de-duplicated
    s = ledger.summary()
    assert s["records"] == 3 and s["ok"] == 2 and s["failures"] == 1 and s["bytes"] == 9
    assert s["sources"] == {"near_rpc": 2, "oneclick": 1}
    assert s["failed"] == ["oneclick/quote:x: HTTP 400: No liquidity available"]
    assert s["warnings"] == ["execution_bench: 1Click returned no liquidity at $250K"]
    assert ledger.get("near_rpc", "protocol_config") is not None and ledger.get("relay", "nope") is None
    assert [r.name for r in ledger.by_source("near_rpc")] == ["block_final", "protocol_config"]


# ----------------------------------------------------------------------------- fetch semantics (mock transport)
def _run(coro):
    return asyncio.run(coro)


def test_fetch_json_non_2xx_body_is_returned_hashed_and_recorded(ledger: ProvenanceLedger):
    body = {"message": "No liquidity available", "correlationId": "abc", "path": "/v0/quote"}
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert json.loads(request.content)["dry"] is True
        return httpx.Response(400, json=body)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_json(
                client, ledger, source="oneclick", name="quote:test:250000", method="POST",
                url="https://1click.chaindefuser.com/v0/quote", json={"dry": True}, retries=3, backoff=0,
            )

    parsed, rec = _run(go())
    assert calls["n"] == 1  # 4xx other than 429 is never retried
    assert parsed == body
    assert rec.ok is False and rec.http_status == 400
    assert rec.error == "HTTP 400: No liquidity available"
    assert rec.request_body_sha256 == sha256_json({"dry": True})
    raw = _raw_file(rec).read_bytes()
    assert sha256_bytes(raw) == rec.sha256 and len(raw) == rec.bytes and json.loads(raw) == body
    assert ledger.records == [rec]


def test_fetch_json_retries_on_429_then_succeeds(ledger: ProvenanceLedger):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"message": "rate limited"}, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"coins": {"coingecko:near": {"price": 4.31}}})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_json(
                client, ledger, source="defillama", name="prices", method="GET",
                url="https://coins.llama.fi/prices/current/coingecko:near", retries=2, backoff=0,
            )

    parsed, rec = _run(go())
    assert calls["n"] == 2 and rec.attempts == 2 and rec.ok is True
    assert parsed["coins"]["coingecko:near"]["price"] == 4.31
    assert rec.url.endswith("/prices/current/coingecko:near")


def test_fetch_json_sync_transport_error_records_failure(ledger: ProvenanceLedger):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("boom", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        parsed, rec = fetch_json_sync(
            ledger, source="nearstats", name="summary", method="GET", url="https://nearstats.org/api/near/summary",
            retries=1, backoff=0, client=client,
        )
    assert parsed is None and rec.ok is False and rec.http_status is None
    assert rec.attempts == 2 and rec.bytes == 0 and rec.sha256 == EMPTY_SHA256 and rec.raw_path is None
    assert rec.error is not None and "ConnectTimeout" in rec.error


def test_fetch_json_params_are_captured_in_url_and_non_json_is_flagged(ledger: ProvenanceLedger):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="<html>Internal Server Error</html>")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        parsed, rec = fetch_json_sync(
            ledger, source="nearstats", name="price_history:90d", method="GET",
            url="https://nearstats.org/api/near/price-history", params={"window": "90d"}, retries=0, client=client,
        )
    assert parsed is None and rec.ok is False and rec.http_status == 500
    assert rec.url == "https://nearstats.org/api/near/price-history?window=90d"
    assert rec.error == "HTTP 500: non-JSON body"
    assert _raw_file(rec).suffix == ".txt"


# ----------------------------------------------------------------------------- NEAR RPC routing
GC_ERROR = {
    "jsonrpc": "2.0", "id": "valuo",
    "error": {
        "name": "HANDLER_ERROR",
        "cause": {"info": {"block_height": 221000000}, "name": "GARBAGE_COLLECTED_BLOCK"},
        "code": -32000, "message": "Server error",
        "data": "The data for block #221000000 is garbage collected on this node, use an archival node to fetch historical data",
    },
}


def test_rpc_error_helpers(load_fixture):
    assert is_gc_block_error(GC_ERROR)
    assert rpc_error_message(GC_ERROR).startswith("GARBAGE_COLLECTED_BLOCK: The data for block #221000000")
    ok_payload = load_fixture("hist_archival.json")
    assert rpc_error_message(ok_payload) is None and not is_gc_block_error(ok_payload)
    assert rpc_error_message({"result": {"error": "account x does not exist", "logs": []}}) == "account x does not exist"
    assert not is_gc_block_error({"error": {"cause": {"name": "UNKNOWN_ACCOUNT"}, "data": "account x does not exist"}})


def test_near_rpc_call_falls_through_to_archival_on_gc_block(ledger: ProvenanceLedger, load_fixture):
    archival_body = load_fixture("hist_archival.json")
    hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        body = json.loads(request.content)
        assert body["method"] == "query" and body["params"]["block_id"] == 221000000
        if request.url.host.startswith("archival"):
            return httpx.Response(200, json=archival_body)
        return httpx.Response(200, json=GC_ERROR)

    params = {"request_type": "view_account", "block_id": 221000000, "account_id": "intents.near"}

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await near_rpc_call(client, ledger, "query", params, "view_account:intents.near@221000000", retries=0)

    result, rec = _run(go())
    assert hosts[0] == httpx.URL(config.NEAR_RPC_URL).host and hosts[-1] == httpx.URL(config.NEAR_ARCHIVAL_RPC_URL).host
    assert result["storage_usage"] == 12888180967 and result["block_height"] == 221000000
    assert rec.ok is True and rec.source == "near_rpc_archival" and rec.url == config.NEAR_ARCHIVAL_RPC_URL
    assert rec.note is not None and "GARBAGE_COLLECTED_BLOCK" in rec.note
    assert len(ledger.records) == 1  # only the final exchange is in the manifest
    raw = _raw_file(rec).read_bytes()
    assert sha256_bytes(raw) == rec.sha256 and json.loads(raw) == archival_body


def test_near_rpc_call_sync_returns_result_and_errors(ledger: ProvenanceLedger, load_fixture):
    block = load_fixture("rpc_block.json")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "block":
            return httpx.Response(200, json=block)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": "valuo", "error": {"name": "HANDLER_ERROR", "cause": {"name": "UNKNOWN_ACCOUNT"}, "code": -32000, "message": "Server error", "data": "account nope.near does not exist while viewing"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result, rec = near_rpc_call_sync(ledger, "block", {"finality": "final"}, "block_final", retries=0, client=client)
        assert rec.ok and rec.source == "near_rpc" and result["header"]["height"] == block["result"]["header"]["height"]
        assert int(result["header"]["total_supply"]) > 10**33
        missing, rec2 = near_rpc_call_sync(ledger, "query", {"request_type": "view_account", "finality": "final", "account_id": "nope.near"}, "view_account:nope", retries=0, client=client)
        assert missing is None and rec2.ok is False and rec2.error.startswith("UNKNOWN_ACCOUNT")
        assert rec2.note is None  # deterministic RPC errors do not trigger fallback
    assert len(ledger.records) == 2


# ----------------------------------------------------------------------------- schema contract
def _minimal_assumption(key: str = "discount_rate") -> Assumption:
    return Assumption(key=key, value=0.25, unit="ratio_annual", low=0.1, high=0.4, source="assumption", justification="test")


def _minimal_truth() -> NearOnchainTruth:
    return NearOnchainTruth(
        block_height=222342342, block_hash="H", timestamp_ns=1793404458274822088, timestamp_utc="2026-10-30T23:54:18.274Z",
        total_supply_near=1.31e9, gas_price_yocto=100000000, max_inflation_rate=0.025, protocol_reward_rate=0.0,
        storage_amount_per_byte_yocto=10**19, storage_near_per_kb=0.01, num_blocks_per_year=31536000, epoch_length_blocks=43200,
        protocol_version=86, active_validator_count=379, total_staked_near=5.93e8, staked_supply_ratio=0.4527,
        nominal_staking_apr_current=0.0552, nominal_staking_apr_svrn_1_6=0.0353, gross_daily_issuance_near=89654.0,
        gross_daily_issuance_svrn_near=57378.0,
        epoch_issuance=EpochIssuanceMeasurement(epoch_start_height=222321137, epoch_start_hash="E", nominal_annual_issuance_near=3.27e7, method_note="test"),
        tracked_sinks=[ContractSinkSnapshot(account_id="intents.near", label="Defuse clearinghouse", has_contract=True, storage_bytes=13135343202, storage_locked_near=131353.4, liquid_balance_near=676.6, total_balance_near=132030.0, staked_near=0.0)],
        total_state_locked_near=131353.4, rpc_endpoint_used=config.NEAR_RPC_URL, archival_available=True,
    )


def test_schemas_instantiate_from_minimal_dicts():
    q = VenueQuote.model_validate({"venue": "across", "supported": False, "status": "unsupported_route", "amount_in_raw": "50000000000", "latency_ms": 310.2, "fetched_at_utc": utc_now_iso(), "raw_record_sha256": SHA_ABC, "error_message": "ROUTE_NOT_ENABLED: Route is not enabled."})
    assert q.amount_out_usd is None and q.fee_breakdown_usd == {}
    clip = CorridorClipResult(corridor_id="eth_usdc_sol_usdc", clip_usd=50000, quotes=[q])
    assert clip.n_venues_ok == 0 and clip.headroom_bps is None
    corridor = Corridor(corridor_id="eth_usdc_sol_usdc", label="ETH USDC -> SOL USDC", archetype="cross_vm", origin={"chain": "eth"}, destination={"chain": "sol"}, venues_attempted=["1click", "relay", "lifi", "across"])
    bench = ExecutionBenchmark(ran_at_utc=utc_now_iso(), clips_usd=[500, 50000, 250000], corridors=[corridor], results=[clip])
    assert bench.oneclick_1y_token_universe is None and bench.competitive_fee_ceiling_bps is None
    share = CallerShare(account_id="escrow.ai.near", cls="ai_agent", receipts=4, share=0.5)
    assert share.cls is CallerClass.ai_agent
    assert EpochIssuanceMeasurement(epoch_start_height=1, epoch_start_hash="x", nominal_annual_issuance_near=1.0, method_note="n").minted_per_epoch_near is None
    assert PeerComp(slug="solana", symbol="SOL").fdv_to_revenue is None
    assert EvidenceClaim(claim="c", status="DERIVED", value="v", source="s", confidence="high").note == ""


def test_open_models_keep_extra_fields_and_snapshot_roundtrips():
    truth = _minimal_truth()
    forensics = IntentsForensics(
        volume={"30d": 3.893e9}, fees={"gross_take_bps": 15.8}, price={"current_usd": 4.31}, volatility={"window": "1y"},
        callers=[CallerShare(account_id="escrow.ai.near", cls=CallerClass.ai_agent, receipts=4, share=1.0)],
        hhi_external=10000.0, n_eff_external=1.0, hhi_all=10000.0, ai_agent_share=1.0, bridge_share=0.0,
        method_mix={"execute_intents": 4}, receipts_sampled=4, pages_fetched=1, sample_block_range=[1, 2],
        extra_metric=42,  # extra field must survive
    )
    assert forensics.model_dump()["extra_metric"] == 42
    near = PeerComp(slug="near", symbol="NEAR", fdv_usd=5.636e9)
    comps = PeerComps(peers=[near, PeerComp(slug="solana", symbol="SOL")], near_combined=near, fetched_at_utc=utc_now_iso())
    a = _minimal_assumption()
    supply = SupplyPhysics(
        inputs={a.key: a}, regimes=[Regime(key="status_quo", label="2.5% flat", inflation_path_annual=[0.025] * 36)],
        trajectories=[SupplyTrajectory(regime="status_quo", months=[1], gross_issuance_cum=[1.0], buyback_cum=[0.5], gas_burn_cum=[0.0], state_lock_cum=[0.0], net_float_change_cum=[0.5], daily_issuance_start=1.0, daily_issuance_end=1.0)],
        breakeven_daily_volume_usd={"status_quo": 1e9}, current_daily_sinks_near={"buyback": 1.0, "gas_burn": 0.0, "state_lock": 0.0, "total": 1.0},
        current_daily_issuance_near=2.0, sink_coverage_ratio=0.5,
    )
    pct = {k: float(i) for i, k in enumerate(("p10", "p25", "p50", "p75", "p90"))}
    sotp = SotpValuation(
        seed=config.SEED, n_paths=10, horizon_months=36, discount_rate=0.25, inputs={a.key: a},
        engines=[EngineValue(key="clearinghouse", label="E1", method="dcf", assumption_heavy=False, **pct)],
        fdv_percentiles=pct, price_percentiles=pct, fdv_ex_monetary_percentiles=pct, current_fdv_usd=5.6e9, upside_p50_pct=0.0,
        fan_chart={"p50": [0.0] * 36}, crossover_month_distribution={"svrn_glidepath": {"p_crossover_within_36m": 0.0}},
        sensitivity_heatmap={"x": [1e8], "y": [2], "fdv_p50": [[1.0]], "net_deflation": [[False]]},
    )
    bear = BearCase(
        base_fdv_p50=2.0, combined_worst_fdv=1.0, combined_drawdown_pct=-0.5, falsification_summary="s",
        scenarios=[BearScenario(key="fee_race_to_zero", title="t", narrative="n", perturbations={"tau_pub_bps": 0.01}, sotp_fdv_p50=1.0, drawdown_pct=-0.5, price_p50=1.0, early_warning_metric="net_take_bps", trigger_threshold=3.0, trigger_breached=False, monitor_source="defillama")],
    )
    snap = Snapshot(
        generated_at_utc=utc_now_iso(), seed=config.SEED, runtime_s=1.0, valuo_version=__version__, near_rpc=truth,
        execution_bench=None, intents_forensics=forensics, comps=comps, supply_physics=supply, sotp=sotp, bear_case=bear,
        assumptions=[a], warnings=["execution_bench skipped"],
    )
    assert snap.schema_version == SCHEMA_VERSION
    dumped = snap.model_dump_json()
    again = Snapshot.model_validate_json(dumped)
    assert again == snap
    assert json.loads(dumped)["intents_forensics"]["callers"][0]["cls"] == "ai_agent"
    manifest = Manifest(generated_at_utc=snap.generated_at_utc, block_height=truth.block_height, block_hash=truth.block_hash, snapshot_sha256=sha256_bytes(dumped.encode()), snapshot_path="artifacts/latest_snapshot.json", records=[_record()], sources={"near_rpc": 1}, failures=0)
    assert Manifest.model_validate_json(manifest.model_dump_json()) == manifest


# ----------------------------------------------------------------------------- assumptions registry
def test_assumption_ranges_contain_defaults_and_mandated_keys_exist():
    assert MANDATED_KEYS <= set(assumptions.keys())
    for a in assumptions.as_list():
        assert a.low <= a.value <= a.high, a.key
        assert a.source == "assumption" and len(a.justification) > 20, a.key
    assert assumptions.get("svrn_target_inflation").value == pytest.approx(0.016)
    assert assumptions.get("buyback_capture_ratio_override").value == -1.0
    assert assumptions.get("state_lock_growth_fallback_near_per_day").value == 0.0
    assert assumptions.value("discount_rate") == pytest.approx(0.25)


def test_with_overrides_validates_and_labels():
    reg = assumptions.with_overrides({"discount_rate": 0.30, "svrn_glidepath_months": 12})
    assert reg["discount_rate"].value == 0.30 and "override: 0.25 -> 0.3" in reg["discount_rate"].justification
    assert reg["svrn_glidepath_months"].value == 12
    assert assumptions.ASSUMPTIONS["discount_rate"].value == 0.25  # registry itself untouched
    assert assumptions.value("discount_rate", reg) == 0.30 and assumptions.value("terminal_multiple_cap", reg) == 60
    with pytest.raises(KeyError):
        assumptions.with_overrides({"not_a_key": 1.0})
    with pytest.raises(ValueError):
        assumptions.with_overrides({"discount_rate": 0.9})
    assert assumptions.with_overrides({"discount_rate": 0.9}, clamp=True)["discount_rate"].value == 0.40
    for name in assumptions.SCENARIO_PRESETS:
        assert len(assumptions.preset(name)) == len(assumptions.ASSUMPTIONS)


# ----------------------------------------------------------------------------- fixtures sanity
def test_fixtures_parse_and_trimmed_shapes(probes_dir: Path, load_fixture):
    files = sorted(p.name for p in probes_dir.glob("*.json"))
    assert len(files) >= 48
    for name in files:
        json.loads((probes_dir / name).read_bytes())
    v = load_fixture("rpc_validators_trimmed.json")["result"]
    assert set(v) == {"epoch_height", "epoch_start_height", "current_validators"} and len(v["current_validators"]) == 5
    assert int(v["current_validators"][0]["stake"]) > 0
    for name in ("llama_fees_near_intents.json", "llama_rev_near_intents.json", "llama_dexs_near_intents.json", "llama_fees_hyperliquid.json"):
        j = load_fixture(name)
        assert len(j["totalDataChart"]) == 60 and "totalDataChartBreakdown" not in j and j["total30d"] > 0
    p2 = load_fixture("nearblocks_txns_p2.json")
    assert isinstance(p2["txns"], list) and len(p2["txns"]) == 25
    assert load_fixture("oneclick_250k.json")["message"] == "No liquidity available"
    assert load_fixture("across_eth_sol.json")["code"] == "ROUTE_NOT_ENABLED"
    assert load_fixture("relay_eth_btc.json")["errorCode"] == "INVALID_INPUT_CURRENCY"
