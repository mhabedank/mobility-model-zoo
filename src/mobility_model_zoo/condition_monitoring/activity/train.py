"""pace-cnn: human activity recognition CNN for the int8 engine (features 005 and 021).

    uv run zoo data download uci-har
    uv run condmon activity freeze                  # benchmark uci-har-v1, once
    uv run condmon activity train --seed N [--out DIR]

A 1D-CNN over 2.56 s of accelerometer and gyroscope signals (9 x 128 @50 Hz) of UCI HAR,
full-integer int8 TFLite and the bit-exact host reference. Training uses the frozen benchmark's
subject-wise split and normalisation and refuses to run unless the criteria record
(configs/condition-monitoring/activity/pace-cnn-criteria.yaml) is committed. Epochs come from the
recipe config. Needs the `edge-train` extra.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from mobility_model_zoo.condition_monitoring import benchmark as bm
from mobility_model_zoo.edge.int8.keras_export import Prereg, Task, tf, train_main

NAME = "pace-cnn"
DATASETS = ["uci-har"]
LABELS = ["walking", "walking_upstairs", "walking_downstairs", "sitting", "standing", "laying"]
SIGNALS = [
    "body_acc_x",
    "body_acc_y",
    "body_acc_z",
    "body_gyro_x",
    "body_gyro_y",
    "body_gyro_z",
    "total_acc_x",
    "total_acc_y",
    "total_acc_z",
]


# Benchmark uci-har-v1 (topics/condition-monitoring/tasks/activity.md, research R1). The only place
# these values live as data; the recipe config states them as text, which load_config keeps equal.
BENCHMARK = {
    "id": "uci-har-v1",
    "validation_seed": 2026,
    "validation_divisor": 7,  # validation = a seventh of the training subjects (3 of 21)
}


class HarSplit(NamedTuple):
    x: np.ndarray  # (n, 128, 9) float32
    y: np.ndarray  # (n,) int64, 0-based class index
    subjects: np.ndarray  # (n,) int64, the dataset's subject number per window


def load_har() -> tuple[HarSplit, HarSplit]:
    """(train, test) of the official UCI HAR split, with the subject of every window."""
    from mobility_model_zoo.datasets.download import dataset_dir

    hits = sorted((dataset_dir("uci-har") / "extracted").rglob("train/Inertial Signals"))
    if not hits:
        raise SystemExit("uci-har not downloaded: zoo data download uci-har")
    base = hits[0].parent.parent

    def split(name):
        x = np.stack(
            [
                np.loadtxt(base / name / "Inertial Signals" / f"{sig}_{name}.txt", dtype=np.float32)
                for sig in SIGNALS
            ],
            axis=-1,
        )  # (n, 128, 9)
        y = np.loadtxt(base / name / f"y_{name}.txt", dtype=np.int64) - 1
        subjects = np.loadtxt(base / name / f"subject_{name}.txt", dtype=np.int64)
        return HarSplit(x, y, subjects)

    return split("train"), split("test")


def cnn():
    arch = FIXED["architecture"]
    layers = tf().keras.layers
    x = inp = layers.Input(tuple(arch["input"]))
    for block in arch["blocks"]:
        filters, k = block["conv"]
        x = layers.Conv2D(filters, (1, k), padding="same", use_bias=False)(x)
        x = layers.BatchNormalization()(x)
        x = layers.ReLU()(x)
        if "max_pool" in block:
            x = layers.MaxPooling2D((1, block["max_pool"]))(x)
        else:
            x = layers.AveragePooling2D((1, block["avg_pool"]))(x)
    x = layers.Flatten()(x)
    x = layers.Dropout(arch["dropout"])(x)
    x = layers.Dense(arch["outputs"])(x)
    x = layers.Softmax()(x)
    return tf().keras.Model(inp, x)


def config_path():
    return bm.repo() / "configs" / "condition-monitoring" / "activity" / f"{NAME}.yaml"


def criteria_path():
    return bm.repo() / "configs" / "condition-monitoring" / "activity" / f"{NAME}-criteria.yaml"


def manifest_path():
    return bm.manifest_path(BENCHMARK["id"])


def _parts(train: HarSplit, test: HarSplit, val_subjects: list[int]) -> dict[str, HarSplit]:
    is_val = np.isin(train.subjects, val_subjects)
    return {
        "train": HarSplit(train.x[~is_val], train.y[~is_val], train.subjects[~is_val]),
        "validation": HarSplit(train.x[is_val], train.y[is_val], train.subjects[is_val]),
        "test": test,
    }


def normalisation(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-channel mean and std (+1e-6) of windows (n, 128, 9), in float32."""
    flat = x.reshape(-1, x.shape[-1])
    return flat.mean(0), flat.std(0) + np.float32(1e-6)


def build_manifest() -> dict:
    """The uci-har-v1 manifest of contracts/records.md (no subject numbers, FR-028)."""
    train, test = load_har()
    n_subjects = len(set(train.subjects.tolist()))
    _, val = bm.split_subjects(
        train.subjects, BENCHMARK["validation_seed"], BENCHMARK["validation_divisor"]
    )
    parts = _parts(train, test, val)
    mean, std = normalisation(parts["train"].x)
    return {
        "benchmark": BENCHMARK["id"],
        "datasets": [bm.dataset_entry(ds) for ds in DATASETS],
        "protocol": {
            "test": "official UCI HAR test split",
            "validation": (
                f"{len(val)} of the {n_subjects} training subjects, drawn with validation_seed"
            ),
            "validation_seed": BENCHMARK["validation_seed"],
            "normalisation": FIXED["data"]["normalisation"],
            "window": {"samples": 128, "channels": len(SIGNALS), "rate_hz": 50, "overlap": 0.5},
            "headline_metrics": ["int8_macro_f1", "int8_accuracy"],
        },
        "splits": {k: bm.split_entry(p.subjects, p.x, p.y) for k, p in parts.items()},
        "normalisation": {"mean": [float(v) for v in mean], "std": [float(v) for v in std]},
    }


def frozen_splits(manifest: dict) -> dict[str, HarSplit]:
    """The splits of the frozen benchmark, each checked against its subject and data hashes."""
    train, test = load_har()
    _, val = bm.split_subjects(
        train.subjects, manifest["protocol"]["validation_seed"], BENCHMARK["validation_divisor"]
    )
    parts = _parts(train, test, val)
    for name, p in parts.items():
        bm.verify_split(manifest, name, p.subjects, p.x, p.y)
    return parts


def make_task(seed: int) -> Task:
    manifest = bm.load_manifest(manifest_path())
    parts = frozen_splits(manifest)
    mean = np.asarray(manifest["normalisation"]["mean"], np.float32)
    std = np.asarray(manifest["normalisation"]["std"], np.float32)

    def norm(a):
        return ((a - mean) / std)[:, None, :, :].astype(np.float32)

    tr, va, te = parts["train"], parts["validation"], parts["test"]
    return Task(
        name=NAME,
        model=cnn(),
        x_train=norm(tr.x),
        y_train=tr.y,
        x_val=norm(va.x),
        y_val=va.y,
        x_test=norm(te.x),
        y_test=te.y,
        datasets=DATASETS,
        labels=LABELS,
        description="Human activity recognition 1D-CNN over 2.56 s of accelerometer + gyroscope "
        "(9 x 128 @50 Hz), trained on UCI HAR",
        preprocess={"channels": SIGNALS, "mean": mean.tolist(), "std": std.tolist()},
    )


# Values fixed in the code, documented in configs/condition-monitoring/activity/pace-cnn.yaml.
FIXED = {
    "architecture": {
        "input": [1, 128, 9],
        "blocks": [
            {"conv": [16, 5], "batch_norm": True, "relu": True, "max_pool": 2},
            {"conv": [32, 5], "batch_norm": True, "relu": True, "max_pool": 2},
            {"conv": [32, 3], "batch_norm": True, "relu": True, "avg_pool": 32},
        ],
        "dropout": 0.3,
        "outputs": len(LABELS),
    },
    "data": {
        "dataset": "uci-har",
        "channels": SIGNALS,
        "test": "official test split (30 % of the subjects)",
        "validation": "3 of the 21 training subjects, drawn with validation_seed 2026",
        "normalisation": "per channel, mean and std of the training subjects (validation excluded)",
    },
}


def main(argv=None) -> dict:
    return train_main(
        make_task,
        NAME,
        DATASETS,
        argv,
        __doc__,
        FIXED,
        prereg=Prereg(criteria_path(), manifest_path(), BENCHMARK["id"]),
        config=config_path(),
        allow_epochs=False,
        per_seed_out=True,
    )


if __name__ == "__main__":
    main()
