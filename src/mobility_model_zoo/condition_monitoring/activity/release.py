"""Upload folder of a pace-cnn release (feature 021, T045; contracts/release-files.md).

    uv run condmon activity export --version 0.1.0 --out DIR

Exports the candidate run (seed 0 of the criteria record) with the generic int8 exporter and writes
`config.json`: the labels, the input contract (channels, units, rate, window, overlap), the
training-subject normalisation of the frozen benchmark, the model's quantisation and the
preparation steps of `prepare.py`. No dataset window and no subject number is written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mobility_model_zoo.condition_monitoring import benchmark as bm
from mobility_model_zoo.condition_monitoring.activity import evaluate as ev
from mobility_model_zoo.condition_monitoring.activity import prepare
from mobility_model_zoo.condition_monitoring.activity import train as pace
from mobility_model_zoo.edge.int8.release_export import ExportRefused, export_int8_release

FORMAT = "pace-cnn-v1"
SCHEMA = Path(__file__).with_name(f"{FORMAT}.schema.json")

__all__ = ["ExportRefused", "config_json", "export"]


def config_json(manifest: dict, qm, version: str) -> dict[str, Any]:
    units = {"acc": prepare.UNITS["acc"], "gyro": prepare.UNITS["gyro"]}
    return {
        "model": pace.NAME,
        "version": version,
        "format": FORMAT,
        "labels": pace.LABELS,
        "input": {
            "shape": [1, prepare.WINDOW, len(pace.SIGNALS)],
            "layout": "row-major: sample t, then channel c (index t * 9 + c)",
            "window": prepare.WINDOW,
            "rate_hz": prepare.RATE_HZ,
            "overlap": 0.5,
            "channels": [
                {"name": ch, "unit": units["gyro"] if "gyro" in ch else units["acc"]}
                for ch in pace.SIGNALS
            ],
            "sensor": "6-axis IMU worn at the waist (belt), as in UCI HAR",
        },
        "normalisation": {
            "rule": "(x - mean) / std per channel",
            "from": f"training subjects of {manifest['benchmark']} (validation excluded)",
            "mean": manifest["normalisation"]["mean"],
            "std": manifest["normalisation"]["std"],
        },
        "quantisation": {
            "input_scale": qm.input_scale,
            "input_zero_point": qm.input_zp,
            "output_scale": qm.output_scale,
            "output_zero_point": qm.output_zp,
            "output": "int8 scores in label order; argmax is the predicted activity",
        },
        "preparation": prepare.config_block(),
        "benchmark": manifest["benchmark"],
    }


def export(version: str, out: Path) -> dict[str, Any]:
    from mobility_model_zoo.edge.int8.model import QModel
    from mobility_model_zoo.release.sbom import library

    criteria, _ = ev.load_criteria()
    seed = criteria["seeds"]["candidate"]
    run = ev.run_dir(seed)
    npz, tflite = run / f"{pace.NAME}.npz", run / f"{pace.NAME}.tflite"
    report_path = run / f"{pace.NAME}.report.json"
    if not (npz.exists() and tflite.exists() and report_path.exists()):
        raise ExportRefused(f"candidate run of seed {seed} is missing in {run}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = bm.load_manifest(pace.manifest_path())
    if report.get("manifest_sha256") != bm.file_sha256(pace.manifest_path()):
        raise ExportRefused("the candidate run was trained on another benchmark manifest")
    qm = QModel.load(npz)
    libraries = [
        library("tensorflow", report["tensorflow"], "training and full-int8 conversion"),
        library("keras", report["keras"], "model definition and training"),
    ]
    return export_int8_release(
        npz,
        tflite,
        out,
        config=config_json(manifest, qm, version),
        example_format=FORMAT,
        schema=SCHEMA,
        sbom_meta={
            "name": pace.NAME,
            "description": "int8 activity recognition CNN for the microinfer engine (C99)",
            "libraries": libraries,
        },
        generator_seed=seed,
    )
