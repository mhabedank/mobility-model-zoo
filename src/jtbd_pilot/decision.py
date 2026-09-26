"""Go / revise / rethink decision derived mechanically from the frozen criteria (FR-030, FR-031).

After one holdout rerun the decision uses the holdout agreement, and a dimension that still misses
its threshold leads to rethink. A second rerun is never offered.
"""

from __future__ import annotations

from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.freeze import set_pilot_state, verify_benchmark_frozen
from jtbd_pilot.jsonio import read_json, write_json
from jtbd_pilot.schema import DecisionCriteria

THRESHOLD_KEYS = {
    "relevance": "relevance_kappa",
    "item_matching": "item_matching_f1",
    "kind": "kind_kappa",
    "actor_type": "actor_type_kappa",
    "evidence_type": "evidence_type_weighted_kappa",
    "evidence_scope": "evidence_scope_kappa",
}


def evaluate(criteria: DecisionCriteria, dims: dict[str, Any], reruns: int) -> dict[str, Any]:
    thresholds = criteria.thresholds.model_dump()
    per_dim: dict[str, dict[str, Any]] = {}
    path: list[str] = []
    for dim, key in THRESHOLD_KEYS.items():
        score = dims[dim]["score"]
        passed = score is not None and score >= thresholds[key]
        per_dim[dim] = {"score": score, "threshold": thresholds[key], "passed": passed,
                        "decision": "go" if passed else "revise"}
    evidence = dims["evidence_type"]["score"]
    rethink_below = criteria.rethink_below["evidence_type_weighted_kappa"]
    band = criteria.revise_band["evidence_type_weighted_kappa"]
    failing = [d for d, v in per_dim.items() if not v["passed"]]

    if evidence is not None and evidence < rethink_below:
        per_dim["evidence_type"]["decision"] = "rethink"
        path.append(f"evidence_type weighted kappa {evidence:.3f} < {rethink_below} -> rethink "
                    "the evidence scale (takes precedence over revise)")
        overall = "rethink"
    elif not failing:
        path.append("all dimensions meet their thresholds -> go")
        overall = "go"
    elif reruns >= criteria.max_reruns:
        for dim in failing:
            per_dim[dim]["decision"] = "rethink"
        path.append(f"after {reruns} rerun(s), {failing} still miss their thresholds on the "
                    f"{criteria.rerun_decision_split} split -> rethink (no further rerun)")
        overall = "rethink"
    else:
        for dim in failing:
            score = per_dim[dim]["score"]
            shown = "n/a" if score is None else f"{score:.3f}"
            if dim == "evidence_type" and score is not None and band[0] <= score < band[1]:
                path.append(f"evidence_type weighted kappa {shown} in [{band[0]}, {band[1]}) "
                            "-> revise definitions and rerun")
            else:
                path.append(f"{dim} {shown} < {per_dim[dim]['threshold']} -> revise")
        overall = "revise"
    return {"per_dimension": per_dim, "path": path, "decision": overall}


def finetuning(criteria: DecisionCriteria, scores: list[dict], perf: dict[str, dict],
               frontier: dict | None) -> dict[str, Any]:
    rule = criteria.finetuning_optional
    baselines = [s for s in scores if s["role"] == "baseline"]
    rows = []
    for s in baselines:
        p = perf.get(s["model_id"])
        throughput_ratio = None
        if p and frontier and frontier.get("chunks_per_min") and p.get("chunks_per_min"):
            throughput_ratio = round(p["chunks_per_min"] / frontier["chunks_per_min"], 4)
        rows.append({
            "model_id": s["model_id"],
            "quality_ratio_a": s["quality_ratio_a"],
            "quality_ratio_b": s["quality_ratio_b"],
            "throughput_ratio": throughput_ratio,
            "meets_rule": bool(
                s["quality_ratio_a"] is not None and throughput_ratio is not None
                and s["quality_ratio_a"] >= rule.min_quality_ratio
                and throughput_ratio >= rule.min_throughput_ratio),
        })
    if not rows or all(r["throughput_ratio"] is None for r in rows):
        status = "undetermined"
    else:
        status = "optional" if any(r["meets_rule"] for r in rows) else "required"
    return {
        "status": status,
        "rule": f"quality_ratio_a >= {rule.min_quality_ratio} and throughput_ratio >= "
                f"{rule.min_throughput_ratio} (throughput against the GPT mini-tier reference, "
                "which makes the 10x hurdle stricter than against a flagship)",
        "models": rows,
    }


def load_scores(settings: Settings) -> list[dict]:
    directory = settings.analysis_dir / "scores"
    return [read_json(p) for p in sorted(directory.glob("*.json"))] if directory.exists() else []


def load_perf(settings: Settings) -> tuple[dict[str, dict], dict | None]:
    directory = settings.analysis_dir / "perf"
    perf, frontier = {}, None
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            data = read_json(path)
            if path.name == "frontier.json":
                frontier = data
            else:
                perf[data["model_id"]] = data
    return perf, frontier


def decide(settings: Settings) -> dict[str, Any]:
    manifest = verify_benchmark_frozen(settings)
    criteria = settings.criteria()
    reruns = int(manifest.get("reruns", 0))
    split = criteria.rerun_decision_split if reruns else "main"
    path = settings.analysis_dir / ("agreement.json" if split == "main"
                                    else f"agreement-{split}.json")
    if not path.exists():
        raise ValidationFailed(f"missing {path.name}: run `pilot agreement --split {split}`")
    agreement = read_json(path)
    result = evaluate(criteria, agreement["dimensions"], reruns)
    perf, frontier = load_perf(settings)
    scores = load_scores(settings)
    result.update({
        "benchmark_version": manifest["version"],
        "test_only": manifest.get("test_only", False),
        "criteria_version": criteria.version,
        "decision_split": split,
        "reruns": reruns,
        "rerun": "holdout" if result["decision"] == "revise" else "none",
        "finetuning": finetuning(criteria, scores, perf, frontier),
        "deviations": sorted({d for s in _run_manifests(settings) for d in s.get("deviations", [])}),
    })
    if reruns and split != "main":
        main_path = settings.analysis_dir / "agreement.json"
        if main_path.exists():
            result["main_split_agreement_optimistic"] = {
                d: v["score"] for d, v in read_json(main_path)["dimensions"].items()}
    write_json(settings.analysis_dir / "decision.json", result)
    set_pilot_state(settings, "revise" if result["decision"] == "revise" else "decided",
                    f"decision: {result['decision']}")
    return result


def _run_manifests(settings: Settings) -> list[dict]:
    return [read_json(p) for p in sorted(settings.runs_dir.glob("run-*/manifest.json"))]
