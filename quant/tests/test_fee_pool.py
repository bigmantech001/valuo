"""Fee-pool share (valuo.collectors.fee_pool): share arithmetic, common window, provisional tail, failed slugs, trend, claim."""
from __future__ import annotations

import asyncio
import math
import random
from datetime import date, timedelta
from typing import Any

import httpx
import pytest

from valuo.collectors.fee_pool import (
    FOCUS_SLUG, HAC_LAG_DAYS, PROTOCOLS, ROLLING_DAYS, build_fee_pool, collect_fee_pool, fees_methodology, memo_markdown,
    parse_daily_fees, scorecard_claim,
)
from valuo.provenance import ProvenanceLedger

DAY = 86400
D0 = 20000  # days since epoch of the first synthetic day (2024-10-04)
AS_OF = date(1970, 1, 1) + timedelta(days=D0 + 400)  # "today", far after every synthetic series
LEVELS = {"near-intents": 200.0, "relay": 400.0, "across": 10.0, "debridge": 40.0, "chainflip": 100.0, "thorchain-dex": 50.0}


def _iso(day: int) -> str:
    return (date(1970, 1, 1) + timedelta(days=day)).isoformat()


def _payload(values: list[float], start: int = D0, name: str | None = None, provisional: float | None = 1.0, **extra: Any) -> dict[str, Any]:
    """A DefiLlama-shaped summary. ``provisional`` appends one newest point (the collector treats it as not final)."""
    vals = list(values) + ([provisional] if provisional is not None else [])
    out = {"name": name, "total30d": sum(values[-30:]), "totalDataChart": [[(start + i) * DAY, v] for i, v in enumerate(vals)],
           "methodology": {"Fees": f"fees as {name} defines them"}}
    out.update(extra)
    return out


def _flat(n: int = 200, **override: list[float]) -> dict[str, Any]:
    return {slug: _payload(override.get(slug.replace("-", "_"), [LEVELS[slug]] * n), name=slug.upper()) for slug in LEVELS}


def test_share_arithmetic_rank_and_window_sums():
    out = build_fee_pool(_flat(), as_of=AS_OF)
    assert out["status"] == "measured" and out["included"] == [p.slug for p in PROTOCOLS] and out["unavailable"] == []
    assert out["pool_label"] == "six-protocol" and out["pool_30d_usd"] == pytest.approx(800.0 * 30)
    by = {p["slug"]: p for p in out["protocols"]}
    assert by[FOCUS_SLUG]["fees_30d_usd"] == pytest.approx(6000.0) and by[FOCUS_SLUG]["fees_90d_usd"] == pytest.approx(18000.0)
    assert by[FOCUS_SLUG]["share_30d"] == pytest.approx(0.25) and by["relay"]["share_30d"] == pytest.approx(0.5)
    assert sum(p["share_30d"] for p in out["protocols"]) == pytest.approx(1.0)
    assert [p["slug"] for p in out["protocols"]][:3] == ["relay", "near-intents", "chainflip"]
    assert out["rank"]["near_intents"] == 2 and out["rank"]["of"] == 6
    assert out["rank"]["reference"]["slug"] == "relay" and out["rank"]["reference"]["relation"] == "behind"
    # rolling table: one row per window day from the 30th on, each row's shares consistent with its fee columns
    cols, rows = out["rolling"]["columns"], out["rolling"]["rows"]
    assert cols[:4] == ["date", "share", "share_ex_relay", "pool_30d_usd"] and cols[4:] == out["included"]
    assert len(rows) == out["window"]["n_days"] - ROLLING_DAYS + 1 == 171
    for row in (rows[0], rows[-1]):
        rec = dict(zip(cols, row))
        assert rec["pool_30d_usd"] == pytest.approx(sum(rec[s] for s in out["included"]))
        assert rec["share"] == pytest.approx(rec[FOCUS_SLUG] / rec["pool_30d_usd"], abs=1e-6)
        assert rec["share_ex_relay"] == pytest.approx(rec[FOCUS_SLUG] / (rec["pool_30d_usd"] - rec["relay"]), abs=1e-6) == pytest.approx(0.5)
    sh = out["share"]
    assert sh["now"]["share"] == sh["d30_ago"]["share"] == sh["d90_ago"]["share"] == sh["window_start"]["share"] == pytest.approx(0.25)
    assert sh["change_pp_30d"] == pytest.approx(0.0) and sh["days_start_to_now"] == 170
    assert out["share_ex_relay"]["now"]["share"] == pytest.approx(0.5)
    # a constant share has no trend and the claim is not supported
    assert out["trend"]["direction"] == "flat" and out["trend"]["excludes_zero"] is False
    assert scorecard_claim(out)["status"] == "NOT_SUPPORTED"
    assert "25.0%" in out["headline"] and "rank 2 of 6 behind RELAY at 50.0%" in out["headline"]


def test_common_window_is_set_by_the_shortest_series():
    charts = _flat(200)
    charts["relay"] = _payload([400.0] * 80, start=D0 + 120, name="Relay")  # Relay only has the last 80 days
    out = build_fee_pool(charts, as_of=AS_OF)
    w = out["window"]
    assert w["start"] == _iso(D0 + 120) and w["end"] == _iso(D0 + 199) and w["n_days"] == 80 and w["limited_by"] == "relay"
    assert len(out["rolling"]["rows"]) == 51 and out["rolling"]["rows"][0][0] == _iso(D0 + 149)
    by = {p["slug"]: p for p in out["protocols"]}
    assert by["relay"]["n_days"] == 80 and by[FOCUS_SLUG]["n_days"] == 200 and by[FOCUS_SLUG]["fees_90d_usd"] is None
    assert out["share"]["d90_ago"] is None and out["share"]["change_pp_90d"] is None and out["share"]["d30_ago"] is not None
    assert out["trend"]["status"] == "insufficient_data"  # 51 rolling points < 60
    assert "80 days" in " ".join(out["caveats"])


def test_window_shorter_than_the_rolling_window_is_insufficient():
    charts = _flat(200)
    charts["relay"] = _payload([400.0] * 20, start=D0 + 180, name="Relay")
    out = build_fee_pool(charts, as_of=AS_OF)
    assert out["status"] == "insufficient_data" and out["window"]["n_days"] == 20 and out["share"] is None
    assert scorecard_claim(out)["status"] == "NOT_SUPPORTED" and "Not measured" in memo_markdown(out, {})


def test_provisional_newest_points_and_today_are_left_out():
    n = 120
    charts = _flat(n)  # every series has a provisional point on day D0+n
    # NEAR Intents lags one day: its newest (partial) point is day n-1; Relay already shows "today" = day n
    charts["near-intents"] = _payload([200.0] * (n - 1), name="NEAR Intents", provisional=3.0)
    out = build_fee_pool(charts, as_of=date(1970, 1, 1) + timedelta(days=D0 + n))
    w = out["window"]
    assert w["end"] == _iso(D0 + n - 2) and w["n_days"] == n - 1
    excluded = {e["date"]: e["reason"] for e in w["excluded_trailing_days"]}
    assert set(excluded) == {_iso(D0 + n - 1), _iso(D0 + n)}
    assert "provisional newest point of near-intents" in excluded[_iso(D0 + n - 1)]
    assert "dated today" in excluded[_iso(D0 + n)] and "not yet published for near-intents" in excluded[_iso(D0 + n)]
    assert out["share"]["now"]["share"] == pytest.approx(0.25)  # the partial 3.0 never enters a sum
    assert out["share"]["now"]["date"] == _iso(D0 + n - 2)


def test_trailing_zero_day_for_one_protocol_ends_the_window_earlier():
    n = 120
    charts = _flat(n, chainflip=[100.0] * (n - 2) + [0.0, 0.0])
    out = build_fee_pool(charts, as_of=AS_OF)
    w = out["window"]
    assert w["end"] == _iso(D0 + n - 3) and w["n_days"] == n - 2
    reasons = {e["date"]: e["reason"] for e in w["excluded_trailing_days"]}
    assert reasons[_iso(D0 + n - 1)] == reasons[_iso(D0 + n - 2)] == "zero or missing for chainflip"
    assert out["share"]["now"]["share"] == pytest.approx(0.25)


def test_failed_slug_is_listed_and_the_share_uses_the_rest():
    charts = _flat()
    del charts["across"]
    charts["debridge"] = None
    out = build_fee_pool(charts, failures={"across": "fetch failed (HTTP 404)"}, as_of=AS_OF)
    assert out["status"] == "measured" and out["included"] == ["near-intents", "relay", "chainflip", "thorchain-dex"]
    assert {u["slug"]: u["reason"] for u in out["unavailable"]} == {"across": "fetch failed (HTTP 404)", "debridge": "no payload"}
    assert out["pool_label"] == "four-protocol" and out["share"]["now"]["share"] == pytest.approx(200.0 / 750.0)
    assert out["rank"]["of"] == 4 and "four-protocol" in out["headline"]
    assert any("Left out of this run" in c and "Across" in c for c in out["caveats"])
    assert any("across left out" in w for w in out["warnings"])


def test_missing_near_intents_or_no_competitor_is_unavailable():
    charts = _flat()
    del charts[FOCUS_SLUG]
    out = build_fee_pool(charts, as_of=AS_OF)
    assert out["status"] == "unavailable" and out["share"] is None and out["protocols"] == []
    claim = scorecard_claim(out)
    assert claim["status"] == "NOT_SUPPORTED" and claim["value"].startswith("not measured")
    assert memo_markdown(out, {}).startswith("Not measured")
    only_ni = build_fee_pool({FOCUS_SLUG: _flat()[FOCUS_SLUG]}, as_of=AS_OF)
    assert only_ni["status"] == "unavailable" and len(only_ni["unavailable"]) == 5
    assert scorecard_claim(None) is None


def test_stale_series_is_left_out_instead_of_shortening_the_window():
    charts = _flat(200)
    charts["thorchain-dex"] = _payload([50.0] * 170, name="THORChain DEX")  # stops 30 days before the others
    out = build_fee_pool(charts, as_of=AS_OF)
    assert "thorchain-dex" not in out["included"] and out["window"]["end"] == _iso(D0 + 199)
    assert out["unavailable"][0]["slug"] == "thorchain-dex" and out["unavailable"][0]["reason"].startswith("stale")


def _trending(slope_per_day: float, noise: float, n: int = 220) -> dict[str, Any]:
    rng = random.Random(20261114)
    ni = [max(200.0 + slope_per_day * d + rng.gauss(0.0, noise), 1.0) for d in range(n)]
    return _flat(n, near_intents=ni)


def test_rising_share_gives_a_positive_trend_and_a_derived_claim():
    out = build_fee_pool(_trending(1.0, 20.0), as_of=AS_OF)
    tr = out["trend"]
    lo, hi = tr["ci90_pp_per_30d"]
    assert tr["status"] == "measured" and tr["hac_lag_days"] == HAC_LAG_DAYS and tr["n_points"] == 191
    assert tr["slope_pp_per_30d"] > 0 and 0 < lo < tr["slope_pp_per_30d"] < hi and tr["direction"] == "rising" and tr["excludes_zero"]
    # slope is close to the endpoint change spread over the window
    per_30d = out["share"]["change_pp_window"] / (out["share"]["days_start_to_now"] / 30.0)
    assert tr["slope_pp_per_30d"] == pytest.approx(per_30d, rel=0.15)
    assert out["share"]["now"]["share"] > out["share"]["d30_ago"]["share"] > out["share"]["d90_ago"]["share"] > out["share"]["window_start"]["share"]
    assert out["trend_daily_cross_check"]["direction"] == "rising" and out["trend_ex_relay"]["direction"] == "rising"
    claim = scorecard_claim(out)
    assert claim["status"] == "DERIVED" and claim["confidence"] == "medium" and "pp per 30 days" in claim["value"]
    assert set(claim) == {"claim", "status", "value", "source", "confidence", "note"}
    assert "Supports the bull case" in out["read"]


def test_falling_share_is_reported_as_such_and_not_supported():
    out = build_fee_pool(_trending(-0.6, 20.0), as_of=AS_OF)
    tr = out["trend"]
    assert tr["direction"] == "falling" and tr["ci90_pp_per_30d"][1] < 0
    claim = scorecard_claim(out)
    assert claim["status"] == "NOT_SUPPORTED" and claim["value"].endswith("(share is falling)")
    assert "Cuts against the bull case" in out["read"] and "falling" in out["headline"]


def test_oscillating_share_is_not_distinguishable_from_flat():
    n = 220
    ni = [200.0 + 60.0 * math.sin(2 * math.pi * d / 95.0) for d in range(n)]
    out = build_fee_pool(_flat(n, near_intents=ni), as_of=AS_OF)
    tr = out["trend"]
    lo, hi = tr["ci90_pp_per_30d"]
    assert tr["status"] == "measured" and lo < 0 < hi and tr["direction"] == "flat" and not tr["excludes_zero"]
    assert scorecard_claim(out)["status"] == "NOT_SUPPORTED" and "not distinguishable from flat" in out["headline"]
    assert scorecard_claim(out)["value"].endswith("(share gain not shown)")


def test_zero_run_and_surge_are_flagged_with_a_robustness_share():
    n = 200
    thor = [50.0] * 40 + [0.0] * 20 + [50.0] * (n - 60)
    relay = [400.0] * 100 + [20000.0] * 20 + [400.0] * (n - 120)
    out = build_fee_pool(_flat(n, thorchain_dex=thor, relay=relay), as_of=AS_OF)
    by = {p["slug"]: p for p in out["protocols"]}
    assert by["thorchain-dex"]["zero_days_in_window"] == 20 and by["thorchain-dex"]["longest_zero_run_days"] == 20
    assert by["thorchain-dex"]["zero_run_start"] == _iso(D0 + 40) and by["thorchain-dex"]["zero_run_end"] == _iso(D0 + 59)
    keys = {r["key"]: r for r in out["robustness"]}
    assert set(keys) == {"ex_relay", "ex_zero_run"} and keys["ex_zero_run"]["excluded"] == ["thorchain-dex"]
    assert keys["ex_zero_run"]["share_now"] == pytest.approx(200.0 / 750.0) and keys["ex_relay"]["share_now"] == pytest.approx(0.5)
    text = " ".join(out["caveats"])
    assert "reports zero fees on 20 days" in text and "RELAY's 30-day fees peaked" in text
    assert out["share"]["low"]["share"] < 0.02 < 0.25 <= out["share"]["high"]["share"]


def test_parse_skips_malformed_negative_and_duplicate_rows():
    payload = {"totalDataChart": [[D0 * DAY, 5.0], [(D0 + 1) * DAY, None], [(D0 + 2) * DAY, -3.0], ["x", 1.0], [1.0], "row",
                                  [(D0 + 3) * DAY, float("nan")], [(D0 + 4) * DAY, True], [(D0 + 5) * DAY + 3600, 7.0], [(D0 + 5) * DAY, 9.0]]}
    days, skipped = parse_daily_fees(payload)
    assert days == {D0: 5.0, D0 + 5: 9.0} and skipped == 8
    assert parse_daily_fees({"totalDataChart": "nope"}) == ({}, 0) and parse_daily_fees(None) == ({}, 0)
    charts = _flat()
    charts["across"]["totalDataChart"].append([(D0 + 50) * DAY, -1.0])
    out = build_fee_pool(charts, as_of=AS_OF)
    assert any("across: 1 malformed" in w for w in out["warnings"])  # the negative row is skipped, the day keeps its value


def test_methodology_falls_back_to_child_protocols():
    assert fees_methodology({"methodology": {"Fees": " gross fees "}}) == "gross fees"
    parent = {"methodology": None, "childProtocols": [{"displayName": "Chainflip AMM", "methodology": {"Fees": "swap fees"}}, {"name": "x"}, 7]}
    assert fees_methodology(parent) == "Chainflip AMM: swap fees"
    assert fees_methodology({"methodology": {"Revenue": "r"}}) is None and fees_methodology([]) is None
    out = build_fee_pool({**_flat(), "chainflip": _payload([100.0] * 200, name="Chainflip", methodology=None, childProtocols=parent["childProtocols"])}, as_of=AS_OF)
    assert {p["slug"]: p["methodology_fees"] for p in out["protocols"]}["chainflip"] == "Chainflip AMM: swap fees"


def test_memo_has_headline_table_readout_and_limits():
    out = build_fee_pool(_trending(1.0, 20.0), as_of=AS_OF)
    md = memo_markdown(out, {})
    assert md.startswith(f"**{out['headline']}**")
    assert "| Rank | Protocol | 30d fees | Share |" in md and "**NEAR-INTENTS**" in md and "fees as RELAY defines them" in md
    assert "| Relay excluded |" in md and "Trend of the rolling share:" in md and "Limits:" in md
    assert all(f"- {c}" in md for c in out["caveats"])
    for banned in ("—", "seamless", "unlock", "revolution", "delve"):
        assert banned not in md and banned not in out["headline"] and banned not in out["read"]


def test_output_is_deterministic():
    a, b = build_fee_pool(_trending(0.4, 30.0), as_of=AS_OF), build_fee_pool(_trending(0.4, 30.0), as_of=AS_OF)
    assert a == b


def test_collector_records_every_fetch_and_survives_a_failed_slug(tmp_path):
    n = 150
    today = date.today()  # the collector uses the real clock; build the series to end yesterday (UTC drift of a day is harmless here)
    start = (today - date(1970, 1, 1)).days - n
    payloads = {slug: _payload([LEVELS[slug]] * n, start=start, name=slug.upper()) for slug in LEVELS}
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        slug = request.url.path.rsplit("/", 1)[-1]
        seen.append(f"{slug}?{request.url.query.decode()}")
        if slug == "across":
            return httpx.Response(404, json={"message": "Fees for across not found"})
        return httpx.Response(200, json=payloads[slug])

    ledger = ProvenanceLedger(raw_dir=tmp_path / "raw")
    logs: list[str] = []

    async def run() -> dict[str, Any] | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await collect_fee_pool(client, ledger, None, logs.append, {})

    out = asyncio.run(run())
    assert out is not None and out["status"] == "measured"
    assert sorted(seen) == sorted(f"{slug}?dataType=dailyFees" for slug in LEVELS)
    assert {r.name for r in ledger.records} == {f"fee_pool:{slug}:dailyFees" for slug in LEVELS} and all(r.source == "defillama" for r in ledger.records)
    assert [u["slug"] for u in out["unavailable"]] == ["across"] and "fetch failed" in out["unavailable"][0]["reason"]
    assert any(w.startswith("fee_pool: across left out") for w in ledger.warnings)
    by = {p["slug"]: p for p in out["protocols"]}
    rec = ledger.get("defillama", "fee_pool:near-intents:dailyFees")
    assert by[FOCUS_SLUG]["sha256"] == rec.sha256 and by[FOCUS_SLUG]["record"] == "defillama/fee_pool:near-intents:dailyFees"
    assert out["share"]["now"]["share"] == pytest.approx(200.0 / 790.0) and out["fetched_at_utc"].endswith("Z")
    assert logs and "5 of 6 protocols" in logs[0]
