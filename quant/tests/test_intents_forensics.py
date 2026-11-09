"""intents_forensics collector: classification, HHI math, take-rate math, sigma math, and the full
assembly against recorded fixtures served through an httpx MockTransport (no network). Synthetic
inputs appear only here, never in the collector."""
from __future__ import annotations

import asyncio
import json
import math
from collections import Counter
from pathlib import Path

import httpx
import numpy as np
import pytest

from valuo import config
from valuo.collectors import intents_forensics as forensics
from valuo.collectors.intents_forensics import (
    IntentsForensicsError,
    align_daily_series,
    caller_concentration,
    classify_account,
    classify_caller,
    collect_intents_forensics,
    collect_intents_forensics_async,
    extract_top_swaps,
    fee_metrics,
    hhi_from_counts,
    price_volatility,
    volume_volatility,
)
from valuo.provenance import ProvenanceLedger
from valuo.schemas import CallerClass, IntentsForensics

PAGE1_CURSOR = "24894480007"
EXEC_FIXTURE = "nearblocks_exec_txns_5pages_trimmed.json"
LIFETIME_COUNT = "156722083"


# ----------------------------------------------------------------------------- mock transport
def _fixture_id_rate(rows: list[dict]) -> float:
    return forensics.estimate_id_rate([(int(r["id"]), int(r["receipt_block"]["block_timestamp"])) for r in rows])


def _deep_exec_page(rows: list[dict], cursor: int, calls: list[int]) -> dict:
    """A synthetic deep page for an id cursor: the next recorded 50-row chunk (rows 50..249, cycling) re-stamped so its
    newest id is cursor - 1 and its timestamps move with the ids at the recorded id/time slope (a linear id <-> time map,
    which is what the collector's cursor aiming assumes). Payloads are the recorded ones; only id/time are shifted."""
    chunk = rows[50 + 50 * (len(calls) % 4): 100 + 50 * (len(calls) % 4)]
    calls.append(cursor)
    rate = _fixture_id_rate(rows)  # ids per second
    shift = cursor - 1 - max(int(r["id"]) for r in chunk)
    out = []
    for r in chunk:
        rb = dict(r["receipt_block"])
        rb["block_timestamp"] = int(rb["block_timestamp"]) + int(shift / rate * 1e9)
        out.append({**r, "id": str(int(r["id"]) + shift), "receipt_block": rb})
    return {"cursor": str(min(int(r["id"]) for r in out)), "txns": out}


def _router(probes_dir: Path, *, drop_cursor: bool = False, fail: frozenset[str] = frozenset(), seen: list[httpx.URL] | None = None):
    """Route requests to fixture bytes by host/path. ``fail`` names hosts that answer 404 JSON (never retried)."""

    exec_calls: list[int] = []

    def fixture(name: str) -> bytes:
        return (probes_dir / name).read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        url = request.url
        if seen is not None:
            seen.append(url)
        host, path, q = url.host, url.path, dict(url.params)
        if host in fail:
            return httpx.Response(404, json={"message": f"simulated outage for {host}"})
        if host == "nearstats.org":
            if path.endswith("/summary"):
                return httpx.Response(200, content=fixture("nearstats_summary.json"))
            if path.endswith("/price-history"):
                assert q.get("window") == "1y"
                return httpx.Response(200, content=fixture("nearstats_price_1y.json"))
        if host == "api.llama.fi":
            if path.endswith("/summary/dexs/near-intents"):
                return httpx.Response(200, content=fixture("llama_dexs_near_intents.json"))
            if path.endswith("/summary/fees/near-intents"):
                dt = q.get("dataType")
                name = {"dailyRevenue": "llama_rev_near_intents.json", "dailyHoldersRevenue": "llama_hrev_near_intents.json"}.get(dt, "llama_fees_near_intents.json")
                return httpx.Response(200, content=fixture(name))
        if host == "api.nearblocks.io":
            if path.endswith("/txns/count"):
                return httpx.Response(200, json={"txns": [{"cost": "245113770.83", "count": LIFETIME_COUNT}]})
            if path.endswith("/stats"):
                return httpx.Response(200, content=fixture("nearblocks_stats.json"))
            if path.endswith("/account/intents.near/txns") and q.get("method") == "execute_intents":
                # Method-filtered solver pages: slices of the recorded 2026-11-08 hub-settled sample.
                assert q.get("per_page") == "50"
                exec_rows = json.loads(fixture(EXEC_FIXTURE))
                if "cursor" in q:
                    page = _deep_exec_page(exec_rows["txns"], int(q["cursor"]), exec_calls)
                else:
                    page = {"cursor": exec_rows["_page1_cursor"], "txns": exec_rows["txns"][:50]}
                return httpx.Response(200, json=page)
            if path.endswith("/account/intents.near/txns"):
                assert q.get("per_page") == "25"
                if "cursor" in q:
                    assert q["cursor"] == PAGE1_CURSOR
                    page = json.loads(fixture("nearblocks_txns_p2.json"))
                else:
                    page = json.loads(fixture("nearblocks_txns.json" if q.get("page") == "1" else "nearblocks_txns_p2.json"))
                if drop_cursor:
                    page.pop("cursor", None)
                return httpx.Response(200, json=page)
        return httpx.Response(404, json={"message": f"unrouted {url}"})

    return handler


def _collect(ledger: ProvenanceLedger, handler, **kwargs) -> IntentsForensics:
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await collect_intents_forensics_async(ledger, client=client, page_delay_s=0, **kwargs)

    return asyncio.run(go())


# ----------------------------------------------------------------------------- classification
@pytest.mark.parametrize(
    "account, expected",
    [
        ("system", CallerClass.system),
        ("intents.near", CallerClass.self_internal),
        ("escrow.ai.near", CallerClass.ai_agent),
        ("vault-7.agent.near", CallerClass.ai_agent),
        ("sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near", CallerClass.bridge_relayer),
        ("eth.omft.near", CallerClass.bridge_relayer),
        ("v2_1.omni.hot.tg", CallerClass.bridge_relayer),
        ("omni.bridge.near", CallerClass.bridge_relayer),
        ("7f4aacbef51f39f90338b106acc1522d6304dd0a9515fe14185f3518be3bb75a", CallerClass.implicit_account),
        ("0xd8da6bf26964af9d7eed9e03e53415d37aa96045", CallerClass.implicit_account),
        ("kevin4.near", CallerClass.named_account),
        ("wrap.near", CallerClass.named_account),
        ("7f4aacbef51f39f90338b106acc1522d6304dd0a9515fe14185f3518be3bb75", CallerClass.named_account),  # 63 hex chars
    ],
)
def test_classify_account_rules(account: str, expected: CallerClass):
    assert classify_account(account) is expected


def test_classify_caller_is_method_aware():
    usdc = "17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1"
    # a 64-hex predecessor calling ft_on_transfer is the token contract (NEP-141 ft_transfer_call), not a user
    assert classify_caller(usdc, ["ft_on_transfer"]) is CallerClass.bridge_relayer
    assert classify_caller(usdc, ["ft_withdraw"]) is CallerClass.implicit_account
    assert classify_caller(usdc) is CallerClass.implicit_account
    assert classify_caller("escrow.ai.near", ["ft_on_transfer"]) is CallerClass.ai_agent  # AI label wins
    assert classify_caller("wrap.near", [None, "TRANSFER"]) is CallerClass.named_account


# ----------------------------------------------------------------------------- HHI math
def test_hhi_from_counts_bounds_and_identities():
    hhi, shares = hhi_from_counts({"a": 7})
    assert hhi == pytest.approx(10_000.0) and shares == {"a": 1.0}
    for n in (2, 5, 12, 100):
        hhi, shares = hhi_from_counts({f"acct{i}": 3 for i in range(n)})
        assert hhi == pytest.approx(10_000.0 / n)
        assert sum(shares.values()) == pytest.approx(1.0, abs=1e-9)
    hhi, shares = hhi_from_counts({"a": 4, "b": 1, "c": 1, "d": 0})
    assert "d" not in shares and hhi == pytest.approx((100 * 4 / 6) ** 2 + 2 * (100 / 6) ** 2)
    assert hhi_from_counts({}) == (None, {}) and hhi_from_counts({"a": 0}) == (None, {})


def test_caller_concentration_from_two_fixture_pages(load_fixture):
    rows = load_fixture("nearblocks_txns.json")["txns"] + load_fixture("nearblocks_txns_p2.json")["txns"]
    warnings: list[str] = []
    c = caller_concentration(rows, warnings=warnings)
    assert warnings == [] and c["receipts_sampled"] == 50 and c["external_receipts_sampled"] == 12

    # independent recomputation of the external HHI from raw predecessor counts
    ext = Counter(t["predecessor_account_id"] for t in rows if t["predecessor_account_id"] not in ("system", "intents.near"))
    total = sum(ext.values())
    expected_hhi = sum((100 * v / total) ** 2 for v in ext.values())
    assert c["hhi_external"] == pytest.approx(expected_hhi) and c["hhi_external"] == pytest.approx(1666.6667, rel=1e-6)
    assert 0 < c["hhi_external"] <= 10_000 and c["n_eff_external"] == pytest.approx(6.0)
    assert sum(s.share for s in c["callers"]) == pytest.approx(1.0, abs=1e-9)
    assert sum(s.receipts for s in c["callers"]) == total == 12

    all_counts = Counter(t["predecessor_account_id"] for t in rows)
    assert c["hhi_all"] == pytest.approx(sum((100 * v / 50) ** 2 for v in all_counts.values())) == pytest.approx(2984.0)

    top = c["callers"][0]
    assert top.account_id == "escrow.ai.near" and top.cls is CallerClass.ai_agent and top.receipts == 4
    assert top.share == pytest.approx(4 / 12)
    # first escrow.ai.near receipt on page 1 -> clickable explorer link target
    assert top.example_tx_hash.startswith("6WR1wU9cEN9U") and len(top.example_tx_hash) >= 40
    assert c["ai_agent_share"] == pytest.approx(4 / 12)
    # bridge = 4 omft token contracts + the 64-hex NEAR-native USDC contract (ft_on_transfer)
    assert c["bridge_share"] == pytest.approx(5 / 12)
    assert c["class_counts"]["implicit_account"] == 1 and c["class_counts"]["named_account"] == 2
    assert c["class_counts"]["system"] == 19 and c["class_counts"]["self_internal"] == 19
    # without the AI escrow caller: 8 single-receipt callers -> HHI 10000/8
    assert c["hhi_external_ex_ai_agent"] == pytest.approx(1250.0) and c["n_eff_external_ex_ai_agent"] == pytest.approx(8.0)

    assert sum(c["method_mix"].values()) == 50
    assert c["method_mix"]["execute_intents"] == 12 and c["method_mix"]["TRANSFER"] == 20 and c["method_mix"]["ft_on_transfer"] == 5
    assert c["sample_block_range"] == [222342320, 222342533]
    assert len(c["sample_time_range_utc"]) == 2 and c["sample_span_s"] > 0


def test_caller_concentration_dedups_and_skips_malformed(load_fixture):
    rows = load_fixture("nearblocks_txns.json")["txns"]
    warnings: list[str] = []
    c = caller_concentration(rows + rows[:5] + [{"no_predecessor": True}], warnings=warnings)
    assert c["receipts_sampled"] == 25
    assert any("duplicate" in w for w in warnings) and any("shape validation" in w for w in warnings)
    assert caller_concentration([], warnings=[])["hhi_external"] is None


# ----------------------------------------------------------------------------- take-rate math
def test_fee_metrics_take_rates_and_series(load_fixture):
    fees, rev, hrev, dexs = (load_fixture(n) for n in ("llama_fees_near_intents.json", "llama_rev_near_intents.json", "llama_hrev_near_intents.json", "llama_dexs_near_intents.json"))
    warnings: list[str] = []
    m = fee_metrics(fees, rev, hrev, dexs, nearstats_volume_30d=1.0, nearstats_public_30d=2_357_475_756.0, warnings=warnings)
    assert warnings == []
    # One aligned window: the last 30 complete UTC days common to all four charts (fixtures end 2026-10-29).
    assert m["take_rate_window_days"] == 30 and m["take_rate_window_start_utc"] == "2026-09-30" and m["take_rate_window_end_utc"] == "2026-10-29"
    assert m["volume_30d_source"].startswith("defillama:dexs/near-intents daily chart") and "aligned" in m["take_rate_window"]
    assert m["volume_30d_usd"] == pytest.approx(sum(v for _, v in dexs["totalDataChart"][-30:])) == dexs["total30d"]
    assert m["gross_fees_30d_usd"] == pytest.approx(sum(v for _, v in fees["totalDataChart"][-30:]))
    assert m["defillama_total30d"] == {"fees": fees["total30d"], "revenue": rev["total30d"], "holders": hrev["total30d"], "volume": dexs["total30d"]}
    assert m["volume_30d_nearstats_usd"] == 1.0
    assert m["gross_take_bps"] == pytest.approx(fees["total30d"] / dexs["total30d"] * 1e4) == pytest.approx(15.819, abs=1e-3)
    assert m["net_take_bps"] == pytest.approx(rev["total30d"] / dexs["total30d"] * 1e4) == pytest.approx(5.589, abs=1e-3)
    assert m["holders_take_bps"] == pytest.approx(hrev["total30d"] / dexs["total30d"] * 1e4)
    assert m["capture_ratio"] == pytest.approx(rev["total30d"] / fees["total30d"]) == pytest.approx(0.3533, abs=1e-4)
    assert m["gross_take_bps_on_public_volume"] == pytest.approx(fees["total30d"] / 2_357_475_756.0 * 1e4)
    assert m["cumulative_fees_usd"] == fees["totalAllTime"] and m["fees_1y_usd"] == fees["total1y"] and m["revenue_1y_usd"] == rev["total1y"]
    assert m["annualized_gross_fees_30d_usd"] == pytest.approx(fees["total30d"] * 365 / 30)
    assert "swept" in m["methodology"]["revenue"].lower() or "revenue" in m["methodology"]["revenue"].lower()
    series = m["daily_series"]
    assert m["daily_series_days"] == len(series) == 60 and m["daily_series_columns"][0] == "ts_unix_s"
    ts = [r[0] for r in series]
    assert ts == sorted(ts) and len(set(ts)) == len(ts)
    assert series[-1] == [dexs["totalDataChart"][-1][0], fees["totalDataChart"][-1][1], rev["totalDataChart"][-1][1], dexs["totalDataChart"][-1][1]]


def test_fee_metrics_degrades_to_null_and_nearstats_denominator(load_fixture):
    fees = load_fixture("llama_fees_near_intents.json")
    warnings: list[str] = []
    m = fee_metrics(fees, None, None, None, nearstats_volume_30d=3_893_483_160.0, warnings=warnings)
    assert m["volume_30d_source"].startswith("nearstats") and m["gross_take_bps"] == pytest.approx(fees["total30d"] / 3_893_483_160.0 * 1e4)
    assert m["net_take_bps"] is None and m["capture_ratio"] is None and m["daily_series"] == []
    assert any("dailyRevenue" in w for w in warnings) and any("fell back to nearstats" in w for w in warnings)
    m2 = fee_metrics(None, None, None, None, warnings=[])
    assert m2["gross_take_bps"] is None and m2["volume_30d_usd"] is None


def test_align_daily_series_inner_join():
    fees = [[1, 10], [2, 20], [3, 30], [4, 40]]
    rev = [[2, 2], [3, 3], [4, 4], [5, 5]]
    vol = [[1, 100], [3, 300], [4, 400], ["bad", 1], [5]]
    assert align_daily_series(fees, rev, vol) == [[3, 30, 3, 300], [4, 40, 4, 400]]
    assert align_daily_series(fees, rev, vol, days=1) == [[4, 40, 4, 400]]
    assert align_daily_series(None, rev, vol) == []


def test_aligned_window_drops_partial_current_day_and_unaligned_points():
    from datetime import date

    from valuo.collectors.intents_forensics import aligned_window_sums

    day = 86_400
    t0 = 1_790_000_000 - (1_790_000_000 % day)  # a UTC midnight
    days = [t0 + k * day for k in range(6)]
    fees = [[t, 10.0] for t in days]                    # 6 days incl. a trailing partial day
    rev = [[t, 3.0] for t in days[:-1]]                 # revenue chart lacks the last day
    vol = [[t, 1000.0] for t in days[1:]]               # volume chart lacks the first day
    hrev = [[t, 3.0] for t in days]
    as_of = date.fromtimestamp(days[-1])  # "today" == the trailing fees point -> partial, dropped anyway by the join
    w = aligned_window_sums(fees, rev, hrev, vol, days=30, as_of=as_of)
    assert w["window_days"] == 4 and w["fees"] == 40.0 and w["revenue"] == 12.0 and w["volume"] == 4000.0 and w["holders"] == 12.0
    # When the volume chart does carry today's point it is still excluded as a partial day.
    vol_today = vol + []
    rev_today = rev + [[days[-1], 3.0]]
    w2 = aligned_window_sums(fees, rev_today, hrev, vol_today, days=30, as_of=as_of)
    assert w2["window_days"] == 4 and w2["window_end_utc"] == date.fromtimestamp(days[-2]).isoformat()
    w3 = aligned_window_sums(fees, rev_today, None, vol_today, days=2, as_of=date.fromtimestamp(days[-1] + day))
    assert w3["window_days"] == 2 and w3["fees"] == 20.0 and w3["holders"] is None
    assert aligned_window_sums(None, rev, hrev, vol)["window_days"] == 0


def test_fee_metrics_window_is_shared_by_take_rates(load_fixture):
    fees, rev, hrev, dexs = (load_fixture(n) for n in ("llama_fees_near_intents.json", "llama_rev_near_intents.json", "llama_hrev_near_intents.json", "llama_dexs_near_intents.json"))
    # Append a partial "today" point to the fees chart only: DefiLlama's total30d would include it, the window must not.
    fees_partial = dict(fees)
    last_ts = fees["totalDataChart"][-1][0]
    fees_partial["totalDataChart"] = fees["totalDataChart"] + [[last_ts + 86_400, 50_000.0]]
    fees_partial["total30d"] = fees["total30d"] + 50_000.0 - fees["totalDataChart"][-30][1]
    from datetime import datetime, timezone
    as_of = datetime.fromtimestamp(last_ts + 86_400, tz=timezone.utc).date()
    m = fee_metrics(fees_partial, rev, hrev, dexs, warnings=[], as_of=as_of)
    assert m["gross_fees_30d_usd"] == pytest.approx(sum(v for _, v in fees["totalDataChart"][-30:]))
    assert m["defillama_total30d"]["fees"] == fees_partial["total30d"] != m["gross_fees_30d_usd"]
    assert m["gross_take_bps"] == pytest.approx(m["gross_fees_30d_usd"] / m["volume_30d_usd"] * 1e4)
    assert m["net_take_bps"] == pytest.approx(m["net_revenue_30d_usd"] / m["volume_30d_usd"] * 1e4)
    assert m["capture_ratio"] == pytest.approx(m["net_revenue_30d_usd"] / m["gross_fees_30d_usd"])


# ----------------------------------------------------------------------------- sigma math
def test_price_volatility_matches_numpy(load_fixture):
    points = load_fixture("nearstats_price_1y.json")["points"]
    warnings: list[str] = []
    v = price_volatility(points, warnings)
    closes = np.array([p["c"] for p in sorted(points, key=lambda p: p["t"])], dtype=float)
    rets = np.diff(np.log(closes))
    assert warnings == [] and v["n_points"] == 365 and v["n_obs"] == 364
    assert v["periods_per_year"] == pytest.approx(365.0)
    assert v["daily_sigma"] == pytest.approx(rets.std(ddof=1), rel=1e-12)
    assert v["annualized_sigma"] == pytest.approx(rets.std(ddof=1) * math.sqrt(365), rel=1e-12)
    assert v["sigma_30d_annualized"] == pytest.approx(rets[-30:].std(ddof=1) * math.sqrt(365), rel=1e-12)
    assert v["sigma_90d_annualized"] == pytest.approx(rets[-90:].std(ddof=1) * math.sqrt(365), rel=1e-12)
    assert v["mean_daily_log_return"] == pytest.approx(rets.mean(), rel=1e-12)
    assert 0.3 < v["annualized_sigma"] < 3.0  # NEAR realized vol is in the tens of percent to low hundreds
    assert v["first_t_utc"] < v["last_t_utc"] and v["price_last_usd"] == closes[-1]


def test_price_volatility_handles_short_or_broken_series():
    warnings: list[str] = []
    v = price_volatility([{"t": 1, "c": 1.0}, {"t": 2, "c": 0.0}, {"t": 3}], warnings)
    assert v["daily_sigma"] is None and v["annualized_sigma"] is None and v["n_obs"] == 0
    assert warnings and "sigma null" in warnings[0]


def test_volume_volatility_daily_and_monthly(load_fixture):
    chart = load_fixture("llama_dexs_near_intents.json")["totalDataChart"]  # trimmed to 60 days
    warnings: list[str] = []
    v = volume_volatility(chart, warnings=warnings)
    vals = np.array([row[1] for row in chart], dtype=float)
    rets = np.diff(np.log(vals))
    assert v["volume_series_days"] == 60 and v["volume_daily_n_obs"] == 59
    assert v["volume_daily_sigma"] == pytest.approx(rets.std(ddof=1), rel=1e-12)
    assert v["volume_annualized_sigma"] == pytest.approx(rets.std(ddof=1) * math.sqrt(365), rel=1e-12)
    # 60 days -> two 30-day sums -> one monthly return -> no sample std
    assert v["volume_monthly_n_obs"] == 1 and v["volume_monthly_sigma"] is None
    assert any("monthly sigma null" in w for w in warnings)

    # synthetic 400-day series (tests only): 13 non-overlapping 30-day sums anchored at the end -> 12 returns
    days = 400
    synthetic = [[1_700_000_000 + 86_400 * i, 1e8 * (1.0 + 0.3 * math.sin(i / 9.0))] for i in range(days)]
    w2: list[str] = []
    v2 = volume_volatility(synthetic, days=days, warnings=w2)
    assert w2 == [] and v2["volume_daily_n_obs"] == 399 and v2["volume_monthly_n_obs"] == 12
    # the default window keeps only the trailing 365 days: 364 daily returns, 12 sums -> 11 monthly returns
    v3 = volume_volatility(synthetic, warnings=[])
    assert v3["volume_series_days"] == 365 and v3["volume_daily_n_obs"] == 364 and v3["volume_monthly_n_obs"] == 11
    arr = np.array([r[1] for r in synthetic])
    sums = [arr[days - 30 * (k + 1): days - 30 * k].sum() for k in range(13)][::-1]
    assert v2["volume_monthly_sigma"] == pytest.approx(np.diff(np.log(sums)).std(ddof=1), rel=1e-12)
    assert v2["volume_monthly_sigma"] > 0


# ----------------------------------------------------------------------------- solver audit (execute_intents payloads)
def test_decode_nested_json_peels_string_layers():
    from valuo.collectors.intents_forensics import decode_nested_json

    inner = {"signer_id": "a.near", "intents": [{"intent": "token_diff", "diff": {"x": "-1", "y": "2"}}]}
    once = json.dumps(inner)
    twice = json.dumps(once)[1:-1]            # a JSON string literal with its quotes stripped (NearBlocks message shape)
    args = json.dumps({"signed": [{"payload": {"message": twice}, "standard": "nep413"}]})
    assert decode_nested_json(once) == inner and decode_nested_json(twice) == inner
    assert decode_nested_json(args)["signed"][0]["standard"] == "nep413"
    assert decode_nested_json("not json") is None and decode_nested_json(None) is None and decode_nested_json({"a": 1}) == {"a": 1}


def _payload(signer: str, intents: list[str]) -> dict:
    return {"signer_id": signer, "intents": intents, "token_diffs": [{"a": "-1", "b": "1"}] if "token_diff" in intents else []}


def test_classify_fill_signers_rules():
    from valuo.collectors.intents_forensics import classify_fill_signers

    deposit = "6f935eb596e1cff5486ce983fe64a005e74700a2e38c38d05675ff86175a42bc"
    # structure: the pure token_diff signer is the solver; the withdrawing 1Click deposit address is the taker
    assert classify_fill_signers([_payload("blockzen-1-main.near", ["token_diff"]), _payload(deposit, ["token_diff", "transfer", "ft_withdraw"])]) == (
        ["blockzen-1-main.near"], [deposit], "structure")
    # name: two pure token_diff named accounts -> the one whose name says solver
    assert classify_fill_signers([_payload("brlabs-solver.near", ["token_diff"]), _payload("kipseli.near", ["token_diff"])]) == (
        ["brlabs-solver.near"], ["kipseli.near"], "name_or_known")
    # known: a solver identified by structure elsewhere keeps its identity in an all-pure fill
    assert classify_fill_signers([_payload("blockzen-1-main.near", ["token_diff"]), _payload(deposit, ["token_diff"])],
                                 frozenset({"blockzen-1-main.near"})) == (["blockzen-1-main.near"], [deposit], "name_or_known")
    # implicit: named vs implicit when nothing else separates them
    assert classify_fill_signers([_payload("somebody.near", ["token_diff"]), _payload(deposit, ["token_diff"])]) == (
        ["somebody.near"], [deposit], "implicit")
    # not a fill: one signer, or transfer-only payloads (solver inventory moves)
    assert classify_fill_signers([_payload("solver-priv-liq.near", ["transfer"]), _payload("solver-priv-liq.near", ["transfer"])]) == ([], [], "not_a_fill")
    assert classify_fill_signers([_payload("a.near", ["token_diff"])]) == ([], [], "not_a_fill")
    # unresolved: two pure, both named, neither flagged
    assert classify_fill_signers([_payload("a.near", ["token_diff"]), _payload("b.near", ["token_diff"])])[2] == "unresolved"


def test_solver_concentration_from_fixture_pages(load_fixture):
    from valuo.collectors.intents_forensics import (
        parse_execute_intents,
        solver_concentration,
    )

    rows = load_fixture("nearblocks_txns.json")["txns"] + load_fixture("nearblocks_txns_p2.json")["txns"]
    warnings: list[str] = []
    s = solver_concentration(rows, warnings)
    # 8 participations < SOLVER_MIN_PARTICIPATIONS: computed, but labelled thin with a warning.
    assert warnings == ["solver audit: only 8 solver fill participations; HHI_solver 2,812 is thin (< 10)"] and s["n_payloads_undecodable"] == 0
    assert s["measurement_status"] == "thin" and s["settlement_hub"] is None and s["n_fills_hub_legs"] == 0
    assert s["n_execute_intents_receipts"] == 12 and s["n_fills"] == 5 and s["n_fills_atomic"] == 5 and s["n_fills_unresolved"] == 0
    assert 0 < s["hhi_solver"] <= 10_000 and s["n_eff_solver"] == pytest.approx(10_000 / s["hhi_solver"])
    assert sum(r["share"] for r in s["solvers"]) == pytest.approx(1.0) and sum(r["fills"] for r in s["solvers"]) == s["n_fills_attributed"]
    by = {r["account_id"]: r for r in s["solvers"]}
    assert by["blockzen-1-main.near"]["fills"] >= 2 and by["solver-multichain-asset.near"]["fills"] >= 2
    assert "blockzen-1-main.near" in s["known_solvers_from_structure"]
    assert by["blockzen-1-main.near"]["example_tx_hash"] and len(by["blockzen-1-main.near"]["example_tx_hash"]) >= 40
    assert s["taker_class_mix"]["implicit_account"] >= 5  # takers are 1Click deposit addresses
    assert s["attribution_rules"]["not_a_fill"] == 7  # transfer-only execute_intents are inventory moves
    # The signers really are in the recorded payloads.
    signers = {p["signer_id"] for r in rows for p in parse_execute_intents(r) if p.get("signer_id")}
    assert set(by) <= signers
    assert solver_concentration([], [])["hhi_solver"] is None


# ----------------------------------------------------------------------------- top swaps
def test_extract_top_swaps_sorted_and_linked(load_fixture):
    swaps = extract_top_swaps(load_fixture("nearstats_summary.json"))
    assert len(swaps) == 10
    vols = [s["volume_usd"] for s in swaps]
    assert vols == sorted(vols, reverse=True) and vols[0] > 10_000
    assert swaps[0]["explorer_url"].startswith("https://nearblocks.io/txns/") and swaps[0]["tx_hash"] in swaps[0]["explorer_url"]
    assert "buybacks.multisignature.near" in {a for s in swaps for a in s["affiliates"]}
    assert extract_top_swaps({}) == []


# ----------------------------------------------------------------------------- full assembly (mock transport)
def test_collect_assembles_everything_from_fixtures(ledger: ProvenanceLedger, probes_dir: Path, load_fixture):
    seen: list[httpx.URL] = []
    f = _collect(ledger, _router(probes_dir, seen=seen), nearblocks_pages=2, solver_pages=2)
    summary, dexs, fees, rev = (load_fixture(n) for n in ("nearstats_summary.json", "llama_dexs_near_intents.json", "llama_fees_near_intents.json", "llama_rev_near_intents.json"))

    # volume + split
    totals, split = summary["intents"]["totals"], summary["intents"]["totalsBreakdown"]
    assert f.volume["source"] == "nearstats:intents.totals" and f.volume["30d"] == totals["volume30dUsd"] and f.volume["allTimeUsd"] == totals["allTimeUsd"]
    assert f.volume["public30d"] == split["public"]["volume30dUsd"] and f.volume["confidential30d"] == split["confidential"]["volume30dUsd"]
    assert f.volume["confidential_share_30d"] == pytest.approx(split["confidential"]["volume30dUsd"] / totals["volume30dUsd"])
    assert 0.35 < f.volume["confidential_share_30d"] < 0.45
    assert len(f.volume["weekOverWeek"]["days"]) == 14 and f.volume["records"]["max30dUsd"] > f.volume["30d"]
    assert f.volume["drawdown_from_30d_record"] == pytest.approx(1 - totals["volume30dUsd"] / split["records"]["max30dUsd"])
    assert f.volume["defillama"]["30d"] == dexs["total30d"]

    # protocol metrics
    assert f.confidential_tvl_usd == 144_420_000 and f.confidential_tvl_verified is False
    assert f.confidential_tvl_source_status == "unverified" and f.unique_users_7d == 103_102
    assert f.fees["cumulative_fees_nearstats_usd"] == pytest.approx(summary["intents"]["protocolMetrics"]["totalGeneratedFeesUsd"])

    # fees
    assert f.fees["gross_take_bps"] == pytest.approx(fees["total30d"] / dexs["total30d"] * 1e4)
    assert f.fees["capture_ratio"] == pytest.approx(rev["total30d"] / fees["total30d"])
    assert f.fees["daily_series_days"] == 60

    # price
    facts = summary["price"]["facts"]
    assert f.price["current_usd"] == summary["price"]["currentUsd"] and f.price["fdv_usd"] == facts["fdvUsd"] and f.price["ath_usd"] == facts["athUsd"]
    assert f.price["perf"]["1y"] == summary["price"]["performance"]["1y"] and f.price["source"] == "coingecko"
    assert f.price["circulating_supply_nearblocks"] == pytest.approx(1_249_836_992.16, rel=1e-9)
    assert f.price["total_supply_nearblocks"] == pytest.approx(1_310_395_407.25, rel=1e-9)

    # volatility (both price and volume blocks merged)
    assert f.volatility["n_obs"] == 364 and f.volatility["annualized_sigma"] > 0 and f.volatility["volume_daily_sigma"] > 0
    assert f.volatility["volume_monthly_sigma"] is None  # trimmed fixture

    # callers (deposit-source HHI) and solvers (execute_intents payload HHI)
    assert f.pages_fetched == 2 and f.receipts_sampled == 50 and f.lifetime_receipts == int(LIFETIME_COUNT)
    assert f.hhi_external == pytest.approx(1666.6667, rel=1e-6) and f.n_eff_external == pytest.approx(6.0)
    # solver audit = execute_intents in the caller pages (5 atomic fills, 2026-10-30) + 2 method-filtered pages (2026-11-08)
    sc = f.solver_concentration
    assert sc["sample"]["execute_intents_pages_ok"] == 2 and sc["sample"]["execute_intents_page_receipts"] == 100
    assert sc["n_execute_intents_receipts"] == 112 and sc["n_fills_atomic"] == 6 and sc["n_fills_hub_legs"] == 6
    assert sc["measurement_status"] == "measured" and 0 < sc["hhi_solver"] <= 10_000
    lo, hi = sc["hhi_solver_ci90"]
    assert lo <= sc["hhi_solver"] <= hi and sc["bootstrap_draws"] == 2000 and sc["bootstrap_seed"] == [20261114, 1]
    assert sc["settlement_hub"]["account_id"].startswith("51e8f94d")
    assert f.caller_sample["hhi_external_ci90"][0] <= f.hhi_external <= f.caller_sample["hhi_external_ci90"][1]
    assert f.caller_sample["execute_intents_by_predecessor_class"]["self_internal"] >= 8
    assert "deposit-source" in f.caller_sample["hhi_external_meaning"]
    assert sum(c.share for c in f.callers) == pytest.approx(1.0, abs=1e-9) and 0 < f.hhi_external <= 10_000
    assert f.callers[0].account_id == "escrow.ai.near" and f.ai_agent_share == pytest.approx(1 / 3)
    assert f.sample_block_range == [222342320, 222342533] and f.explorer_base == "https://nearblocks.io"
    assert len(f.top_swaps) == 10

    # provenance: 2 nearstats + 4 defillama + 2 caller pages + 2 execute_intents pages + count + stats, all ok, second pages via cursor
    names = sorted(r.name for r in ledger.records)
    assert names == sorted([
        "summary", "price_history:1y",
        "fees:near-intents", "fees:near-intents:dailyRevenue", "fees:near-intents:dailyHoldersRevenue", "dexs:near-intents",
        "txns:intents.near:p1", "txns:intents.near:p2", "txns_count:intents.near", "stats",
        "txns:intents.near:execute_intents:p1", "txns:intents.near:execute_intents:p2",
    ])
    assert all(r.ok for r in ledger.records) and ledger.sources() == {"defillama": 4, "nearblocks": 6, "nearstats": 2}
    page_urls = [u for u in seen if u.path.endswith("/account/intents.near/txns") and "method" not in u.params]
    assert dict(page_urls[0].params) == {"per_page": "25", "page": "1"} and dict(page_urls[1].params) == {"per_page": "25", "cursor": PAGE1_CURSOR}
    exec_urls = [u for u in seen if u.params.get("method") == "execute_intents"]
    assert len(exec_urls) == 2 and dict(exec_urls[0].params) == {"per_page": "50", "method": "execute_intents", "page": "1"}
    for rec in ledger.records:
        assert len(rec.sha256) == 64 and rec.raw_path is not None

    # warnings: only the trimmed-fixture monthly sigma, mirrored on the ledger with the module prefix
    assert f.warnings and all("monthly sigma" in w for w in f.warnings)
    assert ledger.warnings == [f"intents_forensics: {w}" for w in f.warnings]
    assert f.source_status["nearstats_summary"] is True and f.source_status["nearblocks_pages_ok"] == 2

    # round-trips through the schema with extras intact
    again = IntentsForensics.model_validate_json(f.model_dump_json())
    assert again == f and json.loads(f.model_dump_json())["callers"][0]["cls"] == "ai_agent"


def test_collect_falls_back_to_page_numbers_without_cursor(ledger: ProvenanceLedger, probes_dir: Path):
    seen: list[httpx.URL] = []
    f = _collect(ledger, _router(probes_dir, drop_cursor=True, seen=seen), nearblocks_pages=2)
    page_urls = [u for u in seen if u.path.endswith("/account/intents.near/txns")]
    assert dict(page_urls[1].params) == {"per_page": "25", "page": "2"}
    assert f.pages_fetched == 2 and any("no cursor" in w for w in f.warnings)


def test_collect_degrades_when_nearstats_is_down(ledger: ProvenanceLedger, probes_dir: Path, load_fixture):
    f = _collect(ledger, _router(probes_dir, fail=frozenset({"nearstats.org", "coins.llama.fi"})), nearblocks_pages=1)
    dexs = load_fixture("llama_dexs_near_intents.json")
    assert f.volume["source"] == "defillama:dexs/near-intents" and f.volume["30d"] == dexs["total30d"]
    assert f.volume["confidential_share_30d"] is None and f.volume["public30d"] is None
    assert f.confidential_tvl_usd is None and f.confidential_tvl_verified is False and f.unique_users_7d is None
    assert f.price["fdv_usd"] is None and f.price["circulating_supply_nearblocks"] is not None  # nearblocks still up
    assert f.volatility["annualized_sigma"] is None and f.volatility["volume_daily_sigma"] is not None
    assert f.top_swaps == [] and f.fees["gross_take_bps"] is not None
    assert f.source_status["nearstats_summary"] is False and f.source_status["nearstats_price_history"] is False
    assert any("nearstats summary unavailable" in w for w in f.warnings) and any("price-history" in w for w in f.warnings)
    assert any("coins.llama.fi price chart unavailable" in w for w in f.warnings)
    assert sum(1 for r in ledger.records if not r.ok) == 3  # summary, price-history, and the chart fallback


def test_price_sigma_falls_back_to_coins_llama_chart(ledger: ProvenanceLedger, probes_dir: Path, load_fixture):
    points = load_fixture("nearstats_price_1y.json")["points"]
    chart = {"coins": {"coingecko:near": {"symbol": "NEAR", "confidence": 0.99, "prices": [{"timestamp": p["t"] / 1e3, "price": p["c"]} for p in points]}}}
    base = _router(probes_dir, fail=frozenset({"nearstats.org"}))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "coins.llama.fi" and request.url.path.startswith("/chart/coingecko:near"):
            assert dict(request.url.params) == {"span": "365", "period": "1d"}
            return httpx.Response(200, json=chart)
        return base(request)

    f = _collect(ledger, handler, nearblocks_pages=1)
    expected = price_volatility(points, [])
    assert f.volatility["annualized_sigma"] == pytest.approx(expected["annualized_sigma"], rel=1e-9)
    assert "coins.llama.fi" in f.volatility["source"] and f.source_status["nearstats_price_history"] is False
    assert ledger.get("defillama", "price_chart:near:365d").ok is True


def test_nearblocks_transport_failure_fails_fast(ledger: ProvenanceLedger, probes_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("valuo.provenance._backoff_delay", lambda *_a, **_k: 0.0)
    base = _router(probes_dir)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.nearblocks.io":
            raise httpx.ConnectError("connection refused", request=request)
        return base(request)

    with pytest.raises(IntentsForensicsError, match="ConnectError"):
        _collect(ledger, handler, nearblocks_pages=4)
    nb = ledger.by_source("nearblocks")
    assert len(nb) == 1 and nb[0].attempts == 2  # count call only: one transport retry, then the chain is skipped
    assert any("unreachable" in w for w in ledger.warnings)


def test_collect_raises_when_no_receipts(ledger: ProvenanceLedger, probes_dir: Path):
    with pytest.raises(IntentsForensicsError, match="HHI undefined"):
        _collect(ledger, _router(probes_dir, fail=frozenset({"api.nearblocks.io"})), nearblocks_pages=2)
    assert all(not r.ok for r in ledger.by_source("nearblocks")) and ledger.by_source("nearstats")


def test_collect_raises_when_no_volume_anywhere(ledger: ProvenanceLedger, probes_dir: Path):
    with pytest.raises(IntentsForensicsError, match="30d intents volume unavailable"):
        _collect(ledger, _router(probes_dir, fail=frozenset({"nearstats.org", "api.llama.fi"})), nearblocks_pages=1)


def test_sync_wrapper_uses_same_defaults(monkeypatch: pytest.MonkeyPatch, ledger: ProvenanceLedger, probes_dir: Path):
    captured: dict[str, object] = {}

    async def fake(ledger_, **kwargs):
        captured.update(kwargs)
        return "sentinel"

    monkeypatch.setattr(forensics, "collect_intents_forensics_async", fake)
    assert collect_intents_forensics(ledger) == "sentinel"
    assert captured == {"nearblocks_pages": 4, "per_page": 25, "page_delay_s": None, "solver_pages": None, "solver_target_span_s": None}


# ----------------------------------------------------------------------------- live
@pytest.mark.live
def test_live_collect_intents_forensics(ledger: ProvenanceLedger):
    f = collect_intents_forensics(ledger, nearblocks_pages=2)
    assert f.volume["30d"] is not None and f.volume["30d"] > 1e8
    assert 0 < f.hhi_external <= 10_000 and sum(c.share for c in f.callers) == pytest.approx(1.0, abs=1e-9)
    assert f.n_eff_external == pytest.approx(10_000 / f.hhi_external)
    assert f.receipts_sampled >= 25 and f.pages_fetched >= 1 and f.sample_block_range[0] <= f.sample_block_range[1]
    if f.fees["gross_take_bps"] is not None:
        assert 0.1 < f.fees["gross_take_bps"] < 200 and 0 < f.fees["capture_ratio"] <= 1.5
    if f.volatility["annualized_sigma"] is not None:
        assert 0.2 < f.volatility["annualized_sigma"] < 4.0
    assert all(len(r.sha256) == 64 for r in ledger.records)
    assert config.NEARBLOCKS_PAGE_DELAY_S >= 0.4
    sm = f.solver_concentration["sample"]
    if sm["execute_intents_pages_ok"] >= 2 and sm["design"] == "stratified_time_sample":
        assert f.solver_concentration["sample_span_s"] >= 3600  # cursor jumps reach hours, not one ~3-minute window


# ----------------------------------------------------------------------------- confidential split guard (2026-11 source change)
def _split(load_fixture, name: str):
    from valuo.collectors.intents_forensics import confidential_split_guard, extract_protocol_metrics, extract_volume

    summary = load_fixture(name)
    warnings: list[str] = []
    vol = extract_volume(summary, None, warnings)
    metrics = extract_protocol_metrics(summary, warnings)
    return confidential_split_guard(vol, summary, metrics, warnings), warnings, summary


def test_split_guard_rejects_collapsed_split_and_falls_back_to_assumption(load_fixture):
    from valuo import assumptions as A

    vol, warnings, summary = _split(load_fixture, "nearstats_summary_split_collapsed.json")
    split = summary["intents"]["totalsBreakdown"]
    assert split["confidential"]["volume30dUsd"] < 1.0 and split["confidential"]["allTimeUsd"] == 0  # the recorded 2026-11-08 payload
    assert vol["confidential_share_status"] == "implausible_fallback" and vol["confidential_share_measured"] is False
    assert vol["confidential_share_30d"] == A.value("confidential_share") and vol["confidential_share_source"].startswith("assumption:")
    assert vol["confidential_share_30d_reported"] < 1e-9
    reasons = " | ".join(vol["confidential_share_reason"])
    assert "share_below_floor" in reasons and "tvl_without_volume" in reasons and "stream_ok" in reasons and "split_withheld" in reasons
    # raw fields withdrawn from the measured slots, preserved for audit
    assert vol["public30d"] is None and vol["confidential30d"] is None and vol["confidential_share_7d"] is None
    assert vol["split_reported"]["confidential30d"] == split["confidential"]["volume30dUsd"]
    assert vol["split_reported"]["public30d"] == split["public"]["volume30dUsd"]
    chain = vol["confidential_share_fallback_chain"]
    assert [c["step"] for c in chain] == ["nearstats intents.totalsBreakdown", "cross-check in fetched payloads", "assumption:confidential_share"]
    assert chain[-1]["source"] == "assumption"
    assert any(w.startswith("CONFIDENTIAL SPLIT IMPLAUSIBLE - NOT MEASURED") for w in warnings)


def test_split_guard_keeps_a_plausible_split_measured(load_fixture):
    vol, warnings, summary = _split(load_fixture, "nearstats_summary.json")
    assert vol["confidential_share_status"] == "measured" and vol["confidential_share_measured"] is True
    assert vol["confidential_share_30d"] == vol["confidential_share_30d_reported"] and 0.35 < vol["confidential_share_30d"] < 0.45
    assert "split_reported" not in vol and not any("CONFIDENTIAL SPLIT" in w for w in warnings)


def test_split_guard_uncorroborated_collapse_stays_measured_and_missing_split_is_unavailable():
    from valuo.collectors.intents_forensics import confidential_split_guard

    # A genuine collapse: nothing in the payload contradicts it -> measured, with a warning.
    vol = {"confidential_share_30d": 0.001, "allTimeUsd": 3.7e10, "confidential_allTimeUsd": 4.0e9}
    w: list[str] = []
    out = confidential_split_guard(vol, {"sourceHealth": {"confidentialStream": {"status": "degraded"}}}, {"confidential_tvl_usd": 1.4e8}, w)
    assert out["confidential_share_status"] == "measured" and out["confidential_share_30d"] == 0.001
    assert out["confidential_share_reason"] == ["below_floor_uncorroborated"] and any("genuine collapse" in x for x in w)
    # One contradiction is enough.
    out2 = confidential_split_guard({"confidential_share_30d": 0.0, "allTimeUsd": 3.7e10, "confidential_allTimeUsd": 4.0e9},
                                    {"sourceHealth": {"confidentialStream": {"status": "ok"}}}, {}, [])
    assert out2["confidential_share_status"] == "implausible_fallback"
    # Missing split: unavailable, share stays None (sotp's not-measured branch).
    out3 = confidential_split_guard({"confidential_share_30d": None}, None, None, [])
    assert out3["confidential_share_status"] == "unavailable" and out3["confidential_share_30d"] is None
    assert out3["confidential_share_measured"] is False


def test_collect_with_collapsed_split_flows_fallback_downstream(ledger: ProvenanceLedger, probes_dir: Path):
    base = _router(probes_dir)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "nearstats.org" and request.url.path.endswith("/summary"):
            return httpx.Response(200, content=(probes_dir / "nearstats_summary_split_collapsed.json").read_bytes())
        return base(request)

    f = _collect(ledger, handler, nearblocks_pages=1, solver_pages=0)
    assert f.volume["confidential_share_status"] == "implausible_fallback" and f.volume["confidential_share_30d"] == pytest.approx(0.40)
    assert f.fees["gross_take_bps_on_public_volume"] is None  # public 30d is not a measurement this run
    assert any("CONFIDENTIAL SPLIT IMPLAUSIBLE" in w for w in ledger.warnings)
    # sotp reads the share through confidential_share_30d (value flows; labelling needs the status, see report)
    from valuo.models.sotp_valuation import _volumes_30d
    from valuo import assumptions as A

    pub, conf, meta = _volumes_30d(f, A.ASSUMPTIONS, [])
    assert conf / (pub + conf) == pytest.approx(0.40)


# ----------------------------------------------------------------------------- hub-settled solver audit + bootstrap
def test_solver_audit_decodes_hub_settled_format(load_fixture):
    from valuo.collectors.intents_forensics import solver_concentration

    rows = load_fixture(EXEC_FIXTURE)["txns"]
    assert len(rows) == 250
    w: list[str] = []
    s = solver_concentration(rows, w)
    assert w == [] and s["measurement_status"] == "measured" and s["n_execute_intents_receipts"] == 250
    # 2026-11-08: almost no atomic token_diff fills; settlement runs through one hub account via transfer intents.
    assert s["n_fills_atomic"] == 2 and s["n_fills_hub_legs"] == 30 and s["n_fills_attributed"] == 34
    hub = s["settlement_hub"]
    assert hub["account_id"] == "51e8f94d77b5e90dc9852ca6113771e11e8382ce69473a75e313e41665de7cbe"
    assert hub["distinct_counterparties"] == 74 and hub["runner_up_counterparties"] == 17
    assert set(hub["solver_counterparties"]) == {"solver-priv-liq.near", "solver-multichain-asset.near", "solver-multichain-asset-escrow.near"}
    by = {r["account_id"]: r for r in s["solvers"]}
    assert by["solver-priv-liq.near"]["fills"] == 25 and by["solver-priv-liq.near"]["fills_hub"] == 23
    assert s["hhi_solver"] == pytest.approx(10_000 * (25**2 + 5**2 + 4**2) / 34**2)
    lo, hi = s["hhi_solver_ci90"]
    assert lo < s["hhi_solver"] < hi and lo > 3500  # whole interval above the cartel threshold in this sample
    assert s["n_eff_solver_ci90"] == pytest.approx([10_000 / hi, 10_000 / lo])
    assert s["attribution_rules"]["hub_transfer_leg"] == 30
    # deterministic
    assert solver_concentration(rows, [])["hhi_solver_ci90"] == s["hhi_solver_ci90"]


def test_bootstrap_hhi_ci_properties():
    from valuo.collectors.intents_forensics import bootstrap_hhi_ci

    one = bootstrap_hhi_ci([["a"]] * 20)
    assert one["hhi_ci90"] == [10_000.0, 10_000.0] and one["n_eff_ci90"] == [1.0, 1.0]
    empty = bootstrap_hhi_ci([])
    assert empty["hhi_ci90"] is None and empty["n_eff_ci90"] is None and empty["units"] == 0
    # 4 equal solvers x 100 units: HHI 2,500; the BC interval brackets the point and is reproducible per stream.
    units = [[k] for k in "abcd" for _ in range(100)]
    a = bootstrap_hhi_ci(units, stream=1)
    lo, hi = a["hhi_ci90"]
    assert lo <= 2500.0 <= hi and hi - lo < 300 and a["hhi_point"] == pytest.approx(2500.0)
    assert bootstrap_hhi_ci(units, stream=1) == a and bootstrap_hhi_ci(units, stream=2)["hhi_ci90"] != a["hhi_ci90"]
    # equal shares are the HHI minimum: every resample is >= 2,500, so the plain percentile interval sits above the point
    assert a["hhi_ci90_percentile"][0] > 2500.0 and lo == pytest.approx(2500.0)
    # multi-solver units count every participant
    multi = bootstrap_hhi_ci([["a", "b"]] * 10)
    assert multi["hhi_ci90"] == pytest.approx([5000.0, 5000.0])


def test_detect_settlement_hub_requires_dominance():
    from valuo.collectors.intents_forensics import detect_settlement_hub

    star = [(f"u{i}", "hub") for i in range(12)] + [("hub", f"v{i}") for i in range(3)]
    hub = detect_settlement_hub(star)
    assert hub is not None and hub["account_id"] == "hub" and hub["distinct_counterparties"] == 15 and hub["transfers_in"] == 12
    assert detect_settlement_hub([(f"u{i}", "hub") for i in range(5)]) is None  # too few counterparties
    two_hubs = [(f"u{i}", "h1") for i in range(12)] + [(f"w{i}", "h2") for i in range(10)]
    assert detect_settlement_hub(two_hubs) is None  # no single dominant account
    assert detect_settlement_hub([]) is None


def test_caller_concentration_carries_bootstrap_ci(load_fixture):
    rows = load_fixture("nearblocks_txns.json")["txns"] + load_fixture("nearblocks_txns_p2.json")["txns"]
    c = caller_concentration(rows, "intents.near", [])
    lo, hi = c["hhi_external_ci90"]
    assert 0 < lo <= c["hhi_external"] <= hi <= 10_000 and c["n_eff_external_ci90"] == pytest.approx([10_000 / hi, 10_000 / lo])
    assert c["bootstrap_draws"] == 2000


def test_solver_pages_skipped_after_caller_walk_fails(ledger: ProvenanceLedger, probes_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("valuo.provenance._backoff_delay", lambda *_a, **_k: 0.0)
    base = _router(probes_dir)

    def handler(request: httpx.Request) -> httpx.Response:
        q = dict(request.url.params)
        if request.url.path.endswith("/account/intents.near/txns") and "cursor" in q and "method" not in q:
            return httpx.Response(429, json={"message": "You have exceeded your API request limit."})
        return base(request)

    seen: list[httpx.URL] = []

    def spy(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return handler(request)

    f = _collect(ledger, spy, nearblocks_pages=2, solver_pages=3)
    assert f.pages_fetched == 1 and not any(u.params.get("method") for u in seen)
    assert f.solver_concentration["sample"]["execute_intents_pages_ok"] == 0
    assert "skipped" in (f.solver_concentration["sample"]["execute_intents_pages_skipped_reason"] or "")


# ----------------------------------------------------------------------------- stratified-in-time solver sample
def test_plan_stratum_offsets_even_stride():
    assert forensics.plan_stratum_offsets(6, 21_600) == [0.0, 4320.0, 8640.0, 12960.0, 17280.0, 21600.0]
    assert forensics.plan_stratum_offsets(2, 3600) == [0.0, 3600.0]
    assert forensics.plan_stratum_offsets(1, 3600) == [0.0] and forensics.plan_stratum_offsets(0, 3600) == []


def test_estimate_id_rate_and_cursor_aiming():
    t0 = 1_794_170_000 * 10**9
    pts = [(24_925_000_000 + 45 * s, t0 + s * 10**9) for s in range(0, 60, 3)]
    assert forensics.estimate_id_rate(pts) == pytest.approx(45.0)
    assert forensics.estimate_id_rate([(1, t0), (2, t0)]) is None  # one timestamp: no slope
    assert forensics.estimate_id_rate([(10, t0), (5, t0 + 10**9)]) is None  # ids falling with time: unusable
    assert forensics.cursor_for_offset(24_925_000_000, 45.0, 3600) == 24_925_000_000 - 162_000
    assert forensics.cursor_for_offset(100, 45.0, 1e9) == 1


def test_block_bootstrap_by_page_is_deterministic_and_wider_for_clustered_pages():
    from valuo.collectors.intents_forensics import bootstrap_hhi_ci

    # Two solvers that each own whole pages: unit resampling sees 60 independent fills and a tight CI near 5,000;
    # page resampling sees 6 blocks and must allow one solver to take every drawn page.
    events = [["a"]] * 30 + [["b"]] * 30
    strata = [f"p{1 + i // 10}" for i in range(60)]  # p1-p3 all "a", p4-p6 all "b"
    unit = bootstrap_hhi_ci(events, stream=1)
    block = bootstrap_hhi_ci(events, stream=1, strata=strata)
    assert unit["resampling"] == "unit" and block["resampling"] == "block_by_page" and block["blocks"] == 6
    assert "block bootstrap by page" in block["method"] and "p1, p2, p3, p4, p5, p6" in block["method"]
    assert block["hhi_ci90"][1] - block["hhi_ci90"][0] > 2 * (unit["hhi_ci90"][1] - unit["hhi_ci90"][0])
    assert block["hhi_ci90"][0] <= 5000.0 <= block["hhi_ci90"][1] and block["hhi_point"] == pytest.approx(5000.0)
    assert bootstrap_hhi_ci(events, stream=1, strata=strata) == block  # fixed seed [20261114, 1]
    # One stratum (or none tagged) falls back to unit resampling; a label count mismatch is an error.
    assert bootstrap_hhi_ci(events, stream=1, strata=["p1"] * 60)["resampling"] == "unit"
    with pytest.raises(ValueError):
        bootstrap_hhi_ci(events, strata=["p1"])


def test_solver_audit_is_stratified_in_time(ledger: ProvenanceLedger, probes_dir: Path):
    seen: list[httpx.URL] = []
    f = _collect(ledger, _router(probes_dir, seen=seen), nearblocks_pages=2, solver_pages=6, solver_target_span_s=21_600)
    sc = f.solver_concentration
    sm = sc["sample"]
    assert sm["design"] == "stratified_time_sample" and sm["pages_fetched"] == [1, 2, 3, 4, 5, 6]
    assert sm["execute_intents_pages_ok"] == 6 and sm["execute_intents_page_receipts"] == 300 and sm["target_span_s"] == 21_600
    # p1 newest, p6 aimed at 6 h with the page-1 slope, p2..p5 at even offsets of the depth p6 actually reached.
    offs = [m["offset_from_newest_s"] for m in sm["strata"]]
    reached = offs[-1]
    # The one-page id/time slope is noisy (here it overshoots ~30%); the depth reached is recorded, never assumed.
    assert offs[0] == 0.0 and 0.5 * 21_600 < reached < 2 * 21_600
    for k, off in enumerate(offs):
        assert off == pytest.approx(reached * k / 5, abs=60.0)  # ids are not strictly monotonic in time within a page
    assert sm["stride_s_median"] == pytest.approx(reached / 5, rel=0.01)
    assert sc["sample_span_s"] >= 3600 and sm["span_s"] == sc["sample_span_s"] and sm["span_s"] > reached
    assert 0 < sm["coverage_share"] < 0.05  # six ~45-300 s windows inside ~6 h
    assert all(m["receipts"] == 50 and m["span_s"] > 0 and m["name"] == f"txns:intents.near:execute_intents:p{m['page']}" for m in sm["strata"])
    # call order p1, p6, p2..p5; cursors strictly inside the right region and below page 1
    exec_urls = [u for u in seen if u.params.get("method") == "execute_intents"]
    assert dict(exec_urls[0].params) == {"per_page": "50", "method": "execute_intents", "page": "1"}
    cursors = [int(u.params["cursor"]) for u in exec_urls[1:]]
    assert len(cursors) == 5 and cursors[0] == min(cursors) and cursors[1:] == sorted(cursors[1:], reverse=True)
    p1_ids = sm["strata"][0]["id_range"]
    assert max(cursors) <= p1_ids[0]
    # raw records per page under the old naming
    names = {r.name for r in ledger.records}
    assert {f"txns:intents.near:execute_intents:p{k}" for k in range(1, 7)} <= names
    # page-block bootstrap, reproducible, with the unit bootstrap and per-page HHIs alongside
    assert sc["bootstrap_resampling"] == "block_by_page" and sc["bootstrap_blocks"] >= 2 and "block bootstrap by page" in sc["bootstrap_method"]
    lo, hi = sc["hhi_solver_ci90"]
    assert lo <= sc["hhi_solver"] <= hi and sc["hhi_solver_ci90_unit_bootstrap"] is not None
    assert {s["stratum"] for s in sc["hhi_solver_by_stratum"]} <= {f"p{k}" for k in range(1, 7)}
    assert sum(s["participations"] for s in sc["hhi_solver_by_stratum"]) == sc["n_fills_attributed"]
    again = _collect(ProvenanceLedger(ledger.raw_dir.parent / "again"), _router(probes_dir), nearblocks_pages=2, solver_pages=6, solver_target_span_s=21_600)
    assert again.solver_concentration["hhi_solver_ci90"] == sc["hhi_solver_ci90"]
    # the raw records are untouched: no collector tag leaks into hashed NearBlocks payloads
    raw_files = [p for p in ledger.raw_dir.iterdir() if "execute_intents" in p.name]
    assert len(raw_files) == 6 and all("valuo_stratum" not in p.read_text() for p in raw_files)


def test_solver_strata_survive_a_failed_deep_page(ledger: ProvenanceLedger, probes_dir: Path):
    base = _router(probes_dir)
    n = {"deep": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("method") == "execute_intents" and "cursor" in request.url.params:
            n["deep"] += 1
            if n["deep"] == 3:  # p3 (third cursor call: p6, p2, p3)
                return httpx.Response(404, json={"message": "simulated miss"})
        return base(request)

    f = _collect(ledger, handler, nearblocks_pages=2, solver_pages=6, solver_target_span_s=7200)
    sm = f.solver_concentration["sample"]
    assert sm["pages_fetched"] == [1, 2, 4, 5, 6] and sm["execute_intents_pages_ok"] == 5
    assert any("page 3" in w and "without this stratum" in w for w in f.warnings)
    assert f.solver_concentration["sample_span_s"] >= 3600


def test_solver_sample_falls_back_to_contiguous_without_ids(ledger: ProvenanceLedger, probes_dir: Path):
    base = _router(probes_dir)

    def handler(request: httpx.Request) -> httpx.Response:
        resp = base(request)
        if request.url.params.get("method") == "execute_intents" and "cursor" not in request.url.params:
            body = json.loads(resp.content)
            body["txns"] = [{k: v for k, v in r.items() if k != "id"} for r in body["txns"]]
            return httpx.Response(200, json=body)
        return resp

    f = _collect(ledger, handler, nearblocks_pages=2, solver_pages=3)
    sm = f.solver_concentration["sample"]
    assert sm["design"] == "contiguous_cursor_walk" and sm["pages_fetched"] == [1, 2, 3]
    assert any("falls back to contiguous" in w for w in f.warnings)


def test_solver_walk_paces_in_chunks(ledger: ProvenanceLedger, probes_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """With pacing on, the solver walk sleeps for a full rate window after every NEARBLOCKS_SOLVER_CALLS_PER_CHUNK calls."""
    sleeps: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(s: float):
        sleeps.append(s)
        await real_sleep(0)

    monkeypatch.setattr(forensics.asyncio, "sleep", fake_sleep)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(_router(probes_dir))) as client:
            return await forensics._fetch_solver_strata(
                client, ledger, [], pages=7, per_page=50, delay=0.0, target_span_s=7200, chunk=5, window_s=62.0,
            )

    out = asyncio.run(go())
    assert out["pages_ok"] == 7 and [m["page"] for m in out["strata"]] == [1, 2, 3, 4, 5, 6, 7]
    big = [s for s in sleeps if s > 30]
    assert len(big) == 1 and big[0] == pytest.approx(62.0, abs=1.0) and out["pacing_wait_s"] == pytest.approx(big[0])
