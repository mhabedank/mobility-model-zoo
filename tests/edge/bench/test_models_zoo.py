import json
import shutil
import subprocess

import numpy as np
import pytest

from mobility_model_zoo.edge.bench.reference_models import ensure_sources, load_eval, load_zoo
from mobility_model_zoo.edge.int8.codegen import zoo_sources
from mobility_model_zoo.edge.int8.quant import dequantize, quantize
from mobility_model_zoo.edge.int8.reference import run_batch
from mobility_model_zoo.edge.paths import BENCH_FIRMWARE

ZOO = load_zoo()


def test_firmware_sources_match_zoo(tmp_path, monkeypatch):
    """The build generates firmware/bench/lib/modelzoo from the bench models (not committed)."""
    monkeypatch.delenv("MMZ_EDGE_MODELS", raising=False)
    models = ensure_sources(fw_out=tmp_path)
    h, c = zoo_sources(models)
    d = tmp_path
    assert (d / "model_zoo.h").read_text() == h
    assert (d / "model_zoo.c").read_text() == c


@pytest.mark.parametrize("name", list(ZOO))
def test_golden_vectors_reproducible(name):
    m = ZOO[name]
    assert np.array_equal(run_batch(m, m.test_inputs), m.test_outputs)


@pytest.mark.parametrize("name", list(ZOO))
def test_model_roundtrip(tmp_path, name):
    m = ZOO[name]
    m.save(tmp_path / "m.npz")
    m2 = type(m).load(tmp_path / "m.npz")
    assert m2.crc32() == m.crc32()
    assert m2.summary() == m.summary()


def test_can_ids_accuracy_on_eval_set():
    m = ZOO["can_ids_mlp"]
    ev = load_eval("can_ids_mlp")
    acc = (run_batch(m, ev["inputs"]).argmax(1) == ev["labels"]).mean()
    assert acc > 0.97


def test_int8_close_to_float_for_autoencoder():
    m = ZOO["sensor_ae"]
    ev = load_eval("sensor_ae")
    x = ev["targets"][:64]
    out = dequantize(run_batch(m, quantize(x, m.input_scale, m.input_zp)), m.output_scale, m.output_zp)
    assert np.abs(out - x).mean() < 0.1


def test_excluding_a_model_shrinks_buffers(tmp_path):
    if not shutil.which("make") or not shutil.which("cc"):
        pytest.skip("needs make + cc")
    ensure_sources()
    subprocess.run(
        [
            "make",
            "-B",
            "-C",
            str(BENCH_FIRMWARE / "native"),
            f"OUT={tmp_path}",
            "CFLAGS=-O2 -DMI_EXCLUDE_SENSOR_AE",
        ],
        check=True,
        capture_output=True,
    )
    out = subprocess.run(
        [str(tmp_path / "edge-sim")], input="#1 INFO\n", capture_output=True, text=True
    ).stdout
    info = json.loads([line for line in out.splitlines() if '"id":1' in line][0][1:])
    assert info["models"] == len(ZOO) - 1
    assert info["arena"] == max(m.arena_size() for n, m in ZOO.items() if n != "sensor_ae")
