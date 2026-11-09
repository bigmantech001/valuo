"""The single registry of labeled assumptions.

Every non-measured model input lives here as an ``Assumption`` (key, default value, unit, plausible
[low, high] range, one-sentence justification citing its source). Models read values through this
registry so the snapshot can list exactly which numbers were assumed versus fetched or derived, and
the web sliders can expose the same ranges. Nothing here is a silent fallback for a failed live fetch:
the four explicit fallbacks (``state_lock_growth_fallback_near_per_day`` = zero credit,
``terminal_multiple_fallback``, ``price_sigma_annual_fallback``, ``volume_sigma_monthly_fallback``) are used
only when every live source is null, are always accompanied by a warning, and are labeled
``source="assumption"`` in the snapshot.
"""
from __future__ import annotations

from collections.abc import Mapping

from valuo.schemas import Assumption

__all__ = [
    "ASSUMPTIONS", "SCENARIO_PRESETS", "BEAR_STRESS_KEYS",
    "get", "value", "keys", "as_list", "with_overrides", "preset", "describe",
]


def _a(key: str, default: float, unit: str, low: float, high: float, justification: str) -> Assumption:
    if not (low <= default <= high):
        raise ValueError(f"assumption {key}: default {default} outside [{low}, {high}]")
    return Assumption(key=key, value=float(default), unit=unit, low=float(low), high=float(high), source="assumption", justification=justification)


_REGISTRY: tuple[Assumption, ...] = (
    _a(
        "svrn_target_inflation", 0.016, "ratio_annual", 0.005, 0.03,
        "SVRN governance proposal to cut the protocol max_inflation_rate from 2.5% to 1.6%; not enacted on-chain "
        "(live EXPERIMENTAL_protocol_config.max_inflation_rate is still [1, 40]).",
    ),
    _a(
        "svrn_glidepath_months", 24, "months", 6, 48,
        "QUANT_PIPELINE_SPEC and TERMINAL_UI_SPEC model the 2.5% -> 1.6% cut as a linear 24-month (730-day) glidepath; "
        "the proposal itself does not fix the phasing.",
    ),
    _a(
        "public_volume_growth_yoy", 0.30, "ratio_yoy", -0.20, 1.50,
        "EXPECTED (mean) public-volume growth: the volume GBM carries the Ito drift ln(1+g) - sigma^2/2 per month, so "
        "E[V_t] = V_0 (1+g)^(t/12) and 30% YoY is the growth of the MEAN path (= the deterministic path); the Monte Carlo "
        "MEDIAN path is lower by exp(-sigma^2 t/2) at the measured monthly sigma (see sotp.calibration.gbm_convention and "
        "volume_terminal_median_usd_day). Default 30% is set well below the trailing-1y DefiLlama near-intents volume growth, "
        "which included incentive-driven months (NEAR@3.33); the slider range spans decay to -20% and 2.5x growth.",
    ),
    _a(
        "confidential_share_target", 0.40, "ratio", 0.05, 0.60,
        "nearstats intents.totalsBreakdown shows confidential ~39% of 30d volume (derived as NEAR total minus public); "
        "40% holds the mix flat rather than extrapolating growth.",
    ),
    _a(
        "confidential_take_bps", 20, "bps", 10, 30,
        "QUANT_PIPELINE_SPEC's institutional MEV-protected shard fee band is 15-25 bps; 20 is the midpoint and no live "
        "confidential fee series exists to verify it.",
    ),
    _a(
        "fee_compression_lambda_monthly", 0.03, "per_month", 0.0, 0.15,
        "Monthly mean-reversion speed of the public take toward the competitive floor; 3%/month is a ~23-month half-life, "
        "in line with bridge-fee compression observed across Across/Relay since 2023.",
    ),
    _a(
        "confidential_compression_divisor", 3, "x", 1, 10,
        "MODEL_DESIGN section 4.2 sets lambda_conf = lambda / 3: confidential execution competes on privacy rather than price, "
        "so fees compress slower than public routing.",
    ),
    _a(
        "discount_rate", 0.25, "ratio_annual", 0.10, 0.40,
        "25% is a venture-stage crypto hurdle rate; Dragonfly / Electric Capital style memos use 20-30% for pre-maturity "
        "protocol cash flows.",
    ),
    _a(
        "terminal_multiple_floor", 8, "x_fdv_to_revenue", 2, 20,
        "Guardrail on the live peer-median FDV/revenue multiple: 8x is roughly a mature L1 fee multiple floor; clipping is "
        "logged in SotpValuation.calibration.",
    ),
    _a(
        "terminal_multiple_cap", 60, "x_fdv_to_revenue", 20, 150,
        "Guardrail so a single high-multiple peer (ETH/SOL trade above 100x revenue on DefiLlama) cannot drive the terminal "
        "value; 60x caps the peer median.",
    ),
    _a(
        "terminal_multiple_fallback", 30, "x_fdv_to_revenue", 8, 60,
        "Used ONLY when the live peer FDV/revenue median AND the FDV/fees median are both null (CoinGecko outage / 429): "
        "30x is the midpoint of listed-exchange and L1 REV multiples (roughly 8x mature L1 fee multiples to 60x the guardrail "
        "cap); the run records a warning, calibration.terminal_multiple_source = 'assumption' and Engine 1 is flagged "
        "assumption-heavy. Never used when a live multiple exists.",
    ),
    _a(
        "price_sigma_annual_fallback", 1.0, "ratio_annual", 0.6, 1.6,
        "Used ONLY when both price series (nearstats price-history 1y and the coins.llama.fi daily chart) are unavailable: "
        "100% annualized volatility is the centre of the 60-160% band large-cap alt-L1 tokens have realized over 1y windows; "
        "the run records a warning and sotp.inputs.sigma_price_annual is labeled source 'assumption'.",
    ),
    _a(
        "volume_sigma_monthly_fallback", 0.35, "ratio_monthly", 0.15, 0.6,
        "Used ONLY when the DefiLlama near-intents dexs chart is unavailable and neither volume_monthly_sigma nor "
        "volume_daily_sigma could be measured (the 30-day volume itself then comes from nearstats): 0.35 is the class of "
        "the measured monthly log-return sigma of 30-day volume aggregates (0.27-0.36 across windows in the committed "
        "snapshots); the run records a warning and sotp.inputs.sigma_volume_monthly is labeled source 'assumption'. "
        "A chart outage never exits the run.",
    ),
    _a(
        "confidential_multiple_haircut", 0.7, "ratio", 0.3, 1.0,
        "nearstats flags intents.protocolMetrics.confidentialTvlUsd as sourceStatus 'unverified'; a 30% haircut on Engine 2's "
        "terminal multiple prices that verification risk.",
    ),
    _a(
        "kb_per_agent_vault", 20, "KB", 5, 50,
        "A NEAR account with a few access keys and small contract state costs 5-50 KB; at storage_amount_per_byte = 1e19 yocto "
        "20 KB locks 0.2 NEAR per agent vault.",
    ),
    _a(
        "state_lock_growth_fallback_near_per_day", 0.0, "NEAR_per_day", 0.0, 10_000.0,
        "Used ONLY if the archival measurement of storage growth fails; default 0 gives no credit to the sink and the run "
        "records a warning rather than inventing a number.",
    ),
    _a(
        "buyback_capture_ratio_override", -1.0, "ratio", -1.0, 1.0,
        "-1 means use the live DefiLlama near-intents dailyHoldersRevenue / fees capture ratio (~35%, reconciles with "
        "revenue.near.org); any value in [0, 1] overrides it for slider scenarios.",
    ),
    _a(
        "near_price_drift_annual", 0.0, "ratio_annual", -0.5, 1.0,
        "Zero drift: the model does not forecast NEAR price to value the token; price enters only to convert USD buybacks "
        "into NEAR units (MODEL_DESIGN section 4.2).",
    ),
    _a(
        "public_take_floor_bps", 0.5, "bps", 0.0, 5.0,
        "MODEL_DESIGN 4.2 hard floor for the public take: tau_floor = max(this, min(live public take, live cross-VM headroom)). "
        "It is the floor on its own only when the execution benchmark did not run, and the run then records a warning.",
    ),
    _a(
        "confidential_volume_sigma_multiplier", 1.0, "x", 1.0, 3.0,
        "Multiplier on the confidential-volume GBM sigma applied while nearstats flags confidentialTvlUsd as unverified "
        "(MODEL_DESIGN 4.2). Default 1.0 = no widening, because no measured dispersion factor exists; Engine 2 stays "
        "assumption_heavy regardless.",
    ),
    # ---- bear-case stress definitions (MODEL_DESIGN 4.3 / QUANT_PIPELINE_SPEC Model C); prefixed bear_* ----
    _a(
        "bear_fee_race_tau_pub_bps", 0.01, "bps", 0.0, 1.0,
        "1 pip is the bare intents.near contract fee once third-party frontends route around near.com and its 25 bps / "
        "10-20 bps partner fees (QUANT_PIPELINE_SPEC Model C.1, MODEL_DESIGN 4.3.1).",
    ),
    _a(
        "bear_fee_race_tau_conf_bps", 5.0, "bps", 0.0, 10.0,
        "Confidential execution repriced to 5 bps, a quarter of the 20 bps default, once public routing is free (MODEL_DESIGN 4.3.1).",
    ),
    _a(
        "bear_fee_race_trigger_net_take_bps", 3.0, "bps", 1.0, 5.0,
        "Early warning: DefiLlama near-intents 30d net take below 3 bps (live ~5.6 bps class) means compression is already past "
        "the mid-point to zero (MODEL_DESIGN 4.3.1).",
    ),
    _a(
        "bear_decay_v_pub_multiplier", 0.40, "ratio", 0.10, 1.0,
        "Public volume -60%: QUANT_PIPELINE_SPEC Model C.3 sizes the NEAR@3.33 mercenary-liquidity unwind at -60% of 30d volume.",
    ),
    _a(
        "bear_decay_v_conf_multiplier", 0.30, "ratio", 0.10, 1.0,
        "Confidential volume -70%: the shard's TVL is flagged unverified by nearstats, so its volume is assumed more "
        "incentive-dependent than public flow (MODEL_DESIGN 4.3.3).",
    ),
    _a(
        "bear_decay_tvl_multiplier", 0.30, "ratio", 0.10, 1.0,
        "Confidential TVL -70% (QUANT_PIPELINE_SPEC Model C.3).",
    ),
    _a(
        "bear_decay_trigger_volume_drawdown", -0.40, "ratio", -0.80, -0.10,
        "Early warning: 30d volume more than 40% below the 30d record (nearstats records.max30dUsd) (MODEL_DESIGN 4.3.3).",
    ),
    _a(
        "bear_cartel_hhi_external", 3500.0, "hhi", 2500.0, 10000.0,
        "HHI 3,500 is two actors at ~40% each plus a tail; the US horizontal-merger guideline calls > 2,500 highly concentrated "
        "(QUANT_PIPELINE_SPEC Model C.4).",
    ),
    _a(
        "bear_cartel_headroom_bps", -2.0, "bps", -10.0, 0.0,
        "Cartel spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM; 1Click must give the same 2 bps "
        "of take back to keep flow (MODEL_DESIGN 4.3.4).",
    ),
    _a(
        "bear_tau_floor_bps", 0.5, "bps", 0.0, 2.0,
        "Floor on the cartel scenario's public take give-back: max(0.5 bps, live public take - 2 bps) (MODEL_DESIGN 4.2 competitive floor).",
    ),
    _a(
        "bear_cartel_lambda_monthly", 0.15, "per_month", 0.0, 0.15,
        "Compression speed set to the registry's high bound for fee_compression_lambda_monthly (0.15/month): losing the spread "
        "means order flow leaves at the fastest plausible rate.",
    ),
    _a(
        "sensitivity_measured_lookback_windows", 6, "windows", 3, 12,
        "Tornado range for measured Intents ratios (gross take, holder capture): min..max over this many trailing non-overlapping "
        "30-day windows of the DefiLlama daily series. Six windows covers the period since the 2026-02-23 buyback start; earlier "
        "windows mix a different revenue regime.",
    ),
    _a(
        "sensitivity_unmeasured_band", 0.25, "ratio", 0.10, 0.50,
        "Tornado range (+/- this fraction of the measured value) for live inputs that have no measured dispersion in the snapshot "
        "(L1 gas burn, state-lock growth, cross-VM headroom). A labeled width, not a confidence interval.",
    ),
    # ---- data-quality guards and evidence grading (intents_forensics split guard, reproduce scorecard) ----
    _a(
        "confidential_share", 0.40, "ratio", 0.15, 0.60,
        "FALLBACK ONLY, used when the live nearstats public/confidential split is implausible (intents_forensics."
        "volume.confidential_share_status = implausible_fallback). The last plausible split, nearstats totalsBreakdown as of "
        "2026-10-31, read $1.58B confidential of $3.86B 30d (40.9%); from the 2026-11-07 split onward the explorer public tile "
        "equals the NEAR total and confidential all-time volume reads $0 while confidential TVL is ~$143M, i.e. a source "
        "change, not a measurement. Range: the bear preset target (15%) to confidential_share_target's high bound (60%).",
    ),
    _a(
        "confidential_share_plausibility_floor", 0.01, "ratio", 0.001, 0.05,
        "A reported confidential 30d share below 1% is treated as a broken split (not a measurement) when nearstats' own "
        "payload contradicts it: confidential TVL > 0 with ~zero all-time confidential volume, the confidential stream "
        "reporting ok, or a split check whose detail says the split is withheld. With ~$140M of confidential TVL a <1% share "
        "would mean the shard turns over less than ~0.3x its TVL per month.",
    ),
    _a(
        "solver_sample_min_span_s", 3600.0, "seconds", 900.0, 86400.0,
        "Minimum wall-clock span of the solver sample before the cartelization trigger may grade HHI_solver breached or clear. "
        "The method-filtered execute_intents pages and settlement-hub legs typically cover a window of minutes; fills inside a "
        "2-minute window are serially correlated (the same solvers quote consecutive blocks), and the bootstrap CI resamples only "
        "within that window, so it measures within-window noise, not how concentration varies across hours. One hour is the "
        "shortest span that spans several quoting cycles; the range runs from 15 minutes to one day.",
    ),
    _a(
        "solver_sample_pages", 8, "pages", 2, 10,
        "Number of method-filtered NearBlocks execute_intents pages (50 receipts each) in the stratified solver sample: the "
        "newest page plus pages placed at even time offsets back to solver_sample_target_span_s. Each page is one block of "
        "the page-block bootstrap, so more pages tighten the HHI_solver CI. Unauthenticated NearBlocks served 5 solver calls "
        "after the caller walk and refused the 6th (HTTP 429, 2026-11-08), so the walk runs in chunks of 5 one rate window "
        "apart: 6 to 10 pages cost the same single extra ~62 s window, and 8 = 5 + 3 leaves headroom in the second window. "
        "~400 receipts spread over hours versus the 4 contiguous pages (~3 minutes) used before.",
    ),
    _a(
        "solver_sample_target_span_s", 21600.0, "seconds", 3600.0, 43200.0,
        "Target time depth of the deepest solver-sample page (6 h), reached by jumping NearBlocks' id cursor rather than "
        "walking page=N (page >= 2 without a cursor answered HTTP 520 after 50 s on 2026-11-08). Deeper cursors cost "
        "latency: 1.4 s at ~5 h, 2.0 s at ~11 h, 14 s at ~41 h, 40 s at ~7 days (measured 2026-11-08). 6 h is 6x the "
        "solver_sample_min_span_s floor, so a misaimed cursor still clears it, and spans the Asia/Europe/US session "
        "hand-offs inside one run; the range runs from the 1 h minimum to 12 h (latency still ~2 s).",
    ),
    _a(
        "evidence_materiality_share", 0.10, "ratio", 0.05, 0.25,
        "Scorecard threshold: a flow share (confidential volume, AI-agent-labeled receipts) is called 'material' at >= 10% "
        "of the measured total; below it the claim is graded NOT_SUPPORTED. A conventional materiality line, not a fitted value.",
    ),
)

# Keys a model may read as a group (bear_case.STRESS_PARAMETERS); every key must exist in the registry.
BEAR_STRESS_KEYS: tuple[str, ...] = (
    "bear_fee_race_tau_pub_bps", "bear_fee_race_tau_conf_bps", "bear_fee_race_trigger_net_take_bps",
    "bear_decay_v_pub_multiplier", "bear_decay_v_conf_multiplier", "bear_decay_tvl_multiplier",
    "bear_decay_trigger_volume_drawdown", "bear_cartel_hhi_external", "bear_cartel_headroom_bps",
    "bear_tau_floor_bps", "bear_cartel_lambda_monthly",
)

ASSUMPTIONS: dict[str, Assumption] = {a.key: a for a in _REGISTRY}

# Scenario presets are partial overrides, not new assumptions; every key must exist in ASSUMPTIONS.
SCENARIO_PRESETS: dict[str, dict[str, float]] = {
    "base": {},
    "bull": {
        "public_volume_growth_yoy": 0.80,
        "confidential_share_target": 0.50,
        "fee_compression_lambda_monthly": 0.01,
        "confidential_take_bps": 25,
    },
    "bear": {
        "public_volume_growth_yoy": -0.20,
        "confidential_share_target": 0.15,
        "fee_compression_lambda_monthly": 0.10,
        "confidential_take_bps": 10,
        "confidential_multiple_haircut": 0.4,
    },
}


def get(key: str) -> Assumption:
    """Return the registered Assumption for ``key`` (KeyError if unknown)."""
    try:
        return ASSUMPTIONS[key]
    except KeyError as exc:
        raise KeyError(f"unknown assumption {key!r}; known: {sorted(ASSUMPTIONS)}") from exc


def value(key: str, overrides: Mapping[str, Assumption] | None = None) -> float:
    """Value of ``key`` from ``overrides`` (a registry from with_overrides) when present, else the default."""
    if overrides is not None and key in overrides:
        return overrides[key].value
    return get(key).value


def keys() -> list[str]:
    return list(ASSUMPTIONS)


def as_list(overrides: Mapping[str, Assumption] | None = None) -> list[Assumption]:
    """All assumptions (optionally an overridden registry) in registration order, as copies."""
    source = overrides if overrides is not None else ASSUMPTIONS
    return [source[k].model_copy() for k in ASSUMPTIONS if k in source]


def with_overrides(overrides: Mapping[str, float] | None, *, clamp: bool = False) -> dict[str, Assumption]:
    """Copy of the registry with ``overrides`` applied.

    Unknown keys raise KeyError. Values outside [low, high] raise ValueError unless ``clamp=True``, in
    which case they are clipped to the range. Overridden entries keep ``source="assumption"`` and their
    justification gains an ``(override: <default> -> <value>)`` suffix so the snapshot shows the change.
    """
    registry = {k: a.model_copy() for k, a in ASSUMPTIONS.items()}
    for key, raw in (overrides or {}).items():
        base = get(key)
        v = float(raw)
        if not (base.low <= v <= base.high):
            if not clamp:
                raise ValueError(f"assumption {key}={v} outside [{base.low}, {base.high}]")
            v = min(max(v, base.low), base.high)
        if v != base.value:
            registry[key] = base.model_copy(
                update={"value": v, "justification": f"{base.justification} (override: {base.value:g} -> {v:g})"}
            )
    return registry


def preset(name: str, *, clamp: bool = False) -> dict[str, Assumption]:
    """Registry with a named scenario preset applied ("base" | "bull" | "bear")."""
    if name not in SCENARIO_PRESETS:
        raise KeyError(f"unknown preset {name!r}; known: {sorted(SCENARIO_PRESETS)}")
    return with_overrides(SCENARIO_PRESETS[name], clamp=clamp)


def describe() -> list[dict[str, object]]:
    """Plain dicts for the memo / web sliders."""
    return [a.model_dump() for a in as_list()]


for _preset_name, _preset in SCENARIO_PRESETS.items():
    for _k in _preset:
        if _k not in ASSUMPTIONS:
            raise RuntimeError(f"preset {_preset_name} references unknown assumption {_k}")
for _k in BEAR_STRESS_KEYS:
    if _k not in ASSUMPTIONS:
        raise RuntimeError(f"BEAR_STRESS_KEYS references unknown assumption {_k}")
if ASSUMPTIONS["bear_cartel_lambda_monthly"].value != ASSUMPTIONS["fee_compression_lambda_monthly"].high:
    raise RuntimeError("bear_cartel_lambda_monthly must equal the high bound of fee_compression_lambda_monthly")
