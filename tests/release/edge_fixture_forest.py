"""The emlearn tree fixture `edge-fixture-forest` (feature 007, T020).

Model files never go into git, so a 3-tree forest is trained at test time on synthetic frames,
exported to C with emlearn, and the examples are computed from the host build of that C code.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

NAME = "edge-fixture-forest"
ALARM = {"k": 2, "window_ms": 200, "holdoff_ms": 1000}


def staged_files() -> dict[str, bytes]:
    """Trained forest -> the staged files of an emlearn release (data-model.md)."""
    import joblib
    from sklearn.ensemble import RandomForestClassifier

    from mobility_model_zoo.security.can_ids import forest
    from mobility_model_zoo.security.can_ids.forest_features import extract
    from mobility_model_zoo.security.can_ids.scorer import HEADERS, SOURCES
    from mobility_model_zoo.security.can_ids.synth import generate

    frames = pd.concat([generate(a, n_frames=3000, seed=i) for i, a in enumerate(("dos", "fuzzing"))])
    idx = forest.cols(forest.FEATURE_SETS["no_can_id"])
    x, y = extract(frames)[:, idx], frames["label"].to_numpy()
    clf = RandomForestClassifier(n_estimators=3, max_depth=4, random_state=0).fit(x, y)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        forest.to_c(clf, idx, 0.5, ALARM, out)
        joblib.dump(
            {"model": clf, "threshold": 0.5, "input_index": idx, "alarm": ALARM}, out / "m.joblib"
        )
        files = {h: (out / h).read_bytes() for h in HEADERS}
        files["model.joblib"] = (out / "m.joblib").read_bytes()
    files["config.json"] = json.dumps({"model": NAME, "alarm": ALARM}).encode()
    files.update({f"c/{n}": p.read_bytes() for n, p in SOURCES.items()})
    return files


def write_examples(model_dir: Path, files: dict[str, bytes]) -> None:
    from mobility_model_zoo.security.can_ids.scorer import build_scorer, example_from_frames
    from mobility_model_zoo.security.can_ids.synth import generate

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for name, data in files.items():
            (work / name).parent.mkdir(parents=True, exist_ok=True)
            (work / name).write_bytes(data)
        exe = build_scorer(work, work / "build", sources_dir=work / "c")
        ex_dir = model_dir / "examples"
        ex_dir.mkdir(parents=True, exist_ok=True)
        for i, attack in enumerate(("dos", "fuzzing", "scan")):
            gen = {"name": "picket-synth", "version": 1, "seed": 10 + i, "attack": attack}
            ex = example_from_frames(generate(attack, n_frames=600, seed=10 + i), exe, "synthetic", gen)
            (ex_dir / f"0{i + 1}-{attack}.json").write_text(json.dumps(ex) + "\n", encoding="utf-8")


def flip_first_score_bit(path: Path) -> None:
    ex = json.loads(path.read_text())
    bits = int(ex["expected_scores"][0], 16) ^ 1
    ex["expected_scores"][0] = f"{bits:08x}"
    path.write_text(json.dumps(ex))


def staged_bits(frames: np.ndarray) -> list[str]:  # pragma: no cover - debugging aid
    return [f"{int(b):08x}" for b in np.asarray(frames, dtype=np.float32).view(np.uint32)]
