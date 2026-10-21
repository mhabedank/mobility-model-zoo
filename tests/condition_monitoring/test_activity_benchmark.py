"""Benchmark uci-har-v1: freeze, refuse changes, no subject numbers (feature 021, T008)."""

import hashlib
import json

import numpy as np
from typer.testing import CliRunner

from mobility_model_zoo.condition_monitoring import benchmark as bm
from mobility_model_zoo.condition_monitoring.activity import train as pace
from mobility_model_zoo.condition_monitoring.cli import app

runner = CliRunner()


def _repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(bm, "repo", lambda: root)
    return root


def _freeze():
    return runner.invoke(app, ["activity", "freeze"])


def test_first_freeze_writes_manifest(har_tree, tmp_path, monkeypatch):
    root = _repo(tmp_path, monkeypatch)
    res = _freeze()
    assert res.exit_code == 0, res.output
    path = root / "topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json"
    m = json.loads(path.read_text())
    assert m["benchmark"] == "uci-har-v1"
    assert [m["splits"][s]["subjects"] for s in ("train", "validation", "test")] == [18, 3, 9]
    per = har_tree.per_subject
    assert m["splits"]["test"]["windows"] == 9 * per
    assert m["splits"]["train"]["windows"] + m["splits"]["validation"]["windows"] == 21 * per
    assert m["protocol"]["validation_seed"] == 2026
    assert m["protocol"]["validation"].startswith("3 of the 21 training subjects")
    assert m["datasets"] == [
        {
            "id": "uci-har",
            "licence": "CC-BY-4.0",
            "retrieved_at": "2026-01-01T00:00:00Z",
            "archive_sha256": "ab" * 32,
        }
    ]
    assert len(m["normalisation"]["mean"]) == 9 and len(m["normalisation"]["std"]) == 9
    assert "frozen_at" in m


def test_second_freeze_changes_nothing(har_tree, tmp_path, monkeypatch):
    root = _repo(tmp_path, monkeypatch)
    assert _freeze().exit_code == 0
    path = root / "topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json"
    before = path.read_bytes()
    res = _freeze()
    assert res.exit_code == 0, res.output
    assert path.read_bytes() == before


def test_changed_validation_seed_is_refused(har_tree, tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    assert _freeze().exit_code == 0
    monkeypatch.setitem(pace.BENCHMARK, "validation_seed", 7)
    res = _freeze()
    assert res.exit_code == 3
    assert "validation_seed" in res.output


def test_missing_dataset_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_DATA", str(tmp_path / "empty"))
    root = _repo(tmp_path, monkeypatch)
    res = _freeze()
    assert res.exit_code == 4
    assert not (root / "topics").exists()


def test_manifest_holds_no_subject_numbers(har_tree, tmp_path, monkeypatch):
    root = _repo(tmp_path, monkeypatch)
    assert _freeze().exit_code == 0
    m = json.loads(
        (root / "topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json").read_text()
    )

    def lists(node):
        if isinstance(node, dict):
            for v in node.values():
                yield from lists(v)
        elif isinstance(node, list):
            yield node
            for v in node:
                yield from lists(v)

    for values in lists(m):  # only the 9 normalisation floats and string lists may appear
        assert not all(isinstance(v, int) for v in values) or not values
    for split in m["splits"].values():
        assert set(split) == {"subjects", "windows", "subjects_sha256", "data_sha256"}
        assert isinstance(split["subjects"], int)


def test_hashes_follow_the_contract(har_tree):
    subjects = [5, 3, 3, 12]
    assert bm.subjects_sha256(subjects) == hashlib.sha256(b"3,5,12").hexdigest()
    x = np.ones((2, 128, 9), np.float64)
    y = np.array([0, 1])
    want = hashlib.sha256(
        np.ones((2, 128, 9), np.float32).tobytes() + np.array([0, 1], np.int64).tobytes()
    ).hexdigest()
    assert bm.data_sha256(x, y) == want
