"""Subject-wise validation and normalisation of uci-har-v1 (feature 021, T009)."""

import numpy as np
import pytest

from mobility_model_zoo.condition_monitoring import benchmark as bm
from mobility_model_zoo.condition_monitoring.activity import train as pace


def test_validation_is_drawn_by_whole_subjects():
    subjects = list(range(1, 22))
    train, val = bm.split_subjects(subjects, 2026, 7)
    assert len(val) == 3 and len(train) == 18
    assert not set(train) & set(val)
    assert sorted(train + val) == subjects
    assert bm.split_subjects(subjects, 2026, 7) == (train, val)  # seeded, reproducible
    assert bm.split_subjects(subjects, 2027, 7) != (train, val)


def test_parts_keep_subjects_apart(har_tree):
    manifest = pace.build_manifest()
    parts = pace.frozen_splits(manifest)
    seen = [set(parts[s].subjects.tolist()) for s in ("train", "validation", "test")]
    assert not (seen[0] & seen[1]) and not (seen[0] & seen[2]) and not (seen[1] & seen[2])
    assert [len(s) for s in seen] == [18, 3, 9]


def test_normalisation_uses_training_subjects_only(har_tree):
    manifest = pace.build_manifest()
    parts = pace.frozen_splits(manifest)
    flat = parts["train"].x.reshape(-1, 9)
    assert np.allclose(manifest["normalisation"]["mean"], flat.mean(0), atol=1e-6)
    assert np.allclose(manifest["normalisation"]["std"], flat.std(0) + 1e-6, atol=1e-6)
    with_val = np.concatenate([parts["train"].x, parts["validation"].x]).reshape(-1, 9)
    assert not np.allclose(manifest["normalisation"]["mean"], with_val.mean(0), atol=1e-9)


def test_changed_split_data_is_refused(har_tree):
    manifest = pace.build_manifest()
    manifest["splits"]["train"]["data_sha256"] = "0" * 64
    with pytest.raises(bm.SplitChanged, match="train"):
        pace.frozen_splits(manifest)
