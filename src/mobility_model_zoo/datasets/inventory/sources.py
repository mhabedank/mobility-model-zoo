"""Source collections: the registers of crawled texts, `topics/<topic>/compliance/sources.yaml`.

One row per topic register. Counts come from the register; the snapshot store is measured where it
exists (`paths.snapshots` of the JTBD configuration, outside git).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

from .hashes import canonical_yaml_hash
from .rows import InventoryRow
from .third_party import measure

VERSION = "current"  # a living register; its hash tells versions apart


def snapshot_dir(root: Path, topic: str) -> Path | None:
    """The snapshot store named by the topic's task configurations (`paths.snapshots`)."""
    for config in sorted((root / "configs" / topic).glob("*/*.yaml")):
        try:
            paths = (yaml.safe_load(config.read_text(encoding="utf-8")) or {}).get("paths") or {}
        except (yaml.YAMLError, AttributeError):
            continue
        if isinstance(paths, dict) and paths.get("snapshots"):
            return root / paths["snapshots"]
    return None


def strictest_use(uses: list[str | None]) -> str | None:
    if "benchmark_only" in uses:
        return "benchmark_only"
    return "training_allowed" if "training_allowed" in uses else None


def collect(root: Path) -> list[InventoryRow]:
    rows = []
    for path in sorted((root / "topics").glob("*/compliance/sources.yaml")):
        topic = path.parent.parent.name
        records = [
            r for r in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("sources") or []
        ]
        if not records:
            continue
        uses = [r.get("permitted_use") for r in records]
        row = InventoryRow(
            kind="source-collection",
            topic=topic,
            id=f"{topic}-sources",
            version=VERSION,
            status="active",
            source=path.relative_to(root).as_posix(),
            permitted_use=strictest_use(uses),
            counts={"sources": len(records)},
            distribution={
                "source_class": dict(sorted(Counter(str(r.get("class")) for r in records).items())),
                "licence": dict(sorted(Counter(str(r.get("licence")) for r in records).items())),
                "permitted_use": dict(sorted(Counter(str(u) for u in uses).items())),
            },
            sha256=canonical_yaml_hash(path),
            availability="register-only",
        )
        snapshots = snapshot_dir(root, topic)
        if snapshots and snapshots.is_dir():
            row.size_mb, row.files = measure(snapshots)
            row.counts["snapshot_files"] = row.files
            row.availability = "measured"
        else:
            row.notes.append("snapshots not on this machine")
        rows.append(row)
    return rows
