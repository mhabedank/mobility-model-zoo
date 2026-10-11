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


def test_event_flags_spread_over_an_injection_and_flag_fuzzing():
    table = cal.calibrate([_benign(3)])
    c = _cap("fabrication", 3)
    x = cal.features(c, table)
    y = c["y"] == 1
    first_two = np.zeros(y.size, bool)
    first_two[np.flatnonzero(y)[:2]] = True  # the model flags only two injected frames
    out = cal.event_flags(c, x, table, first_two, confirm=2, margin=0.25) > 0
    assert out[y].sum() > first_two[y].sum()  # the episode of that ID is spread
    none = cal.event_flags(c, x, table, np.zeros(y.size, bool), confirm=2, margin=0.25)
    fuzz = (x[:, 7] >= 3) | (x[:, 8] >= 8)
    assert np.array_equal(none > 0, fuzz)  # without model flags only the fuzzing state remains


def test_binary_detectors_keep_their_decision():
    class Fixed(ev2.Rules):
        def score(self, caps):
            return [np.where(np.arange(c["y"].size) % 2 == 0, 1.0, 0.0).astype(np.float32) for c in caps]

    c = _cap("fabrication", 4)
    calib = ev2._calibrate(Fixed("f", "baseline", "fixed"), [c], [1, 10])
    assert calib["threshold"] == 0.5


def test_unknown_id_state_does_not_survive_a_recording_gap():
    table = cal.calibrate([_benign(5)])
    c = _cap("fuzzing", 5)
    y = c["y"] == 1
    cut = np.flatnonzero(y)[-1] + 1  # end of the fuzzing episode
    gap = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in c.items()}
    gap["ts"][cut:] += 50.0  # 50 s without frames after the episode
    x = cal.features(gap, table)
    after = np.arange(y.size) >= cut
    assert x[after & (gap["ts"] > gap["ts"][cut] + 0.01), 8].max() < 8


def test_c_counts_match_the_numpy_bucket_count():
    table = cal.calibrate([_benign(6)])
    c = _cap("fabrication", 6)
    x = cal.features(c, table)
    ts = cal.to_us(c["ts"])
    ids = c["can_id"].astype(np.int64)
    for i in table.known:
        sel = ids == i
        want = cal.bucket_counts(ts[sel], table.window[i]) - table.max_count[i]
        assert np.array_equal(x[sel, 3], want.astype(np.float32))
