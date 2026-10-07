"""Quality-vs-throughput front with span candidates next to the baselines (T043)."""

import hashlib

from helpers import pilot, run_ids
from span_helpers import git_commit_all, teacher_env, write_recipe

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.report.pareto import pareto_front

NAMES = ["relevance", "item_matching", "kind", "actor_type"]


def candidate(bench, train, cid, composite, per_min):
    settings, dataset = load_settings(bench), load_settings(train)
    sha = hashlib.sha256(cid.encode()).hexdigest()
    run_id = f"run-student-fake-{cid}"
    write_json(settings.analysis_dir / "scores" / f"{run_id}.json", {
        "run_id": run_id, "role": "student", "model_id": "scout-large",
        "benchmark_version": "mini-v1", "composite": composite,
        "dimensions": {d: {"score": composite} for d in NAMES},
        "comparison_composite": {"dimensions": NAMES, "value": composite}})
    write_json(settings.analysis_dir / "perf" / f"scout-large-{sha[:12]}.json",
               {"model_id": "scout-large", "model_sha256": sha,
                "chunks_per_min": per_min})
    path = dataset.data_dir / "analysis" / "candidates.json"
    rows = read_json(path)["candidates"] if path.exists() else []
    write_json(path, {"candidates": [*rows, {"candidate_id": cid, "model_sha256": sha,
                                             "run_id": run_id, "selected": False}]})


def test_candidates_are_plotted_with_the_baselines(tmp_path):
    bench, train, _ = teacher_env(tmp_path)
    work = bench.parent
    recipe = write_recipe(work / "recipe.yaml", ["actor_type"], dataset_config="span.yaml",
                          benchmark_config="pilot.yaml")
    pilot(bench, "agreement")
    pilot(bench, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    pilot(bench, "score", "--run", run_ids(bench)["mock-small"])
    settings = load_settings(bench)
    write_json(settings.analysis_dir / "perf" / "mock-small.json",
               {"model_id": "mock-small", "chunks_per_min": 2.0})
    candidate(bench, train, "c1", 0.9, 400.0)
    candidate(bench, train, "c2", 0.5, 300.0)
    git_commit_all(work)
    out = pilot(bench, "span", "pareto", "--recipe", str(recipe))
    points = read_json(work / "docs/recipes/figures/scout-large-pareto.json")
    assert (work / "docs/recipes/figures/scout-large-pareto.png").stat().st_size
    assert points["dimensions"] == NAMES and points["benchmark_version"] == "mini-v1"
    assert [p["model_id"] for p in points["baselines"]] == ["mock-small"]
    assert [p["model_id"] for p in points["candidates"]] == ["c1 (span)", "c2 (span)"]
    assert "c1 (span)" in out["front"] and "c2 (span)" not in out["front"]


def test_pareto_front_keeps_undominated_points():
    points = [("a", 1, 0.9), ("b", 10, 0.5), ("c", 5, 0.4), ("d", 10, 0.6)]
    assert [p[0] for p in pareto_front(points)] == ["a", "d"]
