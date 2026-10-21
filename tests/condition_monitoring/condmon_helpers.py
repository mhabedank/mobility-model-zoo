"""Helpers of the condition-monitoring tests: a tiny synthetic UCI HAR tree, fake runs.

The tree has the layout of the real download (`$MMZ_DATA/uci-har/extracted/.../{train,test}/`) and a
`SOURCE.json` in the real format, but random signals and labels: no dataset content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mobility_model_zoo.condition_monitoring.activity.train import LABELS, SIGNALS

N_TRAIN_SUBJECTS = 21
N_TEST_SUBJECTS = 9


@dataclass
class HarTree:
    root: Path  # $MMZ_DATA
    base: Path  # folder that holds train/ and test/
    train_subjects: list[int]
    test_subjects: list[int]
    per_subject: int


def write_split(base: Path, name: str, subjects: list[int], per_subject: int, rng) -> None:
    n = len(subjects) * per_subject
    d = base / name / "Inertial Signals"
    d.mkdir(parents=True)
    for sig in SIGNALS:
        np.savetxt(d / f"{sig}_{name}.txt", rng.normal(size=(n, 128)), fmt="%.6e")
    labels = (np.arange(n) % len(LABELS)) + 1
    rng.shuffle(labels)
    np.savetxt(base / name / f"y_{name}.txt", labels, fmt="%d")
    np.savetxt(base / name / f"subject_{name}.txt", np.repeat(subjects, per_subject), fmt="%d")


def write_har(root: Path, per_subject: int = 3, seed: int = 0) -> HarTree:
    rng = np.random.default_rng(seed)
    ids = [int(i) for i in rng.permutation(np.arange(1, N_TRAIN_SUBJECTS + N_TEST_SUBJECTS + 1))]
    train, test = sorted(ids[:N_TRAIN_SUBJECTS]), sorted(ids[N_TRAIN_SUBJECTS:])
    base = root / "uci-har" / "extracted" / "UCI HAR Dataset" / "UCI HAR Dataset"
    write_split(base, "train", train, per_subject, rng)
    write_split(base, "test", test, per_subject, rng)
    source = {
        "id": "uci-har",
        "license": "CC-BY-4.0",
        "retrieved_at": "2026-01-01T00:00:00Z",
        "files": [{"name": "uci-har.zip", "sha256": "ab" * 32, "bytes": 1}],
    }
    (root / "uci-har" / "SOURCE.json").write_text(json.dumps(source))
    return HarTree(root, base, train, test, per_subject)


# ---- pre-registration and fake runs (feature 021) -------------------------------------------------

# The criteria record of contracts/records.md, as committed in configs/condition-monitoring/activity/.
CRITERIA_YAML = """version: 1
date: 2026-10-20
rationale: Owner decisions of 2026-10-18 (spec 021, Clarifications).
benchmark: uci-har-v1
recipe: configs/condition-monitoring/activity/pace-cnn.yaml
seeds: {candidate: 0, spread: [1, 2, 3, 4]}
selection: none (model after the last epoch of the candidate seed)
success:
  - {id: S1, metric: int8_macro_f1, op: ">=", value: 0.90}
  - {id: S2, metric: int8_accuracy, op: ">=", value: 0.90}
  - {id: S3, metric: int8_f1_min_class, op: ">=", value: 0.80}
  - {id: S4, budgets_on_reference_board: true}
  - {id: S5, fact: transfer_tested, value: true}
kill:
  - {id: K1, metric: int8_macro_f1, op: "<", value: 0.80}
  - {id: K2, difference: float_macro_f1 - int8_macro_f1, op: ">", value: 0.03}
  - {id: K3, budgets_exceeded_on_reference_board: true}
budgets:
  flash_kb: 128
  ram_kb: 32
  latency_us: 100000
  reference_hardware: ESP32 (esp32-1, LilyGO LoRa32)
"""


def tiny_qmodel(seed: int):
    """A random int8 model with pace-cnn's input (1 x 128 x 9) and six outputs, built without
    TensorFlow."""
    from mobility_model_zoo.edge.int8.floatnet import FLayer, FloatNet

    rng = np.random.default_rng(seed)
    net = FloatNet(
        (1, 128, 9),
        [
            FLayer("conv2d", 4, kernel=(1, 5), padding="same", act="relu"),
            FLayer("avgpool2d", kernel=(1, 128), stride=(1, 128)),
            FLayer("reshape"),
            FLayer("dense", len(LABELS)),
        ],
    ).build(rng)
    return net.quantize("pace-cnn", rng.normal(size=(64, 1, 128, 9)).astype(np.float32))


def write_runs(manifest_path: Path, criteria_path: Path, mismatches: int = 0, **override) -> None:
    """Five fake run folders in $MMZ_DATA/derived/pace-cnn/seed-<n>/, as `train` writes them."""
    import hashlib

    from mobility_model_zoo.edge.paths import derived_dir

    def sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    for seed in range(5):
        out = derived_dir("pace-cnn") / f"seed-{seed}"
        out.mkdir(parents=True, exist_ok=True)
        qm = tiny_qmodel(seed)
        qm.save(out / "pace-cnn.npz")
        report = {
            "name": "pace-cnn",
            "seed": seed,
            "benchmark": "uci-har-v1",
            "manifest_sha256": sha(manifest_path),
            "criteria_version": 1,
            "criteria_sha256": sha(criteria_path),
            "criteria_commit": "c0ffee" * 6 + "c0ff",
            "npz_sha256": sha(out / "pace-cnn.npz"),
            "weights_sha256": f"{seed:064d}",
            "trained_at": f"2026-10-2{seed}T10:00:00Z",
            "float_accuracy": 0.5,
            "float_macro_f1": 0.5,
            "tflite_interpreter_mismatches": mismatches,
            "validation": {
                "float_accuracy": 0.5,
                "float_macro_f1": 0.5,
                "int8_accuracy": 0.5,
                "int8_macro_f1": 0.5,
            },
            **override,
        }
        (out / "pace-cnn.report.json").write_text(json.dumps(report))
