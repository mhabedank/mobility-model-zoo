"""Change history of registers and manifests from git (FR-005, research R12).

Same pattern as `site/roadmap.py:_history`: every committed version of a file, oldest first, parsed
and compared record by record. Only register values are reported, never dataset content. In a
shallow clone the history is what the clone holds, and callers say so.
"""

from __future__ import annotations

import json
import subprocess
from functools import cache
from pathlib import Path
from typing import Any

from .rows import HistoryEvent, InventoryRow

# Register fields worth a history line; free text (titles, attribution, notes) is left out.
TRACKED_FIELDS = (
    "status",
    "licence",
    "permitted_use",
    "redistribution",
    "commercial_use",
    "approx_size_mb",
    "license_checked",
    "last_reviewed",
    "used_by",
    "class",
)


def git(root: Path, *args: str) -> str | None:
    out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return out.stdout if out.returncode == 0 else None


@cache
def in_git(root: Path) -> bool:
    return git(root, "rev-parse", "HEAD") is not None


@cache
def is_shallow(root: Path) -> bool:
    return (git(root, "rev-parse", "--is-shallow-repository") or "").strip() == "true"


@cache
def file_log(root: Path, rel: str) -> tuple[tuple[str, str], ...]:
    """(commit, date) of every commit touching `rel`, oldest first."""
    out = git(root, "log", "--format=%H %cs", "--reverse", "HEAD", "--", rel)
    if not out:
        return ()
    return tuple(tuple(line.split(" ", 1)) for line in out.splitlines() if line.strip())  # type: ignore[misc]


@cache
def show(root: Path, sha: str, rel: str) -> str | None:
    return git(root, "show", f"{sha}:{rel}")


def last_change(root: Path, rel: str) -> str | None:
    log = file_log(root, rel)
    return log[-1][1] if log else None


def _parse(rel: str, text: str) -> Any:
    if rel.endswith(".json"):
        return json.loads(text)
    import yaml

    return yaml.safe_load(text)


@cache
def record_versions(root: Path, rel: str, collection: str) -> tuple[tuple[str, str, dict], ...]:
    """(commit, date, {id: record}) for every committed version of a register file."""
    out = []
    for sha, date in file_log(root, rel):
        text = show(root, sha, rel)
        if text is None:
            continue
        try:
            data = _parse(rel, text) or {}
        except Exception:  # noqa: BLE001 - a broken historic version is skipped, not fatal
            continue
        records = {r.get("id"): r for r in data.get(collection) or [] if isinstance(r, dict)}
        out.append((sha, date, records))
    return tuple(out)


def record_last_change(root: Path, rel: str, collection: str, rid: str) -> str | None:
    """Date of the last commit that changed this one record (not just the file)."""
    last, previous = None, None
    for _sha, date, records in record_versions(root, rel, collection):
        rec = records.get(rid)
        if rec != previous:
            last = date if rec is not None else last
        previous = rec
    return last


def register_events(root: Path, rel: str, collection: str, subject: str, rid: str) -> list[HistoryEvent]:
    events: list[HistoryEvent] = []
    previous: dict | None = None
    for sha, date, records in record_versions(root, rel, collection):
        rec = records.get(rid)
        if rec is None:
            previous = None
            continue
        if previous is None:
            events.append(HistoryEvent(date, sha, subject, "registered"))
        else:
            for name in TRACKED_FIELDS:
                if rec.get(name) != previous.get(name):
                    events.append(
                        HistoryEvent(
                            date, sha, subject, "field-changed", name, previous.get(name), rec.get(name)
                        )
                    )
        previous = rec
    return events


def added_commit(root: Path, rel: str) -> tuple[str, str] | None:
    out = git(root, "log", "--format=%H %cs", "--diff-filter=A", "HEAD", "--", rel)
    if not out or not out.strip():
        return None
    sha, date = out.splitlines()[-1].split(" ", 1)
    return sha, date


def _day(value: Any) -> str | None:
    return str(value)[:10] if value else None


def manifest_events(root: Path, row: InventoryRow) -> list[HistoryEvent]:
    """Freeze, lineage and the manifest's own recorded events (history, events, revisions)."""
    subject = f"{row.kind}:{row.name}"
    events: list[HistoryEvent] = []
    added = added_commit(root, row.source) if in_git(root) else None
    events.append(
        HistoryEvent(
            row.frozen_at or (added[1] if added else ""), added[0] if added else None, subject, "frozen"
        )
    )
    for link in row.lineage:
        if link["relation"] in ("supersedes", "based_on"):
            events.append(
                HistoryEvent(
                    row.frozen_at or "",
                    added[0] if added else None,
                    subject,
                    "superseded",
                    link["relation"],
                    link["target"],
                    row.name,
                )
            )
    manifest = json.loads((root / row.source).read_text(encoding="utf-8"))
    for item in manifest.get("revisions") or []:
        events.append(HistoryEvent(_day(item.get("at")) or "", None, subject, "revised"))
    for item in manifest.get("events") or manifest.get("history") or []:
        text = str(item.get("event", ""))
        kind = "excluded" if "exclu" in text else "revised"
        events.append(
            HistoryEvent(
                _day(item.get("at") or item.get("ts")) or "",
                None,
                subject,
                kind,
                "event",
                None,
                text[:120],
            )
        )
    for cap in manifest.get("captures") or []:
        if cap.get("role") == "excluded":
            events.append(
                HistoryEvent(
                    row.frozen_at or "", None, subject, "excluded", "capture", None, cap.get("id")
                )
            )
    return events


def changed_after(root: Path, rel: str, sha: str) -> list[tuple[str, str]]:
    """Commits after `sha` that touch `rel`, oldest first."""
    out = git(root, "log", "--format=%H %cs", "--reverse", f"{sha}..HEAD", "--", rel)
    if not out:
        return []
    return [tuple(line.split(" ", 1)) for line in out.splitlines() if line.strip()]  # type: ignore[misc]
