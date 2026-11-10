"""bull_case: every condition graded from snapshot fields; statuses follow the rules; nulls stay not_measured."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from valuo.models.bull_case import AGAINST, BEHIND, NOT_MEASURED, ON_TRACK, run_bull_case

SNAP = json.loads((Path(__file__).resolve().parents[2] / "artifacts" / "latest_snapshot.json").read_text())


def _by_key(out):
    return {c["key"]: c for c in out["conditions"]}


def test_runs_on_committed_snapshot():
    out = run_bull_case(SNAP)
    assert out["n_conditions"] == 8 and sum(out["counts"].values()) == 8
    assert out["headline"].startswith("The long-term case for NEAR")
    for c in out["conditions"]:
        assert c["status"] in (ON_TRACK, BEHIND, AGAINST, NOT_MEASURED)


def test_status_rules():
    s = copy.deepcopy(SNAP)
    for solve in s["market_implied"]["solves"]:
        if solve["param"] == "public_volume_growth_yoy":
            solve["required_value"], solve["evidence"]["value"] = 0.5, 0.6
    s["intents_forensics"]["solver_concentration"]["hhi_solver"] = 9000.0
    s["intents_forensics"]["solver_concentration"]["hhi_solver_ci90"] = [8000.0, 9500.0]
    c = _by_key(run_bull_case(s))
    assert c["volume_growth"]["status"] == ON_TRACK
    assert c["solver_competition"]["status"] == AGAINST   # whole CI above the threshold


def test_missing_inputs_are_not_measured():
    s = copy.deepcopy(SNAP)
    s["market_implied"] = None
    s["execution_bench"] = None
    c = _by_key(run_bull_case(s))
    assert c["volume_growth"]["status"] == NOT_MEASURED and c["pricing_power"]["status"] == NOT_MEASURED


def test_trend_uses_real_series_windows():
    out = _by_key(run_bull_case(SNAP))
    tr = out["volume_growth"]["trend"]
    series = SNAP["intents_forensics"]["fees"]["daily_series"]
    assert tr is not None and tr["now"] == sum(r[3] for r in series[-30:])
    assert tr["then"] == sum(r[3] for r in series[-120:-90])
