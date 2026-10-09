"""Keras -> int8 TFLite -> QModel export shared by the task training modules (T032, T035)."""

import json

import numpy as np
import pytest

pytest.importorskip("tensorflow")
pytest.importorskip("tflite")

from mobility_model_zoo.edge.int8.keras_export import Task, export, fit, tf  # noqa: E402
from mobility_model_zoo.edge.int8.model import QModel  # noqa: E402


def _task(metrics=None) -> Task:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(600, 8)).astype(np.float32)
    y = (x[:, 0] + x[:, 1] > 0).astype(np.int64)
    layers = tf().keras.layers
    inp = layers.Input((8,))
    out = layers.Softmax()(layers.Dense(2)(layers.Dense(8, activation="relu")(inp)))
    tf().keras.utils.set_random_seed(0)
    return Task(
        name="tiny-net",
        model=tf().keras.Model(inp, out),
        x_train=x[:400],
        y_train=y[:400],
        x_val=x[400:500],
        y_val=y[400:500],
        x_test=x[500:],
        y_test=y[500:],
        datasets=[],
        description="test model",
        labels=["normal", "attack"],
        metrics=metrics,
    )


@pytest.mark.parametrize("frame_metrics", [False, True])
def test_export_writes_bit_exact_model_outside_the_repo(tmp_path, frame_metrics):
    from mobility_model_zoo.security.can_ids.mlp import frame_report

    task = _task(frame_report if frame_metrics else None)
    fit(task, epochs=60)
    report = export(task, tmp_path, "0.1.0")
    assert report["tflite_interpreter_mismatches"] == 0
    assert report["reference"].startswith("dataset labels")
    if frame_metrics:  # metrics.py frame metrics of the int8 arithmetic
        assert {"int8_f1", "int8_recall", "int8_fpr", "int8_auc_pr"} <= set(report)
    else:
        assert report["int8_accuracy"] > 0.8
    qm = QModel.load(tmp_path / "tiny-net.npz")
    assert qm.name == "tiny-net" and qm.meta["version"] == "0.1.0"
    with np.load(tmp_path / "tiny-net.eval.npz") as ev:
        assert ev["inputs"].dtype == np.int8 and len(ev["labels"]) == 100
    assert json.loads((tmp_path / "tiny-net.report.json").read_text())["name"] == "tiny-net"


def test_macro_f1():
    from mobility_model_zoo.edge.int8.keras_export import macro_f1

    y = np.array([0, 0, 1, 1, 2, 2])
    assert macro_f1(y, y, 3) == 1.0
    # class 2 never predicted: F1 0 for it; classes 0 and 1 have one error each
    assert abs(macro_f1(y, np.array([0, 0, 1, 1, 0, 1]), 3) - (0.8 + 0.8 + 0) / 3) < 1e-9
