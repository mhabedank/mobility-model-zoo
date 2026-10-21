"""Release folder of an int8 model for the int8 engine (feature 021, research R10).

    export_int8_release(npz, tflite, out, config=..., example_format=..., schema=..., sbom_meta=...)

writes exactly the upload allow-list of specs/021-pace-cnn-first-release/contracts/release-files.md:

    <model>.npz, <model>.tflite      the int8 QModel (synthetic test vectors only) and its flatbuffer
    config.json                      labels, input contract, normalisation, quantisation, preparation
    c/<id>_model.c, c/<id>_model.h   the model's generated C source alone
    c/microinfer.c, c/microinfer.h   the int8 engine (from firmware/bench/lib/microinfer/src/)
    examples/example-<n>.json        synthetic inputs with expected int8 outputs
    sbom.cdx.json                    CycloneDX SBOM of the shipped sources

The examples are the first QModel test vectors (uniform int8 values from the model's seed), so the
board's self-test checks exactly the published examples. No dataset window is ever written: the
held-out `.eval.npz` stays next to the run. The export refuses (`ExportRefused`) if any other file
would end up in the folder or if an example does not reproduce on the host reference. Shared by
the int8 models of every topic (pace-cnn, later hum-fan and picket-mlp).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from mobility_model_zoo.edge.int8.codegen import _ident, model_sources
from mobility_model_zoo.edge.int8.model import QModel
from mobility_model_zoo.edge.int8.reference import run_model
from mobility_model_zoo.edge.paths import BENCH_FIRMWARE

ENGINE_DIR = BENCH_FIRMWARE / "lib" / "microinfer" / "src"
GENERATOR = {"name": "uniform-int8", "version": 1}


class ExportRefused(Exception):
    pass


def allow_list(name: str, n_examples: int) -> set[str]:
    m = _ident(name)
    return {
        f"{name}.npz",
        f"{name}.tflite",
        "config.json",
        "sbom.cdx.json",
        f"c/{m}_model.c",
        f"c/{m}_model.h",
        "c/microinfer.c",
        "c/microinfer.h",
        *(f"examples/example-{i + 1}.json" for i in range(n_examples)),
    }


def _files(out: Path) -> set[str]:
    return {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}


def examples(qm: QModel, example_format: str, n: int, seed: int) -> list[dict[str, Any]]:
    """The first `n` test vectors of the QModel with the host reference's output. `seed` is the
    seed the test vectors were drawn with (the training seed, `tflite_import.load_tflite`)."""
    if len(qm.test_inputs) < n:
        raise ExportRefused(f"{qm.name} has {len(qm.test_inputs)} test vectors, {n} examples needed")
    out = []
    for i in range(n):
        x = np.asarray(qm.test_inputs[i], np.int8)
        expected = run_model(qm, x)
        if not np.array_equal(expected, qm.test_outputs[i]):
            raise ExportRefused(f"example {i + 1} does not reproduce the stored test vector")
        out.append(
            {
                "format": example_format,
                "source": "synthetic",
                "generator": {**GENERATOR, "seed": seed, "index": i},
                "input": x.astype(int).tolist(),
                "expected": expected.astype(int).tolist(),
            }
        )
    return out


def export_int8_release(
    npz: Path,
    tflite: Path,
    out: Path,
    *,
    config: dict[str, Any],
    example_format: str,
    schema: Path,
    sbom_meta: dict[str, Any],
    n_examples: int = 3,
    generator_seed: int = 0,
) -> dict[str, Any]:
    import jsonschema

    from mobility_model_zoo.release.sbom import SBOM_FILE, sbom

    qm = QModel.load(npz)
    out = Path(out)
    allowed = allow_list(qm.name, n_examples)
    if out.exists() and (extra := _files(out) - allowed):
        raise ExportRefused(f"{out} holds files outside the allow-list: {sorted(extra)[:5]}")
    (out / "c").mkdir(parents=True, exist_ok=True)
    (out / "examples").mkdir(exist_ok=True)

    shutil.copy2(npz, out / f"{qm.name}.npz")
    shutil.copy2(tflite, out / f"{qm.name}.tflite")
    h, c = model_sources(qm)
    m = _ident(qm.name)
    (out / "c" / f"{m}_model.h").write_text(h)
    (out / "c" / f"{m}_model.c").write_text(c)
    for f in ("microinfer.c", "microinfer.h"):
        shutil.copy2(ENGINE_DIR / f, out / "c" / f)

    validator = json.loads(Path(schema).read_text())
    shipped = QModel.load(out / f"{qm.name}.npz")
    for i, ex in enumerate(examples(shipped, example_format, n_examples, generator_seed)):
        jsonschema.validate(ex, validator)
        got = run_model(shipped, np.asarray(ex["input"], np.int8))
        if got.astype(int).tolist() != ex["expected"]:
            raise ExportRefused(f"example {i + 1} does not reproduce on the host reference")
        (out / "examples" / f"example-{i + 1}.json").write_text(json.dumps(ex) + "\n")

    (out / "config.json").write_text(json.dumps(config, indent=1, ensure_ascii=False) + "\n")
    doc = sbom(
        out,
        name=sbom_meta["name"],
        description=sbom_meta["description"],
        libraries=sbom_meta.get("libraries", []),
        tool="mobility_model_zoo.edge.int8.release_export",
    )
    (out / SBOM_FILE).write_text(json.dumps(doc, indent=1) + "\n")

    files = _files(out)
    if files != allowed:
        raise ExportRefused(
            f"release folder differs from the allow-list: extra {sorted(files - allowed)}, "
            f"missing {sorted(allowed - files)}"
        )
    return {"model": qm.name, "out": str(out), "files": sorted(files)}
