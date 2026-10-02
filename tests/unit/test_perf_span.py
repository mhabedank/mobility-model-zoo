"""`jtbd perf --backend span`: child-process measurement tied to the quality run (T031)."""

import sys

import pytest
from helpers import pilot
from span_helpers import build_tiny_model, git_commit_all, teacher_env, write_recipe

from mobility_model_zoo.productdev.jtbd.perf import process_rss_mb


@pytest.fixture
def env(tmp_path):
    bench, _, _ = teacher_env(tmp_path)
    work = bench.parent
    recipe = write_recipe(work / "recipe.yaml", ["actor_type"], dataset_config="span.yaml",
                          benchmark_config="pilot.yaml")
    git_commit_all(work)
    model = build_tiny_model(work / "model", ("actor_type",))
    (work / "text.txt").write_text("Der letzte Bus fährt um 18 Uhr. " * 280)
    return bench, recipe, model, work


def test_perf_measures_the_evaluated_files(env):
    bench, recipe, model, work = env
    pilot(bench, "span", "label", "--model-dir", str(model), "--candidate-change", "c1",
          "--recipe", str(recipe))
    out = pilot(bench, "perf", "--backend", "span", "--model-dir", str(model), "--hardware",
                "test machine", "--text", str(work / "text.txt"))
    assert out["text_chars"] == len((work / "text.txt").read_text())
    assert len(out["latencies_s"]) == 5 and out["latency_9k_chars_s"] > 0
    assert out["load_time_s"] > 0 and out["n_chunks"] == 5 and out["chunks_per_min"] > 0
    assert out["peak_rss_mb"] >= out["ru_maxrss_mb"] > 0
    assert out["hardware"]["label"] == "test machine"
    if sys.platform.startswith("linux"):
        assert out["peak_rss_sampled_mb"] is not None


def test_perf_refuses_files_without_a_quality_run(env):
    bench, _, model, work = env
    pilot(bench, "perf", "--backend", "span", "--model-dir", str(model), "--text",
          str(work / "text.txt"), expect=1)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="/proc is Linux only")
def test_process_rss_reads_proc():
    import os

    assert process_rss_mb(os.getpid()) > 0
