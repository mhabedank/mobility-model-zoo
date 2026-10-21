"""Generic int8 release exporter (feature 021, T033/T034; contracts/release-files.md, research R10)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import jsonschema
import numpy as np
import pytest

from mobility_model_zoo.edge.int8 import release_export as rx
from mobility_model_zoo.edge.int8.floatnet import FLayer, FloatNet
from mobility_model_zoo.edge.int8.reference import run_model

SCHEMA = (
    Path(__file__).parents[3]
    / "src/mobility_model_zoo/condition_monitoring/activity/pace-cnn-v1.schema.json"
)
ALLOW = {
    "pace-cnn.npz",
    "pace-cnn.tflite",
    "config.json",
    "sbom.cdx.json",
    "c/pace_cnn_model.c",
    "c/pace_cnn_model.h",
    "c/microinfer.c",
    "c/microinfer.h",
    "examples/example-1.json",
    "examples/example-2.json",
    "examples/example-3.json",
}


@pytest.fixture
def run(tmp_path):
    rng = np.random.default_rng(0)
    net = FloatNet(
        (1, 128, 9),
        [
            FLayer("conv2d", 4, kernel=(1, 5), padding="same", act="relu"),
            FLayer("maxpool2d", kernel=(1, 2), stride=(1, 2)),
            FLayer("avgpool2d", kernel=(1, 64), stride=(1, 64)),
            FLayer("reshape"),
            FLayer("dense", 6),
        ],
    ).build(rng)
    qm = net.quantize("pace-cnn", rng.normal(size=(32, 1, 128, 9)).astype(np.float32))
    d = tmp_path / "run"
    d.mkdir()
    qm.save(d / "pace-cnn.npz")
    (d / "pace-cnn.tflite").write_bytes(b"TFL3 test bytes")
    return d, qm


def _export(run, tmp_path, **kw):
    d, _ = run
    return rx.export_int8_release(
        d / "pace-cnn.npz",
        d / "pace-cnn.tflite",
        tmp_path / "out",
        config={"labels": list("abcdef"), "format": "pace-cnn-v1"},
        example_format="pace-cnn-v1",
        schema=SCHEMA,
        sbom_meta={"name": "pace-cnn", "description": "test", "libraries": []},
        **kw,
    )


def _files(out):
    return {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}


def test_folder_matches_the_allow_list(run, tmp_path):
    _export(run, tmp_path)
    out = tmp_path / "out"
    assert _files(out) == ALLOW
    assert not list(out.rglob("*.eval.npz"))
    cfg = json.loads((out / "config.json").read_text())
    assert cfg["format"] == "pace-cnn-v1" and cfg["labels"] == list("abcdef")
    sbom = json.loads((out / "sbom.cdx.json").read_text())
    assert {c["name"] for c in sbom["components"]} >= {"c/pace_cnn_model.c", "c/microinfer.c"}


def test_examples_are_synthetic_and_bit_exact(run, tmp_path):
    _, qm = run
    _export(run, tmp_path)
    schema = json.loads(SCHEMA.read_text())
    for i in range(3):
        ex = json.loads((tmp_path / "out" / "examples" / f"example-{i + 1}.json").read_text())
        jsonschema.validate(ex, schema)
        assert ex["source"] == "synthetic" and ex["generator"]["name"] == "uniform-int8"
        x = np.asarray(ex["input"], np.int8)
        assert np.array_equal(x, qm.test_inputs[i])  # the board's self-test covers the examples
        assert ex["expected"] == run_model(qm, x).tolist()


def test_a_file_outside_the_allow_list_is_refused(run, tmp_path):
    out = tmp_path / "out"
    (out / "data").mkdir(parents=True)
    (out / "data" / "windows.npy").write_bytes(b"x")
    with pytest.raises(rx.ExportRefused, match="allow-list"):
        _export(run, tmp_path)


def test_an_example_that_does_not_reproduce_is_refused(run, tmp_path, monkeypatch):
    real = rx.run_model
    monkeypatch.setattr(rx, "run_model", lambda m, x: real(m, x) + np.int8(1))
    with pytest.raises(rx.ExportRefused, match="reproduce"):
        _export(run, tmp_path)


needs_cc = pytest.mark.skipif(
    not (shutil.which("cc") or os.environ.get("CC")), reason="needs a host C compiler"
)

DRIVER = r"""
#include <stdio.h>
#include "pace_cnn_model.h"

int main(void) {
    static int8_t arena[PACE_CNN_ARENA_SIZE];
    int8_t in[PACE_CNN_IN_SIZE], out[PACE_CNN_OUT_SIZE];
    for (unsigned i = 0; i < PACE_CNN_IN_SIZE; i++) {
        int v;
        if (scanf("%d", &v) != 1) return 2;
        in[i] = (int8_t)v;
    }
    if (mi_invoke(&mi_model_pace_cnn, in, out, arena, sizeof arena) != 0) return 3;
    for (unsigned i = 0; i < PACE_CNN_OUT_SIZE; i++) printf("%d ", out[i]);
    return 0;
}
"""


@needs_cc
def test_shipped_c_sources_reproduce_the_examples(run, tmp_path):
    _export(run, tmp_path)
    out = tmp_path / "out"
    (tmp_path / "driver.c").write_text(DRIVER)
    exe = tmp_path / "pace"
    cc = os.environ.get("CC", "cc")
    srcs = [str(p) for p in sorted((out / "c").glob("*.c"))]
    subprocess.run(
        [
            cc,
            "-std=c99",
            "-O2",
            "-Wall",
            "-Werror",
            "-I",
            str(out / "c"),
            *srcs,
            str(tmp_path / "driver.c"),
            "-o",
            str(exe),
        ],
        check=True,
        capture_output=True,
    )
    for p in sorted((out / "examples").glob("*.json")):
        ex = json.loads(p.read_text())
        got = subprocess.run(
            [str(exe)], input=" ".join(map(str, ex["input"])), capture_output=True, text=True
        )
        assert got.returncode == 0, got.stderr
        assert [int(v) for v in got.stdout.split()] == ex["expected"], p.name
