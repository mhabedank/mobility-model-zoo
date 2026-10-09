"""`edge measure` against the simulator board `sim` (T062)."""

import json
import os
import shutil

import jsonschema
import pytest

from mobility_model_zoo.edge.bench import cli, measure
from mobility_model_zoo.edge.bench.reference_models import bench_models, ensure_sources
from mobility_model_zoo.edge.int8.model import QModel
from mobility_model_zoo.edge.paths import EDGE_MODELS, REPO_ROOT

needs_cc = pytest.mark.skipif(
    not shutil.which("make") or not (shutil.which("cc") or os.environ.get("CC")),
    reason="needs make + a C compiler (simulator build)",
)

METRICS = {
    "latency_us": "us",
    "latency_p99_us": "us",
    "flash_kb": "KiB",
    "ram_kb": "KiB",
    "arena_bytes": "bytes",
}


@pytest.fixture
def lab_env(tmp_path, monkeypatch):
    """Isolated build/lock/results dirs so the shared build/fw artifacts stay untouched."""
    for key in ("build_dir", "lock_dir", "results_dir"):
        monkeypatch.setenv(f"MMZ_{key.upper()}", str(tmp_path / key))
    monkeypatch.delenv("MMZ_BOARDS", raising=False)
    monkeypatch.delenv("MMZ_EDGE_MODELS", raising=False)
    bench_models()  # reference models in build/edge/models (built on first use)
    yield tmp_path
    monkeypatch.delenv("MMZ_EDGE_MODELS", raising=False)
    ensure_sources()  # drop the test models from the shared generated firmware sources


def _run(*argv):
    return cli.main(["measure", *map(str, argv), "-b", "sim", "-n", "5", "--warmup", "1"])


def _check(path, model):
    data = json.loads(path.read_text())
    schema = REPO_ROOT / "src" / "mobility_model_zoo" / "release" / "schemas" / "results.schema.json"
    jsonschema.validate(data, json.loads(schema.read_text()))
    assert data["kind"] == "performance"
    assert data["model"] == model.name
    by_name = {m["name"]: m for m in data["metrics"]}
    assert set(by_name) == set(METRICS)
    for name, unit in METRICS.items():
        m = by_name[name]
        assert m["unit"] == unit
        assert m["origin"] == "simulator"
        assert m["value"] > 0, name
        assert m["hardware"].startswith("host simulator")
        assert m["description"] and m["date"]
    assert by_name["arena_bytes"]["value"] == model.arena_size()
    assert by_name["latency_p99_us"]["value"] >= by_name["latency_us"]["value"]
    return data


@needs_cc
def test_measure_reference_model(lab_env):
    npz = EDGE_MODELS / "can_ids_mlp.npz"
    out = lab_env / "ref.json"
    assert _run(npz, "--out", out) == 0
    _check(out, QModel.load(npz))


@needs_cc
def test_measure_custom_model_via_edge_models_env(lab_env):
    qm = QModel.load(EDGE_MODELS / "can_ids_mlp.npz")
    qm.name = "measure_test_tiny"
    qm.description = "test copy of can_ids_mlp under another name"
    npz = lab_env / "measure_test_tiny.npz"
    qm.save(npz)
    out = lab_env / "custom.json"
    assert _run(npz, "--out", out, "--model-version", "0.0.1") == 0
    data = _check(out, qm)
    assert data["version"] == "0.0.1"
    assert "MMZ_EDGE_MODELS" not in os.environ  # restored after the build


@needs_cc
def test_measure_exit_codes(lab_env, monkeypatch):
    assert _run(lab_env / "missing.npz", "--out", lab_env / "x.json") == 2
    assert cli.main(["measure", str(EDGE_MODELS / "can_ids_mlp.npz"), "-b", "nope", "--out", "x"]) == 2
    # A model that is not compiled into the firmware: the device does not know it -> 1.
    qm = QModel.load(EDGE_MODELS / "can_ids_mlp.npz")
    qm.name = "not_in_firmware"
    npz = lab_env / "not_in_firmware.npz"
    qm.save(npz)
    monkeypatch.setattr(measure, "_needs_env", lambda model: False)
    assert _run(npz, "--out", lab_env / "y.json") == 1
    assert not (lab_env / "y.json").exists()


def test_origin_and_hardware_from_inventory():
    from mobility_model_zoo.edge.bench.config import load_lab
    from mobility_model_zoo.edge.paths import HIL_DIR

    lab = load_lab(HIL_DIR / "boards.yaml")
    assert measure.origin_of(lab.board("sim")) == "simulator"
    assert measure.origin_of(lab.board("esp8266-1")) == "real_board"
    qemu = load_lab(HIL_DIR / "qemu-boards.yaml").board("esp32-qemu")
    assert measure.origin_of(qemu) == "emulator"
    info = {"chip": "ESP32-D0WD", "cpu_mhz": 240}
    assert measure.hardware_of(qemu, info, "emulator").startswith("ESP32-D0WD, 240 MHz in QEMU")
    real = measure.hardware_of(lab.board("esp8266-1"), {"chip": "ESP8266", "cpu_mhz": 80}, "real_board")
    assert real.startswith("ESP8266, 80 MHz")
