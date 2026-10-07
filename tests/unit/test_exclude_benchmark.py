"""Training snapshots never share a source with the benchmark or spike data (T019, research R2)."""

import json

import pytest
import yaml
from helpers import pilot
from span_helpers import make_snapshot, prose, snapshot_map, span_train_env

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.corpus import separation
from mobility_model_zoo.productdev.jtbd.sources import registry

BENCH_PAPER = "snap-53d0c1790348"  # used by main chunk ch-005 of the mini corpus


@pytest.fixture
def env(tmp_path):
    bench, train = span_train_env(tmp_path)
    return bench, train, load_settings(train)


def autochunk(train, map_path, expect=0):
    return pilot(train, "corpus", "autochunk", "--map", str(map_path), "--train", "3",
                 "--eval", "0", "--seed", "1", expect=expect)


def test_clean_snapshot_passes_and_is_chunked(env, tmp_path):
    _, train, settings = env
    snap = make_snapshot(settings, "https://example.net/clean-report", prose("clean"))
    result = autochunk(train, snapshot_map(tmp_path / "map.yaml", [snap]))
    assert result["train"] >= 1


def test_benchmark_snapshot_is_refused(env, tmp_path):
    _, train, settings = env
    bench = separation.benchmark_sources(settings)
    assert separation.violations(settings, BENCH_PAPER, bench, set()) == [
        "snapshot_id", "origin_url", "content_hash"]
    autochunk(train, snapshot_map(tmp_path / "map.yaml", [BENCH_PAPER]), expect=1)


def test_same_url_in_another_form_is_refused(env):
    _, _, settings = env
    snap = make_snapshot(settings, "http://www.example.org/protokoll-1/?utm_source=feed",
                         prose("url"))
    bench = separation.benchmark_sources(settings)
    assert separation.violations(settings, snap, bench, set()) == ["origin_url"]


def test_same_content_under_another_id_is_refused(env):
    _, _, settings = env
    snap = make_snapshot(settings, "https://example.net/copy", prose("copy"))
    meta = yaml.safe_load((settings.snapshots_dir / snap / "source.yaml").read_text())
    bench = separation.benchmark_sources(settings)
    bench.hashes.add(meta["raw_sha256"])  # the shared store keeps one ID per content hash
    assert separation.violations(settings, snap, bench, set()) == ["content_hash"]


def test_superseding_snapshot_is_refused(env):
    _, _, settings = env
    snap = make_snapshot(settings, "https://example.net/new-home-of-the-protocol", prose("moved"))
    registry.register(settings, snap, "https://example.net/new-home-of-the-protocol",
                      "2026-10-02T00:00:00+00:00", "snap-b8ce3db5e85b")
    bench = separation.benchmark_sources(settings)
    assert separation.violations(settings, snap, bench, set()) == ["supersession"]


def test_spike_snapshot_is_refused(env, tmp_path):
    _, train, settings = env
    snap = make_snapshot(settings, "https://example.net/spike-source", prose("spike"))
    spike = settings.base / "data/spike/chunks"
    spike.mkdir(parents=True)
    (spike / "ch-001.json").write_text(json.dumps({"snapshot_id": snap}))
    assert separation.spike_snapshot_ids(settings) == {snap}
    autochunk(train, snapshot_map(tmp_path / "map.yaml", [snap]), expect=1)


@pytest.mark.parametrize("url,expected", [
    ("https://www.Example.org/a/b/?utm_medium=x&fbclid=1", "example.org/a/b"),
    ("http://example.org/a/b", "example.org/a/b"),
    ("https://example.org/a?b=2&a=1", "example.org/a?a=1&b=2"),
])
def test_normalize_url(url, expected):
    assert separation.normalize_url(url) == expected
