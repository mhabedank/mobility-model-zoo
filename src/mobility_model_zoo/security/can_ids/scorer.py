"""Host build of the picket-forest C detector (feature 007, research R7).

The same C code that runs on the device (features, emlearn forest, alarm stage) is compiled for
the host with `-ffp-contract=off`, so its float32 scores are bit-identical to the Python reference.
Used for the C-versus-Python parity check, the published examples and release gate rules 12/13.

Sources come either from the repository or from a staged release folder (`c/` subfolder), and the
generated headers (`picket_forest_model.h`, `picket_forest_config.h`) from an export folder.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from mobility_model_zoo.edge.paths import REPO_ROOT

C_DIR = REPO_ROOT / "firmware" / "picket-forest" / "c"
FEATURES_DIR = REPO_ROOT / "firmware" / "components" / "can_features"
HARNESS = C_DIR / "host_score.c"
# Released device sources: name in the release folder `c/` -> repository path
SOURCES = {
    "picket_forest.c": C_DIR / "picket_forest.c",
    "picket_forest.h": C_DIR / "picket_forest.h",
    "msml_can_features.c": FEATURES_DIR / "msml_can_features.c",
    "msml_can_features.h": FEATURES_DIR / "include" / "msml_can_features.h",
    "msml_alarm.c": FEATURES_DIR / "msml_alarm.c",
    "msml_alarm.h": FEATURES_DIR / "include" / "msml_alarm.h",
}
HEADERS = ("picket_forest_model.h", "picket_forest_config.h")
FRAME_DTYPE = np.dtype([("ts", "<i8"), ("can_id", "<u2"), ("dlc", "u1"), ("data", "u1", (8,))])
PAYLOAD = [f"b{i}" for i in range(8)]


def build_scorer(headers_dir: Path, out_dir: Path, sources_dir: Path | None = None) -> Path:
    """Compile the host scorer. `sources_dir` holds the released `SOURCES` (default: repository)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = out_dir / "host_score"
    if sources_dir is None:
        include = [C_DIR, FEATURES_DIR / "include"]
        sources = [SOURCES["picket_forest.c"], SOURCES["msml_can_features.c"], SOURCES["msml_alarm.c"]]
    else:
        include = [sources_dir]
        sources = [sources_dir / n for n in ("picket_forest.c", "msml_can_features.c", "msml_alarm.c")]
    flags = ["-std=c99", "-O2", "-ffp-contract=off", "-Wall", "-Wextra", "-Werror"]
    flags.append("-Wno-unused-parameter")  # emlearn-generated trees ignore features_length
    argv = [os.environ.get("CC", "cc"), *flags, "-I", str(headers_dir)]
    for d in include:
        argv += ["-I", str(d)]
    subprocess.run([*argv, str(HARNESS), *map(str, sources), "-o", str(exe)], check=True)
    return exe


def frames_to_bin(df: pd.DataFrame) -> np.ndarray:
    """Frames with `ts` in seconds (relative to the first frame in the record)."""
    ts = np.asarray(df["ts"].to_numpy(), dtype=np.float64)
    rec = np.zeros(len(df), dtype=FRAME_DTYPE)
    rec["ts"] = np.rint((ts - ts[0]) * 1e6).astype(np.int64) if len(df) else 0
    rec["can_id"] = df["can_id"].to_numpy()
    rec["dlc"] = df["dlc"].to_numpy()
    rec["data"] = df[PAYLOAD].to_numpy(np.uint8)
    return rec


def run_scorer(exe: Path, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(float32 scores, uint8 alarm flags) of the whole C chain for one capture, in bus order."""
    with tempfile.TemporaryDirectory() as tmp:
        fin, fs, fa = Path(tmp) / "f.bin", Path(tmp) / "s.bin", Path(tmp) / "a.bin"
        frames_to_bin(df).tofile(fin)
        subprocess.run([str(exe), str(fin), str(fs), str(fa)], check=True)
        return np.fromfile(fs, dtype=np.float32), np.fromfile(fa, dtype=np.uint8)


def score_bits(scores: np.ndarray) -> list[str]:
    """float32 scores as 8-digit hex IEEE-754 bit patterns (exact comparison in examples)."""
    return [f"{int(b):08x}" for b in np.asarray(scores, dtype=np.float32).view(np.uint32)]


def frames_from_example(example: dict) -> pd.DataFrame:
    """Example frames `[[ts_us, can_id, dlc, [8 bytes]], ...]` -> scorer input."""
    frames = example["frames"]
    df = pd.DataFrame(
        {
            "ts": np.array([f[0] for f in frames], dtype=np.float64) / 1e6,
            "can_id": np.array([f[1] for f in frames], dtype=np.uint16),
            "dlc": np.array([f[2] for f in frames], dtype=np.uint8),
        }
    )
    payload = np.array([f[3] for f in frames], dtype=np.uint8).reshape(-1, 8)
    for i, c in enumerate(PAYLOAD):
        df[c] = payload[:, i]
    return df


def example_from_frames(df: pd.DataFrame, exe: Path, source: str, generator: dict) -> dict:
    """An example (data-model.md "Tree-model example") with expected scores and alarms."""
    scores, alarms = run_scorer(exe, df)
    ts_us = np.rint((df["ts"].to_numpy() - df["ts"].iloc[0]) * 1e6).astype(np.int64)
    frames = [
        [int(t), int(i), int(d), [int(b) for b in row]]
        for t, i, d, row in zip(
            ts_us, df["can_id"], df["dlc"], df[PAYLOAD].to_numpy(np.uint8), strict=True
        )
    ]
    return {
        "source": source,
        "generator": generator,
        "frames": frames,
        "expected_scores": score_bits(scores),
        "expected_alarms": [int(i) for i in np.flatnonzero(alarms)],
    }


def check_example(exe: Path, example: dict) -> str | None:
    """None if the C chain reproduces the example bit-exactly, else the first difference."""
    scores, alarms = run_scorer(exe, frames_from_example(example))
    got = score_bits(scores)
    want = example["expected_scores"]
    if len(got) != len(want):
        return f"{len(got)} scores, expected {len(want)}"
    for i, (g, w) in enumerate(zip(got, want, strict=True)):
        if g != w:
            return f"score of frame {i} is {g}, expected {w}"
    got_alarms = [int(i) for i in np.flatnonzero(alarms)]
    if got_alarms != list(example["expected_alarms"]):
        want_alarms = list(example["expected_alarms"])
        return f"alarms at frames {got_alarms[:5]}, expected {want_alarms[:5]} (first five)"
    return None
