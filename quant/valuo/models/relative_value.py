"""Relative value: NEAR's FDV-to-cash-flow against the live peer set, and the staking / security-budget lens.

Pure, deterministic, no network: reads only the snapshot's ``comps`` (DefiLlama fees/revenue + CoinGecko FDV,
already fetched with provenance), ``supply_physics`` and ``near_rpc``. Nothing here is a fair value:

(a) Peer cash-flow coverage. For every peer row in comps and for NEAR (L1 gas + Intents combined, and each
    component) compute FDV / annualised fees and FDV / annualised revenue on two bases: the 30-day run-rate
    (comps.annualized_*) and the trailing 365 days (comps.*_1y_usd). NEAR's rank (1 = lowest multiple, i.e.
    cheapest), percentile among peers and the peer median are computed, not assumed.
(b) Staking lens. Nominal and real staking APR (supply_physics.staking_yield_table), the security budget
    (annual issuance x price) against fees and holder revenue, and a fee-multiple cross-check:
    NEAR annualised fees x peer P25 / median / P75 FDV/fees. Labeled a relative-value cross-check.

CLI: ``uv run python -m valuo.models.relative_value artifacts/latest_snapshot.json``.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from valuo.models.market_implied import _num, _usd, main as _main

__all__ = ["METRICS", "multiples_row", "rank_against_peers", "run_relative_value", "main"]

# metric key -> (numerator FDV over this denominator field, label)
METRICS: dict[str, tuple[str, str]] = {
    "fdv_to_fees_run_rate": ("annualized_fees_usd", "FDV / annualised fees (30-day run-rate)"),
    "fdv_to_revenue_run_rate": ("annualized_revenue_usd", "FDV / annualised revenue (30-day run-rate)"),
    "fdv_to_fees_1y": ("fees_1y_usd", "FDV / trailing-365-day fees"),
    "fdv_to_revenue_1y": ("revenue_1y_usd", "FDV / trailing-365-day revenue"),
}


def _ratio(n: float | None, d: float | None) -> float | None:
    return n / d if n is not None and d is not None and d > 0 else None


def multiples_row(entry: Mapping[str, Any]) -> dict[str, Any]:
    """FDV / cash-flow multiples recomputed from the raw comps fields of one row."""
    fdv = _num(entry.get("fdv_usd"))
    row: dict[str, Any] = {
        "slug": entry.get("slug"), "symbol": entry.get("symbol"), "label": entry.get("label"), "fdv_usd": fdv,
        "annualized_fees_usd": _num(entry.get("annualized_fees_usd")), "annualized_revenue_usd": _num(entry.get("annualized_revenue_usd")),
        "fees_1y_usd": _num(entry.get("fees_1y_usd")), "revenue_1y_usd": _num(entry.get("revenue_1y_usd")),
        "revenue_to_fees_run_rate": _ratio(_num(entry.get("annualized_revenue_usd")), _num(entry.get("annualized_fees_usd"))),
        "revenue_methodology": entry.get("revenue_methodology"),
    }
    for key, (field, _label) in METRICS.items():
        row[key] = _ratio(fdv, _num(entry.get(field)))
    return row


def rank_against_peers(value: float | None, peer_values: list[float]) -> dict[str, Any]:
    """Rank (1 = lowest multiple) of ``value`` in peers + itself, share of peers strictly below, peer quartiles."""
    vals = [v for v in peer_values if v is not None]
    if value is None or not vals:
        return {"value": value, "rank": None, "n": len(vals) + (value is not None), "percentile": None,
                "peer_median": float(np.median(vals)) if vals else None, "peer_p25": None, "peer_p75": None,
                "peer_min": min(vals) if vals else None, "peer_max": max(vals) if vals else None, "position": None,
                "vs_peer_median": None}
    below = sum(1 for v in vals if v < value)
    med = float(np.median(vals))
    position = "below every peer" if value < min(vals) else "above every peer" if value > max(vals) else "inside the peer range"
    return {
        "value": value, "rank": below + 1, "n": len(vals) + 1, "percentile": below / len(vals),
        "peer_median": med, "peer_p25": float(np.percentile(vals, 25)), "peer_p75": float(np.percentile(vals, 75)),
        "peer_min": min(vals), "peer_max": max(vals), "position": position, "vs_peer_median": value / med if med > 0 else None,
    }


def _staking(snapshot: Mapping[str, Any], near: Mapping[str, Any], price: float | None) -> dict[str, Any]:
    supply = snapshot.get("supply_physics") or {}
    rpc = snapshot.get("near_rpc") or {}
    table = supply.get("staking_yield_table") or []
    daily_iss = _num(supply.get("current_daily_issuance_near"))
    total_supply = _num(rpc.get("total_supply_near"))
    annual_iss = daily_iss * 365.25 if daily_iss is not None else None
    budget = annual_iss * price if annual_iss is not None and price is not None else None
    fees = _num(near.get("annualized_fees_usd"))
    rev = _num(near.get("annualized_revenue_usd"))
    fdv = _num(near.get("fdv_usd"))
    return {
        "basis": "security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate",
        "regimes": table,
        "staked_supply_ratio": _num(rpc.get("staked_supply_ratio")),
        "nominal_staking_apr_current": _num(rpc.get("nominal_staking_apr_current")),
        "annual_issuance_near": annual_iss,
        "measured_inflation_rate": annual_iss / total_supply if annual_iss is not None and total_supply else None,
        "near_price_usd": price,
        "security_budget_usd_per_year": budget,
        "security_budget_pct_of_fdv": _ratio(budget, fdv),
        "annualized_fees_usd": fees,
        "annualized_holder_revenue_usd": rev,
        "fees_to_security_budget": _ratio(fees, budget),
        "revenue_to_security_budget": _ratio(rev, budget),
        "net_dilution_usd_per_year": budget - rev if budget is not None and rev is not None else None,
    }


def run_relative_value(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    comps = snapshot.get("comps") or {}
    peers = [multiples_row(p) for p in comps.get("peers") or []]
    near_raw = comps.get("near_combined") or {}
    near = multiples_row(near_raw)
    components = [multiples_row(c) for c in comps.get("near_components") or []]
    coverage = {k: rank_against_peers(near.get(k), [p[k] for p in peers if p.get(k) is not None]) for k in METRICS}
    for k, (_f, label) in METRICS.items():
        coverage[k]["label"] = label

    # fee-multiple cross-check band -------------------------------------------------------------------------
    def band(metric: str, base_field: str) -> dict[str, Any] | None:
        vals = [p[metric] for p in peers if p.get(metric) is not None]
        base = _num(near_raw.get(base_field))
        if not vals or base is None:
            return None
        return {
            "near_cash_flow_usd": base, "basis": f"comps.near_combined.{base_field} x peer {METRICS[metric][1]}",
            "n_peers": len(vals),
            "p25_fdv_usd": base * float(np.percentile(vals, 25)), "median_fdv_usd": base * float(np.median(vals)),
            "p75_fdv_usd": base * float(np.percentile(vals, 75)),
        }

    cal = (snapshot.get("sotp") or {}).get("calibration") or {}
    price = _num(cal.get("price_usd")) or _num(near_raw.get("price_usd"))
    current_fdv = _num((snapshot.get("sotp") or {}).get("current_fdv_usd")) or near.get("fdv_usd")
    implied = {
        "label": "relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution",
        "fees": band("fdv_to_fees_run_rate", "annualized_fees_usd"),
        "revenue": band("fdv_to_revenue_run_rate", "annualized_revenue_usd"),
        "current_fdv_usd": current_fdv,
    }
    staking = _staking(snapshot, near_raw, price)

    # model cap against the peer set -------------------------------------------------------------------------
    cap = _num(cal.get("terminal_multiple_used"))
    peer_rev = [p["fdv_to_revenue_run_rate"] for p in peers if p.get("fdv_to_revenue_run_rate") is not None]
    n_at_or_below_cap = sum(1 for v in peer_rev if cap is not None and v <= cap)

    # findings -------------------------------------------------------------------------------------------------
    findings: list[str] = []
    cf, cr = coverage["fdv_to_fees_run_rate"], coverage["fdv_to_revenue_run_rate"]
    if cf["value"] is not None and cf["peer_median"] is not None:
        findings.append(
            f"NEAR trades at {cf['value']:,.0f}x annualised fees versus a peer median of {cf['peer_median']:,.0f}x "
            f"(rank {cf['rank']} of {cf['n']}, lowest first; {cf['position']})"
            + (f"; on revenue it is {cr['value']:,.0f}x versus {cr['peer_median']:,.0f}x ({cr['position']})."
               if cr["value"] is not None and cr["peer_median"] is not None else ".")
        )
    if cap is not None and peer_rev:
        findings.append(
            f"{n_at_or_below_cap} of {len(peer_rev)} peers trade at or below the model's {cap:,.0f}x terminal FDV/revenue multiple"
            + (f"; NEAR itself trades at {cr['value']:,.0f}x." if cr["value"] is not None else ".")
        )
    fb = implied["fees"]
    if fb is not None:
        findings.append(
            f"At the peer FDV/fees distribution, NEAR's {_usd(fb['near_cash_flow_usd'])} of annualised fees maps to "
            f"{_usd(fb['p25_fdv_usd'])}-{_usd(fb['p75_fdv_usd'])} (median {_usd(fb['median_fdv_usd'])}, n = {fb['n_peers']})"
            + (f" against a {_usd(current_fdv)} market FDV" if current_fdv is not None else "")
            + "; a relative-value cross-check, not a fair value."
        )
    sb = staking["security_budget_usd_per_year"]
    if sb is not None and staking["annualized_holder_revenue_usd"] is not None:
        findings.append(
            f"NEAR issues {_usd(sb)} a year to validators and delegators ({staking['security_budget_pct_of_fdv']:.1%} of FDV) against "
            f"{_usd(staking['annualized_fees_usd'])} of annualised fees and {_usd(staking['annualized_holder_revenue_usd'])} of holder "
            f"revenue (gas burn + Intents buyback): revenue covers {staking['revenue_to_security_budget']:.0%} of the security budget."
        )
    sq = next((r for r in staking["regimes"] if r.get("regime") == "status_quo"), None)
    if sq is not None and _num(sq.get("nominal_staking_apr")) is not None:
        real = _num(sq.get("real_staking_apr_with_buyback")) or _num(sq.get("real_staking_apr"))
        ns = _num(sq.get("real_non_staker_apr"))
        findings.append(
            f"At {sq['inflation_rate']:.1%} inflation stakers earn {sq['nominal_staking_apr']:.2%} nominal and "
            f"{real:.2%} real including buybacks; non-stakers lose {abs(ns):.2%} a year to dilution net of buybacks."
            if real is not None and ns is not None else
            f"At {sq['inflation_rate']:.1%} inflation stakers earn {sq['nominal_staking_apr']:.2%} nominal."
        )
    return {
        "basis": "live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR",
        "peers": peers,
        "near": near,
        "near_components": components,
        "coverage": coverage,
        "model_terminal_multiple": cap,
        "n_peers_at_or_below_model_multiple": n_at_or_below_cap,
        "n_peers": len(peers),
        "implied_fdv_band": implied,
        "staking": staking,
        "findings": findings,
        "caveat": (f"Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples "
                   f"compare different cash-flow definitions; with n = {len(peers)} peers the median is a reference point, not a distribution."),
    }


def main(argv: list[str] | None = None) -> int:
    return _main(argv, runner=run_relative_value)


if __name__ == "__main__":
    raise SystemExit(main())
