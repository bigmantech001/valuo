"""Unit tests for valuo.models.sotp_valuation (pure math; synthetic inputs live only here)."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from valuo import assumptions as A
from valuo.models.sotp_valuation import (
    DAYS_PER_MONTH,
    HARD_FLOOR_BPS,
    HEATMAP_NET_TAKE_BPS,
    HEATMAP_VOLUMES_USD,
    REGIME_GLIDEPATH,
    REGIME_STATUS_QUO,
    build_inputs,
    deterministic_sotp,
    percentiles,
    run_sotp,
    simulate_paths,
)
from valuo.schemas import (
    PERCENTILE_KEYS,
    Assumption,
    EpochIssuanceMeasurement,
    ExecutionBenchmark,
    IntentsForensics,
    NearOnchainTruth,
    PeerComp,
    PeerComps,
    Regime,
    SotpValuation,
    SupplyPhysics,
    SupplyTrajectory,
)

H = 36
SUPPLY = 1.31e9
PRICE = 4.31
SEED = 20261114
# Magnitudes follow docs/LIVE_ENDPOINT_FACTS.md (Oct 2026) so sanity bounds are meaningful; they are
# test fixtures, not model inputs.
V_PUB_30D = 2.357e9
V_CONF_30D = 1.536e9
FEES_30D = 6.159e6
HREV_30D = 2.176e6
DAILY_ISSUANCE = 88_700.0


def _truth() -> NearOnchainTruth:
    return NearOnchainTruth(
        block_height=222_342_342, block_hash="H", timestamp_ns=0, timestamp_utc="2026-10-30T23:51:00Z",
        total_supply_near=SUPPLY, gas_price_yocto=100_000_000, max_inflation_rate=0.025, protocol_reward_rate=0.0,
        storage_amount_per_byte_yocto=10**19, storage_near_per_kb=0.01, num_blocks_per_year=31_536_000,
        epoch_length_blocks=43_200, protocol_version=86, active_validator_count=379, total_staked_near=5.93e8,
        staked_supply_ratio=0.4527, nominal_staking_apr_current=0.0552, nominal_staking_apr_svrn_1_6=0.0353,
        gross_daily_issuance_near=SUPPLY * 0.025 / 365.25, gross_daily_issuance_svrn_near=SUPPLY * 0.016 / 365.25,
        epoch_issuance=EpochIssuanceMeasurement(
            epoch_start_height=222_321_137, epoch_start_hash="E", nominal_annual_issuance_near=SUPPLY * 0.025,
            method_note="fixture",
        ),
        total_state_locked_near=276_000.0, measured_state_lock_growth_near_per_day=290.0,
        rpc_endpoint_used="fixture", archival_available=True,
    )


def _forensics(**over) -> IntentsForensics:
    volatility = {"window": "1y", "n_obs": 365, "daily_sigma": 0.0563, "annualized_sigma": 1.076,
                  "volume_daily_sigma": 0.62, "volume_annualized_sigma": 11.8, "volume_monthly_sigma": 0.4645}
    volatility.update(over.pop("volatility", {}))
    fields = dict(
        volume={"allTimeUsd": 36.68e9, "24h": 141.7e6, "7d": 800.5e6, "30d": V_PUB_30D + V_CONF_30D,
                "public30d": V_PUB_30D, "confidential30d": V_CONF_30D,
                "confidential_share_30d": V_CONF_30D / (V_PUB_30D + V_CONF_30D)},
        fees={"gross_fees_30d_usd": FEES_30D, "net_revenue_30d_usd": HREV_30D, "holders_revenue_30d_usd": HREV_30D,
              "gross_take_bps": FEES_30D / (V_PUB_30D + V_CONF_30D) * 1e4,
              "net_take_bps": HREV_30D / (V_PUB_30D + V_CONF_30D) * 1e4, "capture_ratio": HREV_30D / FEES_30D},
        confidential_tvl_usd=144.42e6, confidential_tvl_verified=False, unique_users_7d=103_102,
        price={"current_usd": PRICE, "fdv_usd": PRICE * SUPPLY, "market_cap_usd": PRICE * SUPPLY,
               "circulating_supply": SUPPLY, "total_supply": SUPPLY},
        volatility=volatility,
        callers=[], hhi_external=1800.0, n_eff_external=5.5, hhi_all=2500.0, ai_agent_share=0.2, bridge_share=0.1,
        method_mix={"execute_intents": 50}, receipts_sampled=100, pages_fetched=4, lifetime_receipts=156_722_083,
        sample_block_range=[222_300_000, 222_342_342],
    )
    fields.update(over)
    return IntentsForensics(**fields)


def _comps(median: float | None = 25.0) -> PeerComps:
    near = PeerComp(slug="near", symbol="NEAR", fdv_usd=PRICE * SUPPLY, revenue_30d_usd=HREV_30D)
    return PeerComps(peers=[PeerComp(slug="solana", symbol="SOL", fdv_to_revenue=median)], near_combined=near,
                     median_fdv_to_revenue_ex_near=median, median_fdv_to_fees_ex_near=None,
                     fetched_at_utc="2026-10-30T23:51:00Z")


def _trajectory(regime: str, path: list[float], buyback_day: float, gas_day: float, lock_day: float) -> SupplyTrajectory:
    months = list(range(1, H + 1))
    iss = np.cumsum([SUPPLY * r / 12.0 for r in path]).tolist()
    bb = [buyback_day * DAYS_PER_MONTH * m for m in months]
    gas = [gas_day * DAYS_PER_MONTH * m for m in months]
    lock = [lock_day * DAYS_PER_MONTH * m for m in months]
    net = [i - b - g - lk for i, b, g, lk in zip(iss, bb, gas, lock, strict=True)]
    return SupplyTrajectory(regime=regime, months=months, gross_issuance_cum=iss, buyback_cum=bb, gas_burn_cum=gas,
                            state_lock_cum=lock, net_float_change_cum=net, crossover_month=None,
                            daily_issuance_start=SUPPLY * path[0] / 365.25, daily_issuance_end=SUPPLY * path[-1] / 365.25)


def _supply(**over) -> SupplyPhysics:
    sq = [0.025] * H
    # 0-based like supply_physics: month 1 is still the live rate.
    glide = [0.025 + (0.016 - 0.025) * min(t - 1, 24) / 24 for t in range(1, H + 1)]
    buyback_day = HREV_30D / 30 / PRICE
    gas_day = 141_650 / 30 / PRICE
    lock_day = 290.0
    fields = dict(
        inputs={}, regimes=[Regime(key=REGIME_STATUS_QUO, label="2.5% flat", inflation_path_annual=sq),
                            Regime(key=REGIME_GLIDEPATH, label="2.5% -> 1.6%", inflation_path_annual=glide)],
        trajectories=[_trajectory(REGIME_STATUS_QUO, sq, buyback_day, gas_day, lock_day),
                      _trajectory(REGIME_GLIDEPATH, glide, buyback_day, gas_day, lock_day)],
        breakeven_daily_volume_usd={REGIME_STATUS_QUO: 6.7e8, REGIME_GLIDEPATH: 4.3e8},
        current_daily_sinks_near={"buyback": buyback_day, "gas_burn": gas_day, "state_lock": lock_day,
                                  "total": buyback_day + gas_day + lock_day},
        current_daily_issuance_near=DAILY_ISSUANCE, sink_coverage_ratio=(buyback_day + gas_day + lock_day) / DAILY_ISSUANCE,
    )
    fields.update(over)
    return SupplyPhysics(**fields)


def _bench(headroom: float | None = 1.0) -> ExecutionBenchmark:
    return ExecutionBenchmark(ran_at_utc="2026-10-30T23:51:00Z", clips_usd=[500, 50_000, 250_000], corridors=[], results=[],
                              headroom_by_archetype_bps={"cross_vm": headroom, "evm_l2": -1.0, "native_btc": 15.0},
                              competitive_fee_ceiling_bps=14.0, oneclick_1y_token_universe=210, oneclick_blockchains=["eth"])


def _base_inputs(**kw):
    inputs, cal, labeled = build_inputs(_truth(), _forensics(), _comps(), _supply(), A.ASSUMPTIONS, bench=_bench(), **kw)
    return inputs, cal, labeled


def _small_inputs(**over) -> dict:
    """Hand-computable deterministic case (H=1, no discounting, no growth, no compression)."""
    base = dict(
        v_pub_usd_day=1e6, v_conf_usd_day=0.0, tau_pub_bps=10.0, tau_conf_bps=20.0, alpha_capture=0.5,
        discount_rate=0.0, terminal_multiple=10.0, conf_haircut=0.7, gas_burn_usd_day=0.0, state_lock_near_day=0.0,
        price_usd=1.0, total_supply=1e6, issuance_rate_path=[0.12], growth_monthly_pub=0.0, growth_monthly_conf=0.0,
        lambda_pub=0.0, lambda_conf=0.0, tau_floor_bps=0.5, horizon_months=1,
    )
    base.update(over)
    return base


# ----------------------------------------------------------------------------- percentiles
def test_percentiles_keys_and_order():
    p = percentiles(np.arange(1, 101, dtype=float))
    assert tuple(p) == PERCENTILE_KEYS
    assert p["p10"] < p["p25"] < p["p50"] < p["p75"] < p["p90"]
    assert p["p50"] == pytest.approx(50.5)
    with pytest.raises(ValueError):
        percentiles([])


# ----------------------------------------------------------------------------- deterministic engine
def test_deterministic_sotp_hand_computed_h1():
    res = deterministic_sotp(_small_inputs())
    rev = 1e6 * 10 / 1e4 * DAYS_PER_MONTH * 0.5  # 15,218.75
    assert rev == pytest.approx(15_218.75)
    e1 = rev + rev * 12 * 10  # PV (df=1) + year-3 run-rate x multiple
    assert res["engine_clearinghouse"] == pytest.approx(e1)
    assert res["engine_confidential"] == 0.0 and res["engine_monetary"] == 0.0
    assert res["fdv_total"] == pytest.approx(e1) and res["fdv_ex_monetary"] == pytest.approx(e1)
    issuance = 1e6 * 0.12 / 12  # 10,000 NEAR
    buyback = rev / 1.0
    assert res["monthly_net_float_change_near"] == [pytest.approx(issuance - buyback)]
    assert res["crossover_month"] == 1 and res["net_deflation"] is True
    assert res["supply_at_horizon_internal"] == pytest.approx(1e6 + issuance - buyback)
    assert res["implied_price"] == pytest.approx(e1 / (1e6 + issuance - buyback))
    assert res["monthly_holder_revenue"] == [pytest.approx(rev)]


def test_deterministic_sotp_hand_computed_h2_growth_compression():
    inputs = _small_inputs(horizon_months=2, issuance_rate_path=[0.12, 0.12], alpha_capture=1.0, terminal_multiple=1.0,
                           tau_pub_bps=10.0, tau_floor_bps=4.0, lambda_pub=0.5, growth_monthly_pub=0.1,
                           total_supply=1e9)
    res = deterministic_sotp(inputs)
    tau1, tau2 = 4 + 6 * 0.5, 4 + 6 * 0.25  # 7.0, 5.5
    v1, v2 = 1e6 * 1.1, 1e6 * 1.21
    rev1 = v1 * tau1 / 1e4 * DAYS_PER_MONTH
    rev2 = v2 * tau2 / 1e4 * DAYS_PER_MONTH
    assert res["monthly_tau_pub_bps"] == [pytest.approx(tau1), pytest.approx(tau2)]
    assert res["monthly_holder_revenue"] == [pytest.approx(rev1), pytest.approx(rev2)]
    tv = (rev1 + rev2) * (12 / 2) * 1.0
    assert res["engine_clearinghouse"] == pytest.approx(rev1 + rev2 + tv)
    assert res["crossover_month"] is None and res["net_deflation"] is False  # 1e9 x 1% = 10M NEAR/month issued


def test_deterministic_discounting_and_supply_override():
    inputs = _small_inputs(discount_rate=0.25, supply_at_horizon=2e6)
    res = deterministic_sotp(inputs)
    rev = 15_218.75
    df = 1.25 ** (-1 / 12)
    assert res["engine_clearinghouse"] == pytest.approx(rev * df + rev * 12 * 10 * df)
    assert res["implied_price"] == pytest.approx(res["fdv_total"] / 2e6)
    assert res["supply_at_horizon_used"] == 2e6


def test_deterministic_zero_volume_zeroes_revenue_engines():
    inputs = _small_inputs(v_pub_usd_day=0.0, v_conf_usd_day=0.0, gas_burn_usd_day=100.0, state_lock_near_day=5.0)
    res = deterministic_sotp(inputs)
    assert res["engine_clearinghouse"] == 0.0 and res["engine_confidential"] == 0.0
    assert res["engine_monetary"] > 0.0  # measured sinks are held at level when volume is zero
    assert res["fdv_total"] == pytest.approx(res["engine_monetary"])


def test_deterministic_engines_sum_to_total_and_validation():
    inputs, _, _ = _base_inputs()
    res = deterministic_sotp(inputs)
    assert res["fdv_total"] == pytest.approx(res["engine_clearinghouse"] + res["engine_confidential"] + res["engine_monetary"])
    assert res["fdv_ex_monetary"] == pytest.approx(res["engine_clearinghouse"] + res["engine_confidential"])
    assert len(res["monthly_holder_revenue"]) == H
    with pytest.raises(ValueError):
        deterministic_sotp({**inputs, "issuance_rate_path": [0.025] * 10})
    with pytest.raises(ValueError):
        deterministic_sotp({**inputs, "price_usd": 0.0})


# ----------------------------------------------------------------------------- input assembly
def test_build_inputs_reconciles_month0_fees_and_records_calibration():
    inputs, cal, labeled = _base_inputs()
    # Month-0 modelled gross fees equal DefiLlama's 30d fees for any confidential-take assumption.
    pub_fees = V_PUB_30D * inputs["tau_pub_bps"] / 1e4
    conf_fees = V_CONF_30D * inputs["tau_conf_bps"] / 1e4
    assert pub_fees + conf_fees == pytest.approx(FEES_30D)
    assert inputs["alpha_capture"] == pytest.approx(HREV_30D / FEES_30D)
    assert cal["net_take_start_bps"] == pytest.approx(HREV_30D / (V_PUB_30D + V_CONF_30D) * 1e4)
    # tau_floor = max(0.5, min(tau_pub0, headroom 1.0)) = 1.0 bps from the benchmark
    assert inputs["tau_floor_bps"] == pytest.approx(1.0) and cal["tau_floor_source"] == "derived"
    assert cal["competitive_fee_ceiling_bps"] == 14.0
    assert cal["terminal_multiple_used"] == 25.0 and cal["terminal_multiple_clipped"] is False
    assert cal["sigma_volume_source"].startswith("measured") and cal["sigma_volume_monthly"] == pytest.approx(0.4645)
    assert cal["sigma_price_monthly"] == pytest.approx(1.076 / math.sqrt(12))
    assert inputs["growth_monthly_pub"] == pytest.approx(1.3 ** (1 / 12) - 1)
    assert cal["issuance_scale_measured_over_path"] == pytest.approx(DAILY_ISSUANCE * 365.25 / (SUPPLY * 0.025))
    assert len(inputs["issuance_rate_path"]) == H and set(inputs["issuance_rate_paths"]) == {REGIME_STATUS_QUO, REGIME_GLIDEPATH}
    assert inputs["supply_at_horizon"] is not None and inputs["supply_at_horizon"] > 1e9
    assert cal["warnings"] == []
    for k in ("tau_pub_start_bps", "alpha_capture", "terminal_multiple", "tau_floor_bps", "sigma_price_annual", "sigma_volume_monthly", "discount_rate"):
        assert k in labeled
    assert labeled["alpha_capture"].source == "measured" and labeled["tau_pub_start_bps"].source == "derived"


def test_build_inputs_without_benchmark_uses_hard_floor_with_warning():
    inputs, cal, labeled = build_inputs(_truth(), _forensics(), _comps(), _supply(), A.ASSUMPTIONS, bench=None)
    assert inputs["tau_floor_bps"] == HARD_FLOOR_BPS
    assert "public_take_floor_bps" in labeled and labeled["public_take_floor_bps"].source == "assumption"
    assert any("benchmark unavailable" in w for w in cal["warnings"])


def test_build_inputs_volume_sigma_fallback_chain_never_raises():
    _, cal, labeled = build_inputs(_truth(), _forensics(volatility={"volume_monthly_sigma": None}), _comps(), _supply(),
                                   A.ASSUMPTIONS, bench=_bench())
    assert cal["sigma_volume_monthly"] == pytest.approx(0.62 * math.sqrt(30))
    assert cal["sigma_volume_source"].startswith("derived") and labeled["sigma_volume_monthly"].source == "derived"
    assert cal["sigma_volume_measured"] is True  # derived from the measured daily sigma, like sigma_price_measured
    assert any("volume_monthly_sigma missing" in w for w in cal["warnings"])
    # Both volume sigmas null (DefiLlama dexs chart outage; the 30d volume itself fell back to nearstats): the run degrades
    # to the labeled volume_sigma_monthly_fallback with a loud warning instead of exiting 4 - a single-source outage is
    # never fatal, mirroring the price-sigma and peer-multiple fallbacks.
    inputs, cal2, labeled2 = build_inputs(_truth(), _forensics(volatility={"volume_monthly_sigma": None, "volume_daily_sigma": None}), _comps(),
                                          _supply(), A.ASSUMPTIONS, bench=_bench())
    fb = A.value("volume_sigma_monthly_fallback")
    assert cal2["sigma_volume_monthly"] == fb and inputs["sigma_volume_monthly"] == pytest.approx(fb)
    assert cal2["sigma_volume_source"] == "assumption:volume_sigma_monthly_fallback" and cal2["sigma_volume_measured"] is False
    assert labeled2["sigma_volume_monthly"].source == "assumption" and "volume_sigma_monthly_fallback" in labeled2
    assert labeled2["volume_sigma_monthly_fallback"].source == "assumption"
    assert any("volume_sigma_monthly_fallback" in w and "not measured" in w for w in cal2["warnings"])


def test_price_sigma_missing_falls_back_to_labeled_assumption_not_exit():
    # Both price series down (nearstats price-history and the coins.llama.fi chart): the run degrades to the labeled
    # price_sigma_annual_fallback with a warning instead of exiting 4.
    inputs, cal, labeled = build_inputs(_truth(), _forensics(volatility={"annualized_sigma": None, "daily_sigma": None}), _comps(), _supply(),
                                        A.ASSUMPTIONS, bench=_bench())
    fb = A.value("price_sigma_annual_fallback")
    assert cal["sigma_price_annual"] == fb and inputs["sigma_price_monthly"] == pytest.approx(fb / math.sqrt(12))
    assert cal["sigma_price_source"] == "assumption:price_sigma_annual_fallback" and cal["sigma_price_measured"] is False
    assert labeled["sigma_price_annual"].source == "assumption" and "price_sigma_annual_fallback" in labeled
    assert any("price_sigma_annual_fallback" in w and "not measured" in w for w in cal["warnings"])


def test_build_inputs_terminal_multiple_fallback_chain_and_clipping_logged():
    # CoinGecko outage, no FDV/fees median either: the labeled terminal_multiple_fallback (30x), source "assumption", no exit.
    inputs, cal, labeled = build_inputs(_truth(), _forensics(), _comps(None), _supply(), A.ASSUMPTIONS)
    assert inputs["terminal_multiple"] == A.value("terminal_multiple_fallback") == 30.0
    assert cal["terminal_multiple_raw"] is None and cal["terminal_multiple_source"] == "assumption"
    assert labeled["terminal_multiple"].source == "assumption" and "terminal_multiple_fallback" in labeled
    assert any("terminal_multiple_fallback" in w and "WARNING" in w for w in cal["warnings"])
    res = run_sotp(_truth(), _forensics(), _comps(None), _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=200, bench=_bench())
    assert res.engines[0].assumption_heavy is True and "terminal_multiple_fallback" in res.engines[0].method  # Engine 1 flagged
    # FDV/revenue median null but FDV/fees median present: the fees multiple stands in, labeled derived_fdv_to_fees.
    comps_fees = _comps(None)
    comps_fees.median_fdv_to_fees_ex_near = 12.0
    comps_fees.n_peers_in_fees_median = 2
    inputs, cal, labeled = build_inputs(_truth(), _forensics(), comps_fees, _supply(), A.ASSUMPTIONS)
    assert inputs["terminal_multiple"] == 12.0 and cal["terminal_multiple_source"] == "derived_fdv_to_fees"
    assert labeled["terminal_multiple"].source == "derived" and "FEES" in cal["terminal_multiple_basis"]
    assert any("FDV/fees" in w for w in cal["warnings"])
    res = run_sotp(_truth(), _forensics(), comps_fees, _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=200, bench=_bench())
    assert res.engines[0].assumption_heavy is False and "FDV/fees" in res.engines[0].method
    # Live median above the cap is clipped and logged, source stays derived.
    inputs, cal, _ = build_inputs(_truth(), _forensics(), _comps(250.0), _supply(), A.ASSUMPTIONS)
    assert inputs["terminal_multiple"] == A.value("terminal_multiple_cap") and cal["terminal_multiple_clipped"] is True
    assert cal["terminal_multiple_source"] == "derived"
    assert any("clipped" in w for w in cal["warnings"])


def test_build_inputs_survives_nearstats_outage_with_zero_confidential_and_supply_price():
    # nearstats down: no public/confidential split, no nearstats price. The confidential volume is credited 0 (Engine 2
    # reported as not measured, nothing invented), the price is the one supply_physics resolved (comps), sigma stays measured.
    forensics = _forensics(
        volume={"30d": V_PUB_30D + V_CONF_30D, "public30d": None, "confidential30d": None, "confidential_share_30d": None},
        price={"current_usd": None, "fdv_usd": None},
    )
    supply = _supply(inputs={"near_price_usd": Assumption(key="near_price_usd", value=PRICE, unit="USD", low=PRICE, high=PRICE,
                                                           source="measured", justification="comps peer 'near' price_usd")})
    inputs, cal, labeled = build_inputs(_truth(), forensics, _comps(), supply, A.ASSUMPTIONS, bench=_bench())
    assert inputs["v_conf_usd_day"] == 0.0 and inputs["v_pub_usd_day"] == pytest.approx((V_PUB_30D + V_CONF_30D) / 30)
    assert cal["confidential_share_assumed"] is True and cal["confidential_engine_measured"] is False
    assert labeled["confidential_share_start"].source == "assumption" and labeled["confidential_share_start"].value == 0.0
    assert inputs["price_usd"] == PRICE and "comps" in cal["price_source"]
    assert inputs["current_fdv_usd"] == pytest.approx(PRICE * SUPPLY)  # FDV on the model's own basis
    assert any("confidential share set to 0" in w for w in cal["warnings"])
    res = run_sotp(_truth(), forensics, _comps(), supply, A.ASSUMPTIONS, seed=SEED, n_paths=200, bench=_bench())
    conf = next(e for e in res.engines if e.key == "confidential")
    assert conf.p50 == 0.0 and "NOT MEASURED" in conf.method
    # Volume absent everywhere is still fatal, and the error names the null fields rather than listing present keys.
    with pytest.raises(ValueError, match="null in every source"):
        build_inputs(_truth(), _forensics(volume={"30d": None}, fees={"gross_fees_30d_usd": FEES_30D, "holders_revenue_30d_usd": HREV_30D}),
                     _comps(), supply, A.ASSUMPTIONS)


def test_build_inputs_labels_implausible_split_fallback_as_assumption():
    # confidential_split_guard rejected the nearstats split and substituted the registry confidential_share: the share
    # sizes Engine 2 but is labelled an assumption everywhere (calibration, inputs, engine method, warning).
    share = A.value("confidential_share")
    total = V_PUB_30D + V_CONF_30D
    forensics = _forensics(volume={
        "30d": total, "public30d": None, "confidential30d": None, "confidential_share_30d": share,
        "confidential_share_30d_reported": 0.0004, "confidential_share_status": "implausible_fallback",
        "confidential_share_measured": False,
        "confidential_share_source": f"assumption: registry confidential_share = {share:.0%} (nearstats split implausible; not a measurement)",
    })
    inputs, cal, labeled = build_inputs(_truth(), forensics, _comps(), _supply(), A.ASSUMPTIONS, bench=_bench())
    assert inputs["v_conf_usd_day"] == pytest.approx(total * share / 30)
    assert cal["confidential_share_status"] == "implausible_fallback"
    assert cal["confidential_share_assumed"] is True and cal["confidential_engine_measured"] is False
    assert cal["confidential_share_source"].startswith("assumption: registry confidential_share")
    lab = labeled["confidential_share_start"]
    assert lab.source == "assumption" and lab.justification.startswith("assumption:confidential_share")
    assert lab.value == pytest.approx(share)
    assert labeled["confidential_share"].source == "assumption"
    assert any("ASSUMPTION confidential_share" in w and "0.0400%" in w for w in cal["warnings"])
    res = run_sotp(_truth(), forensics, _comps(), _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=200, bench=_bench())
    conf = next(e for e in res.engines if e.key == "confidential")
    assert "NOT MEASURED" in conf.method and "assumption confidential_share" in conf.method and conf.p50 > 0
    assert res.inputs["confidential_share_start"].justification.startswith("assumption:confidential_share")


def test_build_inputs_measured_split_is_not_labelled_assumption():
    inputs, cal, labeled = build_inputs(_truth(), _forensics(), _comps(), _supply(), A.ASSUMPTIONS, bench=_bench())
    assert cal["confidential_engine_measured"] is True and cal["confidential_share_assumed"] is False
    assert cal["confidential_share_status"] == "measured" and "confidential_share_start" not in labeled


def test_current_fdv_is_price_times_onchain_supply_with_coingecko_cross_check():
    forensics = _forensics(price={"current_usd": PRICE, "fdv_usd": PRICE * SUPPLY * 0.99})
    inputs, cal, _ = build_inputs(_truth(), forensics, _comps(), _supply(), A.ASSUMPTIONS, bench=_bench())
    assert inputs["current_fdv_usd"] == pytest.approx(PRICE * SUPPLY)
    assert cal["current_fdv_coingecko_usd"] == pytest.approx(PRICE * SUPPLY * 0.99) == cal["current_fdv_nearstats_usd"]
    assert cal["current_fdv_nearstats_gap_pct"] == pytest.approx(-1.0)
    assert cal["gross_take_bps"] == pytest.approx(FEES_30D / (V_PUB_30D + V_CONF_30D) * 1e4)  # consumed from forensics.fees, not recomputed


def test_gbm_is_mean_matching_and_labeled():
    # E[V_12] equals v0 x (1+g)^12 (the deterministic path), so the labeled 30% YoY is the EXPECTED growth; the median
    # sits below it by exp(-sigma^2 t / 2). Same convention for price: zero drift keeps E[P_t] = P_0.
    inputs, cal, _ = _base_inputs()
    sim = simulate_paths(inputs, seed=SEED, n_paths=50_000)
    v0, g, sig = inputs["v_pub_usd_day"], inputs["growth_monthly_pub"], inputs["sigma_volume_monthly"]
    v12 = sim["v_pub"][:, 11]
    assert float(v12.mean()) == pytest.approx(v0 * (1 + g) ** 12, rel=0.10)
    assert float(v12.mean()) == pytest.approx(v0 * 1.30, rel=0.10)  # 30% YoY is the mean growth
    assert float(np.median(v12)) == pytest.approx(v0 * (1 + g) ** 12 * math.exp(-(sig**2) * 12 / 2), rel=0.05)
    assert float(np.median(sim["price"][:, -1])) < inputs["price_usd"] < float(sim["price"][:, -1].mean()) * 1.3
    assert float(np.median(sim["price"][:, -1])) == pytest.approx(inputs["price_usd"] * math.exp(-(inputs["sigma_price_monthly"] ** 2) * H / 2), rel=0.05)
    assert cal["volume_mean_to_median_12m"] == pytest.approx(math.exp(sig**2 * 12 / 2))
    assert cal["volume_terminal_mean_usd_day"] == pytest.approx(v0 * (1 + g) ** H)
    assert cal["volume_terminal_median_usd_day"] == pytest.approx(v0 * (1 + g) ** H * math.exp(-(sig**2) * H / 2))
    assert "mean-matching" in cal["gbm_convention"] and "EXPECTED" in A.get("public_volume_growth_yoy").justification
    res = run_sotp(_truth(), _forensics(), _comps(), _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=2000, bench=_bench())
    assert res.calibration["mc_mean_fdv"] > res.fdv_percentiles["p50"] and "not a base case" in res.calibration["mc_mean_fdv_note"]
    assert res.calibration["volume_terminal_median_usd_day_mc"] < res.calibration["volume_terminal_mean_usd_day_mc"]
    assert "not additive" in res.calibration["engine_percentiles_note"].lower()
    shares = res.calibration["engine_shares_on_median_total_path"]
    assert shares["clearinghouse"] + shares["confidential"] + shares["monetary"] == pytest.approx(shares["fdv_total"], rel=1e-9)
    # Zero sigmas collapse the Monte Carlo onto the deterministic path exactly (the drift correction vanishes).
    flat = {**inputs, "sigma_volume_monthly": 0.0, "sigma_price_monthly": 0.0, "confidential_sigma_multiplier": 1.0}
    sim0 = simulate_paths(flat, seed=SEED, n_paths=3)
    det = deterministic_sotp(inputs)
    assert np.allclose(sim0["fdv"], det["fdv_total"], rtol=1e-9)


def test_compound_issuance_matches_supply_physics_trajectory():
    from valuo.models.sotp_valuation import compound_issuance
    from valuo.models.supply_physics import trajectory

    path = [0.025 + (0.016 - 0.025) * min(t - 1, 24) / 24 for t in range(1, H + 1)]
    iss = compound_issuance(np.asarray(path), SUPPLY)
    tr = trajectory(REGIME_GLIDEPATH, path, SUPPLY, 1e8, 15.8, 0.35, PRICE, 0.0, 0.0)
    assert np.allclose(np.cumsum(iss), tr.gross_issuance_cum, rtol=1e-12)
    # Compounding issues more than the flat S0 x i / 12 approximation, and the SOTP uses the compounded path.
    assert iss.sum() > sum(SUPPLY * r / 12 for r in path)
    inputs, _, _ = _base_inputs()
    det = deterministic_sotp(inputs)
    assert det["cum_issuance_near"] == pytest.approx(compound_issuance(np.asarray(inputs["issuance_rate_path"]), SUPPLY).sum())


def test_build_inputs_missing_regime_and_state_lock_degrade_with_warnings():
    supply = _supply(regimes=[], trajectories=[], current_daily_sinks_near={"buyback": 1.0, "gas_burn": 10.0})
    inputs, cal, labeled = build_inputs(_truth(), _forensics(), _comps(), supply, A.ASSUMPTIONS, bench=_bench())
    assert inputs["state_lock_near_day"] == A.value("state_lock_growth_fallback_near_per_day")
    assert "state_lock_growth_fallback_near_per_day" in labeled
    assert inputs["supply_at_horizon"] is None
    glide = inputs["issuance_rate_paths"][REGIME_GLIDEPATH]
    assert glide[0] > glide[-1] and len(glide) == H
    assert sum("regime" in w for w in cal["warnings"]) >= 2 and any("state_lock" in w for w in cal["warnings"])
    with pytest.raises(ValueError, match="gas_burn"):
        build_inputs(_truth(), _forensics(), _comps(), _supply(current_daily_sinks_near={}), A.ASSUMPTIONS)


def test_build_inputs_capture_override_assumption():
    reg = A.with_overrides({"buyback_capture_ratio_override": 0.5})
    inputs, cal, labeled = build_inputs(_truth(), _forensics(), _comps(), _supply(), reg, bench=_bench())
    assert inputs["alpha_capture"] == 0.5 and cal["alpha_source"].startswith("assumption")
    assert labeled["alpha_capture"].source == "assumption"


# ----------------------------------------------------------------------------- Monte Carlo
def test_simulate_paths_deterministic_for_same_seed():
    inputs, _, _ = _base_inputs()
    a = simulate_paths(inputs, seed=SEED, n_paths=500)
    b = simulate_paths(inputs, seed=SEED, n_paths=500)
    for key in ("fdv", "e1", "e2", "e3", "running_fdv", "cum_rev", "v_pub", "price"):
        assert np.array_equal(a[key], b[key]), key
    for k in a["net_float_by_regime"]:
        assert np.array_equal(a["net_float_by_regime"][k], b["net_float_by_regime"][k])
    c = simulate_paths(inputs, seed=SEED + 1, n_paths=500)
    assert not np.array_equal(a["fdv"], c["fdv"])


def test_simulate_paths_engines_sum_to_total_per_path():
    inputs, _, _ = _base_inputs()
    sim = simulate_paths(inputs, seed=SEED, n_paths=1000)
    assert sim["fdv"].shape == (1000,) and sim["running_fdv"].shape == (1000, H)
    assert np.allclose(sim["e1"] + sim["e2"] + sim["e3"], sim["fdv"], rtol=1e-12, atol=0)
    assert np.all(sim["e1"] >= 0) and np.all(sim["e2"] >= 0) and np.all(sim["e3"] >= 0)
    assert np.all(np.isfinite(sim["fdv"]))


def test_zero_sigma_monte_carlo_collapses_onto_deterministic():
    inputs, _, _ = _base_inputs()
    inputs = {**inputs, "sigma_volume_monthly": 0.0, "sigma_price_monthly": 0.0}
    sim = simulate_paths(inputs, seed=SEED, n_paths=64)
    det = deterministic_sotp(inputs)
    assert np.allclose(sim["fdv"], det["fdv_total"], rtol=1e-10)
    assert np.allclose(sim["e1"], det["engine_clearinghouse"], rtol=1e-10)
    assert np.allclose(sim["e3"], det["engine_monetary"], rtol=1e-10)
    assert np.allclose(sim["net_float"][0], det["monthly_net_float_change_near"], rtol=1e-10)


def test_zero_volume_monte_carlo_zeroes_revenue_engines():
    inputs, _, _ = _base_inputs()
    inputs = {**inputs, "v_pub_usd_day": 0.0, "v_conf_usd_day": 0.0}
    sim = simulate_paths(inputs, seed=SEED, n_paths=200)
    assert np.all(sim["e1"] == 0.0) and np.all(sim["e2"] == 0.0)
    assert np.all(sim["cum_rev"] == 0.0)


# ----------------------------------------------------------------------------- run_sotp
@pytest.fixture(scope="module")
def sotp() -> SotpValuation:
    return run_sotp(_truth(), _forensics(), _comps(), _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=2000, bench=_bench())


def test_run_sotp_determinism(sotp: SotpValuation):
    again = run_sotp(_truth(), _forensics(), _comps(), _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=2000, bench=_bench())
    assert again.model_dump() == sotp.model_dump()
    assert np.array_equal(np.asarray(again.fan_chart["fdv_p50"]), np.asarray(sotp.fan_chart["fdv_p50"]))


def _monotone(d: dict[str, float]) -> bool:
    vals = [d[k] for k in PERCENTILE_KEYS]
    return all(a <= b for a, b in zip(vals, vals[1:], strict=False))


def test_run_sotp_percentiles_monotone_and_shapes(sotp: SotpValuation):
    assert sotp.seed == SEED and sotp.n_paths == 2000 and sotp.horizon_months == H
    assert _monotone(sotp.fdv_percentiles) and _monotone(sotp.price_percentiles) and _monotone(sotp.fdv_ex_monetary_percentiles)
    assert [e.key for e in sotp.engines] == ["clearinghouse", "confidential", "monetary"]
    for e in sotp.engines:
        assert e.p10 <= e.p25 <= e.p50 <= e.p75 <= e.p90
    assert sotp.engines[0].assumption_heavy is False and sotp.engines[1].assumption_heavy and sotp.engines[2].assumption_heavy
    for k in PERCENTILE_KEYS:
        assert len(sotp.fan_chart[f"fdv_{k}"]) == H and len(sotp.fan_chart[f"rev_{k}"]) == H
    for m in range(H):
        f = [sotp.fan_chart[f"fdv_{k}"][m] for k in PERCENTILE_KEYS]
        r = [sotp.fan_chart[f"rev_{k}"][m] for k in PERCENTILE_KEYS]
        assert f == sorted(f) and r == sorted(r)
    # cumulative revenue p50 is non-decreasing in time
    rev50 = sotp.fan_chart["rev_p50"]
    assert all(a <= b for a, b in zip(rev50, rev50[1:], strict=False))
    assert sotp.fdv_ex_monetary_percentiles["p50"] <= sotp.fdv_percentiles["p50"]


def test_run_sotp_price_percentiles_equal_fdv_over_supply(sotp: SotpValuation):
    supply_h = sotp.calibration["supply_at_horizon_used"]
    assert supply_h == sotp.calibration["supply_at_horizon_near"]
    traj = next(t for t in _supply().trajectories if t.regime == REGIME_GLIDEPATH)
    expected = SUPPLY + traj.gross_issuance_cum[-1] - traj.buyback_cum[-1] - traj.gas_burn_cum[-1] - traj.state_lock_cum[-1]
    assert supply_h == pytest.approx(expected)
    for k in PERCENTILE_KEYS:
        assert sotp.price_percentiles[k] == pytest.approx(sotp.fdv_percentiles[k] / supply_h)


def test_run_sotp_upside_and_current_fdv(sotp: SotpValuation):
    assert sotp.current_fdv_usd == pytest.approx(PRICE * SUPPLY)
    assert sotp.upside_p50_pct == pytest.approx((sotp.fdv_percentiles["p50"] / sotp.current_fdv_usd - 1) * 100)
    assert sotp.discount_rate == A.value("discount_rate")
    assert sotp.inputs["discount_rate"].source == "assumption"


def test_run_sotp_heatmap_shape_and_monotonicity(sotp: SotpValuation):
    hm = sotp.sensitivity_heatmap
    assert hm["x"] == list(HEATMAP_VOLUMES_USD) and hm["y"] == list(HEATMAP_NET_TAKE_BPS)
    fdv, defl = hm["fdv_p50"], hm["net_deflation"]
    assert len(fdv) == 5 and all(len(r) == 5 for r in fdv)
    assert len(defl) == 5 and all(len(r) == 5 and all(isinstance(c, bool) for c in r) for r in defl)
    for row in fdv:  # more volume -> more value
        assert all(a < b for a, b in zip(row, row[1:], strict=False))
    for j in range(5):  # higher take -> more value
        col = [fdv[i][j] for i in range(5)]
        assert all(a < b for a, b in zip(col, col[1:], strict=False))
    for i in range(5):  # deflation is monotone in volume and take
        assert all((not a) or b for a, b in zip(defl[i], defl[i][1:], strict=False))
    for j in range(5):
        col = [defl[i][j] for i in range(5)]
        assert all((not a) or b for a, b in zip(col, col[1:], strict=False))
    # $1.5B/day at 18 bps net = $2.7M/day of buybacks >> ~$380k/day of issuance: deflationary.
    assert defl[-1][-1] is True
    # $100M/day at 2 bps net = $20k/day: not deflationary.
    assert defl[0][0] is False
    # Cell value equals the deterministic function at the held-constant inputs.
    inputs, _, _ = _base_inputs()
    share = hm["confidential_share_used"]
    cell = {**inputs, "v_pub_usd_day": 5e8 * (1 - share), "v_conf_usd_day": 5e8 * share, "tau_pub_bps": 10.0, "tau_conf_bps": 10.0,
            "alpha_capture": 1.0, "tau_floor_bps": 10.0, "growth_monthly_pub": 0.0, "growth_monthly_conf": 0.0,
            "lambda_pub": 0.0, "lambda_conf": 0.0, "price_drift_annual": 0.0}
    assert fdv[2][2] == pytest.approx(deterministic_sotp(cell)["fdv_total"])


def test_run_sotp_crossover_distribution(sotp: SotpValuation):
    cd = sotp.crossover_month_distribution
    for regime in (REGIME_STATUS_QUO, REGIME_GLIDEPATH):
        d = cd[regime]
        assert 0.0 <= d[f"p_crossover_within_{H}m"] <= 1.0
        assert 0.0 <= d["p_deflationary_at_horizon"] <= 1.0
        if d["n_paths_crossed"]:
            assert 1 <= d["p10_month"] <= d["p50_month"] <= d["p90_month"] <= H
    # Lower issuance can only make crossover more likely.
    assert cd[REGIME_GLIDEPATH][f"p_crossover_within_{H}m"] >= cd[REGIME_STATUS_QUO][f"p_crossover_within_{H}m"]
    assert cd["deterministic_crossover_month"] == sotp.calibration["deterministic_base"]["crossover_month"]


def test_run_sotp_calibration_and_json_roundtrip(sotp: SotpValuation):
    cal = sotp.calibration
    assert cal["deterministic_base"]["fdv_total"] > 0
    assert cal["tau_pub_start_bps"] > cal["tau_floor_bps"] and len(cal["monthly_tau_pub_bps"]) == H
    assert cal["monthly_tau_pub_bps"][0] > cal["monthly_tau_pub_bps"][-1] >= cal["tau_floor_bps"]
    payload = json.loads(sotp.model_dump_json())
    assert payload["fdv_percentiles"]["p50"] == sotp.fdv_percentiles["p50"]
    assert isinstance(payload["sensitivity_heatmap"]["net_deflation"][0][0], bool)
    SotpValuation.model_validate(payload)


def test_run_sotp_median_path_is_close_to_deterministic_when_sigma_small():
    forensics = _forensics(volatility={"annualized_sigma": 0.01, "volume_monthly_sigma": 0.01})
    res = run_sotp(_truth(), forensics, _comps(), _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=4000, bench=_bench())
    det = res.calibration["deterministic_base"]["fdv_total"]
    assert res.fdv_percentiles["p50"] == pytest.approx(det, rel=0.02)
    assert res.fdv_percentiles["p10"] < res.fdv_percentiles["p90"]


def test_deterministic_svrn_target_override_rebuilds_issuance_path():
    inputs, _, _ = _base_inputs()
    assert inputs["svrn_target_inflation"] is None  # explicit path is used by default
    base = deterministic_sotp(inputs)
    assert base["issuance_rate_path_used"] == pytest.approx(inputs["issuance_rate_paths"][REGIME_GLIDEPATH])
    # Target = live rate -> flat status quo, identical to swapping in the status_quo path explicitly.
    stalemate = deterministic_sotp({**inputs, "svrn_target_inflation": inputs["max_inflation_rate"]})
    explicit = deterministic_sotp({**inputs, "issuance_rate_path": inputs["issuance_rate_paths"][REGIME_STATUS_QUO]})
    assert stalemate["issuance_rate_path_used"] == pytest.approx(explicit["issuance_rate_path_used"])
    assert stalemate["monthly_net_float_change_near"] == pytest.approx(explicit["monthly_net_float_change_near"])
    assert stalemate["fdv_total"] == pytest.approx(base["fdv_total"])  # issuance does not enter the cash-flow engines
    assert stalemate["net_float_change_cum_near"] > base["net_float_change_cum_near"]
    # The glidepath supply override shifts by exactly the extra issuance, so the per-token value is diluted.
    extra = stalemate["cum_issuance_near"] - base["cum_issuance_near"]
    assert extra > 0
    assert stalemate["supply_at_horizon_near"] == pytest.approx(base["supply_at_horizon_near"] + extra)
    assert stalemate["implied_price"] < base["implied_price"]
    assert explicit["supply_at_horizon_near"] == pytest.approx(inputs["supply_at_horizon"])  # explicit path: override untouched
    # Target = the registry glidepath reproduces the supply_physics path exactly (same 0-based formula).
    rebuilt = deterministic_sotp({**inputs, "svrn_target_inflation": A.value("svrn_target_inflation")})
    assert rebuilt["issuance_rate_path_used"] == pytest.approx(base["issuance_rate_path_used"])
    # A scalar path means a flat regime.
    flat = deterministic_sotp({**inputs, "issuance_rate_path": 0.025})
    assert flat["issuance_rate_path_used"] == [pytest.approx(0.025)] * H
    # The Monte Carlo valuation regime follows the same resolution.
    sim = simulate_paths({**inputs, "svrn_target_inflation": inputs["max_inflation_rate"]}, seed=SEED, n_paths=50)
    assert np.allclose(sim["net_float_by_regime"][REGIME_GLIDEPATH], sim["net_float_by_regime"][REGIME_STATUS_QUO])


def test_deterministic_accepts_bear_case_alias_names():
    inputs, _, _ = _base_inputs()
    aliased = dict(inputs)
    aliased["v_pub_daily_usd"] = aliased.pop("v_pub_usd_day")
    aliased["v_conf_daily_usd"] = aliased.pop("v_conf_usd_day")
    aliased["fee_compression_lambda_monthly"] = aliased.pop("lambda_pub")
    assert deterministic_sotp(aliased) == deterministic_sotp(inputs)
    assert deterministic_sotp(inputs)["supply_at_horizon_near"] == inputs["supply_at_horizon"]
    with pytest.raises(KeyError, match="v_pub_usd_day"):
        deterministic_sotp({k: v for k, v in inputs.items() if k != "v_pub_usd_day"})


def test_bear_case_integration_with_build_inputs():
    bear_case = pytest.importorskip("valuo.models.bear_case")
    inputs, cal, _ = _base_inputs()
    key_map = {"v_pub_daily_usd": "v_pub_usd_day", "v_conf_daily_usd": "v_conf_usd_day",
               "fee_compression_lambda_monthly": "lambda_pub"}
    live = {"net_take_bps": cal["net_take_start_bps"], "hhi_external": 1800.0, "headroom_cross_vm_bps": 1.0,
            "max_inflation_rate": 0.025, "volume_30d_usd": V_PUB_30D + V_CONF_30D, "record_30d_usd": 4.84e9,
            "confidential_tvl_usd": 144.42e6, "confidential_tvl_verified": False}
    base = deterministic_sotp(inputs)
    bc = bear_case.run_bear_case(inputs, base, live, key_map=key_map)
    assert bc.base_fdv_p50 == pytest.approx(base["fdv_total"])
    assert [s.key for s in bc.scenarios] == ["fee_race_to_zero", "governance_stalemate", "post_incentive_decay", "solver_cartelization"]
    by_key = {s.key: s for s in bc.scenarios}
    assert by_key["fee_race_to_zero"].drawdown_pct < -0.5
    assert by_key["post_incentive_decay"].drawdown_pct < -0.3
    assert by_key["solver_cartelization"].drawdown_pct < 0.0
    # Governance stalemate reaches the model through svrn_target_inflation: cash flows unchanged, float dilutes more.
    gs = by_key["governance_stalemate"]
    assert gs.sotp_fdv_p50 == pytest.approx(base["fdv_total"])
    assert "svrn_target_inflation" in gs.perturbations_applied
    assert bc.combined_worst_fdv <= min(s.sotp_fdv_p50 for s in bc.scenarios)


def test_run_sotp_bear_preset_lowers_p50():
    base = run_sotp(_truth(), _forensics(), _comps(), _supply(), A.ASSUMPTIONS, seed=SEED, n_paths=1500, bench=_bench())
    bear = run_sotp(_truth(), _forensics(), _comps(), _supply(), A.preset("bear"), seed=SEED, n_paths=1500, bench=_bench())
    bull = run_sotp(_truth(), _forensics(), _comps(), _supply(), A.preset("bull"), seed=SEED, n_paths=1500, bench=_bench())
    assert bear.fdv_percentiles["p50"] < base.fdv_percentiles["p50"] < bull.fdv_percentiles["p50"]
