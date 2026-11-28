"""Third-party datasets of the topic registers, measured where they are downloaded (FR-002, FR-003).

Only `SOURCE.json` is read; every other file under `$MMZ_DATA/<id>/` is only `stat()`ed (FR-008).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .hashes import dataset_hash
from .rows import REGISTER_VERSION, InventoryRow


def measure(directory: Path) -> tuple[float, int]:
    """(size in MB, file count) of a directory tree, without opening any file."""
    total, count = 0, 0
    for base, _dirs, names in os.walk(directory):
        for name in names:
            try:
                total += (Path(base) / name).stat().st_size
            except OSError:
                continue
            count += 1
    return round(total / 1_000_000, 1), count


def collect(root: Path, data_root: Path) -> list[InventoryRow]:
    from mobility_model_zoo.datasets.registry import declarations

    rows: list[InventoryRow] = []
    topics_of: dict[str, list[str]] = {}
    for topic, rec in declarations(root):
        topics_of.setdefault(rec.get("id"), []).append(topic)
    for topic, rec in declarations(root):
        rid = rec.get("id")
        source = f"topics/{topic}/compliance/datasets.yaml"
        if len(topics_of[rid]) > 1:
            if topic != topics_of[rid][0]:
                continue
            rows.append(
                InventoryRow(
                    kind="dataset",
                    topic=topic,
                    id=rid,
                    version=REGISTER_VERSION,
                    status=rec.get("status", "active"),
                    source=source,
                    availability="error",
                    notes=[
                        f"declared in topics {', '.join(topics_of[rid])}; "
                        "`zoo data validate` refuses this"
                    ],
                )
            )
            continue
        row = InventoryRow(
            kind="dataset",
            topic=topic,
            id=rid,
            version=REGISTER_VERSION,
            status=rec.get("status", "active"),
            source=source,
            licence=rec.get("licence"),
            permitted_use=rec.get("permitted_use"),
            redistribution=rec.get("redistribution"),
            approx_size_mb=rec.get("approx_size_mb"),
            used_by=list(rec.get("used_by") or []),
            availability="register-only",
        )
        directory = data_root / rid
        manifest = directory / "SOURCE.json"
        if manifest.is_file():
            try:
                meta = json.loads(manifest.read_text(encoding="utf-8"))
                row.version = str(meta.get("retrieved_at") or "")[:10] or REGISTER_VERSION
                row.sha256 = dataset_hash(meta)
                row.size_mb, row.files = measure(directory)
                row.availability = "measured"
            except (OSError, ValueError) as e:
                row.availability = "error"
                row.notes.append(f"SOURCE.json unreadable: {e.__class__.__name__}")
        else:
            row.notes.append("not downloaded here")
        rows.append(row)
    return rows
