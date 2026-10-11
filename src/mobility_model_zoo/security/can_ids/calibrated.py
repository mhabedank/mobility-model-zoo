"""Per-vehicle calibration and vehicle-relative frame features for picket-forest 0.2.0.

A device first gets a fixed table learned from benign traffic of its vehicle (research R1 of
feature 010): per CAN ID the median interval, a count window of max(0.25 s, 4 periods), the largest
frame count seen in that window and the usual DLC, plus the set of known IDs and the bus frame rate.
Frame features are expressed relative to this table, so a model trained on some vehicles applies to
another vehicle once that vehicle is calibrated.

The features and the event decision are computed by the C library `msml_cal`
(firmware/components/can_features/msml_cal.c), the same code that runs on the device; Python calls
it through ctypes, so host and device values are identical. Counts use 8 time buckets per ID;
times are integer microseconds; ratios are rounded to 1/256. The table is learned here (host).

The pure-numpy equivalent that users run (no compiler, no repository) is
`picket_forest.py`; this module keeps the C path as the parity oracle of the release export
and the tests (feature 013). Table, calibrate, rules and the constants live there and are
re-exported here.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np

from mobility_model_zoo.edge.paths import BUILD_DIR, REPO_ROOT
from mobility_model_zoo.security.can_ids.picket_forest import (  # noqa: F401  (re-exports)
    BUCKETS,
    ENTRY,
    FEATURE_NAMES,
    MAX_IDS,
    MIN_FRAMES,
    MIN_WINDOW_US,
    RULES_MARGIN,
    WINDOW_PERIODS,
    Table,
    bucket_counts,
    calibrate,
    rules,
    to_us,
)

FEATURES_DIR = REPO_ROOT / "firmware" / "components" / "can_features"
C_FILE = FEATURES_DIR / "msml_cal.c"
H_FILE = FEATURES_DIR / "include" / "msml_cal.h"

CONFIRM = 2  # event decision: model flags of an ID before its episode spreads
MARGIN = 0.5  # event decision: count above the calibrated maximum by 50 %


@lru_cache(maxsize=1)
def _lib() -> ctypes.CDLL:
    digest = hashlib.sha256(C_FILE.read_bytes() + H_FILE.read_bytes()).hexdigest()[:12]
    cache = Path(os.environ.get("MMZ_CTYPES_CACHE", BUILD_DIR / "ctypes"))
    cache.mkdir(parents=True, exist_ok=True)
    so = cache / f"libmsml_cal_{digest}.so"
    if not so.exists():
        cc = os.environ.get("CC", "cc")
        flags = ["-O2", "-ffp-contract=off", "-shared", "-fPIC", "-DMSML_CAL_HOST"]
        subprocess.run([cc, *flags, "-I", str(H_FILE.parent), str(C_FILE), "-o", str(so)], check=True)
    lib = ctypes.CDLL(str(so))
    lib.msml_cal_batch.restype = ctypes.c_int
    lib.msml_cal_batch.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.c_float,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_void_p,
    ]
    return lib


def _batch(cap: dict, table: Table, model_flags: np.ndarray | None, confirm: int, margin: float):
    n = cap["ts"].size
    x = np.zeros((n, len(FEATURE_NAMES)), dtype=np.float32)
    ev = np.zeros(n, dtype=np.uint8) if model_flags is not None else None
    if n == 0:
        return x, ev
    entries = np.ascontiguousarray(table.entries())
    ts = np.ascontiguousarray(to_us(cap["ts"]))
    ids = np.ascontiguousarray(cap["can_id"], dtype=np.uint32)
    dlc = np.ascontiguousarray(cap["dlc"], dtype=np.uint8)
    data = np.ascontiguousarray(cap["data"], dtype=np.uint8)
    mf = None if model_flags is None else np.ascontiguousarray(model_flags, dtype=np.uint8)
    rc = _lib().msml_cal_batch(
        entries.ctypes.data,
        len(entries),
        float(np.float32(table.bus_rate)),
        ts.ctypes.data,
        ids.ctypes.data,
        dlc.ctypes.data,
        data.ctypes.data,
        n,
        x.ctypes.data,
        None if mf is None else mf.ctypes.data,
        confirm,
        margin,
        None if ev is None else ev.ctypes.data,
    )
    if rc != 0:
        raise MemoryError("msml_cal_batch failed")
    return x, ev


def features(cap: dict, table: Table) -> np.ndarray:
    """Vehicle-relative features of every frame of a capture (float32, n x len(FEATURE_NAMES))."""
    return _batch(cap, table, None, CONFIRM, MARGIN)[0]


def event_flags(
    cap: dict,
    x: np.ndarray,
    table: Table,
    model_flags: np.ndarray,
    confirm: int = CONFIRM,
    margin: float = MARGIN,
) -> np.ndarray:
    """Event-level decision on top of the model's frame flags (msml_cal_event): spread over an
    ID's injection episode once the model flagged `confirm` frames of it within its window and its
    count stays `margin` above the calibrated maximum; fuzzing state (several unknown IDs)."""
    return _batch(cap, table, np.asarray(model_flags).astype(np.uint8), confirm, margin)[1].astype(
        np.float32
    )
