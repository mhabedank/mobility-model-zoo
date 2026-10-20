"""pace-cnn data loading on a tiny synthetic UCI HAR tree (no TensorFlow needed)."""

import numpy as np
import pytest

from mobility_model_zoo.condition_monitoring.activity.train import LABELS, load_har


def test_load_har_shapes_and_zero_based_labels(har_tree):
    train, test = load_har()
    n_train = len(har_tree.train_subjects) * har_tree.per_subject
    n_test = len(har_tree.test_subjects) * har_tree.per_subject
    assert train.x.shape == (n_train, 128, 9) and test.x.shape == (n_test, 128, 9)
    assert train.y.min() >= 0 and train.y.max() < len(LABELS)


def test_load_har_returns_one_subject_per_window(har_tree):
    train, test = load_har()
    assert len(train.subjects) == len(train.y) and len(test.subjects) == len(test.y)
    assert sorted(set(train.subjects.tolist())) == har_tree.train_subjects
    assert sorted(set(test.subjects.tolist())) == har_tree.test_subjects
    assert not set(train.subjects.tolist()) & set(test.subjects.tolist())
    assert train.subjects.dtype == np.int64


def test_load_har_without_download(tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    with pytest.raises(SystemExit, match="zoo data download uci-har"):
        load_har()
