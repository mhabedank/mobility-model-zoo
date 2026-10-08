"""hum-fan: machine-sound anomaly detection autoencoder for the int8 engine (feature 005, T032).

    uv run zoo data download mimii
    uv run condmon sound-anomaly train [--epochs 20] [--out DIR]

Log-mel context windows of the normal fan recordings of MIMII (6 dB SNR) train a dense
autoencoder; the anomaly score is the reconstruction error averaged over a 10 s clip. Clips are
split per machine id as in the DCASE protocol, thresholds come from validation normals only.
Needs the `edge-train` extra.
"""

from __future__ import annotations

import numpy as np

from mobility_model_zoo.condition_monitoring.sound_anomaly.features import SR, log_mel, read_wav
from mobility_model_zoo.edge.int8.keras_export import Task, tf, train_main

NAME = "hum-fan"
DATASETS = ["mimii"]
MELS = 40
FRAMES = 5  # context of 5 x 64 ms -> 200 inputs
FFT = 1024  # 64 ms @16 kHz
HOP = 512


def roc_auc(scores: np.ndarray, labels: np.ndarray, max_fpr: float = 1.0) -> float:
    """Area under the ROC curve (labels 1 = anomaly); with max_fpr < 1 the partial
    AUC normalised to [0, 1] as in DCASE (pAUC)."""
    order = np.argsort(-scores, kind="mergesort")
    s, y = scores[order], labels[order].astype(bool)
    distinct = np.r_[np.nonzero(np.diff(s))[0], len(s) - 1]
    tpr = np.r_[0.0, np.cumsum(y)[distinct] / max(y.sum(), 1)]
    fpr = np.r_[0.0, np.cumsum(~y)[distinct] / max((~y).sum(), 1)]
    if max_fpr < 1.0:
        stop = np.searchsorted(fpr, max_fpr, side="right")
        tpr = np.r_[tpr[:stop], np.interp(max_fpr, fpr, tpr)]
        fpr = np.r_[fpr[:stop], max_fpr]
    return float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2) / max_fpr)


def clip_logmel(path: str) -> np.ndarray:
    # channel 0 only: a deployed sensor has a single microphone
    x = read_wav(path, length=10 * SR, channel=0)
    return log_mel(x, n_mels=MELS, win=FFT, hop=HOP, nfft=FFT, fmax=SR / 2)


def windows(lm: np.ndarray, stride: int = 1) -> np.ndarray:
    """(frames, mels) log-mel -> (n, FRAMES * mels) stacked context windows."""
    n = (len(lm) - FRAMES) // stride + 1
    idx = np.arange(FRAMES)[None, :] + stride * np.arange(n)[:, None]
    return lm[idx].reshape(n, -1)


def load_mimii(seed: int = 0, workers: int = 4):
    """Clips per machine id; per id as many normal clips as abnormal ones are held out
    for testing (DCASE protocol), the rest of the normals train the autoencoder."""
    from multiprocessing import Pool

    from mobility_model_zoo.datasets.download import dataset_dir

    clips = sorted((dataset_dir("mimii") / "extracted").rglob("*.wav"))
    if not clips:
        raise SystemExit("mimii not downloaded: zoo data download mimii")
    rng = np.random.default_rng(seed)
    by_id: dict[str, dict[str, list[str]]] = {}
    for c in clips:
        by_id.setdefault(c.parent.parent.name, {}).setdefault(c.parent.name, []).append(str(c))
    train, test = [], []  # (path, label, machine)
    for mid, d in sorted(by_id.items()):
        normal = [d["normal"][i] for i in rng.permutation(len(d.get("normal", [])))]
        abnormal = d.get("abnormal", [])
        n_hold = min(len(abnormal), len(normal) // 2)
        test += [(c, 0, mid) for c in normal[:n_hold]] + [(c, 1, mid) for c in abnormal]
        train += [(c, 0, mid) for c in normal[n_hold:]]
        print(
            f"mimii {mid}: {len(normal) - n_hold} train normal, {n_hold} test normal, "
            f"{len(abnormal)} test abnormal",
            flush=True,
        )
    with Pool(workers) as pool:
        lm_train = pool.map(clip_logmel, [c for c, _, _ in train], chunksize=8)
        lm_test = pool.map(clip_logmel, [c for c, _, _ in test], chunksize=8)
    return train, lm_train, test, lm_test


def autoencoder(n_in: int = MELS * FRAMES, hidden: int = 64, code: int = 8):
    layers = tf().keras.layers
    x = inp = layers.Input((n_in,))
    for units in (hidden, hidden):
        x = layers.Dense(units, activation="relu")(x)
    x = layers.Dense(code)(x)  # linear bottleneck
    for units in (hidden, hidden):
        x = layers.Dense(units, activation="relu")(x)
    x = layers.Dense(n_in)(x)
    return tf().keras.Model(inp, x)


def anomaly_report(groups: np.ndarray, subsets: dict):
    """Metrics of the int8 device arithmetic against the MIMII labels (normal / abnormal clip).

    Scores = mean squared reconstruction error per window, averaged per clip. The window
    threshold is the 95th percentile of the validation normals, never tuned on the test set.
    """

    def report(task: Task, qm, out: np.ndarray) -> tuple[dict, dict]:
        from mobility_model_zoo.edge.int8.quant import dequantize, quantize
        from mobility_model_zoo.edge.int8.reference import run_batch

        def errors(x, o):
            rec = dequantize(o, qm.output_scale, qm.output_zp)
            return ((rec - x.reshape(len(x), -1)) ** 2).mean(1)

        xv = task.x_val
        err_val = errors(
            xv, run_batch(qm, quantize(xv.reshape(len(xv), -1), qm.input_scale, qm.input_zp))
        )
        err = errors(task.x_test, out)
        flat = task.x_test.reshape(len(err), -1)
        err_float = (
            (task.model.predict(task.x_test, verbose=0).reshape(len(err), -1) - flat) ** 2
        ).mean(1)
        uniq, inv = np.unique(groups, return_inverse=True)

        def clip(e):
            return np.bincount(inv, e) / np.bincount(inv)

        clip_y = np.zeros(len(uniq), np.int64)
        clip_y[inv] = task.y_test
        window_thr = float(np.percentile(err_val, 95))
        metrics = {
            "reference": "dataset labels (MIMII normal / abnormal clips)",
            "float_auc": roc_auc(clip(err_float), clip_y),
            "int8_auc": roc_auc(clip(err), clip_y),
            "int8_pauc": roc_auc(clip(err), clip_y, max_fpr=0.1),
            "int8_window_auc": roc_auc(err, task.y_test),
            "int8_window_detection_rate": float((err[task.y_test == 1] > window_thr).mean()),
            "int8_window_false_positive_rate": float((err[task.y_test == 0] > window_thr).mean()),
            "test_clips": int(len(uniq)),
            "test_samples": int(len(err)),
        }
        for name, mask in subsets.items():
            g = np.unique(inv[mask])
            metrics[f"int8_auc_{name}"] = roc_auc(clip(err)[g], clip_y[g])
        # the per-window threshold is used by the HIL test
        return metrics, {"threshold": window_thr}

    return report


def make_task(seed: int) -> Task:
    train, lm_train, test, lm_test = load_mimii(seed)
    stacked = np.concatenate(lm_train)
    mean, std = stacked.mean(0), stacked.std(0) + 1e-6

    def norm(w):
        z = (w.reshape(len(w), FRAMES, MELS) - mean) / std
        return z.reshape(len(w), -1).astype(np.float32)

    rng = np.random.default_rng(seed)
    # validation = whole clips, so the threshold is not tuned on frames of training clips
    order = rng.permutation(len(train))
    n_val = max(1, len(train) // 10)
    xs = {
        k: norm(np.concatenate([windows(lm_train[i], stride=4) for i in idx]))
        for k, idx in (("val", order[:n_val]), ("train", order[n_val:]))
    }
    xs["train"] = xs["train"][rng.permutation(len(xs["train"]))]
    wins = [windows(lm, stride=8) for lm in lm_test]
    x_test = norm(np.concatenate(wins))
    groups = np.concatenate([np.full(len(w), i) for i, w in enumerate(wins)])
    y_test = np.concatenate([np.full(len(w), lab) for w, (_, lab, _) in zip(wins, test, strict=True)])
    machine = np.concatenate([np.full(len(w), mid) for w, (_, _, mid) in zip(wins, test, strict=True)])
    print(
        f"mimii windows: train {len(xs['train'])}, val {len(xs['val'])}, test {len(x_test)}", flush=True
    )
    return Task(
        name=NAME,
        model=autoencoder(),
        kind="anomaly",
        x_train=xs["train"],
        y_train=np.zeros(len(xs["train"]), np.int64),
        x_val=xs["val"],
        y_val=np.zeros(len(xs["val"]), np.int64),
        x_test=x_test,
        y_test=y_test,
        datasets=DATASETS,
        labels=["normal", "anomaly"],
        description="Machine-sound anomaly detection autoencoder "
        f"({FRAMES} x {MELS} log-mel -> 64-64-8-64-64), trained on normal fan recordings of "
        "MIMII (6 dB SNR); anomaly score = reconstruction MSE averaged over a 10 s clip",
        preprocess={
            "sample_rate": SR,
            "channel": 0,
            "n_fft": FFT,
            "hop": HOP,
            "n_mels": MELS,
            "fmin": 20.0,
            "fmax": 8000.0,
            "frames": FRAMES,
            "log": "natural log of mel power + 1e-6",
            "mean": mean.tolist(),
            "std": std.tolist(),
        },
        metrics=anomaly_report(groups, {m: machine == m for m in sorted(set(machine))}),
        eval_targets=True,
    )


def main(argv=None) -> dict:
    return train_main(make_task, NAME, DATASETS, argv, __doc__)


if __name__ == "__main__":
    main()
