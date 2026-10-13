"""Horizon ids, quarters and today of the roadmap (feature 015, research R2 and R5)."""

from __future__ import annotations

from datetime import date

import pytest

from mobility_model_zoo.site import roadmap


@pytest.mark.parametrize(
    ("hid", "label", "start", "end"),
    [
        ("2026-Q4", "Q4 2026", date(2026, 10, 1), date(2026, 12, 31)),
        ("2027-Q1..Q2", "H1 2027", date(2027, 1, 1), date(2027, 6, 30)),
        ("2027-Q3..Q4", "H2 2027", date(2027, 7, 1), date(2027, 12, 31)),
        ("2027-Q2..Q3", "Q2–Q3 2027", date(2027, 4, 1), date(2027, 9, 30)),
        ("2027-Q4..2028-Q1", "Q4 2027 – Q1 2028", date(2027, 10, 1), date(2028, 3, 31)),
    ],
)
def test_horizon_ids(hid, label, start, end):
    h = roadmap.parse_horizon(hid)
    assert (h.label, h.start, h.end) == (label, start, end)


def test_months():
    assert roadmap.parse_horizon("2026-Q4").months == "October – December"


@pytest.mark.parametrize(
    "hid", ["2027-Q2..Q4", "2027-Q3..2028-Q1", "2027-Q5", "2027-Q1..2028-Q1", "Q4 2026", ""]
)
def test_rejected_horizon_ids(hid):
    with pytest.raises(ValueError):
        roadmap.parse_horizon(hid)


def test_quarters():
    assert roadmap.quarter_of(date(2026, 12, 31)) == "2026-Q4"
    assert roadmap.quarter_of(date(2027, 1, 1)) == "2027-Q1"
    assert roadmap.quarters_between("2026-Q3", "2027-Q1") == ["2026-Q3", "2026-Q4", "2027-Q1"]
    assert roadmap.quarters_between("2027-Q1", "2026-Q4") == []


def test_today(monkeypatch):
    monkeypatch.setenv("ZOO_TODAY", "2027-01-05")
    assert roadmap.today() == date(2027, 1, 5)
    monkeypatch.delenv("ZOO_TODAY")
    assert isinstance(roadmap.today(), date)
