"""Go / revise / rethink decision derived mechanically from the frozen criteria (FR-030, FR-031).

Teacher candidates are classified as fit or not fit to generate training data (FR-031a); this
classification is reported alongside the decision and does not change it.

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


def teacher_fitness(criteria: DecisionCriteria, scores: list[dict],
                    frontier_dims: dict[str, float | None] | None = None) -> dict[str, Any]:
    """FR-031a on the repaired view: fit, reasons when not fit, and the recommended teacher.

    `frontier_dims` are the frontier-versus-frontier scores on consensus units; with them the
    reasons name the dimensions that miss the quality ratio.
    """
    rule = criteria.teacher_fitness
    rows = []
    for s in scores:
        if s["role"] != "teacher_candidate":
            continue
        view = s.get("repaired") or {}
        ratio = view.get("quality_ratio_a")
        schema_valid = ((s.get("check_pass_rates") or {}).get("schema_valid") or {}).get("rate")
        reasons = []
        if not view:
            reasons.append("no repaired score (run `pilot score` again)")
        elif ratio is None:
            reasons.append("repaired quality_ratio_a not available")
        elif ratio < rule.min_quality_ratio:
            reasons.append(f"repaired quality_ratio_a {ratio:.3f} < {rule.min_quality_ratio}")
            for dim, ref in (frontier_dims or {}).items():
                score = (view.get("dimensions", {}).get(dim) or {}).get("score")
                if ref is not None and (score is None or score < rule.min_quality_ratio * ref):
                    shown = "n/a" if score is None else f"{score:.3f}"
                    reasons.append(f"{dim} {shown} < {rule.min_quality_ratio} x frontier "
                                   f"{ref:.3f}")
        if schema_valid is None or schema_valid < rule.min_schema_valid:
            shown = "n/a" if schema_valid is None else f"{schema_valid:.3f}"
            reasons.append(f"schema_valid {shown} < {rule.min_schema_valid}")
        rows.append({
            "model_id": s["model_id"],
            "composite": view.get("composite"),
            "quality_ratio_a": ratio,
            "schema_valid": schema_valid,
            "cost_per_chunk_eur": s.get("cost_per_chunk_eur"),
            "fit": not reasons,
            "reasons": reasons,
        })
    fit = [r for r in rows if r["fit"]]
    recommended = None
    if fit:
        best = max(r["composite"] for r in fit)
        close = [r for r in fit if best - r["composite"] <= rule.tie_margin + 1e-12]
        recommended = min(close, key=lambda r: (
            r["cost_per_chunk_eur"] if r["cost_per_chunk_eur"] is not None else float("inf"),
            -r["composite"], r["model_id"]))["model_id"]
    return {
        "rule": f"fit if the repaired composite reaches quality_ratio_a >= "
                f"{rule.min_quality_ratio} (against the frontier-vs-frontier composite on "
                f"consensus units) and schema_valid >= {rule.min_schema_valid}; among fit "
                f"candidates the highest repaired composite is recommended, and within "
                f"{rule.tie_margin} of it the lowest cost per chunk",
        "candidates": rows,
        "recommended": recommended,
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
    main_path = settings.analysis_dir / "agreement.json"  # teachers are scored on the main split
    main_agreement = read_json(main_path) if main_path.exists() else {}
    result.update({
        "benchmark_version": manifest["version"],
        "test_only": manifest.get("test_only", False),
        "criteria_version": criteria.version,
        "decision_split": split,
        "reruns": reruns,
        "rerun": "holdout" if result["decision"] == "revise" else "none",
        "finetuning": finetuning(criteria, scores, perf, frontier),
        "teacher_fitness": teacher_fitness(criteria, scores, main_agreement.get(
            "consensus_unit_scores")),
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
