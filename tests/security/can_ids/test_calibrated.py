"""Per-vehicle calibration and the can-ids-v2 plan (feature 010)."""

from __future__ import annotations

import numpy as np
import pytest

from mobility_model_zoo.security.can_ids import calibrated as cal
from mobility_model_zoo.security.can_ids import evaluate_v2 as ev2
from mobility_model_zoo.security.can_ids.detectors import make_capture
from mobility_model_zoo.security.can_ids.synth import generate


def _cap(attack, seed, n=4000):
    df = generate(attack, n_frames=n, seed=seed)
    return make_capture(df, f"synth/{attack}/{seed}", attack)


def _benign(seed):
    c = _cap("fabrication", seed)
    keep = c["y"] == 0
    return {
        k: (v[keep] if isinstance(v, np.ndarray) and v.shape[:1] == keep.shape else v)
        for k, v in c.items()
    }


def test_calibration_refuses_attack_frames():
    with pytest.raises(ValueError, match="attack frames"):
        cal.calibrate([_cap("fabrication", 1)])


def test_features_flag_rate_increase_and_unknown_ids():
    table = cal.calibrate([_benign(1)])
    assert table.known and table.seconds > 0
    for attack in ("fabrication", "dos", "fuzzing"):
        c = _cap(attack, 1)
        x = cal.features(c, table)
        assert x.shape == (c["y"].size, len(cal.FEATURE_NAMES))
        flagged = cal.rules(x) >= 0.5
        assert flagged[c["y"] == 1].mean() > flagged[c["y"] == 0].mean()


def test_features_do_not_use_identifiers_or_time():
    table = cal.calibrate([_benign(2)])
    c = _cap("fabrication", 2)
    shifted = {**c, "ts": c["ts"] + 1e6}
    a, b = cal.features(c, table), cal.features(shifted, table)
    # equal up to float rounding of the shifted timestamps: a window edge may move by one frame
    other = [i for i, n in enumerate(cal.FEATURE_NAMES) if n not in ("log_count_ratio", "count_excess")]
    assert np.allclose(a[:, other], b[:, other], atol=1e-3)
    assert np.abs(a[:, 3] - b[:, 3]).max() <= 1


def _entry(cid, s, split, role, vehicle, family, sha, attack=0):
    return {
        "id": cid,
        "dataset": "can-train-and-test",
        "set": s,
        "split": split,
        "role": role,
        "vehicle": vehicle,
        "attack_family": family,
        "sha256": sha,
        "attack_frames": attack,
    }


def test_plan_uses_separate_benign_captures_and_refuses_overlap():
    caps = [
        _entry("s1/af", "set_01", "train_01", "train", "A", "attack-free", "h1"),
        _entry("s1/dos", "set_01", "train_01", "train", "A", "DoS", "h2", 10),
        _entry("s1/t2", "set_01", "test_02_unknown_vehicle_known_attack", "test", "B", "DoS", "h3", 10),
        _entry("s2/af", "set_02", "train_01", "train", "B", "attack-free", "h4"),
        _entry("s2/af2", "set_02", "train_01", "validation", "B", "attack-free", "h5"),
    ]
    v1 = {"benchmark": "can-ids-v1", "captures": caps, "protocol": {}}
    plan = ev2.calibration_plan(v1)
    assert plan["set_01"] == {"A": ["s1/af"], "B": ["s2/af", "s2/af2"]}
    m = {**v1, "calibration": {"set_01": {"A": ["s1/af"], "B": ["s1/t2"]}}}
    with pytest.raises(ev2.CalibrationOverlap):
        ev2.check_disjoint(m)
