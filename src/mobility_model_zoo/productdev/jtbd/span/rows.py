"""Training rows from the teacher's labels (feature 004, research R7, T025-T026).

`jtbd span build-rows` turns a complete `teacher` run on the train split into one row per usable
chunk: the chunk text, the teacher's relevance decision and its items as character spans (quotes
repaired with the frozen rule of the teacher-scoring configuration), keeping only the attribute
dimensions the model produces. Validation rows are 10% of the snapshots, never single chunks, so
validation never shares a source with training. `jtbd span freeze-data` hashes chunks and rows.
"""

from __future__ import annotations

import random
from collections import Counter
from datetime import UTC, date, datetime
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.ensemble import with_repair
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import sha256_bytes, sha256_text
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, read_jsonl, write_json, write_jsonl
from mobility_model_zoo.productdev.jtbd.runs import load_outputs, load_run_manifest
from mobility_model_zoo.productdev.jtbd.span.recipe import load_recipe, recipe_dimensions
from mobility_model_zoo.productdev.jtbd.span.units import units

MIN_OVERLAP = 0.5  # share of the unit or of the item a unit must cover to take the item


def rows_dir(settings: Settings):
    return settings.data_dir / "rows"


def rows_path(settings: Settings):
    return rows_dir(settings) / "rows.jsonl"


def align_units(text: str, items: list[dict[str, Any]]
                ) -> list[tuple[tuple[int, int], dict[str, Any] | None]]:
    """Each unit of `text` with the item it belongs to (None: no item).

    A unit takes the item that overlaps it most, if the overlap covers at least half of the unit
    or half of the item.
    """
    aligned = []
    for a, b in units(text):
        best, best_overlap = None, 0
        for item in items:
            s, e = item["span"]
            overlap = min(b, e) - max(a, s)
            if overlap > best_overlap:
                best, best_overlap = item, overlap
        if best and (best_overlap >= MIN_OVERLAP * (b - a)
                     or best_overlap >= MIN_OVERLAP * (best["span"][1] - best["span"][0])):
            aligned.append(((a, b), best))
        else:
            aligned.append(((a, b), None))
    return aligned


def validation_snapshots(snapshot_ids: list[str], fraction: float, seed: int) -> set[str]:
    ids = sorted(set(snapshot_ids))
    if len(ids) < 2:
        return set()
    rng = random.Random(seed)
    rng.shuffle(ids)
    return set(ids[:max(1, round(fraction * len(ids)))])


def build_rows(settings: Settings, run_id: str, recipe_file: str | None = None) -> dict[str, Any]:
    if settings.span_train is None:
        raise UsageError("build-rows needs a training dataset config (span_train section)")
    run = load_run_manifest(settings, run_id)
    if run.role != "teacher" or run.split != "train":
        raise ValidationFailed(f"{run_id} is not a teacher run on the train split")
    if run.status != "complete":
        raise ValidationFailed(f"{run_id} is not complete (status {run.status})")
    dims = recipe_dimensions(load_recipe(settings, recipe_file))
    rule = settings.teacher_scoring().quote_repair
    chunks = chunk_map(settings, "train")
    outputs = load_outputs(settings, run_id)
    validation = settings.span_train["validation"]
    val = validation_snapshots([c.snapshot_id for c in chunks.values()],
                               float(validation["fraction_of_snapshots"]), int(validation["seed"]))
    stats: Counter = Counter()
    excluded: Counter = Counter()
    rows = []
    for chunk_id, chunk in sorted(chunks.items()):
        out = outputs.get(chunk_id)
        if out is None or out.relevant is None:
            excluded["no_valid_teacher_output"] += 1
            continue
        stats["items_in"] += len(out.items)
        items = with_repair(out, chunk.text, rule, stats) if out.relevant else []
        if out.relevant and out.items and not items:
            excluded["all_items_dropped"] += 1  # an empty target would teach a wrong "nothing"
            continue
        row_items = [{"span": list(it.span), "kind": it.kind, **{d: getattr(it, d) for d in dims}}
                     for it in sorted(items, key=lambda i: i.span)]
        aligned = sum(1 for _, item in align_units(chunk.text, row_items) if item)
        stats["units_with_item"] += aligned
        rows.append({"chunk_id": chunk_id, "snapshot_id": chunk.snapshot_id, "text": chunk.text,
                     "relevant": out.relevant, "items": row_items,
                     "split": "val" if chunk.snapshot_id in val else "train",
                     "language": chunk.language, "source_type": chunk.source_type,
                     "sub_area": chunk.sub_area})
    write_jsonl(rows_path(settings), rows)
    split_counts = Counter(r["split"] for r in rows)
    result = {
        "run_id": run_id,
        "dimensions": dims,
        "chunks_in": len(chunks),
        "excluded": dict(excluded),
        "rows": len(rows),
        "rows_per_split": {"train": split_counts.get("train", 0),
                           "val": split_counts.get("val", 0)},
        "validation_snapshots": len(val),
        "items_in": stats["items_in"],
        "items_kept": sum(len(r["items"]) for r in rows),
        "items_repaired": stats["repaired"],
        "items_dropped": stats["dropped"],
        "units_with_item": stats["units_with_item"],
        "relevant_rows": sum(1 for r in rows if r["relevant"]),
        "composition": {
            key: dict(sorted(Counter(r[key] for r in rows).items()))
            for key in ("language", "source_type", "sub_area")},
    }
    write_json(rows_dir(settings) / "rows.stats.json", result)
    return result


def load_rows(settings: Settings, split: str | None = None) -> list[dict[str, Any]]:
    path = rows_path(settings)
    if not path.exists():
        raise ValidationFailed(f"no training rows at {path}; run `jtbd span build-rows`")
    rows = list(read_jsonl(path))
    return [r for r in rows if r["split"] == split] if split else rows


def _data_hashes(settings: Settings) -> dict[str, Any]:
    chunks = {c: sha256_text(ch.text) for c, ch in sorted(chunk_map(settings, "train").items())}
    rows_sha = sha256_bytes(rows_path(settings).read_bytes())
    combined = sha256_text("\n".join([*(f"{k}:{v}" for k, v in chunks.items()),
                                      f"rows:{rows_sha}"]))
    return {"chunks": chunks, "rows_sha256": rows_sha, "sha256": combined}


def freeze_data(settings: Settings) -> dict[str, Any]:
    """Hash chunks and rows into frozen.json and write retention.yaml (Principle IX, R17)."""
    if settings.span_train is None:
        raise UsageError("freeze-data needs a training dataset config (span_train section)")
    if not rows_path(settings).exists():
        raise ValidationFailed("no training rows; run `jtbd span build-rows` first")
    current = _data_hashes(settings)
    path = settings.data_dir / "frozen.json"
    if path.exists():
        frozen = read_json(path)
        if frozen["sha256"] != current["sha256"]:
            raise ValidationFailed(f"{settings.span_train.get('dataset')} is already frozen with "
                                   "other content; build a new dataset version instead")
        return {k: v for k, v in frozen.items() if k != "chunks"}
    now = datetime.now(UTC)
    retention = settings.span_train.get("retention") or {}
    months = int(retention.get("review_by_months_after_freeze", 24))
    year, month = divmod(now.month - 1 + months, 12)
    review_by = date(now.year + year, month + 1, min(now.day, 28))
    frozen = {"dataset": settings.span_train.get("dataset"), "frozen_at": now.isoformat(),
              "chunk_count": len(current["chunks"]), **current}
    write_json(path, frozen)
    import yaml

    (settings.data_dir / "retention.yaml").write_text(yaml.safe_dump({
        "dataset": settings.span_train.get("dataset"), "frozen_at": now.isoformat(),
        "rule": retention.get("rule", "while a model trained on it is current"),
        "review_by": review_by.isoformat(), "published": False}, sort_keys=False),
        encoding="utf-8")
    return {k: v for k, v in frozen.items() if k != "chunks"}


def frozen_data(settings: Settings) -> dict[str, Any]:
    """The frozen state, refusing if chunks or rows changed since `freeze-data`."""
    path = settings.data_dir / "frozen.json"
    if not path.exists():
        raise ValidationFailed("training data is not frozen; run `jtbd span freeze-data`")
    frozen = read_json(path)
    if _data_hashes(settings)["sha256"] != frozen["sha256"]:
        raise ValidationFailed("training chunks or rows changed since `jtbd span freeze-data`")
    return frozen
