"""Freezing benchmark can-ids-v1 (feature 007, T007, FR-001..FR-004, SC-001)."""

from __future__ import annotations

import json
import zlib
from pathlib import Path

import pytest
import yaml

from mobility_model_zoo.security.can_ids import benchmark as bm

VEHICLE_SPLITS = (
    "train_01",
    "test_01_known_vehicle_known_attack",
    "test_02_unknown_vehicle_known_attack",
    "test_03_known_vehicle_unknown_attack",
    "test_04_unknown_vehicle_unknown_attack",
)


def _csv(path: Path, start: float, attack_rows=(), n=200, can_id="0C8", seed=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["timestamp,arbitration_id,data_field,attack"]
    for i in range(n):
        attack = 1 if i in attack_rows else 0
        lines.append(f"{start + i * 0.01:.6f},{can_id},{(i + seed) % 256:02X}00000000000000,{attack}")
    path.write_text("\n".join(lines) + "\n")


def _ctt(root: Path, sets=("set_01", "set_02")):
    """Two tiny can-train-and-test sets; every capture differs (seed) unless a test copies one."""
    seed = 0
    for s in sets:
        for split in VEHICLE_SPLITS:
            for cap in ("DoS-1", "DoS-2", "fuzzing-1"):
                seed += 1
                _csv(root / s / split / f"{cap}.csv", 1000.0, attack_rows=range(50, 60), seed=seed)


def _road(root: Path):
    base = root / "extracted" / "road"
    (base / "ambient").mkdir(parents=True)
    (base / "attacks").mkdir()
    meta = {}
    for i in range(8):
        lines = [f"({i * 100 + k * 0.01:.6f}) can0 100#{(k + i) % 256:02X}" for k in range(100)]
        (base / "ambient" / f"ambient_drive_{i}.log").write_text("\n".join(lines) + "\n")
    for j, name in enumerate(
        (
            "fuzzing_attack_1",
            "fuzzing_attack_2",
            "correlated_signal_attack_2",
            "correlated_signal_attack_2_masquerade",
            "accelerator_attack_drive_2",
        )
    ):
        lines = [f"({k * 0.01:.6f}) can0 2AA#{(k + 7 * j) % 256:02X}" for k in range(100)]
        (base / "attacks" / f"{name}.log").write_text("\n".join(lines) + "\n")
        meta[name] = {"injection_interval": [0.2, 0.4], "injection_id": "XXX"}
    (base / "attacks" / "capture_metadata.json").write_text(json.dumps(meta))


@pytest.fixture
def data(tmp_path):
    ctt = tmp_path / "can-train-and-test" / "extracted"
    _ctt(ctt)
    _road(tmp_path / "road")
    return tmp_path


def _freeze(data, out, resolutions=None):
    return bm.freeze(
        {"can-train-and-test": data / "can-train-and-test" / "extracted", "road": data / "road"},
        out,
        resolutions,
    )


def test_manifest_fields_and_no_frame_data(data, tmp_path):
    out = tmp_path / "bench"
    _freeze(data, out)
    m = json.loads((out / "manifest.json").read_text())
    assert m["benchmark"] == "can-ids-v1"
    assert m["protocol"]["episode_gap_s"] == 1.0 and m["protocol"]["budgets_per_hour"] == [1, 10]
    ids = [c["id"] for c in m["captures"]]
    assert len(ids) == len(set(ids))
    for c in m["captures"]:
        assert set(c) >= {
            "id",
            "dataset",
            "set",
            "split",
            "vehicle",
            "attack_family",
            "role",
            "frames",
            "attack_frames",
            "episodes",
            "duration_s",
            "sha256",
        }
    text = (out / "manifest.json").read_text()
    assert "data_field" not in text and "0C8" not in text  # no frames, no payloads


def test_second_freeze_is_identical_and_a_change_is_refused(data, tmp_path):
    out = tmp_path / "bench"
    _freeze(data, out)
    first = (out / "manifest.json").read_bytes()
    _freeze(data, out)
    assert (out / "manifest.json").read_bytes() == first
    _csv(data / "can-train-and-test/extracted/set_01/train_01/DoS-9.csv", 5.0, seed=99)
    with pytest.raises(bm.FrozenChanged):
        _freeze(data, out)


def test_duplicate_with_conflicting_labels_stops_until_resolved(data, tmp_path):
    root = data / "can-train-and-test" / "extracted"
    src = root / "set_01" / "test_04_unknown_vehicle_unknown_attack" / "DoS-1.csv"
    dst = root / "set_02" / "test_01_known_vehicle_known_attack" / "DoS-1.csv"
    dst.write_bytes(src.read_bytes())  # same frames, different vehicle label
    out = tmp_path / "bench"
    with pytest.raises(bm.UnresolvedDuplicates) as err:
        _freeze(data, out)
    assert "set_01/test_04_unknown_vehicle_unknown_attack/DoS-1" in str(err.value)
    assert "set_02/test_01_known_vehicle_known_attack/DoS-1" in str(err.value)
    sha = err.value.groups[0]["sha256"]
    res = tmp_path / "resolutions.yaml"
    res.write_text(
        yaml.safe_dump(
            {
                "resolutions": [
                    {
                        "sha256": sha,
                        "action": "drop",
                        "captures": [
                            "can-train-and-test/set_02/test_01_known_vehicle_known_attack/DoS-1"
                        ],
                        "reason": "identical to a set_01 capture labelled as another vehicle",
                    }
                ]
            }
        )
    )
    _freeze(data, out, res)
    m = json.loads((out / "manifest.json").read_text())
    assert m["resolutions_sha256"]
    dropped = [c for c in m["captures"] if c["role"] == "dropped"]
    assert [c["id"] for c in dropped] == [
        "can-train-and-test/set_02/test_01_known_vehicle_known_attack/DoS-1"
    ]


def test_resolution_needs_a_reason(data, tmp_path):
    res = tmp_path / "r.yaml"
    res.write_text(yaml.safe_dump({"resolutions": [{"sha256": "x", "action": "drop", "captures": []}]}))
    with pytest.raises(ValueError, match="reason"):
        bm.load_resolutions(res)


def test_verify_captures_names_a_changed_capture(data, tmp_path):
    out = tmp_path / "bench"
    _freeze(data, out)
    manifest = json.loads((out / "manifest.json").read_text())
    path = data / "can-train-and-test/extracted/set_01/test_02_unknown_vehicle_known_attack/DoS-2.csv"
    path.write_text(path.read_text().replace(",0\n", ",1\n", 1))
    with pytest.raises(bm.CaptureChanged, match="set_01/test_02_unknown_vehicle_known_attack/DoS-2"):
        bm.verify_captures(
            manifest,
            {"can-train-and-test": data / "can-train-and-test" / "extracted", "road": data / "road"},
        )


def test_roles(data, tmp_path):
    out = tmp_path / "bench"
    _freeze(data, out)
    roles = {
        c["id"]: (c["role"], c["attack_family"])
        for c in json.load(open(out / "manifest.json"))["captures"]
    }
    # validation: the highest-numbered capture per attack type of train_01
    assert roles["can-train-and-test/set_01/train_01/DoS-2"][0] == "validation"
    assert roles["can-train-and-test/set_01/train_01/DoS-1"][0] == "train"
    assert roles["can-train-and-test/set_01/train_01/fuzzing-1"][0] == "validation"
    assert roles["can-train-and-test/set_01/test_02_unknown_vehicle_known_attack/DoS-1"][0] == "test"
    assert roles["road/attacks/fuzzing_attack_2"] == ("test", "fuzzing")
    assert roles["road/attacks/fuzzing_attack_1"] == ("train", "fuzzing")
    assert roles["road/attacks/correlated_signal_attack_2"] == ("test", "fabrication")
    assert roles["road/attacks/correlated_signal_attack_2_masquerade"] == ("out_of_scope", "masquerade")
    assert roles["road/attacks/accelerator_attack_drive_2"] == ("out_of_scope", "accelerator")
    for i in range(8):
        name = f"ambient_drive_{i}.log"
        want = "test" if zlib.crc32(name.encode()) % 4 == 0 else "train"
        assert roles[f"road/ambient/ambient_drive_{i}"] == (want, "benign")
