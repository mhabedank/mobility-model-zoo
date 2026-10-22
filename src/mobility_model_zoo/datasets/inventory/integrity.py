"""Integrity of frozen benchmarks (FR-007, research R12).

Always, from the repository alone:
1. every `based_on.manifest_sha256` equals the hash of the parent's current manifest;
2. a frozen manifest has no commits after the one that added it, except revisions it records itself
   (`revisions[]`, JTBD cluster). Skipped in a shallow clone, which may not hold the freezing commit.

With `verify=True` and the data on this machine, the existing content verifiers run as well. They
need the `jtbd` or `edge` extras; when one cannot be imported or its data is missing, the row stays
`unchecked` with a note. A frozen manifest is never edited to make a check pass (constitution IX).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import history
from .rows import InventoryRow


def _set(row: InventoryRow, value: str, note: str | None = None) -> None:
    order = ("unchecked", "ok", "changed-after-freeze", "mismatch")
    if order.index(value) > order.index(row.integrity):
        row.integrity = value
    if note:
        row.notes.append(note)


def check_lineage(rows: list[InventoryRow]) -> None:
    by_name = {r.name: r for r in rows if r.kind == "benchmark"}
    for row in rows:
        for link in row.lineage:
            if link.get("relation") != "based_on" or not link.get("sha256"):
                continue
            parent = by_name.get(link["target"])
            if parent is None or parent.sha256 is None:
                row.notes.append(f"based_on {link['target']} not found")
                continue
            if parent.sha256 != link["sha256"]:
                _set(row, "mismatch", f"based_on hash differs from {link['target']}'s current manifest")
            else:
                _set(row, "ok")


def check_frozen_files(root: Path, rows: list[InventoryRow]) -> None:
    if not history.in_git(root) or history.is_shallow(root):
        for row in rows:
            if row.kind == "benchmark":
                row.notes.append("freeze check skipped (no full git history)")
        return
    for row in rows:
        if row.kind != "benchmark" or row.availability == "error":
            continue
        violation = frozen_violation(root, row.source)
        if violation is None:
            _set(row, "ok")
        else:
            sha, date, keys = violation
            _set(
                row,
                "changed-after-freeze",
                f"{', '.join(keys)} changed after freeze in {sha[:12]} ({date})",
            )


# Keys a task's own lifecycle writes after the freeze (state machine, event log, reruns, review
# dates); they never change what is measured.
LIFECYCLE = {"state", "pilot_state", "events", "history", "reruns", "retention_review_by", "revisions"}


def _freeze_marks(manifest: dict) -> tuple:
    """What changes when a benchmark is (re)frozen: its own date and its label freeze."""
    bench = manifest.get("benchmark")
    return (manifest.get("frozen_at"), bench.get("frozen_at") if isinstance(bench, dict) else None)


def _refrozen(previous: dict, current: dict) -> bool:
    """A new freeze: a new freeze date, or a new event the task logged in state `frozen` (the
    JTBD cluster task re-freezes before any labeling and records it that way)."""
    if _freeze_marks(current) != _freeze_marks(previous):
        return True
    log = current.get("events") or []
    new = log[len(previous.get("events") or []) :]
    return any(isinstance(e, dict) and e.get("state") == "frozen" for e in new)


def frozen_violation(root: Path, rel: str) -> tuple[str, str, list[str]] | None:
    """First committed change to a frozen manifest that is neither lifecycle, a new freeze nor a
    revision the manifest records itself; None when there is none.

    A re-freeze (new `frozen_at`) before an evaluation is how the tasks rebuild a benchmark, so each
    freeze starts a new baseline; after it, only lifecycle keys may change, and `hashes` only
    together with a new `revisions[]` entry."""
    previous: dict | None = None
    for sha, date in history.file_log(root, rel):
        text = history.show(root, sha, rel)
        if text is None:
            continue
        try:
            current = json.loads(text)
        except ValueError:
            continue
        if previous is not None and previous.get("frozen_at") and not _refrozen(previous, current):
            changed = [
                k for k in sorted(set(previous) | set(current)) if previous.get(k) != current.get(k)
            ]
            revised = len(current.get("revisions") or []) > len(previous.get("revisions") or [])
            content = [k for k in changed if k not in LIFECYCLE and not (k == "hashes" and revised)]
            if content:
                return sha, date, content
        previous = current
    return None


def verify_content(root: Path, rows: list[InventoryRow]) -> None:
    """Re-hash the data behind each benchmark with the task's own verifier, where possible."""
    for row in rows:
        if row.kind != "benchmark" or row.availability == "error":
            continue
        try:
            if row.id == "can-ids":
                _verify_can_ids(root, row)
            else:
                row.notes.append("content check: run `jtbd freeze --verify` with the task configuration")
        except ImportError as e:
            row.notes.append(f"content check skipped ({e.name} not installed)")
        except FileNotFoundError:
            row.notes.append("content check skipped (data not on this machine)")
        except Exception as e:  # noqa: BLE001 - a verifier's refusal is the finding
            _set(row, "mismatch", f"content check failed: {e}")


def _verify_can_ids(root: Path, row: InventoryRow) -> None:
    from mobility_model_zoo.security.can_ids.benchmark import verify_captures
    from mobility_model_zoo.security.cli import benchmark_sources

    manifest = json.loads((root / row.source).read_text(encoding="utf-8"))
    sources = benchmark_sources()
    if not all(p.exists() for p in sources.values()):
        raise FileNotFoundError("can-ids data")
    verify_captures(manifest, sources)
    _set(row, "ok")


def check(root: Path, rows: list[InventoryRow], verify: bool = False) -> None:
    check_lineage(rows)
    check_frozen_files(root, rows)
    if verify:
        verify_content(root, rows)
