"""`jtbd span label`: student runs on the main split, candidate record and cap (T030)."""

import pytest
from helpers import pilot
from span_helpers import build_tiny_model, git_commit_all, teacher_env, write_recipe

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json


@pytest.fixture
def env(tmp_path):
    bench, train, _ = teacher_env(tmp_path)
    work = bench.parent
    recipe = write_recipe(work / "recipe.yaml", ["actor_type"], dataset_config="span.yaml",
                          benchmark_config="pilot.yaml", selection={"benchmark_candidate_cap": 2})
    pilot(bench, "agreement")
    git_commit_all(work)
    return bench, train, recipe, work


def label(bench, recipe, model, change="c: test", split="main", expect=0):
    return pilot(bench, "span", "label", "--model-dir", str(model), "--split", split,
                 "--candidate-change", change, "--recipe", str(recipe), expect=expect)


def test_label_check_score_and_candidates(env):
    bench, train, recipe, work = env
    model = build_tiny_model(work / "m1", ("actor_type",), seed=1)
    out = label(bench, recipe, model, "c1: recipe defaults")
    assert out["candidate_id"] == "c1" and out["dimensions"] == ["actor_type"]
    rates = pilot(bench, "check", "--run", out["run_id"])["pass_rates"]
    assert rates["schema_valid"]["rate"] == 1.0 and rates["quote_verbatim"]["rate"] == 1.0
    assert all(v["rate"] == 1.0 for k, v in rates.items() if k.startswith("consistency."))
    score = pilot(bench, "score", "--run", out["run_id"])
    assert score["role"] == "student"
    assert score["dimensions"]["evidence_type"]["status"] == "not_produced"
    assert score["comparison_composite"]["dimensions"] == [
        "relevance", "item_matching", "kind", "actor_type"]
    candidates = read_json(load_settings(train).data_dir / "analysis/candidates.json")
    assert [c["candidate_id"] for c in candidates["candidates"]] == ["c1"]
    assert candidates["candidates"][0]["change"] == "c1: recipe defaults"
    manifest = read_json(load_settings(bench).runs_dir / out["run_id"] / "manifest.json")
    assert len(manifest["settings"]["git_commit"]) == 40


def test_cap_same_model_and_holdout_are_refused(env):
    bench, _, recipe, work = env
    m1 = build_tiny_model(work / "m1", ("actor_type",), seed=1)
    label(bench, recipe, m1, split="holdout", expect=1)
    label(bench, recipe, m1)
    label(bench, recipe, m1, expect=1)  # same model files again
    label(bench, recipe, build_tiny_model(work / "m2", ("actor_type",), seed=2))
    label(bench, recipe, build_tiny_model(work / "m3", ("actor_type",), seed=3), expect=1)  # cap 2


def test_dirty_tree_is_refused(env):
    bench, _, recipe, work = env
    (work / "src").mkdir()
    (work / "src" / "change.py").write_text("x = 1\n")
    label(bench, recipe, build_tiny_model(work / "m1", ("actor_type",)), expect=1)
