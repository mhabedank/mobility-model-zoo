"""The zoo roadmap (feature 015): `zoo/roadmap/roadmap.yaml`, its checks RM1-RM8 and the context of
the roadmap page and the start-page cards.

Horizons are spans of calendar quarters (`2026-Q4`, `2027-Q1..Q2`, `2027-Q4..2028-Q1`; research
R2). An entry keeps the horizon it was first planned in (`planned`, guarded by the git history,
RM5); moves and drops are recorded with date and reason. Delivery is read from the release records:
the first published version of `model`, or `delivered_by` for an update (research R3). Constitution
2.3.0, "Roadmap and Delivery Pace".
"""

from __future__ import annotations

import calendar
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry, _Loader, load_yaml, parse_version
from mobility_model_zoo.site import budgets, facts

RECORD = "zoo/roadmap/roadmap.yaml"
REVIEWS = "zoo/roadmap/reviews"
MAX_OPEN_PER_HORIZON = 6
MAX_AS_OF_AGE_DAYS = 100
WARN_DAYS_BEFORE_END = 14
TEXT_WORDS, PRECONDITION_WORDS, REASON_WORDS = 20, 8, 20
REPLANNING = "## Re-planning"
REPLANNING_PLACEHOLDER = "<!-- How the next horizons use the measured pace (constitution 2.3.0). -->"

_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")
_HORIZON = re.compile(r"^(\d{4})-Q([1-4])(?:\.\.(?:Q([1-4])|(\d{4})-Q([1-4])))?$")
_MONTHS = calendar.month_name


# ---- today and quarters -----------------------------------------------------------------------
def today() -> date:
    """The UTC date, or `ZOO_TODAY` (ISO date) when set (tests, rehearsals)."""
    override = os.environ.get("ZOO_TODAY")
    if override:
        return date.fromisoformat(override)
    return datetime.now(UTC).date()


def _quarter_start(year: int, q: int) -> date:
    return date(year, 3 * q - 2, 1)


def _quarter_end(year: int, q: int) -> date:
    month = 3 * q
    return date(year, month, calendar.monthrange(year, month)[1])


def _next(year: int, q: int) -> tuple[int, int]:
    return (year + 1, 1) if q == 4 else (year, q + 1)


def parse_quarter(qid: str) -> tuple[int, int]:
    m = _QUARTER.match(qid)
    if not m:
        raise ValueError(f"not a quarter id: {qid!r}")
    return int(m.group(1)), int(m.group(2))


def quarter_id(year: int, q: int) -> str:
    return f"{year}-Q{q}"


def quarter_of(day: date) -> str:
    return quarter_id(day.year, (day.month - 1) // 3 + 1)


def quarter_span(qid: str) -> tuple[date, date]:
    year, q = parse_quarter(qid)
    return _quarter_start(year, q), _quarter_end(year, q)


def quarters_between(first: str, last: str) -> list[str]:
    """Quarter ids from `first` to `last`, both included; empty if `last` is before `first`."""
    year, q = parse_quarter(first)
    end = parse_quarter(last)
    out = []
    while (year, q) <= end:
        out.append(quarter_id(year, q))
        year, q = _next(year, q)
    return out


@dataclass(frozen=True)
class Horizon:
    id: str
    quarters: tuple[tuple[int, int], ...]
    start: date
    end: date
    label: str
    months: str


@cache
def parse_horizon(hid: str) -> Horizon:
    """A horizon id: one quarter, or two consecutive quarters (research R2, data-model.md)."""
    m = _HORIZON.match(hid or "")
    if not m:
        raise ValueError(f"not a horizon id: {hid!r}")
    year, q = int(m.group(1)), int(m.group(2))
    quarters: list[tuple[int, int]] = [(year, q)]
    if m.group(3):
        q2 = int(m.group(3))
        if q2 != q + 1:
            raise ValueError(f"not a horizon id: {hid!r} (quarters must follow each other)")
        quarters.append((year, q2))
    elif m.group(4):
        y2, q2 = int(m.group(4)), int(m.group(5))
        if (q, y2, q2) != (4, year + 1, 1):
            raise ValueError(f"not a horizon id: {hid!r} (only Q4..next year's Q1 crosses a year)")
        quarters.append((y2, q2))
    start, end = _quarter_start(*quarters[0]), _quarter_end(*quarters[-1])
    if len(quarters) == 1:
        label = f"Q{q} {year}"
    elif quarters[1][0] != year:
        label = f"Q4 {year} – Q1 {year + 1}"
    elif (q, quarters[1][1]) == (1, 2):
        label = f"H1 {year}"
    elif (q, quarters[1][1]) == (3, 4):
        label = f"H2 {year}"
    else:
        label = f"Q{q}–Q{quarters[1][1]} {year}"
    months = f"{_MONTHS[start.month]} – {_MONTHS[end.month]}"
    return Horizon(hid, tuple(quarters), start, end, label, months)


def long_date(day: date) -> str:
    return f"{day.day} {_MONTHS[day.month]} {day.year}"


# ---- loading (RM1) ----------------------------------------------------------------------------
def load(reg: Registry) -> dict[str, Any]:
    """The record, validated against its schema (RM1)."""
    from mobility_model_zoo.site.context import _schema_errors

    path = reg.root / RECORD
    if not path.exists():
        raise GateFailed([f"RM1 {RECORD} is missing"])
    data = load_yaml(path) or {}
    errors = [f"RM1 {RECORD} {e}" for e in _schema_errors("roadmap", data)]
    seen: set[str] = set()
    for entry in data.get("entries") or []:
        if isinstance(entry, dict) and entry.get("id") in seen:
            errors.append(f"RM1 entries: duplicate id {entry['id']}")
        if isinstance(entry, dict):
            seen.add(entry.get("id"))
    if errors:
        raise GateFailed(errors)
    return data


# ---- delivery and state -----------------------------------------------------------------------
def _published_on(reg: Registry, name: str, version: str) -> date | None:
    if version not in reg.versions(name):
        return None
    rec = reg.record_raw(name, version)
    published = rec.get("published") or {}
    if not published:
        return None
    stamp = published.get("published_at")
    if stamp:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).astimezone(UTC).date()
    return date.fromisoformat(str(rec["date"]))  # records published before `published_at` existed


def delivering_release(reg: Registry, entry: dict[str, Any]) -> tuple[str, str] | None:
    """The release that delivers the entry, if it is published (research R3)."""
    if entry["kind"] == "update":
        ref = entry.get("delivered_by")
        if not ref or ref["model"] not in reg.model_names():
            return None
        if _published_on(reg, ref["model"], ref["version"]) is None:
            return None
        return ref["model"], ref["version"]
    model = entry.get("model")
    if not model or model not in reg.model_names():
        return None
    published = reg.published_versions(model)
    if not published:
        return None
    return model, min(published, key=parse_version)


def delivery_date(reg: Registry, entry: dict[str, Any]) -> date | None:
    release = delivering_release(reg, entry)
    return _published_on(reg, *release) if release else None


def state(reg: Registry, entry: dict[str, Any]) -> str:
    if entry.get("dropped"):
        return "dropped"
    return "delivered" if delivering_release(reg, entry) else "open"


def timing(entry: dict[str, Any], day: date) -> tuple[str, int | None, int | None]:
    """Early, on time or late against the first planned horizon; slip in days and quarters."""
    planned = parse_horizon(entry["planned"])
    if day < planned.start:
        return "early", None, None
    if day <= planned.end:
        return "on time", None, None
    end_year, end_q = planned.quarters[-1]
    slip_quarters = len(quarters_between(quarter_id(*_next(end_year, end_q)), quarter_of(day)))
    return "late", (day - planned.end).days, slip_quarters


def usage_label(reg: Registry, entry: dict[str, Any]) -> str | None:
    """Derived from the registration, never written into the entry (FR-007)."""
    model = entry.get("model")
    if not model or model not in reg.model_names():
        return None
    usage = reg.model_raw(model).get("usage_class", "commercial")
    return {"commercial-share-alike": "share-alike"}.get(usage) or (
        "non-commercial" if usage.startswith("non-commercial") else None
    )


def motif_name(reg: Registry, entry: dict[str, Any]) -> str | None:
    from importlib import resources

    model = entry.get("model")
    if not model:
        return None
    site = reg.model_dir(model) / "site.yaml"
    if site.exists():
        motif = (load_yaml(site) or {}).get("motif")
        if motif:
            return motif
    motifs = resources.files("mobility_model_zoo.site").joinpath("static/img/motifs")
    return f"{model}.svg" if motifs.joinpath(f"{model}.svg").is_file() else None


def open_entries(reg: Registry, record: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in record["entries"] if state(reg, e) == "open"]


# ---- checks RM2-RM8 ---------------------------------------------------------------------------
def check_registry(reg: Registry, record: dict[str, Any]) -> list[str]:
    """RM2: the record agrees with the model registry."""
    from mobility_model_zoo.site.context import is_sandbox

    errors = []
    names = set(reg.model_names())
    topics = {t["id"] for t in reg.topics()}
    for e in record["entries"]:
        where = f"RM2 {e['id']}"
        if e["topic"] not in topics or e["topic"] == "sandbox":
            errors.append(f"{where}: topic {e['topic']!r} is not a zoo topic")
        model = e.get("model")
        if model:
            if model not in names or is_sandbox(reg, model):
                errors.append(f"{where}: model {model!r} is not a registered model")
                continue
            if reg.model_raw(model).get("topic") != e["topic"]:
                errors.append(f"{where}: topic {e['topic']} differs from the topic of {model}")
            if e["kind"] == "new-model" and e["working_name"]:
                errors.append(f"{where}: {model} is registered, set working_name: false")
        if e["kind"] == "update" and model in names and state(reg, e) == "open":
            if not reg.published_versions(model):
                errors.append(f"{where}: update of {model}, which has no published version")
    covered = {
        e["model"]
        for e in record["entries"]
        if e.get("model") and e["kind"] != "update" and not e.get("dropped")
    }
    for name in sorted(names):
        if is_sandbox(reg, name) or reg.published_versions(name):
            continue
        if name not in covered:
            errors.append(f"RM2 {name}: registered and unpublished, but has no open entry")
    return errors


def check_text(record: dict[str, Any]) -> list[str]:
    """RM3: short, without numbers, placeholders or release-status words (FR-004)."""
    errors = []

    def rules(where: str, text: str, limit: int) -> None:
        if budgets.words(text) > limit:
            errors.append(f"RM3 {where} has {budgets.words(text)} words, limit {limit}")
        for n in facts.literal_numbers(text):
            errors.append(f"RM3 {where}: literal number {n!r}")
        if budgets.PLACEHOLDER.search(text):
            errors.append(f"RM3 {where}: metric placeholder")
        if m := budgets.STATUS_WORDS.search(text):
            errors.append(f"RM3 {where}: release-status word {m.group(0)!r}")

    for e in record["entries"]:
        rules(f"{e['id']}.text", e["text"], TEXT_WORDS)
        if e.get("precondition"):
            rules(f"{e['id']}.precondition", e["precondition"], PRECONDITION_WORDS)
        for i, move in enumerate(e.get("moves") or []):
            if budgets.words(move["reason"]) > REASON_WORDS:
                errors.append(f"RM3 {e['id']}.moves[{i}].reason is longer than {REASON_WORDS} words")
        if e.get("dropped") and budgets.words(e["dropped"]["reason"]) > REASON_WORDS:
            errors.append(f"RM3 {e['id']}.dropped.reason is longer than {REASON_WORDS} words")
    return errors


def check_horizons(reg: Registry, record: dict[str, Any]) -> list[str]:
    """RM4: three consecutive horizons, consistent moves, at most six open entries per horizon."""
    errors = []
    try:
        hs = [parse_horizon(h) for h in record["horizons"]]
    except ValueError as e:
        return [f"RM4 horizons: {e}"]
    if len(hs[0].quarters) != 1:
        errors.append(f"RM4 horizons: the first horizon {hs[0].id} must span one quarter")
    for h in hs[1:]:
        if len(h.quarters) != 2:
            errors.append(f"RM4 horizons: {h.id} must span two quarters")
    for a, b in zip(hs, hs[1:], strict=False):
        if _next(*a.quarters[-1]) != b.quarters[0]:
            errors.append(f"RM4 horizons: {b.id} does not follow {a.id}")
    current = {h.id for h in hs}
    counts = dict.fromkeys(current, 0)
    for e in record["entries"]:
        where = f"RM4 {e['id']}"
        try:
            parse_horizon(e["planned"])
            parse_horizon(e["horizon"])
            for move in e.get("moves") or []:
                parse_horizon(move["to"])
        except ValueError as err:
            errors.append(f"{where}: {err}")
            continue
        moves = e.get("moves") or []
        expected = moves[-1]["to"] if moves else e["planned"]
        if e["horizon"] != expected:
            errors.append(
                f"{where}: horizon is {e['horizon']}, but "
                + (
                    f"the last move goes to {expected}"
                    if moves
                    else f"planned is {expected} and no move is recorded"
                )
            )
        dates = [m["date"] for m in moves]
        if dates != sorted(dates):
            errors.append(f"{where}: move dates are not in order")
        entry_state = state(reg, e)
        if e.get("dropped") and delivering_release(reg, e):
            errors.append(f"{where}: dropped and delivered at once")
        if entry_state == "open":
            if e["horizon"] not in current:
                errors.append(
                    f"{where}: open, but its horizon {e['horizon']} is not one of {sorted(current)}"
                )
            else:
                counts[e["horizon"]] += 1
    for hid, n in counts.items():
        if n > MAX_OPEN_PER_HORIZON:
            errors.append(f"RM4 {hid} holds {n} open entries, limit {MAX_OPEN_PER_HORIZON}")
    return errors


def _history(root: Path) -> tuple[dict[str, Any], ...]:
    """Every committed version of the record, oldest first; empty without git history."""
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    if head.returncode != 0:
        return ()
    return _history_at(root, head.stdout.strip())


@cache
def _history_at(root: Path, head: str) -> tuple[dict[str, Any], ...]:
    log = subprocess.run(
        ["git", "-C", str(root), "log", "--format=%H", "--reverse", head, "--", RECORD],
        capture_output=True,
        text=True,
        check=False,
    )
    if log.returncode != 0:
        return ()
    out = []
    for sha in log.stdout.split():
        shown = subprocess.run(
            ["git", "-C", str(root), "show", f"{sha}:{RECORD}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if shown.returncode == 0:
            out.append(yaml.load(shown.stdout, Loader=_Loader) or {})
    return tuple(out)


def check_first_planned(reg: Registry, record: dict[str, Any]) -> list[str]:
    """RM5: `planned` equals its value in the first commit that contained the entry."""
    first: dict[str, str] = {}
    for version in _history(reg.root.resolve()):
        for e in version.get("entries") or []:
            if isinstance(e, dict) and e.get("id") and e["id"] not in first:
                first[e["id"]] = e.get("planned")
    return [
        f"RM5 {e['id']}: planned was {first[e['id']]} when the entry was added, now {e['planned']}"
        for e in record["entries"]
        if e["id"] in first and first[e["id"]] != e["planned"]
    ]


def check_stale(reg: Registry, record: dict[str, Any], day: date) -> list[str]:
    """RM6: a current date, and no open entry in a horizon that has ended."""
    errors = []
    as_of = date.fromisoformat(record["as_of"])
    if as_of > day:
        errors.append(f"RM6 as_of {as_of} is in the future (today {day})")
    elif (day - as_of).days > MAX_AS_OF_AGE_DAYS:
        errors.append(
            f"RM6 as_of {as_of} is {(day - as_of).days} days old, "
            f"limit {MAX_AS_OF_AGE_DAYS}: review the roadmap"
        )
    for e in open_entries(reg, record):
        try:
            end = parse_horizon(e["horizon"]).end
        except ValueError:
            continue
        if end < day:
            errors.append(
                f"RM6 {e['id']}: open entry in {e['horizon']}, which ended {end}: "
                "move it (with a reason), drop it, or record its delivery"
            )
    return errors


def review_errors(path: Path) -> str | None:
    if not path.exists():
        return "missing"
    text = path.read_text(encoding="utf-8")
    if REPLANNING not in text:
        return f"has no {REPLANNING!r} section"
    body = text.split(REPLANNING, 1)[1].split("\n## ", 1)[0]
    body = body.replace(REPLANNING_PLACEHOLDER, "")
    if not re.search(r"[A-Za-z]{3,}", body):
        return f"{REPLANNING!r} is empty"
    return None


def check_reviews(reg: Registry, record: dict[str, Any]) -> list[str]:
    """RM7: every closed quarter from `since` up to the first horizon has a filled review."""
    first = parse_horizon(record["horizons"][0])
    previous = quarter_of(first.start - timedelta(days=1))
    errors = []
    for qid in quarters_between(record["since"], previous):
        problem = review_errors(reg.root / REVIEWS / f"{qid}.md")
        if problem:
            errors.append(
                f"RM7 {REVIEWS}/{qid}.md {problem}: run `zoo roadmap pace {qid} --write` and fill in "
                "the re-planning section before rolling the horizons forward"
            )
    return errors


def check_delivery(reg: Registry, record: dict[str, Any]) -> list[str]:
    """RM8: `delivered_by` names a published release."""
    errors = []
    for e in record["entries"]:
        ref = e.get("delivered_by")
        if not ref:
            continue
        if (
            ref["model"] not in reg.model_names()
            or _published_on(reg, ref["model"], ref["version"]) is None
        ):
            errors.append(f"RM8 {e['id']}: {ref['model']} {ref['version']} is not published")
    return errors


def validate(reg: Registry, record: dict[str, Any], day: date | None = None) -> list[str]:
    """RM2-RM8 on a record that passed RM1 (contracts/checks.md)."""
    day = day or today()
    return (
        check_registry(reg, record)
        + check_text(record)
        + check_horizons(reg, record)
        + check_first_planned(reg, record)
        + check_stale(reg, record, day)
        + check_reviews(reg, record)
        + check_delivery(reg, record)
    )


def warnings(record: dict[str, Any], day: date | None = None) -> list[str]:
    day = day or today()
    try:
        first = parse_horizon(record["horizons"][0])
    except ValueError:
        return []
    left = (first.end - day).days
    if 0 <= left <= WARN_DAYS_BEFORE_END:
        return [
            f"RM6 warning: {first.label} ends {first.end} ({left} days); after that the site build "
            f"fails until the roadmap is reviewed (`zoo roadmap pace {quarter_of(first.start)} --write`)"
        ]
    return []


def load_and_check(reg: Registry, day: date | None = None) -> dict[str, Any]:
    """RM1-RM8; raises GateFailed with every finding."""
    record = load(reg)
    errors = validate(reg, record, day)
    if errors:
        raise GateFailed(errors)
    return record


# ---- page context -----------------------------------------------------------------------------
def page_context(reg: Registry, record: dict[str, Any], day: date | None = None) -> dict[str, Any]:
    """What the roadmap page and the start page need (data-model.md, "Page context")."""
    day = day or today()
    horizons = [parse_horizon(h) for h in record["horizons"]]
    topics = {t["id"]: t["title"] for t in reg.topics()}
    by_horizon: dict[str, list[dict[str, Any]]] = {h.id: [] for h in horizons}
    for e in open_entries(reg, record):
        if e["horizon"] not in by_horizon:
            continue
        model = e.get("model")
        by_horizon[e["horizon"]].append(
            {
                "id": e["id"],
                "name": e["name"],
                "working_name": e["working_name"],
                "model": model,
                "topic_title": topics.get(e["topic"], e["topic"]),
                "kind": e["kind"],
                "stage": e["stage"],
                "text": e["text"],
                "precondition": e.get("precondition"),
                "usage_label": usage_label(reg, e),
                "motif": motif_name(reg, e),
                "model_url": f"models/{model}/" if e["kind"] == "update" else None,
            }
        )
    first = horizons[0]
    span = (first.end - first.start).days or 1
    now = min(max((day - first.start).days / span, 0.0), 1.0)
    out_horizons = [
        {
            "id": h.id,
            "label": h.label,
            "months": h.months,
            "start": h.start,
            "end": h.end,
            "is_first": i == 0,
            "entries": by_horizon[h.id],
        }
        for i, h in enumerate(horizons)
    ]
    upcoming = [
        {**e, "horizon_label": h["label"]}
        for h in out_horizons
        for e in h["entries"]
        if e["kind"] in ("new-model", "first-release")
    ]
    return {
        "as_of": long_date(date.fromisoformat(record["as_of"])),
        "horizons": out_horizons,
        "upcoming": upcoming,
        "now_fraction": round(now, 3),
    }
