"""`zoo tracking import`: past results as runs, once, values unchanged (feature 017 T050, T052)."""

import json
from types import SimpleNamespace

from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture
from typer.testing import CliRunner

from mobility_model_zoo.release.cli import app
from mobility_model_zoo.tracking.importer import import_results

NO_INVENTORY = SimpleNamespace(rows=[])
BENCH = SimpleNamespace(
    name="pilot@pilot-v2",
    id="pilot",
    version="pilot-v2",
    kind="benchmark",
    sha256="ab" * 32,
    source="topics/alpha/benchmarks/pilot-v2/manifest.json",
    counts={"items": 3},
    distribution={},
)


def _json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _model(root, name, task, version, quality, date="2026-10-07"):
    base = root / "zoo/models" / name
    base.mkdir(parents=True, exist_ok=True)
    (base / "model.yaml").write_text(f"name: {name}\ntask: {task}\ntopic: productdev\n")
    (base / "releases").mkdir(exist_ok=True)
    (base / "releases" / f"{version}.yaml").write_text(
        f"date: {date}\nrecipe:\n  git_commit: {'c' * 40}\nevaluation:\n  benchmark: pilot-v2\n"
        "usage:\n  class: commercial\n  licence: Apache-2.0\n"
    )
    metrics = [{"name": k, "value": v} for k, v in quality.items()]
    _json(base / "results" / version / "quality.json", {"kind": "quality", "metrics": metrics})
    _json(
        base / "results" / version / "performance.json",
        {"kind": "performance", "metrics": [{"name": "load_time_s", "value": 12.2319}]},
    )


def fixture_repo(root):
    _model(root, "scout", "jtbd", "0.1.0", {"agreement_kind": 0.831548, "missing": None})
    _model(root, "sandbox-pipeline-tiny", "jtbd", "0.1.0", {"agreement_kind": 0.1})
    _json(
        root / "topics/productdev/benchmarks/cluster-v1/decision.json",
        {
            "benchmark_version": "cluster-v1",
            "split": "holdout",
            "decided_at": "2026-10-11T10:59:17+00:00",
            "levels": {
                "duplicate": {"value": 0.6416, "threshold": 0.6, "decision": "go"},
                "cluster_level_2": {"value": None, "threshold": 0.6, "decision": "not_measured"},
            },
            "final": True,
        },
    )
    return root


def test_import_once_with_exact_values(store, tmp_path):  # noqa: F811
    root = fixture_repo(tmp_path / "repo")
    first = {a.key: a.action for a in import_results(root, inventory=SimpleNamespace(rows=[BENCH]))}
    assert first == {"scout@0.1.0": "created", "cluster-v1/decision": "created"}  # no sandbox model
    again = import_results(root, inventory=NO_INVENTORY)
    assert {a.action for a in again} == {"exists"}

    [run] = runs_of(store, "productdev/jtbd-span")
    tags, metrics = run.data.tags, run.data.metrics
    assert tags["mmz.imported"] == "true"
    assert tags["mmz.import_key"] == "scout@0.1.0"
    assert tags["mmz.model_version"] == "0.1.0"
    assert tags["mmz.benchmark"] == "pilot-v2"
    assert tags["mmz.git_commit"] == "c" * 40
    assert metrics == {"agreement_kind": 0.831548, "load_time_s": 12.2319}  # `missing` stays missing
    assert run.data.params["usage.class"] == "commercial"
    assert run.info.start_time == run.info.end_time == 1791331200000  # 2026-10-07, not today
    [inp] = run.inputs.dataset_inputs
    assert inp.dataset.name == "pilot@pilot-v2" and inp.dataset.digest == "ab" * 8
    artifacts = sorted(a.path for a in store.list_artifacts(run.info.run_id))
    assert artifacts == ["performance.json", "quality.json"]

    [decision] = runs_of(store, "productdev/jtbd-cluster")
    assert decision.data.metrics == {
        "duplicate.value": 0.6416,
        "duplicate.threshold": 0.6,
        "cluster_level_2.threshold": 0.6,
    }
    assert decision.data.params["cluster_level_2.decision"] == "not_measured"


def test_unresolved_benchmark_and_model_filter(store, tmp_path):  # noqa: F811
    root = fixture_repo(tmp_path / "repo")
    actions = import_results(root, models=["scout"], inventory=NO_INVENTORY)
    assert [a.key for a in actions] == ["scout@0.1.0"]
    [run] = runs_of(store, "productdev/jtbd-span")
    assert run.data.tags["mmz.input_unresolved"] == "pilot-v2"
    assert run.inputs.dataset_inputs == []


def test_dry_run_creates_nothing(store, tmp_path):  # noqa: F811
    root = fixture_repo(tmp_path / "repo")
    actions = import_results(root, dry_run=True, inventory=NO_INVENTORY)
    assert {a.action for a in actions} == {"create"}
    assert runs_of(store, "productdev/jtbd-span") == []


def test_repository_results_pass_the_guard(store):  # noqa: F811
    from mobility_model_zoo.edge.paths import repo_root

    r = CliRunner().invoke(app, ["tracking", "import"])
    assert r.exit_code == 0, r.output
    assert "sandbox-pipeline-tiny" not in r.stdout
    assert "created  scout-large@0.1.3" in r.stdout
    quality = json.loads((repo_root() / "zoo/models/scout-large/results/0.1.3/quality.json").read_text())
    [run] = runs_of(store, "productdev/jtbd-span", "tags.`mmz.import_key` = 'scout-large@0.1.3'")
    for metric in quality["metrics"]:
        assert run.data.metrics[metric["name"]] == metric["value"]
    r = CliRunner().invoke(app, ["tracking", "import"])
    assert r.exit_code == 0 and "created" not in r.stdout
    assert CliRunner().invoke(app, ["tracking", "audit"]).exit_code == 0
