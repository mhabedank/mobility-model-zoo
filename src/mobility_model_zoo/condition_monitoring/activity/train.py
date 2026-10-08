"""pace-cnn: human activity recognition CNN for the int8 engine (feature 005, T032).

    uv run zoo data download uci-har
    uv run condmon activity train [--epochs 20] [--out DIR]

A 1D-CNN over 2.56 s of accelerometer and gyroscope signals (9 x 128 @50 Hz) of UCI HAR,
full-integer int8 TFLite and the bit-exact host reference. Needs the `edge-train` extra.
"""

from __future__ import annotations

import numpy as np

from mobility_model_zoo.edge.int8.keras_export import Task, tf, train_main

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


def load_har():
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
        return x, y

    return split("train"), split("test")


def cnn():
    layers = tf().keras.layers
    x = inp = layers.Input((1, 128, 9))
    for filters, k in ((16, 5), (32, 5)):
        x = layers.Conv2D(filters, (1, k), padding="same", use_bias=False)(x)
        x = layers.BatchNormalization()(x)
        x = layers.ReLU()(x)
        x = layers.MaxPooling2D((1, 2))(x)
    x = layers.Conv2D(32, (1, 3), padding="same", use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.AveragePooling2D((1, 32))(x)
    x = layers.Flatten()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(len(LABELS))(x)
    x = layers.Softmax()(x)
    return tf().keras.Model(inp, x)


def make_task(seed: int) -> Task:
    (xtr, ytr), (xte, yte) = load_har()
    mean = xtr.reshape(-1, 9).mean(0)
    std = xtr.reshape(-1, 9).std(0) + 1e-6

    def norm(a):
        return ((a - mean) / std)[:, None, :, :].astype(np.float32)

    perm = np.random.default_rng(seed).permutation(len(ytr))
    n_val = len(ytr) // 7
    val, tr = perm[:n_val], perm[n_val:]
    return Task(
        name=NAME,
        model=cnn(),
        x_train=norm(xtr[tr]),
        y_train=ytr[tr],
        x_val=norm(xtr[val]),
        y_val=ytr[val],
        x_test=norm(xte),
        y_test=yte,
        datasets=DATASETS,
        labels=LABELS,
        description="Human activity recognition 1D-CNN over 2.56 s of accelerometer + gyroscope "
        "(9 x 128 @50 Hz), trained on UCI HAR",
        preprocess={"channels": SIGNALS, "mean": mean.tolist(), "std": std.tolist()},
    )


def main(argv=None) -> dict:
    return train_main(make_task, NAME, DATASETS, argv, __doc__)


if __name__ == "__main__":
    main()
