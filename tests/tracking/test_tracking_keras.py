"""Keras training with tracking on (feature 017 T043, T044, T045).

TensorFlow is not installed in CI; a minimal stand-in module provides the callback base class and
the seed function, and `fit`/`export` are replaced, so the test covers the tracking wiring only.
"""

import json
import sys
import types

from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture

from mobility_model_zoo.edge.int8 import keras_export


def _fake_tensorflow(monkeypatch):
    callbacks = types.SimpleNamespace(Callback=type("Callback", (), {}))
    keras = types.SimpleNamespace(
        callbacks=callbacks, utils=types.SimpleNamespace(set_random_seed=lambda s: None)
    )
    module = types.ModuleType("tensorflow")
    module.keras = keras
    module.__version__ = keras.__version__ = "0.0-fake"  # run_environment (feature 021)
    # deterministic training (feature 021): `tf.config.experimental.enable_op_determinism()`
    module.config = types.SimpleNamespace(
        experimental=types.SimpleNamespace(enable_op_determinism=lambda: None)
    )
    monkeypatch.setitem(sys.modules, "tensorflow", module)
    monkeypatch.setattr(keras_export, "tf", lambda: module)


def test_callback_sends_one_step_per_epoch(monkeypatch):
    _fake_tensorflow(monkeypatch)
    from mobility_model_zoo.tracking.keras import callback

    seen = []
    run = types.SimpleNamespace(log_step=lambda step, m: seen.append((step, m)))
    cb = callback(run)
    cb.on_epoch_end(0, {"loss": 0.5, "val_loss": 0.6})
    cb.on_epoch_end(1, {"loss": 0.4})
    assert seen == [(1, {"loss": 0.5, "val_loss": 0.6}), (2, {"loss": 0.4})]


def test_keras_training_is_one_tracked_run(store, tmp_path, monkeypatch):  # noqa: F811
    _fake_tensorflow(monkeypatch)

    def fake_fit(task, epochs, callbacks=None):
        for epoch in range(epochs):
            for cb in callbacks or []:
                cb.on_epoch_end(epoch, {"loss": 1.0 / (epoch + 1), "val_loss": 1.1 / (epoch + 1)})

    def fake_export(task, out, version, seed, report_extra=None):
        out.mkdir(parents=True, exist_ok=True)
        report = {
            "name": task.name,
            "version": version,
            "float_auc": 0.91,
            "int8_auc": 0.9,
            "datasets": [{"id": "mimii"}],
        }
        (out / f"{task.name}.report.json").write_text(json.dumps(report))
        return report

    monkeypatch.setattr(keras_export, "fit", fake_fit)
    monkeypatch.setattr(keras_export, "export", fake_export)
    task = types.SimpleNamespace(name="hum-fan")
    out = tmp_path / "derived" / "hum-fan"
    keras_export.train(lambda seed: task, "hum-fan", ["mimii"], epochs=3, version="0.1.0", out=out)

    [run] = runs_of(store, "condition-monitoring/sound-anomaly")
    tags = run.data.tags
    assert tags["mmz.kind"] == "train" and tags["mmz.model"] == "hum-fan"
    assert tags["mmz.task"] == "sound-anomaly" and tags["mmz.training_set"] == "mimii"
    assert [m.step for m in store.get_metric_history(run.info.run_id, "val_loss")] == [1, 2, 3]
    assert run.data.metrics["int8_auc"] == 0.9
    assert [a.path for a in store.list_artifacts(run.info.run_id)] == ["report.json"]
    assert sorted(p.name for p in out.iterdir()) == ["hum-fan.report.json"]  # export folder unchanged
    assert json.loads((out.parent / "hum-fan.tracking.json").read_text())["complete"] is True


def test_model_experiment_mapping():
    from mobility_model_zoo import tracking

    assert tracking.model_experiment("pace-cnn") == (
        "condition-monitoring/activity",
        "condition-monitoring",
        "activity",
    )
    assert tracking.model_experiment("picket-mlp")[0] == "security/can-ids"
    assert tracking.model_experiment("no-such-model")[0] == "spikes"
