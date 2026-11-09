"""Steel-manned bear case: four falsification scenarios run through the deterministic SOTP.

The thesis is only worth anything if we can state the conditions under which it is wrong. Each
scenario below is a perturbation of the deterministic SOTP inputs (MODEL_DESIGN section 4.3),
re-priced with the same pure function the heatmap uses, and paired with one live, weekly-checkable
early-warning metric. Nothing here touches the network; ``live`` carries the already-collected
values and a ``None`` for anything the collectors could not measure.

Definitions
-----------
``sotp_fdv_p50``            = the DETERMINISTIC (median-input) FDV of the scenario, i.e. deterministic_sotp
                              at perturbed inputs. It is NOT the Monte Carlo P50 (which is ~2x larger at the
                              measured sigmas). When ``mc_fn`` is supplied the true MC median is attached as
                              ``mc_fdv_p50`` / ``mc_drawdown_pct`` so both bases are side by side.
``drawdown_pct``            = fdv_scenario / fdv_base - 1              (signed fraction; -0.5 = -50%)
``trigger_evaluated``       = False when the live metric was not measured this run (or the sample is too thin
                              to grade); ``trigger_breached`` is then ``None`` (null in JSON), the memo prints
                              "not measured", never "not breached", and the row is excluded from the "x of y"
                              count. ``BearCase.value_basis`` states that every FDV here is deterministic.
                              solver_cartelization combines two conditions asymmetrically: a breach on either
                              measured condition (HHI_solver > threshold, cross-VM headroom < 0) is a breach; a
                              clear requires the primary HHI_solver to have been graded; an unmeasured or thin
                              HHI_solver with a non-negative (or unmeasured) headroom is ``None``, not a clear.
                              ``sample_thin`` flags a point-graded HHI_solver that rests on fewer than
                              ``THIN_SOLVER_SAMPLE_FILLS`` sampled fills; the memo and scorecard repeat the caveat.
                              When the forensics carry a bootstrap ``hhi_solver_ci90`` the HHI condition is graded
                              on the interval: breached iff lower bound > threshold, clear iff upper bound <
                              threshold, else ``primary_status = "inconclusive"`` (treated like unmeasured: the
                              row is null unless the headroom condition breaches). The HHI condition is also left
                              ungraded (``primary_status = "short_span"``, ``trigger_status = "inconclusive"``) when
                              the solver sample spans less than ``solver_sample_min_span_s`` (registry, 3,600 s):
                              a window of minutes is serially correlated and its CI covers within-window noise only.
                              ``trigger_status`` on the row is "breached" | "not_breached" | "inconclusive" | "not_measured".
``price_drawdown_pct``      = price_scenario / price_base - 1          (extra field; equals the FDV
                              drawdown unless the scenario changes the horizon supply)
``combined_worst``          = every scenario's perturbation applied at once; on a key collision the
                              value that is worse for the thesis wins (lower take/volume, higher
                              inflation/HHI/compression).
``crossover_month``         = first month m in 1..H with issuance_m <= sinks_m, where
                              issuance_m = S_{m-1} * i_m * d, sinks_m = (buyback + gas_burn + state_lock) * d,
                              buyback = (V_pub*tau_pub + V_conf*tau_conf)/1e4 * alpha / P, d = 365.25/12 days,
                              i_m linear from the live max_inflation_rate to the terminal rate over the
                              glidepath months. Only computed here when the SOTP result omits it and a
                              ``supply_ctx`` is supplied; otherwise taken from the SOTP result.

Deterministic SOTP contract (canonical input keys; aliases in ``INPUT_ALIASES``, remap with ``key_map``)
    v_pub_daily_usd, v_conf_daily_usd, tau_pub_bps (net, holder-captured), tau_conf_bps, alpha_capture,
    svrn_target_inflation, svrn_glidepath_months, fee_compression_lambda_monthly, headroom_cross_vm_bps,
    confidential_tvl_usd, hhi_external, tau_floor_bps
Result keys read: fdv_total (required), implied_price (required), crossover_month, supply_at_horizon_near,
    fdv_ex_monetary (optional).

Scenario stress parameters (-60% volume, 1 pip take, HHI 3,500, ...) are falsification-test definitions
fixed by MODEL_DESIGN 4.3 / QUANT_PIPELINE_SPEC Model C. They are carried as labeled ``Assumption``
objects in ``STRESS_PARAMETERS`` and attached to the BearCase so the snapshot shows them as assumed,
not measured.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from valuo import assumptions
from valuo.schemas import Assumption, BearCase, BearScenario

__all__ = [
    "SCENARIO_KEYS",
    "INPUT_ALIASES",
    "STRESS_PARAMETERS",
    "MIN_SOLVER_FILLS_FOR_TRIGGER",
    "THIN_SOLVER_SAMPLE_FILLS",
    "SotpFn",
    "McFn",
    "run_bear_case",
    "build_perturbations",
    "merge_worst",
    "evaluate_triggers",
    "estimate_crossover_month",
    "live_metrics",
    "resolve_key",
]

SotpFn = Callable[[dict[str, Any]], dict[str, Any]]

SCENARIO_KEYS: tuple[str, ...] = (
    "fee_race_to_zero",
    "governance_stalemate",
    "post_incentive_decay",
    "solver_cartelization",
)

_TITLES: dict[str, str] = {
    "fee_race_to_zero": "Aggregator bypass: public take races to 1 pip",
    "governance_stalemate": "Governance stalemate: 2.5% issuance forever",
    "post_incentive_decay": "Post-incentive volume decay (NEAR@3.33 unwind)",
    "solver_cartelization": "Solver cartelization: HHI_solver > 3,500, 1Click loses the spread",
}

# Below this many solver fill participations one solver taking four fills breaches 3,500 by chance, so the
# trigger is reported as unevaluated (thin sample) rather than graded; --nearblocks-pages raises the count.
MIN_SOLVER_FILLS_FOR_TRIGGER = 10
# A graded HHI_solver resting on fewer sampled fills than this is a point estimate within sampling noise of the
# 3,500 threshold (canonical runs minutes apart measured 2,893 / 3,200 / 1,598): the trigger row is annotated
# "thin sample: N fills" and the scorecard grades the solver-concentration claim DERIVED, confidence low.
THIN_SOLVER_SAMPLE_FILLS = 30

# Where each scenario's early-warning metric is read from (URL only; the JSON path is a separate field).
_MONITOR_URL: dict[str, str] = {
    "fee_race_to_zero": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue",
    "governance_stalemate": "https://free.rpc.fastnear.com",
    "post_incentive_decay": "https://nearstats.org/api/near/summary",
    "solver_cartelization": "https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50",
}
_MONITOR_FIELD: dict[str, str] = {
    "fee_race_to_zero": "sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days",
    "governance_stalemate": "EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)",
    "post_incentive_decay": "intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1",
    "solver_cartelization": (
        "HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, "
        "token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)"
    ),
}

# Canonical input key -> names the parallel-built deterministic_sotp might use. First hit wins.
INPUT_ALIASES: dict[str, tuple[str, ...]] = {
    # sotp_valuation.deterministic_sotp's own names (v_pub_usd_day, v_conf_usd_day, lambda_pub) come right after the
    # canonical name so build_inputs() dicts need no key_map.
    "v_pub_daily_usd": ("v_pub_daily_usd", "v_pub_usd_day", "public_daily_volume_usd", "v_pub", "daily_volume_public_usd", "public_volume_daily_usd"),
    "v_conf_daily_usd": ("v_conf_daily_usd", "v_conf_usd_day", "confidential_daily_volume_usd", "v_conf", "daily_volume_confidential_usd", "confidential_volume_daily_usd"),
    "tau_pub_bps": ("tau_pub_bps", "net_take_bps", "public_take_bps", "take_pub_bps", "tau_pub"),
    "tau_conf_bps": ("tau_conf_bps", "confidential_take_bps", "take_conf_bps", "tau_conf"),
    "alpha_capture": ("alpha_capture", "capture_ratio", "alpha", "buyback_capture_ratio"),
    "svrn_target_inflation": ("svrn_target_inflation", "inflation_terminal_annual", "terminal_inflation_annual", "target_inflation_annual", "inflation_target"),
    "svrn_glidepath_months": ("svrn_glidepath_months", "glidepath_months"),
    "fee_compression_lambda_monthly": ("fee_compression_lambda_monthly", "lambda_pub", "lambda_monthly", "compression_lambda_monthly", "lambda_compression"),
    "headroom_cross_vm_bps": ("headroom_cross_vm_bps", "headroom_bps", "cross_vm_headroom_bps"),
    "confidential_tvl_usd": ("confidential_tvl_usd", "conf_tvl_usd"),
    "hhi_external": ("hhi_external", "hhi"),
    "tau_floor_bps": ("tau_floor_bps", "tau_pub_floor_bps", "floor_bps", "competitive_floor_bps"),
    "max_inflation_rate": ("max_inflation_rate", "inflation_current_annual", "current_inflation_annual"),
}

_RESULT_ALIASES: dict[str, tuple[str, ...]] = {
    "fdv_total": ("fdv_total", "fdv_p50", "fdv_usd", "fdv"),
    "implied_price": ("implied_price", "price_p50", "implied_price_usd", "price_usd"),
    "crossover_month": ("crossover_month", "crossover_month_glidepath", "crossover"),
    "supply_at_horizon_near": ("supply_at_horizon_near", "supply_at_horizon", "horizon_supply_near"),
    "fdv_ex_monetary": ("fdv_ex_monetary", "fdv_ex_monetary_total"),
}

# Direction of harm per canonical key, used when merging scenarios into combined_worst.
_LOWER_IS_WORSE: frozenset[str] = frozenset({
    "v_pub_daily_usd", "v_conf_daily_usd", "tau_pub_bps", "tau_conf_bps", "alpha_capture",
    "confidential_tvl_usd", "headroom_cross_vm_bps", "tau_floor_bps",
})
_HIGHER_IS_WORSE: frozenset[str] = frozenset({
    "hhi_external", "svrn_target_inflation", "fee_compression_lambda_monthly", "svrn_glidepath_months",
})

# Required canonical inputs per scenario: without these the scenario cannot move the model, so we fail loudly
# rather than report a zero drawdown that looks like evidence.
_REQUIRED: dict[str, tuple[str, ...]] = {
    "fee_race_to_zero": ("tau_pub_bps", "tau_conf_bps"),
    "governance_stalemate": ("svrn_target_inflation",),
    "post_incentive_decay": ("v_pub_daily_usd", "v_conf_daily_usd"),
    "solver_cartelization": ("tau_pub_bps",),
}

_MISSING: Any = object()


# The stress definitions live in the single registry (valuo/assumptions.py, keys bear_*) so the snapshot's
# assumptions list and the web sliders see them next to every other labeled input.
STRESS_PARAMETERS: dict[str, Assumption] = {key: assumptions.get(key) for key in assumptions.BEAR_STRESS_KEYS}


# ----------------------------------------------------------------------------- key resolution
def resolve_key(inputs: Mapping[str, Any], canonical: str, key_map: Mapping[str, str] | None = None) -> str | None:
    """Actual key in ``inputs`` for a canonical name: ``key_map`` first, then ``INPUT_ALIASES``; None if absent."""
    if key_map and canonical in key_map:
        actual = key_map[canonical]
        return actual if actual in inputs else None
    for alias in INPUT_ALIASES.get(canonical, (canonical,)):
        if alias in inputs:
            return alias
    return None


def _get(inputs: Mapping[str, Any], canonical: str, key_map: Mapping[str, str] | None = None) -> float | None:
    actual = resolve_key(inputs, canonical, key_map)
    if actual is None:
        return None
    raw = inputs[actual]
    return None if raw is None else float(raw)


def _result_get(result: Mapping[str, Any], canonical: str) -> Any:
    for alias in _RESULT_ALIASES[canonical]:
        if alias in result:
            return result[alias]
    return _MISSING


def _apply(
    base_inputs: Mapping[str, Any], perturbations: Mapping[str, float], key_map: Mapping[str, str] | None
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Copy of ``base_inputs`` with perturbations written under the model's actual key names.

    Returns (inputs, applied canonical->actual, unapplied canonical keys). Optional keys the model does
    not accept are reported, not silently added, so the snapshot shows what actually reached the model.
    """
    out = dict(base_inputs)
    applied: dict[str, str] = {}
    unapplied: list[str] = []
    for canonical, value in perturbations.items():
        actual = resolve_key(base_inputs, canonical, key_map)
        if actual is None:
            unapplied.append(canonical)
            continue
        out[actual] = value
        applied[canonical] = actual
    return out, applied, unapplied


def _require(base_inputs: Mapping[str, Any], scenario: str, key_map: Mapping[str, str] | None) -> None:
    missing = [k for k in _REQUIRED[scenario] if resolve_key(base_inputs, k, key_map) is None]
    if missing:
        raise KeyError(
            f"bear_case[{scenario}]: base_inputs lacks required key(s) {missing}; accepted aliases "
            f"{ {k: INPUT_ALIASES[k] for k in missing} }; base_inputs keys = {sorted(base_inputs)}. "
            "Pass key_map={canonical: actual} to remap."
        )


# ----------------------------------------------------------------------------- perturbations
def _live(live: Mapping[str, Any], key: str) -> float | None:
    raw = live.get(key)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def build_perturbations(
    base_inputs: Mapping[str, Any], live: Mapping[str, Any], key_map: Mapping[str, str] | None = None
) -> dict[str, dict[str, float]]:
    """Absolute perturbed values per scenario, keyed by canonical input name.

    fee_race_to_zero:     tau_pub -> 1 pip, tau_conf -> 5 bps, floor -> 1 pip; alpha unchanged.
    governance_stalemate: terminal inflation -> live max_inflation_rate (glidepath becomes flat).
    post_incentive_decay: V_pub x0.4, V_conf x0.3, confidential TVL x0.3.
    solver_cartelization: HHI -> 3,500, headroom -> -2 bps, tau_pub -> max(floor, tau_pub - 2), lambda -> high bound.
    """
    for scenario in SCENARIO_KEYS:
        _require(base_inputs, scenario, key_map)
    p = STRESS_PARAMETERS

    tau_pub = _get(base_inputs, "tau_pub_bps", key_map)
    v_pub = _get(base_inputs, "v_pub_daily_usd", key_map)
    v_conf = _get(base_inputs, "v_conf_daily_usd", key_map)
    assert tau_pub is not None and v_pub is not None and v_conf is not None  # guaranteed by _require

    inflation_now = _live(live, "max_inflation_rate")
    if inflation_now is None:
        inflation_now = _get(base_inputs, "max_inflation_rate", key_map)
    if inflation_now is None:
        raise ValueError("bear_case[governance_stalemate]: live['max_inflation_rate'] is required (on-chain protocol config)")

    fee_race = {
        "tau_pub_bps": p["bear_fee_race_tau_pub_bps"].value,
        "tau_conf_bps": p["bear_fee_race_tau_conf_bps"].value,
        "tau_floor_bps": p["bear_fee_race_tau_pub_bps"].value,
    }
    stalemate = {"svrn_target_inflation": inflation_now}
    decay: dict[str, float] = {
        "v_pub_daily_usd": v_pub * p["bear_decay_v_pub_multiplier"].value,
        "v_conf_daily_usd": v_conf * p["bear_decay_v_conf_multiplier"].value,
    }
    tvl = _get(base_inputs, "confidential_tvl_usd", key_map)
    if tvl is None:
        tvl = _live(live, "confidential_tvl_usd")
    if tvl is not None:
        decay["confidential_tvl_usd"] = tvl * p["bear_decay_tvl_multiplier"].value

    giveback = -p["bear_cartel_headroom_bps"].value
    cartel = {
        "hhi_external": p["bear_cartel_hhi_external"].value,
        "headroom_cross_vm_bps": p["bear_cartel_headroom_bps"].value,
        "tau_pub_bps": max(p["bear_tau_floor_bps"].value, tau_pub - giveback),
        "fee_compression_lambda_monthly": p["bear_cartel_lambda_monthly"].value,
    }
    return {
        "fee_race_to_zero": fee_race,
        "governance_stalemate": stalemate,
        "post_incentive_decay": decay,
        "solver_cartelization": cartel,
    }


def merge_worst(per_scenario: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    """Union of all scenario perturbations; on collision keep the value that is worse for the thesis."""
    merged: dict[str, float] = {}
    for scenario in SCENARIO_KEYS:
        for key, value in per_scenario.get(scenario, {}).items():
            if key not in merged:
                merged[key] = value
            elif key in _LOWER_IS_WORSE:
                merged[key] = min(merged[key], value)
            elif key in _HIGHER_IS_WORSE:
                merged[key] = max(merged[key], value)
            else:
                merged[key] = value
    return merged


# ----------------------------------------------------------------------------- triggers
def _ci_pair(value: Any) -> tuple[float, float] | None:
    """(lo, hi) from a two-element numeric sequence with lo <= hi, else None."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lo, hi = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    return (lo, hi) if lo <= hi else None


def _trigger(
    metric: str, current: float | None, threshold: float, comparator: str, scenario: str, note: str = "", *, evaluable: bool = True,
) -> dict[str, Any]:
    """One early-warning evaluation. ``trigger_evaluated`` is False and ``trigger_breached`` is None when the metric is
    unmeasured or ``evaluable`` is False (thin sample); the memo prints such rows as "not measured", never "not breached"."""
    ops: dict[str, Callable[[float, float], bool]] = {
        "<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
    }
    evaluated = current is not None and evaluable
    breached: bool | None = bool(ops[comparator](current, threshold)) if evaluated else None
    if current is None:
        note = (note + " " if note else "") + "current value unmeasured in this run; trigger not measured (trigger_breached null, not counted as breached or clear)"
    return {
        "early_warning_metric": metric,
        "current_value": current,
        "trigger_threshold": float(threshold),
        "trigger_comparator": comparator,
        "trigger_breached": breached,
        "trigger_evaluated": bool(evaluated),
        "monitor_source": _MONITOR_URL[scenario],
        "monitor_field": _MONITOR_FIELD[scenario],
        "trigger_note": note.strip() or None,
    }


_SPAN_POSITION = {"breached": "above", "clear": "below", "inconclusive": "as straddling"}


def evaluate_triggers(
    live: Mapping[str, Any], base_inputs: Mapping[str, Any] | None = None, key_map: Mapping[str, str] | None = None
) -> dict[str, dict[str, Any]]:
    """Per-scenario early-warning evaluation against the live metrics (unmeasured metric -> trigger_breached None, noted)."""
    p = STRESS_PARAMETERS
    base_inputs = base_inputs or {}

    net_take = _live(live, "net_take_bps")
    fee_race = _trigger("net_take_bps_30d", net_take, p["bear_fee_race_trigger_net_take_bps"].value, "<", "fee_race_to_zero")

    target = _get(base_inputs, "svrn_target_inflation", key_map)
    if target is None:
        target = assumptions.value("svrn_target_inflation")
    inflation_now = _live(live, "max_inflation_rate")
    stalemate = _trigger(
        "max_inflation_rate", inflation_now, target, ">", "governance_stalemate",
        note="breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted",
    )

    vol = _live(live, "volume_30d_usd")
    rec = _live(live, "record_30d_usd")
    drawdown = None if (vol is None or rec is None or rec <= 0) else vol / rec - 1.0
    decay = _trigger("volume_30d_vs_record_30d", drawdown, p["bear_decay_trigger_volume_drawdown"].value, "<=", "post_incentive_decay")

    # Solver cartelization is about the market makers filling intents. The external-predecessor HHI cannot see them
    # (fills are relayer self-receipts), so the trigger reads HHI_solver from the execute_intents payload audit.
    # With too few parsed fills the HHI is noise and the trigger is left unevaluated; the deposit-source HHI is
    # kept in the note for context only.
    hhi_solver = _live(live, "hhi_solver")
    n_fills = _live(live, "solver_fills_attributed")
    n_sampled = _live(live, "solver_fills_sampled")
    hhi_deposit = _live(live, "hhi_external")
    span = _live(live, "sample_span_s")
    thin = n_fills is not None and n_fills < MIN_SOLVER_FILLS_FOR_TRIGGER
    threshold = p["bear_cartel_hhi_external"].value
    ci = _ci_pair(live.get("hhi_solver_ci90"))
    cartel = _trigger("hhi_solver", hhi_solver, threshold, ">", "solver_cartelization", evaluable=not thin)
    primary: bool | None = cartel["trigger_breached"]  # True/False when HHI_solver was graded, None when unmeasured or thin
    # With a bootstrap 90% CI the primary condition is graded on the interval, not the point: breached only when the
    # lower bound is above the threshold, clear only when the upper bound is below it, otherwise inconclusive (None).
    if hhi_solver is None:
        primary_status = "not_measured"
    elif thin:
        primary_status = "thin"
    elif ci is not None:
        lo, hi = ci
        primary = True if lo > threshold else (False if hi < threshold else None)
        primary_status = {True: "breached", False: "clear", None: "inconclusive"}[primary]
    else:
        primary_status = "breached" if primary else "clear"
    # Span rule: a sample covering less than solver_sample_min_span_s is one serially correlated window; its bootstrap CI
    # covers within-window noise only, so the HHI condition may not be graded breached or clear on it (inconclusive).
    min_span = assumptions.value("solver_sample_min_span_s")
    short_span = primary_status in ("breached", "clear", "inconclusive") and (span is None or span < min_span)
    graded_status_before_span = primary_status
    if short_span:
        primary = None
        primary_status = "short_span"
    headroom = _live(live, "headroom_cross_vm_bps")
    secondary_breached: bool | None = (headroom < 0.0) if headroom is not None else None
    # Asymmetric rule: a breach on either measured condition is a breach; a clear needs the primary HHI_solver to have
    # been graded and both conditions to hold clear; a primary that is unmeasured or too thin with a secondary that is
    # not breached is NOT measured (null) - never "not breached" on the strength of the headroom alone.
    if primary is True or secondary_breached is True:
        breached: bool | None = True
    elif primary is False:
        breached = False
    else:
        breached = None
    # With a CI the interval carries the sampling noise; the fixed-count caveat applies only to a point-graded HHI.
    sample_thin = primary is not None and ci is None and n_sampled is not None and n_sampled < THIN_SOLVER_SAMPLE_FILLS

    note_parts: list[str] = []
    if hhi_solver is None:
        note_parts.append("no execute_intents fill with an attributable solver was parsed this run")
    elif short_span:
        span_txt = f"{span:,.0f} s" if span is not None else "an unknown span"
        ci_txt = f", bootstrap 90% CI [{ci[0]:,.0f}, {ci[1]:,.0f}]" if ci is not None else ""
        note_parts.append(
            f"inconclusive: the solver sample covers {span_txt}, below the {min_span:,.0f} s minimum (solver_sample_min_span_s); "
            f"HHI_solver {hhi_solver:,.0f}{ci_txt}" + (f" over {n_fills:,.0f} fill participations" if n_fills is not None else "")
            + f" would grade {_SPAN_POSITION[graded_status_before_span]} the {threshold:,.0f} threshold, but a window that short is serially "
            "correlated and its CI covers within-window noise only, so the HHI condition is not graded"
        )
    elif ci is not None and not thin:
        verdict = {
            "breached": f"CI lower bound {ci[0]:,.0f} > {threshold:,.0f}: breached",
            "clear": f"CI upper bound {ci[1]:,.0f} < {threshold:,.0f}: clear",
            "inconclusive": f"CI straddles {threshold:,.0f}: inconclusive, not graded",
        }[primary_status]
        note_parts.append(
            f"sample: {n_fills:,.0f} solver fill participations" + (f" over {span:,.0f} s" if span is not None else "")
            + f"; HHI_solver {hhi_solver:,.0f}, bootstrap 90% CI [{ci[0]:,.0f}, {ci[1]:,.0f}] ({verdict})"
        )
    elif thin:
        note_parts.append(
            f"only {n_fills:,.0f} solver fill participations parsed (< {MIN_SOLVER_FILLS_FOR_TRIGGER}); HHI_solver "
            f"{hhi_solver:,.0f} is too thin to grade - raise --nearblocks-pages"
        )
    else:
        note_parts.append(f"sample: {n_fills:,.0f} solver fill participations" + (f" over {span:,.0f} s" if span is not None else ""))
    if sample_thin:
        note_parts.append(
            f"thin sample: {n_sampled:,.0f} fills (< {THIN_SOLVER_SAMPLE_FILLS}); HHI_solver moves by hundreds of points between runs "
            "at this size, so the grade is a point estimate, not a market-share measure"
        )
    if breached is None:
        headroom_txt = "unmeasured (benchmark missing)" if headroom is None else f"{headroom:+.2f} bps, not negative"
        what = ("solver HHI CI straddles the threshold" if primary_status == "inconclusive"
                else "solver sample span below the minimum" if primary_status == "short_span" else "solver HHI unmeasured or too thin")
        graded_word = "inconclusive" if primary_status in ("inconclusive", "short_span") else "not measured"
        note_parts.append(
            f"{what} and cross-VM headroom {headroom_txt}; trigger {graded_word} "
            "(trigger_breached null, not counted as breached or clear)"
        )
    elif primary is None and secondary_breached is True:
        note_parts.append(f"graded on the secondary condition alone: cross-VM headroom {headroom:+.2f} bps < 0 (solver HHI {primary_status.replace('_', ' ')})")
    elif headroom is None:
        note_parts.append("cross-VM headroom unmeasured (benchmark missing); graded on the solver HHI alone")
    if hhi_deposit is not None:
        note_parts.append(f"deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = {hhi_deposit:,.0f}")

    cartel.update({
        "trigger_note": "; ".join(note_parts) or None,
        "trigger_breached": breached,
        "trigger_evaluated": breached is not None,
        "hhi_deposit_source_external": hhi_deposit,
        "solver_fills_attributed": n_fills,
        "solver_fills_sampled": n_sampled,
        "sample_thin": sample_thin,
        "hhi_solver_ci90": list(ci) if ci is not None else None,
        "primary_status": primary_status,
        "trigger_status": (
            "breached" if breached is True else "not_breached" if breached is False
            else "inconclusive" if primary_status in ("inconclusive", "short_span") else "not_measured"
        ),
        "sample_span_s": span,
        "min_sample_span_s": min_span,
        "span_sufficient": (span is not None and span >= min_span),
        "secondary_metric": "headroom_cross_vm_bps",
        "secondary_value": headroom,
        "secondary_threshold": 0.0,
        "secondary_comparator": "<",
        "secondary_breached": secondary_breached,
        "secondary_evaluated": headroom is not None,
    })

    return {
        "fee_race_to_zero": fee_race,
        "governance_stalemate": stalemate,
        "post_incentive_decay": decay,
        "solver_cartelization": cartel,
    }


# ----------------------------------------------------------------------------- crossover fallback
def estimate_crossover_month(
    inputs: Mapping[str, Any], supply_ctx: Mapping[str, Any], key_map: Mapping[str, str] | None = None
) -> int | None:
    """First month where monthly issuance <= monthly sinks under the inputs' inflation path, else None.

    supply_ctx keys: total_supply_near, price_usd, gas_burn_near_per_day, state_lock_near_per_day (0 if
    unmeasured, with the caller's warning), max_inflation_rate, horizon_months (default 36). The take in
    ``inputs`` is treated as net (holder-captured) unless supply_ctx['tau_is_gross'] is true, in which case
    alpha_capture from the inputs scales it. Returns None when the context is incomplete.
    """
    try:
        supply = float(supply_ctx["total_supply_near"])
        price = float(supply_ctx["price_usd"])
        gas_burn = float(supply_ctx.get("gas_burn_near_per_day") or 0.0)
        state_lock = float(supply_ctx.get("state_lock_near_per_day") or 0.0)
        i0 = float(supply_ctx["max_inflation_rate"])
    except (KeyError, TypeError, ValueError):
        return None
    if supply <= 0 or price <= 0:
        return None
    horizon = int(supply_ctx.get("horizon_months") or 36)

    v_pub = _get(inputs, "v_pub_daily_usd", key_map) or 0.0
    v_conf = _get(inputs, "v_conf_daily_usd", key_map) or 0.0
    tau_pub = _get(inputs, "tau_pub_bps", key_map) or 0.0
    tau_conf = _get(inputs, "tau_conf_bps", key_map) or 0.0
    alpha = 1.0
    if supply_ctx.get("tau_is_gross"):
        alpha = _get(inputs, "alpha_capture", key_map) or 0.0
    terminal = _get(inputs, "svrn_target_inflation", key_map)
    terminal = i0 if terminal is None else terminal
    glide = _get(inputs, "svrn_glidepath_months", key_map)
    glide = assumptions.value("svrn_glidepath_months") if glide is None else glide

    days = 365.25 / 12.0
    buyback_daily = (v_pub * tau_pub + v_conf * tau_conf) / 1e4 * alpha / price
    sinks_m = (buyback_daily + gas_burn + state_lock) * days
    for m in range(1, horizon + 1):
        frac = 1.0 if glide <= 0 else min(m, glide) / glide
        i_m = i0 + (terminal - i0) * frac
        issuance_m = supply * i_m * days / 365.25
        if issuance_m <= sinks_m:
            return m
        supply += issuance_m - gas_burn * days
    return None


# ----------------------------------------------------------------------------- formatting
def _fmt_usd(x: float | None) -> str:
    if x is None:
        return "n/a"
    a = abs(x)
    if a >= 1e9:
        return f"${x / 1e9:,.2f}B"
    if a >= 1e6:
        return f"${x / 1e6:,.1f}M"
    if a >= 1e3:
        return f"${x:,.0f}"
    return f"${x:,.2f}"


def _fmt_pct(x: float | None, digits: int = 1, signed: bool = True) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:+.{digits}f}%" if signed else f"{x * 100:.{digits}f}%"


def _fmt_bps(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{x:.{digits}f} bps"


def _fmt_num(x: float | None, digits: int = 0) -> str:
    return "n/a" if x is None else f"{x:,.{digits}f}"


def _fmt_price(x: float | None) -> str:
    return "n/a" if x is None else f"${x:,.2f}"


def _fmt_month(m: int | None) -> str:
    return "none within horizon" if m is None else f"month {m}"


# ----------------------------------------------------------------------------- narratives
def _narrative(
    scenario: str, base_inputs: Mapping[str, Any], live: Mapping[str, Any], pert: Mapping[str, float],
    base: dict[str, Any], scn: dict[str, Any], trig: Mapping[str, Any], key_map: Mapping[str, str] | None,
) -> str:
    tau_pub = _get(base_inputs, "tau_pub_bps", key_map)
    tau_conf = _get(base_inputs, "tau_conf_bps", key_map)
    alpha = _get(base_inputs, "alpha_capture", key_map)
    v_pub = _get(base_inputs, "v_pub_daily_usd", key_map)
    v_conf = _get(base_inputs, "v_conf_daily_usd", key_map)
    headroom = _live(live, "headroom_cross_vm_bps")
    dd, pdd = scn["drawdown_pct"], scn["price_drawdown_pct"]
    fdv, price = _fmt_usd(scn["fdv"]), _fmt_price(scn["price"])

    if scenario == "fee_race_to_zero":
        headroom_txt = (
            f"Evidence against it: live cross-VM headroom is {headroom:+.1f} bps, so a bypassing frontend must first give up that execution edge."
            if headroom is not None else
            "Evidence against it is missing this run: the cross-VM headroom benchmark did not return."
        )
        return (
            f"Third-party frontends route around near.com and the public gross take collapses from {_fmt_bps(tau_pub)} to "
            f"{_fmt_bps(pert['tau_pub_bps'], 2)} (the bare intents.near contract fee); confidential execution reprices from "
            f"{_fmt_bps(tau_conf, 0)} to {_fmt_bps(pert['tau_conf_bps'], 0)}. Capture ratio alpha is held at "
            f"{_fmt_pct(alpha, 0, signed=False)}, so the hit is price, not allocation. Deterministic (median-input) FDV {_fmt_pct(dd)} to {fdv}; implied "
            f"price {price}. {headroom_txt} Trigger: DefiLlama 30d net take (gross x alpha) below {_fmt_bps(trig['trigger_threshold'])} "
            f"(now {_fmt_bps(trig['current_value'])})."
        )
    if scenario == "governance_stalemate":
        extra_supply = None
        if base.get("supply_at_horizon") is not None and scn.get("supply_at_horizon") is not None:
            extra_supply = scn["supply_at_horizon"] - base["supply_at_horizon"]
        supply_txt = f"{_fmt_num(extra_supply)} more NEAR outstanding at the horizon and" if extra_supply is not None else "a higher horizon supply and"
        target = _get(base_inputs, "svrn_target_inflation", key_map)
        if target is None:
            target = assumptions.value("svrn_target_inflation")
        return (
            f"Validators never enact the SVRN cut: max_inflation_rate stays at {_fmt_pct(pert['svrn_target_inflation'], 2, signed=False)} "
            f"for the full horizon instead of gliding to {_fmt_pct(target, 2, signed=False)}. Protocol cash flows do not change, so "
            f"FDV moves {_fmt_pct(dd)}; the damage is dilution: {supply_txt} a per-token value of {price} ({_fmt_pct(pdd)} vs base). "
            f"Net-float crossover: {_fmt_month(scn['crossover_month'])} (base: {_fmt_month(base['crossover_month'])}). "
            f"This scenario is live today: the on-chain cap reads {_fmt_pct(trig['current_value'], 2, signed=False)} and no cut has been enacted."
        )
    if scenario == "post_incentive_decay":
        vol = _live(live, "volume_30d_usd")
        rec = _live(live, "record_30d_usd")
        ratio_txt = (
            f"Current 30d volume {_fmt_usd(vol)} is {_fmt_pct(vol / rec, 0, signed=False)} of the 30d record {_fmt_usd(rec)}; the trigger fires at "
            f"{_fmt_pct(trig['trigger_threshold'], 0)}."
            if (vol is not None and rec) else
            "30d volume versus its record is unmeasured this run, so the trigger could not be evaluated."
        )
        tvl_txt = f" and confidential TVL x{STRESS_PARAMETERS['bear_decay_tvl_multiplier'].value:.1f} (nearstats flags that TVL unverified)" if "confidential_tvl_usd" in pert else ""
        return (
            f"Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume {_fmt_usd(v_pub)} -> "
            f"{_fmt_usd(pert['v_pub_daily_usd'])} (-60%), confidential {_fmt_usd(v_conf)} -> {_fmt_usd(pert['v_conf_daily_usd'])} (-70%){tvl_txt}. "
            f"Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV {_fmt_pct(dd)} to {fdv}; implied price {price}. {ratio_txt}"
        )
    hhi = trig.get("current_value")
    n_eff = None if (hhi is None or hhi <= 0) else 10_000.0 / hhi
    n_fills = _live(live, "solver_fills_attributed")
    hhi_deposit = _live(live, "hhi_external")
    if hhi is None:
        live_txt = "Live: no solver fill could be attributed from the sampled execute_intents payloads this run"
    else:
        live_txt = (
            f"Live: HHI over solver fill participations {_fmt_num(hhi)} ({_fmt_num(n_eff, 1)} effective solvers across "
            f"{_fmt_num(n_fills)} fill participations)"
        )
        ci = _ci_pair(trig.get("hhi_solver_ci90"))
        if ci is not None:
            live_txt += f", bootstrap 90% CI [{_fmt_num(ci[0])}, {_fmt_num(ci[1])}]"
            if trig.get("primary_status") == "inconclusive":
                live_txt += f" straddles {_fmt_num(trig['trigger_threshold'])}, so the HHI condition is inconclusive"
        if trig.get("primary_status") == "short_span":
            sp = trig.get("sample_span_s")
            live_txt += (f"; the sample spans {_fmt_num(sp)} s, under the {_fmt_num(trig.get('min_sample_span_s'))} s minimum, "
                         "so the HHI condition is inconclusive" if sp is not None else
                         "; the sample span is unknown, so the HHI condition is inconclusive")
        if not trig.get("trigger_evaluated") and n_fills is not None and n_fills < MIN_SOLVER_FILLS_FOR_TRIGGER:
            live_txt += f", too few to grade (< {MIN_SOLVER_FILLS_FOR_TRIGGER})"
    deposit_txt = f"; deposit-source HHI over external predecessors {_fmt_num(hhi_deposit)} (not a solver measure)" if hhi_deposit is not None else ""
    return (
        f"Two market makers take most fills (HHI_solver > {_fmt_num(pert['hhi_external'])}) and spreads widen until Relay/LI.FI deliver "
        f"{_fmt_bps(-pert['headroom_cross_vm_bps'], 0)} better net execution on cross-VM (headroom {pert['headroom_cross_vm_bps']:+.0f} bps). "
        f"Keeping flow costs the same {_fmt_bps(-pert['headroom_cross_vm_bps'], 0)} of take ({_fmt_bps(tau_pub)} -> "
        f"{_fmt_bps(pert['tau_pub_bps'])}) while compression runs at {pert['fee_compression_lambda_monthly']:.2f}/month. "
        f"Deterministic (median-input) FDV {_fmt_pct(dd)} to {fdv}; implied price {price}. {live_txt}{deposit_txt}; cross-VM headroom "
        f"{'n/a' if headroom is None else f'{headroom:+.1f} bps'}; trigger at HHI_solver > {_fmt_num(trig['trigger_threshold'])} or headroom < 0."
    )


def _status(s: BearScenario) -> str:
    if s.trigger_breached is None or not getattr(s, "trigger_evaluated", True):
        return "inconclusive" if getattr(s, "trigger_status", None) == "inconclusive" else "not measured"
    return "BREACHED" if s.trigger_breached else "not breached"


def _summary(base_fdv: float, scenarios: list[BearScenario], combined_fdv: float, combined_dd: float) -> str:
    """Five sentences: one per scenario (key, condition, drawdown, weekly metric, status) and one combined.

    FDV figures are deterministic (median-input) values; the memo table carries the Monte Carlo medians beside them.
    """
    by_key = {s.key: s for s in scenarios}
    parts: list[str] = []

    s = by_key["fee_race_to_zero"]
    parts.append(
        f"fee_race_to_zero: public gross take at {_fmt_bps(s.perturbations['tau_pub_bps'], 2)} and confidential at "
        f"{_fmt_bps(s.perturbations['tau_conf_bps'], 0)} puts the deterministic FDV at {_fmt_usd(s.sotp_fdv_p50)} ({_fmt_pct(s.drawdown_pct)}); "
        f"watch DefiLlama near-intents 30d net take weekly, trigger < {_fmt_bps(s.trigger_threshold)}, now "
        f"{_fmt_bps(s.current_value)} ({_status(s)})."
    )
    s = by_key["governance_stalemate"]
    pdd = getattr(s, "price_drawdown_pct", None)
    parts.append(
        f"governance_stalemate: no SVRN cut (cap {_fmt_pct(s.perturbations['svrn_target_inflation'], 2, signed=False)} for 36 months) "
        f"leaves the deterministic FDV at {_fmt_usd(s.sotp_fdv_p50)} ({_fmt_pct(s.drawdown_pct)}) but dilutes per-token value to {_fmt_price(s.price_p50)} "
        f"({_fmt_pct(pdd)}) with crossover {_fmt_month(s.crossover_month)}; watch max_inflation_rate in EXPERIMENTAL_protocol_config, "
        f"trigger > {_fmt_pct(s.trigger_threshold, 2, signed=False)}, now {_fmt_pct(s.current_value, 2, signed=False)} "
        f"({_status(s)})."
    )
    s = by_key["post_incentive_decay"]
    parts.append(
        f"post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at {_fmt_usd(s.sotp_fdv_p50)} "
        f"({_fmt_pct(s.drawdown_pct)}); watch nearstats 30d volume against its 30d record weekly, trigger <= "
        f"{_fmt_pct(s.trigger_threshold, 0)}, now {_fmt_pct(s.current_value)} ({_status(s)})."
    )
    s = by_key["solver_cartelization"]
    headroom = getattr(s, "secondary_value", None)
    parts.append(
        f"solver_cartelization: HHI_solver > {_fmt_num(s.perturbations['hhi_external'])} with cross-VM headroom at "
        f"{s.perturbations['headroom_cross_vm_bps']:+.0f} bps puts the deterministic FDV at {_fmt_usd(s.sotp_fdv_p50)} ({_fmt_pct(s.drawdown_pct)}); "
        f"watch the execute_intents solver HHI (now {_fmt_num(s.current_value)}) and the live quote-race headroom "
        f"(now {'n/a' if headroom is None else f'{headroom:+.1f} bps'}) weekly ({_status(s)})."
    )
    evaluated = [x for x in scenarios if x.trigger_breached is not None and getattr(x, "trigger_evaluated", True)]
    n_breached = sum(1 for x in evaluated if x.trigger_breached is True)
    unevaluated = [x.key for x in scenarios if x not in evaluated]
    unev_txt = f" ({len(unevaluated)} not graded this run, inconclusive or not measured: {', '.join(unevaluated)})" if unevaluated else ""
    parts.append(
        f"All four at once: deterministic FDV {_fmt_usd(combined_fdv)} ({_fmt_pct(combined_dd)} vs base {_fmt_usd(base_fdv)}); "
        f"{n_breached} of {len(evaluated)} measured triggers currently breached{unev_txt}, and the thesis is falsified if any trigger holds for 30 consecutive days."
    )
    return " ".join(parts)


# ----------------------------------------------------------------------------- evaluation
def _read(result: Mapping[str, Any], label: str) -> dict[str, Any]:
    fdv = _result_get(result, "fdv_total")
    price = _result_get(result, "implied_price")
    if fdv is _MISSING or fdv is None:
        raise KeyError(f"bear_case: {label} sotp result lacks fdv_total (aliases {_RESULT_ALIASES['fdv_total']}); keys = {sorted(result)}")
    if price is _MISSING or price is None:
        raise KeyError(f"bear_case: {label} sotp result lacks implied_price (aliases {_RESULT_ALIASES['implied_price']}); keys = {sorted(result)}")
    crossover = _result_get(result, "crossover_month")
    supply = _result_get(result, "supply_at_horizon_near")
    fdv_ex = _result_get(result, "fdv_ex_monetary")
    return {
        "fdv": float(fdv),
        "price": float(price),
        "crossover_month": crossover,  # may be _MISSING
        "supply_at_horizon": None if supply is _MISSING or supply is None else float(supply),
        "fdv_ex_monetary": None if fdv_ex is _MISSING or fdv_ex is None else float(fdv_ex),
    }


def _ratio_change(new: float, base: float) -> float:
    return 0.0 if base == 0 else new / base - 1.0


def _evaluate(
    label: str, inputs: dict[str, Any], sotp_fn: SotpFn, base: dict[str, Any],
    supply_ctx: Mapping[str, Any] | None, key_map: Mapping[str, str] | None,
) -> dict[str, Any]:
    """Run the SOTP on perturbed inputs and measure it against the base."""
    out = _read(sotp_fn(inputs), label)
    out["drawdown_pct"] = _ratio_change(out["fdv"], base["fdv"])
    out["price_drawdown_pct"] = _ratio_change(out["price"], base["price"])
    if out["crossover_month"] is _MISSING:
        out["crossover_month"] = estimate_crossover_month(inputs, supply_ctx, key_map) if supply_ctx else None
        out["crossover_source"] = "bear_case.estimate_crossover_month" if supply_ctx else "unavailable"
    else:
        out["crossover_source"] = "deterministic_sotp"
    if out["crossover_month"] is not None:
        out["crossover_month"] = int(out["crossover_month"])
    return out


McFn = Callable[[dict[str, Any]], float]


def _mc(mc_fn: McFn | None, inputs: dict[str, Any]) -> float | None:
    return None if mc_fn is None else float(mc_fn(inputs))


def run_bear_case(
    base_inputs: Mapping[str, Any],
    base_sotp: Mapping[str, Any],
    live: Mapping[str, Any],
    *,
    sotp_fn: SotpFn | None = None,
    supply_ctx: Mapping[str, Any] | None = None,
    key_map: Mapping[str, str] | None = None,
    mc_fn: McFn | None = None,
) -> BearCase:
    """Price the four falsification scenarios and the combined worst case.

    ``base_inputs`` is the dict accepted by ``sotp_valuation.deterministic_sotp`` (imported lazily when
    ``sotp_fn`` is None); ``base_sotp`` = sotp_fn(base_inputs); ``live`` = {net_take_bps, hhi_solver,
    solver_fills_attributed, hhi_external, headroom_cross_vm_bps, max_inflation_rate, volume_30d_usd,
    record_30d_usd, confidential_tvl_usd, confidential_tvl_verified} with None for anything unmeasured.
    ``supply_ctx`` (optional) lets this module estimate the crossover month when the SOTP result omits it.
    ``mc_fn`` (optional) returns the Monte Carlo median FDV for an input dict; when given, each scenario also
    carries ``mc_fdv_p50`` / ``mc_drawdown_pct`` next to the deterministic figures. Deterministic; no network.
    """
    if sotp_fn is None:
        from valuo.models.sotp_valuation import (
            deterministic_sotp,  # written in parallel; resolved at call time
        )

        sotp_fn = deterministic_sotp

    base = _read(base_sotp, "base")
    if base["crossover_month"] is _MISSING:
        base["crossover_month"] = estimate_crossover_month(base_inputs, supply_ctx, key_map) if supply_ctx else None
    if base["crossover_month"] is not None:
        base["crossover_month"] = int(base["crossover_month"])
    base_mc = _mc(mc_fn, dict(base_inputs))

    per_scenario = build_perturbations(base_inputs, live, key_map)
    triggers = evaluate_triggers(live, base_inputs, key_map)

    scenarios: list[BearScenario] = []
    for key in SCENARIO_KEYS:
        pert = per_scenario[key]
        inputs, applied, unapplied = _apply(base_inputs, pert, key_map)
        scn = _evaluate(key, inputs, sotp_fn, base, supply_ctx, key_map)
        trig = triggers[key]
        mc = _mc(mc_fn, inputs)
        scenarios.append(
            BearScenario(
                key=key,
                title=_TITLES[key],
                narrative=_narrative(key, base_inputs, live, pert, base, scn, trig, key_map),
                perturbations={k: float(v) for k, v in pert.items()},
                sotp_fdv_p50=scn["fdv"],
                drawdown_pct=scn["drawdown_pct"],
                price_p50=scn["price"],
                crossover_month=scn["crossover_month"],
                **{k: trig[k] for k in ("early_warning_metric", "current_value", "trigger_threshold", "trigger_breached", "monitor_source")},
                # extra fields (OpenModel): provenance of the trigger and what actually reached the model
                trigger_evaluated=trig["trigger_evaluated"],
                monitor_field=trig["monitor_field"],
                trigger_comparator=trig["trigger_comparator"],
                trigger_note=trig["trigger_note"],
                price_drawdown_pct=scn["price_drawdown_pct"],
                fdv_ex_monetary=scn["fdv_ex_monetary"],
                supply_at_horizon_near=scn["supply_at_horizon"],
                crossover_source=scn["crossover_source"],
                perturbations_applied=applied,
                perturbations_unapplied=unapplied,
                fdv_basis="deterministic (median-input) SOTP at perturbed inputs; not the Monte Carlo P50",
                mc_fdv_p50=mc,
                mc_drawdown_pct=(_ratio_change(mc, base_mc) if (mc is not None and base_mc) else None),
                **{k: trig[k] for k in (
                    "secondary_metric", "secondary_value", "secondary_threshold", "secondary_comparator", "secondary_breached", "secondary_evaluated",
                    "hhi_deposit_source_external", "solver_fills_attributed", "solver_fills_sampled", "sample_thin",
                    "hhi_solver_ci90", "primary_status", "trigger_status", "sample_span_s", "min_sample_span_s", "span_sufficient",
                ) if k in trig},
            )
        )

    combined_pert = merge_worst(per_scenario)
    combined_inputs, combined_applied, combined_unapplied = _apply(base_inputs, combined_pert, key_map)
    combined = _evaluate("combined_worst", combined_inputs, sotp_fn, base, supply_ctx, key_map)
    combined_mc = _mc(mc_fn, combined_inputs)

    summary = _summary(base["fdv"], scenarios, combined["fdv"], combined["drawdown_pct"])
    evaluated = [s for s in scenarios if s.trigger_breached is not None and getattr(s, "trigger_evaluated", True)]
    return BearCase(
        base_fdv_p50=base["fdv"],
        scenarios=scenarios,
        combined_worst_fdv=combined["fdv"],
        combined_drawdown_pct=combined["drawdown_pct"],
        falsification_summary=summary,
        # extra fields (OpenModel)
        value_basis="deterministic at median inputs; not a Monte Carlo percentile",
        basis=(
            "base_fdv_p50 / sotp_fdv_p50 / combined_worst_fdv keep their field names for compatibility but are DETERMINISTIC "
            "(median-input) FDVs from deterministic_sotp, not Monte Carlo percentiles; mc_* fields carry the seeded MC medians when computed"
        ),
        base_mc_fdv_p50=base_mc,
        combined_mc_fdv_p50=combined_mc,
        combined_mc_drawdown_pct=(_ratio_change(combined_mc, base_mc) if (combined_mc is not None and base_mc) else None),
        base_price_p50=base["price"],
        base_crossover_month=base["crossover_month"],
        combined_worst_price=combined["price"],
        combined_price_drawdown_pct=combined["price_drawdown_pct"],
        combined_crossover_month=combined["crossover_month"],
        combined_perturbations=combined_pert,
        combined_perturbations_applied=combined_applied,
        combined_perturbations_unapplied=combined_unapplied,
        triggers_breached=sum(1 for s in evaluated if s.trigger_breached is True),
        triggers_evaluated=len(evaluated),
        triggers_unevaluated=[s.key for s in scenarios if s not in evaluated],
        live_metrics={k: live.get(k) for k in (
            "net_take_bps", "hhi_solver", "n_eff_solver", "solver_fills_attributed", "solver_fills_sampled", "hhi_external",
            "hhi_external_ex_ai_agent", "external_receipts_sampled", "sample_span_s",
            "headroom_cross_vm_bps", "max_inflation_rate", "volume_30d_usd", "record_30d_usd", "confidential_tvl_usd", "confidential_tvl_verified",
        )},
        stress_parameters=[a.model_dump() for a in STRESS_PARAMETERS.values()],  # plain dicts: extras are untyped, keep JSON == object
        drawdown_definition=(
            "drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; "
            "price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed"
        ),
    )


# ----------------------------------------------------------------------------- integration helper
def _field(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def live_metrics(forensics: Any, truth: Any, bench: Any | None = None) -> dict[str, Any]:
    """Assemble the ``live`` dict from collector outputs (models or their dict dumps); None where unmeasured."""
    fees = _field(forensics, "fees", {}) or {}
    volume = _field(forensics, "volume", {}) or {}
    records = volume.get("records") or {}
    caller_sample = _field(forensics, "caller_sample", {}) or {}
    solvers = _field(forensics, "solver_concentration", {}) or {}
    headroom_map = _field(bench, "headroom_by_archetype_bps", {}) or {}
    return {
        "net_take_bps": fees.get("net_take_bps"),
        "hhi_solver": solvers.get("hhi_solver"),
        "hhi_solver_ci90": solvers.get("hhi_solver_ci90"),
        "n_eff_solver": solvers.get("n_eff_solver"),
        "solver_fills_attributed": solvers.get("n_fills_attributed"),
        "solver_fills_sampled": solvers.get("n_fills"),
        "hhi_external": _field(forensics, "hhi_external"),
        "hhi_external_ex_ai_agent": caller_sample.get("hhi_external_ex_ai_agent"),
        "external_receipts_sampled": caller_sample.get("external_receipts_sampled"),
        # The cartel note quotes the span of the SOLVER sample (caller pages + method-filtered execute_intents pages) when
        # the audit reports one; older snapshots fall back to the caller-page span.
        "sample_span_s": solvers.get("sample_span_s") if solvers.get("sample_span_s") is not None else caller_sample.get("sample_span_s"),
        "headroom_cross_vm_bps": headroom_map.get("cross_vm"),
        "max_inflation_rate": _field(truth, "max_inflation_rate"),
        "volume_30d_usd": volume.get("30d"),
        "record_30d_usd": records.get("max30dUsd"),
        "confidential_tvl_usd": _field(forensics, "confidential_tvl_usd"),
        "confidential_tvl_verified": bool(_field(forensics, "confidential_tvl_verified", False)),
    }
