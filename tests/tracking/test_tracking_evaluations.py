"""Evaluation, measurement and training results as runs (feature 017 T046-T049, T052, T061)."""

import json

from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture

from mobility_model_zoo import tracking
from mobility_model_zoo.edge.bench.results import Recorder, write_summary
from mobility_model_zoo.security.can_ids import track


def test_record_keeps_numbers_only(store):  # noqa: F811
    rid = tracking.record(
        "spikes",
        "r",
        "spike",
        "evaluate",
        {"a": {"b": 1, "c": "text", "d": True, "e": float("nan")}, "f": 2.5},
    )
    [run] = runs_of(store, "spikes")
    assert run.info.run_id == rid
    assert run.data.metrics == {"a.b": 1.0, "f": 2.5}


def test_record_without_uri_is_a_no_op(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    from mobility_model_zoo.tracking import config

    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    assert tracking.record("spikes", "r", "spike", "evaluate", {"a": 1}) is None


def test_can_ids_evaluation_names_its_benchmark(store):  # noqa: F811
    result = {
        "benchmark": "can-ids-v3",
        "sets": ["set_01"],
        "partial": True,
        "detectors": {"picket-forest": {"recall": 0.97, "false_alarms_per_hour": 0.4}},
    }
    track.evaluation(result, "can-ids-v3", "picket-forest")
    [run] = runs_of(store, "security/can-ids", "datasets.name = 'can-ids@can-ids-v3'")
    assert run.data.tags["mmz.kind"] == "evaluate" and run.data.tags["mmz.benchmark"] == "can-ids-v3"
    assert run.data.metrics["detectors.picket-forest.recall"] == 0.97


def test_picket_forest_training_logs_config_never_model_files(store, tmp_path):  # noqa: F811
    export = tmp_path / "export-v2"
    export.mkdir()
    (export / "config.json").write_text(
        json.dumps({"benchmark": "can-ids-v3", "manifest_sha256": "a" * 64, "code_commit": "b" * 12})
    )
    (export / "model.joblib").write_bytes(b"weights")
    config = {"frame_threshold": 0.5, "tree_nodes": 1234, "hyperparameters": {"n_estimators": 64}}
    track.training(config, "can-ids-v3", export, None)
    [run] = runs_of(store, "security/can-ids")
    assert run.data.tags["mmz.kind"] == "train"
    assert run.data.tags["mmz.training_set"] == "can-ids-v3:train+calibration"
    assert run.data.params["hp.n_estimators"] == "64"
    assert run.inputs.dataset_inputs[0].dataset.name == "can-ids@can-ids-v3"
    assert [a.path for a in store.list_artifacts(run.info.run_id)] == ["export-config.json"]


def test_measurement_and_hil_runs(store, tmp_path):  # noqa: F811
    track.measurement(
        [{"name": "latency_ms", "value": 1.2, "hardware": "esp32s3"}], "esp32", "esp32-a", "0.2.1"
    )
    rec = Recorder(tmp_path)
    rec.record(
        "bench", "sim", model="hum-fan", us_avg=120.0, us_min=100, us_max=150, cyc_avg=0, macs=1000, n=10
    )
    rec.record("test", "sim", outcome="passed", nodeid="t::a")
    write_summary(tmp_path)
    [m] = runs_of(store, "security/can-ids")
    assert m.data.tags["mmz.kind"] == "measure" and m.data.tags["mmz.hardware"] == "esp32-a"
    [hil] = runs_of(store, "edge/hil-bench")
    assert hil.data.tags["mmz.kind"] == "measure"
    assert hil.data.metrics["perf.sim.hum-fan.us_avg"] == 120.0
    assert store.list_artifacts(hil.info.run_id) == []  # board details and failure texts stay local
