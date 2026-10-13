"""The pace review (feature 015, US4; research R6, contracts/pace-report.md) on a constructed quarter:
one entry delivered on time, one moved, one dropped, one unplanned release."""

from __future__ import annotations

from datetime import date

import pytest

from mobility_model_zoo.release.errors import UsageError
from mobility_model_zoo.site import pace, roadmap

RECORD = "zoo/roadmap/roadmap.yaml"
TODAY = date(2027, 1, 5)


def publish(env, model, version, when):
    path = env.root / "zoo" / "models" / model / "releases" / f"{version}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"model: {model}\nversion: {version}\ndate: {when[:10]}\nstatus: experimental\n"
        f"published:\n  tag: v{version}\n  published_at: {when}\n",
        encoding="utf-8",
    )


@pytest.fixture
def quarter(site_env):
    publish(site_env, "picket-forest", "0.1.0", "2026-11-20T10:00:00Z")  # first release, on time
    publish(
        site_env, "scout-large", "0.1.3", "2026-12-01T09:00:00Z"
    )  # unplanned, like 0.1.2 of the fixture

    def plan(r):
        for e in r["entries"]:
            if e["id"] == "scout-large-reader-test":
                e["horizon"] = "2027-Q1..Q2"
                e["moves"] = [{"date": "2026-12-15", "to": "2027-Q1..Q2", "reason": "No readers yet."}]
            if e["id"] == "picket-signal":
                e["dropped"] = {"date": "2026-11-02", "reason": "Covered by picket-forest."}

    site_env.edit_yaml(RECORD, plan)
    return site_env


def make(env, q="2026-Q4", **kwargs):
    return pace.report(env.reg, roadmap.load(env.reg), q, TODAY, **kwargs)


def test_summary(quarter):
    s = make(quarter)["summary"]
    assert (s["releases"], s["delivered"], s["early"], s["on_time"], s["late"]) == (3, 1, 0, 1, 0)
    assert (s["due"], s["due_done"]) == (2, 1)  # picket-forest and the reader test were due in Q4
    assert (s["moved"], s["dropped"], s["unplanned"]) == (1, 1, 2)


def test_sections(quarter):
    r = make(quarter)
    assert r["delivered"] == [
        {
            "id": "picket-forest",
            "kind": "first-release",
            "planned": "Q4 2026",
            "date": date(2026, 11, 20),
            "release": "picket-forest 0.1.0",
            "timing": "on time",
            "slip": "",
        }
    ]
    assert r["missed"] == [
        {
            "id": "scout-large-reader-test",
            "planned": "Q4 2026",
            "now": "H1 2027",
            "moves": "2026-12-15: No readers yet.",
        }
    ]
    assert r["moved"][0] == {
        "id": "scout-large-reader-test",
        "from": "Q4 2026",
        "to": "H1 2027",
        "date": "2026-12-15",
        "reason": "No readers yet.",
    }
    assert [d["id"] for d in r["dropped"]] == ["picket-signal"]
    assert r["unplanned"] == [
        {"release": "scout-large 0.1.2", "date": date(2026, 10, 8), "note": ""},
        {"release": "scout-large 0.1.3", "date": date(2026, 12, 1), "note": ""},
    ]
    assert [t["quarter"] for t in r["trend"]] == ["Q4 2026"]


def test_late_delivery_in_the_next_quarter(quarter):
    def late(r):
        for e in r["entries"]:
            if e["id"] == "scout-large-reader-test":
                e["delivered_by"] = {"model": "scout-large", "version": "0.1.4"}

    publish(quarter, "scout-large", "0.1.4", "2027-02-10T09:00:00Z")
    quarter.edit_yaml(RECORD, late)
    r = pace.report(quarter.reg, roadmap.load(quarter.reg), "2027-Q1", date(2027, 4, 2))
    assert [(d["id"], d["timing"], d["slip"]) for d in r["delivered"]] == [
        ("scout-large-reader-test", "late", "41 d, 1 q")
    ]
    assert [t["quarter"] for t in r["trend"]] == ["Q4 2026", "Q1 2027"]


def test_markdown(quarter):
    text = pace.render_markdown(make(quarter))
    assert text.startswith("# Pace review Q4 2026\n")
    assert "| Delivery rate | 1 of 2 entries due this quarter |" in text
    assert (
        "| picket-forest | first-release | Q4 2026 | 2026-11-20 | picket-forest 0.1.0 | on time |  |"
        in text
    )
    assert "## Unplanned releases" in text and "scout-large 0.1.3" in text


def test_empty_tables_say_none(site_env):
    text = pace.render_markdown(make(site_env))
    assert "## Moved this quarter\n\nNone." in text and "## Dropped this quarter\n\nNone." in text


def test_open_quarter_is_refused(site_env):
    with pytest.raises(UsageError, match="has not ended yet"):
        pace.report(site_env.reg, roadmap.load(site_env.reg), "2026-Q4", date(2026, 12, 1))
    assert make(site_env, "2027-Q1", draft=True)["draft"]


def test_write_keeps_the_replanning(quarter):
    path = pace.write(quarter.reg, "2026-Q4", pace.render_markdown(make(quarter)))
    text = path.read_text()
    assert text.count(roadmap.REPLANNING) == 1 and roadmap.REPLANNING_PLACEHOLDER in text
    assert roadmap.review_errors(path) == f"{roadmap.REPLANNING!r} is empty"
    path.write_text(text.replace(roadmap.REPLANNING_PLACEHOLDER, "We keep five entries in Q1."))
    path2 = pace.write(quarter.reg, "2026-Q4", "# Pace review Q4 2026\n\nNew numbers.\n")
    again = path2.read_text()
    assert "New numbers." in again and "We keep five entries in Q1." in again
    assert roadmap.review_errors(path2) is None
