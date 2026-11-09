"""Unit tests for valuo.models.supply_physics: accounting identities, regime paths, crossover detection.

All inputs here are synthetic (allowed only inside tests); the module itself never fabricates values.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from valuo import assumptions, config
from valuo.models.supply_physics import (
    DAYS_PER_MONTH,
    DAYS_PER_YEAR,
    REGIME_CUSTOM_CAP,
    REGIME_STATUS_QUO,
    REGIME_SVRN_GLIDEPATH,
    agent_scale_rows,
    breakeven_daily_volume_usd,
    daily_issuance_near,
    daily_sinks_near,
    inflation_path,
    net_float_change_near_day,
    run_supply_physics,
    staking_yield_rows,
    trajectory,
)
from valuo.schemas import (
    ContractSinkSnapshot,
    EpochIssuanceMeasurement,
    IntentsForensics,
    NearOnchainTruth,
    PeerComp,
    PeerComps,
    SupplyPhysics,
)

SUPPLY = 1.3104e9
PRICE = 4.31
VOL30 = 3.893483161e9
GROSS30 = 6_159_085.0
HOLDERS30 = 2_175_899.0
MINTED = 26_483.4
EPOCHS_PER_YEAR = 1230.3


def _truth(*, measured: bool = True, burn: float | None = -297.0, lock: float | None = 290.0) -> NearOnchainTruth:
    ep = EpochIssuanceMeasurement(
        epoch_start_height=222321137, epoch_start_hash="E", prev_epoch_start_height=222277937,
        minted_per_epoch_near=MINTED if measured else None, epoch_duration_hours=7.12 if measured else None,
        epochs_per_year=EPOCHS_PER_YEAR if (measured or burn is not None) else None,
        net_burn_per_epoch_near=burn,
        implied_annual_issuance_near=MINTED * EPOCHS_PER_YEAR if measured else None,
        implied_annual_inflation_rate=MINTED * EPOCHS_PER_YEAR / SUPPLY if measured else None,
        nominal_annual_issuance_near=SUPPLY * 0.025, method_note="synthetic",
    )
    return NearOnchainTruth(
        block_height=222342342, block_hash="H", timestamp_ns=1793404458274822088, timestamp_utc="2026-10-30T23:54:18.274Z",
        total_supply_near=SUPPLY, gas_price_yocto=100000000, max_inflation_rate=0.025, protocol_reward_rate=0.0,
        storage_amount_per_byte_yocto=10**19, storage_near_per_kb=0.01, num_blocks_per_year=31536000, epoch_length_blocks=43200,
        protocol_version=86, active_validator_count=379, total_staked_near=0.4527 * SUPPLY, staked_supply_ratio=0.4527,
        nominal_staking_apr_current=0.025 / 0.4527, nominal_staking_apr_svrn_1_6=0.016 / 0.4527,
        gross_daily_issuance_near=SUPPLY * 0.025 / DAYS_PER_YEAR, gross_daily_issuance_svrn_near=SUPPLY * 0.016 / DAYS_PER_YEAR,
        epoch_issuance=ep,
        tracked_sinks=[ContractSinkSnapshot(
            account_id="intents.near", label="Defuse clearinghouse", has_contract=True, storage_bytes=13135343202,
            storage_locked_near=131353.4, liquid_balance_near=676.6, total_balance_near=132030.0, staked_near=0.0,
            growth_bytes_per_day=29e6 if lock is not None else None, growth_locked_near_per_day=lock, growth_window_days=30.0 if lock is not None else None,
        )],
        total_state_locked_near=131353.4, measured_state_lock_growth_near_per_day=lock,
        rpc_endpoint_used=config.NEAR_RPC_URL, archival_available=lock is not None,
    )


def _forensics(*, price: float | None = PRICE, fees: dict | None = None) -> IntentsForensics:
    return IntentsForensics(
        volume={"30d": VOL30, "public30d": 2.357e9, "confidential30d": 1.536e9},
        fees={"gross_fees_30d_usd": GROSS30, "net_revenue_30d_usd": HOLDERS30, "holders_revenue_30d_usd": HOLDERS30,
              "volume_30d_usd": VOL30, "take_rate_window": "fixture 30 complete days", "take_rate_window_days": 30,
              "gross_take_bps": GROSS30 / VOL30 * 1e4, "capture_ratio": HOLDERS30 / GROSS30} if fees is None else fees,
        price={"current_usd": price}, volatility={"window": "1y"},
        callers=[], hhi_external=2500.0, n_eff_external=4.0, hhi_all=3000.0, ai_agent_share=0.1, bridge_share=0.2,
        receipts_sampled=100, pages_fetched=4,
    )


def _comps(*, near_revenue_30d: float | None = 141_650.0, near_price: float | None = PRICE, in_peers: bool = False) -> PeerComps:
    """Mirror collectors/comps.py: the NEAR L1 gas row lives in the extra ``near_components`` list, not ``peers``."""
    near_chain = PeerComp(slug="near", symbol="NEAR", revenue_30d_usd=near_revenue_30d, price_usd=near_price, fdv_usd=5.636e9)
    combined = PeerComp(slug="near_combined", symbol="NEAR", price_usd=near_price, fdv_usd=5.636e9)
    peers = [PeerComp(slug="solana", symbol="SOL")] + ([near_chain] if in_peers else [])
    return PeerComps(
        peers=peers, near_combined=combined, fetched_at_utc="2026-10-31T00:00:00Z",
        near_components=[] if in_peers else [near_chain, PeerComp(slug="near-intents", symbol="NEAR")],
    )


def _run(**kw) -> SupplyPhysics:
    truth = kw.pop("truth", _truth())
    forensics = kw.pop("forensics", _forensics())
    comps = kw.pop("comps", _comps())
    reg = kw.pop("registry", assumptions.with_overrides(None))
    return run_supply_physics(truth, forensics, comps, reg, **kw)


# ----------------------------------------------------------------------------- pure helpers
def test_daily_issuance_times_year_equals_annual():
    assert daily_issuance_near(SUPPLY, 0.025) * DAYS_PER_YEAR == pytest.approx(SUPPLY * 0.025, rel=1e-12)
    assert DAYS_PER_MONTH * 12 == pytest.approx(DAYS_PER_YEAR)


def test_glidepath_endpoints_and_monotonicity():
    path = inflation_path(REGIME_SVRN_GLIDEPATH, 36, 0.025, 0.016, 24)
    assert len(path) == 36
    assert path[0] == pytest.approx(0.025)
    assert path[24] == pytest.approx(0.016) and path[-1] == pytest.approx(0.016)
    assert path[23] == pytest.approx(0.025 + (0.016 - 0.025) * 23 / 24)
    assert all(a >= b for a, b in zip(path, path[1:]))
    assert all(x == pytest.approx(0.016) for x in path[24:])


def test_status_quo_and_custom_cap_paths_are_constant():
    assert inflation_path(REGIME_STATUS_QUO, 36, 0.025, 0.016, 24) == [0.025] * 36
    cap = inflation_path(REGIME_CUSTOM_CAP, 36, 0.025, 0.012, 24)
    assert cap == [0.012] * 36
    with pytest.raises(ValueError):
        inflation_path("not_a_regime", 36, 0.025, 0.016, 24)
    with pytest.raises(ValueError):
        inflation_path(REGIME_SVRN_GLIDEPATH, 0, 0.025, 0.016, 24)


def test_breakeven_flips_sign_of_net_float_change():
    issuance = daily_issuance_near(SUPPLY, 0.025)
    tau, alpha, gas, lock = 15.8, 0.353, 1000.0, 290.0
    v_star = breakeven_daily_volume_usd(issuance, gas, lock, PRICE, tau, alpha)
    assert v_star > 0
    at = net_float_change_near_day(issuance, daily_sinks_near(v_star, tau, alpha, PRICE, gas, lock))
    below = net_float_change_near_day(issuance, daily_sinks_near(v_star * (1 - 1e-6), tau, alpha, PRICE, gas, lock))
    above = net_float_change_near_day(issuance, daily_sinks_near(v_star * (1 + 1e-6), tau, alpha, PRICE, gas, lock))
    assert abs(at) < 1e-6 * issuance
    assert below > 0 > above


def test_breakeven_is_zero_when_burn_and_lock_exceed_issuance_and_raises_without_capture():
    assert breakeven_daily_volume_usd(100.0, 80.0, 30.0, PRICE, 15.8, 0.35) == 0.0
    with pytest.raises(ValueError):
        breakeven_daily_volume_usd(100.0, 0.0, 0.0, PRICE, 15.8, 0.0)
    with pytest.raises(ValueError):
        daily_sinks_near(1e8, 15.8, 0.35, 0.0, 0.0, 0.0)


def test_daily_sinks_total_identity():
    s = daily_sinks_near(1.3e8, 15.8, 0.353, PRICE, 1000.0, 290.0)
    assert s["total"] == pytest.approx(s["buyback"] + s["gas_burn"] + s["state_lock"])
    assert s["buyback"] == pytest.approx(1.3e8 * 15.8e-4 * 0.353 / PRICE)


# ----------------------------------------------------------------------------- trajectory
def test_trajectory_cumulative_arrays_monotone_and_identity():
    path = inflation_path(REGIME_SVRN_GLIDEPATH, 36, 0.025, 0.016, 24)
    tr = trajectory(REGIME_SVRN_GLIDEPATH, path, SUPPLY, 1.3e8, 15.8, 0.353, PRICE, 1000.0, 290.0, realization_factor=0.99)
    for arr in (tr.gross_issuance_cum, tr.buyback_cum, tr.gas_burn_cum, tr.state_lock_cum):
        assert len(arr) == 36 and all(b >= a for a, b in zip(arr, arr[1:]))
    net = np.array(tr.gross_issuance_cum) - np.array(tr.buyback_cum) - np.array(tr.gas_burn_cum) - np.array(tr.state_lock_cum)
    assert np.allclose(net, tr.net_float_change_cum, rtol=0, atol=1e-6)
    assert tr.months == list(range(1, 37))
    # first month issuance = S x i_0 x f x D / 365.25, expressed per day
    assert tr.daily_issuance_start == pytest.approx(SUPPLY * 0.025 * 0.99 / DAYS_PER_YEAR, rel=1e-12)
    # terminal rate 1.6% applied to the compounded supply
    s_end_start = SUPPLY * np.prod([1 + r * 0.99 * DAYS_PER_MONTH / DAYS_PER_YEAR for r in path[:-1]])
    assert tr.daily_issuance_end == pytest.approx(s_end_start * 0.016 * 0.99 / DAYS_PER_YEAR, rel=1e-12)
    assert tr.crossover_month is None  # flat run-rate volume cannot offset 2.5%/1.6% issuance
    assert all(isinstance(x, float) for x in tr.net_float_change_cum)


def test_trajectory_crossover_detection():
    path = inflation_path(REGIME_STATUS_QUO, 36, 0.025, 0.025, 24)
    # volume above V* from day one -> crossover in month 1 and cumulative crossover in month 1
    issuance = daily_issuance_near(SUPPLY, 0.025)
    v_star = breakeven_daily_volume_usd(issuance, 0.0, 0.0, PRICE, 15.8, 0.353)
    tr = trajectory(REGIME_STATUS_QUO, path, SUPPLY, v_star * 1.05, 15.8, 0.353, PRICE, 0.0, 0.0)
    assert tr.crossover_month == 1
    assert tr.model_dump()["cumulative_crossover_month"] == 1
    # growth path: starts below V*, grows 150%/yr -> crosses mid-horizon; before it monthly net > 0, at it <= 0
    tr = trajectory(REGIME_STATUS_QUO, path, SUPPLY, v_star * 0.5, 15.8, 0.353, PRICE, 0.0, 0.0, volume_growth_yoy=1.5)
    assert tr.crossover_month is not None and 1 < tr.crossover_month < 36
    monthly = tr.model_dump()["monthly_net_float_change"]
    assert all(x > 0 for x in monthly[: tr.crossover_month - 1]) and monthly[tr.crossover_month - 1] <= 0
    cum = tr.model_dump()["cumulative_crossover_month"]
    assert cum is None or cum >= tr.crossover_month
    # far below V*, flat -> never
    tr = trajectory(REGIME_STATUS_QUO, path, SUPPLY, v_star * 0.1, 15.8, 0.353, PRICE, 0.0, 0.0)
    assert tr.crossover_month is None


def test_trajectory_price_path_and_validation():
    path = inflation_path(REGIME_STATUS_QUO, 12, 0.025, 0.025, 24)
    spot = trajectory(REGIME_STATUS_QUO, path, SUPPLY, 1e8, 15.8, 0.353, PRICE, 0.0, 0.0)
    doubled = trajectory(REGIME_STATUS_QUO, path, SUPPLY, 1e8, 15.8, 0.353, PRICE, 0.0, 0.0, price_path=[2 * PRICE] * 12)
    assert doubled.buyback_cum[-1] == pytest.approx(spot.buyback_cum[-1] / 2)
    assert doubled.gross_issuance_cum == spot.gross_issuance_cum
    with pytest.raises(ValueError):
        trajectory(REGIME_STATUS_QUO, path, SUPPLY, 1e8, 15.8, 0.353, PRICE, 0.0, 0.0, price_path=[PRICE] * 5)
    with pytest.raises(ValueError):
        trajectory(REGIME_STATUS_QUO, [], SUPPLY, 1e8, 15.8, 0.353, PRICE, 0.0, 0.0)


# ----------------------------------------------------------------------------- tables
def test_staking_rows_formulas():
    rows = staking_yield_rows({"status_quo": 0.025, "svrn_glidepath": 0.016}, treasury_share=0.0, staked_supply_ratio=0.4527,
                              total_supply_near=SUPPLY, buyback_near_per_day=16_828.3)
    sq = rows[0]
    assert sq["nominal_staking_apr"] == pytest.approx(0.025 / 0.4527)
    assert sq["real_staking_apr"] == pytest.approx(0.025 / 0.4527 - 0.025)
    assert sq["buyback_accrual_apr"] == pytest.approx(16_828.3 * DAYS_PER_YEAR / SUPPLY)
    assert sq["real_non_staker_apr"] == pytest.approx(-0.025 + sq["buyback_accrual_apr"])
    # a 10% treasury share reduces the validator APR by 10%
    with_t = staking_yield_rows({"x": 0.025}, treasury_share=0.1, staked_supply_ratio=0.4527, total_supply_near=SUPPLY, buyback_near_per_day=0.0)
    assert with_t[0]["nominal_staking_apr"] == pytest.approx(0.9 * 0.025 / 0.4527)
    assert rows[1]["real_staking_apr"] < rows[0]["real_staking_apr"]  # lower inflation lowers the staker's real spread...
    assert rows[1]["real_non_staker_apr"] > rows[0]["real_non_staker_apr"]  # ...but improves the unstaked holder


def test_agent_scale_rows_grid_and_formula():
    rows = agent_scale_rows(20.0, 0.01, daily_issuance_near_=89_000.0, total_supply_near=SUPPLY)
    assert len(rows) == 9
    one_m = next(r for r in rows if r["agents"] == 1_000_000 and r["kb_per_agent"] == 20.0)
    assert one_m["locked_near"] == pytest.approx(1_000_000 * 20 * 0.01) and one_m["is_default_kb"]
    assert one_m["days_of_issuance_absorbed"] == pytest.approx(200_000 / 89_000)
    assert len(agent_scale_rows(7.0, 0.01)) == 12  # non-grid default kb adds a column


# ----------------------------------------------------------------------------- run_supply_physics
def test_run_uses_measured_issuance_and_identities_hold():
    sp = _run(competitive_ceiling_bps=3.0)
    assert sp.inputs["annual_issuance_near"].source == "measured"
    assert sp.inputs["annual_issuance_near"].value == pytest.approx(MINTED * EPOCHS_PER_YEAR)
    assert sp.current_daily_issuance_near * DAYS_PER_YEAR == pytest.approx(sp.inputs["annual_issuance_near"].value, rel=1e-12)
    f = sp.inputs["issuance_realization_factor"].value
    assert f == pytest.approx(MINTED * EPOCHS_PER_YEAR / (SUPPLY * 0.025))
    # buyback identity: V x tau x alpha / P == holders_revenue_30d / 30 / P
    assert sp.current_daily_sinks_near["buyback"] == pytest.approx(HOLDERS30 / 30 / PRICE, rel=1e-9)
    assert sp.current_daily_sinks_near["gas_burn"] == pytest.approx(297.0 * EPOCHS_PER_YEAR / DAYS_PER_YEAR)
    assert sp.inputs["gas_burn_near_per_day"].source == "measured"
    assert sp.current_daily_sinks_near["state_lock"] == 290.0 and sp.inputs["state_lock_growth_near_per_day"].source == "measured"
    assert sp.sink_coverage_ratio == pytest.approx(sp.current_daily_sinks_near["total"] / sp.current_daily_issuance_near)
    # breakeven per regime at the regime's terminal rate x realization factor
    for regime, terminal in ((REGIME_STATUS_QUO, 0.025), (REGIME_SVRN_GLIDEPATH, 0.016)):
        issuance = daily_issuance_near(SUPPLY, terminal) * f
        s = sp.current_daily_sinks_near
        expected = breakeven_daily_volume_usd(issuance, s["gas_burn"], s["state_lock"], PRICE, sp.inputs["gross_take_bps"].value, sp.inputs["capture_ratio"].value)
        assert sp.breakeven_daily_volume_usd[regime] == pytest.approx(expected)
        sinks_at = daily_sinks_near(expected, sp.inputs["gross_take_bps"].value, sp.inputs["capture_ratio"].value, PRICE, s["gas_burn"], s["state_lock"])
        assert abs(net_float_change_near_day(issuance, sinks_at)) < 1e-6 * issuance
    assert sp.breakeven_daily_volume_usd[REGIME_SVRN_GLIDEPATH] < sp.breakeven_daily_volume_usd[REGIME_STATUS_QUO]
    # status quo trajectory starts at the measured daily issuance
    sq = next(t for t in sp.trajectories if t.regime == REGIME_STATUS_QUO)
    assert sq.daily_issuance_start == pytest.approx(sp.current_daily_issuance_near, rel=1e-9)
    # ceiling variant: lower take -> more volume needed
    dumped = sp.model_dump()
    ceiling = dumped["breakeven_daily_volume_usd_at_ceiling"]
    assert set(ceiling) == set(sp.breakeven_daily_volume_usd)
    assert ceiling[REGIME_STATUS_QUO] == pytest.approx(sp.breakeven_daily_volume_usd[REGIME_STATUS_QUO] * sp.inputs["gross_take_bps"].value / 3.0)
    assert sp.inputs["competitive_fee_ceiling_bps"].source == "derived"  # a statistic over quotes, not an observed schedule
    # V, tau and alpha all come from the same aligned window published by intents_forensics.
    assert "same window" in sp.inputs["gross_take_bps"].justification and "same window" in sp.inputs["capture_ratio"].justification
    assert sp.inputs["daily_volume_usd"].value == pytest.approx(VOL30 / 30)
    assert dumped["warnings"] == []


def test_run_regimes_and_glidepath_endpoints():
    sp = _run()
    keys = [r.key for r in sp.regimes]
    assert keys == [REGIME_STATUS_QUO, REGIME_SVRN_GLIDEPATH]
    glide = next(r for r in sp.regimes if r.key == REGIME_SVRN_GLIDEPATH)
    assert glide.inflation_path_annual[0] == pytest.approx(0.025) and glide.inflation_path_annual[-1] == pytest.approx(0.016)
    assert len(glide.inflation_path_annual) == config.HORIZON_MONTHS
    assert {t.regime for t in sp.trajectories} == set(keys)
    assert {t["regime"] for t in sp.model_dump()["growth_trajectories"]} == set(keys)
    assert sp.model_dump()["growth_trajectories"][0]["volume_growth_yoy"] == pytest.approx(assumptions.value("public_volume_growth_yoy"))
    assert [r["regime"] for r in sp.staking_yield_table] == keys
    assert sp.staking_yield_table[0]["nominal_staking_apr"] == pytest.approx(_truth().nominal_staking_apr_current)


def test_run_custom_cap_regime_is_constant():
    sp = _run(custom_cap=0.012)
    cap = next(r for r in sp.regimes if r.key == REGIME_CUSTOM_CAP)
    assert cap.inflation_path_annual == [0.012] * config.HORIZON_MONTHS
    tr = next(t for t in sp.trajectories if t.regime == REGIME_CUSTOM_CAP)
    f = sp.inputs["issuance_realization_factor"].value
    assert tr.daily_issuance_start == pytest.approx(daily_issuance_near(SUPPLY, 0.012) * f, rel=1e-12)
    assert REGIME_CUSTOM_CAP in sp.breakeven_daily_volume_usd
    assert sp.inputs["custom_cap_inflation"].source == "assumption"


def test_run_falls_back_to_nominal_issuance_with_warning():
    sp = _run(truth=_truth(measured=False))
    assert sp.inputs["annual_issuance_near"].source == "derived"
    assert sp.inputs["annual_issuance_near"].value == pytest.approx(SUPPLY * 0.025)
    assert sp.inputs["issuance_realization_factor"].value == 1.0
    assert any("nominal" in w for w in sp.model_dump()["warnings"])


def test_run_state_lock_fallback_is_zero_credit_with_warning():
    sp = _run(truth=_truth(lock=None))
    assert sp.current_daily_sinks_near["state_lock"] == 0.0
    assert sp.inputs["state_lock_growth_near_per_day"].source == "assumption"
    assert any("state-lock growth not measured" in w for w in sp.model_dump()["warnings"])
    # and the labeled fallback value is honoured when overridden
    reg = assumptions.with_overrides({"state_lock_growth_fallback_near_per_day": 500.0})
    sp2 = _run(truth=_truth(lock=None), registry=reg)
    assert sp2.current_daily_sinks_near["state_lock"] == 500.0


def test_run_gas_burn_fallback_chain():
    llama = _run(truth=_truth(burn=None))
    assert llama.inputs["gas_burn_near_per_day"].source == "derived"
    assert llama.current_daily_sinks_near["gas_burn"] == pytest.approx(141_650.0 / 30 / PRICE)
    assert any("DefiLlama" in w for w in llama.model_dump()["warnings"])
    # the "near" row is found whether it sits in peers or in the collector's near_components extra
    in_peers = _run(truth=_truth(burn=None), comps=_comps(in_peers=True))
    assert in_peers.current_daily_sinks_near["gas_burn"] == pytest.approx(141_650.0 / 30 / PRICE)
    none = _run(truth=_truth(burn=None), comps=_comps(near_revenue_30d=None))
    assert none.current_daily_sinks_near["gas_burn"] == 0.0
    assert any("gas burn unavailable" in w for w in none.model_dump()["warnings"])
    positive_drift = _run(truth=_truth(burn=+50.0))
    assert positive_drift.current_daily_sinks_near["gas_burn"] == 0.0


def test_run_capture_override_assumption():
    reg = assumptions.with_overrides({"buyback_capture_ratio_override": 0.5})
    sp = _run(registry=reg)
    assert sp.inputs["capture_ratio"].source == "assumption" and sp.inputs["capture_ratio"].value == 0.5
    assert sp.current_daily_sinks_near["buyback"] == pytest.approx(VOL30 / 30 * (GROSS30 / VOL30) * 0.5 / PRICE)


def test_run_price_resolution_and_failure():
    kwarg = _run(price_usd=2 * PRICE)
    assert kwarg.inputs["near_price_usd"].value == 2 * PRICE
    assert kwarg.current_daily_sinks_near["buyback"] == pytest.approx(HOLDERS30 / 30 / (2 * PRICE))
    from_comps = _run(forensics=_forensics(price=None))
    assert from_comps.inputs["near_price_usd"].value == PRICE
    with pytest.raises(ValueError):
        _run(forensics=_forensics(price=None), comps=_comps(near_price=None))


def test_run_requires_volume_and_take():
    with pytest.raises(ValueError):
        _run(forensics=IntentsForensics(volume={}, fees={}, price={"current_usd": PRICE}, volatility={}, hhi_external=0, n_eff_external=0,
                                        hhi_all=0, ai_agent_share=0, bridge_share=0, receipts_sampled=0, pages_fetched=0))
    with pytest.raises(ValueError):
        _run(forensics=_forensics(fees={}))


def test_run_precomputed_ratios_fallback_when_raw_totals_missing():
    sp = _run(forensics=_forensics(fees={"gross_take_bps": 15.8, "capture_ratio": 0.353}))
    assert sp.inputs["gross_take_bps"].value == 15.8 and sp.inputs["capture_ratio"].value == 0.353
    assert sp.current_daily_sinks_near["buyback"] == pytest.approx(VOL30 / 30 * 15.8e-4 * 0.353 / PRICE)


def test_run_is_deterministic_and_json_safe():
    a, b = _run(custom_cap=0.01, competitive_ceiling_bps=3.0), _run(custom_cap=0.01, competitive_ceiling_bps=3.0)
    assert a.model_dump() == b.model_dump()
    text = a.model_dump_json()
    parsed = json.loads(text)  # strict JSON: no NaN / Infinity / numpy scalars
    assert SupplyPhysics.model_validate_json(text).model_dump() == a.model_dump()
    assert all(isinstance(v, float) for v in parsed["breakeven_daily_volume_usd"].values())
    assert set(parsed["current_daily_sinks_near"]) == {"buyback", "gas_burn", "state_lock", "total"}
    assert all(a_.source in {"measured", "derived", "assumption"} for a_ in a.inputs.values())
