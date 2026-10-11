"""State machine (feature 009 data-model.md, FR-016, FR-018, T037)."""

from __future__ import annotations

import copy

import pytest

from mobility_model_zoo.catalog import states
from mobility_model_zoo.catalog.model import load

DAY = "2026-10-11"


@pytest.fixture
def cat(catalog_dir):
    return load(catalog_dir)


def _e(cat, eid):
    return copy.deepcopy(cat.entries[eid])


def test_candidate_needs_network_checks_and_no_fail(cat):
    e = _e(cat, "pl-stat-transport-tables")
    e["status"] = {"value": "candidate", "since": DAY}
    e["checks"] = [{"check": "K1", "result": "pass", "at": DAY}]
    assert states.transition(e, DAY) == "candidate"
    e["checks"] += [
        {"check": "K4", "result": "fail", "at": DAY},
        {"check": "K6", "result": "pass", "at": DAY},
    ]
    assert states.transition(e, DAY) == "candidate"
    e["checks"][1]["result"] = "pass"
    assert states.transition(e, DAY) == "cleared"  # verified, then every clearing condition holds


@pytest.mark.parametrize(
    "eid,blocker",
    [
        ("jp-gtfs-feeds", "no free access route"),  # auth: account
        ("es-parlamento-comision-transportes", "no free access route"),  # streaming platform
        ("fr-charts-mobilite", "permitted use is undetermined"),
        ("pl-radio-transport", "opt-out signal: robots"),
    ],
)
def test_clear_blockers(cat, eid, blocker):
    e = _e(cat, eid)
    assert any(b.startswith(blocker) for b in states.clear_blockers(e))
    assert states.transition(e, DAY) == "verified"


def test_api_key_route_clears_but_account_does_not(cat):
    e = _e(cat, "jp-gtfs-feeds")
    e["access"][0]["auth"] = "api_key"
    assert states.clear_blockers(e) == []


def test_blocking_flags(cat):
    e = _e(cat, "pl-stat-transport-tables")
    for flag in ("unreachable", "personal_data_in_metadata", "owner_decision_needed"):
        states.set_flag(e, flag)
        assert states.clear_blockers(e) == [f"flags: {flag}"]
        states.set_flag(e, flag, False)


def test_cleared_falls_back_when_the_recheck_changed(cat):
    e = _e(cat, "pl-stat-transport-tables")
    assert states.transition(e, DAY, ["evidence"]) == "verified"
    assert "licence_changed" in states.flags(e) and "evidence" in e["status"]["reason"]


def test_cleared_falls_back_on_a_failed_check(cat):
    e = _e(cat, "pl-stat-transport-tables")
    e["checks"][3]["result"] = "fail"  # K4
    assert states.transition(e, DAY) == "verified"


def test_retired_after_three_gone_answers_seven_days_apart(cat):
    e = _e(cat, "pl-stat-transport-tables")
    k4 = next(c for c in e["checks"] if c["check"] == "K4")
    k4["result"] = "fail"
    k4["previous"] = {"gone_dates": ["2026-09-01", "2026-09-03", "2026-09-20"]}
    assert states.transition(e, DAY) == "verified"  # only two dates ≥ 7 days apart
    k4["previous"]["gone_dates"].append("2026-10-01")
    assert states.transition(e, DAY) == "retired" and e["status"]["reason"]


def test_terminal_states_need_reasons_and_stay(cat):
    from mobility_model_zoo.catalog.validate import k1

    e = _e(cat, "pl-stat-transport-tables")
    states.set_status(e, "rejected", DAY, None)
    assert any("reason" in f.field or "reason" in f.message for f in k1(e))
    states.set_status(e, "withdrawn", DAY, "objection")
    assert any("request_id" in f.message for f in k1(e))
    states.set_status(e, "withdrawn", DAY, "objection", request_id="REQ-1")
    assert not k1(e)
    assert states.transition(e, DAY) == "withdrawn"
