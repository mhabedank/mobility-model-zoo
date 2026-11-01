"""Which model versions use which data (FR-002 "models that use it").

* Datasets: the register's `used_by` plus every release record whose provenance names the dataset.
* Benchmarks: every release record whose `evaluation.benchmark` is the version.
* Training sets: every release record whose recipe configuration names the training set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .rows import InventoryRow


def release_records(root: Path) -> list[tuple[str, str, dict[str, Any]]]:
    out = []
    for path in sorted((root / "zoo" / "models").glob("*/releases/*.yaml")):
        if path.name.count(".") != 3:  # <version>.yaml has exactly the version's two dots
            continue
        try:
            rec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        out.append((path.parents[1].name, str(rec.get("version") or path.stem), rec))
    return out


def _recipe_dataset(root: Path, rec: dict[str, Any], cache: dict[str, str | None]) -> str | None:
    config = (rec.get("recipe") or {}).get("config")
    if not config or not config.endswith((".yaml", ".yml")):
        return None
    if config not in cache:
        path = root / config
        try:
            cache[config] = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("dataset")
        except (OSError, yaml.YAMLError):
            cache[config] = None
    return cache[config]


def resolve(root: Path, rows: list[InventoryRow]) -> None:
    records = release_records(root)
    configs: dict[str, str | None] = {}
    for row in rows:
        users = set(row.used_by)
        for model, version, rec in records:
            ref = f"{model}@{version}"
            if row.kind == "dataset":
                if any(
                    s.get("dataset") == row.id
                    for s in (rec.get("provenance") or {}).get("sources") or []
                ):
                    users.add(ref)
            elif row.kind == "benchmark":
                if (rec.get("evaluation") or {}).get("benchmark") == row.version:
                    users.add(ref)
            elif row.kind == "training-set":
                if _recipe_dataset(root, rec, configs) == row.version:
                    users.add(ref)
        row.used_by = sorted(users)
