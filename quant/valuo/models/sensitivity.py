"""One-at-a-time sensitivity ("what you have to believe"): a tornado over every model input with a range.

Pure, deterministic, no network. Each row evaluates ``deterministic_sotp`` (inputs rebuilt from the snapshot by
``market_implied.compose_inputs``, so the fee reconciliation, take floor and confidential growth re-derive exactly as
``sotp_valuation.build_inputs``) at the input's low and high with every other input at base, and rows are ranked
by the FDV swing |FDV_high - FDV_low|.

Ranges, by input source:
  assumption  the registry [low, high] the snapshot run used (snapshot.assumptions)
  measured    a measured dispersion when the snapshot has one: starting volume x exp(+/- monthly volume sigma);
              spot price x exp(+/- monthly price sigma); gross take and holder capture = min..max over the trailing
              ``sensitivity_measured_lookback_windows`` 30-day windows of the DefiLlama daily series; otherwise
              +/- ``sensitivity_unmeasured_band`` (a labeled registry width)
  derived     terminal multiple: registry guardrails [terminal_multiple_floor, terminal_multiple_cap high]
Variance proxy share = swing^2 / sum(swing^2) (the first-order variance decomposition for independent inputs
with symmetric ranges); an approximation, labeled as such.

CLI: ``uv run python -m valuo.models.sensitivity artifacts/latest_snapshot.json``.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from valuo import assumptions as A
from valuo.models.market_implied import (
    _assumption_range,
    _assumption_value,
    _num,
    _usd,
    compose_inputs,
    main as _main,
    primitives_from_snapshot,
)
from valuo.models.sotp_valuation import deterministic_sotp

__all__ = ["ASSUMPTION_PARAMS", "FDV_INVARIANT_PARAMS", "measured_windows", "tornado_rows", "run_sensitivity", "main"]

# registry key -> (primitive key, label)
ASSUMPTION_PARAMS: dict[str, tuple[str, str]] = {
    "public_volume_growth_yoy": ("public_volume_growth_yoy", "Expected annual public-volume growth"),
    "confidential_share_target": ("confidential_share_target", "Confidential share at month 36"),
    "confidential_take_bps": ("tau_conf_bps", "Confidential gross take (public take re-reconciled to live fees)"),
    "fee_compression_lambda_monthly": ("lambda_pub", "Public take compression speed (per month)"),
    "confidential_compression_divisor": ("confidential_compression_divisor", "Confidential compression divisor"),
    "discount_rate": ("discount_rate", "Annual discount rate"),
    "confidential_multiple_haircut": ("conf_haircut", "Confidential multiple haircut"),
    "near_price_drift_annual": ("price_drift_annual", "NEAR price drift (gas-burn and state-lock USD value)"),
    "public_take_floor_bps": ("public_take_floor_bps", "Public take hard floor"),
}

# Registry inputs that move issuance (supply, implied price, crossover) but not the FDV.
FDV_INVARIANT_PARAMS: dict[str, str] = {
    "svrn_target_inflation": "issuance path only: moves supply at horizon and implied price, not FDV",
    "svrn_glidepath_months": "issuance path only: moves supply at horizon and implied price, not FDV",
}


def measured_windows(snapshot: Mapping[str, Any], n_windows: int) -> dict[str, Any] | None:
    """Gross take (fees/volume, bps) and capture (revenue/fees) per trailing non-overlapping 30-day window."""
    fees = (snapshot.get("intents_forensics") or {}).get("fees") or {}
    series = fees.get("daily_series")
    cols = fees.get("daily_series_columns") or ["ts_unix_s", "fees_usd", "revenue_usd", "volume_usd"]
    if not isinstance(series, list) or not all(c in cols for c in ("fees_usd", "revenue_usd", "volume_usd")):
        return None
    i_f, i_r, i_v = cols.index("fees_usd"), cols.index("revenue_usd"), cols.index("volume_usd")
    takes, captures = [], []
    for w in range(int(n_windows)):
        end = len(series) - 30 * w
        rows = series[end - 30:end] if end - 30 >= 0 else []
        if len(rows) < 30:
            break
        f = sum(_num(r[i_f]) or 0.0 for r in rows)
        rv = sum(_num(r[i_r]) or 0.0 for r in rows)
        v = sum(_num(r[i_v]) or 0.0 for r in rows)
        if v > 0 and f > 0:
            takes.append(f / v * 1e4)
            captures.append(rv / f)
    if len(takes) < 2:
        return None
    return {"gross_take_bps": takes, "capture_ratio": captures, "n_windows": len(takes)}


def _row(p: Mapping[str, Any], *, param: str, label: str, source: str, unit: str, base: float, low: float, high: float,
         key: str, basis: str, transform: Any = None) -> dict[str, Any]:
    def fdv(v: float) -> tuple[float, float]:
        q = dict(p)
        if transform is not None:
            q.update(transform(v))
        else:
            q[key] = v
        res = deterministic_sotp(compose_inputs(q))
        return float(res["fdv_total"]), float(res["implied_price"])

    f_lo, px_lo = fdv(low)
    f_hi, px_hi = fdv(high)
    return {
        "param": param, "label": label, "source": source, "unit": unit, "base": base, "low": low, "high": high,
        "fdv_low": f_lo, "fdv_high": f_hi, "swing_usd": abs(f_hi - f_lo),
        "implied_price_low": px_lo, "implied_price_high": px_hi, "range_basis": basis,
    }


def tornado_rows(snapshot: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """(primitives, unranked rows, notes)."""
    p = primitives_from_snapshot(snapshot)
    cal = (snapshot.get("sotp") or {}).get("calibration") or {}
    notes: list[str] = []
    rows: list[dict[str, Any]] = []
    units = {a.key: a.unit for a in A.as_list()}

    # assumptions: registry range ---------------------------------------------------------------------
    for key, (prim, label) in ASSUMPTION_PARAMS.items():
        lo, hi = _assumption_range(snapshot, key)
        rows.append(_row(p, param=key, label=label, source="assumption", unit=units.get(key, ""), base=float(p[prim]),
                         low=lo, high=hi, key=prim, basis=f"registry range [{lo:g}, {hi:g}]"))

    # derived: terminal multiple ----------------------------------------------------------------------
    m_lo = _assumption_value(snapshot, "terminal_multiple_floor")
    m_hi = _assumption_range(snapshot, "terminal_multiple_cap")[1]
    raw = _num(cal.get("terminal_multiple_raw"))
    rows.append(_row(p, param="terminal_multiple", label="Terminal FDV / holder-revenue multiple", source="derived", unit="x",
                     base=float(p["terminal_multiple"]), low=m_lo, high=m_hi, key="terminal_multiple",
                     basis=(f"registry guardrails: terminal_multiple_floor {m_lo:g}x .. terminal_multiple_cap high {m_hi:g}x"
                            + (f" (live peer median {raw:,.0f}x, clipped)" if raw is not None else ""))))

    band = _assumption_value(snapshot, "sensitivity_unmeasured_band")
    n_win = int(_assumption_value(snapshot, "sensitivity_measured_lookback_windows"))

    # measured: starting volume x exp(+/- sigma_monthly) ------------------------------------------------
    sig_v = _num(cal.get("sigma_volume_monthly"))
    if sig_v is not None:
        lo, hi = math.exp(-sig_v), math.exp(sig_v)
        rows.append(_row(p, param="starting_volume", label="Starting 30-day Intents volume (public + confidential)", source="measured",
                         unit="x_base", base=1.0, low=lo, high=hi, key="volume_scale",
                         basis=f"x exp(+/- measured monthly volume sigma {sig_v:.3f}) ({cal.get('sigma_volume_source') or 'sotp.calibration'})"))
    else:
        notes.append("starting_volume: no measured volume sigma in sotp.calibration; row omitted")

    # measured: gross take and capture over trailing windows ----------------------------------------------
    win = measured_windows(snapshot, n_win)
    v_total = float(p["v_pub_30d_usd"]) + float(p["v_conf_30d_usd"])
    base_take = float(p["gross_fees_30d_usd"]) / v_total * 1e4 if v_total > 0 else 0.0
    if win is not None and v_total > 0:
        t = win["gross_take_bps"]
        rows.append(_row(p, param="gross_take_bps", label="Blended gross take (public take re-reconciled)", source="measured", unit="bps",
                         base=base_take, low=min(t), high=max(t), key="gross_fees_30d_usd",
                         transform=lambda bps: {"gross_fees_30d_usd": bps / 1e4 * v_total},
                         basis=f"min..max over {win['n_windows']} trailing 30-day windows of DefiLlama near-intents fees / volume"))
        c = win["capture_ratio"]
        rows.append(_row(p, param="alpha_capture", label="Holder capture (revenue / gross fees)", source="measured", unit="ratio",
                         base=float(p["alpha_capture"]), low=min(c), high=max(c), key="alpha_capture",
                         basis=f"min..max over {win['n_windows']} trailing 30-day windows of DefiLlama near-intents revenue / fees"))
    else:
        notes.append("gross_take_bps, alpha_capture: no DefiLlama daily series in the snapshot; using the labeled band")
        rows.append(_row(p, param="gross_take_bps", label="Blended gross take (public take re-reconciled)", source="assumption", unit="bps",
                         base=base_take, low=base_take * (1 - band), high=base_take * (1 + band), key="gross_fees_30d_usd",
                         transform=lambda bps: {"gross_fees_30d_usd": bps / 1e4 * v_total},
                         basis=f"+/- {band:.0%} (sensitivity_unmeasured_band)"))
        a = float(p["alpha_capture"])
        rows.append(_row(p, param="alpha_capture", label="Holder capture (revenue / gross fees)", source="assumption", unit="ratio",
                         base=a, low=a * (1 - band), high=min(1.0, a * (1 + band)), key="alpha_capture",
                         basis=f"+/- {band:.0%} (sensitivity_unmeasured_band)"))

    # measured: spot price x exp(+/- monthly price sigma) ----------------------------------------------------
    sig_p = _num(cal.get("sigma_price_monthly"))
    price = float(p["price_usd"])
    if sig_p is not None:
        rows.append(_row(p, param="price_usd", label="NEAR spot price (USD value of gas burn and state lock)", source="measured", unit="USD",
                         base=price, low=price * math.exp(-sig_p), high=price * math.exp(sig_p), key="price_usd",
                         basis=f"x exp(+/- measured monthly price sigma {sig_p:.3f})"))

    # measured without dispersion: labeled band -------------------------------------------------------------
    for key, label, unit in (
        ("gas_burn_near_day", "L1 gas burn (NEAR/day)", "NEAR_per_day"),
        ("state_lock_near_day", "State-lock growth (NEAR/day)", "NEAR_per_day"),
        ("headroom_cross_vm_bps", "Cross-VM headroom (sets the public take floor)", "bps"),
    ):
        b = _num(p.get(key))
        if b is None:
            notes.append(f"{key}: null in the snapshot; row omitted")
            continue
        lo, hi = sorted((b * (1 - band), b * (1 + band)))
        rows.append(_row(p, param=key, label=label, source="measured", unit=unit, base=b, low=lo, high=hi, key=key,
                         basis=f"+/- {band:.0%} of the live value (sensitivity_unmeasured_band; no measured dispersion)"))
    return p, rows, notes


def run_sensitivity(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Tornado: rows ranked by FDV swing, with each row's share of the swing^2 variance proxy."""
    p, rows, notes = tornado_rows(snapshot)
    base = deterministic_sotp(compose_inputs(p))
    base_fdv = float(base["fdv_total"])
    rows.sort(key=lambda r: r["swing_usd"], reverse=True)
    total = sum(r["swing_usd"] ** 2 for r in rows)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["variance_share"] = r["swing_usd"] ** 2 / total if total > 0 else 0.0
    top3 = rows[:3]
    top3_share = sum(r["variance_share"] for r in top3)
    current = _num((snapshot.get("sotp") or {}).get("current_fdv_usd"))
    above = [r for r in rows if current is not None and max(r["fdv_low"], r["fdv_high"]) >= current]
    lead = rows[0] if rows else None
    if lead is not None:
        headline = (
            f"{', '.join(r['param'] for r in top3)} carry {top3_share:.0%} of the swing-squared variance proxy; "
            f"{lead['param']} alone moves FDV from {_usd(min(lead['fdv_low'], lead['fdv_high']))} to "
            f"{_usd(max(lead['fdv_low'], lead['fdv_high']))} across its range"
            + (f", and {len(above)} of {len(rows)} single-input ranges reach the {_usd(current)} market FDV." if current is not None else ".")
        )
    else:
        headline = "No sensitivity rows could be evaluated."
    return {
        "basis": "deterministic_sotp expected path; one input at its low / high, all others at the snapshot base",
        "variance_proxy": "swing^2 / sum(swing^2): first-order share for independent inputs, an approximation",
        "base_fdv_usd": base_fdv,
        "base_implied_price": float(base["implied_price"]),
        "current_fdv_usd": current,
        "rows": rows,
        "top3_share": top3_share,
        "n_rows_reaching_market_fdv": len(above),
        "excluded": [{"param": k, "reason": v} for k, v in FDV_INVARIANT_PARAMS.items()],
        "notes": notes,
        "headline": headline,
    }


def main(argv: list[str] | None = None) -> int:
    return _main(argv, runner=run_sensitivity)


if __name__ == "__main__":
    raise SystemExit(main())
