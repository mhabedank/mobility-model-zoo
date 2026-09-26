"""Composition checks for a split (FR-002 to FR-007, FR-002a, SC-001, SC-010)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.corpus.store import load_chunks
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.jsonio import write_json
from jtbd_pilot.schema import ChunkRecord

SUB_AREAS = ("public_transport_rural", "logistics_delivery", "emobility_charging",
             "car_ownership_use", "sharing_platforms")
SOURCE_TYPES = ("paper", "reddit", "forum_review", "transcript")


def _in(value: float, bounds: list[float]) -> bool:
    return bounds[0] - 1e-9 <= value <= bounds[1] + 1e-9


def composition(chunks: list[ChunkRecord]) -> dict[str, Any]:
    n = len(chunks)
    relevant = [c for c in chunks if c.relevance_intent == "relevant"]
    return {
        "n": n,
        "sub_area": dict(Counter(c.sub_area for c in relevant)),
        "source_type": dict(Counter(c.source_type for c in chunks)),
        "language": dict(Counter(c.language for c in chunks)),
        "region": dict(Counter(c.region for c in chunks)),
        "relevance_intent": dict(Counter(c.relevance_intent for c in chunks)),
        "n_relevant": len(relevant),
    }


def check_targets(
    chunks: list[ChunkRecord], targets: dict[str, Any], split: str,
    substitutions: list[dict[str, Any]], snapshot_ids: set[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    comp = composition(chunks)
    n, n_rel = comp["n"], comp["n_relevant"]
    failures: list[str] = []

    size_key = "main_size" if split == "main" else "holdout_size"
    if not _in(n, targets[size_key]):
        failures.append(f"{split} size {n} outside {targets[size_key]}")
    if n == 0:
        return comp, failures

    for area in SUB_AREAS:
        share = comp["sub_area"].get(area, 0) / n_rel if n_rel else 0.0
        if not _in(share, targets["sub_area_share_of_relevant"]):
            failures.append(f"sub_area {area} share {share:.2f} outside "
                            f"{targets['sub_area_share_of_relevant']}")

    subs = {s["source_type"]: s for s in substitutions}
    for sub in substitutions:
        if not (sub.get("explanation") or "").strip():
            failures.append(f"substitution for {sub.get('source_type')} lacks an explanation")
    for stype in SOURCE_TYPES:
        if stype in subs:
            continue
        low, high = targets["source_type_share"]
        if any(s.get("replaced_by") == stype for s in substitutions):
            high = high * 2
        share = comp["source_type"].get(stype, 0) / n
        if not _in(share, [low, high]):
            failures.append(f"source_type {stype} share {share:.2f} outside {[low, high]}")

    irrelevant = comp["relevance_intent"].get("irrelevant", 0) + comp["relevance_intent"].get(
        "near_miss", 0)
    if not _in(irrelevant / n, targets["irrelevant_or_near_miss_share"]):
        failures.append(f"irrelevant/near-miss share {irrelevant / n:.2f} outside "
                        f"{targets['irrelevant_or_near_miss_share']}")

    non_eu = comp["region"].get("non_EU", 0) / n
    if not _in(non_eu, targets["non_eu_share"]):
        failures.append(f"non-EU share {non_eu:.2f} outside {targets['non_eu_share']}")
    if targets.get("dach_largest_region"):
        dach = comp["region"].get("DACH", 0)
        if dach <= max(comp["region"].get("EU_other", 0), comp["region"].get("non_EU", 0)):
            failures.append("DACH is not the largest regional group")

    for lang in ("de", "en"):
        share = comp["language"].get(lang, 0) / n
        if share < targets["language_min_share"] - 1e-9:
            failures.append(f"language {lang} share {share:.2f} below "
                            f"{targets['language_min_share']}")

    low, high = targets["token_range"]
    for chunk in chunks:
        tokens = chunk.token_count or 0
        if not low <= tokens <= high:
            failures.append(f"{chunk.chunk_id} has {tokens} tokens, outside {low}-{high}")
        if snapshot_ids is not None and chunk.snapshot_id not in snapshot_ids:
            failures.append(f"{chunk.chunk_id} references missing snapshot {chunk.snapshot_id}")
    return comp, failures


def validate_split(settings: Settings, split: str) -> dict[str, Any]:
    chunks = load_chunks(settings, split)
    snapshot_ids = {p.name for p in settings.snapshots_dir.glob("snap-*") if p.is_dir()}
    comp, failures = check_targets(
        chunks,
        settings.pilot["composition"],
        split,
        settings.pilot.get("substitutions") or [],
        snapshot_ids,
    )
    result = {"split": split, "composition": comp, "failures": failures,
              "substitutions": settings.pilot.get("substitutions") or []}
    write_json(settings.analysis_dir / f"composition-{split}.json", result)
    if failures:
        raise ValidationFailed(f"{len(failures)} composition target(s) missed: {failures}")
    return result
