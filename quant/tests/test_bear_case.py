"""Unit tests for valuo.models.bear_case against an injected deterministic SOTP stub.

The stub is linear in volume and take (revenue x multiple) and dilutes per-token value along the
inflation glidepath, so every scenario has a measurable effect without any network or the real
sotp_valuation module. All numbers here are synthetic test fixtures.
"""
from __future__ import annotations

import json
import re
from typing import Any

import pytest

from valuo import assumptions
from valuo import assumptions as A
from valuo.models import bear_case as bc
from valuo.schemas import BearCase, BearScenario

I0 = 0.025  # stub's current protocol inflation cap (the live value is read from `live` in production)

BASE_INPUTS: dict[str, Any] = {
    "v_pub_daily_usd": 78.0e6,
    "v_conf_daily_usd": 51.0e6,
    "tau_pub_bps": 5.6,
    "tau_conf_bps": 20.0,
    "alpha_capture": 1.0,
    "svrn_target_inflation": 0.016,
    "svrn_glidepath_months": 24,
    "fee_compression_lambda_monthly": 0.03,
    "headroom_cross_vm_bps": 1.0,
    "confidential_tvl_usd": 144.0e6,
    "hhi_external": 1800.0,
    "tau_floor_bps": 0.5,
    "total_supply_near": 1.31e9,
    "terminal_multiple": 30.0,
}

LIVE_CALM: dict[str, Any] = {
    "net_take_bps": 5.6,
    "hhi_external": 2400.0,  # deposit/caller concentration: context only, never the cartel trigger
    "hhi_solver": 1800.0,
    "solver_fills_attributed": 20,
    "sample_span_s": 7200.0,  # above solver_sample_min_span_s, so the HHI condition may be graded
    "headroom_cross_vm_bps": 1.0,
    "max_inflation_rate": 0.016,  # pretend the cut is enacted so no trigger fires
    "volume_30d_usd": 3.6e9,
    "record_30d_usd": 3.9e9,
    "confidential_tvl_usd": 144.0e6,
    "confidential_tvl_verified": False,
}

LIVE_NOW: dict[str, Any] = {**LIVE_CALM, "max_inflation_rate": 0.025}


def _supply_at_horizon(inputs: dict[str, Any], horizon: int = 36) -> float:
    supply = float(inputs["total_supply_near"])
    terminal = float(inputs["svrn_target_inflation"])
    glide = float(inputs["svrn_glidepath_months"])
    for m in range(1, horizon + 1):
        frac = 1.0 if glide <= 0 else min(m, glide) / glide
        supply *= 1.0 + (I0 + (terminal - I0) * frac) / 12.0
    return supply


def stub_sotp(inputs: dict[str, Any]) -> dict[str, Any]:
    """FDV = daily holder revenue x 365.25 x multiple; price = FDV / horizon supply."""
    rev_daily = (inputs["v_pub_daily_usd"] * inputs["tau_pub_bps"] + inputs["v_conf_daily_usd"] * inputs["tau_conf_bps"]) / 1e4
    rev_daily *= inputs["alpha_capture"]
    fdv = rev_daily * 365.25 * inputs["terminal_multiple"]
    supply = _supply_at_horizon(inputs)
    return {"fdv_total": fdv, "implied_price": fdv / supply, "supply_at_horizon_near": supply, "crossover_month": None}


def stub_sotp_minimal(inputs: dict[str, Any]) -> dict[str, Any]:
    """Same math, but only the two required result keys (exercises the crossover fallback)."""
    full = stub_sotp(inputs)
    return {"fdv_total": full["fdv_total"], "implied_price": full["implied_price"]}


def _run(live: dict[str, Any] = LIVE_NOW, inputs: dict[str, Any] = BASE_INPUTS, fn=stub_sotp, **kw: Any) -> BearCase:
    return bc.run_bear_case(inputs, fn(inputs), live, sotp_fn=fn, **kw)


def _by_key(case: BearCase) -> dict[str, BearScenario]:
    return {s.key: s for s in case.scenarios}


# ----------------------------------------------------------------------------- structure
def test_four_scenarios_in_order_and_schema_validates():
    case = _run()
    assert [s.key for s in case.scenarios] == list(bc.SCENARIO_KEYS)
    assert BearCase.model_validate(case.model_dump()) == case
    assert BearCase.model_validate_json(case.model_dump_json()).model_dump() == case.model_dump()
    assert case.base_fdv_p50 == pytest.approx(stub_sotp(BASE_INPUTS)["fdv_total"])
    for s in case.scenarios:
        assert s.title and len(s.narrative) > 80
        assert s.monitor_source.startswith("https://")
        assert s.perturbations and all(isinstance(v, float) for v in s.perturbations.values())


# ----------------------------------------------------------------------------- drawdowns
def test_cash_flow_scenarios_reduce_fdv_and_every_scenario_reduces_price():
    case = _run()
    by = _by_key(case)
    base_price = case.model_dump()["base_price_p50"]
    for key in ("fee_race_to_zero", "post_incentive_decay", "solver_cartelization"):
        assert by[key].sotp_fdv_p50 < case.base_fdv_p50, key
        assert by[key].drawdown_pct < 0, key
    # Governance stalemate does not touch cash flows: FDV holds, per-token value falls through dilution.
    gov = by["governance_stalemate"]
    assert gov.sotp_fdv_p50 <= case.base_fdv_p50
    assert gov.drawdown_pct == pytest.approx(0.0)
    assert gov.model_dump()["price_drawdown_pct"] < 0
    for s in case.scenarios:
        assert s.price_p50 < base_price, s.key
        assert s.drawdown_pct == pytest.approx(s.sotp_fdv_p50 / case.base_fdv_p50 - 1.0)


def test_fee_race_drawdown_matches_linear_stub_exactly():
    case = _run()
    s = _by_key(case)["fee_race_to_zero"]
    expected = stub_sotp({**BASE_INPUTS, "tau_pub_bps": 0.01, "tau_conf_bps": 5.0})["fdv_total"]
    assert s.sotp_fdv_p50 == pytest.approx(expected)
    assert s.drawdown_pct == pytest.approx(expected / case.base_fdv_p50 - 1.0)
    assert s.drawdown_pct < -0.70  # a 1-pip public take wipes out most of the revenue base


def test_combined_worst_is_at_most_the_worst_single_scenario():
    case = _run()
    worst_single = min(s.sotp_fdv_p50 for s in case.scenarios)
    assert case.combined_worst_fdv <= worst_single
    assert case.combined_drawdown_pct <= min(s.drawdown_pct for s in case.scenarios)
    assert case.combined_drawdown_pct == pytest.approx(case.combined_worst_fdv / case.base_fdv_p50 - 1.0)
    dumped = case.model_dump()
    assert dumped["combined_worst_price"] < dumped["base_price_p50"]
    assert dumped["combined_price_drawdown_pct"] < dumped["combined_drawdown_pct"]  # dilution adds to the cash-flow hit


# ----------------------------------------------------------------------------- perturbation values
def test_perturbation_values_follow_model_design_4_3():
    case = _run()
    by = _by_key(case)
    assert by["fee_race_to_zero"].perturbations["tau_pub_bps"] == pytest.approx(0.01)
    assert by["fee_race_to_zero"].perturbations["tau_conf_bps"] == pytest.approx(5.0)
    assert "alpha_capture" not in by["fee_race_to_zero"].perturbations
    assert by["governance_stalemate"].perturbations == {"svrn_target_inflation": pytest.approx(0.025)}
    decay = by["post_incentive_decay"].perturbations
    assert decay["v_pub_daily_usd"] == pytest.approx(BASE_INPUTS["v_pub_daily_usd"] * 0.4)
    assert decay["v_conf_daily_usd"] == pytest.approx(BASE_INPUTS["v_conf_daily_usd"] * 0.3)
    assert decay["confidential_tvl_usd"] == pytest.approx(BASE_INPUTS["confidential_tvl_usd"] * 0.3)
    cartel = by["solver_cartelization"].perturbations
    assert cartel["hhi_external"] == pytest.approx(3500.0)
    assert cartel["headroom_cross_vm_bps"] == pytest.approx(-2.0)
    assert cartel["tau_pub_bps"] == pytest.approx(BASE_INPUTS["tau_pub_bps"] - 2.0)
    assert cartel["fee_compression_lambda_monthly"] == pytest.approx(assumptions.get("fee_compression_lambda_monthly").high)


def test_cartel_take_giveback_is_floored():
    inputs = {**BASE_INPUTS, "tau_pub_bps": 1.2}
    pert = bc.build_perturbations(inputs, LIVE_NOW)
    assert pert["solver_cartelization"]["tau_pub_bps"] == pytest.approx(0.5)


def test_merge_worst_picks_harmful_direction_on_collision():
    merged = bc.merge_worst({
        "fee_race_to_zero": {"tau_pub_bps": 0.01, "hhi_external": 1000.0},
        "solver_cartelization": {"tau_pub_bps": 3.6, "hhi_external": 3500.0},
    })
    assert merged == {"tau_pub_bps": 0.01, "hhi_external": 3500.0}


def test_stress_parameters_are_labeled_assumptions_and_attached():
    for a in bc.STRESS_PARAMETERS.values():
        assert a.source == "assumption" and a.low <= a.value <= a.high and len(a.justification) > 30, a.key
    case = _run()
    attached = {a["key"] for a in case.model_dump()["stress_parameters"]}
    assert attached == set(bc.STRESS_PARAMETERS)


# ----------------------------------------------------------------------------- triggers
@pytest.mark.parametrize(
    ("live_override", "scenario", "breached"),
    [
        ({"hhi_solver": 4000.0}, "solver_cartelization", True),
        ({"hhi_solver": 3500.0}, "solver_cartelization", False),  # strict >
        ({"hhi_solver": 1200.0, "headroom_cross_vm_bps": 1.0}, "solver_cartelization", False),
        ({"hhi_solver": 1200.0, "headroom_cross_vm_bps": -0.5}, "solver_cartelization", True),  # secondary condition
        ({"hhi_external": 9000.0}, "solver_cartelization", False),  # deposit HHI cannot fire the solver trigger
        ({"net_take_bps": 2.5}, "fee_race_to_zero", True),
        ({"net_take_bps": 5.6}, "fee_race_to_zero", False),
        ({"max_inflation_rate": 0.025}, "governance_stalemate", True),
        ({"max_inflation_rate": 0.016}, "governance_stalemate", False),
        ({"volume_30d_usd": 1.9e9, "record_30d_usd": 3.9e9}, "post_incentive_decay", True),
        ({"volume_30d_usd": 3.5e9, "record_30d_usd": 3.9e9}, "post_incentive_decay", False),
    ],
)
def test_trigger_logic(live_override: dict[str, Any], scenario: str, breached: bool):
    case = _run({**LIVE_CALM, **live_override})
    s = _by_key(case)[scenario]
    assert s.trigger_breached is breached, (scenario, s.current_value, s.trigger_threshold)


def test_trigger_metrics_thresholds_and_sources():
    case = _run(LIVE_NOW)
    by = _by_key(case)
    fee = by["fee_race_to_zero"]
    assert fee.early_warning_metric == "net_take_bps_30d" and fee.trigger_threshold == 3.0 and fee.current_value == 5.6
    assert "llama.fi" in fee.monitor_source
    gov = by["governance_stalemate"]
    assert gov.early_warning_metric == "max_inflation_rate"
    assert gov.trigger_threshold == pytest.approx(0.016) and gov.current_value == pytest.approx(0.025)
    assert "fastnear" in gov.monitor_source
    decay = by["post_incentive_decay"]
    assert decay.trigger_threshold == -0.40 and decay.current_value == pytest.approx(3.6e9 / 3.9e9 - 1)
    assert "nearstats" in decay.monitor_source
    cartel = by["solver_cartelization"]
    assert cartel.early_warning_metric == "hhi_solver" and cartel.trigger_threshold == 3500.0 and cartel.current_value == 1800.0
    assert "nearblocks" in cartel.monitor_source and "execute_intents" in (cartel.monitor_field or "")
    assert cartel.model_dump()["secondary_value"] == 1.0 and cartel.model_dump()["hhi_deposit_source_external"] == 2400.0
    dumped = case.model_dump()
    assert dumped["triggers_breached"] == 1 and dumped["triggers_evaluated"] == 4 and dumped["triggers_unevaluated"] == []  # only governance is live
    assert dumped["value_basis"] == "deterministic at median inputs; not a Monte Carlo percentile"


def test_missing_live_values_are_null_not_false_and_never_invent_numbers():
    live = {k: None for k in LIVE_NOW} | {"max_inflation_rate": 0.025, "confidential_tvl_verified": False}
    case = _run(live)
    by = _by_key(case)
    for key in ("fee_race_to_zero", "post_incentive_decay", "solver_cartelization"):
        assert by[key].trigger_breached is None, key  # not measured -> null, never "not breached"
        assert by[key].trigger_evaluated is False and by[key].current_value is None
        assert "unmeasured" in by[key].model_dump()["trigger_note"]
    cartel = by["solver_cartelization"].model_dump()
    assert cartel["secondary_breached"] is None and cartel["secondary_evaluated"] is False
    assert "n/a" in by["fee_race_to_zero"].narrative
    assert by["governance_stalemate"].trigger_breached is True
    dumped = case.model_dump()
    assert dumped["triggers_breached"] == 1 and dumped["triggers_evaluated"] == 1
    assert set(dumped["triggers_unevaluated"]) == {"fee_race_to_zero", "post_incentive_decay", "solver_cartelization"}
    assert "not measured" in case.falsification_summary and "not breached" not in case.falsification_summary
    # JSON carries null, and the schema round-trips it.
    raw = json.loads(case.model_dump_json())
    assert raw["scenarios"][0]["trigger_breached"] is None
    assert BearCase.model_validate(raw).scenarios[0].trigger_breached is None


def test_governance_requires_live_inflation_cap():
    live = {**LIVE_NOW, "max_inflation_rate": None}
    inputs = {k: v for k, v in BASE_INPUTS.items() if k != "max_inflation_rate"}
    with pytest.raises(ValueError, match="max_inflation_rate"):
        bc.run_bear_case(inputs, stub_sotp(inputs), live, sotp_fn=stub_sotp)


# ----------------------------------------------------------------------------- summary & narratives
_BUZZWORDS = re.compile(r"\b(revolutioni[sz]e|delve|seamless|unlock(?:s|ing)?|leverag(?:e|es|ing)|game.changing|paradigm)\b", re.I)


def test_summary_mentions_each_scenario_key_and_is_three_to_five_sentences():
    case = _run()
    text = case.falsification_summary
    for key in bc.SCENARIO_KEYS:
        assert key in text, key
    sentences = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Za-z_])", text) if s.strip()]
    assert 3 <= len(sentences) <= 5, sentences
    assert "BREACHED" in text and "not breached" in text
    assert not _BUZZWORDS.search(text)
    for s in case.scenarios:
        assert not _BUZZWORDS.search(s.narrative), s.key
        assert re.search(r"\d", s.narrative)


def test_narratives_quote_the_model_numbers():
    case = _run()
    by = _by_key(case)
    fee = by["fee_race_to_zero"]
    assert "5.6 bps" in fee.narrative and "0.01 bps" in fee.narrative and "5 bps" in fee.narrative
    gov = by["governance_stalemate"]
    assert "2.50%" in gov.narrative and "1.60%" in gov.narrative
    cartel = by["solver_cartelization"]
    assert "3,500" in cartel.narrative and "-2 bps" in cartel.narrative


# ----------------------------------------------------------------------------- key resolution & fallbacks
def test_alias_resolution_and_key_map():
    renamed = {
        "public_daily_volume_usd": BASE_INPUTS["v_pub_daily_usd"],
        "confidential_daily_volume_usd": BASE_INPUTS["v_conf_daily_usd"],
        "net_take_bps": BASE_INPUTS["tau_pub_bps"],
        "confidential_take_bps": BASE_INPUTS["tau_conf_bps"],
        "capture_ratio": 1.0,
        "inflation_terminal_annual": 0.016,
        "glidepath_months": 24,
        "weird_lambda": 0.03,
        "total_supply_near": BASE_INPUTS["total_supply_near"],
        "terminal_multiple": 30.0,
    }

    def fn(i: dict[str, Any]) -> dict[str, Any]:
        canon = {
            "v_pub_daily_usd": i["public_daily_volume_usd"], "v_conf_daily_usd": i["confidential_daily_volume_usd"],
            "tau_pub_bps": i["net_take_bps"], "tau_conf_bps": i["confidential_take_bps"], "alpha_capture": i["capture_ratio"],
            "svrn_target_inflation": i["inflation_terminal_annual"], "svrn_glidepath_months": i["glidepath_months"],
            "total_supply_near": i["total_supply_near"], "terminal_multiple": i["terminal_multiple"],
        }
        return stub_sotp(canon)

    case = bc.run_bear_case(renamed, fn(renamed), LIVE_NOW, sotp_fn=fn, key_map={"fee_compression_lambda_monthly": "weird_lambda"})
    by = _by_key(case)
    assert by["fee_race_to_zero"].sotp_fdv_p50 < case.base_fdv_p50
    cartel = by["solver_cartelization"].model_dump()
    assert cartel["perturbations_applied"]["fee_compression_lambda_monthly"] == "weird_lambda"
    assert set(cartel["perturbations_unapplied"]) == {"hhi_external", "headroom_cross_vm_bps"}


def test_missing_required_input_raises_with_guidance():
    inputs = {k: v for k, v in BASE_INPUTS.items() if k != "tau_conf_bps"}
    with pytest.raises(KeyError, match="tau_conf_bps"):
        bc.run_bear_case(inputs, stub_sotp(BASE_INPUTS), LIVE_NOW, sotp_fn=stub_sotp)


def test_result_without_fdv_raises():
    with pytest.raises(KeyError, match="fdv_total"):
        bc.run_bear_case(BASE_INPUTS, {"implied_price": 1.0}, LIVE_NOW, sotp_fn=stub_sotp)


def test_crossover_fallback_from_supply_ctx():
    supply_ctx = {
        "total_supply_near": 1.31e9, "price_usd": 4.0, "gas_burn_near_per_day": 1_000.0,
        "state_lock_near_per_day": 400.0, "max_inflation_rate": 0.025, "horizon_months": 36,
    }
    # Sinks: (78e6*5.6 + 51e6*20)/1e4/4 = 36,420 NEAR/day buyback + 1,400 = 37,820 vs issuance 89,700/day -> no crossover.
    assert bc.estimate_crossover_month(BASE_INPUTS, supply_ctx) is None
    # Push the take to a level where the glidepath crosses before the horizon, and check the month is the first one.
    hot = {**BASE_INPUTS, "tau_pub_bps": 12.0, "tau_conf_bps": 40.0}
    m = bc.estimate_crossover_month(hot, supply_ctx)
    assert m is not None and 1 <= m <= 36
    assert bc.estimate_crossover_month(hot, {**supply_ctx, "max_inflation_rate": 0.05}) in (None, *range(m, 37))
    assert bc.estimate_crossover_month(hot, {"price_usd": 4.0}) is None  # incomplete context -> None, never a guess

    case = bc.run_bear_case(hot, stub_sotp_minimal(hot), LIVE_NOW, sotp_fn=stub_sotp_minimal, supply_ctx=supply_ctx)
    by = _by_key(case)
    assert case.model_dump()["base_crossover_month"] == m
    assert by["governance_stalemate"].crossover_month is None  # 2.5% forever never crosses at these sinks
    assert by["governance_stalemate"].model_dump()["crossover_source"] == "bear_case.estimate_crossover_month"
    case_no_ctx = bc.run_bear_case(hot, stub_sotp_minimal(hot), LIVE_NOW, sotp_fn=stub_sotp_minimal)
    assert all(s.crossover_month is None for s in case_no_ctx.scenarios)


def test_crossover_from_sotp_result_is_preferred():
    def fn(i: dict[str, Any]) -> dict[str, Any]:
        return {**stub_sotp(i), "crossover_month": 7 if i["svrn_target_inflation"] < 0.02 else None}

    case = bc.run_bear_case(BASE_INPUTS, fn(BASE_INPUTS), LIVE_NOW, sotp_fn=fn, supply_ctx={"total_supply_near": 1.31e9, "price_usd": 4.0, "max_inflation_rate": 0.025})
    by = _by_key(case)
    assert by["fee_race_to_zero"].crossover_month == 7
    assert by["governance_stalemate"].crossover_month is None
    assert by["fee_race_to_zero"].model_dump()["crossover_source"] == "deterministic_sotp"


# ----------------------------------------------------------------------------- determinism & helper
def test_deterministic_repeat_runs_are_identical():
    a = _run().model_dump()
    b = _run().model_dump()
    assert a == b


def test_live_metrics_helper_reads_collector_shapes():
    forensics = {
        "fees": {"net_take_bps": 5.59, "gross_take_bps": 15.8},
        "volume": {"30d": 3.893e9, "records": {"max30dUsd": 3.95e9}},
        "hhi_external": 2100.0, "confidential_tvl_usd": 144.42e6, "confidential_tvl_verified": False,
        "caller_sample": {"hhi_external_ex_ai_agent": 1450.0, "external_receipts_sampled": 23, "sample_span_s": 51.0},
    }
    truth = {"max_inflation_rate": 0.025}
    bench = {"headroom_by_archetype_bps": {"cross_vm": 1.0, "evm_l2": -1.0}}
    forensics["solver_concentration"] = {"hhi_solver": 1900.0, "n_eff_solver": 10_000 / 1900.0, "n_fills_attributed": 14, "n_fills": 9}
    live = bc.live_metrics(forensics, truth, bench)
    assert live == {
        "net_take_bps": 5.59, "hhi_solver": 1900.0, "hhi_solver_ci90": None, "n_eff_solver": pytest.approx(10_000 / 1900.0), "solver_fills_attributed": 14,
        "solver_fills_sampled": 9, "hhi_external": 2100.0, "hhi_external_ex_ai_agent": 1450.0, "external_receipts_sampled": 23,
        "sample_span_s": 51.0, "headroom_cross_vm_bps": 1.0, "max_inflation_rate": 0.025, "volume_30d_usd": 3.893e9,
        "record_30d_usd": 3.95e9, "confidential_tvl_usd": 144.42e6, "confidential_tvl_verified": False,
    }
    empty = bc.live_metrics({}, {}, None)
    assert empty["headroom_cross_vm_bps"] is None and empty["hhi_external_ex_ai_agent"] is None and empty["hhi_solver"] is None


def test_cartel_trigger_reads_solver_population_not_deposit_callers():
    # Deposit/caller concentration can be extreme (one bridge contract, one AI escrow) without any solver concentration;
    # the trigger must read HHI_solver and keep the deposit figure in the note for context only.
    live = {**LIVE_CALM, "hhi_external": 3989.0, "hhi_external_ex_ai_agent": 3600.0, "hhi_solver": 1250.0, "solver_fills_attributed": 18}
    s = _by_key(_run(live))["solver_cartelization"]
    assert s.early_warning_metric == "hhi_solver" and s.current_value == 1250.0 and s.trigger_breached is False
    assert s.trigger_evaluated is True and "3,989" in s.model_dump()["trigger_note"] and "3,989" in s.narrative
    # Solver HHI above the threshold with a graded sample breaches.
    s2 = _by_key(_run({**LIVE_CALM, "hhi_solver": 3989.0, "solver_fills_attributed": 18}))["solver_cartelization"]
    assert s2.trigger_breached is True
    # Too few parsed fills: HHI is noise -> not measured (null), even when the number itself is above 3,500.
    s3 = _by_key(_run({**LIVE_CALM, "hhi_solver": 5000.0, "solver_fills_attributed": 4, "headroom_cross_vm_bps": None}))["solver_cartelization"]
    assert s3.trigger_breached is None and s3.trigger_evaluated is False and "too thin" in s3.model_dump()["trigger_note"]
    # Thin HHI but a measured negative headroom: the secondary condition decides and the trigger is measured.
    s4 = _by_key(_run({**LIVE_CALM, "hhi_solver": 5000.0, "solver_fills_attributed": 4, "headroom_cross_vm_bps": -0.3}))["solver_cartelization"]
    assert s4.trigger_breached is True and s4.trigger_evaluated is True
    # No solver HHI at all -> not measured, with the deposit HHI quoted as context.
    s5 = _by_key(_run({**LIVE_CALM, "hhi_solver": None, "solver_fills_attributed": None, "headroom_cross_vm_bps": None}))["solver_cartelization"]
    assert s5.trigger_breached is None and "deposit-source HHI" in s5.model_dump()["trigger_note"]


def test_cartel_rule_is_asymmetric_unmeasured_hhi_with_clear_headroom_is_not_a_clear():
    # A NearBlocks 429 run: hhi_solver null while the quote race measured a non-negative headroom. The headroom alone
    # cannot clear the trigger (only the primary HHI_solver can), so the row is "not measured", not "not breached".
    s = _by_key(_run({**LIVE_CALM, "hhi_solver": None, "solver_fills_attributed": None, "headroom_cross_vm_bps": 1.08}))["solver_cartelization"]
    d = s.model_dump()
    assert s.trigger_breached is None and s.trigger_evaluated is False and s.current_value is None
    assert d["secondary_evaluated"] is True and d["secondary_breached"] is False
    assert "trigger_breached null" in d["trigger_note"] and "+1.08 bps" in d["trigger_note"]
    # Thin HHI (above the threshold, too few fills) with a non-negative headroom: likewise not measured.
    s2 = _by_key(_run({**LIVE_CALM, "hhi_solver": 5000.0, "solver_fills_attributed": 5, "headroom_cross_vm_bps": 1.08}))["solver_cartelization"]
    assert s2.trigger_breached is None and s2.trigger_evaluated is False and "too thin" in s2.model_dump()["trigger_note"]
    # The unevaluated row is excluded from the "x of y" count and the summary says "not measured".
    case = _run({**LIVE_NOW, "hhi_solver": None, "solver_fills_attributed": None, "headroom_cross_vm_bps": 1.08})
    dumped = case.model_dump()
    assert dumped["triggers_evaluated"] == 3 and dumped["triggers_unevaluated"] == ["solver_cartelization"]
    assert "not measured" in case.falsification_summary
    # A graded primary with a measured, non-negative headroom is a genuine clear and carries no null sentence.
    s3 = _by_key(_run(LIVE_CALM))["solver_cartelization"]
    assert s3.trigger_breached is False and s3.trigger_evaluated is True and "trigger_breached null" not in s3.model_dump()["trigger_note"]
    # A graded primary breached by the secondary alone says so.
    s4 = _by_key(_run({**LIVE_CALM, "hhi_solver": None, "solver_fills_attributed": None, "headroom_cross_vm_bps": -0.3}))["solver_cartelization"]
    assert s4.trigger_breached is True and "secondary condition alone" in s4.model_dump()["trigger_note"]


def test_thin_solver_sample_is_flagged_on_graded_rows_only():
    # Graded (>= MIN_SOLVER_FILLS_FOR_TRIGGER participations) but resting on few sampled fills: flagged, still graded.
    thin = _by_key(_run({**LIVE_CALM, "hhi_solver": 3200.0, "solver_fills_attributed": 10, "solver_fills_sampled": 8}))["solver_cartelization"]
    d = thin.model_dump()
    assert thin.trigger_breached is False and d["sample_thin"] is True and d["solver_fills_sampled"] == 8
    assert "thin sample: 8 fills" in d["trigger_note"]
    # A well-sampled run is not flagged.
    full = _by_key(_run({**LIVE_CALM, "solver_fills_attributed": 40, "solver_fills_sampled": bc.THIN_SOLVER_SAMPLE_FILLS}))["solver_cartelization"]
    assert full.model_dump()["sample_thin"] is False and "thin sample" not in (full.model_dump()["trigger_note"] or "")
    # An unmeasured primary is not "thin": it is not graded at all.
    unmeasured = _by_key(_run({**LIVE_CALM, "hhi_solver": None, "solver_fills_attributed": None, "solver_fills_sampled": 3, "headroom_cross_vm_bps": None}))["solver_cartelization"]
    assert unmeasured.model_dump()["sample_thin"] is False and unmeasured.trigger_breached is None


def test_cartel_trigger_is_graded_on_the_bootstrap_ci():
    # Point below the threshold but the 90% CI reaches above it: inconclusive -> not measured (null), never "not breached".
    base = {**LIVE_CALM, "hhi_solver": 3000.0, "solver_fills_attributed": 34, "solver_fills_sampled": 32, "headroom_cross_vm_bps": 1.0}
    s = _by_key(_run({**base, "hhi_solver_ci90": [2400.0, 3900.0]}))["solver_cartelization"]
    d = s.model_dump()
    assert s.trigger_breached is None and s.trigger_evaluated is False
    assert d["primary_status"] == "inconclusive" and d["trigger_status"] == "inconclusive" and d["hhi_solver_ci90"] == [2400.0, 3900.0]
    assert "inconclusive" in d["trigger_note"] and "[2,400, 3,900]" in d["trigger_note"] and "CI" in s.narrative
    # Upper bound below the threshold: a clear.
    clear = _by_key(_run({**base, "hhi_solver_ci90": [2400.0, 3400.0]}))["solver_cartelization"].model_dump()
    assert clear["trigger_breached"] is False and clear["primary_status"] == "clear" and clear["trigger_status"] == "not_breached"
    # Lower bound above the threshold: breached, even though a point-graded thin flag would not apply (CI carries the noise).
    hot = _by_key(_run({**base, "hhi_solver": 5761.0, "hhi_solver_ci90": [4521.0, 7285.0], "solver_fills_sampled": 12}))["solver_cartelization"].model_dump()
    assert hot["trigger_breached"] is True and hot["primary_status"] == "breached" and hot["sample_thin"] is False
    # Inconclusive HHI with a negative headroom: the secondary condition still breaches.
    sec = _by_key(_run({**base, "hhi_solver_ci90": [2400.0, 3900.0], "headroom_cross_vm_bps": -0.4}))["solver_cartelization"].model_dump()
    assert sec["trigger_breached"] is True and "secondary condition alone" in sec["trigger_note"] and "inconclusive" in sec["trigger_note"]
    # Too few participations: thin wins over any CI.
    thin = _by_key(_run({**base, "solver_fills_attributed": 4, "hhi_solver_ci90": [5000.0, 10000.0]}))["solver_cartelization"].model_dump()
    assert thin["trigger_breached"] is None and thin["primary_status"] == "thin"
    # Malformed CI is ignored (point grading).
    bad = _by_key(_run({**base, "hhi_solver_ci90": [3900.0, 2400.0]}))["solver_cartelization"].model_dump()
    assert bad["hhi_solver_ci90"] is None and bad["trigger_breached"] is False


def test_cartel_trigger_needs_minimum_solver_sample_span():
    min_span = A.value("solver_sample_min_span_s")
    assert min_span == 3600.0 and A.get("solver_sample_min_span_s").low == 900.0 and A.get("solver_sample_min_span_s").high == 86400.0
    base = {**LIVE_CALM, "hhi_solver": 2900.0, "hhi_solver_ci90": [2200.0, 3300.0], "solver_fills_attributed": 60,
            "solver_fills_sampled": 40, "headroom_cross_vm_bps": 1.0}
    # A 2-minute window with a CI entirely below the threshold: still inconclusive, never "not breached".
    short = _by_key(_run({**base, "sample_span_s": 120.0}))["solver_cartelization"]
    d = short.model_dump()
    assert short.trigger_breached is None and short.trigger_evaluated is False
    assert d["trigger_status"] == "inconclusive" and d["primary_status"] == "short_span" and d["span_sufficient"] is False
    assert d["sample_span_s"] == 120.0 and d["min_sample_span_s"] == min_span
    note = d["trigger_note"]
    assert "120 s" in note and "3,600 s" in note and "2,900" in note and "[2,200, 3,300]" in note and "below" in note
    assert "120 s" in short.narrative and "inconclusive" in short.narrative
    # Same window with a CI above the threshold: also inconclusive (the rule cuts both ways).
    hot = _by_key(_run({**base, "sample_span_s": 120.0, "hhi_solver": 6000.0, "hhi_solver_ci90": [4800.0, 7200.0]}))["solver_cartelization"].model_dump()
    assert hot["trigger_breached"] is None and hot["trigger_status"] == "inconclusive" and "above" in hot["trigger_note"]
    # Unknown span: not graded either.
    unknown = _by_key(_run({**base, "sample_span_s": None}))["solver_cartelization"].model_dump()
    assert unknown["trigger_status"] == "inconclusive" and "unknown span" in unknown["trigger_note"]
    # The headroom condition can still breach on its own.
    sec = _by_key(_run({**base, "sample_span_s": 120.0, "headroom_cross_vm_bps": -0.5}))["solver_cartelization"].model_dump()
    assert sec["trigger_breached"] is True and sec["trigger_status"] == "breached" and "secondary condition alone" in sec["trigger_note"]
    # At or above the minimum the CI grades as before.
    ok = _by_key(_run({**base, "sample_span_s": min_span}))["solver_cartelization"].model_dump()
    assert ok["trigger_breached"] is False and ok["trigger_status"] == "not_breached" and ok["span_sufficient"] is True
    # Unevaluated row is excluded from the x-of-y count.
    case = _run({**LIVE_NOW, **{k: v for k, v in base.items() if k != "max_inflation_rate"}, "sample_span_s": 120.0})
    assert "solver_cartelization" in case.model_dump()["triggers_unevaluated"]
