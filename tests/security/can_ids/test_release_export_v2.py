"""picket-forest 0.2.0 C chain against the Python reference (feature 010)."""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from mobility_model_zoo.security.can_ids import calibrated as cal
from mobility_model_zoo.security.can_ids import release_export_v2 as rx
from mobility_model_zoo.security.can_ids import scorer
from mobility_model_zoo.security.can_ids.detectors import make_capture
from mobility_model_zoo.security.can_ids.synth import generate

# find_spec, not importorskip: importing emlearn changes numpy's error state for the whole session
pytestmark = pytest.mark.skipif(importlib.util.find_spec("emlearn") is None, reason="emlearn missing")


def _cap(attack, seed=42, n=6000):
    return make_capture(generate(attack, n_frames=n, seed=seed), f"synth/{attack}", attack)


@pytest.fixture(scope="module")
def model():
    table = rx.example_table()
    caps = [_cap(a, seed=42) for a in ("fabrication", "dos", "fuzzing", "scan")]
    x = np.concatenate([cal.features(c, table) for c in caps])
    y = np.concatenate([c["y"] for c in caps])
    clf = RandomForestClassifier(n_estimators=5, max_depth=6, min_samples_leaf=5, random_state=0)
    clf.fit(x, y)
    return clf, table


def test_c_chain_is_bit_exact_with_python(model, tmp_path):
    clf, table = model
    caps = [_cap(a, seed=42, n=4000) for a in ("fabrication", "dos", "fuzzing")]
    par = rx.parity(clf, 0.5, caps, table, tmp_path / "parity")
    assert par["frames"] > 0
    assert par["score_mismatches"] == 0 and par["alarm_mismatches"] == 0


def test_examples_check_against_the_staged_chain(model, tmp_path):
    clf, table = model
    exp = tmp_path / "export"
    (exp / "c").mkdir(parents=True)
    rx.model_header(clf, exp / "picket_forest_model.h")
    rx.config_header(exp / "picket_forest_config.h", 0.5, rx.DEFAULT_ALARM, cal.CONFIRM, cal.MARGIN)
    rx.table_header(table, exp / "picket_forest_table.h", "test")
    srcs, _, _, _ = scorer.layout(scorer.V2)
    for name, path in srcs.items():
        (exp / "c" / name).write_bytes(path.read_bytes())
    paths = rx.write_examples(exp, tmp_path / "examples")
    exe = rx.build(exp, tmp_path / "b", sources_dir=exp / "c")
    import json

    for p in paths:
        ex = json.loads(p.read_text())
        assert scorer.check_example(exe, ex) is None
        assert ex["expected_alarms"], p.name  # every example attack raises an alarm
