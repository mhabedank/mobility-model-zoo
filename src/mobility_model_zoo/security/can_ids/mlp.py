"""picket-mlp: per-frame CAN intrusion detection MLP for the int8 engine (feature 005, T032).

    uv run zoo data download road
    uv run security can-ids mlp train [--epochs 20] [--out DIR]

Features a CAN gateway can compute with O(#IDs) state, a Keras MLP (32-64-32-2), full-integer
int8 TFLite and the bit-exact host reference. Frames come from the common frame format
(`frames.py`); metrics come from `metrics.py`, the same code that scores picket-forest.
Needs the `edge-train` extra.
"""

from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np

from mobility_model_zoo.edge.int8.keras_export import Task, tf, train_main
from mobility_model_zoo.security.can_ids import frames

NAME = "picket-mlp"
DATASETS = ["road"]
CAN_FEATURES = 32
AMBIENT_MAX_BYTES = 120e6  # keep CI time and memory bounded
BENIGN_KEEP = 0.15  # subsample of the long benign captures


def can_features(f: dict, known_ids: set) -> np.ndarray:
    """Per-frame features: 11 ID bits, DLC, 8 payload bytes, log inter-arrival time of this ID,
    ratio to the previous inter-arrival time, payload Hamming distance and per-byte deltas to the
    previous frame of the same ID, known-ID flag. `f` comes from `frames.to_arrays`."""
    n = len(f["t"])
    order = np.lexsort((f["t"], f["id"]))  # group by ID, then time
    same = np.zeros(n, bool)
    same[1:] = f["id"][order][1:] == f["id"][order][:-1]
    prev = np.where(same, np.roll(order, 1), -1)  # previous frame of the same ID (sorted space)
    prev_idx = np.full(n, -1)
    prev_idx[order] = prev
    has = prev_idx >= 0
    p = np.where(has, prev_idx, 0)
    dt = np.where(has, f["t"] - f["t"][p], 1.0)
    pp = np.where(has, prev_idx[p], -1)
    dt_prev = np.where(pp >= 0, f["t"][p] - f["t"][np.maximum(pp, 0)], dt)
    d = f["data"].astype(np.int64)
    dprev = np.where(has[:, None], d[p], d)
    x = np.zeros((n, CAN_FEATURES), np.float32)
    x[:, 0:11] = (f["id"][:, None] >> np.arange(11)) & 1
    x[:, 11] = f["dlc"] / 8.0
    x[:, 12:20] = d / 255.0
    x[:, 20] = np.clip((np.log10(np.maximum(dt, 1e-6)) + 6) / 6, 0, 1.5)
    x[:, 21] = np.clip(np.log2(np.maximum(dt, 1e-6) / np.maximum(dt_prev, 1e-6)) / 8 + 0.5, 0, 1)
    x[:, 22] = np.unpackbits((d ^ dprev).astype(np.uint8), axis=1).sum(1) / 64.0
    x[:, 23:31] = np.abs(d - dprev) / 255.0
    x[:, 31] = np.isin(f["id"], list(known_ids)).astype(np.float32)
    return x


def split_of(capture: str) -> str:
    """Deterministic split: every 4th ambient capture and the `_2` attack runs are test data."""
    kind, name = capture.split("/", 1)
    if kind == "ambient":
        return "test" if zlib.crc32(name.encode()) % 4 == 0 else "train"
    return "test" if Path(name).stem.removesuffix("_masquerade").endswith("_2") else "train"


def load_can(seed: int = 0, directory: Path | None = None) -> dict:
    from mobility_model_zoo.datasets.download import dataset_dir

    caps = list(frames.from_road(directory or dataset_dir("road"), AMBIENT_MAX_BYTES))
    known: set[int] = set()
    for df in caps:
        if df["capture"].iat[0].startswith("ambient/"):
            known |= set(np.unique(df["can_id"]).tolist())
    rng = np.random.default_rng(seed)
    parts: dict[str, list] = {"train": [], "test": []}
    for df in caps:
        cap = df["capture"].iat[0]
        x = can_features(frames.to_arrays(df), known)
        y = df["label"].to_numpy(np.int64)
        if cap.startswith("ambient/"):
            keep = rng.random(len(y)) < BENIGN_KEEP
            x, y = x[keep], y[keep]
        parts[split_of(cap)].append((x, y))
        print(f"road {cap}: {len(y)} frames, {int(y.sum())} attack, {split_of(cap)}", flush=True)
    out = {}
    for split, items in parts.items():
        x = np.concatenate([a for a, _ in items])
        y = np.concatenate([b for _, b in items])
        perm = rng.permutation(len(y))
        out[split] = (x[perm], y[perm])
        print(f"can {split}: {len(y)} frames, {y.mean() * 100:.2f}% attack", flush=True)
    return out


def can_model():
    layers = tf().keras.layers
    arch = FIXED["architecture"]
    x = inp = layers.Input((arch["inputs"],))
    for units in arch["dense"]:
        x = layers.Dense(units, activation=arch["activation"])(x)
    x = layers.Dense(arch["outputs"])(x)
    x = layers.Softmax()(x)
    return tf().keras.Model(inp, x)


def frame_report(task: Task, qm, out: np.ndarray) -> tuple[dict, dict]:
    """Frame metrics of the int8 device arithmetic against the ROAD labels (metrics.py)."""
    from mobility_model_zoo.edge.int8.quant import dequantize
    from mobility_model_zoo.security.can_ids.metrics import frame_metrics

    score = dequantize(out, qm.output_scale, qm.output_zp)[:, 1]
    float_score = task.model.predict(task.x_test, verbose=0)[:, 1]
    m = frame_metrics(task.y_test, score, 0.5)
    f = frame_metrics(task.y_test, float_score, 0.5)
    return {
        "reference": "dataset labels (ROAD injection intervals)",
        **{f"int8_{k}": v for k, v in m.items()},
        "float_f1": f["f1"],
        "float_auc_pr": f["auc_pr"],
        "test_samples": int(len(task.y_test)),
    }, {}


def make_task(seed: int, directory: Path | None = None) -> Task:
    d = load_can(seed, directory)
    xtr, ytr = d["train"]
    n_val = len(ytr) // 10
    pos = max(ytr.mean(), 1e-4)
    return Task(
        name=NAME,
        model=can_model(),
        x_train=xtr[n_val:],
        y_train=ytr[n_val:],
        x_val=xtr[:n_val],
        y_val=ytr[:n_val],
        x_test=d["test"][0],
        y_test=d["test"][1],
        datasets=DATASETS,
        labels=["normal", "attack"],
        description="CAN bus intrusion detection MLP (32-64-32-2) on per-frame features, trained on "
        "the ROAD dataset (real vehicle; fuzzing, fabrication, masquerade attacks)",
        fit_kwargs={"class_weight": {0: 1.0, 1: float(min(0.5 / pos, 50.0))}},
        metrics=frame_report,
    )


# Values fixed in the code, documented in configs/security/can-ids/picket-mlp.yaml.
FIXED = {
    "architecture": {"inputs": CAN_FEATURES, "dense": [64, 32], "outputs": 2, "activation": "relu"},
    "data": {
        "dataset": "road",
        "benign_keep": BENIGN_KEEP,
        "ambient_max_bytes": int(AMBIENT_MAX_BYTES),
        "test_attacks": "captures whose name ends in _2 (also _2_masquerade)",
        "test_ambient": "every 4th capture by CRC32 of the file name",
        "validation": "first tenth of the shuffled training frames",
        "class_weight": "attack weight min(0.5 / attack share, 50)",
    },
}


def main(argv=None) -> dict:
    return train_main(make_task, NAME, DATASETS, argv, __doc__, FIXED)


if __name__ == "__main__":
    main()
