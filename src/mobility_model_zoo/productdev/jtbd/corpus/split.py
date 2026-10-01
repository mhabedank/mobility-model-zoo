"""Stratified main/holdout split (FR-002a) by sub-area x source type x language."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks, save_chunk
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import load_manifest


def stratified_holdout(chunk_keys: dict[str, tuple], holdout: int, seed: int) -> set[str]:
    """Pick `holdout` ids with largest-remainder allocation over strata."""
    total = len(chunk_keys)
    if not 0 <= holdout <= total:
        raise UsageError(f"holdout {holdout} must be between 0 and {total}")
    strata: dict[tuple, list[str]] = defaultdict(list)
    for chunk_id, key in sorted(chunk_keys.items()):
        strata[key].append(chunk_id)
    rng = random.Random(seed)
    for ids in strata.values():
        rng.shuffle(ids)
    quotas = {key: holdout * len(ids) / total for key, ids in strata.items()}
    alloc = {key: int(q) for key, q in quotas.items()}
    remaining = holdout - sum(alloc.values())
    order = sorted(strata, key=lambda k: (-(quotas[k] - alloc[k]), str(k)))
    for key in order[:remaining]:
        alloc[key] += 1
    picked: set[str] = set()
    for key, ids in strata.items():
        picked.update(ids[: alloc[key]])
    return picked


def split_corpus(settings: Settings, holdout: int, seed: int) -> dict[str, Any]:
    manifest = load_manifest(settings)
    if manifest:
        raise ValidationFailed(
            f"benchmark {manifest['version']} is already frozen; the split cannot change"
        )
    chunks = load_chunks(settings)
    keys = {c.chunk_id: (c.sub_area, c.source_type, c.language) for c in chunks}
    picked = stratified_holdout(keys, holdout, seed)
    for chunk in chunks:
        chunk.split = "holdout" if chunk.chunk_id in picked else "main"
        save_chunk(settings, chunk)
    return {"main": len(chunks) - len(picked), "holdout": len(picked), "seed": seed}
