"""Runs against a real store: tags, params, steps, inputs, status and the circuit breaker
(feature 017 T032, T033, T037; FR-018, FR-020)."""

import json

import pytest
from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture

from mobility_model_zoo import tracking
from mobility_model_zoo.tracking import client as tc

CONFIG = "configs/security/can-ids/picket-forest.yaml"


def _run(out, **kw):
    return tracking.run(
        "security/can-ids",
        "unit-run",
        "can-ids",
        config_path=CONFIG,
        out_dir=out,
        inputs=[tracking.data_ref("can-ids", "can-ids-v3", "evaluation")],
        tags={"mmz.kind": "evaluate", "mmz.benchmark": "can-ids-v3"},
        **kw,
    )


def test_a_run_records_what_the_contract_names(store, tmp_path):  # noqa: F811
    with _run(tmp_path / "out") as r:
        for step in range(3):
            r.log_step(step, {"loss": 1.0 / (step + 1), "label": "ignored"})
        r.log_final({"recall": 0.9})
    [run] = runs_of(store, "security/can-ids")
    tags = run.data.tags
    assert run.info.status == "FINISHED"
    assert tags["mmz.task"] == "can-ids" and tags["mmz.topic"] == "security"
    assert len(tags["mmz.git_commit"]) == 40 and tags["mmz.git_clean"] in ("true", "false")
    assert tags["mmz.benchmark"] == "can-ids-v3"
    assert run.data.params["config"] == CONFIG
    assert run.data.metrics["recall"] == 0.9
    history = store.get_metric_history(run.info.run_id, "loss")
    assert [m.step for m in history] == [0, 1, 2]
    [ds] = run.inputs.dataset_inputs
    assert ds.dataset.name == "can-ids@can-ids-v3" and len(ds.dataset.digest) == 16
    assert json.loads(ds.dataset.profile)["counts"]["captures"] == 281
    side = json.loads((tmp_path / "out" / "tracking.json").read_text())
    assert side["complete"] is True and side["run_id"] == run.info.run_id
    found = runs_of(store, "security/can-ids", "datasets.name = 'can-ids@can-ids-v3'")
    assert [r.info.run_id for r in found] == [run.info.run_id]


def test_failure_and_interrupt_set_the_status(store, tmp_path):  # noqa: F811
    with pytest.raises(RuntimeError):
        with _run(tmp_path / "a"):
            raise RuntimeError("training broke")
    with pytest.raises(KeyboardInterrupt):
        with _run(tmp_path / "b"):
            raise KeyboardInterrupt
    statuses = sorted(r.info.status for r in runs_of(store, "security/can-ids"))
    assert statuses == ["FAILED", "KILLED"]


def test_server_lost_mid_run_degrades_without_harming_the_run(store, tmp_path, monkeypatch):  # noqa: F811
    with _run(tmp_path / "out") as r:

        def broken(*args, **kwargs):
            raise ConnectionError("server gone")

        monkeypatch.setattr(r.client, "log_batch", broken)
        monkeypatch.setattr(r.client, "set_terminated", broken)
        for step in range(5):
            r.log_step(step, {"loss": 0.5})  # must not raise
        result = "trained"
    assert result == "trained"
    side = json.loads((tmp_path / "out" / "tracking.json").read_text())
    assert side["complete"] is False and side["dropped"] >= 5
    assert any("server unreachable" in w for w in side["warnings"])


def test_unreachable_server_at_start(tmp_path, monkeypatch):
    pytest.importorskip("mlflow")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:9")  # discard port: refused
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    with tracking.run("spikes", "x", "spike", out_dir=tmp_path) as r:
        r.log_step(0, {"loss": 1.0})
    side = json.loads((tmp_path / "tracking.json").read_text())
    assert side == {**side, "run_id": None, "complete": False}


def test_guard_drops_with_warning_or_raises_when_strict(store, tmp_path, monkeypatch):  # noqa: F811
    with tracking.run("spikes", "g", "spike", out_dir=tmp_path) as r:
        r.log_params({"note": "a whole sentence of free text goes here"})
        r.log_artifact(tmp_path / "weights.safetensors")
    side = json.loads((tmp_path / "tracking.json").read_text())
    assert side["complete"] is True and side["dropped"] == 2
    monkeypatch.setattr(tc, "STRICT", True)
    from mobility_model_zoo.tracking.guard import GuardRefused

    with pytest.raises(GuardRefused):
        with tracking.run("spikes", "g2", "spike") as r:
            r.set_tag("free", "x")


def test_unresolved_input_is_tagged(store, tmp_path):  # noqa: F811
    with tracking.run("spikes", "u", "spike", inputs=[tracking.data_ref("nope", "nope-v9", "training")]):
        pass
    [run] = runs_of(store, "spikes")
    assert run.data.tags["mmz.input_unresolved"] == "nope@nope-v9"


def test_artifacts_are_scrubbed_of_paths(store, tmp_path):  # noqa: F811
    report = tmp_path / "summary.json"
    report.write_text(json.dumps({"out": "/home/someone/data/models/x", "auc": 0.9}))
    with tracking.run("edge/hil-bench", "a", "hil") as r:
        r.log_artifact(report)
    [run] = runs_of(store, "edge/hil-bench")
    local = store.download_artifacts(run.info.run_id, "summary.json", str(tmp_path / "dl"))
    assert json.loads(open(local).read()) == {"out": "x", "auc": 0.9}
