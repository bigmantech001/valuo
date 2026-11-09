"""Reverse valuation: what the market FDV requires of each model input, next to its evidence.

Pure, deterministic, no network. Runs the SAME engine as the snapshot (``sotp_valuation.deterministic_sotp``)
on inputs rebuilt from a snapshot dict exactly as ``build_inputs`` builds them (and as the web port
``web/src/lib/quantClient.ts::baseInputsFromSnapshot`` rebuilds them). One parameter moves at a time, all
others at base, and a bracketed root finder (``scipy.optimize.brentq``) finds the value at which the
deterministic (expected-path) FDV equals the current market FDV. When the root is outside the search
bounds the solve returns ``required_value = None`` with the reason; nothing is extrapolated.

Basis: the deterministic engine is the model's EXPECTED path (mean-matching GBM), so every required value
here is the expected-path requirement. The Monte Carlo P50 is lower by lognormal convexity; it is reported
for context (``base_fdv_mc_p50_usd``) but is not what the solves invert.

The input reconstruction is split in two layers so the sensitivity module can perturb primitives:
  ``primitives_from_snapshot(snapshot)`` -> the primitive parameters (measured / assumption / derived)
  ``compose_inputs(primitives)``         -> the ``deterministic_sotp`` input dict, re-deriving
      tau_pub_0 (fee reconciliation), tau_floor, g_pub, g_conf and lambda_conf exactly as ``build_inputs``.

CLI: ``uv run python -m valuo.models.market_implied artifacts/latest_snapshot.json`` prints the result as JSON.
"""
from __future__ import annotations

import json
import math
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from scipy.optimize import brentq

from valuo import assumptions as A
from valuo.models.sotp_valuation import (
    HARD_FLOOR_BPS,
    REGIME_GLIDEPATH,
    REGIME_STATUS_QUO,
    deterministic_sotp,
)

__all__ = [
    "SEARCH_BOUNDS", "primitives_from_snapshot", "compose_inputs", "inputs_from_snapshot", "fdv_at",
    "trailing_volume_growth", "run_market_implied", "load_snapshot", "main",
]

# Economically sane search bounds for each solve (value space of the parameter). A root outside these is
# reported as unreachable; these bounds never enter a valuation.
SEARCH_BOUNDS: dict[str, tuple[float, float]] = {
    "public_volume_growth_yoy": (-0.99, 10.0),     # -99%/yr .. +1,000%/yr expected growth
    "tau_pub_bps": (0.0, 200.0),                    # gross public take at t=0, bps (2% of notional)
    "terminal_multiple": (0.0, 10_000.0),           # FDV / annual holder revenue
    "discount_rate": (0.0, 1.0),                    # annual hurdle rate; negative rates are not sane
    "confidential_share_target": (0.0, 0.99),       # build_inputs clips the target to 0.99
    "holder_revenue_scale": (0.0, 1_000.0),         # multiplier on starting public + confidential volume
}

TOLERANCE_REL = 1e-9

SHORT_LABELS: dict[str, str] = {
    "public_volume_growth_yoy": "volume growth",
    "tau_pub_bps": "public take",
    "terminal_multiple": "terminal multiple",
    "discount_rate": "discount rate",
    "confidential_share_target": "confidential share",
    "holder_revenue_scale": "year-3 holder revenue",
}


# ============================================================================ snapshot -> primitives -> inputs
def _num(x: Any) -> float | None:
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _assumption_value(snapshot: Mapping[str, Any], key: str) -> float:
    """Registry value used by the snapshot run (snapshot.assumptions / sotp.inputs), else the current registry."""
    sotp_inputs = (snapshot.get("sotp") or {}).get("inputs") or {}
    entry = sotp_inputs.get(key)
    if isinstance(entry, Mapping) and _num(entry.get("value")) is not None:
        return float(entry["value"])
    for a in snapshot.get("assumptions") or []:
        if isinstance(a, Mapping) and a.get("key") == key and _num(a.get("value")) is not None:
            return float(a["value"])
    return A.value(key)


def _assumption_range(snapshot: Mapping[str, Any], key: str) -> tuple[float, float]:
    for a in snapshot.get("assumptions") or []:
        if isinstance(a, Mapping) and a.get("key") == key:
            lo, hi = _num(a.get("low")), _num(a.get("high"))
            if lo is not None and hi is not None:
                return lo, hi
    a = A.get(key)
    return a.low, a.high


def primitives_from_snapshot(snapshot: Mapping[str, Any], regime: str = REGIME_GLIDEPATH) -> dict[str, Any]:
    """Primitive model parameters as the snapshot run used them. Raises ValueError when a required field is null."""
    sotp = snapshot.get("sotp") or {}
    cal = sotp.get("calibration") or {}
    missing: list[str] = []

    def need(label: str, v: Any) -> float:
        n = _num(v)
        if n is None:
            missing.append(label)
            return float("nan")
        return n

    paths = cal.get("regime_inflation_paths_annual") or {}
    path = paths.get(regime)
    if not isinstance(path, list) or not path:
        missing.append(f"sotp.calibration.regime_inflation_paths_annual.{regime}")
        path = []
    scale = need("sotp.calibration.issuance_scale_measured_over_path", cal.get("issuance_scale_measured_over_path"))
    sq = paths.get(REGIME_STATUS_QUO)
    window_days = _num(cal.get("take_rate_window_days")) or _num((snapshot.get("intents_forensics") or {}).get("fees", {}).get("take_rate_window_days")) or 30.0
    p: dict[str, Any] = {
        "horizon_months": int(need("sotp.horizon_months", sotp.get("horizon_months"))) if _num(sotp.get("horizon_months")) else 0,
        "window_days": window_days,
        "v_pub_30d_usd": need("sotp.calibration.v_pub_30d_usd", cal.get("v_pub_30d_usd")),
        "v_conf_30d_usd": need("sotp.calibration.v_conf_30d_usd", cal.get("v_conf_30d_usd")),
        "gross_fees_30d_usd": need("sotp.calibration.gross_fees_30d_usd", cal.get("gross_fees_30d_usd")),
        "alpha_capture": need("sotp.calibration.alpha_capture", cal.get("alpha_capture")),
        "tau_conf_bps": need("sotp.calibration.tau_conf_start_bps", cal.get("tau_conf_start_bps")),
        "tau_pub_bps": None,  # None -> reconciled to live fees exactly as build_inputs
        "public_take_floor_bps": _num(cal.get("public_take_floor_bps")) if _num(cal.get("public_take_floor_bps")) is not None else _assumption_value(snapshot, "public_take_floor_bps"),
        "headroom_cross_vm_bps": _num(cal.get("headroom_cross_vm_bps")),
        "terminal_multiple": need("sotp.calibration.terminal_multiple_used", cal.get("terminal_multiple_used")),
        "discount_rate": need("sotp.discount_rate", sotp.get("discount_rate")),
        "conf_haircut": _assumption_value(snapshot, "confidential_multiple_haircut"),
        "gas_burn_near_day": need("sotp.calibration.gas_burn_near_day", cal.get("gas_burn_near_day")),
        "state_lock_near_day": need("sotp.calibration.state_lock_near_day", cal.get("state_lock_near_day")),
        "price_usd": need("sotp.calibration.price_usd", cal.get("price_usd")),
        "total_supply": need("near_rpc.total_supply_near", (snapshot.get("near_rpc") or {}).get("total_supply_near")),
        "issuance_rate_path": [float(x) * scale for x in path],
        "supply_at_horizon": _num((cal.get("supply_at_horizon_by_regime") or {}).get(regime)),
        "max_inflation_rate": float(sq[0]) if isinstance(sq, list) and sq else None,
        "svrn_glidepath_months": _assumption_value(snapshot, "svrn_glidepath_months"),
        "issuance_scale": scale,
        "public_volume_growth_yoy": _assumption_value(snapshot, "public_volume_growth_yoy"),
        "confidential_share_target": need("sotp.calibration.confidential_share_target", cal.get("confidential_share_target")),
        "lambda_pub": need("sotp.calibration.lambda_pub_monthly", cal.get("lambda_pub_monthly")),
        "confidential_compression_divisor": _assumption_value(snapshot, "confidential_compression_divisor"),
        "price_drift_annual": _assumption_value(snapshot, "near_price_drift_annual"),
        "volume_scale": 1.0,
        "current_fdv_usd": need("sotp.current_fdv_usd", sotp.get("current_fdv_usd") or cal.get("current_fdv_usd")),
    }
    if missing:
        raise ValueError(f"market_implied: snapshot is missing required fields: {', '.join(missing)}")
    return p


def _reconciled_tau_pub(p: Mapping[str, Any]) -> float:
    v_pub, v_conf, fees = float(p["v_pub_30d_usd"]), float(p["v_conf_30d_usd"]), float(p["gross_fees_30d_usd"])
    v_total = v_pub + v_conf
    blended = fees / v_total * 1e4 if v_total > 0 else 0.0
    if v_pub <= 0:
        return blended
    tau = (fees - v_conf * float(p["tau_conf_bps"]) / 1e4) / v_pub * 1e4
    return blended if tau < HARD_FLOOR_BPS else tau


def compose_inputs(p: Mapping[str, Any]) -> dict[str, Any]:
    """``deterministic_sotp`` inputs from primitives, re-deriving every derived input as ``build_inputs`` does.

    tau_pub_0 = (fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d x 1e4 unless ``tau_pub_bps`` is given;
    tau_floor = max(public_take_floor_bps, min(tau_pub_0, headroom_cross_vm)) (registry floor alone if unmeasured);
    g_pub = (1 + g_yoy)^(1/12) - 1; g_conf moves the confidential share linearly in odds to the target by H;
    lambda_conf = lambda_pub / divisor. ``volume_scale`` multiplies starting volumes after the take is reconciled.
    """
    horizon = int(p["horizon_months"])
    window = float(p["window_days"])
    v_pub_30d, v_conf_30d = float(p["v_pub_30d_usd"]), float(p["v_conf_30d_usd"])
    v_total = v_pub_30d + v_conf_30d
    tau_pub0 = float(p["tau_pub_bps"]) if p.get("tau_pub_bps") is not None else _reconciled_tau_pub(p)
    hard = float(p["public_take_floor_bps"])
    headroom = p.get("headroom_cross_vm_bps")
    floor = max(hard, min(tau_pub0, float(headroom))) if headroom is not None else hard
    g_yoy = float(p["public_volume_growth_yoy"])
    if g_yoy <= -1.0:
        raise ValueError("public_volume_growth_yoy must be > -1")
    g_pub = (1.0 + g_yoy) ** (1.0 / 12.0) - 1.0
    s0 = v_conf_30d / v_total if v_total > 0 else 0.0
    s_target = min(max(float(p["confidential_share_target"]), 0.0), 0.99)
    if 0.0 < s0 < 1.0 and v_pub_30d > 0:
        odds0 = s0 / (1.0 - s0)
        odds_h = s_target / (1.0 - s_target)
        g_conf = ((1.0 + g_pub) ** horizon * odds_h / odds0) ** (1.0 / horizon) - 1.0
    else:
        g_conf = g_pub
    lam = float(p["lambda_pub"])
    k = float(p.get("volume_scale", 1.0))
    price = float(p["price_usd"])
    return {
        "v_pub_usd_day": v_pub_30d / window * k,
        "v_conf_usd_day": v_conf_30d / window * k,
        "tau_pub_bps": tau_pub0,
        "tau_conf_bps": float(p["tau_conf_bps"]),
        "alpha_capture": float(p["alpha_capture"]),
        "discount_rate": float(p["discount_rate"]),
        "terminal_multiple": float(p["terminal_multiple"]),
        "conf_haircut": float(p["conf_haircut"]),
        "gas_burn_usd_day": float(p["gas_burn_near_day"]) * price,
        "state_lock_near_day": float(p["state_lock_near_day"]),
        "price_usd": price,
        "total_supply": float(p["total_supply"]),
        "issuance_rate_path": list(p["issuance_rate_path"]),
        "growth_monthly_pub": g_pub,
        "growth_monthly_conf": g_conf,
        "lambda_pub": lam,
        "lambda_conf": lam / max(float(p["confidential_compression_divisor"]), 1e-9),
        "tau_floor_bps": floor,
        "horizon_months": horizon,
        "price_drift_annual": float(p.get("price_drift_annual") or 0.0),
        "supply_at_horizon": p.get("supply_at_horizon"),
        "svrn_target_inflation": None,
        "max_inflation_rate": p.get("max_inflation_rate"),
        "svrn_glidepath_months": p.get("svrn_glidepath_months"),
        "issuance_scale": p.get("issuance_scale"),
    }


def inputs_from_snapshot(snapshot: Mapping[str, Any], regime: str = REGIME_GLIDEPATH) -> dict[str, Any]:
    """The base ``deterministic_sotp`` inputs of a snapshot (reproduces sotp.calibration.deterministic_base)."""
    return compose_inputs(primitives_from_snapshot(snapshot, regime))


def fdv_at(p: Mapping[str, Any], **overrides: Any) -> float:
    """Deterministic FDV with primitive ``overrides`` applied (all else at ``p``)."""
    q = dict(p)
    q.update(overrides)
    return float(deterministic_sotp(compose_inputs(q))["fdv_total"])


# ============================================================================ evidence
def trailing_volume_growth(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    """Trailing-12-month growth of NEAR Intents 30-day volume, from data already in the snapshot.

    Primary: DefiLlama daily series (intents_forensics.fees.daily_series): last 30 days vs the 30 days ending
    one year earlier. Fallback: the monthly log returns of 30-day aggregates (sotp.calibration), annualised.
    """
    fees = (snapshot.get("intents_forensics") or {}).get("fees") or {}
    series = fees.get("daily_series")
    cols = fees.get("daily_series_columns") or ["ts_unix_s", "fees_usd", "revenue_usd", "volume_usd"]
    if isinstance(series, list) and len(series) >= 365 and "volume_usd" in cols:
        iv = cols.index("volume_usd")
        vols = [_num(r[iv]) for r in series]
        last = vols[-30:]
        prior = vols[-365:-335]
        if all(v is not None for v in last + prior) and sum(prior) > 0:
            return {
                "value": sum(last) / sum(prior) - 1.0,
                "last_30d_usd": sum(last), "prior_year_30d_usd": sum(prior),
                "source": "DefiLlama dexs/near-intents daily volume (intents_forensics.fees.daily_series): last 30 days vs the 30 days ending 335 days earlier",
            }
    cal = (snapshot.get("sotp") or {}).get("calibration") or {}
    rets = cal.get("sigma_volume_monthly_log_returns")
    if isinstance(rets, list) and rets and all(_num(r) is not None for r in rets):
        n = len(rets)
        return {
            "value": math.exp(sum(rets) * 12.0 / n) - 1.0,
            "n_monthly_returns": n,
            "source": f"sotp.calibration.sigma_volume_monthly_log_returns: {n} monthly log returns of 30-day volume, annualised",
        }
    return None


def _peer_multiples(snapshot: Mapping[str, Any]) -> list[tuple[str, float]]:
    out = []
    for peer in (snapshot.get("comps") or {}).get("peers") or []:
        fdv, rev = _num(peer.get("fdv_usd")), _num(peer.get("annualized_revenue_usd"))
        if fdv and rev and rev > 0:
            out.append((str(peer.get("symbol") or peer.get("slug")), fdv / rev))
    return out


# ============================================================================ formatting
def _usd(x: float) -> str:
    a = abs(x)
    if a >= 1e9:
        return f"${x / 1e9:,.2f}B"
    if a >= 1e6:
        return f"${x / 1e6:,.0f}M"
    if a >= 1e3:
        return f"${x / 1e3:,.0f}K"
    return f"${x:,.2f}"


def _pct(x: float) -> str:
    return f"{x * 100:,.0f}%"


def _fmt(x: float, unit: str) -> str:
    if unit in ("ratio_yoy", "ratio_annual", "ratio"):
        return _pct(x)
    if unit == "bps":
        return f"{x:,.2f} bps"
    if unit == "x":
        return f"{x:,.0f}x"
    if unit == "usd_per_year":
        return _usd(x) + "/yr"
    return f"{x:,.4g}"


# ============================================================================ solver
def _solve(f: Callable[[float], float], target: float, lo: float, hi: float) -> tuple[float | None, str]:
    """Root of f(x) = target on [lo, hi].

    Returns (x, "ok"), or (None, "short") when the FDV stays below the target at both bounds, or
    (None, "over") when it stays above it at both bounds.
    """
    flo, fhi = f(lo) - target, f(hi) - target
    if flo == 0.0:
        return lo, "ok"
    if fhi == 0.0:
        return hi, "ok"
    if flo * fhi > 0:
        return None, "short" if flo < 0 else "over"
    x = brentq(lambda v: f(v) - target, lo, hi, xtol=1e-12, rtol=1e-12, maxiter=500)
    return float(x), "ok"


def _row(
    *, param: str, label: str, unit: str, base_value: float, required: float | None, reason: str | None,
    evidence: dict[str, Any] | None, harder: str, fdv_check: float | None, target: float, verdict: str,
) -> dict[str, Any]:
    ev_val = _num((evidence or {}).get("value"))
    rel: dict[str, Any] = {"ratio": None, "difference": None, "within_evidence": None}
    if required is not None and ev_val is not None:
        rel["difference"] = required - ev_val
        if ev_val > 0 and required > 0:
            rel["ratio"] = required / ev_val
        rel["within_evidence"] = required <= ev_val if harder == "higher" else required >= ev_val
    return {
        "param": param, "label": label, "short_label": SHORT_LABELS[param], "unit": unit, "base_value": base_value,
        "required_value": required, "reachable": required is not None, "reason": reason,
        "search_bounds": list(SEARCH_BOUNDS[param]), "harder_direction": harder,
        "evidence": evidence, "required_vs_evidence": rel,
        "fdv_at_required_usd": fdv_check,
        "check_rel_error": (abs(fdv_check / target - 1.0) if fdv_check is not None and target else None),
        "verdict": verdict,
    }


def run_market_implied(snapshot: Mapping[str, Any], *, current_fdv_usd: float | None = None) -> dict[str, Any]:
    """Solve, one parameter at a time, the value that makes the deterministic model FDV equal the market FDV."""
    p = primitives_from_snapshot(snapshot)
    target = float(current_fdv_usd) if current_fdv_usd is not None else float(p["current_fdv_usd"])
    base_inputs = compose_inputs(p)
    base = deterministic_sotp(base_inputs)
    base_fdv = float(base["fdv_total"])
    horizon = int(p["horizon_months"])
    years = horizon / 12.0
    sotp = snapshot.get("sotp") or {}
    cal = sotp.get("calibration") or {}
    bench = snapshot.get("execution_bench") or {}
    vol = (snapshot.get("intents_forensics") or {}).get("volume") or {}
    rows: list[dict[str, Any]] = []
    gap_word = "closes the gap" if target > base_fdv else "matches the market"

    def unreachable(side: str, param: str, unit: str, noun: str, increasing: bool = True) -> str:
        lo, hi = SEARCH_BOUNDS[param]
        if (side == "short") == increasing:
            return f"not reachable below {_fmt(hi, unit)} {noun} (search bound)"
        return f"not reachable above {_fmt(lo, unit)} {noun} (search bound)"

    # 1. expected annual public-volume growth --------------------------------------------------------
    param, unit = "public_volume_growth_yoy", "ratio_yoy"
    req, side = _solve(lambda x: fdv_at(p, public_volume_growth_yoy=x), target, *SEARCH_BOUNDS[param])
    tg = trailing_volume_growth(snapshot)
    ev = {"value": tg["value"], "label": "trailing-12-month NEAR Intents 30-day volume growth", "source": tg["source"]} if tg else None
    reason = None if req is not None else unreachable(side, param, unit, "annual growth")
    ev_txt = f"; trailing-12-month Intents volume growth was {_pct(tg['value'])}" if tg else "; no trailing growth series in the snapshot"
    verdict = (
        f"Justifying {_usd(target)} needs {_pct(req)} expected annual public-volume growth for {years:g} years (base {_pct(p[param])}){ev_txt}."
        if req is not None else
        f"No expected growth rate up to {_pct(SEARCH_BOUNDS[param][1])}/yr {gap_word} at the other base inputs{ev_txt}."
    )
    rows.append(_row(param=param, label="Expected annual public-volume growth (3-year path)", unit=unit, base_value=p[param],
                     required=req, reason=reason, evidence=ev, harder="higher",
                     fdv_check=fdv_at(p, **{param: req}) if req is not None else None, target=target, verdict=verdict))

    # 2. gross public take rate at t=0 ----------------------------------------------------------------
    param, unit = "tau_pub_bps", "bps"
    tau0 = float(base_inputs["tau_pub_bps"])
    req, side = _solve(lambda x: fdv_at(p, tau_pub_bps=x), target, *SEARCH_BOUNDS[param])
    ceiling = _num(bench.get("competitive_fee_ceiling_bps"))
    ev = ({"value": ceiling, "label": "live competitive fee ceiling (median best-competitor friction, cross-VM cells)",
           "source": f"execution_bench.competitive_fee_ceiling_bps ({bench.get('competitive_fee_ceiling_basis') or 'live quote benchmark'})"}
          if ceiling is not None else None)
    reason = None if req is not None else unreachable(side, param, unit, "starting public take")
    lam_txt = f"decaying to the {float(base_inputs['tau_floor_bps']):.2f} bps floor at {float(p['lambda_pub']) * 100:g}%/month"
    ev_txt = f"; the live competitive fee ceiling is {ceiling:.2f} bps" if ceiling is not None else "; no live competitive ceiling in the snapshot"
    verdict = (
        f"Justifying {_usd(target)} needs a starting gross public take of {req:.1f} bps ({lam_txt}) versus {tau0:.2f} bps today{ev_txt}."
        if req is not None else
        f"No starting public take up to {SEARCH_BOUNDS[param][1]:g} bps ({lam_txt}) {gap_word}{ev_txt}."
    )
    rows.append(_row(param=param, label="Starting gross public take rate", unit=unit, base_value=tau0, required=req, reason=reason,
                     evidence=ev, harder="higher", fdv_check=fdv_at(p, **{param: req}) if req is not None else None,
                     target=target, verdict=verdict))

    # 3. terminal multiple -----------------------------------------------------------------------------
    param, unit = "terminal_multiple", "x"
    req, side = _solve(lambda x: fdv_at(p, terminal_multiple=x), target, *SEARCH_BOUNDS[param])
    peers = _peer_multiples(snapshot)
    raw_median = _num(cal.get("terminal_multiple_raw"))
    if raw_median is None:
        raw_median = _num((snapshot.get("comps") or {}).get("median_fdv_to_revenue_ex_near"))
    peer_txt = ", ".join(f"{s} {m:,.0f}x" for s, m in sorted(peers, key=lambda t: t[1]))
    ev = ({"value": raw_median, "label": "peer median FDV / annualised revenue ex-NEAR (unclipped)",
           "source": f"comps.median_fdv_to_revenue_ex_near ({peer_txt})", "peers": [{"symbol": s, "fdv_to_revenue": m} for s, m in peers],
           "model_cap": _num(cal.get("terminal_multiple_used"))}
          if raw_median is not None else None)
    reason = None if req is not None else unreachable(side, param, unit, "terminal multiple")
    ev_txt = f"; the live peer median is {raw_median:,.0f}x ({peer_txt}) and the model caps it at {p[param]:,.0f}x" if raw_median is not None else ""
    verdict = (
        f"Justifying {_usd(target)} needs a {req:,.0f}x terminal FDV/holder-revenue multiple{ev_txt}."
        if req is not None else
        f"No terminal multiple up to {SEARCH_BOUNDS[param][1]:,.0f}x {gap_word}{ev_txt}."
    )
    rows.append(_row(param=param, label="Terminal FDV / annual holder-revenue multiple", unit=unit, base_value=p[param],
                     required=req, reason=reason, evidence=ev, harder="higher",
                     fdv_check=fdv_at(p, **{param: req}) if req is not None else None, target=target, verdict=verdict))

    # 4. discount rate ----------------------------------------------------------------------------------
    param, unit = "discount_rate", "ratio_annual"
    req, side = _solve(lambda x: fdv_at(p, discount_rate=x), target, *SEARCH_BOUNDS[param])
    lo_r, hi_r = _assumption_range(snapshot, "discount_rate")
    ev = {"value": lo_r, "label": f"low end of the registry discount-rate range ({_pct(lo_r)}-{_pct(hi_r)})",
          "source": "assumption registry: discount_rate", "range": [lo_r, hi_r]}
    if req is None:
        fdv0 = fdv_at(p, discount_rate=SEARCH_BOUNDS[param][0])
        reason = (f"not reachable at any discount rate >= 0% (FDV at 0% is {_usd(fdv0)})" if side == "short"
                  else unreachable(side, param, unit, "discount rate", increasing=False))
        verdict = f"Even a 0% discount rate gives {_usd(fdv0)}, short of {_usd(target)}: the gap is not a discount-rate question."
    else:
        verdict = f"Justifying {_usd(target)} needs a {req * 100:.1f}% discount rate versus {_pct(p[param])} base; the registry range is {_pct(lo_r)}-{_pct(hi_r)}."
    rows.append(_row(param=param, label="Annual discount rate", unit=unit, base_value=p[param], required=req, reason=reason,
                     evidence=ev, harder="lower", fdv_check=fdv_at(p, **{param: req}) if req is not None else None,
                     target=target, verdict=verdict))

    # 5. confidential share target ------------------------------------------------------------------------
    param, unit = "confidential_share_target", "ratio"
    req, side = _solve(lambda x: fdv_at(p, confidential_share_target=x), target, *SEARCH_BOUNDS[param])
    s30 = _num(vol.get("confidential_share_30d")) or _num(cal.get("confidential_share_start"))
    s7 = _num(vol.get("confidential_share_7d"))
    share_status = vol.get("confidential_share_status") or ("measured" if _num(vol.get("confidential_share_30d")) is not None else "unavailable")
    share_measured = share_status == "measured" and cal.get("confidential_engine_measured", True) is not False
    if share_measured:
        ev = ({"value": s30, "label": "measured confidential share of 30-day volume",
               "source": "intents_forensics.volume.confidential_share_30d (nearstats totalsBreakdown)", "share_7d": s7, "status": share_status}
              if s30 is not None else None)
        ev_txt = f"; the measured share is {_pct(s30)} (30d)" + (f" and {_pct(s7)} (7d)" if s7 is not None else "") if s30 is not None else ""
    else:
        # The split guard substituted the registry assumption (or the split is missing): this is not evidence, and the
        # row must not read as "measured". within_evidence is then a comparison against an assumption, labelled as such.
        ev = ({"value": s30, "label": "ASSUMED confidential share (registry confidential_share; the nearstats split was not measured this run)",
               "source": str(vol.get("confidential_share_source") or cal.get("confidential_share_source") or "assumption"),
               "status": share_status, "assumption": True}
              if s30 is not None else None)
        ev_txt = (f"; the share is NOT MEASURED this run (the model assumes {_pct(s30)}, registry confidential_share)" if s30 is not None
                  else "; the share is not measured this run")
    reason = None if req is not None else unreachable(side, param, unit, "confidential share at month 36")
    verdict = (
        f"Justifying {_usd(target)} needs the confidential share to reach {_pct(req)} by month {horizon}{ev_txt}."
        if req is not None else
        f"No confidential share up to {_pct(SEARCH_BOUNDS[param][1])} by month {horizon} {gap_word}{ev_txt}."
    )
    rows.append(_row(param=param, label=f"Confidential share of volume at month {horizon}", unit=unit, base_value=p[param],
                     required=req, reason=reason, evidence=ev, harder="higher",
                     fdv_check=fdv_at(p, **{param: req}) if req is not None else None, target=target, verdict=verdict))

    # 6. joint: month-36 annualised holder revenue at the base multiple (scale starting volumes) -------------
    param, unit = "holder_revenue_scale", "usd_per_year"
    k_req, side = _solve(lambda k: fdv_at(p, volume_scale=k), target, *SEARCH_BOUNDS[param])
    rev = base["monthly_holder_revenue"]
    kk = min(12, horizon)
    base_yr3 = sum(rev[-kk:]) * 12.0 / kk
    current_run = float(p["alpha_capture"]) * float(p["gross_fees_30d_usd"]) * 365.25 / float(p["window_days"])
    ev = {"value": current_run, "label": "current annualised holder revenue (30-day window x 365.25/30)",
          "source": "sotp.calibration: alpha_capture x gross_fees_30d_usd (DefiLlama near-intents holders revenue)",
          "base_model_year3_usd": base_yr3}
    req = k_req * base_yr3 if k_req is not None else None
    if req is not None:
        cagr = (req / current_run) ** (1.0 / years) - 1.0 if current_run > 0 else None
        reason = None
        verdict = (
            f"Justifying {_usd(target)} at the {p['terminal_multiple']:,.0f}x base multiple needs {_usd(req)} of annualised holder revenue "
            f"in year {years:g} ({k_req:,.1f}x the base path's {_usd(base_yr3)}), versus {_usd(current_run)} today"
            + (f" ({_pct(cagr)}/yr compounded)." if cagr is not None else ".")
        )
    else:
        reason = unreachable(side, param, "x", "x starting volume")
        verdict = f"No volume scale up to {SEARCH_BOUNDS[param][1]:,.0f}x {gap_word} at the base multiple."
    row = _row(param=param, label=f"Year-{years:g} annualised holder revenue at the base multiple (volumes scaled jointly)", unit=unit,
               base_value=base_yr3, required=req, reason=reason, evidence=ev, harder="higher",
               fdv_check=fdv_at(p, volume_scale=k_req) if k_req is not None else None, target=target, verdict=verdict)
    row["required_volume_scale"] = k_req
    rows.append(row)

    # headline ------------------------------------------------------------------------------------------------
    gap = target / base_fdv if base_fdv > 0 else None
    mc_p50 = _num((sotp.get("fdv_percentiles") or {}).get("p50"))
    inside = [r for r in rows if r["required_vs_evidence"]["within_evidence"]]
    lead = f"Market FDV {_usd(target)} is {gap:,.1f}x the model's expected-path FDV {_usd(base_fdv)}" if gap else f"Market FDV {_usd(target)}"
    if inside:
        names = "; ".join(f"{r['short_label']} {_fmt(r['required_value'], r['unit'])} (evidence {_fmt(r['evidence']['value'], r['unit'])})" for r in inside)
        headline = f"{lead}; holding the rest at base, the gap closes inside measured evidence only through: {names}."
    else:
        ranked = sorted((r for r in rows if r["required_vs_evidence"]["ratio"] is not None), key=lambda r: r["required_vs_evidence"]["ratio"])
        if ranked:
            r = ranked[0]
            headline = (f"{lead}; no single input closes the gap inside its evidence, the nearest is the {r['short_label']} at "
                        f"{_fmt(r['required_value'], r['unit'])} versus {_fmt(r['evidence']['value'], r['unit'])} measured.")
        else:
            headline = f"{lead}; no single input closes the gap inside its evidence."
    return {
        "basis": "deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base",
        "current_fdv_usd": target,
        "base_fdv_usd": base_fdv,
        "base_fdv_mc_p50_usd": mc_p50,
        "gap_multiple": gap,
        "gap_multiple_vs_mc_p50": (target / mc_p50) if mc_p50 else None,
        "horizon_months": horizon,
        "solver": "scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12",
        "solves": rows,
        "n_reachable": sum(1 for r in rows if r["reachable"]),
        "n_within_evidence": len(inside),
        "headline": headline,
    }


# ============================================================================ CLI
def load_snapshot(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def main(argv: list[str] | None = None, runner: Callable[[Mapping[str, Any]], dict[str, Any]] = run_market_implied) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(f"usage: python -m {runner.__module__} <snapshot.json>", file=sys.stderr)
        return 2
    print(json.dumps(runner(load_snapshot(args[0])), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
