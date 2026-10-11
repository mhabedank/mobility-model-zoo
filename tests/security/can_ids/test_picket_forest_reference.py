"""The user-facing Python reference of picket-forest (feature 013).

Runs without a C compiler: the example captures carry the scores and alarms the release's C chain
produced, so reproducing them bit for bit proves the numpy port against the device code. The
comparison with the ctypes build of msml_cal lives in test_release_export_v2.py (needs a compiler).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest
from picket_fixtures import (
    REPO_ROOT,
    example_paths,
    header_bus_rate,
    header_table,
    load_release_model,
)

from mobility_model_zoo.security.can_ids import picket_forest as pf

MODULE = REPO_ROOT / "src" / "mobility_model_zoo" / "security" / "can_ids" / "picket_forest.py"
ALLOWED_THIRD_PARTY = {"numpy", "joblib", "sklearn"}
FORBIDDEN = ("mobility_model_zoo", "ctypes", "subprocess", "pandas")
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def table(tmp_path_factory) -> pf.Table:
    """The calibration table published with the release, through its JSON form."""
    from mobility_model_zoo.security.can_ids import release_export_v2 as rx

    path = tmp_path_factory.mktemp("table") / "calibration_table.json"
    pf.save_table(rx.example_table(), path, note="synthetic example vehicle")
    return pf.load_table(path)


def test_module_imports_are_user_safe():
    """Users install the package, not the repository: no compiled helpers, no repo paths, no pandas."""
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module)
    for name in imported:
        assert not name.startswith(FORBIDDEN), f"picket_forest imports {name}"
    import sys

    third_party = {n.split(".")[0] for n in imported} - set(sys.stdlib_module_names) - {"__future__"}
    assert third_party <= ALLOWED_THIRD_PARTY, third_party


@pytest.mark.parametrize("path", example_paths(), ids=lambda p: p.stem)
def test_examples_reproduce_expected_scores_and_alarms(path, table):
    example = json.loads(path.read_text(encoding="utf-8"))
    scores, alarms = pf.score(pf.load_capture(path), table, load_release_model())
    got = [f"{int(b):08x}" for b in scores.astype(np.float32).view(np.uint32)]
    want = example["expected_scores"]
    assert len(got) == len(want)
    first = next((i for i, (g, w) in enumerate(zip(got, want, strict=True)) if g != w), None)
    assert first is None, f"score of frame {first}: {got[first]}, expected {want[first]}"
    assert np.flatnonzero(alarms).tolist() == example["expected_alarms"]


def test_summary_is_deterministic(table):
    path = example_paths()[0]
    cap = pf.load_capture(path)
    scores, alarms = pf.score(cap, table, load_release_model())
    text = pf.summary(cap, scores, alarms)
    assert text == pf.summary(cap, scores, alarms)
    assert text.startswith("3000 frames, ")
    assert "1 alarm at frame 1155" in text


def test_table_roundtrip_and_header_equivalence(tmp_path):
    from mobility_model_zoo.security.can_ids import release_export_v2 as rx

    t = rx.example_table()
    pf.save_table(t, tmp_path / "t.json", note="test")
    back = pf.load_table(tmp_path / "t.json")
    for field in ("period", "window", "max_count", "dlc"):
        assert getattr(back, field) == getattr(t, field), field
    assert back.bus_rate == float(np.float32(t.bus_rate))
    assert back.seconds == pytest.approx(t.seconds)
    rx.table_header(t, tmp_path / "t.h", "test")
    assert header_table(tmp_path / "t.h") == [tuple(int(v) for v in r) for r in back.entries()]
    assert header_bus_rate(tmp_path / "t.h") == pf.device_bus_rate(back.bus_rate)


def test_table_from_header_inverts_the_header_writer(tmp_path):
    from mobility_model_zoo.security.can_ids import release_export_v2 as rx

    t = rx.example_table()
    rx.table_header(t, tmp_path / "t.h", "test")
    back = pf.table_from_header((tmp_path / "t.h").read_text())
    for field in ("period", "window", "max_count", "dlc"):
        assert getattr(back, field) == getattr(t, field), field
    assert back.bus_rate == float(np.float32(t.bus_rate))
    assert pf.device_bus_rate(back.bus_rate) == header_bus_rate(tmp_path / "t.h")
    with pytest.raises(ValueError):
        pf.table_from_header("/* not a table */")


def test_load_table_refuses_other_formats(tmp_path):
    (tmp_path / "t.json").write_text(json.dumps({"format": "something-else", "ids": []}))
    with pytest.raises(ValueError, match="picket-forest-table-v1"):
        pf.load_table(tmp_path / "t.json")


def test_load_model_refuses_other_formats(tmp_path):
    import joblib

    joblib.dump({"format": "picket-forest-v1", "model": None}, tmp_path / "m.joblib")
    with pytest.raises(ValueError, match="picket-forest-v2"):
        pf.load_model(tmp_path / "m.joblib")


def test_read_candump_matches_frames_reader():
    from mobility_model_zoo.security.can_ids.frames import read_candump

    path = FIXTURES / "benign.log"
    cap = pf.read_candump(path)
    df = read_candump(path)
    assert np.array_equal(np.rint(cap["ts"] * 1e6).astype(np.int64), df["ts_us"].to_numpy())
    assert np.array_equal(cap["can_id"], df["can_id"].to_numpy())
    assert np.array_equal(cap["dlc"], df["dlc"].to_numpy())
    assert np.array_equal(cap["data"], df[[f"b{i}" for i in range(8)]].to_numpy())
    assert not cap["y"].any()
    t = pf.calibrate([cap])
    assert t.known == set(np.unique(cap["can_id"]).tolist())


def test_features_refuse_frames_out_of_order(table):
    cap = pf.load_capture(example_paths()[0])
    cap["ts"] = cap["ts"][::-1].copy()
    with pytest.raises(ValueError, match="bus order"):
        pf.features(cap, table)


# Alarm stage, cases written by hand from msml_alarm.c (k frames within the window, then hold-off).
ALARM_CASES = [
    # (ts_us, flagged, k, window_ms, holdoff_ms, frames that raise an alarm)
    (
        [0, 10_000, 50_000, 100_000, 150_000, 1_200_000, 1_250_000, 1_300_000],
        [1, 0, 1, 1, 1, 1, 1, 1],
        3,
        200,
        1000,
        [3, 7],
    ),
    ([0, 150_000, 300_000], [1, 1, 1], 3, 200, 1000, []),  # spread wider than the window
    ([0, 100_000, 200_000], [1, 1, 1], 3, 200, 1000, [2]),  # exactly the window still counts
    ([0, 500_000, 1_100_000], [1, 1, 1], 0, 200, 1000, [0, 2]),  # k clamped to 1, hold-off applies
]


@pytest.mark.parametrize("ts,flagged,k,window,holdoff,expected", ALARM_CASES)
def test_alarms_matches_c_semantics(ts, flagged, k, window, holdoff, expected):
    got = pf.alarms(np.array(ts, np.int64), np.array(flagged, np.uint8), k, window, holdoff)
    assert got.dtype == np.uint8
    assert np.flatnonzero(got).tolist() == expected
