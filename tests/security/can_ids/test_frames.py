"""Common CAN frame format (feature 005, T034) on tiny synthetic files."""

import json

import numpy as np
import pandas as pd
import pytest

from mobility_model_zoo.security.can_ids import frames


def _candump(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def test_read_candump_columns_and_dtypes(tmp_path):
    p = _candump(tmp_path / "a.log", ["(1.000001) can0 123#DEADBEEF", "(1.5) can0 7FF#"])
    df = frames.read_candump(p)
    assert list(df.columns) == frames.COLUMNS
    frames.validate(df)
    assert df["ts_us"].tolist() == [1_000_001, 1_500_000]
    assert df["can_id"].tolist() == [0x123, 0x7FF]
    assert df["dlc"].tolist() == [4, 0]
    assert df.loc[0, ["b0", "b1", "b2", "b3", "b4"]].tolist() == [0xDE, 0xAD, 0xBE, 0xEF, 0]
    assert df["capture"].iat[0] == "a.log" and df["label"].sum() == 0


def test_from_road_labels_attacks(tmp_path):
    root = tmp_path / "road" / "extracted" / "road"
    _candump(root / "ambient" / "drive.log", ["(0.0) can0 100#00", "(0.1) can0 100#01"])
    _candump(
        root / "attacks" / "fuzzing_attack_1.log",
        ["(10.0) can0 100#00", "(10.6) can0 2AA#FF", "(12.0) can0 100#00"],
    )
    meta = {"fuzzing_attack_1": {"injection_interval": [0.5, 1.0], "injection_id": "XXX"}}
    (root / "attacks" / "capture_metadata.json").write_text(json.dumps(meta))
    caps = list(frames.from_road(tmp_path / "road"))
    assert [c["capture"].iat[0] for c in caps] == ["ambient/drive.log", "attacks/fuzzing_attack_1.log"]
    assert caps[0]["label"].sum() == 0
    assert caps[1]["label"].tolist() == [0, 1, 0]


def test_from_road_without_download(tmp_path):
    with pytest.raises(FileNotFoundError, match="zoo data download road"):
        list(frames.from_road(tmp_path))


def test_from_can_train_and_test_csv(tmp_path):
    d = tmp_path / "set_01" / "test_02_unknown_vehicle_known_attack"
    d.mkdir(parents=True)
    (d / "DoS-1.csv").write_text(
        "timestamp,arbitration_id,data_field,attack\n1.0,0C8,0102030405060708,0\n1.25,000,00,1\n"
    )
    (df,) = list(frames.from_can_train_and_test(tmp_path))
    frames.validate(df)
    assert df["capture"].iat[0] == "set_01/test_02_unknown_vehicle_known_attack/DoS-1"
    assert df["vehicle"].iat[0] == "chevrolet_silverado"
    assert df["ts_us"].tolist() == [1_000_000, 1_250_000]
    assert df["label"].tolist() == [0, 1]
    assert df.loc[0, frames.PAYLOAD].tolist() == [1, 2, 3, 4, 5, 6, 7, 8]


def test_validate_rejects_other_formats():
    df = pd.DataFrame({"ts": [0.0], "can_id": [1]})
    with pytest.raises(ValueError, match="columns"):
        frames.validate(df)
    good = frames._frame(
        np.array([0]), np.array([1]), np.array([0]), np.zeros((1, 8), np.uint8), np.array([2]), "x"
    )
    with pytest.raises(ValueError, match="label"):
        frames.validate(good)


def test_write_parquet_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    p = _candump(tmp_path / "a.log", ["(1.0) can0 123#01", "(2.0) can0 124#02"])
    df = frames.read_candump(p)
    out = frames.write_parquet(df, tmp_path / "out" / "frames.parquet")
    back = pd.read_parquet(out).astype({"capture": object, "vehicle": object})  # pandas 3: str
    pd.testing.assert_frame_equal(back, df)
