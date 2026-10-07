"""Score a teacher-candidate or baseline run against the frozen consensus (FR-028, FR-031).

Same metric per dimension as reference agreement, on consensus units. Items matching a contested
reference item are scored neutrally (neither hit nor error) and counted. A chunk without a valid
output counts against the model.

Teacher candidates also get a `repaired` view (FR-026a): near-miss quotes are repaired with the
frozen `quote_repair` rule of the teacher-scoring configuration before scoring, because training
data is built from repaired quotes. Check pass rates always refer to the raw output.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from mobility_model_zoo.productdev.jtbd.checks import check_run, load_pass_rates
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.consensus import load_consensus
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import verify_benchmark_frozen
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.matching import match_items
from mobility_model_zoo.productdev.jtbd.metrics import (
    CATEGORY_LABELS,
    EVIDENCE_LABELS,
    composite,
    compute_agreement,
    f1_stat,
    kappa_stat,
    summarize,
)
from mobility_model_zoo.productdev.jtbd.runs import (
    ChunkOutput,
    load_outputs,
    load_run_manifest,
    produced_dimensions,
)
from mobility_model_zoo.productdev.jtbd.schema import evidence_rank

RELEVANCE_LABELS = ["false", "true", "invalid"]
ALL_DIMENSIONS = ("relevance", "item_matching", "kind", "actor_type", "evidence_type",
                  "evidence_scope")
# Always scored; the attribute dimensions only when the model produces them (feature 004).
CORE_DIMENSIONS = ("relevance", "item_matching", "kind")
ATTRIBUTES = ("actor_type", "evidence_type", "evidence_scope")


def not_produced() -> dict[str, Any]:
    """Score entry of a dimension the model does not produce: reported, never 0, never mixed in."""
    return {"status": "not_produced", "score": None, "n": 0}


def comparison_composite(dimensions: dict[str, Any], names: list[str] | tuple[str, ...]
                         ) -> float | None:
    """The composite over exactly `names` (spec FR-015), from a score file's `dimensions`.

    Every dimension in `names` must be scored; a missing or not-produced one makes the
    comparison undefined (None) instead of silently shrinking the set.
    """
    scores = []
    for name in names:
        entry = dimensions.get(name)
        if not isinstance(entry, dict) or entry.get("status") == "not_produced":
            return None
        scores.append(entry.get("score"))
    if any(v is None for v in scores):
        return None
    return composite(scores)


@dataclass
class Target:
    span: tuple[int, int]
    kind: str | None
    values: dict[str, str] = field(default_factory=dict)
    contested_existence: bool = False


def _relevance_label(value: bool | None) -> str:
    return "invalid" if value is None else ("true" if value else "false")


def score_units(consensus: list[dict], contested: list[dict], chunk_ids: list[str],
                outputs: dict, min_iou: float, attributes: tuple[str, ...] = ATTRIBUTES
                ) -> tuple[dict[str, list], Counter]:
    """Scoring units per dimension. Attribute dimensions outside `attributes` (not produced by
    the model) get no units at all."""
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
                    if dim != "kind" and dim not in attributes:
                        continue
                    if dim in m.b.values:
                        units[dim].append((chunk_id, (getattr(m.a, dim), m.b.values[dim])))
                    else:
                        neutral[dim] += 1
                if "evidence_type" in attributes:
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


def _ratio(value: float | None, reference: float | None) -> float | None:
    return round(value / reference, 6) if value is not None and reference else None


def _dimensions(settings: Settings, consensus: list[dict], contested: list[dict],
                chunk_ids: list[str], outputs: dict, min_iou: float,
                attributes: tuple[str, ...] = ATTRIBUTES) -> tuple[dict, Counter]:
    units, neutral = score_units(consensus, contested, chunk_ids, outputs, min_iou, attributes)
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
    dims = {d: dims[d] if d in CORE_DIMENSIONS or d in attributes else not_produced()
            for d in ALL_DIMENSIONS}
    return dims, neutral


def repaired_view(settings: Settings, outputs: dict[str, ChunkOutput]
                  ) -> tuple[dict[str, ChunkOutput], Counter]:
    """Outputs with near-miss quotes repaired by the frozen `quote_repair` rule (FR-026a)."""
    from mobility_model_zoo.productdev.jtbd.ensemble import with_repair

    rule = settings.teacher_scoring().quote_repair
    chunks = chunk_map(settings, "main")
    stats: Counter = Counter()
    repaired = {}
    for chunk_id, out in outputs.items():
        if out.relevant is None:
            repaired[chunk_id] = out
            continue
        items = with_repair(out, chunks[chunk_id].text, rule, stats)
        repaired[chunk_id] = ChunkOutput(chunk_id, out.relevant, items)
    return repaired, stats


def score_run(settings: Settings, run_id: str) -> dict[str, Any]:
    manifest = verify_benchmark_frozen(settings)
    run = load_run_manifest(settings, run_id)
    if run.split != "main":
        raise ValidationFailed("scoring uses the frozen main-split benchmark")
    if run.status != "complete":
        raise ValidationFailed(f"{run_id} is not complete (status {run.status})")
    if run.role == "reference":
        raise ValidationFailed("reference runs are part of the consensus; use `jtbd agreement`")
    if run.role == "teacher":
        raise ValidationFailed("teacher runs label the training split; they are not scored")
    produced = produced_dimensions(run)
    attributes = ATTRIBUTES if produced is None else tuple(a for a in ATTRIBUTES if a in produced)
    consensus, contested, meta = load_consensus(settings, "main")
    outputs = load_outputs(settings, run_id)
    min_iou = float(settings.pilot.get("min_iou", 0.3))
    dims, neutral = _dimensions(settings, consensus, contested, meta["chunks"], outputs, min_iou,
                                attributes)

    agreement_path = settings.analysis_dir / "agreement.json"
    if meta.get("single_reference"):
        agreement = None  # spike: one reference, no reference-vs-reference agreement exists
    elif agreement_path.exists():
        agreement = read_json(agreement_path)
    else:
        agreement = compute_agreement(settings, "main")
    model_composite = composite(d["score"] for d in dims.values()
                                if d.get("status") != "not_produced")
    frontier_a = agreement["composite_consensus_units"] if agreement else None
    frontier_b = agreement["composite_all_units"] if agreement else None
    repaired = None
    if run.role == "teacher_candidate":
        repaired_outputs, stats = repaired_view(settings, outputs)
        repaired_dims, _ = _dimensions(settings, consensus, contested, meta["chunks"],
                                       repaired_outputs, min_iou)
        repaired_composite = composite(d["score"] for d in repaired_dims.values())
        repaired = {
            "dimensions": repaired_dims,
            "composite": repaired_composite,
            "quality_ratio_a": _ratio(repaired_composite, frontier_a),
            "quality_ratio_b": _ratio(repaired_composite, frontier_b),
            "repair_stats": {k: stats[k] for k in ("invalid_quotes", "repaired", "dropped")},
        }
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
        "quality_ratio_a": _ratio(model_composite, frontier_a),
        "quality_ratio_b": _ratio(model_composite, frontier_b),
        "neutral_contested_hits": dict(neutral),
        "check_pass_rates": rates,
        "excluded_chunks": len(run.excluded_chunks),
        "license_basis": run.license_basis,
        "quantization": run.quantization,
        "cost_per_chunk_eur": round(run.cost_eur / len(outputs), 6) if outputs else None,
    }
    if repaired is not None:
        result["repaired"] = repaired
    if run.role == "student":
        names = [*CORE_DIMENSIONS, *attributes]
        result["produced_dimensions"] = list(attributes)
        result["comparison_composite"] = {"dimensions": names,
                                          "value": comparison_composite(dims, names)}
    write_json(settings.analysis_dir / "scores" / f"{run_id}.json", result)
    return result
