"""`condmon activity evaluate` on fake runs (feature 021, T014; FR-010, research R5, R21, R22)."""

import json
from pathlib import Path

import jsonschema
from condmon_helpers import write_runs
from typer.testing import CliRunner

import mobility_model_zoo.release as release_pkg
from mobility_model_zoo.condition_monitoring.activity import evaluate as ev
from mobility_model_zoo.condition_monitoring.activity.train import LABELS
from mobility_model_zoo.condition_monitoring.cli import app

runner = CliRunner()
SCHEMA = json.loads((Path(release_pkg.__file__).parent / "schemas/results.schema.json").read_text())
ORDER = [
    "int8_macro_f1",
    "int8_accuracy",
    "int8_f1_min_class",
    *[f"int8_f1_{c}" for c in LABELS],
    "int8_macro_f1_worst_subject",
    "int8_macro_f1_subject_range",
    "int8_macro_f1_seed_min",
    "int8_macro_f1_seed_mean",
    "int8_macro_f1_seed_max",
    "float_macro_f1",
    "float_accuracy",
    "tflite_interpreter_mismatches",
]


def _paths(root):
    manifest = root / "topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json"
    criteria = root / "configs/condition-monitoring/activity/pace-cnn-criteria.yaml"
    report = root / "topics/condition-monitoring/reports/pace-cnn/0.1.0"
    quality = root / "zoo/models/pace-cnn/results/0.1.0/quality.json"
    return manifest, criteria, report, quality


def _evaluate(monkeypatch):
    monkeypatch.setattr(ev, "fidelity_check", lambda parts: {"note": "test"})
    return runner.invoke(app, ["activity", "evaluate", "--version", "0.1.0"])


def test_evaluate_writes_report_quality_and_verdict(frozen, monkeypatch):
    manifest, criteria, report, quality = _paths(frozen)
    write_runs(manifest, criteria)
    res = _evaluate(monkeypatch)
    assert res.exit_code == 0, res.output
    assert "experimental" in res.output

    q = json.loads(quality.read_text())
    jsonschema.validate(q, SCHEMA)
    assert [m["name"] for m in q["metrics"]] == ORDER
    for m in q["metrics"]:
        assert m["reference"] == "labels of the uci-har dataset"
        assert m["benchmark"] == "uci-har-v1"
        assert m["hardware"] and m["date"]
    n = {m["name"]: m["n_items"] for m in q["metrics"]}
    assert n["int8_macro_f1"] == 27 and n["int8_macro_f1_worst_subject"] == 9
    assert n["int8_macro_f1_seed_mean"] == 5

    e = json.loads((report / "evaluation.json").read_text())
    subj = e["per_subject_macro_f1"]
    assert len(subj) == 9 and subj == sorted(subj)
    assert len(e["confusion_matrix"]["counts"]) == 6
    assert all(len(row) == 6 for row in e["confusion_matrix"]["counts"])
    assert e["confusion_matrix"]["rows"] == "dataset label"
    assert len(e["model_sha256"]) == 64
    assert [r["seed"] for r in e["runs"]] == [0, 1, 2, 3, 4]
    assert set(e["runs"][0]) >= {
        "seed",
        "manifest_sha256",
        "criteria_version",
        "criteria_commit",
        "npz_sha256",
        "trained_at",
    }

    v = json.loads((report / "verdict.json").read_text())
    assert v["status"] == "experimental"
    assert (report / "README.md").exists()


def test_evaluate_is_deterministic(frozen, monkeypatch):
    manifest, criteria, report, quality = _paths(frozen)
    write_runs(manifest, criteria)
    assert _evaluate(monkeypatch).exit_code == 0
    first = {p.name: p.read_bytes() for p in [*report.iterdir(), quality]}
    assert _evaluate(monkeypatch).exit_code == 0
    assert {p.name: p.read_bytes() for p in [*report.iterdir(), quality]} == first


def test_runs_with_another_manifest_are_refused(frozen, monkeypatch):
    manifest, criteria, _, quality = _paths(frozen)
    write_runs(manifest, criteria, manifest_sha256="0" * 64)
    res = _evaluate(monkeypatch)
    assert res.exit_code == 3
    assert not quality.exists()


def test_runs_with_another_criteria_version_are_refused(frozen, monkeypatch):
    manifest, criteria, _, _ = _paths(frozen)
    write_runs(manifest, criteria, criteria_version=2)
    assert _evaluate(monkeypatch).exit_code == 3


def test_missing_runs_are_refused(frozen, monkeypatch):
    assert _evaluate(monkeypatch).exit_code == 3


def test_interpreter_mismatch_blocks(frozen, monkeypatch):
    manifest, criteria, _, _ = _paths(frozen)
    write_runs(manifest, criteria, mismatches=2)
    assert _evaluate(monkeypatch).exit_code == 4
