"""`jtbd cluster perf` with stub models and a small scale set (feature 009, T056)."""

from __future__ import annotations

import json

from bench_helpers import make_env
from cluster_helpers import SETTINGS

from mobility_model_zoo.productdev.jtbd.cluster import bench
from mobility_model_zoo.productdev.jtbd.cluster.bundle import exact_copy_key, read_bundle_lines
from mobility_model_zoo.productdev.jtbd.cluster.metrics import analysis_dir
from mobility_model_zoo.productdev.jtbd.cluster.perf import item_count, perf, scale_lines
from mobility_model_zoo.productdev.jtbd.jsonio import read_jsonl


def test_scale_set_has_unique_sources_and_no_exact_copies(tmp_path):
    env = make_env(tmp_path / "env")
    env.build()
    lines = list(read_jsonl(bench.bench_dir(env.settings()) / "pool-bundle.jsonl"))
    scaled = scale_lines(lines, 500)
    assert item_count(scaled) >= 500
    sources = read_bundle_lines(scaled, "scale")  # valid bundle, unique source ids
    keys = [exact_copy_key(it["kind"], it["quote"]) for s in sources for it in s.output["items"]]
    assert len(set(keys)) == len(keys)


def test_perf_runs_the_stage_in_a_child_and_records_origin(tmp_path):
    env = make_env(tmp_path / "env")
    env.build()
    s = env.settings()
    real = perf(s, SETTINGS)
    scaled = perf(s, SETTINGS, scale=300, hardware="test")
    assert real["origin"] == "real" and scaled["origin"] == "scale-set"
    assert scaled["items"] >= 300 and real["wall_s"] > 0 and real["peak_rss_mb"] > 0
    stored = json.loads((analysis_dir(s) / "perf-cluster-test-scale300.json").read_text())
    assert stored["hardware"]["label"] == "test" and "offline" in stored["conditions"]
