"""Score a teacher-candidate or baseline run against the frozen consensus (FR-028, FR-031).

Same metric per dimension as reference agreement, on consensus units. Items matching a contested
reference item are scored neutrally (neither hit nor error) and counted. A chunk without a valid
output counts against the model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from jtbd_pilot.checks import check_run, load_pass_rates
from jtbd_pilot.config import Settings
from jtbd_pilot.consensus import load_consensus
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.freeze import verify_benchmark_frozen
from jtbd_pilot.jsonio import read_json, write_json
from jtbd_pilot.matching import match_items
from jtbd_pilot.metrics import (
    CATEGORY_LABELS,
    EVIDENCE_LABELS,
    composite,
    compute_agreement,
    f1_stat,
    kappa_stat,
    summarize,
)
from jtbd_pilot.runs import load_outputs, load_run_manifest
from jtbd_pilot.schema import evidence_rank

RELEVANCE_LABELS = ["false", "true", "invalid"]


@dataclass
class Target:
    span: tuple[int, int]
    kind: str | None
    values: dict[str, str] = field(default_factory=dict)
    contested_existence: bool = False


def _relevance_label(value: bool | None) -> str:
    return "invalid" if value is None else ("true" if value else "false")


def score_units(consensus: list[dict], contested: list[dict], chunk_ids: list[str],
                outputs: dict, min_iou: float) -> tuple[dict[str, list], Counter]:
    units: dict[str, list] = {d: [] for d in ("relevance", "item_matching", "kind", "actor_type",
                                              "evidence_type", "evidence_scope")}
    neutral: Counter = Counter()
    rel = {c["chunk_id"]: c["value"] for c in consensus if c["level"] == "relevance"}
    contested_rel = {c["chunk_id"] for c in contested if c["level"] == "relevance"}
    for chunk_id in chunk_ids:
        out = outputs.get(chunk_id)
        model_relevant = out.relevant if out else None
        if chunk_id in rel:
            units["relevance"].append(
                (chunk_id, (_relevance_label(model_relevant), _relevance_label(rel[chunk_id]))))
        elif chunk_id in contested_rel:
            neutral["relevance"] += 1

        targets = [Target(tuple(c["span"]), c["values"].get("kind"), c["values"])
                   for c in consensus if c["level"] == "item" and c["chunk_id"] == chunk_id]
        for c in contested:
            if c["chunk_id"] == chunk_id and c["dimensions"] == ["item_existence"]:
                found = c["values"][c["found_by"]]
                targets.append(Target(tuple(c["span"]), found["kind"], contested_existence=True))
        model_items = out.valid_items if out and out.relevant is not None else []
        tp = fp = fn = 0
        for m in match_items(model_items, targets, min_iou):
            if m.a and m.b:
                if m.b.contested_existence:
                    neutral["item_existence"] += 1
                    continue
                tp += 1
                for dim in ("kind", "actor_type", "evidence_scope"):
                    if dim in m.b.values:
                        units[dim].append((chunk_id, (getattr(m.a, dim), m.b.values[dim])))
                    else:
                        neutral[dim] += 1
                if "evidence_type" in m.b.values:
                    units["evidence_type"].append((chunk_id, (
                        evidence_rank(m.a.evidence_type),
                        evidence_rank(m.b.values["evidence_type"]))))
                else:
                    neutral["evidence_type"] += 1
            elif m.a:
                fp += 1
            elif not m.b.contested_existence:
                fn += 1
        units["item_matching"].append((chunk_id, (tp, fp, fn)))
    return units, neutral


def score_run(settings: Settings, run_id: str) -> dict[str, Any]:
    manifest = verify_benchmark_frozen(settings)
    run = load_run_manifest(settings, run_id)
    if run.split != "main":
        raise ValidationFailed("scoring uses the frozen main-split benchmark")
    if run.status != "complete":
        raise ValidationFailed(f"{run_id} is not complete (status {run.status})")
    if run.role == "reference":
        raise ValidationFailed("reference runs are part of the consensus; use `pilot agreement`")
    consensus, contested, meta = load_consensus(settings, "main")
    outputs = load_outputs(settings, run_id)
    units, neutral = score_units(consensus, contested, meta["chunks"], outputs,
                                 float(settings.pilot.get("min_iou", 0.3)))
    dims = {
        "relevance": summarize(units["relevance"], kappa_stat(RELEVANCE_LABELS), "kappa",
                               settings),
        "item_matching": summarize(
            units["item_matching"], f1_stat, "f1", settings,
            unit_count=sum(p[0] + p[1] + p[2] for _, p in units["item_matching"])),
    }
    for dim, labels in CATEGORY_LABELS.items():
        dims[dim] = summarize(units[dim], kappa_stat(labels), "kappa", settings)
    dims["evidence_type"] = summarize(units["evidence_type"],
                                      kappa_stat(EVIDENCE_LABELS, "quadratic"),
                                      "quadratic_weighted_kappa", settings)
    dims = {d: dims[d] for d in ("relevance", "item_matching", "kind", "actor_type",
                                 "evidence_type", "evidence_scope")}

    agreement_path = settings.analysis_dir / "agreement.json"
    if meta.get("single_reference"):
        agreement = None  # spike: one reference, no reference-vs-reference agreement exists
    elif agreement_path.exists():
        agreement = read_json(agreement_path)
    else:
        agreement = compute_agreement(settings, "main")
    model_composite = composite(d["score"] for d in dims.values())
    frontier_a = agreement["composite_consensus_units"] if agreement else None
    frontier_b = agreement["composite_all_units"] if agreement else None
    rates = load_pass_rates(settings, run_id) or check_run(settings, run_id)["pass_rates"]
    result = {
        "run_id": run_id,
        "role": run.role,
        "model_id": run.model_id,
        "model_version": run.model_version,
        "family": run.family,
        "benchmark_version": manifest["version"],
        "test_only": manifest.get("test_only", False),
        "dimensions": dims,
        "composite": model_composite,
        "frontier_composite_consensus_units": frontier_a,
        "frontier_composite_all_units": frontier_b,
        "quality_ratio_a": round(model_composite / frontier_a, 6)
        if model_composite is not None and frontier_a else None,
        "quality_ratio_b": round(model_composite / frontier_b, 6)
        if model_composite is not None and frontier_b else None,
        "neutral_contested_hits": dict(neutral),
        "check_pass_rates": rates,
        "excluded_chunks": len(run.excluded_chunks),
        "license_basis": run.license_basis,
        "quantization": run.quantization,
    }
    write_json(settings.analysis_dir / "scores" / f"{run_id}.json", result)
    return result
