"""The long-term bull case for $NEAR, stated as falsifiable conditions and graded against live data.

Each condition says what has to be true for the market price to be justified over the long run, the value it
requires, the value measured this run, a trend from a real series where one exists, and a status:

    on_track      the live value already meets the requirement
    behind        moving the right way (or positive) but short of the requirement
    against       moving the wrong way, or a falsification trigger is breached
    not_measured  the input was not measured this run

Nothing here is a new estimate. Requirements come from ``market_implied`` (one lever moved at a time until the
model's expected-path FDV equals the market FDV), ``supply_physics`` (breakeven volume), ``bear_case`` trigger
thresholds and the registry; live values come from the collectors; trends come from the DefiLlama daily series
(``intents_forensics.fees.daily_series``) and the NEAR-reported confidential TVL history
(``intents_forensics.confidential_tvl_history``). Input: the snapshot as a JSON dict (``attach_derived_models``).
"""
from __future__ import annotations

from datetime import date
from typing import Any

ON_TRACK, BEHIND, AGAINST, NOT_MEASURED = "on_track", "behind", "against", "not_measured"


def _get(d: Any, *path: str) -> Any:
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def _num(x: Any) -> float | None:
    return float(x) if isinstance(x, (int, float)) and x == x else None


def _solve(snap: dict[str, Any], param: str) -> dict[str, Any]:
    for s in _get(snap, "market_implied", "solves") or []:
        if isinstance(s, dict) and s.get("param") == param:
            return s
    return {}


def _window_sum(series: list[list[float]], col: int, end_back_days: int, days: int = 30) -> float | None:
    """Sum of column ``col`` over ``days`` days ending ``end_back_days`` days before the last row."""
    if len(series) < end_back_days + days:
        return None
    rows = series[len(series) - end_back_days - days: len(series) - end_back_days]
    vals = [r[col] for r in rows if len(r) > col and isinstance(r[col], (int, float))]
    return sum(vals) if len(vals) == days else None


def _ratio_change(now: float | None, then: float | None) -> float | None:
    return now / then - 1.0 if now is not None and then not in (None, 0) else None


def _trend(label: str, now: float | None, then: float | None, window: str, source: str) -> dict[str, Any] | None:
    ch = _ratio_change(now, then)
    if ch is None:
        return None
    return {"label": label, "now": now, "then": then, "change": ch, "window": window, "source": source,
            "direction": "up" if ch > 0.02 else "down" if ch < -0.02 else "flat"}


def _cond(key: str, statement: str, *, required: Any, live: Any, unit: str, status: str, why: str,
          trend: dict[str, Any] | None = None, required_source: str = "", live_source: str = "",
          kind: str = "requirement") -> dict[str, Any]:
    return {"key": key, "statement": statement, "kind": kind, "required": required, "live": live, "unit": unit,
            "status": status, "why": why, "trend": trend, "required_source": required_source, "live_source": live_source}


def _tvl_at(history: list[list[Any]], days_back: int) -> tuple[str, float] | None:
    """The history point closest to (last date - days_back)."""
    if not history:
        return None
    last = date.fromisoformat(history[-1][0])
    best = None
    for d, v in history:
        gap = abs((last - date.fromisoformat(d)).days - days_back)
        if best is None or gap < best[0]:
            best = (gap, d, v)
    return (best[1], best[2]) if best and best[0] <= 7 else None


def run_bull_case(snap: dict[str, Any]) -> dict[str, Any]:
    fees = _get(snap, "intents_forensics", "fees") or {}
    series = [r for r in (fees.get("daily_series") or []) if isinstance(r, list) and len(r) >= 4]
    fdv = _num(_get(snap, "market_implied", "current_fdv_usd"))
    conds: list[dict[str, Any]] = []

    # 1. Volume compounding (the lever the market price leans on).
    g = _solve(snap, "public_volume_growth_yoy")
    g_req, g_live = _num(g.get("required_value")), _num(_get(g, "evidence", "value"))
    vol_now, vol_90 = _window_sum(series, 3, 0), _window_sum(series, 3, 90)
    conds.append(_cond(
        "volume_growth", "Intents volume compounds fast enough to grow into the price",
        required=g_req, live=g_live, unit="ratio_yoy",
        status=NOT_MEASURED if g_req is None or g_live is None else ON_TRACK if g_live >= g_req else BEHIND if g_live > 0 else AGAINST,
        why=("Holding every other input at base, the market FDV needs this annual public-volume growth for three years; "
             "live is trailing-12-month growth of 30-day volume."),
        trend=_trend("30-day volume vs 90 days earlier", vol_now, vol_90, "90d", "DefiLlama dexs/near-intents daily volume"),
        required_source="market_implied.solves[public_volume_growth_yoy].required_value",
        live_source="market_implied.solves[public_volume_growth_yoy].evidence (DefiLlama)",
    ))

    # 2. Holder revenue scales.
    h = _solve(snap, "holder_revenue_scale")
    h_req, h_live = _num(h.get("required_value")), _num(_get(h, "evidence", "value"))
    rev_now, rev_90 = _window_sum(series, 2, 0), _window_sum(series, 2, 90)
    conds.append(_cond(
        "holder_revenue", "Holder revenue (buybacks) scales to support the price at the model's multiple",
        required=h_req, live=h_live, unit="usd_per_year",
        status=NOT_MEASURED if h_req is None or h_live is None else ON_TRACK if h_live >= h_req else BEHIND,
        why="Year-3 annualised holder revenue the market FDV needs at the model's terminal multiple, against today's run-rate.",
        trend=_trend("30-day holder revenue vs 90 days earlier", rev_now, rev_90, "90d", "DefiLlama near-intents daily revenue"),
        required_source="market_implied.solves[holder_revenue_scale].required_value",
        live_source="market_implied.solves[holder_revenue_scale].evidence",
    ))

    # 3. The market keeps an L1 multiple (the lever that is inside evidence).
    m = _solve(snap, "terminal_multiple")
    m_req, m_live = _num(m.get("required_value")), _num(_get(m, "evidence", "value"))
    conds.append(_cond(
        "l1_multiple", "The market keeps valuing NEAR like an L1, not like a fee-only app",
        required=m_req, live=m_live, unit="x",
        status=NOT_MEASURED if m_req is None or m_live is None else ON_TRACK if m_live >= m_req else BEHIND,
        why=("FDV-to-holder-revenue multiple the market FDV implies, against the peer median for L1s (SOL, ETH, HYPE). "
             "This is the only single lever that closes the gap inside measured evidence."),
        required_source="market_implied.solves[terminal_multiple].required_value",
        live_source="comps.median_fdv_to_revenue_ex_near",
    ))

    # 4. Pricing power on cross-VM routes.
    head = _get(snap, "execution_bench", "headroom_by_archetype_bps") or {}
    cv = _num(head.get("cross_vm"))
    conds.append(_cond(
        "pricing_power", "1Click keeps a pricing edge where it competes (cross-VM routes)",
        required=0.0, live=cv, unit="bps",
        status=NOT_MEASURED if cv is None else ON_TRACK if cv > 0 else AGAINST,
        why=(f"Median headroom over the best competitor on destination units, live quote race. Native BTC "
             f"{_fmt_bps(head.get('native_btc'))} and EVM L2 {_fmt_bps(head.get('evm_l2'))}: 1Click trails there."),
        required_source="execution_bench (headroom > 0 bps means 1Click delivers more)",
        live_source="execution_bench.headroom_by_archetype_bps.cross_vm",
        kind="supporting",
    ))

    # 5. Confidential flow grows (the higher-fee engine).
    f = snap.get("intents_forensics") or {}
    tvl = _num(f.get("confidential_tvl_usd"))
    hist = [x for x in (f.get("confidential_tvl_history") or []) if isinstance(x, list) and len(x) == 2]
    then = _tvl_at(hist, 90)
    last = hist[-1] if hist else None
    net30 = _num(_get(f, "confidential_boundary", "net_flow_30d_usd"))
    tr = _trend("confidential TVL vs 90 days earlier", _num(last[1]) if last else None, then[1] if then else None, "90d",
                "NEAR-reported confidential TVL history (nearstats protocolMetrics)")
    conf_ok = (net30 is not None and net30 > 0) and (tr is None or tr["change"] > 0)
    conds.append(_cond(
        "confidential_growth", "Confidential (private) flow keeps growing",
        required=0.0, live=net30, unit="usd",
        status=NOT_MEASURED if net30 is None else ON_TRACK if conf_ok else AGAINST,
        why=(f"Net 30-day inflow into the Confidential Intents treasury, read on-chain; treasury TVL {_fmt_usd(tvl)}. "
             "Swap volume on the private chain itself is not public, so this is flow, not volume."),
        trend=tr, required_source="net inflow > 0", live_source="intents_forensics.confidential_boundary.net_flow_30d_usd",
        kind="supporting",
    ))

    # 6. Supply turns net-deflationary.
    be = _get(snap, "supply_physics", "breakeven_daily_volume_usd") or {}
    be_sq, be_svrn = _num(be.get("status_quo")), _num(be.get("svrn_glidepath"))
    v30 = _num(_get(f, "volume", "30d"))
    daily = v30 / 30.0 if v30 else None
    conds.append(_cond(
        "net_deflation", "Fees retire more NEAR than issuance creates",
        required=be_svrn if be_svrn is not None else be_sq, live=daily, unit="usd_per_day",
        status=NOT_MEASURED if daily is None or (be_sq is None and be_svrn is None) else ON_TRACK if be_svrn is not None and daily >= be_svrn else BEHIND,
        why=(f"Daily Intents volume at which buybacks, gas burn and state lock offset issuance: {_fmt_usd(be_svrn)}/day under the "
             f"1.6% glidepath, {_fmt_usd(be_sq)}/day at today's 2.5%. Sinks cover "
             f"{_fmt_pct(_num(_get(snap, 'supply_physics', 'sink_coverage_ratio')))} of issuance now."),
        required_source="supply_physics.breakeven_daily_volume_usd.svrn_glidepath", live_source="intents_forensics.volume.30d / 30",
    ))

    # 7. Governance passes the issuance cut.
    infl = _num(_get(snap, "near_rpc", "max_inflation_rate"))
    target = _num(_get(snap, "near_rpc", "svrn_target_inflation_used")) or 0.016
    conds.append(_cond(
        "issuance_cut", "Governance cuts issuance from 2.5% to 1.6%",
        required=target, live=infl, unit="ratio",
        status=NOT_MEASURED if infl is None else ON_TRACK if infl <= target + 1e-9 else BEHIND,
        why="Protocol max inflation read from EXPERIMENTAL_protocol_config; the cut halves the volume needed for net deflation.",
        required_source="SVRN glidepath target", live_source="near_rpc.max_inflation_rate",
    ))

    # 8. Solver competition stays healthy.
    sc = _get(f, "solver_concentration") or {}
    hhi, ci = _num(sc.get("hhi_solver")), sc.get("hhi_solver_ci90")
    thr = next((_num(s.get("trigger_threshold")) for s in (_get(snap, "bear_case", "scenarios") or []) if s.get("key") == "solver_cartelization"), None) or 3500.0
    lo = _num(ci[0]) if isinstance(ci, list) and ci else None
    conds.append(_cond(
        "solver_competition", "Solver competition stays broad enough to keep spreads tight",
        required=thr, live=hhi, unit="hhi",
        status=NOT_MEASURED if hhi is None else ON_TRACK if hhi <= thr else AGAINST if (lo is not None and lo > thr) else BEHIND,
        why=(f"Solver HHI from sampled execute_intents fills (90% CI {_fmt_int(lo)}-{_fmt_int(_num(ci[1]) if isinstance(ci, list) and len(ci) > 1 else None)}); "
             "above the bear-case threshold means a few solvers set prices."),
        required_source="bear_case solver_cartelization threshold", live_source="intents_forensics.solver_concentration.hhi_solver",
    ))

    counts = {k: sum(1 for c in conds if c["status"] == k) for k in (ON_TRACK, BEHIND, AGAINST, NOT_MEASURED)}
    measured = len(conds) - counts[NOT_MEASURED]
    headline = (
        f"The long-term case for NEAR at {_fmt_usd(fdv)}: {counts[ON_TRACK]} of {measured} measured conditions are on track. "
        f"It holds if the market keeps an L1 multiple ({_fmt_x(m_req)} revenue needed against a {_fmt_x(m_live)} peer median) "
        f"while Intents grows into it; it fails if volume growth stays near {_fmt_pct(g_live)} a year against the {_fmt_pct(g_req)} the price implies."
    )
    return {
        "basis": ("Conditions the long-term bull case needs, graded against this run's live data. Requirements come from "
                  "market_implied (one lever at a time), supply_physics and bear_case thresholds; nothing is re-estimated here."),
        "current_fdv_usd": fdv, "conditions": conds, "counts": counts, "n_conditions": len(conds), "n_measured": measured,
        "headline": headline,
        "watch": [c["key"] for c in conds if c["status"] in (BEHIND, AGAINST)],
    }


def _fmt_usd(x: Any) -> str:
    x = _num(x)
    if x is None:
        return "n/a"
    for d, s in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= d:
            return f"${x / d:,.{2 if s == 'B' else 1}f}{s}"
    return f"${x:,.0f}"


def _fmt_pct(x: Any) -> str:
    x = _num(x)
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _fmt_x(x: Any) -> str:
    x = _num(x)
    return "n/a" if x is None else f"{x:,.0f}x"


def _fmt_int(x: Any) -> str:
    x = _num(x)
    return "n/a" if x is None else f"{x:,.0f}"


def _fmt_bps(x: Any) -> str:
    x = _num(x)
    return "n/a" if x is None else f"{x:+.2f} bps"
