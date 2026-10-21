"""`edge performance`: merge measurements into performance.json (feature 021, T032; research R9)."""

import json
from pathlib import Path

import jsonschema
import pytest

from mobility_model_zoo.edge.bench import cli
from mobility_model_zoo.edge.bench import performance as perf

SCHEMA = json.loads(
    (
        Path(__file__).parents[3] / "src/mobility_model_zoo/release/schemas/results.schema.json"
    ).read_text()
)


def _measured(board, origin, latency=40000.0, image=True):
    hw = {"real_board": f"ESP32 (board {board})", "emulator": "ESP32 in QEMU", "simulator": "host"}
    rows = [
        ("latency_us", latency, "us"),
        ("latency_mean_us", latency + 5, "us"),
        ("latency_p99_us", latency + 50, "us"),
        ("flash_kb", 60.1, "KiB"),
        ("ram_kb", 20.4, "KiB"),
        ("arena_bytes", 4096, "bytes"),
        ("device_bit_exact_vectors", 1.0, "share"),
    ]
    if image:
        rows += [("flash_kb_image", 300.2, "KiB"), ("ram_kb_image", 40.0, "KiB")]
    return {
        "kind": "performance",
        "model": "pace-cnn",
        "version": "0.1.0",
        "synthetic": False,
        "source_run": f"edge measure pace-cnn.npz -b {board} (build 0000abcd)",
        "metrics": [
            {
                "name": n,
                "value": v,
                "unit": u,
                "description": n,
                "date": "2026-10-20",
                "hardware": hw[origin],
                "origin": origin,
            }
            for n, v, u in rows
        ],
    }


def test_reference_gives_plain_names_and_extras_suffixed_names():
    merged = perf.merge(
        "pace-cnn",
        "0.1.0",
        _measured("esp32-1", "real_board"),
        [
            _measured("esp32-qemu", "emulator"),
            _measured("esp8266-1", "real_board"),
            _measured("sim", "simulator"),
        ],
    )
    by = {m["name"]: m for m in merged["metrics"]}
    for n in ("flash_kb", "ram_kb", "latency_us", "latency_mean_us", "device_bit_exact_vectors"):
        assert by[n]["origin"] == "real_board" and "esp32-1" in by[n]["hardware"]
    assert by["flash_kb_image_esp32"]["value"] == 300.2
    assert by["ram_kb_image_esp32"]["origin"] == "real_board"
    assert by["latency_us_esp32_qemu"]["origin"] == "emulator"
    assert by["latency_us_esp8266"]["origin"] == "real_board"
    assert by["latency_us_host"]["origin"] == "simulator"
    assert "flash_kb_esp8266" not in by  # sizes of other boards are not merged
    jsonschema.validate(merged, SCHEMA)


def test_non_real_reference_is_refused_without_substitute():
    with pytest.raises(perf.PerformanceRefused, match="real board"):
        perf.merge("pace-cnn", "0.1.0", _measured("esp32-qemu", "emulator"), [])


def test_substitute_keeps_its_origin_on_the_plain_rows():
    merged = perf.merge(
        "pace-cnn", "0.1.0", _measured("esp32-qemu", "emulator"), [], allow_substitute=True
    )
    by = {m["name"]: m for m in merged["metrics"]}
    assert by["latency_us"]["origin"] == "emulator" and by["flash_kb"]["origin"] == "emulator"


def test_cli_writes_the_release_file_and_refuses_with_exit_4(tmp_path, monkeypatch):
    ref, emu = tmp_path / "esp32.json", tmp_path / "qemu.json"
    ref.write_text(json.dumps(_measured("esp32-1", "real_board")))
    emu.write_text(json.dumps(_measured("esp32-qemu", "emulator")))
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    argv = ["performance", "--model", "pace-cnn", "--version", "0.1.0"]
    assert cli.main([*argv, "--reference", str(ref), "--extra", str(emu)]) == 0
    out = tmp_path / "zoo/models/pace-cnn/results/0.1.0/performance.json"
    jsonschema.validate(json.loads(out.read_text()), SCHEMA)
    assert cli.main([*argv, "--reference", str(emu)]) == 4
