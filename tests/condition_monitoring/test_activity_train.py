"""pace-cnn data loading on a tiny synthetic UCI HAR tree (no TensorFlow needed)."""

import numpy as np
import pytest

from mobility_model_zoo.condition_monitoring.activity.train import LABELS, SIGNALS, load_har


def _split(base, name, n, rng):
    d = base / name / "Inertial Signals"
    d.mkdir(parents=True)
    for sig in SIGNALS:
        np.savetxt(d / f"{sig}_{name}.txt", rng.normal(size=(n, 128)))
    np.savetxt(base / name / f"y_{name}.txt", rng.integers(1, len(LABELS) + 1, n), fmt="%d")


def test_load_har_shapes_and_zero_based_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    base = tmp_path / "uci-har" / "extracted" / "UCI HAR Dataset"
    rng = np.random.default_rng(0)
    _split(base, "train", 7, rng)
    _split(base, "test", 3, rng)
    (xtr, ytr), (xte, yte) = load_har()
    assert xtr.shape == (7, 128, 9) and xte.shape == (3, 128, 9)
    assert ytr.min() >= 0 and ytr.max() < len(LABELS)


def test_load_har_without_download(tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    with pytest.raises(SystemExit, match="zoo data download uci-har"):
        load_har()
