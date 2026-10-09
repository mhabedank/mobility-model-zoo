"""Common CAN frame format for the CAN intrusion detection task (feature 005, T034).

Both CAN models (picket-forest, picket-mlp) read their datasets through this module, so a
benchmark split can be written once and scored by either model. One row per frame:

    ts_us:int64 | can_id:int32 | dlc:int8 | b0..b7:uint8 | label:int8 | capture:str | vehicle:str

`label` is 1 for an attack frame, 0 for a benign frame. `capture` names the source recording
(`<set>/<split>/<capture>` for can-train-and-test, `ambient/<file>` or `attacks/<file>` for ROAD),
`vehicle` the vehicle if the dataset says so (empty otherwise).

Readers yield one DataFrame per capture, because a full dataset does not fit in memory.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd

PAYLOAD = [f"b{i}" for i in range(8)]
COLUMNS = ["ts_us", "can_id", "dlc", *PAYLOAD, "label", "capture", "vehicle"]
DTYPES = {
    "ts_us": np.int64,
    "can_id": np.int32,
    "dlc": np.int8,
    **{c: np.uint8 for c in PAYLOAD},
    "label": np.int8,
    "capture": object,
    "vehicle": object,
}

_CANDUMP = re.compile(rb"\(\s*([0-9.]+)\)\s+\S+\s+([0-9A-Fa-f]{1,8})#([0-9A-Fa-f]*)")


def _frame(
    ts_us: np.ndarray,
    can_id: np.ndarray,
    dlc: np.ndarray,
    payload: np.ndarray,
    label: np.ndarray,
    capture: str,
    vehicle: str = "",
) -> pd.DataFrame:
    df = pd.DataFrame({"ts_us": ts_us, "can_id": can_id, "dlc": dlc})
    for i, c in enumerate(PAYLOAD):
        df[c] = payload[:, i]
    df["label"] = label
    df["capture"] = capture
    df["vehicle"] = vehicle
    return df.astype(DTYPES)[COLUMNS]


# ----------------------------------------------------------------- ROAD --


def read_candump(path: str | Path, capture: str | None = None) -> pd.DataFrame:
    """candump log lines `(ts) iface ID#DATA` -> frames with label 0."""
    ts, ids, dlc, data = [], [], [], []
    with open(path, "rb") as fh:
        for m in _CANDUMP.finditer(fh.read()):
            payload = bytes.fromhex(m.group(3).decode()[:16])
            ts.append(float(m.group(1)))
            ids.append(int(m.group(2), 16))
            dlc.append(len(payload))
            data.append(payload.ljust(8, b"\0"))
    payload = np.frombuffer(b"".join(data), dtype=np.uint8).reshape(-1, 8)
    return _frame(
        np.rint(np.array(ts, dtype=np.float64) * 1e6).astype(np.int64),
        np.array(ids, dtype=np.int64),
        np.array(dlc, dtype=np.int64),
        payload,
        np.zeros(len(ts), np.int8),
        capture or Path(path).name,
    )


def road_labels(df: pd.DataFrame, meta: dict) -> np.ndarray:
    """ROAD attack labels: frames inside the injection interval that carry the injected ID
    (any ID for fuzzing) are attacks."""
    t = df["ts_us"].to_numpy() / 1e6
    y = np.zeros(len(t), np.int8)
    interval = meta.get("injection_interval") or meta.get("injection_time") or meta.get("interval")
    if not interval:
        return y
    t0 = t[0] if len(t) else 0.0
    start, end = float(interval[0]), float(interval[1])
    rel = t - t0 if start < 1e6 else t  # relative or absolute timestamps
    inside = (rel >= start) & (rel <= end)
    inj = meta.get("injection_id")
    if inj in (None, "", "XXX", "random"):
        y[inside] = 1
    else:
        ids = inj if isinstance(inj, list) else [inj]
        ids = [int(str(i), 16) if isinstance(i, str) else int(i) for i in ids]
        y[inside & np.isin(df["can_id"].to_numpy(), ids)] = 1
    return y


def road_root(directory: str | Path) -> Path:
    """The folder of a ROAD download that holds `ambient/` and `attacks/`."""
    hits = [
        p
        for p in Path(directory).rglob("attacks")
        if p.is_dir() and (p / "capture_metadata.json").exists()
    ]
    if not hits:
        raise FileNotFoundError(f"no ROAD capture metadata under {directory}: zoo data download road")
    return hits[0].parent


def from_road(directory: str | Path, max_bytes: float | None = None) -> Iterator[pd.DataFrame]:
    """ROAD captures, ambient (benign) first, then attacks with labels from the metadata.

    `max_bytes` skips larger ambient logs (keeps CI time and memory bounded).
    """
    root = road_root(directory)
    meta = json.loads((root / "attacks" / "capture_metadata.json").read_text())
    for p in sorted((root / "ambient").glob("*.log")):
        if max_bytes is None or p.stat().st_size < max_bytes:
            yield read_candump(p, f"ambient/{p.name}")
    for p in sorted((root / "attacks").glob("*.log")):
        df = read_candump(p, f"attacks/{p.name}")
        df["label"] = road_labels(df, meta.get(p.stem) or meta.get(p.name) or {})
        yield df


# --------------------------------------------------- can-train-and-test --


def from_can_train_and_test(directory: str | Path) -> Iterator[pd.DataFrame]:
    """can-train-and-test captures under `<directory>/<set>/<split>/` (Parquet from
    an older conversion, or the CSV files of `zoo data download`)."""
    from mobility_model_zoo.security.can_ids.can_train_and_test import parse_csv, vehicle_of

    root = Path(directory)
    for set_dir in sorted(p for p in root.glob("set_*") if p.is_dir()):
        for split_dir in sorted(p for p in set_dir.iterdir() if p.is_dir()):
            files = sorted(split_dir.glob("*.parquet")) or sorted(split_dir.glob("*.csv"))
            for f in files:
                raw = pd.read_parquet(f) if f.suffix == ".parquet" else parse_csv(f.read_bytes())
                yield _frame(
                    np.rint(raw["ts"].to_numpy(np.float64) * 1e6).astype(np.int64),
                    raw["can_id"].to_numpy(),
                    raw["dlc"].to_numpy(),
                    raw[PAYLOAD].to_numpy(np.uint8),
                    raw["label"].to_numpy(),
                    f"{set_dir.name}/{split_dir.name}/{f.stem}",
                    vehicle_of(set_dir.name, split_dir.name),
                )


# ---------------------------------------------------------------- output --


def validate(df: pd.DataFrame) -> None:
    if list(df.columns) != COLUMNS:
        raise ValueError(f"frame columns {list(df.columns)} != {COLUMNS}")
    for col, dtype in DTYPES.items():
        if dtype is not object and df[col].dtype != np.dtype(dtype):
            raise ValueError(f"column {col} has dtype {df[col].dtype}, expected {np.dtype(dtype)}")
    if not df["label"].isin([0, 1]).all():
        raise ValueError("label must be 0 or 1")


def write_parquet(df: pd.DataFrame, path: str | Path) -> Path:
    """Write frames in the common format; refuses anything else."""
    validate(df)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def to_arrays(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Frames -> the arrays the feature code works on: t (s), id, dlc, data[n, 8]."""
    return {
        "t": df["ts_us"].to_numpy(np.int64) / 1e6,
        "id": df["can_id"].to_numpy(np.int64),
        "dlc": df["dlc"].to_numpy(np.int64),
        "data": df[PAYLOAD].to_numpy(np.uint8),
    }
