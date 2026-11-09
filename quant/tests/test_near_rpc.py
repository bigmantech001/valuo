"""Unit tests for valuo.collectors.near_rpc: parsing and derivations on recorded RPC fixtures.

Only the ``live`` test touches the network. Synthetic inputs appear exclusively here (tests/), never in
the collector itself.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from valuo import assumptions
from valuo.collectors import near_rpc as nr
from valuo.schemas import EpochIssuanceMeasurement, NearOnchainTruth

# Fixture anchors (recorded 2026-10-30, FACTS section 1).
EPOCH_START = 222_321_137
PREV_EPOCH_START = 222_277_937
STORAGE_PER_BYTE = 10**19


@pytest.fixture(scope="module")
def blocks(load_fixture) -> dict[int, nr.BlockHeader]:
    heights = (222_321_137, 222_321_136, 222_277_937, 222_277_936)
    return {h: nr.parse_block(load_fixture(f"block_{h}.json")["result"]) for h in heights}


@pytest.fixture(scope="module")
def head(load_fixture) -> nr.BlockHeader:
    return nr.parse_block(load_fixture("rpc_block.json")["result"])


@pytest.fixture(scope="module")
def proto(load_fixture) -> nr.ProtocolParams:
    return nr.parse_protocol_config(load_fixture("rpc_protocol.json")["result"])


@pytest.fixture(scope="module")
def validators(load_fixture) -> nr.ValidatorSet:
    return nr.parse_validators(load_fixture("rpc_validators_trimmed.json")["result"])


@pytest.fixture(scope="module")
def accounts(load_fixture) -> dict[str, nr.AccountState]:
    files = {
        "intents.near": "rpc_intents_acct.json",
        "aurora": "rpc_aurora.json",
        "wrap.near": "rpc_wrap.json",
        "v1.signer": "rpc_v1signer.json",
        "escrow.ai.near": "rpc_escrow_acct.json",
    }
    return {acct: nr.parse_view_account(load_fixture(name)["result"], acct) for acct, name in files.items()}


# ----------------------------------------------------------------------------- conversions
def test_yocto_to_near_parses_exact_integer_strings():
    assert nr.yocto_to_near("1310395407206600716000010989007608") == pytest.approx(1_310_395_407.2066, rel=1e-12)
    assert nr.yocto_to_near(10**24) == 1.0
    assert nr.yocto_to_near("0") == 0.0


def test_ratio_and_zero_denominator():
    assert nr.ratio([1, 40]) == 0.025
    assert nr.ratio([0, 1]) == 0.0
    with pytest.raises(ValueError):
        nr.ratio([1, 0])


def test_ns_to_iso_millisecond_precision():
    assert nr.ns_to_iso(1_793_404_334_217_061_424) == "2026-10-30T23:52:14.217Z"
    assert nr.ns_to_iso(0) == "1970-01-01T00:00:00.000Z"


def test_storage_lock_formula_matches_facts():
    # 13,135,343,202 bytes x 1e19 yocto/byte / 1e24 = 131,353.43202 NEAR
    assert nr.storage_locked_near(13_135_343_202, STORAGE_PER_BYTE) == pytest.approx(131_353.43202, rel=1e-12)
    assert nr.storage_locked_near(428, STORAGE_PER_BYTE) == pytest.approx(0.00428)
    assert nr.storage_near_per_kb(STORAGE_PER_BYTE) == pytest.approx(0.01)  # 1 NEAR per 100 KB


def test_has_contract_uses_empty_code_hash_sentinel():
    assert nr.has_contract("BtA1BEFNS619KkvXFsgcpQ21Tb5yMm32aaUkn7xNothk")
    assert not nr.has_contract(nr.NO_CONTRACT_CODE_HASH)
    assert not nr.has_contract("")


# ----------------------------------------------------------------------------- parsing
def test_parse_block_header(head: nr.BlockHeader):
    assert head.height == 222_342_342
    assert head.hash == "BKRbswmairy3R8HnWvyf4dQxhrajJEKCF2fLZCpF2nKq"
    assert head.timestamp_ns == 1_793_404_334_217_061_424
    assert head.total_supply_yocto == 1310395407206600716000010989007608
    assert head.gas_price_yocto == 100_000_000
    assert head.epoch_id == "BfxavRFDycJeNG9uZupEhjudjtS9A7NLSWRUichwvUHA"


def test_parse_protocol_config(proto: nr.ProtocolParams):
    assert proto.max_inflation_rate == 0.025
    assert proto.protocol_reward_rate == 0.0  # live: [0, 1], treasury receives nothing
    assert proto.storage_amount_per_byte_yocto == STORAGE_PER_BYTE
    assert proto.num_blocks_per_year == 31_536_000
    assert proto.epoch_length_blocks == 43_200
    assert proto.protocol_version == 86
    assert proto.protocol_treasury_account == "treasury.near"


def test_parse_validators_trimmed(validators: nr.ValidatorSet):
    assert validators.active_validator_count == 5
    assert validators.epoch_start_height == EPOCH_START
    assert validators.epoch_height == 4919
    expected = (
        33242171889781239591123631431857 + 27868334333741972378736104717204 + 22894523951345142193984258432898
        + 21198220785419565469398044850345 + 20119721684346676036809674805792
    )
    assert validators.total_staked_yocto == expected
    assert nr.yocto_to_near(expected) == pytest.approx(125_322_972.6446, rel=1e-9)


def test_parse_view_account_and_sink_snapshot(accounts: dict[str, nr.AccountState]):
    intents = accounts["intents.near"]
    assert intents.storage_usage == 13_135_343_202
    assert intents.block_height == 222_342_342
    snap = nr.sink_snapshot(intents, STORAGE_PER_BYTE, "label")
    assert snap.has_contract is True
    assert snap.storage_locked_near == pytest.approx(131_353.43202)
    assert snap.total_balance_near == pytest.approx(132_029.5698, rel=1e-8)
    assert snap.liquid_balance_near == pytest.approx(132_029.5698 - 131_353.43202, rel=1e-6)
    assert snap.staked_near == 0.0
    escrow = nr.sink_snapshot(accounts["escrow.ai.near"], STORAGE_PER_BYTE, "escrow")
    assert escrow.has_contract is False
    assert escrow.storage_bytes == 428


# ----------------------------------------------------------------------------- epoch issuance
def test_epoch_jump_matches_recorded_boundaries(blocks):
    cur = nr.epoch_jump_near(blocks[EPOCH_START], blocks[EPOCH_START - 1])
    prev = nr.epoch_jump_near(blocks[PREV_EPOCH_START], blocks[PREV_EPOCH_START - 1])
    assert cur == pytest.approx(26_483.40, abs=0.01)
    assert prev == pytest.approx(26_160.56, abs=0.01)


def test_is_epoch_first_block_and_candidate_classification(blocks):
    cur_start, cur_pred = blocks[EPOCH_START], blocks[EPOCH_START - 1]
    prev_start, prev_pred = blocks[PREV_EPOCH_START], blocks[PREV_EPOCH_START - 1]
    assert nr.is_epoch_first_block(cur_start, cur_pred)
    assert nr.is_epoch_first_block(prev_start, prev_pred)
    # The previous epoch's id is the epoch_id of the block just before the current start.
    assert nr.classify_candidate(prev_start, prev_pred, cur_pred.epoch_id, cur_start.epoch_id) == "found"
    # A block inside the previous epoch (same epoch_id as its parent) -> walk back.
    inside = replace(prev_start, height=prev_start.height + 5, epoch_id=cur_pred.epoch_id)
    inside_pred = replace(prev_pred, hash=inside.prev_hash, epoch_id=cur_pred.epoch_id)
    assert nr.classify_candidate(inside, inside_pred, cur_pred.epoch_id, cur_start.epoch_id) == "too_late"
    # A block in the current epoch -> also walk back; a block two epochs back -> step forward.
    assert nr.classify_candidate(cur_start, cur_pred, cur_pred.epoch_id, cur_start.epoch_id) == "too_late"
    assert nr.classify_candidate(prev_pred, prev_pred, cur_pred.epoch_id, cur_start.epoch_id) == "too_early"


def test_measure_epoch_issuance_from_two_boundaries(blocks, head: nr.BlockHeader):
    total_supply = nr.yocto_to_near(head.total_supply_yocto)
    m = nr.measure_epoch_issuance(
        cur_start=blocks[EPOCH_START], cur_pred=blocks[EPOCH_START - 1],
        prev_start=blocks[PREV_EPOCH_START], prev_pred=blocks[PREV_EPOCH_START - 1],
        total_supply_near=total_supply, max_inflation_rate=0.025,
    )
    assert isinstance(m, EpochIssuanceMeasurement)
    assert m.epoch_start_height == EPOCH_START and m.prev_epoch_start_height == PREV_EPOCH_START
    assert m.minted_per_epoch_near == pytest.approx(26_483.40, abs=0.01)
    assert m.epoch_duration_hours == pytest.approx(7.1244, abs=1e-3)
    assert m.epochs_per_year == pytest.approx(8766.0 / m.epoch_duration_hours)
    assert m.net_burn_per_epoch_near == pytest.approx(-296.96, abs=0.01)
    assert m.implied_annual_issuance_near == pytest.approx(m.minted_per_epoch_near * m.epochs_per_year)
    assert 0.0240 < m.implied_annual_inflation_rate < 0.0255
    assert m.nominal_annual_issuance_near == pytest.approx(0.025 * total_supply)
    assert m.implied_annual_issuance_near < m.nominal_annual_issuance_near  # uptime-adjusted payout
    assert m.prev_minted_per_epoch_near == pytest.approx(26_160.56, abs=0.01)
    assert 0.5 < m.avg_block_time_s < 0.7
    assert len(m.jumps) == 2


def test_measure_epoch_issuance_degrades_to_null_without_boundaries(blocks, head):
    m = nr.measure_epoch_issuance(
        cur_start=blocks[EPOCH_START], cur_pred=None, prev_start=None, prev_pred=None,
        total_supply_near=nr.yocto_to_near(head.total_supply_yocto), max_inflation_rate=0.025,
    )
    assert m.minted_per_epoch_near is None and m.epoch_duration_hours is None
    assert m.implied_annual_issuance_near is None and m.implied_annual_inflation_rate is None
    assert m.nominal_annual_issuance_near > 3.2e7


# ----------------------------------------------------------------------------- storage growth
def test_fit_growth_exact_on_linear_points():
    slope, window = nr.fit_growth_bytes_per_day([(-30.0, 1_000), (-7.0, 1_000 + 23 * 50), (0.0, 1_000 + 30 * 50)])
    assert slope == pytest.approx(50.0)
    assert window == pytest.approx(30.0)
    assert nr.fit_growth_bytes_per_day([(0.0, 5)]) == (None, None)
    assert nr.fit_growth_bytes_per_day([(0.0, 5), (0.0, 9)]) == (None, None)
    two, w2 = nr.fit_growth_bytes_per_day([(-10.0, 100), (0.0, 300)])
    assert two == pytest.approx(20.0) and w2 == pytest.approx(10.0)


def test_apply_growth_from_archival_points(load_fixture, accounts, head):
    # Recorded intents.near state at three heights; ages derived from the measured ~0.571 s block time.
    hist1 = load_fixture("hist_archival.json")["result"]   # block 215,000,000
    hist2 = load_fixture("hist_archival2.json")["result"]  # block 221,000,000
    block_time_s = 0.571
    now = accounts["intents.near"]

    def point(res):
        age_days = (head.height - res["block_height"]) * block_time_s / 86400.0
        return {"block_height": res["block_height"], "timestamp_utc": "", "storage_bytes": res["storage_usage"], "days_before_now": age_days}

    history = [point(hist2), point(hist1), {"block_height": now.block_height, "timestamp_utc": nr.ns_to_iso(head.timestamp_ns), "storage_bytes": now.storage_usage, "days_before_now": 0.0}]
    sink = nr.sink_snapshot(now, STORAGE_PER_BYTE, "intents")
    grown = nr.apply_growth(sink, history, STORAGE_PER_BYTE)
    assert [h["block_height"] for h in grown.history] == [215_000_000, 221_000_000, now.block_height]
    assert 20e6 < grown.growth_bytes_per_day < 40e6  # FACTS: ~28-30 MB/day
    assert grown.growth_locked_near_per_day == pytest.approx(grown.growth_bytes_per_day / 1e5)
    assert grown.growth_window_days == pytest.approx((head.height - 215_000_000) * block_time_s / 86400.0)
    untouched = nr.apply_growth(sink, [history[-1]], STORAGE_PER_BYTE)
    assert untouched.growth_bytes_per_day is None and untouched.growth_locked_near_per_day is None


# ----------------------------------------------------------------------------- derived / assembly
def test_staking_apr_and_daily_issuance():
    assert nr.staking_apr(0.025, 0.0, 0.4527) == pytest.approx(0.025 / 0.4527)
    assert nr.staking_apr(0.025, 0.10, 0.5) == pytest.approx(0.045)
    with pytest.raises(ValueError):
        nr.staking_apr(0.025, 0.0, 0.0)
    assert nr.daily_issuance_near(1.3e9, 0.025) == pytest.approx(1.3e9 * 0.025 / 365.25)


def test_assemble_truth_derivations(head, proto, validators, accounts, blocks):
    total_supply = nr.yocto_to_near(head.total_supply_yocto)
    labels = dict(nr.TRACKED_SINKS)
    sinks = [nr.sink_snapshot(state, proto.storage_amount_per_byte_yocto, labels[a]) for a, state in accounts.items()]
    sinks[0] = nr.apply_growth(
        sinks[0],
        [
            {"block_height": 221_000_000, "timestamp_utc": "", "storage_bytes": 12_888_180_967, "days_before_now": 8.0},
            {"block_height": head.height, "timestamp_utc": "", "storage_bytes": 13_135_343_202, "days_before_now": 0.0},
        ],
        proto.storage_amount_per_byte_yocto,
    )
    issuance = nr.measure_epoch_issuance(
        cur_start=blocks[EPOCH_START], cur_pred=blocks[EPOCH_START - 1], prev_start=blocks[PREV_EPOCH_START],
        prev_pred=blocks[PREV_EPOCH_START - 1], total_supply_near=total_supply, max_inflation_rate=proto.max_inflation_rate,
    )
    svrn = assumptions.value("svrn_target_inflation")
    truth = nr.assemble_truth(
        head=head, proto=proto, validators=validators, sinks=sinks, epoch_issuance=issuance,
        rpc_endpoint_used="https://free.rpc.fastnear.com", archival_available=True, archival_attempted=True,
        warnings=["w"], missing_accounts=[], svrn_target_inflation=svrn,
    )
    assert isinstance(truth, NearOnchainTruth)
    assert truth.total_supply_near == pytest.approx(total_supply)
    assert truth.staked_supply_ratio == pytest.approx(nr.yocto_to_near(validators.total_staked_yocto) / total_supply)
    assert truth.nominal_staking_apr_current == pytest.approx(0.025 * (1 - 0.0) / truth.staked_supply_ratio)
    assert truth.nominal_staking_apr_svrn_1_6 == pytest.approx(svrn / truth.staked_supply_ratio)
    assert truth.gross_daily_issuance_near == pytest.approx(total_supply * 0.025 / 365.25)
    assert truth.gross_daily_issuance_svrn_near == pytest.approx(total_supply * svrn / 365.25)
    assert truth.storage_near_per_kb == pytest.approx(0.01)
    assert truth.total_state_locked_near == pytest.approx(sum(s.storage_locked_near for s in sinks))
    assert truth.total_state_locked_near > 275_000  # intents.near + aurora alone exceed 274k NEAR
    assert truth.measured_state_lock_growth_near_per_day == pytest.approx(sinks[0].growth_locked_near_per_day)
    assert truth.measured_daily_issuance_near == pytest.approx(issuance.implied_annual_issuance_near / 365.25)
    assert truth.timestamp_utc == "2026-10-30T23:52:14.217Z"
    assert truth.warnings == ["w"] and truth.archival_attempted is True
    # Round-trip through JSON keeps the extras and nested models.
    dumped = truth.model_dump(mode="json")
    assert dumped["epoch_issuance"]["minted_per_epoch_near"] == pytest.approx(26_483.40, abs=0.01)
    assert NearOnchainTruth.model_validate(dumped).tracked_sinks[0].growth_bytes_per_day == pytest.approx(sinks[0].growth_bytes_per_day)


def test_assemble_truth_growth_null_when_unmeasured(head, proto, validators, accounts, blocks):
    sinks = [nr.sink_snapshot(accounts["intents.near"], proto.storage_amount_per_byte_yocto, "x")]
    issuance = nr.measure_epoch_issuance(
        cur_start=blocks[EPOCH_START], cur_pred=None, prev_start=None, prev_pred=None,
        total_supply_near=nr.yocto_to_near(head.total_supply_yocto), max_inflation_rate=0.025,
    )
    truth = nr.assemble_truth(
        head=head, proto=proto, validators=validators, sinks=sinks, epoch_issuance=issuance,
        rpc_endpoint_used="u", archival_available=False, archival_attempted=False,
        warnings=[], missing_accounts=["meme-cooking.near"], svrn_target_inflation=0.016,
    )
    assert truth.measured_state_lock_growth_near_per_day is None
    assert truth.measured_daily_issuance_near is None
    assert truth.missing_accounts == ["meme-cooking.near"]


# ----------------------------------------------------------------------------- async search logic (offline)
class _FakeRpc:
    """Serves recorded block headers by height or hash; unknown ids return (None, record-like)."""

    def __init__(self, blocks: dict[int, nr.BlockHeader], skipped: set[int] = frozenset()):
        self.by_height = {h: b for h, b in blocks.items() if h not in skipped}
        self.by_hash = {b.hash: b for b in self.by_height.values()}
        self.calls: list[str] = []

    async def call(self, method: str, params, name: str):
        self.calls.append(name)
        block_id = params["block_id"]
        block = self.by_hash.get(block_id) if isinstance(block_id, str) else self.by_height.get(block_id)
        if block is None:
            return None, _rec(name, ok=False, error="UNKNOWN_BLOCK: DB Not Found Error")
        result = {"header": {
            "height": block.height, "hash": block.hash, "prev_hash": block.prev_hash, "epoch_id": block.epoch_id,
            "next_epoch_id": block.next_epoch_id, "timestamp": block.timestamp_ns, "timestamp_nanosec": str(block.timestamp_ns),
            "total_supply": str(block.total_supply_yocto), "gas_price": str(block.gas_price_yocto),
        }}
        return result, _rec(name)


def _rec(name: str, *, ok: bool = True, error: str | None = None):
    from valuo.schemas import RawRecord

    return RawRecord(source="near_rpc", name=name, url="fake", method="POST", ok=ok, error=error, fetched_at_utc="t",
                     latency_ms=0.0, bytes=0, sha256="0" * 64)


def test_find_prev_epoch_start_direct_hit(blocks):
    fake = _FakeRpc(blocks)
    warnings: list[str] = []
    prev_start, prev_pred = asyncio.run(
        nr._find_prev_epoch_start(fake, blocks[EPOCH_START], blocks[EPOCH_START - 1], 43_200, warnings)
    )
    assert prev_start is blocks[PREV_EPOCH_START] or prev_start.height == PREV_EPOCH_START
    assert prev_pred.height == PREV_EPOCH_START - 1
    assert warnings == []
    assert fake.calls == [f"block:{PREV_EPOCH_START}", f"block:pred_of:{PREV_EPOCH_START}"]


def test_find_prev_epoch_start_walks_back_when_inside_epoch(blocks):
    # Pretend the epoch is one block longer: the first candidate lands inside the previous epoch and the
    # search must follow prev_hash back to the true first block.
    inside = replace(blocks[PREV_EPOCH_START], height=PREV_EPOCH_START + 1, hash="INSIDE", prev_hash=blocks[PREV_EPOCH_START].hash,
                     timestamp_ns=blocks[PREV_EPOCH_START].timestamp_ns + 600_000_000)
    extended = dict(blocks)
    extended[PREV_EPOCH_START + 1] = inside
    fake = _FakeRpc(extended)
    warnings: list[str] = []
    prev_start, prev_pred = asyncio.run(
        nr._find_prev_epoch_start(fake, blocks[EPOCH_START], blocks[EPOCH_START - 1], 43_199, warnings)
    )
    assert prev_start.height == PREV_EPOCH_START and prev_pred.height == PREV_EPOCH_START - 1
    assert warnings == []


def test_find_prev_epoch_start_steps_over_skipped_base_height(blocks):
    # The height epoch_start - epoch_length was skipped; the true first block sits one height lower and
    # its parent (two epochs back) is only reachable by hash.
    pred = replace(blocks[PREV_EPOCH_START - 1], height=PREV_EPOCH_START - 2, hash="PRED_HASH")
    true_start = replace(blocks[PREV_EPOCH_START], height=PREV_EPOCH_START - 1, hash="TRUE_START", prev_hash="PRED_HASH")
    fake = _FakeRpc({
        EPOCH_START: blocks[EPOCH_START], EPOCH_START - 1: blocks[EPOCH_START - 1],
        PREV_EPOCH_START - 1: true_start, PREV_EPOCH_START - 2: pred,
    })
    warnings: list[str] = []
    prev_start, prev_pred = asyncio.run(
        nr._find_prev_epoch_start(fake, blocks[EPOCH_START], blocks[EPOCH_START - 1], 43_200, warnings)
    )
    assert prev_start.hash == "TRUE_START" and prev_pred.hash == "PRED_HASH"
    assert warnings == []
    assert fake.calls == [f"block:{PREV_EPOCH_START}", f"block:{PREV_EPOCH_START - 1}", f"block:pred_of:{PREV_EPOCH_START - 1}"]


def test_find_prev_epoch_start_gives_up_with_warning(blocks):
    # A previous-epoch id that matches nothing makes every candidate "too_early"; the bounded forward
    # walk over missing heights must end with a single warning and null boundaries.
    fake = _FakeRpc(blocks)
    wrong_pred = replace(blocks[EPOCH_START - 1], epoch_id="NO_SUCH_EPOCH")
    warnings: list[str] = []
    prev_start, prev_pred = asyncio.run(
        nr._find_prev_epoch_start(fake, blocks[EPOCH_START], wrong_pred, 43_200, warnings)
    )
    assert prev_start is None and prev_pred is None
    assert len(warnings) == 1 and "previous epoch start not found" in warnings[0]
    assert len(fake.calls) <= 2 * nr.EPOCH_SEARCH_STEPS


def test_find_prev_epoch_start_aborts_when_parent_unreachable(blocks):
    fake = _FakeRpc(blocks, skipped={PREV_EPOCH_START})  # 222277936's parent is not in the fixtures
    warnings: list[str] = []
    prev_start, prev_pred = asyncio.run(
        nr._find_prev_epoch_start(fake, blocks[EPOCH_START], blocks[EPOCH_START - 1], 43_200, warnings)
    )
    assert prev_start is None and prev_pred is None
    assert len(warnings) == 1 and "epoch search aborted" in warnings[0]


def test_fetch_block_near_height_steps_over_skipped_heights(blocks):
    fake = _FakeRpc(blocks, skipped={PREV_EPOCH_START})
    found = asyncio.run(nr._fetch_block_near_height(fake, PREV_EPOCH_START))
    assert found.height == PREV_EPOCH_START - 1  # nearest produced neighbour
    assert asyncio.run(nr._fetch_block_near_height(fake, 1)) is None


# ----------------------------------------------------------------------------- live
@pytest.mark.live
def test_live_collector_ground_truth(ledger):
    truth = nr.collect_near_rpc(ledger)
    assert truth.total_supply_near > 1_000_000_000
    assert 0 < truth.max_inflation_rate <= 0.05
    assert 0.25 < truth.staked_supply_ratio < 0.80
    assert truth.active_validator_count > 100
    intents = next(s for s in truth.tracked_sinks if s.account_id == "intents.near")
    assert intents.storage_locked_near > 50_000
    assert intents.has_contract
    ei = truth.epoch_issuance
    assert ei.minted_per_epoch_near is not None and 10_000 < ei.minted_per_epoch_near < 60_000
    assert ei.epoch_duration_hours is not None and 4 < ei.epoch_duration_hours < 14
    assert ei.implied_annual_inflation_rate is not None and 0.015 < ei.implied_annual_inflation_rate < 0.03
    assert len(ledger.by_source("near_rpc")) >= 10
    assert all(len(r.sha256) == 64 for r in ledger.records)
    if truth.archival_available:
        assert intents.growth_bytes_per_day is not None and intents.growth_bytes_per_day > 0
        assert truth.measured_state_lock_growth_near_per_day is not None
