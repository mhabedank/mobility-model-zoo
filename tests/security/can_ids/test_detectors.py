"""Detectors of the can-ids-v1 harness on synthetic traffic (feature 007, T011)."""

import numpy as np
import pytest

from mobility_model_zoo.security.can_ids.detectors import make_capture, registry
from mobility_model_zoo.security.can_ids.synth import generate


def caps(attack, seeds, n=3000):
    return [make_capture(generate(attack, n_frames=n, seed=s), f"{attack}-{s}", attack) for s in seeds]


@pytest.fixture(scope="module")
def data():
    train = caps("dos", [1, 2]) + caps("fuzzing", [3, 4])
    val = caps("dos", [5]) + caps("fuzzing", [6])
    test = caps("dos", [7]) + caps("fuzzing", [8])
    return train, val, test


def _f1(y, s, thr):
    p = s >= thr
    tp = ((p == 1) & (y == 1)).sum()
    return 2 * tp / max(p.sum() + y.sum(), 1)


@pytest.mark.parametrize("name", sorted(registry()))
def test_interface(name, data):
    train, val, test = data
    det = registry()[name]
    det.fit(train, val)
    scores = det.score(test)
    assert [len(s) for s in scores] == [len(c["y"]) for c in test]
    assert all(np.isfinite(s).all() for s in scores)
    assert det.size_bytes() > 0


def test_shuffled_control_collapses_and_forest_does_not(data):
    train, val, test = data
    y = np.concatenate([c["y"] for c in test])
    good = registry()["picket-forest"]
    good.fit(train, val)
    bad = registry()["ctrl-shuffled"]
    bad.fit(train, val)
    from sklearn.metrics import roc_auc_score

    assert _f1(y, np.concatenate(good.score(test)), 0.5) > 0.8
    # no signal left: ranking at chance (F1 alone misleads when attacks are frequent)
    assert roc_auc_score(y, np.concatenate(bad.score(test))) < 0.6


def test_id_lookup_scores_an_attack_only_id_as_attack(data):
    train, val, test = data
    det = registry()["ctrl-id-lookup"]
    det.fit(train, val)
    dos = test[0]
    s = det.score([dos])[0]
    assert np.all(s[dos["can_id"] == 0] == 1.0)  # ID 0x000 only ever appears in attacks


def test_timing_baselines_flag_a_doubled_rate():
    benign = caps("dos", [12])  # same seed -> same benign identifiers as the fabrication capture
    for c in benign:
        c["y"] = np.zeros_like(c["y"])
    det_m, det_b = registry()["bl-mean-interval"], registry()["bl-binning"]
    det_m.fit(benign, [])
    det_b.fit(benign, [])
    c = make_capture(generate("fabrication", n_frames=3000, seed=12), "fab", "fabrication")
    for det in (det_m, det_b):
        s = det.score([c])[0]
        assert s[c["y"] == 1].mean() > s[c["y"] == 0].mean()


def test_can_logic_rules():
    train = caps("dos", [21])
    det = registry()["bl-can-logic"]
    det.fit(train, [])
    scan = make_capture(generate("scan", n_frames=3000, seed=22), "scan", "scan")
    s = det.score([scan])[0]
    assert s[scan["y"] == 1].mean() > 0.9  # unknown IDs
