"""Results files, selection rule and release bar of the span model (T032)."""

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest
from helpers import pilot, run_ids
from span_helpers import build_tiny_model, git_commit_all, teacher_env, write_recipe

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json

ROOT = Path(__file__).resolve().parents[3]
RESULTS_SCHEMA = json.loads(
    (ROOT / "specs/003-model-zoo-hf-release/contracts/results.schema.json").read_text())
NAMES = ["relevance", "item_matching", "kind", "actor_type"]


@pytest.fixture
def env(tmp_path):
    bench, train, _ = teacher_env(tmp_path)
    work = bench.parent
    recipe = write_recipe(work / "recipe.yaml", ["actor_type"], dataset_config="span.yaml",
                          benchmark_config="pilot.yaml")
    pilot(bench, "agreement")
    for model in ("mock-small", "mock-teacher-y"):
        role = "baseline" if model == "mock-small" else "teacher_candidate"
        pilot(bench, "label", "--role", role, "--backend", "mock", "--model", model)
        pilot(bench, "score", "--run", run_ids(bench)[model])
    git_commit_all(work)
    return bench, train, recipe, work


def fake_candidate(bench, train, cid, composite, per_min, rates=1.0, peak_mb=900.0,
                   latency=2.0):
    """A scored and measured candidate without running a model (selection tests)."""
    settings, dataset = load_settings(bench), load_settings(train)
    sha = hashlib.sha256(cid.encode()).hexdigest()
    run_id = f"run-student-fake-{cid}"
    dims = {d: {"score": composite, "metric": "kappa", "n": 10, "ci_low": 0, "ci_high": 1}
            for d in NAMES}
    write_json(settings.analysis_dir / "scores" / f"{run_id}.json", {
        "run_id": run_id, "role": "student", "model_id": "scout-large",
        "benchmark_version": "mini-v1", "dimensions": dims, "composite": composite,
        "comparison_composite": {"dimensions": NAMES, "value": composite},
        "check_pass_rates": {"quote_verbatim": {"n": 5, "passed": 5, "rate": rates},
                             "schema_valid": {"n": 5, "passed": 5, "rate": rates},
                             "consistency.span_order": {"n": 5, "passed": 5, "rate": 1.0}}})
    write_json(settings.analysis_dir / "perf" / f"scout-large-{sha[:12]}.json", {
        "model_sha256": sha, "chunks_per_min": per_min, "peak_rss_mb": peak_mb,
        "latency_9k_chars_s": latency})
    path = dataset.data_dir / "analysis" / "candidates.json"
    candidates = read_json(path)["candidates"] if path.exists() else []
    candidates.append({"candidate_id": cid, "model_sha256": sha, "run_id": run_id,
                       "selected": False})
    write_json(path, {"candidates": candidates})


def baseline_value(bench):
    from mobility_model_zoo.productdev.jtbd.span.results import comparisons

    return comparisons(load_settings(bench), NAMES)["best_baseline"]["comparison_composite"]


def test_select_prefers_the_faster_within_the_margin_and_the_better_beyond(env):
    bench, train, recipe, _ = env
    best = baseline_value(bench)
    fake_candidate(bench, train, "c1", best + 0.05, 10.0)
    fake_candidate(bench, train, "c2", best + 0.04, 30.0)  # 0.01 below c1, three times faster
    out = pilot(bench, "span", "select", "--recipe", str(recipe))
    assert out["selected"] == "c2"
    fake_candidate(bench, train, "c3", best + 0.10, 5.0)  # 0.05 above: quality wins
    assert pilot(bench, "span", "select", "--recipe", str(recipe))["selected"] == "c3"
    candidates = read_json(load_settings(train).data_dir / "analysis/candidates.json")
    assert [c["selected"] for c in candidates["candidates"]] == [False, False, True]


def test_select_chooses_none_when_no_candidate_meets_the_bar(env):
    bench, train, recipe, _ = env
    best = baseline_value(bench)
    fake_candidate(bench, train, "c1", best, 50.0)  # a tie with the best baseline is not above
    fake_candidate(bench, train, "c2", best + 0.1, 50.0, rates=0.99)
    fake_candidate(bench, train, "c3", best + 0.1, 50.0, latency=11.0)
    out = pilot(bench, "span", "select", "--recipe", str(recipe))
    assert out["selected"] is None
    assert all(not r["meets_bar"] for r in out["ranking"])


def test_results_files_validate_and_release_check(env):
    bench, train, recipe, work = env
    model = build_tiny_model(work / "model", ("actor_type",))
    run = pilot(bench, "span", "label", "--model-dir", str(model), "--candidate-change", "c1",
                "--recipe", str(recipe))["run_id"]
    pilot(bench, "check", "--run", run)
    pilot(bench, "score", "--run", run)
    (work / "text.txt").write_text("Der letzte Bus fährt um 18 Uhr. " * 280)
    perf = pilot(bench, "perf", "--backend", "span", "--model-dir", str(model), "--hardware",
                 "test vm", "--text", str(work / "text.txt"))
    pilot(bench, "span", "select", "--recipe", str(recipe))
    perf_file = next((load_settings(bench).analysis_dir / "perf").glob("*.json"))
    dataset = load_settings(train)
    candidates = read_json(dataset.data_dir / "analysis/candidates.json")
    if not candidates["candidates"][0]["selected"]:
        pilot(bench, "span", "results", "--run", run, "--perf", str(perf_file), "--version",
              "0.1.0", "--recipe", str(recipe), expect=1)  # only the selected candidate
        candidates["candidates"][0]["selected"] = True
        write_json(dataset.data_dir / "analysis/candidates.json", candidates)
    pilot(bench, "span", "results", "--run", run, "--perf", str(perf_file), "--version", "0.1.0",
          "--recipe", str(recipe))
    out_dir = work / "zoo/models/scout-large/results/0.1.0"
    quality = read_json(out_dir / "quality.json")
    performance = read_json(out_dir / "performance.json")
    for doc in (quality, performance):
        jsonschema.validate(doc, RESULTS_SCHEMA)
        assert doc["source_run"] == run and doc["synthetic"] is False
    names = {m["name"] for m in quality["metrics"]}
    assert {"agreement_actor_type", "comparison_composite", "consistency_rate",
            "comparison_composite_best_baseline", "comparison_composite_teacher",
            "comparison_composite_reference_85pct", "contested_items"} <= names
    assert "agreement_evidence_type" not in names
    assert {m["name"] for m in performance["metrics"]} == {
        "latency_9k_chars_s", "load_time_s", "peak_ram_gb", "chunks_per_min"}
    assert perf["latency_9k_chars_s"] == next(
        m["value"] for m in performance["metrics"] if m["name"] == "latency_9k_chars_s")
    composite = next(m["value"] for m in quality["metrics"] if m["name"] == "comparison_composite")
    best = next(m["value"] for m in quality["metrics"]
                if m["name"] == "comparison_composite_best_baseline")
    git_commit_all(work)
    out = pilot(bench, "span", "release-check", "--version", "0.1.0", "--recipe", str(recipe),
                expect=0 if composite > best else 1)
    if composite > best:
        assert out["passed"] is True


def test_release_check_fails_on_a_tie_with_the_best_baseline(env):
    bench, _, recipe, work = env
    out_dir = work / "zoo/models/scout-large/results/0.1.0"
    q = {"reference": "r", "benchmark": "b", "n_items": 5, "date": "2026-10-02",
         "description": "d"}
    write_json(out_dir / "quality.json", {"kind": "quality", "metrics": [
        {"name": "comparison_composite", "value": 0.7, **q},
        {"name": "comparison_composite_best_baseline", "value": 0.7, **q},
        *({"name": f"{n}_rate", "value": 1.0, **q}
          for n in ("quotes_verbatim", "schema_valid", "consistency"))]})
    p = {"hardware": "h", "date": "2026-10-02", "description": "d"}
    write_json(out_dir / "performance.json", {"kind": "performance", "metrics": [
        {"name": "peak_ram_gb", "value": 2.3, **p},
        {"name": "latency_9k_chars_s", "value": 4.0, **p}]})
    pilot(bench, "span", "release-check", "--version", "0.1.0", "--recipe", str(recipe), expect=1)
    quality = read_json(out_dir / "quality.json")
    quality["metrics"][0]["value"] = 0.71
    write_json(out_dir / "quality.json", quality)
    assert pilot(bench, "span", "release-check", "--version", "0.1.0", "--recipe",
                 str(recipe))["passed"] is True
