"""picket-forest port checks that need no dataset (T033)."""

import importlib.util
import os
import shutil

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from mobility_model_zoo.security.can_ids import forest  # noqa: E402
from mobility_model_zoo.security.can_ids.forest_features import extract  # noqa: E402

ALARM = {"k": 3, "window_ms": 200, "holdoff_ms": 1000}


def literal_value(lit: str) -> np.float32:
    assert lit.endswith("f")
    return np.float32(float(lit[:-1]))


@pytest.mark.parametrize("thr", [0.5, 1.5, 2.0000001, 10.25, 1e-3, 123456.789, 0.0])
def test_float32_split_literal_matches_sklearn_rule(thr):
    t = literal_value(forest.float32_split_literal(thr))
    a = np.float32(thr)
    candidates = [a, np.nextafter(a, np.float32(-np.inf)), np.nextafter(a, np.float32(np.inf)), t]
    candidates += [np.nextafter(t, np.float32(-np.inf)), np.nextafter(t, np.float32(np.inf))]
    tiny = np.finfo(np.float32).tiny
    for x in candidates:
        if 0 < abs(x) < tiny:  # subnormal inputs are excluded by design (features never are)
            continue
        assert (x < t) == (float(x) <= thr), (thr, x, t)


def test_float32_split_literal_avoids_subnormals():
    t = literal_value(forest.float32_split_literal(1e-45))
    assert t == np.finfo(np.float32).tiny


def test_config_header_uses_picket_forest_names(tmp_path):
    idx = forest.cols(forest.FEATURE_SETS[forest.EXPORT_FEATURES])
    path = tmp_path / forest.CONFIG_HEADER
    forest.write_config_header(path, idx, 0.5666666, ALARM)
    text = path.read_text()
    assert forest.CONFIG_HEADER == "picket_forest_config.h"
    assert "mobility_model_zoo.security.can_ids.forest export" in text
    assert f"#define PICKET_FOREST_N_INPUTS {len(idx)}" in text
    assert "#define PICKET_FOREST_ALARM_K 3" in text
    assert "#define PICKET_FOREST_ALARM_WINDOW_US 200000" in text
    assert "picket_forest_input_index[PICKET_FOREST_N_INPUTS]" in text
    assert "#ifndef PICKET_FOREST_CONFIG_H" in text
    assert "can_ids_tiny" not in text.lower() and "CAN_IDS_TINY" not in text


def test_committed_config_header_matches_generator(tmp_path):
    """The committed header is what write_config_header produces for its own values."""
    committed = (forest.C_DIR / "generated" / forest.CONFIG_HEADER).read_text()
    idx = forest.cols(forest.FEATURE_SETS[forest.EXPORT_FEATURES])
    path = tmp_path / forest.CONFIG_HEADER
    forest.write_config_header(path, idx, 0.566666663, ALARM)
    assert path.read_text() == committed


def test_c_sources_exist():
    assert forest.MODEL_NAME == "picket_forest_model"
    for p in (
        forest.C_DIR / "picket_forest.c",
        forest.C_DIR / "picket_forest.h",
        forest.C_DIR / "host_score.c",
        forest.FEATURES_DIR / "msml_can_features.c",
        forest.FEATURES_DIR / "msml_alarm.c",
        forest.FEATURES_DIR / "include" / "msml_can_features.h",
    ):
        assert p.is_file(), p


def test_cli_defaults_and_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    seen = {}
    monkeypatch.setattr(forest, "cmd_convert", lambda args: seen.update(vars(args)))
    forest.main(["convert"])
    assert seen["data"] == tmp_path / "can-train-and-test" / "extracted"
    assert seen["out"] == tmp_path / "derived" / "picket-forest"
    forest.main(["convert", "--data", str(tmp_path / "d"), "--out", str(tmp_path / "o")])
    assert seen["data"] == tmp_path / "d"
    assert seen["out"] == tmp_path / "o"


def synthetic_frames(rng: np.random.Generator, n: int = 3000) -> pd.DataFrame:
    """Periodic traffic of a few IDs plus injected frames (label 1), as from parse_csv."""
    ids = np.array([0x100, 0x1A0, 0x2C0, 0x3E8], dtype=np.uint16)
    ts = np.cumsum(rng.uniform(0.0004, 0.0016, n))
    can_id = ids[np.arange(n) % ids.size]
    label = np.zeros(n, dtype=np.uint8)
    payload = np.tile(np.arange(8, dtype=np.uint8), (n, 1))
    payload[:, 0] = (np.arange(n) // ids.size).astype(np.uint8)
    attack = rng.random(n) < 0.15
    label[attack] = 1
    can_id[attack] = 0x000
    payload[attack] = rng.integers(0, 256, (int(attack.sum()), 8), dtype=np.uint8)
    df = pd.DataFrame({"ts": 1.7e9 + ts, "can_id": can_id, "dlc": np.full(n, 8, dtype=np.uint8)})
    for i in range(8):
        df[f"b{i}"] = payload[:, i]
    df["label"] = label
    return df


def test_end_to_end_c_matches_python(tmp_path):
    if importlib.util.find_spec("emlearn") is None:
        pytest.skip("emlearn not installed (edge-train extra)")
    if shutil.which(os.environ.get("CC", "cc")) is None:
        pytest.skip("no C compiler")
    from sklearn.ensemble import RandomForestClassifier

    rng = np.random.default_rng(0)
    idx = forest.cols(forest.FEATURE_SETS[forest.EXPORT_FEATURES])
    train = synthetic_frames(rng)
    clf = RandomForestClassifier(n_estimators=3, max_depth=3, random_state=0)
    clf.fit(extract(train)[:, idx], train["label"].to_numpy())

    forest.to_c(clf, idx, 0.5, ALARM, tmp_path)
    assert (tmp_path / f"{forest.MODEL_NAME}.h").is_file()
    exe = forest.build_host_scorer(tmp_path)

    test = synthetic_frames(np.random.default_rng(1), n=2000)
    report = forest.parity_report(clf, idx, exe, test, tmp_path)
    assert report["frames"] == len(test)
    assert report["identical"] == 1.0, report
    assert not list(tmp_path.glob("parity_*.bin"))


@pytest.mark.parametrize("cmd", ["evaluate", "export"])
def test_training_commands_check_the_declaration(cmd, monkeypatch):
    from mobility_model_zoo.datasets import UsageRefused

    def refuse(ds, model=None):
        raise UsageRefused(ds)

    monkeypatch.setattr(forest, "require_training_allowed", refuse)
    with pytest.raises(UsageRefused):
        forest.main([cmd])
