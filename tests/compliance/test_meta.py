"""Meta stage: schema validity, overdue reviews, expired waivers, overdue requests (C-M1…C-M4)."""

import datetime as dt

from compliance_helpers import TODAY, load, seed, write

from mobility_model_zoo.compliance.checks import Context, stage_meta


def ids(root, today=TODAY):
    return {f.check_id for f in stage_meta(Context(load(root, today)))}


def test_clean_register_passes(register_tree):
    assert stage_meta(Context(load(register_tree))) == []


def test_missing_controller_fails(register_tree):
    (register_tree / "compliance/controller.yaml").unlink()
    assert ids(register_tree) == {"C-M1"}


def test_schema_violation(register_tree):
    seed(register_tree, "topics/t/compliance/sources.yaml", lambda d: d["sources"][0].pop("licence"))
    assert ids(register_tree) == {"C-M1"}


def test_overdue_review(register_tree):
    assert ids(register_tree, dt.date(2027, 4, 9)) == {"C-M2"}


def test_legal_watch_unreviewed(register_tree):
    write(
        register_tree,
        "compliance/legal-watch.yaml",
        {
            "items": [
                {
                    "id": "bgh",
                    "title": "BGH I ZR 281/25",
                    "kind": "court",
                    "expected": "2026-12-17",
                    "review_by": "2026-10-07",
                    "reviewed_at": None,
                    "outcome": None,
                    "affects": ["D6"],
                }
            ]
        },
    )
    assert ids(register_tree) == {"C-M2"}


def test_expired_and_overlong_waivers(register_tree):
    w = {"id": "w", "check": "C-I1", "scope": "s", "rationale": "r", "approved_by": "o"}
    write(
        register_tree,
        "compliance/waivers.yaml",
        {"waivers": [{**w, "approved_at": "2026-01-01", "expires_at": "2026-10-01"}]},
    )
    assert ids(register_tree) == {"C-M3"}
    write(
        register_tree,
        "compliance/waivers.yaml",
        {"waivers": [{**w, "approved_at": "2026-10-01", "expires_at": "2027-09-01"}]},
    )
    assert ids(register_tree) == {"C-M3"}


def test_open_request_past_deadline(register_tree):
    write(
        register_tree,
        "compliance/requests.yaml",
        {
            "requests": [
                {
                    "id": "r1",
                    "type": "objection",
                    "received_at": "2026-09-01",
                    "deadline": "2026-10-01",
                    "identifier_hash": "a" * 64,
                    "stores_searched": [],
                    "action": "",
                    "suppression_added": False,
                    "answered_at": None,
                }
            ]
        },
    )
    assert ids(register_tree) == {"C-M4"}
