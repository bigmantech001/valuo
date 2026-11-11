"""Chain Signatures (MPC signer ``v1.signer``) usage audit, key-free.

``v1.signer`` is the NEAR mainnet MPC coordinator: a caller submits ``sign(request)``, the MPC nodes post the
signature with ``respond``, and the contract resolves the caller's promise in
``return_signature_and_clean_state_on_success``. Every sign request is one ``sign`` receipt executed at
``v1.signer``, so counting those receipts counts requests.

What is measured, and how:

1. **Cumulative receipts**: NearBlocks ``/account/v1.signer/txns/count`` (all receipts at the contract, every
   method, as indexed by NearBlocks).
2. **Sign-request rate and trend (sampled)**: NearBlocks cannot give exact daily sign counts for this account
   key-free: the ``method=sign`` list query times out (HTTP 520 after ~50 s) and the count endpoint rejects date
   filters (HTTP 500). So the rate is estimated from sample windows. Each window is one page of the newest
   ``PER_PAGE`` receipts before an anchor; per window, receipt rate = (n - 1) / span and sign rate = receipt rate
   x share of receipts whose action is ``sign``. Two kinds of anchor:

   - ``level``: ``LEVEL_ANCHORS`` block heights in the last 7 days, 42 h apart (``before_block``). 42 h is not a
     multiple of 24 h, so the four windows fall 6 h apart in time of day. Deep ``before_block`` queries time out
     on NearBlocks (observed at ~9 days back), so this kind is used only for the recent stratum.
   - ``midnight``: ``before_date=YYYY-MM-DD`` every ``MIDNIGHT_STEP_DAYS`` days back to 28 days (the newest
     receipts before 00:00 UTC of that date). Same time of day on every date, so the series compares like with
     like; the trend is an OLS fit of ln(sign rate) on time over this series only.

   Trailing 7d rate = mean of the windows dated in the last 7 days. Trailing 30d rate = the 7d mean and the
   days-7-30 mean weighted by the days they cover (7/30, 23/30); the older stratum is sampled at 00:00 UTC only.
   A window covers a few minutes, so these are sample estimates with standard errors, not exact daily counts.
3. **What a request pays**: the deposit attached to each sampled ``sign`` action (yoctoNEAR, as NearBlocks reports
   it) and the gas burnt by every ``v1.signer`` receipt in the windows (``receipt_outcome.tokens_burnt``), per sign
   request. ``burnt_gas_reward`` from the live ``EXPERIMENTAL_protocol_config`` is the share of that gas paid to
   the contract; the rest is burnt.
4. **Storage lock**: not fetched here. ``near_rpc`` already reads ``v1.signer`` ``view_account``;
   ``attach_context`` copies that row and converts NEAR to USD at the snapshot NEAR price.

Failures never abort the run: each missing piece is a warning and a null with a reason.
"""
from __future__ import annotations

import asyncio
import os
import math
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from valuo import config
from valuo.provenance import ProvenanceLedger, fetch_json, near_rpc_call

__all__ = [
    "CONTRACT", "PER_PAGE", "WINDOW_DAYS", "RECENT_DAYS", "LEVEL_ANCHORS", "LEVEL_SPACING_H", "MIDNIGHT_STEP_DAYS",
    "sample_plan", "summarize_window", "aggregate_windows", "log_linear_trend", "caller_shares",
    "collect_chain_signatures", "attach_context",
]

CONTRACT = "v1.signer"
YOCTO = 10 ** 24
WINDOW_DAYS = 30
RECENT_DAYS = 7
LEVEL_ANCHORS = 4
LEVEL_SPACING_H = 42.0
MIDNIGHT_STEP_DAYS = 4
MIDNIGHT_MAX_DAYS = 28
PER_PAGE = 100
# NearBlocks' unauthenticated tier answers HTTP 429 at about 6 calls a minute (observed); 10.5 s spacing stays
# under it. With NEARBLOCKS_API_KEY set the spacing drops to the shared NearBlocks page delay.
UNAUTH_DELAY_S = 10.5
# Wall-time cap on the sample loop so 429 back-offs cannot stretch `make reproduce` indefinitely; windows not
# reached are reported as failed and the rates use what returned. The unattended daily job (ops/vps) raises it
# with VALUO_CHAINSIG_BUDGET_S, since nobody waits on it and a full 12-window sample is worth the minutes.
BUDGET_S = float(os.environ.get("VALUO_CHAINSIG_BUDGET_S") or 240.0)
# Windows that failed in the first pass (429 ladder exhausted) are retried once after this cool-down, while the
# budget lasts: NearBlocks' per-minute quota refills, so a second pass recovers most of them.
RETRY_COOLDOWN_S = 45.0
CADENCE_PROBE_BLOCKS = 100_000
SIGN_METHOD = "sign"
RESPOND_METHOD = "respond"
MIN_WINDOWS_FOR_TREND = 5
# 429s still arrive at that spacing once the quota is partly spent (observed), so back off 8 / 16 / 32 s before giving up.
_RETRY_KW: dict[str, Any] = {"retries": 3, "backoff": 8.0, "retry_after_cap_s": 30.0, "transport_retries": 1}
BRIDGE_SUFFIX = ".bridge.near"


def interleaved(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Request order for ``plan``: alternate the 7-day ``level`` anchors with the ``midnight`` series, oldest
    midnight first after today's. A budget cut then still leaves windows in both strata (last 7 days and days
    7-30) instead of only the first half of the list, so the 30-day rate stays measurable."""
    level = [p for p in plan if p["kind"] == "level"]
    mid = [p for p in plan if p["kind"] == "midnight"]
    mid = mid[:1] + mid[:0:-1] if mid else mid  # today, then 28, 24, ... 4 days back
    out: list[dict[str, Any]] = []
    for i in range(max(len(level), len(mid))):
        out += [x[i] for x in (mid, level) if i < len(x)]
    return out


def sample_plan(head_ns: int, *, level_anchors: int = LEVEL_ANCHORS, level_spacing_h: float = LEVEL_SPACING_H,
                midnight_step_days: int = MIDNIGHT_STEP_DAYS, midnight_max_days: int = MIDNIGHT_MAX_DAYS) -> list[dict[str, Any]]:
    """Anchors to sample: ``level`` (hours before head, placed by block height) then ``midnight`` (UTC dates)."""
    plan: list[dict[str, Any]] = [
        {"kind": "level", "offset_h": level_spacing_h / 2 + level_spacing_h * k} for k in range(level_anchors)
    ]
    today = datetime.fromtimestamp(head_ns / 1e9, tz=timezone.utc).date()
    for d in range(0, midnight_max_days + 1, midnight_step_days):
        plan.append({"kind": "midnight", "before_date": (today - timedelta(days=d)).isoformat()})
    return plan


def _int(x: Any) -> int | None:
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _utc(ns: Any) -> str | None:
    v = _int(ns)
    if v is None:
        return None
    return datetime.fromtimestamp(v / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _methods(row: dict[str, Any]) -> list[str]:
    acts = row.get("actions")
    if not isinstance(acts, list):
        return []
    return [a.get("method") or a.get("action") or "?" for a in acts if isinstance(a, dict)]


def summarize_window(rows: Any) -> dict[str, Any] | None:
    """One NearBlocks ``/account/v1.signer/txns`` page -> counts, span and rates. None if under 2 receipts."""
    if not isinstance(rows, list):
        return None
    seen: set[Any] = set()
    uniq: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        rid = r.get("receipt_id") or r.get("id")
        if rid in seen:
            continue
        seen.add(rid)
        uniq.append(r)
    ts = [t for t in (_int(r.get("block_timestamp")) for r in uniq) if t is not None]
    if len(ts) < 2:
        return None
    span_s = (max(ts) - min(ts)) / 1e9
    n = len(uniq)
    method_mix: Counter[str] = Counter()
    callers: Counter[str] = Counter()
    deposits: list[int] = []
    n_sign = n_sign_ok = n_respond = 0
    gas_yocto = sign_gas_yocto = 0
    for r in uniq:
        methods = _methods(r)
        for m in methods:
            method_mix[m] += 1
        if not methods:
            method_mix["(no actions)"] += 1
        outcome = r.get("receipt_outcome") if isinstance(r.get("receipt_outcome"), dict) else {}
        burnt = _int(outcome.get("tokens_burnt")) or 0
        gas_yocto += burnt
        if SIGN_METHOD in methods:
            n_sign += 1
            sign_gas_yocto += burnt
            if outcome.get("status") is True:
                n_sign_ok += 1
            callers[str(r.get("predecessor_account_id") or "?")] += 1
            for a in r.get("actions") or []:
                if isinstance(a, dict) and a.get("method") == SIGN_METHOD:
                    d = _int(a.get("deposit"))
                    if d is not None:
                        deposits.append(d)
        if RESPOND_METHOD in methods:
            n_respond += 1
    per_s = (n - 1) / span_s if span_s > 0 else None
    share = n_sign / n
    return {
        "n_receipts": n, "n_sign": n_sign, "n_sign_success": n_sign_ok, "n_respond": n_respond,
        "newest_ns": max(ts), "oldest_ns": min(ts), "newest_time_utc": _utc(max(ts)), "oldest_time_utc": _utc(min(ts)),
        "span_s": span_s, "sign_share": share,
        "receipts_per_day": per_s * 86400 if per_s is not None else None,
        "sign_per_day": per_s * share * 86400 if per_s is not None else None,
        "gas_burnt_near": gas_yocto / YOCTO, "sign_gas_burnt_near": sign_gas_yocto / YOCTO,
        "gas_near_per_day": per_s * (gas_yocto / YOCTO) / n * 86400 if per_s is not None else None,
        "deposits_yocto": deposits, "callers": dict(callers), "method_mix": dict(method_mix),
    }


def _mean_se(xs: list[float]) -> tuple[float | None, float | None]:
    xs = [x for x in xs if isinstance(x, (int, float)) and math.isfinite(x)]
    if not xs:
        return None, None
    m = sum(xs) / len(xs)
    if len(xs) < 2:
        return m, None
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return m, math.sqrt(var / len(xs))


def log_linear_trend(points: list[tuple[float, float]]) -> dict[str, Any] | None:
    """OLS of ln(rate) on time in days (older = more negative). Slope/day, 30d growth, t-stat, 90% CI."""
    pts = [(t, math.log(r)) for t, r in points if isinstance(r, (int, float)) and r > 0 and math.isfinite(r)]
    n = len(pts)
    if n < 3:
        return None
    mt = sum(t for t, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((t - mt) ** 2 for t, _ in pts)
    if sxx <= 0:
        return None
    slope = sum((t - mt) * (y - my) for t, y in pts) / sxx
    resid = [y - (my + slope * (t - mt)) for t, y in pts]
    se = math.sqrt(sum(e * e for e in resid) / (n - 2) / sxx)
    t_stat = slope / se if se > 0 else None
    return {
        "n": n, "slope_ln_per_day": slope, "slope_se": se, "t_stat": t_stat,
        "growth_30d": math.exp(slope * 30) - 1,
        "growth_30d_ci90": [math.exp((slope - 1.645 * se) * 30) - 1, math.exp((slope + 1.645 * se) * 30) - 1] if se > 0 else None,
    }


def caller_shares(callers: Counter[str] | dict[str, int], top: int = 8) -> dict[str, Any]:
    """Sampled sign receipts per predecessor account -> shares, HHI (0-10,000) and the share from ``*.bridge.near``.

    ``bridge_share`` classifies by account name only (accounts under ``bridge.near``: the Omni bridge and its BTC /
    Zcash connectors); it is a lower bound on bridge-driven requests, not an audit of each caller.
    """
    total = sum(callers.values())
    if total <= 0:
        return {"n_sign_sampled": 0, "n_callers": 0, "hhi": None, "bridge_share": None, "top": []}
    ranked = sorted(callers.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "n_sign_sampled": total, "n_callers": len(ranked),
        "hhi": sum((c / total * 100) ** 2 for _, c in ranked),
        "bridge_share": sum(c for a, c in ranked if a.endswith(BRIDGE_SUFFIX)) / total,
        "top": [{"account_id": a, "sign_receipts": c, "share": c / total} for a, c in ranked[:top]],
    }


def _median(xs: list[int]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def _growth_status(trend: dict[str, Any] | None) -> str:
    if trend is None:
        return "not_measured"
    if trend.get("t_stat") is None:  # zero residual: the sign of the slope is exact
        slope = trend.get("slope_ln_per_day") or 0.0
        return "growing" if slope > 1e-12 else "declining" if slope < -1e-12 else "inconclusive"
    if trend["t_stat"] >= 2 and trend["slope_ln_per_day"] > 0:
        return "growing"
    if trend["t_stat"] <= -2 and trend["slope_ln_per_day"] < 0:
        return "declining"
    return "inconclusive"


def aggregate_windows(windows: list[dict[str, Any]], *, head_ns: int) -> dict[str, Any]:
    """Window summaries (with ``kind`` and ``newest_ns``) -> trailing 7d / 30d rates, trend, callers, deposits, gas."""
    ok = [w for w in windows if w.get("sign_per_day") is not None and w.get("newest_ns") is not None]
    for w in ok:
        w["days_before_head"] = (head_ns - w["newest_ns"]) / 1e9 / 86400
    recent = [w for w in ok if w["days_before_head"] < RECENT_DAYS]
    older = [w for w in ok if RECENT_DAYS <= w["days_before_head"] < WINDOW_DAYS]
    m7, se7 = _mean_se([w["sign_per_day"] for w in recent])
    m_old, se_old = _mean_se([w["sign_per_day"] for w in older])
    w7, w_old = RECENT_DAYS / WINDOW_DAYS, (WINDOW_DAYS - RECENT_DAYS) / WINDOW_DAYS
    m30 = w7 * m7 + w_old * m_old if m7 is not None and m_old is not None else None
    se30 = math.sqrt((w7 * se7) ** 2 + (w_old * se_old) ** 2) if m30 is not None and se7 is not None and se_old is not None else None
    g7, _ = _mean_se([w["gas_near_per_day"] for w in recent if w.get("gas_near_per_day") is not None])
    g_old, _ = _mean_se([w["gas_near_per_day"] for w in older if w.get("gas_near_per_day") is not None])
    g30 = w7 * g7 + w_old * g_old if g7 is not None and g_old is not None else None

    series = sorted((w for w in ok if w.get("kind") == "midnight"), key=lambda w: w["newest_ns"])
    trend = log_linear_trend([(-w["days_before_head"], w["sign_per_day"]) for w in series]) if len(series) >= MIN_WINDOWS_FOR_TREND else None

    callers: Counter[str] = Counter()
    deposits: list[int] = []
    n_sign = n_ok = n_rec = 0
    gas_all = 0.0
    for w in ok:
        callers.update(w.get("callers") or {})
        deposits += list(w.get("deposits_yocto") or [])
        n_sign += w["n_sign"]
        n_ok += w["n_sign_success"]
        n_rec += w["n_receipts"]
        gas_all += w["gas_burnt_near"]
    return {
        "windows_ok": len(ok), "receipts_sampled": n_rec, "sign_receipts_sampled": n_sign,
        "sign_success_share": n_ok / n_sign if n_sign else None,
        "sampled_seconds": sum(w["span_s"] for w in ok),
        "sign_per_day_7d": m7, "sign_per_day_7d_se": se7, "windows_7d": len(recent),
        "sign_per_day_7_30d": m_old, "sign_per_day_7_30d_se": se_old, "windows_7_30d": len(older),
        "sign_per_day_30d": m30, "sign_per_day_30d_se": se30, "windows_30d": len(recent) + len(older),
        "trend": trend, "trend_windows": len(series), "growth_status": _growth_status(trend),
        "callers": caller_shares(callers),
        "deposit_yocto_median": _median(deposits), "deposit_yocto_max": max(deposits) if deposits else None,
        "deposit_near_mean": (sum(deposits) / len(deposits) / YOCTO) if deposits else None,
        "gas_near_per_sign": gas_all / n_sign if n_sign else None,
        "gas_near_per_day_30d": g30,
    }


async def _block(client: httpx.AsyncClient, ledger: ProvenanceLedger, height: int | None, name: str) -> tuple[int | None, int | None]:
    params: dict[str, Any] = {"finality": "final"} if height is None else {"block_id": int(height)}
    res, _rec = await near_rpc_call(client, ledger, "block", params, name, retries=3)
    h = (res or {}).get("header") or {}
    return _int(h.get("height")), _int(h.get("timestamp_nanosec") or h.get("timestamp"))


async def collect_chain_signatures(
    client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str], *, delay_s: float | None = None,
    plan_kwargs: dict[str, Any] | None = None, budget_s: float = BUDGET_S,
) -> dict[str, Any]:
    """Live audit of ``v1.signer`` (see module docstring). Never raises; failures are warnings plus nulls."""
    if delay_s is None:
        delay_s = config.NEARBLOCKS_PAGE_DELAY_S if config.NEARBLOCKS_API_KEY else UNAUTH_DELAY_S
    out: dict[str, Any] = {
        "contract": CONTRACT, "status": "unavailable",
        "method": (f"NearBlocks pages of the newest {PER_PAGE} receipts before {LEVEL_ANCHORS} block heights in the last {RECENT_DAYS} days "
                   f"({LEVEL_SPACING_H:g} h apart) and before 00:00 UTC every {MIDNIGHT_STEP_DAYS} days back to {MIDNIGHT_MAX_DAYS} days; "
                   "sign rate per window = (n - 1) / span x sign share; 30d rate = day-weighted 7d and 7-30d means; "
                   "trend = OLS of ln(sign rate) on time over the 00:00 UTC series. Sampled estimate, not an exact daily count."),
        "cumulative_receipts": None, "cumulative_receipts_note": None,
        "head_block": None, "head_time_utc": None, "seconds_per_block": None, "burnt_gas_reward": None,
        "windows": [], "not_measured": [],
    }
    out.update(aggregate_windows([], head_ns=0))  # every rate key present (null) even when the run stops early
    try:
        return await _collect(client, ledger, warnings, out, max(0.0, delay_s), plan_kwargs or {}, budget_s)
    except Exception as exc:  # noqa: BLE001 - evidence, not a prerequisite
        warnings.append(f"chain_signatures: collector failed ({type(exc).__name__}: {exc}); fields null")
        out["status"] = "unavailable"
        return out


async def _page(client: httpx.AsyncClient, ledger: ProvenanceLedger, params: dict[str, Any], name: str) -> tuple[Any, Any]:
    return await fetch_json(
        client, ledger, source="nearblocks", name=name, method="GET", url=f"{config.NEARBLOCKS_API_BASE}/account/{CONTRACT}/txns",
        params={"per_page": PER_PAGE, **params}, headers=config.nearblocks_headers(), **_RETRY_KW,
    )


async def _collect(client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str], out: dict[str, Any], delay: float,
                   plan_kwargs: dict[str, Any], budget_s: float = BUDGET_S) -> dict[str, Any]:
    head_h, head_ns = await _block(client, ledger, None, "chain_signatures:block:final")
    probe_h, probe_ns = (None, None)
    if head_h is not None:
        probe_h, probe_ns = await _block(client, ledger, head_h - CADENCE_PROBE_BLOCKS, "chain_signatures:block:cadence_probe")
    proto, _ = await near_rpc_call(client, ledger, "EXPERIMENTAL_protocol_config", {"finality": "final"}, "chain_signatures:protocol_config", retries=2)
    reward = (((proto or {}).get("runtime_config") or {}).get("transaction_costs") or {}).get("burnt_gas_reward")
    if isinstance(reward, list) and len(reward) == 2 and all(isinstance(x, int) for x in reward) and reward[1]:
        out["burnt_gas_reward"] = reward[0] / reward[1]
    else:
        out["not_measured"].append("burnt_gas_reward: EXPERIMENTAL_protocol_config unavailable; the burn/contract split of gas is not stated")

    count, crec = await fetch_json(client, ledger, source="nearblocks", name=f"txns:{CONTRACT}:count", method="GET",
                                   url=f"{config.NEARBLOCKS_API_BASE}/account/{CONTRACT}/txns/count", headers=config.nearblocks_headers(), **_RETRY_KW)
    rows = count.get("txns") if crec.ok and isinstance(count, dict) else None
    c = _int(rows[0].get("count")) if isinstance(rows, list) and rows and isinstance(rows[0], dict) else None
    if c is not None:
        out["cumulative_receipts"] = c
        out["cumulative_receipts_note"] = "all receipts executed at v1.signer (sign, respond, callbacks, admin), NearBlocks index"
    else:
        warnings.append(f"chain_signatures: NearBlocks txns/count unavailable ({crec.error or 'no count'}); cumulative receipts null")
        out["not_measured"].append("cumulative_receipts: NearBlocks count endpoint failed")

    if head_h is None or head_ns is None or probe_ns is None or probe_h is None or head_ns <= probe_ns:
        warnings.append("chain_signatures: head block or cadence probe unavailable; sign-request rate not sampled")
        out["not_measured"].append("sign rate / trend: block cadence unavailable, anchors cannot be placed")
        out["status"] = "count_only" if c is not None else "unavailable"
        return out
    spb = (head_ns - probe_ns) / 1e9 / (head_h - probe_h)
    out.update({"head_block": head_h, "head_time_utc": _utc(head_ns), "seconds_per_block": spb})

    plan = interleaved(sample_plan(head_ns, **plan_kwargs))
    windows: list[dict[str, Any]] = []
    t_start = time.monotonic()
    pending = list(range(len(plan)))
    stopped = False
    for pass_no in (1, 2):
        if not pending or stopped:
            break
        if pass_no == 2:
            if time.monotonic() - t_start + RETRY_COOLDOWN_S > budget_s:
                break
            await asyncio.sleep(RETRY_COOLDOWN_S if delay > 0 else 0)
        retry: list[int] = []
        transport_streak = 0
        # a distinct record name per pass: the failed pass-1 response keeps its own raw file and hash
        suffix = "" if pass_no == 1 else ":retry"
        for n, i in enumerate(pending):
            anchor = plan[i]
            if time.monotonic() - t_start > budget_s:
                warnings.append(f"chain_signatures: {budget_s:g} s sampling budget spent (NearBlocks rate limits) in pass {pass_no} with {len(pending) - n} window(s) left; set VALUO_CHAINSIG_BUDGET_S to sample them")
                retry += pending[n:]
                stopped = True
                break
            await asyncio.sleep(delay)
            if anchor["kind"] == "level":
                before = head_h - round(anchor["offset_h"] * 3600 / spb)
                anchor = {**anchor, "before_block": before}
                page, rec = await _page(client, ledger, {"before_block": before}, f"txns:{CONTRACT}:before_block:{before}{suffix}")
            else:
                page, rec = await _page(client, ledger, {"before_date": anchor["before_date"]}, f"txns:{CONTRACT}:before_date:{anchor['before_date']}{suffix}")
            summ = summarize_window(page.get("txns") if rec.ok and isinstance(page, dict) else None)
            if summ is None:
                retry.append(i)
                transport_streak = transport_streak + 1 if rec.http_status is None else 0
                if transport_streak >= 2:
                    warnings.append(f"chain_signatures: NearBlocks unreachable twice in a row in pass {pass_no}; remaining windows skipped")
                    retry += pending[n + 1:]
                    stopped = True
                    break
                continue
            transport_streak = 0
            summ.update(anchor)
            windows.append(summ)
        if pass_no == 2 and len(retry) < len(pending):
            warnings.append(f"chain_signatures: retry pass recovered {len(pending) - len(retry)} of {len(pending)} window(s) after a {RETRY_COOLDOWN_S:g} s cool-down")
        pending = retry
    failed = len(pending)
    out["windows_planned"] = len(plan)
    windows.sort(key=lambda w: -(w.get("newest_ns") or 0))
    if failed:
        warnings.append(f"chain_signatures: {failed} of {len(plan)} sample windows failed; rates use the {len(windows)} that returned")
    agg = aggregate_windows(windows, head_ns=head_ns)
    out["windows"] = [{k: v for k, v in w.items() if k not in ("deposits_yocto", "callers")} for w in windows]
    out.update(agg)
    if agg["windows_ok"] == 0:
        out["status"] = "count_only" if c is not None else "unavailable"
        out["not_measured"].append("sign rate / trend: no sample window returned")
        return out
    out["status"] = "measured"
    if agg["sign_per_day_30d"] is None:
        out["not_measured"].append("30d rate: one of the two strata (last 7 days, days 7-30) returned no window")
    if agg["trend"] is None:
        out["not_measured"].append(f"trend: fewer than {MIN_WINDOWS_FOR_TREND} 00:00 UTC windows returned")
    dep = agg.get("deposit_near_mean")
    out["fee_note"] = (
        f"sign() attaches {agg['deposit_yocto_median']:,.0f} yoctoNEAR (median of sampled requests), so the contract takes no material "
        "per-request fee; the requester's cost is gas." if dep is not None and dep < 1e-6 else
        "Deposit attached to sign() as reported by NearBlocks; whether the contract keeps or refunds it is not visible in this list."
    )
    if out["burnt_gas_reward"] is not None and agg.get("gas_near_per_day_30d") is not None:
        out["gas_burnt_net_near_per_day_30d"] = agg["gas_near_per_day_30d"] * (1 - out["burnt_gas_reward"])
        out["gas_to_contract_near_per_day_30d"] = agg["gas_near_per_day_30d"] * out["burnt_gas_reward"]
    return out


def attach_context(cs: dict[str, Any] | None, *, storage_sink: Any = None, near_price_usd: Any = None) -> dict[str, Any] | None:
    """Add the near_rpc ``v1.signer`` storage row and USD conversions at the snapshot NEAR price (pure, no I/O)."""
    if cs is None:
        return None
    px = float(near_price_usd) if isinstance(near_price_usd, (int, float)) and math.isfinite(near_price_usd) and near_price_usd > 0 else None
    cs["near_price_usd"] = px
    if storage_sink is not None:
        cs["storage"] = {
            "storage_bytes": getattr(storage_sink, "storage_bytes", None), "storage_locked_near": getattr(storage_sink, "storage_locked_near", None),
            "growth_locked_near_per_day": getattr(storage_sink, "growth_locked_near_per_day", None),
            "state_block_height": getattr(storage_sink, "state_block_height", None), "source": "near_rpc view_account:v1.signer (snapshot block)",
        }
    else:
        cs["storage"] = None
        cs.setdefault("not_measured", []).append("storage: v1.signer missing from near_rpc tracked sinks")

    def usd(x: Any) -> float | None:
        return x * px if px is not None and isinstance(x, (int, float)) else None

    dep = cs.get("deposit_near_mean")
    rate = cs.get("sign_per_day_30d")
    cs["deposit_near_per_day_30d"] = dep * rate if isinstance(dep, (int, float)) and isinstance(rate, (int, float)) else None
    cs["deposit_usd_per_day_30d"] = usd(cs["deposit_near_per_day_30d"])
    cs["gas_usd_per_sign"] = usd(cs.get("gas_near_per_sign"))
    cs["gas_usd_per_day_30d"] = usd(cs.get("gas_near_per_day_30d"))
    cs["storage_locked_usd"] = usd((cs.get("storage") or {}).get("storage_locked_near"))
    return cs
