"""Pace review of a closed quarter (feature 015, US4; constitution 2.3.0, "Roadmap and Delivery
Pace"). Definitions in specs/015-website-roadmap/research.md R6, layout in contracts/pace-report.md.

Everything is computed from the current roadmap record and the release records. The record keeps
each entry's first planned horizon and dates every move and drop, so later edits do not change the
result for an earlier quarter.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.errors import UsageError
from mobility_model_zoo.release.registry import Registry, parse_version
from mobility_model_zoo.site import roadmap
from mobility_model_zoo.site.context import is_sandbox


def _releases(reg: Registry) -> list[tuple[str, str, date]]:
    """Every published, non-sandbox release: (model, version, publication date)."""
    out = []
    for name in reg.model_names():
        if is_sandbox(reg, name):
            continue
        for version in reg.published_versions(name):
            day = roadmap._published_on(reg, name, version)
            if day:
                out.append((name, version, day))
    return sorted(out, key=lambda r: (r[2], r[0], parse_version(r[1])))


def _within(day: date | None, start: date, end: date) -> bool:
    return day is not None and start <= day <= end


def _counts(reg: Registry, record: dict[str, Any], quarter: str) -> dict[str, Any]:
    start, end = roadmap.quarter_span(quarter)
    delivered, due, due_done, late = [], [], 0, 0
    for e in record["entries"]:
        day = roadmap.delivery_date(reg, e)
        if _within(day, start, end):
            delivered.append(e)
            if roadmap.timing(e, day)[0] == "late":
                late += 1
        if _within(roadmap.parse_horizon(e["planned"]).end, start, end):
            due.append(e)
            if day is not None and day <= end:
                due_done += 1
    releases = [r for r in _releases(reg) if _within(r[2], start, end)]
    return {
        "releases": len(releases),
        "delivered": len(delivered),
        "due": len(due),
        "due_done": due_done,
        "late": late,
    }


def report(
    reg: Registry, record: dict[str, Any], quarter: str, day: date | None = None, draft: bool = False
) -> dict[str, Any]:
    """The pace review of `quarter` (contracts/pace-report.md)."""
    day = day or roadmap.today()
    start, end = roadmap.quarter_span(quarter)
    if end >= day and not draft:
        raise UsageError(f"{quarter} has not ended yet (today {day}); use --draft for a preview")
    delivering = {}
    for e in record["entries"]:
        release = roadmap.delivering_release(reg, e)
        if release:
            delivering[release] = e
    first_delivered = {
        rel[0]: rel[1] for rel, e in delivering.items() if e["kind"] in ("first-release", "new-model")
    }

    delivered, missed, moved, dropped = [], [], [], []
    for e in record["entries"]:
        planned = roadmap.parse_horizon(e["planned"])
        when = roadmap.delivery_date(reg, e)
        if _within(when, start, end):
            kind, days, quarters = roadmap.timing(e, when)
            release = roadmap.delivering_release(reg, e)
            delivered.append(
                {
                    "id": e["id"],
                    "kind": e["kind"],
                    "planned": planned.label,
                    "date": when,
                    "release": f"{release[0]} {release[1]}",
                    "timing": kind,
                    "slip": f"{days} d, {quarters} q" if kind == "late" else "",
                }
            )
        if planned.end <= end and (when is None or when > end) and not e.get("dropped"):
            missed.append(
                {
                    "id": e["id"],
                    "planned": planned.label,
                    "now": roadmap.parse_horizon(e["horizon"]).label,
                    "moves": "; ".join(f"{m['date']}: {m['reason']}" for m in e.get("moves") or []),
                }
            )
        previous = e["planned"]
        for m in e.get("moves") or []:
            if _within(date.fromisoformat(m["date"]), start, end):
                moved.append(
                    {
                        "id": e["id"],
                        "from": roadmap.parse_horizon(previous).label,
                        "to": roadmap.parse_horizon(m["to"]).label,
                        "date": m["date"],
                        "reason": m["reason"],
                    }
                )
            previous = m["to"]
        drop = e.get("dropped")
        if drop and _within(date.fromisoformat(drop["date"]), start, end):
            dropped.append(
                {"id": e["id"], "planned": planned.label, "date": drop["date"], "reason": drop["reason"]}
            )

    unplanned = []
    for model, version, when in _releases(reg):
        if not _within(when, start, end) or (model, version) in delivering:
            continue
        first = first_delivered.get(model)
        note = "patch" if first and parse_version(version) > parse_version(first) else ""
        unplanned.append({"release": f"{model} {version}", "date": when, "note": note})

    counts = _counts(reg, record, quarter)
    early = sum(1 for d in delivered if d["timing"] == "early")
    on_time = sum(1 for d in delivered if d["timing"] == "on time")
    trend = []
    for q in roadmap.quarters_between(record["since"], quarter):
        c = _counts(reg, record, q)
        trend.append({"quarter": roadmap.parse_horizon(q).label, **c})
    return {
        "quarter": quarter,
        "label": roadmap.parse_horizon(quarter).label,
        "generated": day,
        "draft": end >= day,
        "summary": {
            **counts,
            "early": early,
            "on_time": on_time,
            "moved": len(moved),
            "dropped": len(dropped),
            "unplanned": len(unplanned),
        },
        "delivered": delivered,
        "missed": missed,
        "moved": moved,
        "dropped": dropped,
        "unplanned": unplanned,
        "trend": trend,
    }


def _table(header: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "None."
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def rate(done: int, due: int) -> str:
    return f"{done} of {due}" if due else "nothing due"


def render_markdown(r: dict[str, Any]) -> str:
    s = r["summary"]
    parts = [
        f"# Pace review {r['label']}" + (" (draft)" if r["draft"] else ""),
        f"Generated {r['generated']} from {roadmap.RECORD} and the release records "
        "(`zoo roadmap pace`). Everything above the re-planning section is replaced on the next run.",
        "## Summary",
        _table(
            ["", "This quarter"],
            [
                ["Releases published", s["releases"]],
                [
                    "Roadmap entries delivered",
                    f"{s['delivered']} (early {s['early']}, on time {s['on_time']}, late {s['late']})",
                ],
                ["Delivery rate", f"{rate(s['due_done'], s['due'])} entries due this quarter"],
                ["Moved", s["moved"]],
                ["Dropped", s["dropped"]],
                ["Unplanned releases", s["unplanned"]],
            ],
        ),
        "## Delivered",
        _table(
            ["Entry", "Kind", "First planned", "Delivered", "Release", "Timing", "Slip"],
            [
                [d["id"], d["kind"], d["planned"], d["date"], d["release"], d["timing"], d["slip"]]
                for d in r["delivered"]
            ],
        ),
        "## Due and not delivered",
        _table(
            ["Entry", "First planned", "Now in", "Moves (date: reason)"],
            [[m["id"], m["planned"], m["now"], m["moves"]] for m in r["missed"]],
        ),
        "## Moved this quarter",
        _table(
            ["Entry", "From", "To", "Date", "Reason"],
            [[m["id"], m["from"], m["to"], m["date"], m["reason"]] for m in r["moved"]],
        ),
        "## Dropped this quarter",
        _table(
            ["Entry", "First planned", "Date", "Reason"],
            [[d["id"], d["planned"], d["date"], d["reason"]] for d in r["dropped"]],
        ),
        "## Unplanned releases",
        _table(
            ["Release", "Published", "Note"],
            [[u["release"], u["date"], u["note"]] for u in r["unplanned"]],
        ),
        "## Trend",
        _table(
            ["Quarter", "Releases", "Delivered", "Due", "Delivery rate", "Late"],
            [
                [
                    t["quarter"],
                    t["releases"],
                    t["delivered"],
                    t["due"],
                    rate(t["due_done"], t["due"]),
                    t["late"],
                ]
                for t in r["trend"]
            ],
        ),
    ]
    return "\n\n".join(parts) + "\n"


def write(reg: Registry, quarter: str, text: str) -> Path:
    """Write `zoo/roadmap/reviews/<quarter>.md`, keeping a hand-written re-planning section."""
    path = reg.root / roadmap.REVIEWS / f"{quarter}.md"
    replanning = f"{roadmap.REPLANNING}\n\n{roadmap.REPLANNING_PLACEHOLDER}\n"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if roadmap.REPLANNING in old:
            replanning = roadmap.REPLANNING + old.split(roadmap.REPLANNING, 1)[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n" + replanning, encoding="utf-8")
    return path
