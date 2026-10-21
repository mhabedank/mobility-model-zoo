"""Frozen benchmarks of the condition-monitoring topic (feature 021, research R1).

A manifest records how each split is derived and the SHA-256 of its subject list and of its data,
never the subject numbers themselves (FR-028). `freeze` writes it once: an identical rebuild is a
no-op, a changed one is refused with `FrozenChanged` (the pattern of security/can_ids/benchmark.py).
`train` and `evaluate` load the manifest and check each split against its data hash before use.

Task-specific code (which dataset, which validation rule) lives with the task, for example
`activity/train.py`; this module only knows splits, hashes and the freeze rule.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from mobility_model_zoo.edge.paths import repo_root

TOPIC = "condition-monitoring"


class FrozenChanged(Exception):
    def __init__(self, path: Path, fields: list[str]):
        self.path, self.fields = path, fields
        super().__init__(
            f"{path} is frozen; these fields would change: {', '.join(fields)}. "
            "A new definition needs a new benchmark version."
        )


class NotFrozen(Exception):
    pass


class SplitChanged(Exception):
    pass


def repo() -> Path:
    """Repository root that holds `topics/` and `configs/` (tests point it at a temporary copy)."""
    return repo_root()


def manifest_path(benchmark: str) -> Path:
    return repo() / "topics" / TOPIC / "benchmarks" / benchmark / "manifest.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def subjects_sha256(subjects: Iterable[int]) -> str:
    """SHA-256 of the sorted, distinct subject numbers joined by commas."""
    text = ",".join(str(s) for s in sorted({int(s) for s in subjects}))
    return hashlib.sha256(text.encode()).hexdigest()


def data_sha256(x: np.ndarray, y: np.ndarray) -> str:
    """SHA-256 of the float32 windows (C order) followed by the int64 labels."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(x, dtype=np.float32).tobytes())
    h.update(np.ascontiguousarray(y, dtype=np.int64).tobytes())
    return h.hexdigest()


def split_subjects(
    train_subjects: Sequence[int], validation_seed: int, divisor: int
) -> tuple[list[int], list[int]]:
    """(training, validation) subjects: validation is one `divisor`-th of the distinct training
    subjects, drawn once with `validation_seed`, so no subject is in both."""
    subs = sorted({int(s) for s in train_subjects})
    n_val = len(subs) // divisor
    if n_val < 1:
        raise ValueError(f"{len(subs)} training subjects are too few for a validation split")
    drawn = np.random.default_rng(validation_seed).choice(subs, size=n_val, replace=False)
    val = sorted(int(s) for s in drawn)
    return [s for s in subs if s not in set(val)], val


def split_entry(subjects: np.ndarray, x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "subjects": len({int(s) for s in subjects}),
        "windows": int(len(y)),
        "subjects_sha256": subjects_sha256(subjects),
        "data_sha256": data_sha256(x, y),
    }


def dataset_entry(ds_id: str) -> dict[str, Any]:
    """Provenance of a downloaded dataset from its `SOURCE.json` (the archive hash is the first
    file's SHA-256)."""
    from mobility_model_zoo.datasets.download import dataset_dir

    path = dataset_dir(ds_id) / "SOURCE.json"
    if not path.exists():
        raise FileNotFoundError(f"{ds_id} not downloaded: zoo data download {ds_id}")
    src = json.loads(path.read_text(encoding="utf-8"))
    return {
        "id": ds_id,
        "licence": src["license"],
        "retrieved_at": src["retrieved_at"],
        "archive_sha256": src["files"][0]["sha256"],
    }


def _dump(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"


def changed_fields(old: Any, new: Any, prefix: str = "") -> list[str]:
    if isinstance(old, dict) and isinstance(new, dict):
        out: list[str] = []
        for k in sorted(set(old) | set(new)):
            out += changed_fields(old.get(k), new.get(k), f"{prefix}{k}.")
        return out
    return [] if old == new else [prefix.rstrip(".")]


def freeze(path: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Write the manifest once. Returns (manifest, written). Identical content (ignoring
    `frozen_at`) is a no-op; any difference raises `FrozenChanged`."""
    body = json.loads(_dump(manifest))
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        old_body = {k: v for k, v in old.items() if k != "frozen_at"}
        if old_body != body:
            raise FrozenChanged(path, changed_fields(old_body, body))
        return old, False
    frozen = {**body, "frozen_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(frozen), encoding="utf-8")
    return frozen, True


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise NotFrozen(f"benchmark not frozen: {path} is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_split(manifest: dict[str, Any], name: str, subjects, x, y) -> None:
    """Refuse a split whose subjects or data differ from the frozen manifest."""
    want = manifest["splits"][name]
    if subjects_sha256(subjects) != want["subjects_sha256"]:
        raise SplitChanged(f"split {name}: subjects differ from the frozen manifest")
    got = data_sha256(x, y)
    if got != want["data_sha256"]:
        raise SplitChanged(
            f"split {name}: data differ from the frozen manifest ({got[:12]}… != "
            f"{want['data_sha256'][:12]}…)"
        )
