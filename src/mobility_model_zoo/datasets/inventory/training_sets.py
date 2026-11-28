"""Frozen training sets (research R11): today the span model's `span-train-v*`.

The configuration names the data directory (`paths.data`, outside git); `frozen.json` holds the
freeze date and hash, `rows/rows.stats.json` the row counts and the composition by language,
source type and sub-area. Without the data on this machine only the configuration is known.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .rows import InventoryRow
from .third_party import measure

CONFIG_GLOB = "configs/*/*/*.yaml"


def configs(root: Path) -> list[tuple[Path, dict]]:
    out = []
    for path in sorted(root.glob(CONFIG_GLOB)):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and isinstance(data.get("span_train"), dict):
            out.append((path, data))
    return out


def _family(name: str) -> str:
    return re.sub(r"-v\d+$", "", name)


def collect(root: Path) -> list[InventoryRow]:
    rows = []
    for path, cfg in configs(root):
        name = cfg["span_train"].get("dataset") or cfg.get("benchmark_version")
        topic = path.relative_to(root).parts[1]  # configs/<topic>/<task>/<file>
        row = InventoryRow(
            kind="training-set",
            topic=topic,
            id=_family(name),
            version=name,
            status="frozen",
            source=path.relative_to(root).as_posix(),
            lineage=[{"relation": "built_from", "target": f"{topic}-sources@current"}],
            permitted_use="training_allowed",  # the training guard admits only such sources
            availability="register-only",
            notes=["built only from sources that allow training (training guard)"],
        )
        data_dir = root / ((cfg.get("paths") or {}).get("data") or f"data/{name}")
        frozen = data_dir / "frozen.json"
        if frozen.is_file():
            meta = json.loads(frozen.read_text(encoding="utf-8"))
            row.frozen_at = str(meta.get("frozen_at") or "")[:10] or None
            row.sha256 = meta.get("sha256")
            row.counts["chunks"] = int(meta.get("chunk_count") or len(meta.get("chunks") or {}))
            row.size_mb, row.files = measure(data_dir)
            row.availability = "measured"
            stats_path = data_dir / "rows" / "rows.stats.json"
            if stats_path.is_file():
                stats = json.loads(stats_path.read_text(encoding="utf-8"))
                per_split = stats.get("rows_per_split") or {}
                row.counts.update(
                    {
                        "rows": int(stats.get("rows") or 0),
                        "rows_train": int(per_split.get("train") or 0),
                        "rows_val": int(per_split.get("val") or 0),
                        "relevant_rows": int(stats.get("relevant_rows") or 0),
                        "items_kept": int(stats.get("items_kept") or 0),
                        "items_dropped": int(stats.get("items_dropped") or 0),
                    }
                )
                for key, values in (stats.get("composition") or {}).items():
                    row.distribution[key] = {str(k): int(v) for k, v in values.items()}
            else:
                row.availability = "partial"
                row.notes.append("rows.stats.json missing")
        else:
            row.notes.append("training set not on this machine")
        rows.append(row)
    return rows
