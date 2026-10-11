"""Device evidence of picket-forest (feature 007, T029): host run and result parsing."""

import json
import shutil
from pathlib import Path

import pytest

from mobility_model_zoo.release.registry import schema_errors
from mobility_model_zoo.security.can_ids import measure

LINE = (
    'boot noise\nPICKET_FOREST_RESULT {"target":"esp8266","cpu_mhz":160,"frames":4000,'
    '"score_mismatches":0,"attack_frames":120,"detected":118,"alarms":2,"expected_alarms":2,'
    '"latency_us":{"median":41.5,"mean":43.0,"p99":77.1,"max":90.0},"state_bytes":10600,'
    '"free_heap":30000}\n'
)


@pytest.fixture
def export(tmp_path):
    pytest.importorskip("emlearn")
    if not (shutil.which("cc") or shutil.which("gcc")):
        pytest.skip("needs a C compiler")
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "release"))
    from edge_fixture_forest import staged_files

    for name, data in staged_files().items():
        if not name.startswith("c/") and name.endswith(".h"):
            (tmp_path / name).write_bytes(data)
    return tmp_path


def test_host_measurement(export, tmp_path):
    run = measure.run_host(export, n_frames=20_000)
    assert run["latency_us"] > 0
    out = tmp_path / "performance.json"
    data = measure.merge(out, measure.metrics("host", run), "picket-forest", "0.1.0")
    assert data["metrics"][0]["origin"] == "host"


def test_result_line_and_board_metrics(tmp_path):
    lines = iter(LINE.splitlines())
    result = measure._read_result(lambda: next(lines), timeout=5)
    run = {"result": result, "sizes": {"text": 6000, "data": 200, "bss": 100}}
    ms = {m["name"]: m for m in measure.metrics("esp8266", run)}
    assert {"latency_us", "latency_p99_us", "flash_kb", "ram_kb"} <= set(ms)
    assert ms["latency_us"]["origin"] == "real_board"
    assert "substitute for the reference board ESP32-S3" in ms["latency_us"]["hardware"]
    out = tmp_path / "perf.json"
    data = measure.merge(out, list(ms.values()), "picket-forest", "0.1.0")
    assert schema_errors("results", data) == []


def test_mismatch_is_refused():
    run = {
        "result": json.loads(
            LINE.split("RESULT ")[1].replace('"score_mismatches":0', '"score_mismatches":3')
        ),
        "sizes": {"text": 1, "data": 1, "bss": 1},
    }
    with pytest.raises(ValueError, match="3 score mismatches"):
        measure.metrics("esp8266", run)


def test_qemu_metrics_are_marked_emulator():
    lines = iter(LINE.replace('"esp8266"', '"esp32"').splitlines())
    run = {
        "result": measure._read_result(lambda: next(lines), 5),
        "sizes": {"text": 1, "data": 1, "bss": 1},
    }
    ms = measure.metrics("esp32-qemu", run)
    assert all(m["origin"] == "emulator" for m in ms)
    assert "not representative" in ms[0]["description"]
