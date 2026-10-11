"""Re-checks keep the index current (feature 009 US5, FR-020, T067)."""

from __future__ import annotations

import httpx
from catalog_http import Web

from mobility_model_zoo.catalog import checks
from mobility_model_zoo.catalog.model import load


def _run(catalog_dir, web, ids, today=None):
    import datetime as dt

    return checks.run(
        load(catalog_dir),
        ids=ids,
        transport=httpx.MockTransport(web),
        throttle=checks.Throttle(sleep=lambda s: None),
        say=lambda m: None,
        today=today or dt.date(2026, 10, 11),
    )


def test_changed_evidence_revokes_clearing_and_keeps_the_previous_hash(catalog_dir):
    _run(catalog_dir, Web(licence_body="CC BY 4.0"), ["pl-stat-transport-tables"])
    _run(catalog_dir, Web(licence_body="changed"), ["pl-stat-transport-tables"])
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    k5 = next(c for c in e["checks"] if c["check"] == "K5")
    assert e["status"]["value"] == "verified" and "licence_changed" in e["status"]["flags"]
    assert k5["previous"]["before"] and k5["previous"]["licence_id"] == "CC-BY-4.0"


def test_unreachable_landing_page_is_flagged_and_not_fetchable(catalog_dir):
    from mobility_model_zoo.catalog import fetchlist

    _run(catalog_dir, Web(status={"/pl-stat-transport-tables": 503}), ["pl-stat-transport-tables"])
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert "unreachable" in e["status"]["flags"] and e["status"]["value"] == "verified"
    assert fetchlist.build(load(catalog_dir), [e], "x", "x", "2026-10-11")["items"] == []


def test_three_gone_answers_retire_the_entry(catalog_dir):
    import datetime as dt

    gone = Web(status={"/pl-stat-transport-tables": 410})
    for day in (dt.date(2026, 10, 1), dt.date(2026, 10, 9), dt.date(2026, 10, 17)):
        _run(catalog_dir, gone, ["pl-stat-transport-tables"], today=day)
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert e["status"]["value"] == "retired" and "404/410" in e["status"]["reason"]
