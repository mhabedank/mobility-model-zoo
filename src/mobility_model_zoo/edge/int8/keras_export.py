"""Keras -> int8 TFLite -> QModel, shared by the task training modules (feature 005, T032).

Pipeline per model: features -> Keras model -> full-integer int8 TFLite ->
`tflite_import` (bit-exact with the TFLite reference kernels) -> metrics of the *device
arithmetic* (the int8 host reference) on the held-out test split.

Outputs go to `out` (default `$MMZ_DATA/derived/<model>/`, or `.../<model>/seed-<n>/` for tasks
with seed folders), never into the repository:

    <model>.npz          quantized model (parameters only, no data)
    <model>.tflite       int8 TFLite flatbuffer
    <model>.report.json  metrics, dataset provenance, licence, run provenance
    <model>.eval.npz     held-out quantized inputs for the HIL accuracy tests

Tasks with a pre-registration (`Prereg`, feature 021) refuse to train (exit 3) unless the benchmark
is frozen and the criteria record is committed unchanged, and record both in the run report.

Needs the `edge-train` extra (TensorFlow).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from mobility_model_zoo.edge.paths import derived_dir

Metrics = Callable[["Task", object, np.ndarray], tuple[dict, dict]]

REFUSED = 3  # exit code: frozen benchmark or pre-registration violated (specs/021 contracts/cli.md)


@dataclass
class Prereg:
    """Pre-registration of a task (feature 021, research R2): the committed criteria record and
    the frozen benchmark manifest that every run must name."""

    criteria: Path
    manifest: Path
    benchmark: str


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def weights_sha256(npz_path: Path) -> str:
    """SHA-256 of a QModel file without its `meta` block (which holds the training time), so two
    runs with identical parameters give the same value (reproduction check, research R4)."""
    with np.load(npz_path) as z:
        header = json.loads(bytes(z["header"]).decode())
        header.pop("meta", None)
        h = hashlib.sha256(json.dumps(header, sort_keys=True).encode())
        for key in sorted(k for k in z.files if k != "header"):
            h.update(key.encode())
            h.update(np.ascontiguousarray(z[key]).tobytes())
    return h.hexdigest()


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _refuse(message: str) -> None:
    print(f"refused: {message}", file=sys.stderr)
    raise SystemExit(REFUSED)


def check_prereg(p: Prereg, seed: int) -> dict:
    """Refuse a run outside the pre-registration; return the fields the run report records."""
    import yaml

    if not Path(p.manifest).exists():
        _refuse(f"benchmark {p.benchmark} is not frozen ({p.manifest} missing)")
    crit = Path(p.criteria)
    if not crit.exists():
        _refuse(f"criteria record {crit} is missing")
    cwd = crit.parent
    if _git(["ls-files", "--error-unmatch", crit.name], cwd).returncode != 0:
        _refuse(f"{crit.name} is not committed; commit it before the first run (FR-007)")
    if _git(["diff", "--quiet", "HEAD", "--", crit.name], cwd).returncode != 0:
        _refuse(f"{crit.name} differs from HEAD; amend it as a new version and commit it")
    data = yaml.safe_load(crit.read_text(encoding="utf-8"))
    if data.get("benchmark") != p.benchmark:
        _refuse(f"{crit.name} names benchmark {data.get('benchmark')!r}, not {p.benchmark!r}")
    seeds = [data["seeds"]["candidate"], *data["seeds"]["spread"]]
    if seed not in seeds:
        _refuse(f"seed {seed} is not pre-registered (seeds {seeds})")
    return {
        "benchmark": p.benchmark,
        "manifest_sha256": file_sha256(p.manifest),
        "criteria_version": data["version"],
        "criteria_sha256": file_sha256(crit),
        "criteria_commit": _git(["log", "-1", "--format=%H", "--", crit.name], cwd).stdout.strip(),
    }


def run_environment() -> dict:
    """Code and library versions of a run (research R4)."""
    from mobility_model_zoo.edge.paths import repo_root

    t = tf()
    root = repo_root()
    status = _git(["status", "--porcelain", "--untracked-files=no"], root)
    return {
        "git_commit": _git(["rev-parse", "HEAD"], root).stdout.strip(),
        "dirty": bool(status.stdout.strip()),
        "tensorflow": t.__version__,
        "keras": t.keras.__version__,
        "platform": platform.platform(),
    }


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


def macro_f1(y: np.ndarray, pred: np.ndarray, n_classes: int) -> float:
    """Mean of the per-class F1 scores (a class absent from labels and predictions counts as 0)."""
    f1 = []
    for c in range(n_classes):
        tp = int(((pred == c) & (y == c)).sum())
        fp = int(((pred == c) & (y != c)).sum())
        fn = int(((pred != c) & (y == c)).sum())
        f1.append(2 * tp / max(2 * tp + fp + fn, 1))
    return float(np.mean(f1))


def classification_metrics(task: Task, qm, out: np.ndarray) -> tuple[dict, dict]:
    """Accuracy and macro-F1 against the dataset labels (ground truth), float and int8 arithmetic."""
    pred_float = task.model.predict(task.x_test, verbose=0).argmax(-1)
    pred = out.argmax(1)
    n = max(len(task.labels), int(task.y_test.max()) + 1)
    return {
        "reference": "dataset labels",
        "float_accuracy": float((pred_float == task.y_test).mean()),
        "float_macro_f1": macro_f1(task.y_test, pred_float, n),
        "int8_accuracy": float((pred == task.y_test).mean()),
        "int8_macro_f1": macro_f1(task.y_test, pred, n),
        "test_samples": int(len(task.y_test)),
    }, {}


def validation_metrics(task: Task, qm) -> dict:
    """Float and int8 results on the validation split (informative; nothing is selected on them)."""
    from mobility_model_zoo.edge.int8.quant import quantize
    from mobility_model_zoo.edge.int8.reference import run_batch

    n = max(len(task.labels), int(task.y_val.max()) + 1)
    pred_float = task.model.predict(task.x_val, verbose=0).argmax(-1)
    xq = quantize(task.x_val.reshape(len(task.x_val), -1), qm.input_scale, qm.input_zp)
    pred = run_batch(qm, xq).argmax(1)
    return {
        "float_accuracy": float((pred_float == task.y_val).mean()),
        "float_macro_f1": macro_f1(task.y_val, pred_float, n),
        "int8_accuracy": float((pred == task.y_val).mean()),
        "int8_macro_f1": macro_f1(task.y_val, pred, n),
        "samples": int(len(task.y_val)),
    }


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


def export(task: Task, out: Path, version: str, seed: int = 0, report_extra: dict | None = None) -> dict:
    from mobility_model_zoo.edge.int8.quant import quantize
    from mobility_model_zoo.edge.int8.reference import run_batch
    from mobility_model_zoo.edge.int8.tflite_import import load_tflite, verify_with_interpreter

    out.mkdir(parents=True, exist_ok=True)
    tfl_path = out / f"{task.name}.tflite"
    tfl_path.write_bytes(to_int8_tflite(task.model, task.x_train))

    qm = load_tflite(str(tfl_path), task.name, task.description, seed=seed)
    xq = quantize(task.x_test.reshape(len(task.x_test), -1), qm.input_scale, qm.input_zp)
    # Deterministic check over every held-out window, not a sample (feature 021, FR-011).
    mismatches = verify_with_interpreter(str(tfl_path), qm, inputs=xq)
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
        "seed": seed,
        "description": task.description,
        "labels": task.labels,
        "summary": qm.summary(),
        **metrics,
        "validation": validation_metrics(task, qm) if task.kind == "classification" else None,
        "datasets": sources,
        **(report_extra or {}),
        "trained_at": qm.meta["trained_at"],
        "npz_sha256": file_sha256(out / f"{task.name}.npz"),
        "weights_sha256": weights_sha256(out / f"{task.name}.npz"),
    }
    (out / f"{task.name}.report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


TRAIN_DEFAULTS = {"epochs": 20, "seed": 0, "version": "0.1.0"}


def load_config(path: Path, name: str, fixed: dict) -> dict:
    """Read a task config (`configs/<topic>/<task>/<model>.yaml`).

    `train` holds the training options. Every other section documents values fixed in the code
    (architecture, features, protocol) and must equal `fixed`, so the config never drifts from
    what the code does.
    """
    import yaml

    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if cfg.get("model") != name:
        raise SystemExit(f"{path}: model is {cfg.get('model')!r}, expected {name!r}")
    extra = set(cfg) - {"model", "train", *fixed}
    if extra:
        raise SystemExit(f"{path}: unknown sections {sorted(extra)}")
    for section, values in fixed.items():
        if cfg.get(section) != values:
            raise SystemExit(f"{path}: section {section!r} differs from the code: {values!r}")
    unknown = set(cfg.get("train") or {}) - set(TRAIN_DEFAULTS)
    if unknown:
        raise SystemExit(f"{path}: unknown train options {sorted(unknown)}")
    return {**TRAIN_DEFAULTS, **(cfg.get("train") or {})}


def train_main(
    make_task: Callable[[int], Task],
    name: str,
    datasets: list[str],
    argv=None,
    doc: str = "",
    fixed: dict | None = None,
    *,
    prereg: Prereg | None = None,
    config: Path | None = None,
    allow_epochs: bool = True,
    per_seed_out: bool = False,
) -> dict:
    """Shared command line of the task training modules: train, export, report.

    `config` is the default task config (epochs and seed come from it); `allow_epochs=False`
    removes `--epochs` so the recipe config decides; `per_seed_out` writes each run to
    `$MMZ_DATA/derived/<name>/seed-<n>/`; `prereg` enforces the pre-registration (feature 021).
    """
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, help="task config; command-line options override it")
    if allow_epochs:
        ap.add_argument("--epochs", type=int)
    ap.add_argument("--version")
    ap.add_argument("--seed", type=int)
    default_out = f"$MMZ_DATA/derived/{name}/" + ("seed-<n>/" if per_seed_out else "")
    ap.add_argument("--out", type=Path, default=None, help=f"default {default_out}")
    ap.add_argument("--download", action="store_true", help="download the datasets first")
    args = ap.parse_args(argv)
    if prereg and not Path(prereg.manifest).exists():  # refuse before reading anything else
        _refuse(f"benchmark {prereg.benchmark} is not frozen ({prereg.manifest} missing)")
    cfg = args.config or config
    opts = load_config(cfg, name, fixed or {}) if cfg else dict(TRAIN_DEFAULTS)
    opts.update({k: getattr(args, k) for k in TRAIN_DEFAULTS if getattr(args, k, None) is not None})
    extra = check_prereg(prereg, opts["seed"]) if prereg else {}
    out = args.out
    if out is None and per_seed_out:
        out = derived_dir(name) / f"seed-{opts['seed']}"
    return train(
        make_task,
        name,
        datasets,
        opts["epochs"],
        opts["version"],
        opts["seed"],
        out,
        args.download,
        report_extra=extra,
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
    report_extra: dict | None = None,
) -> dict:
    from mobility_model_zoo.datasets import require_training_allowed

    for ds in datasets:  # FR-017: only declared, training_allowed, active datasets
        require_training_allowed(ds, model=name)
    if download:
        from mobility_model_zoo.datasets.download import download as fetch

        for ds in datasets:
            fetch(ds)
    t = tf()
    t.keras.utils.set_random_seed(seed)
    t.config.experimental.enable_op_determinism()  # research R4
    # The code state is recorded when the run starts, so edits during training do not change it.
    extra = {**(report_extra or {}), **run_environment(), "epochs": epochs}
    task = make_task(seed)
    fit(task, epochs)
    report = export(task, Path(out) if out else derived_dir(name), version, seed, extra)
    print(json.dumps({k: v for k, v in report.items() if k != "datasets"}, indent=2), flush=True)
    return report
