"""Render ``artifacts/IC_MEMO.md`` from a verified ``Snapshot`` and its ``Manifest``.

Every number printed here is read from the snapshot (live, derived or a labeled assumption); the
renderer computes nothing new except presentation arithmetic that is itself shown (ratios between
two snapshot numbers, table sorting). Missing values print as ``n/a`` and the text says what is
missing rather than smoothing over it. Register: research memo, terse, numeric, skeptical.

Entry point: ``render_memo(snapshot, manifest) -> str`` (Markdown). ``manifest`` may be None when the
memo is rendered before the manifest exists; the provenance header then falls back to the snapshot's
own provenance summary.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from valuo.schemas import (
    BearCase,
    ExecutionBenchmark,
    IntentsForensics,
    Manifest,
    NearOnchainTruth,
    PeerComps,
    Snapshot,
    SotpValuation,
    SupplyPhysics,
)

__all__ = ["render_memo", "render_readme_findings", "README_FINDINGS_START", "README_FINDINGS_END", "fmt_usd", "fmt_near", "fmt_pct", "fmt_bps", "fmt_int", "fmt_num", "fmt_month", "NA"]

README_FINDINGS_START = "<!-- VALUO:FINDINGS:START -->"
README_FINDINGS_END = "<!-- VALUO:FINDINGS:END -->"

NA = "n/a"
# Memo section numbers (one place, so cross-references never drift when sections move).
SEC: dict[str, int] = {
    "bull": 1, "summary": 2, "market": 3, "believe": 4, "relval": 5, "model": 6, "micro": 7, "conc": 8, "supply": 9,
    "sotp": 10, "bear": 11, "score": 12, "assumptions": 13, "reproduce": 14, "provenance": 15,
}
_REGIME_LABEL = {"status_quo": "status quo (cap flat)", "svrn_glidepath": "SVRN glidepath", "custom_cap": "custom cap"}
_CLASS_LABEL = {
    "ai_agent": "AI agent", "bridge_relayer": "bridge / token contract", "implicit_account": "implicit account",
    "named_account": "named account", "self_internal": "self", "system": "system",
}


# ============================================================================ formatting
def _finite(x: Any) -> float | None:
    if x is None or isinstance(x, bool):
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def fmt_usd(x: Any, *, compact: bool = True, decimals: int | None = None) -> str:
    """``$1.35B`` / ``$57.6M`` / ``$5,875`` (compact) or ``$5,875,028`` (full)."""
    v = _finite(x)
    if v is None:
        return NA
    sign = "-" if v < 0 else ""
    a = abs(v)
    if compact:
        if a >= 1e9:
            return f"{sign}${a / 1e9:,.{2 if decimals is None else decimals}f}B"
        if a >= 1e6:
            return f"{sign}${a / 1e6:,.{1 if decimals is None else decimals}f}M"
        if a >= 1e4:
            return f"{sign}${a:,.0f}"
        return f"{sign}${a:,.{2 if decimals is None else decimals}f}"
    return f"{sign}${a:,.{0 if decimals is None else decimals}f}"


def fmt_near(x: Any, decimals: int = 0) -> str:
    v = _finite(x)
    return NA if v is None else f"{v:,.{decimals}f} NEAR"


def fmt_pct(x: Any, decimals: int = 1, *, signed: bool = False) -> str:
    """Ratio in, percent out (0.0253 -> 2.53%)."""
    v = _finite(x)
    if v is None:
        return NA
    return f"{v * 100:+.{decimals}f}%" if signed else f"{v * 100:.{decimals}f}%"


def fmt_bps(x: Any, decimals: int = 2, *, signed: bool = False) -> str:
    v = _finite(x)
    if v is None:
        return NA
    return f"{v:+.{decimals}f} bps" if signed else f"{v:.{decimals}f} bps"


def fmt_int(x: Any) -> str:
    v = _finite(x)
    return NA if v is None else f"{int(round(v)):,}"


def fmt_num(x: Any, decimals: int = 2) -> str:
    v = _finite(x)
    return NA if v is None else f"{v:,.{decimals}f}"


def fmt_mult(x: Any, decimals: int = 1) -> str:
    v = _finite(x)
    return NA if v is None else f"{v:,.{decimals}f}x"


def fmt_month(m: Any) -> str:
    v = _finite(m)
    return "none within horizon" if v is None or v <= 0 else f"month {int(v)}"


def fmt_secs(x: Any) -> str:
    v = _finite(x)
    return NA if v is None else f"{v:,.0f} s"


def _short_hash(h: str | None, n: int = 16) -> str:
    return NA if not h else f"{h[:n]}..."


def _plain_number(x: Any) -> str:
    """Thousands separators, never scientific notation: 1,310,395,312 / 15.2637 / 0.000123."""
    v = _finite(x)
    if v is None:
        return NA
    a = abs(v)
    if a >= 1e4 or v == int(v):
        return f"{v:,.0f}" if a >= 1e4 else f"{v:,.4f}".rstrip("0").rstrip(".")
    if a >= 1:
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    return f"{v:.6g}"


def _table(headers: Sequence[str], rows: Iterable[Sequence[Any]], align: Sequence[str] | None = None) -> str:
    """GitHub-flavoured Markdown table; ``align`` entries are 'l' or 'r' per column."""
    align = align or ["l"] * len(headers)
    sep = ["---:" if a == "r" else ":---" for a in align]
    lines = ["| " + " | ".join(str(h) for h in headers) + " |", "| " + " | ".join(sep) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |")
    lines.append("")  # GFM ends a table only at a blank line; keep following text out of the table
    return "\n".join(lines)


def _bullets(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _clip(clip_usd: float) -> str:
    return f"${clip_usd:,.0f}"


# ============================================================================ section helpers
def _header(snap: Snapshot, manifest: Manifest | None) -> str:
    t = snap.near_rpc
    records = manifest.records if manifest is not None else []
    sha = manifest.snapshot_sha256 if manifest is not None else None
    failures = manifest.failures if manifest is not None else snap.provenance_summary.get("failures")
    n_records = len(records) if manifest is not None else snap.provenance_summary.get("records")
    rows = [
        ("NEAR block", f"{t.block_height:,} (`{t.block_hash}`), {t.timestamp_utc}"),
        ("RPC endpoint", t.rpc_endpoint_used),
        ("Snapshot generated", f"{snap.generated_at_utc} UTC, runtime {snap.runtime_s:,.1f} s, valuo {snap.valuo_version}, schema {snap.schema_version}"),
        ("Snapshot SHA-256", f"`{sha}`" if sha else "n/a (manifest not yet written)"),
        ("Monte Carlo", f"seed {snap.sotp.seed}, {snap.sotp.n_paths:,} paths, {snap.sotp.horizon_months} months"),
        ("Raw records", f"{fmt_int(n_records)} HTTP/RPC exchanges hashed, {fmt_int(failures)} non-2xx/failed (every one listed in manifest.json)"),
    ]
    if snap.execution_bench is None:
        rows.append(("Execution benchmark", "NOT RUN in this snapshot (`--skip-bench`); microstructure claims below are unevaluated"))
    return _table(["Provenance", "Value"], rows)


def _regime_rows(supply: SupplyPhysics) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for traj in supply.trajectories:
        out.setdefault(traj.regime, {})["flow"] = traj
    for traj in supply.growth_trajectories or []:
        out.setdefault(traj.regime, {})["growth"] = traj
    return out


def _heatmap_threshold(sotp: SotpValuation) -> list[tuple[float, float | None]]:
    """For each net-take row, the smallest daily volume whose P50 FDV reaches the current FDV (None if none)."""
    hm = sotp.sensitivity_heatmap or {}
    xs, ys, grid = hm.get("x") or [], hm.get("y") or [], hm.get("fdv_p50") or []
    out: list[tuple[float, float | None]] = []
    for i, y in enumerate(ys):
        hit = None
        for j, x in enumerate(xs):
            if i < len(grid) and j < len(grid[i]) and _finite(grid[i][j]) is not None and grid[i][j] >= sotp.current_fdv_usd:
                hit = float(x)
                break
        out.append((float(y), hit))
    return out


def _section_verdict(snap: Snapshot) -> str:
    sotp, supply, truth, forensics = snap.sotp, snap.supply_physics, snap.near_rpc, snap.intents_forensics
    fp, pp = sotp.fdv_percentiles, sotp.price_percentiles
    det = (sotp.calibration or {}).get("deterministic_base") or {}
    cal = sotp.calibration or {}
    regimes = _regime_rows(supply)
    cross = sotp.crossover_month_distribution or {}
    v_day = _finite((supply.inputs.get("daily_volume_usd") or {}).value if "daily_volume_usd" in supply.inputs else None)
    price_now = _finite(forensics.price.get("current_usd"))

    lines: list[str] = []
    gap = _finite(sotp.upside_p50_pct)
    direction = "below" if (gap is not None and gap < 0) else "above"
    lines.append(
        f"**Base case.** {sotp.n_paths:,}-path SOTP (seed {sotp.seed}): P10 / P50 / P90 FDV = {fmt_usd(fp.get('p10'))} / "
        f"**{fmt_usd(fp.get('p50'))}** / {fmt_usd(fp.get('p90'))}; implied price {fmt_usd(pp.get('p10'), compact=False, decimals=2)} / "
        f"**{fmt_usd(pp.get('p50'), compact=False, decimals=2)}** / {fmt_usd(pp.get('p90'), compact=False, decimals=2)} per NEAR against "
        f"spot {fmt_usd(price_now, compact=False, decimals=2)}. The P50 sits {fmt_pct(abs(gap) / 100 if gap is not None else None)} {direction} "
        f"the current FDV of {fmt_usd(sotp.current_fdv_usd)}. The deterministic SOTP at the labeled inputs (the expected-volume path) is "
        f"{fmt_usd(det.get('fdv_total'))}: engines {fmt_usd(det.get('engine_clearinghouse'))} clearinghouse + {fmt_usd(det.get('engine_confidential'))} "
        f"confidential + {fmt_usd(det.get('engine_monetary'))} monetary; the Monte Carlo mean is {fmt_usd(cal.get('mc_mean_fdv'))}. "
        f"Ex-monetary P50: {fmt_usd(sotp.fdv_ex_monetary_percentiles.get('p50'))}."
    )
    med_ratio = (
        cal["volume_terminal_median_usd_day"] / cal["volume_terminal_mean_usd_day"]
        if _finite(cal.get("volume_terminal_median_usd_day")) is not None and _finite(cal.get("volume_terminal_mean_usd_day")) else None
    )
    lines.append(
        f"**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled "
        f"{fmt_pct(_finite((sotp.inputs.get('public_volume_growth_yoy') or {}).value if 'public_volume_growth_yoy' in sotp.inputs else None), 0, signed=True)} YoY "
        f"volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of "
        f"{fmt_num(cal.get('sigma_volume_monthly'), 3)} the MEDIAN simulated path ends month {sotp.horizon_months} at {fmt_pct(med_ratio, 1)} of the expected path "
        f"({fmt_usd(cal.get('volume_terminal_median_usd_day'))}/day vs {fmt_usd(cal.get('volume_terminal_mean_usd_day'))}/day), which is what pulls the P50 FDV "
        f"below the mean. The dispersion is measured from {fmt_int(cal.get('sigma_volume_monthly_n_obs'))} monthly volume log-returns "
        f"(sigma excluding the three oldest, incentive-era windows: {fmt_num(cal.get('sigma_volume_monthly_ex_first_3'), 3)}); a thin sample, reported as such."
    )
    mi = snap.market_implied or {}
    if gap is not None and gap < 0:
        lines.append(
            "**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation"
            + (f"; section {SEC['market']} solves which single input would: {mi.get('headline')}" if mi.get("headline") else "")
            + f" The P90 ({fmt_usd(fp.get('p90'))}) comes from volume paths, not from take-rate expansion (the public take only "
            "compresses in this model)."
        )
    else:
        lines.append(
            "**Reading.** Run-rate cash flows at live take rates already reproduce the current valuation; the upside case rests on "
            "volume growth and the assumption-heavy confidential and monetary engines flagged below."
        )
    thresholds = [(y, x) for y, x in _heatmap_threshold(sotp) if x is not None]
    if thresholds:
        parts = [f"{fmt_bps(y, 0)} net take needs >= {fmt_usd(x)}/day" for y, x in thresholds]
        lines.append(
            f"**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** {'; '.join(parts)}. "
            f"Live run-rate: {fmt_usd(v_day)}/day at {fmt_bps(cal.get('net_take_start_bps'))} net ({fmt_bps(cal.get('blended_gross_take_bps'))} gross x "
            f"capture {fmt_pct(cal.get('alpha_capture'), 1)})."
        )
    else:
        lines.append("**Sensitivity grid.** No cell of the 5x5 volume x net-take grid reaches the current FDV.")

    # Crossover under both regimes: deterministic trajectories (run-rate volume and +g volume) and MC path fractions.
    cross_parts: list[str] = []
    for key in ("status_quo", "svrn_glidepath"):
        flow = regimes.get(key, {}).get("flow")
        growth = regimes.get(key, {}).get("growth")
        mc = cross.get(key) or {}
        p_within = mc.get(f"p_crossover_within_{sotp.horizon_months}m")
        cross_parts.append(
            f"{_REGIME_LABEL.get(key, key)}: deterministic flow crossover {fmt_month(flow.crossover_month if flow else None)} at run-rate "
            f"volume, {fmt_month(growth.crossover_month if growth else None)} with the {fmt_pct(growth.volume_growth_yoy, 0, signed=True) if growth else NA} YoY "
            f"growth assumption; Monte Carlo P(crossover within {sotp.horizon_months}m) = {fmt_pct(p_within, 1)}, "
            f"P(deflationary at horizon) = {fmt_pct(mc.get('p_deflationary_at_horizon'), 1)}; breakeven volume V* = "
            f"{fmt_usd(supply.breakeven_daily_volume_usd.get(key))}/day"
            + (f" ({fmt_num((supply.breakeven_daily_volume_usd.get(key) or 0) / v_day, 1)}x today)" if v_day and supply.breakeven_daily_volume_usd.get(key) is not None else "")
        )
    lines.append(
        f"**Net-float crossover.** Today sinks cover {fmt_pct(supply.sink_coverage_ratio, 1)} of measured issuance "
        f"({fmt_near(supply.current_daily_sinks_near.get('total'))}/day vs {fmt_near(supply.current_daily_issuance_near)}/day). "
        + " ".join(s + "." for s in cross_parts)
        + " The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price "
        "outruns issuance); the deterministic path (the expected-volume path) is the one to quote."
    )
    bear = snap.bear_case
    breached = [s for s in bear.scenarios if s.trigger_breached is True]
    inconclusive = [s.key for s in bear.scenarios if s.trigger_breached is None and getattr(s, "trigger_status", None) == "inconclusive"]
    unmeasured = [s.key for s in bear.scenarios if s.trigger_breached is None and s.key not in inconclusive]
    n_measured = bear.triggers_evaluated if bear.triggers_evaluated is not None else sum(1 for s in bear.scenarios if s.trigger_breached is not None)
    breached_txt = (
        "breached: " + "; ".join(f"{s.key} ({s.early_warning_metric} now {_trigger_value(s, s.current_value)} vs {s.trigger_comparator or ''} {_trigger_value(s, s.trigger_threshold)})" for s in breached)
        if breached else "none breached"
    )
    if inconclusive:
        breached_txt += f"; inconclusive (not graded) this run: {', '.join(inconclusive)}"
    if unmeasured:
        breached_txt += f"; not measured this run: {', '.join(unmeasured)}"
    lines.append(
        f"**Falsification.** Four stress scenarios (section {SEC['bear']}) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo "
        f"percentile) at {fmt_usd(bear.combined_worst_fdv)} ({fmt_pct(bear.combined_drawdown_pct, 0, signed=True)} vs the deterministic base "
        f"{fmt_usd(bear.base_fdv_p50)}); {fmt_int(bear.triggers_breached)} of {fmt_int(n_measured)} measured early-warning triggers are breached in "
        f"this snapshot ({breached_txt}). The on-chain inflation cap reads {fmt_pct(truth.max_inflation_rate, 2)}; the SVRN cut is a proposal, not protocol state."
    )
    return "\n\n".join(lines)


def competitive_ceiling_note(bench: ExecutionBenchmark | None) -> str | None:
    """Per-venue cross-VM friction medians with the binding venue named, for the ceiling's label.

    The ceiling is the median over cross-VM cells of the BEST competitor's friction, so the venue with the lowest
    median is the binding one and every other venue is "not binding" (an aggregator's fixed fee is not the ceiling):
    'Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding'. None when the benchmark carries no medians.
    """
    if bench is None:
        return None
    by_venue = getattr(bench, "competitor_friction_by_venue_bps", None) or {}
    label = {"relay": "Relay", "lifi": "LI.FI", "across": "Across", "1click": "1Click"}
    rows = sorted(
        (float(stats["median"]), venue, stats.get("n"))
        for venue, stats in by_venue.items() if isinstance(stats, dict) and isinstance(stats.get("median"), (int, float))
    )
    if not rows:
        return None
    return ", ".join(
        f"{label.get(venue, venue)} {median:.1f} bps (n={n}) {'binding' if i == 0 else 'not binding'}" for i, (median, venue, n) in enumerate(rows)
    )


def _trigger_value(s: Any, v: Any) -> str:
    """Format a trigger value in the metric's natural unit."""
    metric = s.early_warning_metric or ""
    if metric == "max_inflation_rate":
        return fmt_pct(v, 2)
    if metric.startswith("hhi"):
        return fmt_num(v, 0)
    if metric.startswith("volume"):
        return fmt_pct(v, 1, signed=True)
    return fmt_bps(v, 2)


def _cell_rows(bench: ExecutionBenchmark) -> list[list[str]]:
    rows: list[list[str]] = []
    label = {c.corridor_id: c.label for c in bench.corridors}
    for cell in bench.results:
        for q in cell.quotes:
            friction = q.friction_bps_raw if q.friction_bps_raw is not None else q.friction_bps_usd
            basis = "raw" if q.friction_bps_raw is not None else ("usd" if q.friction_bps_usd is not None else "")
            tool = q.route_tool or ""
            if q.routes_via_near_intents:
                tool = f"{tool} (= NEAR Intents resold via LI.FI)"
            status = q.status if q.status == "ok" else f"{q.status}: {(q.error_message or '')[:70]}"
            rows.append([
                label.get(cell.corridor_id, cell.corridor_id), _clip(cell.clip_usd), q.venue, status,
                fmt_num(q.amount_out_formatted, 6) if q.amount_out_formatted is not None else NA,
                f"{fmt_bps(friction)} ({basis})" if friction is not None else NA,
                fmt_secs(q.time_estimate_s), tool,
            ])
    return rows


def _headroom_rows(bench: ExecutionBenchmark) -> list[list[str]]:
    label = {c.corridor_id: c.label for c in bench.corridors}
    rows = []
    for cell in bench.results:
        oneclick = next((q for q in cell.quotes if q.venue == "1click"), None)
        if cell.headroom_bps is None:
            why = f"1Click {oneclick.status}" if oneclick is not None and oneclick.status != "ok" else "no competitor quote"
            verdict = f"not comparable ({why})"
        elif cell.headroom_bps >= 0:
            verdict = f"1Click delivers {fmt_bps(cell.headroom_bps)} more than {cell.best_competitor}"
        else:
            verdict = f"1Click trails {cell.best_competitor} by {fmt_bps(-cell.headroom_bps)}"
        rank = f"{cell.oneclick_rank}/{(cell.n_competitors_ok or 0) + 1}" if cell.oneclick_rank is not None else NA
        rows.append([label.get(cell.corridor_id, cell.corridor_id), _clip(cell.clip_usd), fmt_bps(cell.headroom_bps, signed=True),
                     cell.headroom_basis or NA, rank, verdict])
    return rows


def _section_microstructure(snap: Snapshot) -> str:
    bench = snap.execution_bench
    if bench is None:
        floor = (snap.sotp.calibration or {}).get("tau_floor_bps")
        return (
            "The execution benchmark was not run in this snapshot (`--skip-bench`). No statement about 1Click's pricing power "
            "versus Relay, LI.FI or Across is made here; the SOTP's public-take floor fell back to the registry assumption "
            f"`public_take_floor_bps` = {fmt_bps(floor, 1)} with a warning. Re-run `make reproduce` to populate this section."
        )
    price_sources = sorted({str((r.price_basis or {}).get("source")) for r in bench.results if r.price_basis})
    lines = [
        f"Executable quotes fetched {bench.ran_at_utc} UTC ({bench.n_quotes_ok} ok of {sum(len(r.quotes) for r in bench.results)}; "
        f"1Click token universe {fmt_int(bench.oneclick_1y_token_universe)} assets on {len(bench.oneclick_blockchains)} chains). "
        "Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input "
        "(headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, "
        "so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. "
        "USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price "
        f"(`price_basis`: {', '.join(price_sources) if price_sources else NA}); raw-unit friction is exact for USDC -> USDC. "
        "Positive headroom means 1Click paid out more after all fees.",
        "",
        _table(["Corridor", "Clip", "Venue", "Status", "Out", "Friction", "ETA", "Route"], _cell_rows(bench),
               ["l", "r", "l", "l", "r", "r", "r", "l"]),
        "",
        _table(["Corridor", "Clip", "Headroom", "Basis", "1Click rank", "Reading"], _headroom_rows(bench), ["l", "r", "r", "l", "r", "l"]),
        "",
    ]
    agg = [
        f"{a}: median headroom {fmt_bps(v, signed=True)} over {fmt_int((bench.headroom_n_by_archetype or {}).get(a))} comparable cells"
        for a, v in (bench.headroom_by_archetype_bps or {}).items()
    ]
    venues = competitive_ceiling_note(bench)
    agg.append(
        f"competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = {fmt_int(bench.competitive_fee_ceiling_n)}"
        + (f"; per-venue medians: {venues}" if venues else "")
        + f"): {fmt_bps(bench.competitive_fee_ceiling_bps)}. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not."
    )
    lines.append(_bullets(agg))
    lines.append("")
    # Honest statements, computed from the cells.
    losses = [(r.corridor_id, r.clip_usd, r.headroom_bps, r.best_competitor) for r in bench.results if r.headroom_bps is not None and r.headroom_bps < 0]
    no_liq = [(r.corridor_id, r.clip_usd) for r in bench.results for q in r.quotes if q.venue == "1click" and q.status == "no_liquidity"]
    unsupported = sorted({f"{q.venue} on {r.corridor_id} ({q.error_code or 'declared'})" for r in bench.results for q in r.quotes if q.status == "unsupported_route"})
    resold = sorted({f"{r.corridor_id} {_clip(r.clip_usd)}" for r in bench.results for q in r.quotes if q.routes_via_near_intents})
    honest: list[str] = []
    if losses:
        honest.append("Where 1Click loses (destination units): " + "; ".join(f"{c} at {_clip(k)} trails {b} by {fmt_bps(-h)}" for c, k, h, b in losses) + ".")
    else:
        honest.append("1Click delivered the most destination units on every comparable cell in this run.")
    oracle_cells = [r for r in bench.results if getattr(r, "oracle_gap_exceeds_headroom", False)]
    if oracle_cells:
        honest.append(
            "Oracle caveat: on " + ", ".join(f"{r.corridor_id} at {_clip(r.clip_usd)}" for r in oracle_cells)
            + " the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg "
            "comparison there would have been decided by oracles, which is why the ranking uses units."
        )
    if no_liq:
        honest.append("Capacity ceiling: 1Click returned `No liquidity available` on " + ", ".join(f"{c} at {_clip(k)}" for c, k in no_liq)
                      + " while competitors filled the same clip; the pricing edge does not extend to that size today.")
    if unsupported:
        honest.append("Structurally unsupported routes: " + ", ".join(unsupported) + ".")
    if resold:
        honest.append("LI.FI's quote on " + ", ".join(resold) + " routes through NEAR Intents itself (tool `near`), so it is 1Click execution plus LI.FI's fee, not an independent price.")
    honest.append(f"Collector summary: {bench.summary_note}")
    lines.append(_bullets(honest))
    return "\n".join(lines)


def _section_concentration(snap: Snapshot) -> str:
    f: IntentsForensics = snap.intents_forensics
    cs = f.caller_sample or {}
    sc = f.solver_concentration or {}
    span = _finite(cs.get("sample_span_s"))
    rows = [
        [c.account_id, _CLASS_LABEL.get(c.cls.value, c.cls.value), fmt_int(c.receipts), fmt_pct(c.share, 1),
         f"[{c.example_tx_hash[:12]}...]({f.explorer_base}/txns/{c.example_tx_hash})" if c.example_tx_hash else NA]
        for c in f.callers[:12]
    ]
    facts = [
        "Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external "
        "predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = "
        f"**{fmt_num(f.hhi_external, 0)}**{_ci_txt(cs.get('hhi_external_ci90'))} (N_eff = {fmt_num(f.n_eff_external, 2)}); over all predecessors {fmt_num(f.hhi_all, 0)}; "
        f"ex-AI-agent {fmt_num(cs.get('hhi_external_ex_ai_agent'), 0)} (N_eff {fmt_num(cs.get('n_eff_external_ex_ai_agent'), 2)}). "
        "These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts "
        "(predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.",
        f"(b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = "
        f"**{fmt_num(sc.get('hhi_solver'), 0)}**{_ci_txt(sc.get('hhi_solver_ci90'))} (N_eff {fmt_num(sc.get('n_eff_solver'), 2)}) across "
        f"{fmt_int(sc.get('n_fills_attributed'))} fill participations in {fmt_int(sc.get('n_fills'))} fills"
        + (f" ({fmt_int(sc.get('n_fills_atomic'))} atomic token_diff fills, {fmt_int(sc.get('n_fills_hub_legs'))} solver-to-settlement-hub legs)"
           if sc.get("n_fills_hub_legs") is not None else "")
        + f", {fmt_int(sc.get('unique_solvers'))} distinct solvers; {fmt_int(sc.get('n_execute_intents_receipts'))} execute_intents receipts decoded, "
        f"{fmt_int(sc.get('n_fills_unresolved'))} unresolved; the solver sample spans {fmt_secs(sc.get('sample_span_s'))}. "
        f"This is the population the solver_cartelization trigger reads; trigger status: {_cartel_status_word(snap)}." if sc else
        "(b) SOLVER concentration: not measured this run (no execute_intents payload decoded).",
        f"AI-agent share of external receipts {fmt_pct(f.ai_agent_share, 1)} is a NAME-PATTERN classification (*.ai.near, *.agent.near); "
        "escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. "
        f"Bridge / token-contract share {fmt_pct(f.bridge_share, 1)}; "
        f"{fmt_int(cs.get('unique_external_callers'))} unique external callers in {fmt_int(cs.get('external_receipts_sampled'))} external receipts.",
        f"Sample: {fmt_int(f.receipts_sampled)} unique receipts over {f.pages_fetched} NearBlocks pages, blocks "
        f"{fmt_int(f.sample_block_range[0]) if f.sample_block_range else NA}-{fmt_int(f.sample_block_range[1]) if len(f.sample_block_range) > 1 else NA}, "
        f"a {fmt_secs(span)} window; lifetime receipts on intents.near {fmt_int(f.lifetime_receipts)}. A window this short is a point sample, "
        "not a market-share estimate; both HHIs move by hundreds of points between runs.",
        "Method mix: " + ", ".join(f"{k} {v}" for k, v in list(f.method_mix.items())[:10]) + ".",
    ]
    solver_rows = [
        [s.get("account_id"), fmt_int(s.get("fills")), fmt_pct(s.get("share"), 1),
         f"[{s['example_tx_hash'][:12]}...]({f.explorer_base}/txns/{s['example_tx_hash']})" if s.get("example_tx_hash") else NA]
        for s in (sc.get("solvers") or [])[:10]
    ]
    parts = [
        _bullets(facts), "",
        f"### {SEC['conc']}.1 Deposit / caller concentration (external predecessors)",
        _table(["Caller", "Class", "Receipts", "Share", "Example tx"], rows, ["l", "l", "r", "r", "l"]),
        f"### {SEC['conc']}.2 Solver concentration (execute_intents signers)",
    ]
    if solver_rows:
        parts.append(_table(["Solver account", "Fill participations", "Share", "Example tx"], solver_rows, ["l", "r", "r", "l"]))
        parts.append(f"Attribution: {sc.get('method')}")
    else:
        parts.append("No solver fill could be attributed in this sample; hhi_solver is null and the cartelization trigger is not measured.")
    return "\n".join(parts)


def _section_supply(snap: Snapshot) -> str:
    t: NearOnchainTruth = snap.near_rpc
    s: SupplyPhysics = snap.supply_physics
    ei = t.epoch_issuance
    inp = s.inputs
    nominal_daily = _finite((s.cross_checks or {}).get("nominal_daily_issuance_near"))
    gap = _finite(ei.measured_minus_nominal_annual_near)
    issuance = [
        f"Measured: {fmt_near(ei.minted_per_epoch_near, 2)} minted at epoch start {fmt_int(ei.epoch_start_height)} "
        f"(previous jump {fmt_near(ei.prev_minted_per_epoch_near, 2)} at {fmt_int(ei.prev_epoch_start_height)}); epoch wall time "
        f"{fmt_num(ei.epoch_duration_hours, 3)} h = {fmt_num(ei.epochs_per_year, 1)} epochs/yr; implied annual issuance "
        f"**{fmt_near(ei.implied_annual_issuance_near)}** = {fmt_pct(ei.implied_annual_inflation_rate, 4)} of supply.",
        f"Nominal: max_inflation_rate {fmt_pct(t.max_inflation_rate, 2)} x total supply {fmt_near(t.total_supply_near)} = "
        f"{fmt_near(ei.nominal_annual_issuance_near)}/yr; measured minus nominal {fmt_near(gap)}/yr "
        f"({fmt_pct(gap / ei.nominal_annual_issuance_near if gap is not None and ei.nominal_annual_issuance_near else None, 2, signed=True)}). "
        f"Daily: measured {fmt_near(s.current_daily_issuance_near)} vs nominal {fmt_near(nominal_daily)}; treasury share "
        f"{fmt_pct(t.protocol_reward_rate, 1)} (validators receive the rest).",
        f"Within-epoch supply drift (net gas burn) {fmt_near(ei.net_burn_per_epoch_near, 2)}/epoch; measured block time {fmt_num(ei.avg_block_time_s, 3)} s. "
        "Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.",
    ]
    sinks = s.current_daily_sinks_near
    sink_rows = [
        ["Buyback (holders revenue / price)", fmt_near(sinks.get("buyback"), 1), (inp.get("capture_ratio").source if inp.get("capture_ratio") else NA),
         f"{fmt_usd(inp['daily_volume_usd'].value if 'daily_volume_usd' in inp else None)}/day x {fmt_bps(inp['gross_take_bps'].value if 'gross_take_bps' in inp else None)} gross x alpha "
         f"{fmt_pct(inp['capture_ratio'].value if 'capture_ratio' in inp else None, 1)} / {fmt_usd(inp['near_price_usd'].value if 'near_price_usd' in inp else None, compact=False, decimals=2)}"],
        ["L1 gas burn", fmt_near(sinks.get("gas_burn"), 1), (inp.get("gas_burn_near_per_day").source if inp.get("gas_burn_near_per_day") else NA),
         (inp.get("gas_burn_near_per_day").justification if inp.get("gas_burn_near_per_day") else NA)],
        ["NEP state-lock growth", fmt_near(sinks.get("state_lock"), 1), (inp.get("state_lock_growth_near_per_day").source if inp.get("state_lock_growth_near_per_day") else NA),
         (inp.get("state_lock_growth_near_per_day").justification if inp.get("state_lock_growth_near_per_day") else NA)],
        ["Total sinks", fmt_near(sinks.get("total"), 1), "", f"coverage {fmt_pct(s.sink_coverage_ratio, 1)} of measured issuance; net float "
         f"{fmt_near(s.current_net_float_change_near_day, 0)}/day"],
    ]
    be_rows = []
    ceiling = s.breakeven_daily_volume_usd_at_ceiling or {}
    v_day = _finite(inp["daily_volume_usd"].value) if "daily_volume_usd" in inp else None
    for key, v in s.breakeven_daily_volume_usd.items():
        be_rows.append([_REGIME_LABEL.get(key, key), fmt_usd(v), fmt_num(v / v_day, 1) + "x" if v_day else NA, fmt_usd(ceiling.get(key)) if ceiling else "benchmark not run"])
    lock_rows = []
    for sink in t.tracked_sinks:
        lock_rows.append([
            sink.account_id, "yes" if sink.has_contract else "no", fmt_int(sink.storage_bytes), fmt_near(sink.storage_locked_near, 1),
            fmt_int(sink.growth_bytes_per_day) if sink.growth_bytes_per_day is not None else NA,
            fmt_near(sink.growth_locked_near_per_day, 2) if sink.growth_locked_near_per_day is not None else NA,
            fmt_num(sink.growth_window_days, 1) + " d" if sink.growth_window_days is not None else NA,
        ])
    lock_notes = [
        f"Total state-locked across {len(t.tracked_sinks)} tracked contracts: **{fmt_near(t.total_state_locked_near)}** at "
        f"{fmt_num(t.storage_near_per_kb, 2)} NEAR/KB (storage_amount_per_byte {t.storage_amount_per_byte_yocto:,} yocto). Measured lock growth "
        f"{fmt_near(t.measured_state_lock_growth_near_per_day, 1)}/day over {', '.join(t.measured_state_lock_growth_sinks) or 'no sinks'} "
        f"(archival {'available' if t.archival_available else 'unavailable'}).",
    ]
    if t.missing_accounts:
        lock_notes.append(f"Accounts not found on mainnet and excluded: {', '.join(t.missing_accounts)}.")
    traj_rows = []
    for key, pair in _regime_rows(s).items():
        for kind, traj in pair.items():
            if traj is None:
                continue
            traj_rows.append([
                _REGIME_LABEL.get(key, key), "run-rate volume" if kind == "flow" else f"{fmt_pct(traj.volume_growth_yoy, 0, signed=True)} YoY volume",
                fmt_near(traj.daily_issuance_start), fmt_near(traj.daily_issuance_end), fmt_near(traj.gross_issuance_cum[-1]),
                fmt_near(traj.buyback_cum[-1] + traj.gas_burn_cum[-1] + traj.state_lock_cum[-1]), fmt_near(traj.net_float_change_cum[-1]),
                fmt_month(traj.crossover_month), fmt_month(traj.cumulative_crossover_month),
            ])
    staking_rows = [
        [_REGIME_LABEL.get(r.get("regime"), r.get("regime")), fmt_pct(r.get("inflation_rate"), 2), fmt_pct(r.get("nominal_staking_apr"), 2),
         fmt_pct(r.get("real_staking_apr"), 2), fmt_pct(r.get("buyback_accrual_apr"), 3), fmt_pct(r.get("real_staking_apr_with_buyback"), 2),
         fmt_pct(r.get("real_non_staker_apr"), 2)]
        for r in s.staking_yield_table
    ]
    kb_default = _finite(inp["kb_per_agent_vault"].value) if "kb_per_agent_vault" in inp else None
    agent_rows = [
        [fmt_int(r.get("agents")), fmt_num(r.get("kb_per_agent"), 0) + " KB", fmt_near(r.get("locked_near")), fmt_num(r.get("days_of_issuance_absorbed"), 1),
         fmt_pct(r.get("share_of_supply"), 3)]
        for r in s.agent_scale_table if r.get("is_default_kb") or r.get("kb_per_agent") in (5.0, 50.0)
    ]
    parts = [
        f"### {SEC['supply']}.1 Issuance: measured vs nominal", _bullets(issuance), "",
        f"### {SEC['supply']}.2 Daily sinks (NEAR/day, live)", _table(["Sink", "NEAR/day", "Source", "Basis"], sink_rows, ["l", "r", "l", "l"]), "",
        f"### {SEC['supply']}.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)",
        _table(["Regime (terminal rate)", "V* at live take", "vs today", "V* at competitive ceiling"], be_rows, ["l", "r", "r", "r"]),
        "Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.", "",
        f"### {SEC['supply']}.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)",
        _table(["Regime", "Volume path", "Issuance/day m1", "Issuance/day m36", "Gross issuance 36m", "Sinks 36m", "Net float 36m", "Flow crossover", "Cumulative crossover"],
               traj_rows, ["l", "l", "r", "r", "r", "r", "r", "l", "l"]), "",
        f"### {SEC['supply']}.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)",
        _table(["Account", "Contract", "storage_usage bytes", "Locked", "Growth B/day", "Growth NEAR/day", "Window"], lock_rows, ["l", "l", "r", "r", "r", "r", "r"]),
        _bullets(lock_notes), "",
        f"### {SEC['supply']}.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)",
        _table(["Regime", "Inflation", "Nominal APR", "Real APR", "Buyback accrual", "Real APR + accrual", "Non-staker real"], staking_rows, ["l", "r", "r", "r", "r", "r", "r"]),
        f"Live: {t.active_validator_count} validators, {fmt_near(t.total_staked_near)} staked = {fmt_pct(t.staked_supply_ratio, 2)} of supply.", "",
        f"### {SEC['supply']}.7 Agent-scale state lock (locked = agents x KB x {fmt_num(t.storage_near_per_kb, 2)} NEAR/KB; default {fmt_num(kb_default, 0)} KB per vault is an assumption)",
        _table(["Agents", "KB/agent", "Locked", "Days of issuance absorbed", "Share of supply"], agent_rows, ["r", "r", "r", "r", "r"]),
    ]
    return "\n".join(parts)


def _section_sotp(snap: Snapshot) -> str:
    sotp: SotpValuation = snap.sotp
    comps: PeerComps = snap.comps
    cal = sotp.calibration or {}
    eng_rows = [
        [e.key, fmt_usd(e.p10), fmt_usd(e.p25), fmt_usd(e.p50), fmt_usd(e.p75), fmt_usd(e.p90), "yes" if e.assumption_heavy else "no"]
        for e in sotp.engines
    ]
    tot_rows = [
        ["FDV (all engines)"] + [fmt_usd(sotp.fdv_percentiles.get(k)) for k in ("p10", "p25", "p50", "p75", "p90")],
        ["FDV ex-monetary"] + [fmt_usd(sotp.fdv_ex_monetary_percentiles.get(k)) for k in ("p10", "p25", "p50", "p75", "p90")],
        ["Implied price / NEAR"] + [fmt_usd(sotp.price_percentiles.get(k), compact=False, decimals=2) for k in ("p10", "p25", "p50", "p75", "p90")],
    ]
    cal_rows = [
        ["Public take t=0 (gross)", fmt_bps(cal.get("tau_pub_start_bps")), str(cal.get("tau_pub_start_method") or NA)],
        ["Blended gross take / net take", f"{fmt_bps(cal.get('blended_gross_take_bps'))} / {fmt_bps(cal.get('net_take_start_bps'))}", "DefiLlama near-intents fees / volume; net = gross x alpha"],
        ["Capture ratio alpha", fmt_pct(cal.get("alpha_capture"), 2), str(cal.get("alpha_source") or NA)],
        ["Confidential take t=0", fmt_bps(cal.get("tau_conf_start_bps"), 0), cal.get("tau_conf_source") or "assumption (no live confidential fee series)"],
        ["Public take floor", fmt_bps(cal.get("tau_floor_bps")), f"{cal.get('tau_floor_source')}; cross-VM headroom {fmt_bps(cal.get('headroom_cross_vm_bps'), signed=True)}, competitor ceiling {fmt_bps(cal.get('competitive_fee_ceiling_bps'))}"],
        ["Compression lambda (public / confidential)", f"{fmt_num(cal.get('lambda_pub_monthly'), 3)} / {fmt_num(cal.get('lambda_conf_monthly'), 3)} per month", "geometric reversion to the floor"],
        ["Volume growth (public / confidential, monthly)", f"{fmt_pct(cal.get('growth_monthly_pub'), 2)} / {fmt_pct(cal.get('growth_monthly_conf'), 2)}", f"confidential share {fmt_pct(cal.get('confidential_share_start'), 1)} -> {fmt_pct(cal.get('confidential_share_target'), 0)} target"
         + (" (start share ASSUMED: registry confidential_share; nearstats split failed the plausibility guard)" if cal.get("confidential_share_status") == "implausible_fallback"
            else " (start share not measured: split unavailable, credited 0)" if cal.get("confidential_engine_measured") is False else " (start share measured)")],
        ["Sigma: price (annual) / volume (monthly)", f"{fmt_num(cal.get('sigma_price_annual'), 3)} / {fmt_num(cal.get('sigma_volume_monthly'), 3)}", f"{cal.get('sigma_volume_source')}; confidential sigma x {fmt_num(cal.get('confidential_sigma_multiplier'), 2)}"],
        ["Terminal multiple (FDV / annual holder revenue)", f"{fmt_mult(cal.get('terminal_multiple_used'))} (raw {fmt_mult(cal.get('terminal_multiple_raw'))})",
         f"source {cal.get('terminal_multiple_source') or NA}: {cal.get('terminal_multiple_basis') or NA}"
         + ("; clipped to registry guardrails" if cal.get("terminal_multiple_clipped") else "")],
        ["Discount rate", fmt_pct(sotp.discount_rate, 0), "assumption"],
        ["Supply at horizon (glidepath)", fmt_near(cal.get("supply_at_horizon_used")), str(cal.get("price_basis") or NA)],
        ["Current FDV", fmt_usd(sotp.current_fdv_usd), f"{cal.get('current_fdv_basis') or NA}; CoinGecko FDV via nearstats {fmt_usd(cal.get('current_fdv_coingecko_usd'))} "
         f"({fmt_num(cal.get('current_fdv_nearstats_gap_pct'), 2)}% gap, struck at a different instant; cross-check only)"],
        ["GBM convention", "mean-matching (Ito)", str(cal.get("gbm_convention") or NA)],
        ["Terminal public volume, month H", f"mean {fmt_usd(cal.get('volume_terminal_mean_usd_day'))}/day; median {fmt_usd(cal.get('volume_terminal_median_usd_day'))}/day",
         f"start {fmt_usd(cal.get('volume_start_usd_day'))}/day; MC sample mean {fmt_usd(cal.get('volume_terminal_mean_usd_day_mc'))}, median {fmt_usd(cal.get('volume_terminal_median_usd_day_mc'))}; "
         "the labeled YoY growth is the growth of the MEAN path"],
    ]
    peer_rows = []
    for p in [*comps.peers, *comps.near_components, comps.near_combined]:
        peer_rows.append([
            f"{p.symbol} ({p.slug})", fmt_usd(p.fees_30d_usd), fmt_usd(p.revenue_30d_usd), fmt_usd(p.fdv_usd), fmt_mult(p.fdv_to_fees), fmt_mult(p.fdv_to_revenue),
            (p.revenue_methodology or NA)[:110],
        ])
    peer_notes = [
        f"Median ex-NEAR FDV / annualized revenue {fmt_mult(comps.median_fdv_to_revenue_ex_near)} (n = {fmt_int(comps.n_peers_in_revenue_median)}); "
        f"FDV / annualized fees {fmt_mult(comps.median_fdv_to_fees_ex_near)} (n = {fmt_int(comps.n_peers_in_fees_median)}). {comps.annualization or ''}",
        "`revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live "
        "methodology text is carried in the table so the multiple is read with its definition.",
    ]
    hm = sotp.sensitivity_heatmap or {}
    xs, ys = hm.get("x") or [], hm.get("y") or []
    grid, defl = hm.get("fdv_p50") or [], hm.get("net_deflation") or []
    hm_rows = []
    for i, y in enumerate(ys):
        row = [fmt_bps(y, 0)]
        for j, _x in enumerate(xs):
            v = grid[i][j] if i < len(grid) and j < len(grid[i]) else None
            flag = "*" if (i < len(defl) and j < len(defl[i]) and defl[i][j]) else ""
            row.append(f"{fmt_usd(v)}{flag}")
        hm_rows.append(row)
    shares = cal.get("engine_shares_on_median_total_path") or {}
    parts = [
        f"### {SEC['sotp']}.1 Engines (percentiles over paths, USD; discounted to today)",
        _table(["Engine", "P10", "P25", "P50", "P75", "P90", "Assumption-heavy"], eng_rows, ["l", "r", "r", "r", "r", "r", "l"]),
        _table(["Total", "P10", "P25", "P50", "P75", "P90"], tot_rows, ["l", "r", "r", "r", "r", "r"]),
        "Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the "
        f"total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse {fmt_usd(shares.get('clearinghouse'))} "
        f"({fmt_pct(shares.get('clearinghouse_share'), 0)}) + confidential {fmt_usd(shares.get('confidential'))} ({fmt_pct(shares.get('confidential_share'), 0)}) + "
        f"monetary {fmt_usd(shares.get('monetary'))} ({fmt_pct(shares.get('monetary_share'), 0)}) = {fmt_usd(shares.get('fdv_total'))}.",
        "",
        _bullets([e.method for e in sotp.engines]), "",
        f"### {SEC['sotp']}.2 Calibration (what the engines were fed)",
        _table(["Parameter", "Value", "Source / basis"], cal_rows), "",
        f"### {SEC['sotp']}.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)",
        _table(["Protocol", "Fees 30d", "Revenue 30d", "FDV", "FDV/fees", "FDV/revenue", "Revenue methodology (live text)"], peer_rows, ["l", "r", "r", "r", "r", "r", "l"]),
        _bullets(peer_notes), "",
        f"### {SEC['sotp']}.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take ({_REGIME_LABEL.get(hm.get('regime'), hm.get('regime'))}; * = net-deflationary)",
        _table(["Net take \\ Volume/day"] + [fmt_usd(x) for x in xs], hm_rows, ["l"] + ["r"] * len(xs)),
        f"Current FDV {fmt_usd(sotp.current_fdv_usd)}; confidential share used in the split {fmt_pct(hm.get('confidential_share_used'), 1)}. "
        "Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts "
        "and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).",
        "",
        f"### {SEC['sotp']}.5 Out-of-sample backtest of the volume engine",
        _backtest_paragraph(snap),
    ]
    return "\n".join(parts)


def _backtest_paragraph(snap: Snapshot) -> str:
    """Coverage and bias of the volume GBM re-calibrated at each historical origin (models/backtest.py)."""
    bt = getattr(snap, "backtest", None)
    if not isinstance(bt, Mapping) or not bt.get("rows"):
        return "Not computed this run: `backtest` is null or has no scored forecasts (see warnings)."
    by_h = bt.get("by_horizon") or {}
    rows = []
    for h, s in by_h.items():
        if not s.get("n"):
            continue
        ci = s.get("coverage_ci90_wilson") or [None, None]
        rows.append([
            f"{h} month{'s' if h != '1' else ''}", fmt_int(s["n"]), f"{fmt_pct(s['coverage_p10_p90'], 0)} [{fmt_pct(ci[0], 0)}-{fmt_pct(ci[1], 0)}]",
            fmt_num(s.get("binom_p_vs_80"), 2), f"{fmt_int(s['below_p10'])} / {fmt_int(s['above_p90'])}",
            f"{fmt_num(s.get('median_ratio_realized_to_p50'), 2)}x", " ".join(str(c) for c in s.get("pit_hist") or []),
        ])
    s1 = by_h.get("1") or {}
    r1 = s1.get("median_ratio_realized_to_p50")
    direction = "under-predicts" if isinstance(r1, (int, float)) and r1 > 1 else "over-predicts"
    per = bt.get("by_period") or {}
    e1, l1 = (per.get("early") or {}).get("1") or {}, (per.get("late") or {}).get("1") or {}
    def _cov_list(block: Mapping[str, Any]) -> str:
        return ", ".join(f"{h}m {fmt_pct(s.get('coverage_p10_p90'), 0)} (n = {fmt_int(s.get('n'))})" for h, s in block.items() if s.get("n"))

    split = (
        f" Split at the middle origin ({per.get('split_origin_date')}), coverage before: {_cov_list(per.get('early') or {})}; "
        f"from it: {_cov_list(per.get('late') or {})}."
        if e1.get("n") and l1.get("n") else ""
    )
    misses = [r for r in bt.get("rows") or [] if not r.get("inside")]
    if split and misses:
        early_miss = sum(1 for r in misses if str(r.get("origin_date")) < str(per.get("split_origin_date")))
        above = sum(1 for r in misses if r.get("realized_30d_usd", 0) > r.get("p90", float("inf")))
        split += f" {early_miss} of the {len(misses)} misses come from origins before the split; {above} of {len(misses)} are realized volume above P90."
    md = ((bt.get("variants") or {}).get("measured_drift") or {}).get("by_horizon") or {}
    md_txt = ", ".join(f"{h}m {fmt_pct(s.get('coverage_p10_p90'), 0)}" for h, s in md.items() if s.get("n"))
    verdict = "passes at every horizon" if (bt.get("calibrated") or {}).get("all") else "fails at " + (
        ", ".join(f"{h}m" for h, ok in ((bt.get("calibrated") or {}).get("per_horizon") or {}).items() if ok is False) or "n/a")
    text = (
        f"At each of {fmt_int(bt.get('n_origins'))} monthly origins from {bt.get('first_origin')} to {bt.get('last_origin')} the volume GBM was re-calibrated "
        f"on data up to the origin only (trailing 30-day volume, sigma from the trailing 365 days, drift = public_volume_growth_yoy "
        f"{fmt_pct(bt.get('growth_yoy_used'), 0)}) and its P10-P90 band for 30-day volume was compared with what happened "
        f"({bt.get('source')}, {bt.get('first_day')} to {bt.get('last_day')}). The test of 80% coverage {verdict} "
        f"({bt.get('calibrated', {}).get('rule')}). At 1 month the median realized volume is {fmt_num(r1, 2)}x the forecast median: the model {direction}."
        f"{split} With the drift replaced by the trailing mean log return (no registry input) coverage is {md_txt or 'n/a'}. "
        "Not backtested: " + "; ".join(bt.get("not_tested") or []) + ". 3- and 6-month forecasts from monthly origins overlap, so their errors are correlated "
        "and the binomial interval overstates the precision."
    )
    table = _table(["Horizon", "n", "P10-P90 coverage [90% Wilson]", "Binomial p vs 80%", "Below P10 / above P90", "Median realized / P50", "PIT histogram (5 bins)"],
                   rows, ["l", "r", "r", "r", "r", "r", "l"])
    return text + "\n\n" + table


def _trigger_status(breached: bool | None, evaluated: bool | None = None) -> str:
    if breached is None or evaluated is False:
        return "not measured"
    return "**BREACHED**" if breached else "not breached"


def _section_bear(snap: Snapshot) -> str:
    b: BearCase = snap.bear_case
    basis = b.value_basis or "deterministic at median inputs; not a Monte Carlo percentile"
    rows = []
    for s in b.scenarios:
        rows.append([
            s.key, fmt_usd(s.sotp_fdv_p50), fmt_pct(s.drawdown_pct, 1, signed=True), fmt_usd(s.price_p50, compact=False, decimals=2),
            fmt_pct(s.price_drawdown_pct, 1, signed=True), fmt_month(s.crossover_month),
        ])
    rows.append(["combined worst", fmt_usd(b.combined_worst_fdv), fmt_pct(b.combined_drawdown_pct, 1, signed=True),
                 fmt_usd(b.combined_worst_price, compact=False, decimals=2), fmt_pct(b.combined_price_drawdown_pct, 1, signed=True), fmt_month(b.combined_crossover_month)])
    trig_rows = []
    for s in b.scenarios:
        cur_s, thr_s = _trigger_value(s, s.current_value), _trigger_value(s, s.trigger_threshold)
        extra = ""
        if s.secondary_metric:
            extra = (
                f"; secondary {s.secondary_metric} {fmt_bps(s.secondary_value, signed=True)} {s.secondary_comparator} {fmt_bps(s.secondary_threshold, 0)} "
                f"({_trigger_status(s.secondary_breached, s.secondary_evaluated).strip('*')})"
            )
        note = f" Note: {s.trigger_note}" if s.trigger_note else ""
        status = _trigger_status(s.trigger_breached, s.trigger_evaluated)
        if s.trigger_breached is None and getattr(s, "trigger_status", None) == "inconclusive":
            span = getattr(s, "sample_span_s", None)
            status = ("inconclusive (sample span " + fmt_secs(span) + " < " + fmt_secs(getattr(s, "min_sample_span_s", None)) + ")"
                      if getattr(s, "primary_status", None) == "short_span" else "inconclusive (CI straddles threshold)")
        # A graded solver HHI on few sampled fills is within sampling noise of the threshold: say so next to the grade.
        if getattr(s, "sample_thin", False) and s.trigger_breached is not None:
            n_sampled = getattr(s, "solver_fills_sampled", None)
            status += f" (thin sample: {fmt_int(n_sampled)} fills)" if isinstance(n_sampled, (int, float)) else " (thin sample)"
        trig_rows.append([s.key, s.early_warning_metric, cur_s, f"{s.trigger_comparator or ''} {thr_s}".strip(), status,
                          f"{s.monitor_source} ({s.monitor_field}){extra}.{note}"])
    narratives = [f"**{s.title}.** {s.narrative}" for s in b.scenarios]
    parts = [
        f"Value basis: {basis}. Base deterministic FDV (median inputs) {fmt_usd(b.base_fdv_p50)}, implied price "
        f"{fmt_usd(b.base_price_p50, compact=False, decimals=2)}; the Monte Carlo P50 of section {SEC['sotp']} is a different statistic and is not what "
        f"the drawdowns below are measured against. {b.drawdown_definition or ''}",
        "",
        _table(["Scenario", "Deterministic FDV (median inputs)", "FDV drawdown", "Implied price", "Price drawdown", "Flow crossover"], rows, ["l", "r", "r", "r", "r", "l"]),
        "",
        f"### {SEC['bear']}.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)",
        _table(["Scenario", "Metric", "Now", "Trigger", "Status", "Monitor"], trig_rows),
        "",
        f"### {SEC['bear']}.2 Scenario narratives",
        "\n\n".join(narratives),
        "",
        f"### {SEC['bear']}.3 Falsification summary",
        b.falsification_summary,
    ]
    return "\n".join(parts)


def _section_scorecard(snap: Snapshot) -> str:
    rows = [[c.claim, f"**{c.status}**", c.value, c.source, c.confidence, c.note] for c in snap.evidence_scorecard]
    if not rows:
        return "No evidence scorecard was built for this snapshot."
    return _table(["Claim", "Status", "Value", "Source", "Confidence", "Note"], rows)


def _section_assumptions(snap: Snapshot) -> str:
    rows = [[a.key, f"{a.value:g}", a.unit, f"[{a.low:g}, {a.high:g}]", a.justification] for a in snap.assumptions]
    measured: dict[str, Any] = {}
    for src in (snap.supply_physics.inputs, snap.sotp.inputs):
        for k, a in src.items():
            if a.source != "assumption" and k not in measured:
                measured[k] = a
    mrows = [[a.key, _plain_number(a.value), a.unit, a.source, a.justification[:160]] for a in measured.values()]
    return "\n".join([
        f"### {SEC['assumptions']}.1 Labeled assumptions (slider inputs; never presented as measured)",
        _table(["Key", "Default", "Unit", "Range", "Justification"], rows),
        "",
        f"### {SEC['assumptions']}.2 Measured and derived model inputs (point values with their source)",
        _table(["Key", "Value", "Unit", "Source", "Basis"], mrows),
    ])


def _section_reproduce(snap: Snapshot) -> str:
    rc = snap.run_config or {}
    args = " ".join(str(a) for a in (rc.get("argv") or [])) if rc.get("argv") else ""
    cmd = f"uv run python -m valuo.reproduce {args}".strip()
    return "\n".join([
        "```bash",
        "# from the repo root; no API keys; ~20-60 s wall clock",
        "make reproduce          # == cd quant && uv run python -m valuo.reproduce   (canonical artifacts/)",
        "make test               # offline unit tests + invariant checks against artifacts/",
        f"# this snapshot was produced by: cd quant && {cmd}",
        "# faster smoke (no quote race, 2,000 paths) writes to artifacts/dev/, never over the canonical files:",
        "make reproduce-fast     # == cd quant && uv run python -m valuo.reproduce --skip-bench --paths 2000",
        "# verify the artifact bytes against the manifest:",
        "shasum -a 256 artifacts/latest_snapshot.json   # must equal manifest.json: snapshot_sha256",
        "```",
        "",
        f"Determinism: `numpy.random.default_rng({snap.seed})` draws every shock up front; re-running the Monte Carlo on this snapshot's inputs "
        "reproduces every percentile bit-for-bit (tests/test_invariants.py::test_monte_carlo_determinism). Live inputs change block to block, "
        "so a fresh run moves the numbers; the memo always states its block and timestamp.",
    ])


def _section_provenance(snap: Snapshot, manifest: Manifest | None) -> str:
    ps = snap.provenance_summary or {}
    sources = manifest.sources if manifest is not None else ps.get("sources") or {}
    failures = [r for r in manifest.records if not r.ok] if manifest is not None else []
    rows = [[src, fmt_int(n)] for src, n in sorted(sources.items())]
    fail_rows = [[r.source, r.name, str(r.http_status or ""), (r.error or "")[:100]] for r in failures[:40]]
    parts = [
        f"{fmt_int(ps.get('records'))} raw exchanges ({fmt_int(ps.get('ok'))} ok, {fmt_int(ps.get('failures'))} failed), {fmt_int(ps.get('bytes'))} bytes hashed; "
        f"raw bodies persisted under `{manifest.raw_dir if manifest is not None and manifest.raw_dir else 'artifacts/raw/'}` and listed with SHA-256 in `manifest.json`.",
        "",
        _table(["Source", "Records"], rows, ["l", "r"]),
    ]
    if fail_rows:
        parts += ["", "Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):",
                  _table(["Source", "Name", "HTTP", "Error"], fail_rows)]
    if snap.warnings:
        parts += ["", f"### {SEC['provenance']}.1 Methodology warnings recorded during the run ({len(snap.warnings)})", _bullets(snap.warnings)]
    return "\n".join(parts)


# ============================================================================ reframed thesis: market-implied, tornado, relative value
def _fmt_unit(v: Any, unit: str | None) -> str:
    """A solve / tornado value in its natural unit."""
    x = _finite(v)
    if x is None:
        return NA
    u = unit or ""
    if u in ("ratio_yoy", "ratio_annual", "ratio", "ratio_monthly"):
        return fmt_pct(x, 1)
    if u == "per_month":
        return f"{x * 100:.1f}%/month"
    if u == "bps":
        return fmt_bps(x, 2)
    if u.startswith("x"):
        return f"{x:,.2f}x" if u == "x_base" or abs(x) < 10 else f"{x:,.0f}x"
    if u in ("usd_per_year",):
        return f"{fmt_usd(x)}/yr"
    if u == "USD":
        return fmt_usd(x, compact=False, decimals=2)
    if u == "NEAR_per_day":
        return f"{x:,.0f} NEAR/day"
    return _plain_number(x)


def _solve(mi: Mapping[str, Any] | None, param: str) -> Mapping[str, Any] | None:
    if not mi:
        return None
    return next((r for r in mi.get("solves") or [] if r.get("param") == param), None)


def _within(r: Mapping[str, Any] | None) -> bool | None:
    return ((r or {}).get("required_vs_evidence") or {}).get("within_evidence")


def _ci(v: Any) -> tuple[float, float] | None:
    if isinstance(v, (list, tuple)) and len(v) == 2 and all(_finite(x) is not None for x in v):
        return float(v[0]), float(v[1])
    return None


def _ci_txt(v: Any) -> str:
    ci = _ci(v)
    return f" (bootstrap 90% CI {ci[0]:,.0f}-{ci[1]:,.0f})" if ci else " (no bootstrap CI)"


def _cartel_status_word(snap: Snapshot) -> str:
    s = next((x for x in snap.bear_case.scenarios if x.key == "solver_cartelization"), None)
    if s is None:
        return "not evaluated"
    st = getattr(s, "trigger_status", None) or ("not_measured" if s.trigger_breached is None else ("breached" if s.trigger_breached else "not_breached"))
    if st == "inconclusive" and getattr(s, "primary_status", None) == "short_span":
        return f"inconclusive (span {fmt_secs(getattr(s, 'sample_span_s', None))} < {fmt_secs(getattr(s, 'min_sample_span_s', None))} minimum)"
    return st.replace("_", " ")


def _confidential_boundary_sentence(snap: Snapshot) -> str:
    """What the confidential treasury on intents.near shows on-chain (TVL, flows), or '' when not audited."""
    b = getattr(snap.intents_forensics, "confidential_boundary", None) or {}
    if not isinstance(b, dict) or _finite(b.get("tvl_usd")) is None:
        return ""
    vol = snap.intents_forensics.volume or {}
    acct = str(b.get("treasury_account") or "")
    parts = [
        f" On-chain cross-check: the Confidential Intents treasury (`{acct[:8]}...{acct[-6:]}` in `intents.near`) holds "
        f"{fmt_usd(b.get('tvl_usd'))} at block {fmt_num(b.get('block_height'), 0)} ({b.get('n_tokens')} tokens, "
        f"{b.get('n_tokens_unpriced_nonzero')} unpriced)"
    ]
    if _finite(b.get("net_flow_30d_usd")) is not None:
        parts.append(f"; net 30-day boundary flow {fmt_usd(b.get('net_flow_30d_usd'))} at today's prices")
    ratio = _finite(vol.get("confidential_boundary_inflow_ratio_24h"))
    if _finite(b.get("flow_24h_in_lower_bound_usd")) is not None:
        parts.append(
            f"; over 24h at least {fmt_usd(b.get('flow_24h_in_lower_bound_usd'))} entered and {fmt_usd(b.get('flow_24h_out_lower_bound_usd'))} left "
            f"(hourly snapshots, lower bounds)" + (f", an inflow of {fmt_pct(ratio, 1)} of 24h volume" if ratio is not None else "")
        )
    parts.append(
        ". Confidential swaps settle on a private chain whose RPC needs authentication, so swap volume itself cannot be read; "
        "boundary inflow is a proxy, not the share (it nets same-hour flows and includes solver inventory)."
    )
    return "".join(parts)


def _confidential_status_sentence(snap: Snapshot) -> str:
    return _confidential_status_core(snap) + _confidential_boundary_sentence(snap)


def _confidential_status_core(snap: Snapshot) -> str:
    vol = snap.intents_forensics.volume or {}
    cal = snap.sotp.calibration or {}
    status = vol.get("confidential_share_status") or ("measured" if _finite(vol.get("confidential_share_30d")) is not None else "unavailable")
    share = _finite(vol.get("confidential_share_30d"))
    reported = _finite(vol.get("confidential_share_30d_reported"))
    if status == "implausible_fallback":
        return (
            f"Confidential share: NOT MEASURED this run. nearstats reported {fmt_pct(reported, 4)} of 30d volume as confidential, which its own "
            f"payload contradicts ({'; '.join(str(r) for r in (vol.get('confidential_share_reason') or [])[1:3]) or 'see warnings'}); the model uses the "
            f"registry assumption confidential_share = {fmt_pct(share, 0)} (range {fmt_pct(next((a.low for a in snap.assumptions if a.key == 'confidential_share'), None), 0)}"
            f"-{fmt_pct(next((a.high for a in snap.assumptions if a.key == 'confidential_share'), None), 0)}), so Engine 2 "
            f"({fmt_usd(((cal.get('deterministic_base') or {}).get('engine_confidential')))} of the {fmt_usd(((cal.get('deterministic_base') or {}).get('fdv_total')))} "
            "expected-path FDV) values an assumed volume."
        )
    if status == "unavailable":
        return "Confidential share: not measured (nearstats split missing); Engine 2 is credited zero confidential volume."
    return f"Confidential share: measured at {fmt_pct(share, 1)} of 30d volume (nearstats public/confidential split, status `measured`)."


def _cartel_sentence(snap: Snapshot) -> str:
    s = next((x for x in snap.bear_case.scenarios if x.key == "solver_cartelization"), None)
    sc = snap.intents_forensics.solver_concentration or {}
    if s is None:
        return "Solver cartel trigger: not evaluated."
    status = getattr(s, "trigger_status", None) or ("not_measured" if s.trigger_breached is None else ("breached" if s.trigger_breached else "not_breached"))
    hhi = _finite(sc.get("hhi_solver"))
    span = _finite(getattr(s, "sample_span_s", None) if getattr(s, "sample_span_s", None) is not None else sc.get("sample_span_s"))
    min_span = _finite(getattr(s, "min_sample_span_s", None))
    base = (f"Solver HHI {fmt_num(hhi, 0)}{_ci_txt(sc.get('hhi_solver_ci90'))} over {fmt_int(sc.get('n_fills_attributed'))} fill participations "
            f"spanning {fmt_secs(span)}" if hhi is not None else "Solver HHI not measured")
    if status == "inconclusive":
        if getattr(s, "primary_status", None) == "short_span":
            why = f"the sample spans {fmt_secs(span)}, under the {fmt_secs(min_span)} minimum (solver_sample_min_span_s), so the HHI is not graded"
        else:
            why = f"the CI straddles the {fmt_num(s.trigger_threshold, 0)} threshold"
        sec = _finite(getattr(s, "secondary_value", None))
        tail = ("cross-VM headroom is unmeasured (no quote race), so neither condition is graded" if sec is None else
                f"cross-VM headroom {fmt_bps(sec, signed=True)} is the only graded condition ({'breached' if sec < 0 else 'not breached'})")
        return f"{base}. Cartel trigger: INCONCLUSIVE ({why}); {tail}."
    if status == "breached":
        note = (s.trigger_note or "").split("; ")[0].rstrip(".")
        return f"{base}. Cartel trigger: BREACHED ({note})."
    if status == "not_breached":
        return f"{base}. Cartel trigger: not breached (HHI_solver graded below {fmt_num(s.trigger_threshold, 0)} and cross-VM headroom non-negative)."
    return f"{base}. Cartel trigger: not measured."


def _discount_rate_unreachable_txt(snap: Snapshot, dr: Mapping[str, Any], target: Any, cap: float | None) -> str:
    """One conditional sentence for an unreachable discount-rate solve, computed from the model rather than the reason string.

    Re-evaluates the deterministic FDV at the bottom of the discount-rate search range (``market_implied.fdv_at`` on the
    snapshot's own primitives). When that FDV is still below the market's, no discount rate closes the gap; otherwise the
    solve failed for another reason and the sentence says the gap is not resolved by the discount rate alone.
    """
    lo = _finite((dr.get("search_bounds") or [None])[0])
    fdv_lo: float | None = None
    try:
        from valuo.models.market_implied import fdv_at, primitives_from_snapshot

        if lo is not None:
            fdv_lo = _finite(fdv_at(primitives_from_snapshot(snap.model_dump(mode="json")), discount_rate=lo))
    except Exception:  # noqa: BLE001 - the memo must render even when the snapshot cannot be re-evaluated
        fdv_lo = None
    market = _finite(target)
    cap_txt = f", because the terminal multiple is capped at {fmt_mult(cap, 0)}" if cap is not None else ""
    if fdv_lo is not None and market is not None and fdv_lo < market:
        return (f" No discount rate closes the gap: even at {fmt_pct(lo, 0)} the model reaches {fmt_usd(fdv_lo)} against the market's "
                f"{fmt_usd(market)}{cap_txt}. The gap is a multiple question, not a discount-rate question.")
    return (f" No discount rate in the {fmt_pct(lo, 0)}-{fmt_pct(_finite((dr.get('search_bounds') or [None, None])[1]), 0)} search range "
            f"reproduces the market's {fmt_usd(market)}{cap_txt}.")


def _conclusion(snap: Snapshot, mi: Mapping[str, Any]) -> str:
    """The one-paragraph reading of the solves, computed from the numbers so it stays true if signs flip."""
    gap = _finite(mi.get("gap_multiple"))
    target = mi.get("current_fdv_usd")
    years = (_finite(mi.get("horizon_months")) or 36) / 12
    if gap is not None and gap <= 1.0:
        return (
            f"**Conclusion.** The model's expected-path FDV ({fmt_usd(mi.get('base_fdv_usd'))}) is at or above the market FDV ({fmt_usd(target)}): at base "
            "inputs the market price needs no input beyond the measured run-rate and the labeled assumptions. The solves below show how far each input "
            "could fall before the model drops to the market price."
        )
    tm, g, tau, rev = (_solve(mi, k) for k in ("terminal_multiple", "public_volume_growth_yoy", "tau_pub_bps", "holder_revenue_scale"))
    inside = [r for r in mi.get("solves") or [] if _within(r) is True]
    cash: list[str] = []
    if g is not None:
        ev = (g.get("evidence") or {}).get("value")
        cash.append(f"{fmt_pct(g.get('required_value'), 0)}/yr expected public-volume growth for {years:g} years (trailing 12 months: {fmt_pct(ev, 1, signed=True)})"
                    if g.get("required_value") is not None else f"more than {fmt_pct(g['search_bounds'][1], 0)}/yr public-volume growth (no root in the search range)")
    if tau is not None:
        ev = (tau.get("evidence") or {}).get("value")
        cash.append(f"a {fmt_bps(tau.get('required_value'), 0)} starting public take (today {fmt_bps(tau.get('base_value'))}, live competitive ceiling {fmt_bps(ev)})"
                    if tau.get("required_value") is not None else "a starting public take above the search bound")
    if rev is not None and rev.get("required_value") is not None:
        ev = (rev.get("evidence") or {}).get("value")
        ratio = _finite(rev["required_value"]) / ev if _finite(ev) else None
        cash.append(f"{fmt_usd(rev['required_value'])} of annualised holder revenue in year {years:g} ({fmt_num(ratio, 1)}x today's {fmt_usd(ev)})")
    cap = _finite((snap.sotp.calibration or {}).get("terminal_multiple_used"))
    cash_txt = (f" On cash flow alone (multiple held at the model's {fmt_mult(cap, 0)}), the market price requires " + ", or ".join(cash) + "; "
                + ("none of these is inside its measured evidence." if not any(_within(r) for r in (g, tau, rev) if r is not None) else
                   "at least one of these is inside its evidence (see section " + str(SEC["market"]) + ").")) if cash else ""
    if tm is not None and _within(tm) is True:
        ev = tm.get("evidence") or {}
        peers = ", ".join(f"{p['symbol']} {p['fdv_to_revenue']:,.0f}x" for p in sorted(ev.get("peers") or [], key=lambda p: p["fdv_to_revenue"]))
        dr = _solve(mi, "discount_rate")
        fdv0 = _finite((dr or {}).get("fdv_at_required_usd")) if (dr or {}).get("required_value") is not None else None
        dr_txt = ""
        if dr is not None and dr.get("required_value") is None:
            dr_txt = _discount_rate_unreachable_txt(snap, dr, target, cap)
        elif fdv0 is not None:
            dr_txt = f" A {fmt_pct(dr['required_value'], 1)} discount rate would also close it (registry range starts at {fmt_pct((dr.get('evidence') or {}).get('value'), 0)})."
        return (
            f"**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple ({fmt_mult(tm.get('required_value'), 0)} needed; "
            f"live peer FDV/revenue {peers or NA}, median {fmt_mult(ev.get('value'), 0)} over n = {len(ev.get('peers') or [])} peers).{dr_txt} "
            f"The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on "
            f"Intents cash flow at the model's {fmt_mult(cap, 0)} terminal cap.{cash_txt} Whether NEAR keeps an L1 multiple is the investment question; "
            "this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token."
        )
    if inside:
        names = "; ".join(f"{r['short_label']} {_fmt_unit(r['required_value'], r['unit'])} (evidence {_fmt_unit((r.get('evidence') or {}).get('value'), r['unit'])})" for r in inside)
        return f"**Conclusion.** Holding the rest at base, the gap closes inside measured evidence only through: {names}.{cash_txt}"
    return (
        f"**Conclusion.** No single input closes the {fmt_num(gap, 1)}x gap inside its evidence, including the terminal multiple: the market price is not "
        f"reproduced by this model on any one measured input.{cash_txt}"
    )


def _solve_rows(mi: Mapping[str, Any], *, compact: bool = False) -> list[list[str]]:
    rows = []
    for r in mi.get("solves") or []:
        ev = r.get("evidence") or {}
        w = _within(r)
        verdict = "yes" if w is True else ("no" if w is False else "n/a")
        req = _fmt_unit(r.get("required_value"), r.get("unit")) if r.get("required_value") is not None else (r.get("reason") or "no root in the search range")
        ev_txt = _fmt_unit(ev.get("value"), r.get("unit")) if ev else NA
        if ev.get("assumption"):
            ev_txt += " (ASSUMED, not measured)"
        if compact:
            rows.append([r.get("label"), _fmt_unit(r.get("base_value"), r.get("unit")), req, ev_txt, verdict])
        else:
            rows.append([r.get("label"), _fmt_unit(r.get("base_value"), r.get("unit")), req, ev_txt, str(ev.get("label") or NA), verdict])
    return rows


def _section_summary(snap: Snapshot) -> str:
    sotp = snap.sotp
    mi, tor, rv = snap.market_implied, snap.sensitivity, snap.relative_value
    fp = sotp.fdv_percentiles
    target = sotp.current_fdv_usd
    det = _finite((mi or {}).get("base_fdv_usd")) or _finite(((sotp.calibration or {}).get("deterministic_base") or {}).get("fdv_total"))
    p50 = _finite(fp.get("p50"))

    def rel(a: float | None) -> str:
        if a is None or not target:
            return NA
        return f"{target / a:,.1f}x" if target >= a else f"{a / target:,.1f}x below"

    word = "above" if (det is not None and target >= det) else "below"
    lines = [
        f"**Model value vs market value.** Market FDV is {fmt_usd(target)} (spot price x on-chain total supply at block {snap.near_rpc.block_height:,}). "
        f"The model's expected-path FDV is {fmt_usd(det)} and its {sotp.n_paths:,}-path Monte Carlo gives P10 / P50 / P90 = {fmt_usd(fp.get('p10'))} / "
        f"{fmt_usd(p50)} / {fmt_usd(fp.get('p90'))}. The market sits {word} the expected path "
        + (f"({rel(det)} it)" if word == "above" else f"(the model is {rel(det)} above it)")
        + (f" and at {fmt_mult(target / p50, 1)} the Monte Carlo P50." if p50 and target >= p50 else f" and below the Monte Carlo P50 ({fmt_usd(p50)}).")
        + f" The model capitalises NEAR Intents holder revenue, "
        f"L1 gas burn and state-lock flow over {sotp.horizon_months} months at a {fmt_pct(sotp.discount_rate, 0)} discount rate and a "
        f"{fmt_mult((sotp.calibration or {}).get('terminal_multiple_used'), 0)} terminal multiple; the question below is which input would have to change for it to "
        "reach the market price, and whether the evidence allows that.",
    ]
    if mi:
        lines.append(
            f"**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in "
            f"section {SEC['market']}).\n\n"
            + _table(["Input", "Base", "Required for market FDV", "Evidence", "Inside evidence"], _solve_rows(mi, compact=True), ["l", "r", "r", "r", "l"])
        )
        lines.append(_conclusion(snap, mi))
    else:
        lines.append("**What the market is pricing.** Not computed this run (market_implied is null; see warnings).")
    if tor and tor.get("rows"):
        top = tor["rows"][:3]
        lines.append(
            f"**What you have to believe** (section {SEC['believe']}). The three inputs that move FDV most are "
            + "; ".join(f"{r['label']} ({_fmt_unit(r['low'], r['unit'])} to {_fmt_unit(r['high'], r['unit'])}: "
                        f"{fmt_usd(min(r['fdv_low'], r['fdv_high']))}-{fmt_usd(max(r['fdv_low'], r['fdv_high']))})" for r in top)
            + f". Together they carry {fmt_pct(tor.get('top3_share'), 0)} of the swing-squared variance proxy. "
            + (f"{tor.get('n_rows_reaching_market_fdv')} of {len(tor['rows'])} single-input ranges reach the market FDV."
               if tor.get("n_rows_reaching_market_fdv") is not None else "")
        )
    if rv:
        cf = (rv.get("coverage") or {}).get("fdv_to_fees_run_rate") or {}
        band = (rv.get("implied_fdv_band") or {}).get("fees")
        st = rv.get("staking") or {}
        parts = []
        if cf.get("value") is not None and cf.get("peer_median") is not None:
            parts.append(f"NEAR trades at {fmt_mult(cf['value'], 0)} annualised fees against a peer median of {fmt_mult(cf['peer_median'], 0)} "
                         f"(rank {cf.get('rank')} of {cf.get('n')}, lowest multiple first; {cf.get('position')})")
        if band:
            parts.append(f"at peer FDV/fees multiples NEAR's fees map to {fmt_usd(band['p25_fdv_usd'])}-{fmt_usd(band['p75_fdv_usd'])} "
                         f"(cross-check, not a fair value; n = {band['n_peers']} peers)")
        if _finite(st.get("revenue_to_security_budget")) is not None:
            parts.append(f"holder revenue covers {fmt_pct(st['revenue_to_security_budget'], 0)} of the {fmt_usd(st.get('security_budget_usd_per_year'))}/yr security budget")
        if parts:
            lines.append(f"**Relative value** (section {SEC['relval']}). " + "; ".join(parts) + ".")
    f = snap.intents_forensics
    cs = f.caller_sample or {}
    bear = snap.bear_case
    lines.append(
        "**Evidence quality flags.**\n\n" + _bullets([
            _confidential_status_sentence(snap),
            f"Deposit/caller HHI {fmt_num(f.hhi_external, 0)}{_ci_txt(cs.get('hhi_external_ci90'))} over {fmt_int(cs.get('external_receipts_sampled'))} external receipts "
            f"spanning {fmt_secs(cs.get('sample_span_s'))}; a point sample, not a market-share estimate.",
            _cartel_sentence(snap),
            f"Bear case: {fmt_int(bear.triggers_breached)} of {fmt_int(bear.triggers_evaluated)} graded early-warning triggers breached"
            + (f"; not graded this run: {', '.join(bear.triggers_unevaluated)}" if bear.triggers_unevaluated else "")
            + f". Combined-worst deterministic FDV {fmt_usd(bear.combined_worst_fdv)} ({fmt_pct(bear.combined_drawdown_pct, 0, signed=True)}).",
        ])
    )
    return "\n\n".join(lines)


def _section_market(snap: Snapshot) -> str:
    mi = snap.market_implied
    if not mi:
        return "Not computed this run: `market_implied` is null (the model raised; the reason is in the warnings, section " + str(SEC["provenance"]) + ".1)."
    gap = _finite(mi.get("gap_multiple"))
    parts = [
        f"Basis: {mi.get('basis')}. Solver: {mi.get('solver')}. Market FDV {fmt_usd(mi.get('current_fdv_usd'))}; expected-path model FDV "
        f"{fmt_usd(mi.get('base_fdv_usd'))} (gap {fmt_mult(gap, 1)}); Monte Carlo P50 {fmt_usd(mi.get('base_fdv_mc_p50_usd'))} (gap "
        f"{fmt_mult(mi.get('gap_multiple_vs_mc_p50'), 1)}). Every required value is the expected-path requirement; the P50 sits lower by lognormal "
        "convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that "
        "makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).",
        "",
        _table(["Input", "Base", "Required for market FDV", "Evidence", "Evidence basis", "Inside evidence"], _solve_rows(mi), ["l", "r", "r", "r", "l", "l"]),
        _bullets([str(r.get("verdict")) for r in mi.get("solves") or []]),
        "",
        f"Headline: {mi.get('headline')}",
        "",
        f"Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the "
        f"joint requirement is smaller than any single one; section {SEC['believe']} shows which inputs carry the variance.",
    ]
    return "\n".join(parts)


def _section_believe(snap: Snapshot) -> str:
    tor = snap.sensitivity
    if not tor or not tor.get("rows"):
        return "Not computed this run: `sensitivity` is null (see warnings)."
    rows = [
        [fmt_int(r.get("rank")), r.get("label"), r.get("source"), f"{_fmt_unit(r.get('low'), r.get('unit'))} - {_fmt_unit(r.get('high'), r.get('unit'))}",
         _fmt_unit(r.get("base"), r.get("unit")), fmt_usd(r.get("fdv_low")), fmt_usd(r.get("fdv_high")), fmt_usd(r.get("swing_usd")), fmt_pct(r.get("variance_share"), 1)]
        for r in tor["rows"]
    ]
    current = _finite(tor.get("current_fdv_usd"))
    parts = [
        f"Basis: {tor.get('basis')}. Base expected-path FDV {fmt_usd(tor.get('base_fdv_usd'))}"
        + (f" against a {fmt_usd(current)} market FDV" if current is not None else "") + ". "
        f"Variance share: {tor.get('variance_proxy')}. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion "
        "where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).",
        "",
        _table(["#", "Input", "Source", "Range", "Base", "FDV at low", "FDV at high", "Swing", "Variance share"], rows,
               ["r", "l", "l", "r", "r", "r", "r", "r", "r"]),
        f"Top three inputs carry {fmt_pct(tor.get('top3_share'), 0)} of the variance proxy. "
        + (f"{tor.get('n_rows_reaching_market_fdv')} of {len(tor['rows'])} single-input ranges reach the market FDV at either end." if current is not None else ""),
        "",
        f"Headline: {tor.get('headline')}",
    ]
    excl = tor.get("excluded") or []
    if excl:
        parts.append("")
        parts.append("Excluded (move issuance and implied price, not FDV): " + "; ".join(f"{e.get('param')} ({e.get('reason')})" for e in excl) + ".")
    if tor.get("notes"):
        parts.append("Notes: " + "; ".join(str(n) for n in tor["notes"]) + ".")
    return "\n".join(parts)


def _section_relval(snap: Snapshot) -> str:
    rv = snap.relative_value
    if not rv:
        return "Not computed this run: `relative_value` is null (see warnings)."
    cov = rv.get("coverage") or {}
    cov_rows = []
    for key, c in cov.items():
        cov_rows.append([c.get("label") or key, fmt_mult(c.get("value"), 0), fmt_mult(c.get("peer_median"), 0),
                         f"{fmt_mult(c.get('peer_p25'), 0)} - {fmt_mult(c.get('peer_p75'), 0)}",
                         f"{c.get('rank')} of {c.get('n')}" if c.get("rank") is not None else NA, c.get("position") or NA])
    peer_rows = []
    for p in [*(rv.get("peers") or []), rv.get("near") or {}, *(rv.get("near_components") or [])]:
        if not p:
            continue
        peer_rows.append([f"{p.get('symbol')} ({p.get('slug')})", fmt_usd(p.get("fdv_usd")), fmt_usd(p.get("annualized_fees_usd")),
                          fmt_usd(p.get("annualized_revenue_usd")), fmt_mult(p.get("fdv_to_fees_run_rate"), 0), fmt_mult(p.get("fdv_to_revenue_run_rate"), 0),
                          fmt_mult(p.get("fdv_to_fees_1y"), 0), fmt_mult(p.get("fdv_to_revenue_1y"), 0), fmt_pct(p.get("revenue_to_fees_run_rate"), 0)])
    band = rv.get("implied_fdv_band") or {}
    band_rows = []
    for k in ("fees", "revenue"):
        b = band.get(k)
        if b:
            band_rows.append([k, fmt_usd(b.get("near_cash_flow_usd")), fmt_usd(b.get("p25_fdv_usd")), fmt_usd(b.get("median_fdv_usd")), fmt_usd(b.get("p75_fdv_usd")),
                              fmt_int(b.get("n_peers")), b.get("basis")])
    st = rv.get("staking") or {}
    stake = [
        f"Security budget: {fmt_near(st.get('annual_issuance_near'))}/yr of issuance ({fmt_pct(st.get('measured_inflation_rate'), 2)}) x "
        f"{fmt_usd(st.get('near_price_usd'), compact=False, decimals=2)} = {fmt_usd(st.get('security_budget_usd_per_year'))}/yr "
        f"({fmt_pct(st.get('security_budget_pct_of_fdv'), 2)} of FDV).",
        f"Against it: {fmt_usd(st.get('annualized_fees_usd'))}/yr of fees ({fmt_pct(st.get('fees_to_security_budget'), 0)} of the budget) and "
        f"{fmt_usd(st.get('annualized_holder_revenue_usd'))}/yr of holder revenue ({fmt_pct(st.get('revenue_to_security_budget'), 0)}); "
        f"net dilution {fmt_usd(st.get('net_dilution_usd_per_year'))}/yr.",
        f"Staked {fmt_pct(st.get('staked_supply_ratio'), 1)} of supply; nominal staking APR {fmt_pct(st.get('nominal_staking_apr_current'), 2)}. Basis: {st.get('basis')}.",
    ]
    parts = [
        f"Basis: {rv.get('basis')}.",
        "",
        f"### {SEC['relval']}.1 NEAR cash-flow coverage against the peer set",
        _table(["Metric", "NEAR", "Peer median", "Peer P25 - P75", "NEAR rank", "Position"], cov_rows, ["l", "r", "r", "r", "r", "l"]),
        _table(["Protocol", "FDV", "Fees (ann.)", "Revenue (ann.)", "FDV/fees", "FDV/revenue", "FDV/fees 1y", "FDV/revenue 1y", "Revenue/fees"], peer_rows,
               ["l", "r", "r", "r", "r", "r", "r", "r", "r"]),
        f"The model's terminal multiple is {fmt_mult(rv.get('model_terminal_multiple'), 0)}; {fmt_int(rv.get('n_peers_at_or_below_model_multiple'))} of "
        f"{fmt_int(rv.get('n_peers'))} peers trade at or below it on FDV/revenue.",
        "",
        f"### {SEC['relval']}.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)",
        _table(["Cash flow", "NEAR (ann.)", "at peer P25", "at peer median", "at peer P75", "Peers", "Basis"], band_rows, ["l", "r", "r", "r", "r", "r", "l"])
        if band_rows else "No peer band (peer multiples or NEAR cash flow unavailable).",
        f"{band.get('label') or ''}; market FDV {fmt_usd(band.get('current_fdv_usd'))}.",
        "",
        f"### {SEC['relval']}.3 Staking and security budget",
        _bullets(stake),
        "",
        f"### {SEC['relval']}.4 Findings",
        _bullets(rv.get("findings") or ["none"]),
        "",
        f"Caveat: {rv.get('caveat')}",
    ]
    return "\n".join(parts)


_BULL_STATUS = {"on_track": "On track", "behind": "Behind", "against": "Against", "not_measured": "Not measured"}


def _bull_value(x: Any, unit: str) -> str:
    if unit == "ratio_yoy":
        return f"{fmt_pct(x, 0)} a year"
    if unit == "ratio":
        return fmt_pct(x, 1)
    if unit == "usd_per_year":
        return f"{fmt_usd(x)} a year"
    if unit == "usd_per_day":
        return f"{fmt_usd(x)} a day"
    if unit == "usd":
        return fmt_usd(x)
    if unit == "bps":
        return fmt_bps(x, 2, signed=True)
    if unit == "x":
        return fmt_mult(x, 0)
    if unit == "hhi":
        return fmt_int(x)
    return fmt_num(x)


def _section_bull(snap: Snapshot) -> str:
    bc = getattr(snap, "bull_case", None) or {}
    if not isinstance(bc, dict) or not bc.get("conditions"):
        return "_The bull-case scorecard was not computed this run (see warnings)._"
    rows = []
    for c in bc["conditions"]:
        tr = c.get("trend") or {}
        trend = f"{fmt_pct(tr.get('change'), 0, signed=True)} ({tr.get('label')})" if tr else "n/a"
        req = ("> 0" if c.get("key") in ("pricing_power", "confidential_growth") else
               "<= " + _bull_value(c.get("required"), c.get("unit", "")) if c.get("key") == "solver_competition" else
               _bull_value(c.get("required"), c.get("unit", "")))
        rows.append([c.get("statement"), req, _bull_value(c.get("live"), c.get("unit", "")), trend, f"**{_BULL_STATUS.get(c.get('status'), c.get('status'))}**"])
    return "\n\n".join([
        bc.get("headline", ""),
        _table(["Condition", "Required", "Live", "Trend", "Status"], rows, ["l", "r", "r", "l", "l"]),
        ("How to read it: each requirement is what the market price needs if that condition alone carries the case (from the "
         f"reverse valuation in section {SEC['market']}), or the threshold the bear case watches (section {SEC['bear']}). "
         "An investor holding NEAR long-term is betting that the conditions marked Behind close; the ones marked Against "
         "are where the case is currently losing. Re-run `make reproduce` to re-grade every row against live data."),
    ])


# ============================================================================ entry point
def render_memo(snapshot: Snapshot | Mapping[str, Any], manifest: Manifest | Mapping[str, Any] | None) -> str:
    """Render the Investment Committee memo (Markdown) from a snapshot and its manifest."""
    snap = snapshot if isinstance(snapshot, Snapshot) else Snapshot.model_validate(snapshot)
    man = manifest if (manifest is None or isinstance(manifest, Manifest)) else Manifest.model_validate(manifest)
    t = snap.near_rpc
    title = (
        f"# Valuo IC Memo: NEAR at block {t.block_height:,}\n\n"
        f"*NEAR Intents clearinghouse + NEAR L1. Generated {snap.generated_at_utc} UTC from live mainnet RPC and key-free public APIs; "
        "every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. "
        f"Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section {SEC['assumptions']}.*"
    )
    sections = [
        title,
        _header(snap, man),
        f"## {SEC['bull']}. The long-term case, made falsifiable", _section_bull(snap),
        f"## {SEC['summary']}. Executive summary", _section_summary(snap),
        f"## {SEC['market']}. What the market is pricing (reverse valuation)", _section_market(snap),
        f"## {SEC['believe']}. What you have to believe (one-at-a-time sensitivity)", _section_believe(snap),
        f"## {SEC['relval']}. Relative value: peer cash-flow multiples and the security budget", _section_relval(snap),
        f"## {SEC['model']}. Model valuation detail", _section_verdict(snap),
        f"## {SEC['micro']}. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)", _section_microstructure(snap),
        f"## {SEC['conc']}. Concentration and agents on intents.near (NearBlocks receipts)", _section_concentration(snap),
        f"## {SEC['supply']}. Supply physics", _section_supply(snap),
        f"## {SEC['sotp']}. Sum-of-the-parts valuation and peer comparables", _section_sotp(snap),
        f"## {SEC['bear']}. Bear case and early-warning triggers", _section_bear(snap),
        f"## {SEC['score']}. Evidence scorecard", _section_scorecard(snap),
        f"## {SEC['assumptions']}. Assumptions register", _section_assumptions(snap),
        f"## {SEC['reproduce']}. Reproduction", _section_reproduce(snap),
        f"## {SEC['provenance']}. Data provenance", _section_provenance(snap, man),
    ]
    return "\n\n".join(sections).rstrip() + "\n"


# ============================================================================ README findings block
def render_readme_findings(snapshot: Snapshot | Mapping[str, Any], manifest: Manifest | Mapping[str, Any] | None = None) -> str:
    """The README's findings section, generated from the snapshot so the judge-facing page never carries stale numbers.

    Returns Markdown delimited by ``README_FINDINGS_START`` / ``README_FINDINGS_END``; ``reproduce.py`` splices it
    between the same markers in ``README.md`` on every canonical run. Every figure is read from the snapshot (or
    the manifest SHA-256); nulls print as ``n/a`` with the reason.
    """
    snap = snapshot if isinstance(snapshot, Snapshot) else Snapshot.model_validate(snapshot)
    man = manifest if (manifest is None or isinstance(manifest, Manifest)) else Manifest.model_validate(manifest)
    t, f, sp, sotp, bear, bench = snap.near_rpc, snap.intents_forensics, snap.supply_physics, snap.sotp, snap.bear_case, snap.execution_bench
    ei = t.epoch_issuance
    fees, vol, cal = f.fees or {}, f.volume or {}, sotp.calibration or {}
    sc = f.solver_concentration or {}
    intents = next((s for s in t.tracked_sinks if s.account_id == "intents.near"), None)
    sha = man.snapshot_sha256 if man is not None else None

    def _row(label: str, value: str, basis: str) -> list[str]:
        return [label, value, basis]

    mi, tor, rv = snap.market_implied or {}, snap.sensitivity or {}, snap.relative_value or {}
    rows: list[list[str]] = [
        _row("NEAR block / total supply", f"{t.block_height:,} / {fmt_near(t.total_supply_near)}", f"RPC `block` header at {t.timestamp_utc}"),
    ]
    det_fdv = _finite(mi.get("base_fdv_usd")) or _finite((cal.get("deterministic_base") or {}).get("fdv_total"))
    rows.append(_row(
        "Market FDV vs model (expected path / MC P50)",
        f"{fmt_usd(sotp.current_fdv_usd)} vs {fmt_usd(det_fdv)} / {fmt_usd(sotp.fdv_percentiles.get('p50'))} "
        f"(market = {fmt_mult(sotp.current_fdv_usd / det_fdv if det_fdv else None, 1)} the expected path)",
        f"model capitalises Intents holder revenue + gas burn + state lock, {sotp.horizon_months} m, {fmt_pct(sotp.discount_rate, 0)} discount, "
        f"{fmt_mult(cal.get('terminal_multiple_used'), 0)} terminal cap",
    ))
    if mi:
        def _req(param: str) -> str:
            r = _solve(mi, param)
            if r is None:
                return NA
            ev = (r.get("evidence") or {}).get("value")
            req = _fmt_unit(r.get("required_value"), r.get("unit")) if r.get("required_value") is not None else "unreachable"
            return f"{req} (evidence {_fmt_unit(ev, r.get('unit'))}{'; inside' if _within(r) is True else '; outside' if _within(r) is False else ''})"
        rows.append(_row(
            "What the market FDV requires (one input at a time)",
            f"expected volume growth {_req('public_volume_growth_yoy')}; starting public take {_req('tau_pub_bps')}; terminal multiple {_req('terminal_multiple')}",
            "brentq solve on the expected path, others at base; evidence = trailing-12m Intents volume growth, live competitive fee ceiling, "
            "peer median FDV/revenue (`market_implied`)",
        ))
    else:
        rows.append(_row("What the market FDV requires", "n/a (market_implied null this run)", "see warnings"))
    cf = (rv.get("coverage") or {}).get("fdv_to_fees_run_rate") or {}
    if cf.get("value") is not None:
        band = (rv.get("implied_fdv_band") or {}).get("fees") or {}
        rows.append(_row(
            "Relative value: FDV / annualised fees",
            f"NEAR {fmt_mult(cf.get('value'), 0)} vs peer median {fmt_mult(cf.get('peer_median'), 0)}; rank {cf.get('rank')} of {cf.get('n')} (lowest first, {cf.get('position')})",
            (f"peer-multiple band {fmt_usd(band.get('p25_fdv_usd'))}-{fmt_usd(band.get('p75_fdv_usd'))} is a cross-check, not a fair value; " if band else "")
            + f"n = {rv.get('n_peers')} peers (`relative_value`)",
        ))
    if tor.get("rows"):
        top = tor["rows"][:3]
        rows.append(_row(
            "Top FDV drivers (tornado)",
            "; ".join(f"{r['param']} {fmt_usd(min(r['fdv_low'], r['fdv_high']))}-{fmt_usd(max(r['fdv_low'], r['fdv_high']))}" for r in top)
            + f" ({fmt_pct(tor.get('top3_share'), 0)} of swing-squared variance)",
            f"{len(tor['rows'])} inputs at registry / measured ranges; {tor.get('n_rows_reaching_market_fdv')} reach the market FDV (`sensitivity`)",
        ))
    rows += [
        _row(
            "Protocol inflation cap / measured issuance",
            f"{fmt_pct(t.max_inflation_rate, 2)} cap; measured {fmt_near(ei.implied_annual_issuance_near)}/yr = {fmt_pct(ei.implied_annual_inflation_rate, 3)} "
            f"({fmt_near(sp.current_daily_issuance_near)}/day)" if ei.implied_annual_issuance_near is not None
            else f"{fmt_pct(t.max_inflation_rate, 2)} cap; measured issuance n/a (epoch boundary unavailable), nominal {fmt_near(ei.nominal_annual_issuance_near)}/yr",
            "`EXPERIMENTAL_protocol_config`; total_supply jumps at epoch starts",
        ),
        _row("Validators / staked ratio", f"{t.active_validator_count} / {fmt_pct(t.staked_supply_ratio, 2)} ({fmt_near(t.total_staked_near)})", "RPC `validators`"),
        _row(
            "intents.near NEP state lock",
            (f"{fmt_int(intents.storage_bytes)} bytes = {fmt_near(intents.storage_locked_near)} locked; growth "
             f"{fmt_near(intents.growth_locked_near_per_day, 1)}/day over {fmt_num(intents.growth_window_days, 1)} d") if intents is not None
            else "n/a (view_account unavailable this run)",
            f"`view_account` + storage_amount_per_byte ({fmt_num(t.storage_near_per_kb, 2)} NEAR/KB); archival lookback for growth",
        ),
        _row(
            "NEAR Intents 30d volume (public / confidential)",
            f"{fmt_usd(vol.get('30d'))} ({fmt_usd(vol.get('public30d'))} / {fmt_usd(vol.get('confidential30d'))}; confidential share {fmt_pct(vol.get('confidential_share_30d'), 1)})",
            ("nearstats `intents.totalsBreakdown`; DefiLlama dexs chart agrees day-for-day" if (vol.get("confidential_share_status") in (None, "measured"))
             else f"confidential share status `{vol.get('confidential_share_status')}`: NOT MEASURED; {vol.get('confidential_share_source') or 'no split'}"),
        ),
        _row(
            "Gross take / net take / capture ratio",
            f"{fmt_bps(fees.get('gross_take_bps'))} / {fmt_bps(fees.get('net_take_bps'))} / {fmt_pct(fees.get('capture_ratio'), 1)}",
            f"ONE canonical window: {fees.get('take_rate_window') or NA}",
        ),
        _row(
            "Daily sinks vs issuance",
            f"buyback {fmt_near(sp.current_daily_sinks_near.get('buyback'), 0)} + gas burn {fmt_near(sp.current_daily_sinks_near.get('gas_burn'), 0)} + "
            f"state lock {fmt_near(sp.current_daily_sinks_near.get('state_lock'), 0)} = {fmt_pct(sp.sink_coverage_ratio, 1)} of {fmt_near(sp.current_daily_issuance_near)}/day",
            "supply_physics; buyback = V x tau x alpha / P",
        ),
        _row(
            "Breakeven daily volume V* (status quo / SVRN glidepath)",
            f"{fmt_usd(sp.breakeven_daily_volume_usd.get('status_quo'))} / {fmt_usd(sp.breakeven_daily_volume_usd.get('svrn_glidepath'))} per day "
            f"(today {fmt_usd(sp.inputs['daily_volume_usd'].value if 'daily_volume_usd' in sp.inputs else None)}/day)",
            "V* = (I - G - L) x P / (tau x alpha) at the regime's terminal rate",
        ),
    ]
    if bench is not None:
        hb, hn = bench.headroom_by_archetype_bps or {}, bench.headroom_n_by_archetype or {}
        label = {c.archetype: c.label for c in bench.corridors}
        cells = "; ".join(
            f"{label.get(a, a)}: {fmt_bps(hb.get(a), signed=True)} median over {fmt_int(hn.get(a))} cells" for a in ("cross_vm", "native_btc", "evm_l2") if a in hb
        )
        rows.append(_row(
            "Live quote race, 1Click headroom vs best competitor (destination units)",
            cells or "no comparable cell",
            f"1Click vs Relay / LI.FI / Across at {', '.join(_clip(c) for c in bench.clips_usd)}; competitor ceiling {fmt_bps(bench.competitive_fee_ceiling_bps)} on cross-VM; "
            f"{bench.ran_at_utc}",
        ))
    else:
        rows.append(_row("Live quote race", "not run in this snapshot (`--skip-bench`)", "execution_bench null"))
    rows += [
        _row(
            "Deposit/caller HHI / solver HHI on intents.near",
            f"{fmt_num(f.hhi_external, 0)}{_ci_txt((f.caller_sample or {}).get('hhi_external_ci90'))} / {fmt_num(sc.get('hhi_solver'), 0)}"
            f"{_ci_txt(sc.get('hhi_solver_ci90'))} ({fmt_int(sc.get('n_fills_attributed'))} fill participations over {fmt_secs(sc.get('sample_span_s'))}); "
            f"cartel trigger {_cartel_status_word(snap)}",
            f"NearBlocks receipts: {fmt_int(f.receipts_sampled)} over {f.pages_fetched} pages; AI-agent (name-pattern) share {fmt_pct(f.ai_agent_share, 1)}",
        ),
        _row(
            "SOTP FDV P10 / P50 / P90 (36 m, discounted)",
            f"{fmt_usd(sotp.fdv_percentiles.get('p10'))} / {fmt_usd(sotp.fdv_percentiles.get('p50'))} / {fmt_usd(sotp.fdv_percentiles.get('p90'))} vs current FDV "
            f"{fmt_usd(sotp.current_fdv_usd)} ({fmt_pct(sotp.upside_p50_pct / 100 if sotp.upside_p50_pct is not None else None, 1, signed=True)} at P50)",
            f"{sotp.n_paths:,} paths, seed {sotp.seed}; terminal multiple {fmt_mult(cal.get('terminal_multiple_used'))} ({cal.get('terminal_multiple_source') or NA}); "
            f"deterministic (expected-path) FDV {fmt_usd((cal.get('deterministic_base') or {}).get('fdv_total'))}",
        ),
        _row(
            "Bear case, combined worst (deterministic, median inputs)",
            f"{fmt_usd(bear.combined_worst_fdv)} ({fmt_pct(bear.combined_drawdown_pct, 0, signed=True)}); triggers breached "
            f"{fmt_int(bear.triggers_breached)} of {fmt_int(bear.triggers_evaluated)} measured"
            + (f" ({', '.join(bear.triggers_unevaluated)} not graded: inconclusive or unmeasured)" if bear.triggers_unevaluated else ""),
            "four falsification scenarios through deterministic_sotp; live early-warning metrics",
        ),
    ]
    status_counts: dict[str, int] = {}
    for c in snap.evidence_scorecard:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1
    rows.append(_row("Evidence scorecard", ", ".join(f"{k} {v}" for k, v in sorted(status_counts.items())) or NA, f"{len(snap.evidence_scorecard)} graded claims in `IC_MEMO.md` section {SEC['score']}"))
    header = (
        f"## Findings as of the committed snapshot (NEAR block {t.block_height:,}, {t.timestamp_utc} UTC)\n\n"
        f"Generated by `python -m valuo.reproduce` from `artifacts/latest_snapshot.json` (SHA-256 `{sha or NA}`, {snap.generated_at_utc} UTC, "
        f"valuo {snap.valuo_version}). Every figure is a live fetch, an arithmetic derivation or a labeled assumption; `n/a` means the source "
        "was unavailable in this run and nothing was substituted. `make reproduce` regenerates this block.\n"
    )
    table = _table(["Finding", "Value", "Basis"], rows)
    warn = f"\n{len(snap.warnings)} methodology warning(s) recorded in this run; see `IC_MEMO.md` section {SEC['provenance']}.1.\n" if snap.warnings else ""
    return f"{README_FINDINGS_START}\n{header}\n{table}{warn}{README_FINDINGS_END}"
