"""Keras -> int8 TFLite -> QModel, shared by the task training modules (feature 005, T032).

Pipeline per model: features -> Keras model -> full-integer int8 TFLite ->
`tflite_import` (bit-exact with the TFLite reference kernels) -> metrics of the *device
arithmetic* (the int8 host reference) on the held-out test split.

Outputs go to `out` (default `$MMZ_DATA/derived/<model>/`), never into the repository:

    <model>.npz          quantized model (parameters only, no data)
    <model>.tflite       int8 TFLite flatbuffer
    <model>.report.json  metrics, dataset provenance, licence
    <model>.eval.npz     held-out quantized inputs for the HIL accuracy tests

Needs the `edge-train` extra (TensorFlow).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from mobility_model_zoo.edge.paths import derived_dir

Metrics = Callable[["Task", object, np.ndarray], tuple[dict, dict]]


@dataclass
class Task:
    name: str
    model: object  # keras.Model (float, may end with softmax)
    x_train: np.ndarray
    y_train: np.ndarray
    x_val: np.ndarray
    y_val: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    datasets: list[str]
    description: str
    labels: list[str] = field(default_factory=list)
    fit_kwargs: dict = field(default_factory=dict)
    preprocess: dict = field(default_factory=dict)  # host-side feature normalisation
    kind: str = "classification"  # or "anomaly" (autoencoder on normal data)
    # (task, qmodel, int8 outputs on x_test) -> (metrics, extra model meta); default: classification
    metrics: Metrics | None = None
    # anomaly tasks: the reconstruction target saved with the eval set
    eval_targets: bool = False


def tf():
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow

    return tensorflow


def to_int8_tflite(model, rep: np.ndarray) -> bytes:
    t = tf()

    def gen():
        for i in range(min(len(rep), 500)):
            yield [rep[i : i + 1].astype(np.float32)]

    conv = t.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [t.lite.Optimize.DEFAULT]
    conv.representative_dataset = gen
    conv.target_spec.supported_ops = [t.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = t.int8
    conv.inference_output_type = t.int8
    return conv.convert()


def fit(task: Task, epochs: int) -> None:
    t = tf()
    m = task.model
    lr = t.keras.optimizers.schedules.CosineDecay(
        2e-3, decay_steps=max(1, epochs * int(np.ceil(len(task.x_train) / 128)))
    )
    if task.kind == "anomaly":  # autoencoder on normal data only
        m.compile(optimizer=t.keras.optimizers.Adam(lr), loss="mse")
        m.fit(
            task.x_train,
            task.x_train,
            validation_data=(task.x_val, task.x_val),
            epochs=epochs,
            batch_size=128,
            verbose=2,
            **task.fit_kwargs,
        )
        return
    m.compile(
        optimizer=t.keras.optimizers.Adam(lr),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    m.fit(
        task.x_train,
        task.y_train,
        validation_data=(task.x_val, task.y_val),
        epochs=epochs,
        batch_size=128,
        verbose=2,
        **task.fit_kwargs,
    )


def classification_metrics(task: Task, qm, out: np.ndarray) -> tuple[dict, dict]:
    """Accuracy against the dataset labels (ground truth), float model and int8 device arithmetic."""
    pred_float = task.model.predict(task.x_test, verbose=0).argmax(-1)
    return {
        "reference": "dataset labels",
        "float_accuracy": float((pred_float == task.y_test).mean()),
        "int8_accuracy": float((out.argmax(1) == task.y_test).mean()),
        "test_samples": int(len(task.y_test)),
    }, {}


def provenance(datasets: list[str]) -> list[dict]:
    from mobility_model_zoo.datasets.download import dataset_dir
    from mobility_model_zoo.datasets.registry import SOURCES

    rows = []
    for d in datasets:
        src = dataset_dir(d) / "SOURCE.json"
        s = SOURCES[d]
        rows.append(
            {
                "id": s.id,
                "title": s.title,
                "license": s.license,
                "attribution": s.attribution,
                "citation": s.citation,
                "homepage": s.homepage,
                "retrieved": json.loads(src.read_text()).get("retrieved_at") if src.exists() else None,
            }
        )
    return rows


def export(task: Task, out: Path, version: str, seed: int = 0) -> dict:
    from mobility_model_zoo.edge.int8.quant import quantize
    from mobility_model_zoo.edge.int8.reference import run_batch
    from mobility_model_zoo.edge.int8.tflite_import import load_tflite, verify_with_interpreter

    out.mkdir(parents=True, exist_ok=True)
    tfl_path = out / f"{task.name}.tflite"
    tfl_path.write_bytes(to_int8_tflite(task.model, task.x_train))

    qm = load_tflite(str(tfl_path), task.name, task.description, seed=seed)
    mismatches = verify_with_interpreter(str(tfl_path), qm, n=32)

    xq = quantize(task.x_test.reshape(len(task.x_test), -1), qm.input_scale, qm.input_zp)
    y_int8 = run_batch(qm, xq)
    metrics, extra_meta = (task.metrics or classification_metrics)(task, qm, y_int8)
    metrics["tflite_interpreter_mismatches"] = int(mismatches)
    sources = provenance(task.datasets)
    qm.meta.update(
        task=task.kind,
        classes=task.labels,
        version=version,
        datasets=sources,
        preprocess=task.preprocess,
        trained_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **metrics,
        **extra_meta,
    )
    qm.save(out / f"{task.name}.npz")

    keep = np.random.default_rng(seed).permutation(len(xq))[:1024]
    ev = {"inputs": xq[keep], "labels": task.y_test[keep].astype(np.int32)}
    if task.eval_targets:
        ev["targets"] = task.x_test.reshape(len(task.x_test), -1).astype(np.float32)[keep]
    np.savez_compressed(out / f"{task.name}.eval.npz", **ev)

    report = {
        "name": task.name,
        "version": version,
        "description": task.description,
        "labels": task.labels,
        "summary": qm.summary(),
        **metrics,
        "datasets": sources,
    }
    (out / f"{task.name}.report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def train_main(
    make_task: Callable[[int], Task], name: str, datasets: list[str], argv=None, doc: str = ""
) -> dict:
    """Shared command line of the task training modules: train, export, report."""
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--version", default="0.1.0")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None, help=f"default $MMZ_DATA/derived/{name}/")
    ap.add_argument("--download", action="store_true", help="download the datasets first")
    args = ap.parse_args(argv)
    return train(
        make_task, name, datasets, args.epochs, args.version, args.seed, args.out, args.download
    )


def train(
    make_task: Callable[[int], Task],
    name: str,
    datasets: list[str],
    epochs: int = 20,
    version: str = "0.1.0",
    seed: int = 0,
    out: Path | None = None,
    download: bool = False,
) -> dict:
    if download:
        from mobility_model_zoo.datasets.download import download as fetch

        for ds in datasets:
            fetch(ds)
    tf().keras.utils.set_random_seed(seed)
    task = make_task(seed)
    fit(task, epochs)
    report = export(task, Path(out) if out else derived_dir(name), version, seed)
    print(json.dumps({k: v for k, v in report.items() if k != "datasets"}, indent=2), flush=True)
    return report
