"""`jtbd span data-check`: provenance and composition of a training dataset (FR-004, SC-006, R2).

Every training chunk must come from a `training_allowed` snapshot that shares no source with the
excluded benchmark's main or holdout chunks and is not spike data, and must have passed the
redaction check. Composition is reported against the config's targets, not enforced.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus import separation
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import write_json
from mobility_model_zoo.productdev.jtbd.sources.snapshot import load_snapshot

SUB_AREAS = ("public_transport_rural", "logistics_delivery", "emobility_charging",
             "car_ownership_use", "sharing_platforms")


def _share(counter: Counter, total: int) -> dict[str, float]:
    return {k: round(v / total, 4) for k, v in sorted(counter.items())} if total else {}


def composition(chunks: list, targets: dict[str, Any]) -> dict[str, Any]:
    total = len(chunks)
    languages = Counter(c.language for c in chunks)
    source_types = Counter(c.source_type for c in chunks)
    sub_areas = Counter(c.sub_area for c in chunks)
    offtopic = sum(1 for c in chunks if c.relevance_intent != "relevant")
    result: dict[str, Any] = {
        "chunks": total,
        "language_share": _share(languages, total),
        "source_type_counts": dict(sorted(source_types.items())),
        "sub_area_counts": dict(sorted(sub_areas.items())),
        "offtopic_share": round(offtopic / total, 4) if total else 0.0,
    }
    met = {}
    for language, minimum in (targets.get("min_share_per_language") or {}).items():
        met[f"language_{language}"] = result["language_share"].get(language, 0.0) >= minimum
    if "min_offtopic_share" in targets:
        met["offtopic_share"] = result["offtopic_share"] >= targets["min_offtopic_share"]
    if "min_source_types" in targets:
        met["source_types"] = len(source_types) >= targets["min_source_types"]
    if targets.get("all_sub_areas"):
        met["all_sub_areas"] = all(sub_areas.get(a) for a in SUB_AREAS)
    result["targets"] = targets
    result["targets_met"] = met
    return result


def _compliance_train(settings: Settings, origins: list[str],
                      chunks: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    """Train-stage checks of the compliance harness (feature 006, C-T1 … C-T5)."""
    from mobility_model_zoo.compliance.findings import StageFailed
    from mobility_model_zoo.compliance.hashing import url_hasher
    from mobility_model_zoo.compliance.ingest import harness_present
    from mobility_model_zoo.compliance.register import Register
    from mobility_model_zoo.compliance.train import check_training, suppressed_identifier_findings
    from mobility_model_zoo.compliance.usage import declared_class

    if not harness_present(settings.base):
        if settings.test_fixture:
            return {"checked": False, "findings": []}
        raise ValidationFailed("no compliance register (compliance/controller.yaml); training refused")
    reg = Register.load(settings.base)
    import json

    # The teachers whose labels the training rows use: every teacher run of this dataset.
    teachers = sorted({json.loads(m.read_text(encoding="utf-8")).get("model_id")
                       for m in settings.runs_dir.glob("*/manifest.json")
                       if json.loads(m.read_text(encoding="utf-8")).get("role") == "teacher"})
    target = declared_class(settings.base, (settings.span_train or {}).get("model"))
    findings = check_training(reg, origins=origins, model_licence=None, teachers=teachers,
                              url_hash=url_hasher(), usage_class=target)
    findings += suppressed_identifier_findings(reg, chunks or [], url_hasher())
    return {"checked": True, "findings": StageFailed(findings).failures if findings else []}


def data_check(settings: Settings) -> dict[str, Any]:
    if settings.span_train is None:
        raise UsageError("data-check needs a training dataset config (span_train section)")
    chunks = load_chunks(settings, "train")
    if not chunks:
        raise ValidationFailed(f"no training chunks in {settings.chunks_dir}")
    bench = separation.benchmark_sources(settings)
    spike = separation.spike_snapshot_ids(settings)
    counts: Counter = Counter()
    violating: list[dict[str, Any]] = []
    sources: Counter = Counter()
    rules_by_snapshot: dict[str, list[str]] = {}
    for chunk in chunks:
        snapshot = load_snapshot(settings, chunk.snapshot_id)
        problems = []
        if snapshot.permitted_uses != "training_allowed":
            problems.append("not_training_allowed")
        if chunk.snapshot_id not in rules_by_snapshot:
            rules_by_snapshot[chunk.snapshot_id] = separation.violations(
                settings, chunk.snapshot_id, bench, spike)
        rules = rules_by_snapshot[chunk.snapshot_id]
        if any(r != "spike_data" for r in rules):
            problems.append("shared_with_benchmark")
        if "spike_data" in rules:
            problems.append("spike_data")
        if not chunk.redaction.check_passed:
            problems.append("redaction_not_passed")
        counts.update(problems)
        if problems:
            violating.append({"chunk_id": chunk.chunk_id, "snapshot_id": chunk.snapshot_id,
                              "problems": problems, "rules": rules})
        sources[(snapshot.origin_url, snapshot.license, snapshot.permitted_uses)] += 1
    result = {
        "dataset": settings.span_train.get("dataset"),
        "excluded_benchmark": str(settings.span_train.get("exclude_benchmark")),
        "chunks": len(chunks),
        "violations": {k: counts.get(k, 0) for k in ("not_training_allowed",
                                                       "shared_with_benchmark", "spike_data",
                                                       "redaction_not_passed")},
        "violating_chunks": violating,
        "sources": [{"origin": o, "license": lic, "permitted_use": use, "count": n}
                    for (o, lic, use), n in sorted(sources.items())],
        "composition": composition(chunks, settings.span_train.get("composition_targets") or {}),
    }
    result["compliance"] = _compliance_train(settings, [s["origin"] for s in result["sources"]],
                                             [(c.chunk_id, c.text) for c in chunks])
    write_json(settings.data_dir / "analysis" / "provenance.json", result)
    if result["compliance"]["findings"]:
        raise ValidationFailed("compliance train check failed: "
                               + "; ".join(result["compliance"]["findings"][:10]))
    if violating:
        raise ValidationFailed(f"{len(violating)} training chunk(s) violate provenance rules: "
                               f"{result['violations']} (details in analysis/provenance.json)")
    return {k: v for k, v in result.items() if k != "violating_chunks"}
