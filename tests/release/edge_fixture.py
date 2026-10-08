"""The int8 model and examples of the mcu fixture `edge-fixture-tiny` (feature 005 T055).

Model files never go into git (history-check), so the npz is built deterministically at test time
and the examples are computed from it.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from mobility_model_zoo.edge.int8.floatnet import FLayer, FloatNet
from mobility_model_zoo.edge.int8.model import QModel
from mobility_model_zoo.edge.int8.reference import run_model

NAME = "edge-fixture-tiny"


def tiny_model() -> QModel:
    rng = np.random.default_rng(5)
    net = FloatNet((1, 1, 8), [FLayer("dense", 6, act="relu"), FLayer("dense", 2)]).build(rng)
    return net.quantize(NAME, rng.normal(size=(64, 8)).astype(np.float32), description="test model")


def npz_bytes(model: QModel) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.npz"
        model.save(path)
        return path.read_bytes()


def write_examples(model_dir: Path, model: QModel) -> None:
    ex_dir = model_dir / "examples"
    ex_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(9)
    for i in range(3):
        x = rng.integers(-128, 128, 8).astype(np.int8)
        y = run_model(model, x).reshape(-1)
        ex = {"input": x.astype(int).tolist(), "expected": y.astype(int).tolist(), "source": "synthetic"}
        (ex_dir / f"0{i + 1}-random.json").write_text(json.dumps(ex) + "\n", encoding="utf-8")
