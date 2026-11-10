"""Confidential Intents boundary audit, read from NEAR mainnet (no keys).

Confidential Intents settle on a private chain whose RPC needs authentication, so confidential *swap volume*
cannot be read by anyone outside it. What is public is the boundary: funds enter (shield) by an ``intents.near``
transfer to the Confidential Intents Treasury and leave (unshield) when the Treasury releases them
(docs.near-intents.org, integration/market-makers/confidential-intents and confidential-liquidity). The Treasury is
an implicit account holding NEP-245 balances inside ``intents.near``, so three things are measurable here:

1. **TVL**: ``mt_tokens_for_owner`` + ``mt_batch_balance_of`` on ``intents.near`` for the Treasury at the final
   block, priced with the live 1Click token list. Exact for every priced token.
2. **Net 30-day boundary flow**: the same balances ~30 days earlier (archival RPC), priced at *today's* prices so
   the difference is quantity flow, not price drift.
3. **24-hour gross flow, lower bound**: hourly balance snapshots over the last 24 hours; per token, positive steps
   are inflow (shields) and negative steps outflow (unshields). Shields and unshields inside the same hour net out,
   so both sums are LOWER BOUNDS on gross boundary flow.

Boundary flow is not swap volume: it includes solver inventory moves, and one confidential swap between foreign
chains shows up as one shield and one unshield. The pipeline uses inflow only as a floor on the confidential share
(``intents_forensics.confidential_split_guard``), never as the share itself.
"""
from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timezone
from typing import Any

import httpx

from valuo import config
from valuo.provenance import ProvenanceLedger, fetch_json, near_rpc_call

TREASURY = "51e8f94d77b5e90dc9852ca6113771e11e8382ce69473a75e313e41665de7cbe"
CONTRACT = "intents.near"
DOCS_URL = "https://docs.near-intents.org/integration/market-makers/confidential-intents"
FLOW_HOURS = 24
NET_FLOW_DAYS = 30
TOKEN_PAGE = 1000
CONCURRENCY = 4


def _args(obj: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode()


def _view_params(method: str, args: dict[str, Any], block_id: int | None) -> dict[str, Any]:
    p: dict[str, Any] = {"request_type": "call_function", "account_id": CONTRACT, "method_name": method, "args_base64": _args(args)}
    if block_id is None:
        p["finality"] = "final"
    else:
        p["block_id"] = int(block_id)
    return p


def _decode(result: Any) -> Any:
    try:
        return json.loads(bytes(result["result"]).decode())
    except (KeyError, TypeError, ValueError):
        return None


def _utc(ns: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(ns) / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def price_table(tokens: Any) -> dict[str, tuple[float, int, str]]:
    """1Click /v0/tokens -> {asset_id: (price_usd, decimals, symbol)} for priced tokens."""
    out: dict[str, tuple[float, int, str]] = {}
    for t in tokens if isinstance(tokens, list) else []:
        aid, px, dec = t.get("assetId"), t.get("price"), t.get("decimals")
        if isinstance(aid, str) and isinstance(px, (int, float)) and px > 0 and isinstance(dec, int):
            out[aid] = (float(px), dec, str(t.get("symbol") or aid))
    return out


def value_usd(balances: dict[str, int], prices: dict[str, tuple[float, int, str]]) -> float:
    return sum(amt / 10 ** prices[t][1] * prices[t][0] for t, amt in balances.items() if t in prices and amt)


def step_flows(series: list[dict[str, int]], prices: dict[str, tuple[float, int, str]]) -> tuple[float, float]:
    """Sum of priced positive (in) and negative (out) per-token steps between consecutive snapshots."""
    gin = gout = 0.0
    for prev, cur in zip(series, series[1:]):
        for t in set(prev) | set(cur):
            if t not in prices:
                continue
            d = (cur.get(t, 0) - prev.get(t, 0)) / 10 ** prices[t][1] * prices[t][0]
            if d > 0:
                gin += d
            else:
                gout -= d
    return gin, gout


async def _balances(client: httpx.AsyncClient, ledger: ProvenanceLedger, ids: list[str], block_id: int | None, name: str) -> tuple[dict[str, int] | None, int | None]:
    res, _rec = await near_rpc_call(client, ledger, "query", _view_params("mt_batch_balance_of", {"account_id": TREASURY, "token_ids": ids}, block_id), name, retries=3)
    vals = _decode(res) if res else None
    if not isinstance(vals, list) or len(vals) != len(ids):
        return None, None
    return {t: int(v) for t, v in zip(ids, vals)}, res.get("block_height")


async def _block_time(client: httpx.AsyncClient, ledger: ProvenanceLedger, height: int | None, name: str) -> tuple[int | None, str | None]:
    params: dict[str, Any] = {"finality": "final"} if height is None else {"block_id": int(height)}
    res, _rec = await near_rpc_call(client, ledger, "block", params, name, retries=3)
    if not res:
        return None, None
    h = res.get("header", {})
    return h.get("height"), _utc(h.get("timestamp_nanosec") or h.get("timestamp"))


async def collect_confidential_boundary(client: httpx.AsyncClient, ledger: ProvenanceLedger, warnings: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "treasury_account": TREASURY, "contract": CONTRACT, "docs_url": DOCS_URL, "status": "unavailable",
        "tvl_usd": None, "flow_24h_in_lower_bound_usd": None, "flow_24h_out_lower_bound_usd": None, "net_flow_30d_usd": None,
        "basis": ("Treasury NEP-245 balances in intents.near priced with the live 1Click token list; flows are balance "
                  "differences priced at today's prices. Boundary flow is not swap volume; 24h flows are lower bounds."),
    }
    head_h, head_t = await _block_time(client, ledger, None, "confidential:block:final")
    if head_h is None:
        warnings.append("confidential boundary: final block unavailable; treasury not audited")
        return out
    out.update({"block_height": head_h, "block_time_utc": head_t})

    ids: list[str] = []
    while True:
        res, _ = await near_rpc_call(client, ledger, "query", _view_params(
            "mt_tokens_for_owner", {"account_id": TREASURY, "from_index": str(len(ids)), "limit": TOKEN_PAGE}, head_h),
            f"confidential:mt_tokens_for_owner:{len(ids)}", retries=3)
        page = _decode(res) if res else None
        if not isinstance(page, list):
            warnings.append("confidential boundary: mt_tokens_for_owner failed; treasury not audited")
            return out
        ids += [t["token_id"] for t in page if isinstance(t, dict) and "token_id" in t]
        if len(page) < TOKEN_PAGE:
            break

    tokens, _rec = await fetch_json(client, ledger, source="oneclick", name="tokens:confidential_pricing", method="GET",
                                    url=f"{config.ONECLICK_API_BASE}/v0/tokens", headers=config.oneclick_headers())
    prices = price_table(tokens)
    if not prices:
        warnings.append("confidential boundary: 1Click token prices unavailable; treasury balances not priced")
        return out

    head_bal, _ = await _balances(client, ledger, ids, head_h, "confidential:balances:head")
    if head_bal is None:
        warnings.append("confidential boundary: treasury balances unavailable at the final block")
        return out
    unpriced = sorted(t for t, a in head_bal.items() if a and t not in prices)
    top = sorted(((head_bal[t] / 10 ** prices[t][1] * prices[t][0], prices[t][2], t) for t in head_bal if t in prices and head_bal[t]), reverse=True)[:6]
    out.update({
        "status": "measured", "n_tokens": len(ids), "n_tokens_priced": sum(1 for t in ids if t in prices),
        "n_tokens_unpriced_nonzero": len(unpriced), "tvl_usd": value_usd(head_bal, prices),
        "tvl_top": [{"symbol": s, "token_id": t, "usd": v} for v, s, t in top],
    })

    # Block cadence from the chain itself (no hard-coded block time): heights per second over the last ~day.
    probe = max(1, head_h - 150_000)
    probe_h, probe_t = await _block_time(client, ledger, probe, "confidential:block:cadence_probe")
    sec_per_block = None
    if probe_h and probe_t and head_t:
        dt = (datetime.fromisoformat(head_t.replace("Z", "+00:00")) - datetime.fromisoformat(probe_t.replace("Z", "+00:00"))).total_seconds()
        sec_per_block = dt / max(1, head_h - probe_h) if dt > 0 else None
    if not sec_per_block:
        warnings.append("confidential boundary: block cadence unavailable; flows not measured (TVL only)")
        out["status"] = "tvl_only"
        return out
    out["seconds_per_block"] = sec_per_block

    sem = asyncio.Semaphore(CONCURRENCY)

    async def snap(height: int, name: str) -> dict[str, int] | None:
        async with sem:
            bal, _ = await _balances(client, ledger, ids, height, name)
            return bal

    # Net 30-day flow (quantities, priced today).
    h30 = head_h - round(NET_FLOW_DAYS * 86400 / sec_per_block)
    bal30, (b30_h, b30_t) = await asyncio.gather(snap(h30, "confidential:balances:30d_ago"), _block_time(client, ledger, h30, "confidential:block:30d_ago"))
    if bal30 is not None:
        tvl30 = value_usd(bal30, prices)
        out.update({"tvl_30d_ago_usd_at_current_prices": tvl30, "net_flow_30d_usd": out["tvl_usd"] - tvl30,
                    "block_30d_ago": b30_h or h30, "block_30d_ago_time_utc": b30_t})
    else:
        warnings.append("confidential boundary: archival balances 30 days back unavailable; net 30d flow null")

    # 24 hourly snapshots back from head (head reused).
    step = round(3600 / sec_per_block)
    heights = [head_h - k * step for k in range(FLOW_HOURS, 0, -1)]
    snaps = await asyncio.gather(*(snap(h, f"confidential:balances:hourly:-{FLOW_HOURS - i}h") for i, h in enumerate(heights)))
    series = [s for s in snaps if s is not None] + [head_bal]
    n_ok = len(series)
    start_h, start_t = await _block_time(client, ledger, heights[0], "confidential:block:flow_start")
    if n_ok >= FLOW_HOURS * 0.75:
        gin, gout = step_flows(series, prices)
        out.update({
            "flow_24h_in_lower_bound_usd": gin, "flow_24h_out_lower_bound_usd": gout,
            "flow_window": {"start_block": start_h or heights[0], "start_time_utc": start_t, "end_block": head_h, "end_time_utc": head_t,
                            "step_blocks": step, "snapshots_requested": FLOW_HOURS + 1, "snapshots_ok": n_ok},
        })
        if n_ok < FLOW_HOURS + 1:
            warnings.append(f"confidential boundary: {FLOW_HOURS + 1 - n_ok} hourly treasury snapshots failed; their steps merge (flows stay lower bounds)")
    else:
        warnings.append(f"confidential boundary: only {n_ok} of {FLOW_HOURS + 1} hourly treasury snapshots returned; 24h flow not measured")
        out["status"] = "tvl_only" if out["status"] == "measured" else out["status"]
    return out
