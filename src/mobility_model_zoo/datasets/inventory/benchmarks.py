"""Frozen benchmarks: one reader per manifest shape (research R11).

* JTBD pilot (`chunks`, `holdout_chunks`): chunk counts per split, `supersedes`.
* JTBD cluster (`counts.items`): items, snapshots, pairs and sets per split, exclusions.
* CAN intrusion detection (`captures`): captures, frames, episodes and their distributions by role,
  split, set, vehicle, dataset and attack family; `based_on`.

Only counts and hashes are read out of a manifest, never chunk text or frames.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .hashes import manifest_hash
from .rows import InventoryRow
from .sources import strictest_use


def family(version: str) -> str:
    """`can-ids-v3` -> `can-ids`, `pilot-v2` -> `pilot`."""
    return re.sub(r"-v\d+$", "", version)


def _day(value: Any) -> str | None:
    return str(value)[:10] if value else None


def _count(values) -> dict[str, int]:
    return dict(sorted(Counter(str(v) for v in values).items()))


def _pilot(row: InventoryRow, m: dict[str, Any]) -> None:
    row.counts = {
        "chunks": len(m.get("chunks") or {}),
        "holdout_chunks": len(m.get("holdout_chunks") or {}),
        "train_chunks": len(m.get("train_chunks") or {}),
    }
    if m.get("supersedes"):
        row.lineage.append(
            {"relation": "supersedes", "target": f"{family(m['supersedes'])}@{m['supersedes']}"}
        )
    row.notes.append("no label distribution stored in this manifest")


def _cluster(row: InventoryRow, m: dict[str, Any]) -> None:
    counts = m.get("counts") or {}
    for dim in ("items", "snapshots", "sets"):
        per_split = counts.get(dim) or {}
        row.counts[dim] = sum(per_split.values())
        row.distribution[f"{dim}_by_split"] = dict(per_split)
    pairs = counts.get("pairs") or {}
    row.counts["pairs"] = sum(sum(v.values()) for v in pairs.values())
    row.distribution["pairs_by_split"] = {s: sum(v.values()) for s, v in pairs.items()}
    level: Counter = Counter()
    for v in pairs.values():
        level.update(v)
    row.distribution["pairs_by_level"] = dict(sorted(level.items()))
    excluded = m.get("excluded") or {}
    row.counts["excluded_items"] = excluded.get("opt_out_items", 0)
    row.counts["excluded_snapshots"] = excluded.get("opt_out_snapshots", 0)


def _can_ids(row: InventoryRow, m: dict[str, Any], registry: dict[str, dict[str, Any]]) -> None:
    caps = m.get("captures") or []
    row.counts = {
        "captures": len(caps),
        "frames": sum(int(c.get("frames") or 0) for c in caps),
        "attack_frames": sum(int(c.get("attack_frames") or 0) for c in caps),
        "episodes": sum(int(c.get("episodes") or 0) for c in caps),
        "duration_s": round(sum(float(c.get("duration_s") or 0) for c in caps), 1),
    }
    for dim in ("role", "split", "set", "vehicle", "dataset", "attack_family"):
        row.distribution[dim] = _count(c.get(dim) for c in caps)
    frames_by_role: Counter = Counter()
    for c in caps:
        frames_by_role[str(c.get("role"))] += int(c.get("frames") or 0)
    row.distribution["frames_by_role"] = dict(sorted(frames_by_role.items()))
    based = m.get("based_on") or {}
    if based.get("benchmark"):
        row.lineage.append(
            {
                "relation": "based_on",
                "target": f"{family(based['benchmark'])}@{based['benchmark']}",
                "sha256": based.get("manifest_sha256", ""),
            }
        )
    licences = sorted({d.get("licence") for d in m.get("datasets") or [] if d.get("licence")})
    row.licence = " AND ".join(licences) or None
    uses = [(registry.get(d.get("id")) or {}).get("permitted_use") for d in m.get("datasets") or []]
    row.permitted_use = strictest_use(uses)
    reds = {(registry.get(d.get("id")) or {}).get("redistribution") for d in m.get("datasets") or []}
    row.redistribution = (
        "allowed" if reds == {"allowed"} else ("not_allowed" if "not_allowed" in reds else "unclear")
    )
    for d in m.get("datasets") or []:
        row.lineage.append(
            {"relation": "built_from", "target": f"{d.get('id')}@{_day(d.get('retrieved_at'))}"}
        )


def read(
    root: Path, path: Path, registry: dict[str, dict[str, Any]], source_use: dict[str, str | None]
) -> InventoryRow:
    m = json.loads(path.read_text(encoding="utf-8"))
    version = path.parent.name
    topic = path.parents[2].name
    state = m.get("state")
    row = InventoryRow(
        kind="benchmark",
        topic=topic,
        id=family(version),
        version=version,
        status=state if state in ("frozen", "decided", "building") else "frozen",
        source=path.relative_to(root).as_posix(),
        frozen_at=_day(m.get("frozen_at")),
        sha256=manifest_hash(m),
        availability="measured",  # every count of a benchmark is in its manifest
    )
    text_use = source_use.get(topic)
    if "captures" in m:
        _can_ids(row, m, registry)
    elif isinstance(m.get("counts"), dict) and "items" in m["counts"]:
        _cluster(row, m)
    elif "chunks" in m:
        _pilot(row, m)
    else:
        row.availability = "error"
        row.notes.append("unknown manifest shape")
    if "captures" not in m and text_use:
        # text benchmarks draw on the topic's source register: its strictest permitted use applies
        row.permitted_use = text_use
        row.notes.append(f"permitted use: strictest of the {topic} source register")
    current = path.parents[1] / "current"
    if current.is_file() and current.read_text(encoding="utf-8").strip() == version:
        row.notes.append("current benchmark of the task")
    return row


def collect(
    root: Path, registry: dict[str, dict[str, Any]], source_use: dict[str, str | None]
) -> tuple[list[InventoryRow], list[str]]:
    """Rows of every manifest under topics/*/benchmarks/, plus footer notes for topics without any."""
    rows, notes = [], []
    for path in sorted((root / "topics").glob("*/benchmarks/*/manifest.json")):
        try:
            rows.append(read(root, path, registry, source_use))
        except (OSError, ValueError, TypeError, KeyError) as e:
            version = path.parent.name
            rows.append(
                InventoryRow(
                    kind="benchmark",
                    topic=path.parents[2].name,
                    id=family(version),
                    version=version,
                    status="frozen",
                    source=path.relative_to(root).as_posix(),
                    availability="error",
                    notes=[f"manifest unreadable: {e.__class__.__name__}"],
                )
            )
    with_benchmarks = {r.topic for r in rows}
    for topic_dir in sorted((root / "topics").iterdir()):
        if (
            topic_dir.is_dir()
            and (topic_dir / "compliance").is_dir()
            and topic_dir.name not in with_benchmarks
        ):
            if topic_dir.name != "sandbox":
                notes.append(f"{topic_dir.name}: no benchmarks frozen yet")
    return rows, notes
