"""Results files, candidate selection and the release bar of the span model (T032, research R14).

Run with the benchmark config (`jtbd --config configs/productdev/jtbd/pilot-v1.yaml span …`).
Every number the model card shows becomes a metric in the zoo results files (gate rule 9),
including the comparison numbers: the comparison composite (spec FR-015: the composite over
exactly the dimensions the model outputs, computed the same way for every compared model) of the
best zero-shot baseline, the teacher and the frontier reference, and 85% of the latter.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd.checks import consistency_rate
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.decision import load_scores
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.runs import load_run_manifest
from mobility_model_zoo.productdev.jtbd.scoring import comparison_composite
from mobility_model_zoo.productdev.jtbd.span.evaluate import (
    MODEL_ID,
    dataset_settings,
    load_candidates,
    save_candidates,
)
from mobility_model_zoo.productdev.jtbd.span.recipe import check_release_bar, load_recipe

REFERENCE_SHARE = 0.85  # pilot FR-031: a small model is acceptable at 85% of the reference


def _today() -> str:
    return date.today().isoformat()


def _score_file(settings: Settings, run_id: str) -> dict[str, Any]:
    path = settings.analysis_dir / "scores" / f"{run_id}.json"
    if not path.exists():
        raise ValidationFailed(f"no score for {run_id}; run `jtbd score --run {run_id}`")
    return read_json(path)


def _agreement(settings: Settings) -> dict[str, Any]:
    path = settings.analysis_dir / "agreement.json"
    if not path.exists():
        raise ValidationFailed("no agreement.json; run `jtbd agreement` on the benchmark")
    return read_json(path)


def reference_label(settings: Settings, agreement: dict[str, Any]) -> str:
    models = [load_run_manifest(settings, r).model_id for r in agreement["reference_runs"]]
    return f"the consensus of {' and '.join(models)} (frontier reference models)"


def comparisons(settings: Settings, names: list[str]) -> dict[str, Any]:
    """Comparison composites over `names` for the baselines, the teacher and the reference."""
    scores = load_scores(settings)
    baselines = sorted(
        ({"model_id": s["model_id"],
          "comparison_composite": comparison_composite(s["dimensions"], names),
          "composite": s["composite"]} for s in scores if s["role"] == "baseline"),
        key=lambda b: (-(b["comparison_composite"] or -1), b["model_id"]))
    decision_path = settings.analysis_dir / "decision.json"
    teacher_id = ((read_json(decision_path).get("teacher_fitness") or {}).get("recommended")
                  if decision_path.exists() else None)
    teacher = next((s for s in scores if s["role"] == "teacher_candidate"
                    and s["model_id"] == teacher_id), None)
    agreement = _agreement(settings)
    consensus_units = {d: {"score": v} for d, v in agreement["consensus_unit_scores"].items()}
    reference_all = comparison_composite(agreement["dimensions"], names)
    reference_consensus = comparison_composite(consensus_units, names)
    return {
        "baselines": baselines,
        "best_baseline": baselines[0] if baselines else None,
        "teacher": None if teacher is None else {
            "model_id": teacher["model_id"],
            "comparison_composite": comparison_composite(teacher["dimensions"], names),
            "comparison_composite_repaired": comparison_composite(
                (teacher.get("repaired") or {}).get("dimensions", {}), names)},
        "reference_all_units": reference_all,
        "reference_consensus_units": reference_consensus,
        "reference_share_mark": None if reference_consensus is None
        else round(REFERENCE_SHARE * reference_consensus, 6),
        "reference": reference_label(settings, agreement),
        "contested_count": agreement.get("contested_count", 0),
        "chunks": agreement.get("chunks"),
    }


def bar_conditions(recipe: dict[str, Any], score: dict[str, Any], perf: dict[str, Any],
                   table: dict[str, Any]) -> list[dict[str, Any]]:
    """Each release-bar condition (spec FR-015, FR-009) with value, limit and pass."""
    bar = recipe["release_bar"]
    value = (score.get("comparison_composite") or {}).get("value")
    best = table["best_baseline"]
    rates = score.get("check_pass_rates") or {}
    checks = {"quotes_verbatim": (rates.get("quote_verbatim") or {}).get("rate"),
              "schema_valid": (rates.get("schema_valid") or {}).get("rate"),
              "consistency": consistency_rate(rates)}
    rows = [{
        "condition": "comparison composite above every zero-shot baseline",
        "value": value, "limit": None if best is None else best["comparison_composite"],
        "detail": None if best is None else f"best baseline {best['model_id']}",
        "passed": bool(best and value is not None and best["comparison_composite"] is not None
                       and value > best["comparison_composite"]),
    }]
    for name, minimum in bar["deterministic_checks"].items():
        rows.append({"condition": f"{name} rate", "value": checks.get(name), "limit": minimum,
                     "passed": checks.get(name) is not None and checks[name] >= minimum})
    peak_gb = perf["peak_rss_mb"] / 1024
    rows.append({"condition": "peak RAM (GB)", "value": round(peak_gb, 3),
                 "limit": bar["max_peak_ram_gb"], "passed": peak_gb <= bar["max_peak_ram_gb"]})
    rows.append({"condition": "latency for the 9,000-character text (s)",
                 "value": perf["latency_9k_chars_s"], "limit": bar["max_latency_s_9k"],
                 "passed": perf["latency_9k_chars_s"] <= bar["max_latency_s_9k"]})
    return rows


def _perf_file(settings: Settings, sha: str) -> dict[str, Any] | None:
    matches = sorted((settings.analysis_dir / "perf").glob(f"*-{sha[:12]}.json"))
    perfs = [read_json(p) for p in matches]
    perfs = [p for p in perfs if p.get("model_sha256") == sha]
    return perfs[-1] if perfs else None


def select(settings: Settings, recipe_file: str | None = None) -> dict[str, Any]:
    """Apply `selection.rule` to every evaluated candidate (span-xlmr.yaml, fixed in advance)."""
    recipe = load_recipe(settings, recipe_file)
    dataset = dataset_settings(settings, recipe)
    candidates = load_candidates(dataset)
    if not candidates:
        raise ValidationFailed("no evaluated candidates; run `jtbd span label` first")
    margin = float(recipe["selection"].get("tie_margin", 0.02))
    ranking = []
    for candidate in candidates:
        score = _score_file(settings, candidate["run_id"])
        perf = _perf_file(settings, candidate["model_sha256"])
        if perf is None:
            raise ValidationFailed(f"candidate {candidate['candidate_id']} has no perf file; "
                                   "run `jtbd perf --backend span` for it")
        names = score["comparison_composite"]["dimensions"]
        conditions = bar_conditions(recipe, score, perf, comparisons(settings, names))
        ranking.append({"candidate_id": candidate["candidate_id"],
                        "comparison_composite": score["comparison_composite"]["value"],
                        "chunks_per_min": perf["chunks_per_min"],
                        "meets_bar": all(c["passed"] for c in conditions),
                        "failed": [c["condition"] for c in conditions if not c["passed"]]})
    passing = [r for r in ranking if r["meets_bar"]]
    chosen = None
    if passing:
        top = max(r["comparison_composite"] for r in passing)
        close = [r for r in passing if top - r["comparison_composite"] <= margin + 1e-12]
        chosen = max(close, key=lambda r: (r["chunks_per_min"] or 0, r["comparison_composite"],
                                           r["candidate_id"]))["candidate_id"]
    for candidate in candidates:
        candidate["selected"] = candidate["candidate_id"] == chosen
    save_candidates(dataset, candidates)
    return {"rule": recipe["selection"]["rule"], "ranking": ranking, "selected": chosen}


def _metric(name: str, value: float, description: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "value": value, "unit": extra.pop("unit", None),
            "description": description, "date": _today(), **extra}


def write_results(settings: Settings, run_id: str, perf_path: Path, version: str,
                  recipe_file: str | None = None) -> dict[str, Any]:
    recipe = load_recipe(settings, recipe_file)
    candidates = load_candidates(dataset_settings(settings, recipe))
    selected = [c for c in candidates if c.get("selected")]
    if candidates and (not selected or selected[0]["run_id"] != run_id):
        raise ValidationFailed(f"{run_id} is not the selected candidate; run `jtbd span select`")
    run = load_run_manifest(settings, run_id)
    score = _score_file(settings, run_id)
    perf = read_json(perf_path)
    sha = getattr(run.settings, "model_sha256", None)
    measured = str(perf.get("model_sha256"))
    if measured != sha:
        raise ValidationFailed(f"the perf file measured other model files ({measured[:12]}) "
                               f"than {run_id} ({str(sha)[:12]})")
    names = score["comparison_composite"]["dimensions"]
    table = comparisons(settings, names)
    benchmark = score["benchmark_version"]
    reference = table["reference"]
    chunks = int(table["chunks"] or len(score.get("dimensions", {})))
    q = {"reference": reference, "benchmark": benchmark}
    metrics = []
    for dim in names:
        entry = score["dimensions"][dim]
        metrics.append(_metric(
            f"agreement_{dim}", entry["score"],
            f"Agreement with the reference on {dim.replace('_', ' ')} ({entry['metric']}), "
            f"95% CI {entry['ci_low']}-{entry['ci_high']}",
            n_items=max(int(entry["n"]), 1), **q))
    value = score["comparison_composite"]["value"]
    dims_text = ", ".join(n.replace("_", " ") for n in names)
    metrics.append(_metric("comparison_composite", value,
                           f"Mean agreement over the dimensions this model outputs ({dims_text})",
                           n_items=chunks, **q))
    rates = score["check_pass_rates"]
    for name, check, text in (("quotes_verbatim_rate", "quote_verbatim",
                               "Share of quotes that are verbatim spans of the input"),
                              ("schema_valid_rate", "schema_valid",
                               "Share of outputs valid against the jtbd-span-v1 schema")):
        metrics.append(_metric(name, rates[check]["rate"], text,
                               n_items=max(int(rates[check]["n"]), 1), **q))
    metrics.append(_metric("consistency_rate", consistency_rate(rates),
                           "Share of passed consistency checks (dimensions, order, relevance)",
                           n_items=chunks, **q))
    metrics.append(_metric("contested_items", table["contested_count"],
                           "Benchmark items the reference models disagree on, reported "
                           "separately and scored neutrally", n_items=chunks, **q))
    best = table["best_baseline"]
    if best is None:
        raise ValidationFailed("no zero-shot baseline scores on this benchmark")
    metrics.append(_metric("comparison_composite_best_baseline", best["comparison_composite"],
                           f"Same composite for the best zero-shot small baseline "
                           f"({best['model_id']})", n_items=chunks, **q))
    if table["teacher"] and table["teacher"]["comparison_composite"] is not None:
        metrics.append(_metric("comparison_composite_teacher",
                               table["teacher"]["comparison_composite"],
                               f"Same composite for the teacher ({table['teacher']['model_id']})",
                               n_items=chunks, **q))
    metrics.append(_metric("comparison_composite_reference", table["reference_consensus_units"],
                           "Same composite for the two reference models against each other, "
                           "on consensus units", n_items=chunks, **q))
    metrics.append(_metric("comparison_composite_reference_85pct", table["reference_share_mark"],
                           "85% of the reference value: the pilot's bar for a usable small model",
                           n_items=chunks, **q))

    p = {"hardware": hardware_text(perf)}
    perf_metrics = [
        _metric("latency_9k_chars_s", perf["latency_9k_chars_s"],
                f"Median time to process a {perf['text_chars']}-character text, model loaded",
                unit="s", **p),
        _metric("load_time_s", perf["load_time_s"], "Time to load the model from local files",
                unit="s", **p),
        _metric("peak_ram_gb", round(perf["peak_rss_mb"] / 1024, 3),
                "Peak memory of the process while loading and processing", unit="GB", **p),
        _metric("chunks_per_min", perf["chunks_per_min"],
                f"Throughput over the {perf['n_chunks']} benchmark chunks", unit="chunks/min",
                n_items=max(int(perf["n_chunks"]), 1), **p),
    ]
    model = recipe["model"]
    out_dir = settings.base / "zoo" / "models" / model / "results" / version
    quality = {"kind": "quality", "model": model, "version": version, "synthetic": False,
               "source_run": run_id, "metrics": metrics}
    performance = {"kind": "performance", "model": model, "version": version,
                   "synthetic": False, "source_run": run_id, "metrics": perf_metrics}
    write_json(out_dir / "quality.json", quality)
    write_json(out_dir / "performance.json", performance)
    return {"quality": str(out_dir / "quality.json"),
            "performance": str(out_dir / "performance.json"),
            "metrics": len(metrics) + len(perf_metrics)}


def hardware_text(perf: dict[str, Any]) -> str:
    """One line naming the measurement hardware (results files and release record)."""
    hardware = perf["hardware"]
    # A container's memory limit, not the host's MemTotal, is the RAM the model had.
    mem_mb = hardware.get("mem_limit_mb") or hardware.get("mem_total_mb")
    return (f"{hardware.get('label') or 'unlabeled'} ({hardware.get('machine')}, "
            f"{hardware.get('vcpus')} vCPU"
            + (f", {mem_mb * 1048576 / 1e9:.1f} GB RAM" if mem_mb else "")
            + (f", {hardware['cpu_model']}" if hardware.get("cpu_model") else "")
            + ", CPU only)")


def _metric_value(metrics: list[dict[str, Any]], name: str) -> float | None:
    return next((m["value"] for m in metrics if m["name"] == name), None)


def release_check(settings: Settings, version: str, recipe_file: str | None = None
                  ) -> dict[str, Any]:
    """The release bar from the results files; exit 1 if any condition fails (FR-015)."""
    recipe = load_recipe(settings, recipe_file)
    bar_history = check_release_bar(settings, recipe)
    out_dir = settings.base / "zoo" / "models" / recipe["model"] / "results" / version
    quality = read_json(out_dir / "quality.json")["metrics"]
    performance = read_json(out_dir / "performance.json")["metrics"]
    bar = recipe["release_bar"]
    value = _metric_value(quality, "comparison_composite")
    best = _metric_value(quality, "comparison_composite_best_baseline")
    conditions = [{"condition": "comparison composite above every zero-shot baseline",
                   "value": value, "limit": best,
                   "passed": value is not None and best is not None and value > best}]
    for name, minimum in bar["deterministic_checks"].items():
        rate = _metric_value(quality, f"{name}_rate")
        conditions.append({"condition": f"{name} rate", "value": rate, "limit": minimum,
                           "passed": rate is not None and rate >= minimum})
    peak = _metric_value(performance, "peak_ram_gb")
    latency = _metric_value(performance, "latency_9k_chars_s")
    conditions.append({"condition": "peak RAM (GB)", "value": peak,
                       "limit": bar["max_peak_ram_gb"],
                       "passed": peak is not None and peak <= bar["max_peak_ram_gb"]})
    conditions.append({"condition": "latency for the 9,000-character text (s)", "value": latency,
                       "limit": bar["max_latency_s_9k"],
                       "passed": latency is not None and latency <= bar["max_latency_s_9k"]})
    result = {"version": version, "conditions": conditions,
              "release_bar_commit": bar_history["release_bar_commit"],
              "release_bar_changes": bar_history["release_bar_changes"],
              "passed": all(c["passed"] for c in conditions)}
    write_json(dataset_settings(settings, recipe).data_dir / "analysis"
               / f"release-check-{version}.json", result)
    if not result["passed"]:
        failed = [c["condition"] for c in conditions if not c["passed"]]
        raise ValidationFailed(f"the release bar is missed: {failed}; the model is not published "
                               "(FR-015)")
    return result


FIGURE = Path("topics/productdev/recipes/figures/scout-large-pareto")


def pareto(settings: Settings, recipe_file: str | None = None) -> dict[str, Any]:
    """Quality-vs-throughput front: every evaluated candidate next to the zero-shot baselines,
    on the same benchmark version and the same dimensions (constitution: gate before reporting)."""
    from mobility_model_zoo.productdev.jtbd.decision import load_perf
    from mobility_model_zoo.productdev.jtbd.report.pareto import draw, pareto_front

    recipe = load_recipe(settings, recipe_file)
    candidates = load_candidates(dataset_settings(settings, recipe))
    if not candidates:
        raise ValidationFailed("no evaluated candidates; run `jtbd span label` first")
    students, names, version = [], None, None
    for candidate in candidates:
        score = _score_file(settings, candidate["run_id"])
        perf = _perf_file(settings, candidate["model_sha256"])
        if perf is None:
            raise ValidationFailed(f"candidate {candidate['candidate_id']} has no perf file")
        names = score["comparison_composite"]["dimensions"]
        version = score["benchmark_version"]
        students.append((f"{MODEL_ID} ({candidate['candidate_id']})",
                         perf["chunks_per_min"],
                         score["comparison_composite"]["value"]))
    baseline_perf, _ = load_perf(settings)
    table = comparisons(settings, names)
    baselines = [(b["model_id"], baseline_perf[b["model_id"]]["chunks_per_min"],
                  b["comparison_composite"]) for b in table["baselines"]
                 if b["model_id"] in baseline_perf
                 and baseline_perf[b["model_id"]].get("chunks_per_min")
                 and b["comparison_composite"] is not None]
    out = settings.base / FIGURE
    shown = [(n.removeprefix("baseline-"), x, y) for n, x, y in baselines]  # shorter labels
    figure = draw(shown, out.with_suffix(".png"), version=version,
                  quality_bar=table["reference_share_mark"], throughput_bar=None,
                  students=students,
                  title=f"Quality vs throughput, span candidates and baselines ({version})",
                  ylabel=f"Comparison composite ({len(names)} dimensions)")
    points = {"benchmark_version": version, "dimensions": names,
              "reference_85pct": table["reference_share_mark"],
              "baselines": [{"model_id": n, "chunks_per_min": x, "comparison_composite": y}
                            for n, x, y in baselines],
              "candidates": [{"model_id": n, "chunks_per_min": x, "comparison_composite": y}
                             for n, x, y in students],
              "front": [n for n, _, _ in pareto_front(baselines + students)]}
    write_json(out.with_suffix(".json"), points)
    return {"figure": str(figure), "points": str(out.with_suffix(".json")),
            "front": points["front"]}


def write_record(settings: Settings, version: str, recipe_file: str | None = None
                 ) -> dict[str, Any]:
    """Fill the release record from the measured data (T045); `zoo stage` adds files/staging."""
    import json

    import yaml

    from mobility_model_zoo.productdev.jtbd.span.extractor import CONFIG_FILE

    recipe = load_recipe(settings, recipe_file)
    dataset = dataset_settings(settings, recipe)
    selected = [c for c in load_candidates(dataset) if c.get("selected")]
    if len(selected) != 1:
        raise ValidationFailed("no selected candidate; run `jtbd span select`")
    candidate = selected[0]
    span_config = json.loads((Path(candidate["model_dir"]) / CONFIG_FILE).read_text())
    provenance_path = dataset.data_dir / "analysis" / "provenance.json"
    if not provenance_path.exists():
        raise ValidationFailed("no provenance.json; run `jtbd span data-check`")
    provenance = read_json(provenance_path)
    decision = read_json(settings.analysis_dir / "decision.json")
    recommended = (decision.get("teacher_fitness") or {}).get("recommended")
    ensemble = settings.teacher_scoring().teacher_ensemble
    teacher_ids = sorted(ensemble.members) if recommended == ensemble.model_id else [recommended]
    from mobility_model_zoo.compliance.register import Register

    compliance = Register.load(settings.base)
    teachers = []
    for model_id in teacher_ids:
        basis = settings.model(model_id).license_basis
        if not basis:
            raise ValidationFailed(f"no license_basis recorded for teacher {model_id}")
        # From the provider route records (feature 006), not assumed: unclear or missing is False.
        permitted = compliance.output_training_permitted(model_id)
        teachers.append({"model_id": model_id, "license_basis": basis,
                         "training_on_outputs_permitted": permitted})
    perf = _perf_file(settings, candidate["model_sha256"])
    if perf is None:
        raise ValidationFailed("the selected candidate has no perf file")
    score = _score_file(settings, candidate["run_id"])
    model = recipe["model"]
    path = settings.base / "zoo" / "models" / model / "releases" / f"{version}.yaml"
    record = yaml.safe_load(path.read_text(encoding="utf-8"))
    record["date"] = _today()
    record["recipe"] = {"git_commit": span_config["recipe_commit"],
                        "config": span_config.get("recipe", "configs/productdev/jtbd/span-xlmr.yaml"),
                        "doc": "topics/productdev/recipes/scout-large.md"}
    record["provenance"] = {
        "sources": [{"origin": s["origin"], "license": s["license"],
                     "permitted_use": s["permitted_use"], "count": s["count"]}
                    for s in provenance["sources"]],
        "teachers": teachers, "spike_data": False}
    record["evaluation"] = {**record.get("evaluation", {}),
                            "benchmark": score["benchmark_version"],
                            "reference": reference_label(settings, _agreement(settings)),
                            "results": f"results/{version}/quality.json"}
    record["performance"] = {"hardware": hardware_text(perf),
                             "budget": {"ram_gb": recipe["release_bar"]["max_peak_ram_gb"],
                                        "gpu": False},
                             "results": f"results/{version}/performance.json"}
    path.write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    return {"record": str(path), "candidate": candidate["candidate_id"],
            "teachers": teacher_ids, "sources": len(record["provenance"]["sources"])}
