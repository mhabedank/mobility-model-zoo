"""Release export of picket-forest (feature 007, T026/T027, data-model.md "Release record").

The release model is the harness's model trained on the training captures of all four
can-train-and-test sets, with threshold and alarm rule chosen on their validation captures
(`evaluate.release_model`). The export writes every staged file:

    picket_forest_model.h, picket_forest_config.h   generated C (emlearn forest, inputs, alarm rule)
    model.joblib                                    host reference (scikit-learn)
    config.json                                     recipe, selection, parity, benchmark hash
    c/*.c, c/*.h                                    detector, feature and alarm sources
    sbom.cdx.json                                   CycloneDX bill of materials of the device code

and checks C against Python on the validation captures (must be identical).
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mobility_model_zoo.security.can_ids import forest, scorer
from mobility_model_zoo.security.can_ids.evaluate import DEFAULT_ALARM, code_commit, load_capture

ALARM_PREFERENCE = ("1", "10")  # alarm rule: within 1 false alarm/h on validation, else within 10


def _alarm(cal: dict) -> dict:
    for budget in ALARM_PREFERENCE:
        point = cal["points"].get(budget)
        if point:
            return {
                "k": point["k"],
                "window_ms": point["window_ms"],
                "holdoff_ms": point["holdoff_ms"],
                "selected_on": f"validation captures, best episode recall within {budget} FA/h",
                "validation": point["validation"],
            }
    return {**DEFAULT_ALARM, "selected_on": "default (no rule met a budget on validation)"}


def sbom(out_dir: Path) -> dict:
    """The SBOM of picket-forest's device code (generator shared in release/sbom.py)."""
    import sklearn

    from mobility_model_zoo.release.sbom import library
    from mobility_model_zoo.release.sbom import sbom as build_sbom

    emlearn = forest._import_emlearn()  # keeps the numpy error state
    return build_sbom(
        out_dir,
        name="picket-forest",
        description="CAN intrusion detector for microcontrollers (C99)",
        libraries=[
            library("emlearn", emlearn.__version__, "C code generator of the forest"),
            library("scikit-learn", sklearn.__version__, "training of the forest"),
        ],
        tool="mobility_model_zoo.security.can_ids.release_export",
    )


def export(
    out_dir: Path, manifest: dict, sources: dict, cache: Path | None, store: Path | None = None
) -> dict[str, Any]:
    import joblib

    from mobility_model_zoo.security.can_ids.evaluate import release_model

    det, cal = release_model(manifest, sources, cache, store)
    alarm = _alarm(cal)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "c").mkdir(parents=True)
    forest.to_c(det.model, det.idx, cal["threshold"], alarm, out_dir)
    for name, path in scorer.SOURCES.items():
        shutil.copy(path, out_dir / "c" / name)
    joblib.dump(
        {"model": det.model, "threshold": cal["threshold"], "input_index": det.idx, "alarm": alarm},
        out_dir / "model.joblib",
    )
    # C against Python on the validation captures (the release model has no untouched test set)
    exe = scorer.build_scorer(out_dir, out_dir.parent / "export-build", sources_dir=out_dir / "c")
    frames = mismatches = 0
    for e in manifest["captures"]:
        if e["dataset"] != "can-train-and-test" or e["role"] != "validation":
            continue
        cap = load_capture(e, sources, cache)
        df = pd.DataFrame({"ts": cap["ts"], "can_id": cap["can_id"], "dlc": cap["dlc"]})
        for i in range(8):
            df[f"b{i}"] = cap["data"][:, i]
        c_scores, _ = scorer.run_scorer(exe, df)
        py = det.score([cap])[0]
        frames += len(py)
        mismatches += int(np.count_nonzero(c_scores != py))
    if mismatches:
        raise SystemExit(f"C and Python scores differ on {mismatches} of {frames} validation frames")
    config = {
        "model": "picket-forest",
        "algorithm": "random forest, hard voting, exported to C with emlearn (float)",
        "hyperparameters": {**det.info["hyperparameters"], "min_samples_leaf": 20},
        "tree_nodes": det.info["tree_nodes"],
        "inputs": [forest.FEATURE_NAMES[i] for i in det.idx],
        "threshold": cal["threshold"],
        "alarm": alarm,
        "training": (
            "train_01 captures of set_01..set_04 of can-train-and-test; validation captures select"
        ),
        "benchmark": manifest["benchmark"],
        "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "code_commit": code_commit(),
        "parity_c_vs_python": {"frames": frames, "mismatches": mismatches, "host": platform.machine()},
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=1, default=float) + "\n")
    (out_dir / "sbom.cdx.json").write_text(json.dumps(sbom(out_dir), indent=1) + "\n")
    return config


def write_examples(export_dir: Path, out_dir: Path) -> list[Path]:
    """Three synthetic examples (fabrication, DoS, fuzzing) with expected scores and alarms from
    the C chain of the export (research R8)."""
    from mobility_model_zoo.security.can_ids.synth import generate

    exe = scorer.build_scorer(
        export_dir, export_dir.parent / "examples-build", sources_dir=export_dir / "c"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, attack in enumerate(("fabrication", "dos", "fuzzing")):
        seed = 100 + i
        gen = {"name": "picket-synth", "version": 1, "seed": seed, "attack": attack}
        ex = scorer.example_from_frames(
            generate(attack, n_frames=2000, seed=seed), exe, "synthetic", gen
        )
        path = out_dir / f"0{i + 1}-{attack}.json"
        path.write_text(json.dumps(ex) + "\n", encoding="utf-8")
        written.append(path)
    return written
