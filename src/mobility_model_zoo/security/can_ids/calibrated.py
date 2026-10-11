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
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from mobility_model_zoo.edge.paths import BUILD_DIR, REPO_ROOT

FEATURES_DIR = REPO_ROOT / "firmware" / "components" / "can_features"
C_FILE = FEATURES_DIR / "msml_cal.c"
H_FILE = FEATURES_DIR / "include" / "msml_cal.h"

MIN_WINDOW_US = 250_000
WINDOW_PERIODS = 4
BUCKETS = 8
MIN_FRAMES = 5  # an ID needs this many benign frames to get a period
MAX_IDS = 128  # MSML_CAL_MAX_IDS
CONFIRM = 2  # event decision: model flags of an ID before its episode spreads
MARGIN = 0.5  # event decision: count above the calibrated maximum by 50 %
RULES_MARGIN = 0.25  # rules-only baseline: 25 % (fixed when the baseline was defined)

FEATURE_NAMES = [
    "known_id",
    "log_dt_period",  # log2(interval to the previous frame of this ID / calibrated median interval)
    "log_count_ratio",  # log2((frames of this ID in its window + 1) / (calibrated max + 1))
    "count_excess",  # frames of this ID in its window minus the calibrated maximum
    "dlc_changed_cal",  # DLC differs from the calibrated DLC of this ID
    "hamming",  # bits changed against the previous frame of this ID (known IDs)
    "bytes_changed",
    "unknown_count",  # unknown-ID frames among the last 256 bus frames within 2 s (max 64)
    "unknown_count_long",  # unknown-ID frames among the last 2048 bus frames within 2 s (max 64)
    "log_bus_rate",  # log2(bus rate over the last 256 frames / calibrated bus rate)
]

ENTRY = np.dtype(
    [("id", "<u4"), ("period_us", "<u4"), ("window_us", "<u4"), ("max_count", "<u2"), ("dlc", "u1")],
    align=True,
)


@dataclass
class Table:
    """Calibration table of one vehicle."""

    period: dict[int, int] = field(default_factory=dict)  # median interval, us
    window: dict[int, int] = field(default_factory=dict)  # count window, us
    max_count: dict[int, int] = field(default_factory=dict)
    dlc: dict[int, int] = field(default_factory=dict)
    bus_rate: float = 0.0  # frames per second (float32 value)
    seconds: float = 0.0  # benign time used

    @property
    def known(self) -> set[int]:
        return set(self.dlc)

    def entries(self) -> np.ndarray:
        ids = sorted(self.dlc)
        e = np.zeros(len(ids), dtype=ENTRY)
        for k, i in enumerate(ids):
            e[k] = (
                i,
                self.period.get(i, 0),
                self.window[i],
                min(self.max_count[i], 0xFFFF),
                self.dlc[i],
            )
        return e


def to_us(ts: np.ndarray) -> np.ndarray:
    """Seconds (absolute) -> integer microseconds relative to the first frame."""
    ts = np.asarray(ts, dtype=np.float64)
    return np.rint((ts - ts[0]) * 1e6).astype(np.int64)


def _window(period_us: int) -> int:
    return max(MIN_WINDOW_US, WINDOW_PERIODS * period_us)


def bucket_counts(ts_us: np.ndarray, window_us: int) -> np.ndarray:
    """Frames of one ID in the current and the 7 previous buckets (ts sorted), as in msml_cal.c."""
    b = np.floor_divide(ts_us, window_us // BUCKETS)
    return np.arange(b.size) - np.searchsorted(b, b - (BUCKETS - 1), side="left") + 1


def _trim(caps: list[dict], max_seconds: float | None):
    used = 0.0
    for c in caps:
        ts, ids, dlc, y = c["ts"], c["can_id"].astype(np.int64), c["dlc"], c["y"]
        if max_seconds is not None:
            left = max_seconds - used
            if left <= 0:
                return
            keep = ts - ts[0] <= left
            ts, ids, dlc, y = ts[keep], ids[keep], dlc[keep], y[keep]
        if ts.size < 2:
            continue
        if np.any(y != 0):
            raise ValueError(f"calibration capture {c.get('id')} contains attack frames")
        used += float(ts[-1] - ts[0])
        yield to_us(ts), ids, dlc


def calibrate(caps: list[dict], max_seconds: float | None = None) -> Table:
    """Learn the table from benign captures only (a capture with attack frames is refused)."""
    t = Table()
    parts = list(_trim(caps, max_seconds))
    intervals: dict[int, list[np.ndarray]] = {}
    dlcs: dict[int, list[np.ndarray]] = {}
    counts: dict[int, int] = {}
    frames = 0
    for ts, ids, dlc in parts:
        t.seconds += float(ts[-1] - ts[0]) / 1e6
        frames += ts.size
        for i in np.unique(ids):
            sel = ids == i
            intervals.setdefault(int(i), []).append(np.diff(ts[sel]))
            dlcs.setdefault(int(i), []).append(dlc[sel])
            counts[int(i)] = counts.get(int(i), 0) + int(sel.sum())
    keep = sorted(counts, key=lambda i: -counts[i])[:MAX_IDS]  # the table holds at most MAX_IDS IDs
    for i in keep:
        d = np.concatenate(intervals[i])
        t.dlc[i] = int(np.bincount(np.concatenate(dlcs[i])).argmax())
        if d.size >= MIN_FRAMES:
            t.period[i] = int(np.floor(np.median(d) + 0.5))
        t.window[i] = _window(t.period.get(i, 0))
    for ts, ids, _ in parts:
        for i in np.unique(ids):
            if int(i) in t.window:
                c = int(bucket_counts(ts[ids == i], t.window[int(i)]).max())
                t.max_count[int(i)] = max(t.max_count.get(int(i), 0), c)
    t.bus_rate = float(np.float32(frames / t.seconds)) if t.seconds > 0 else 0.0
    return t


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


def rules(x: np.ndarray, margin: float = RULES_MARGIN) -> np.ndarray:
    """Rules-only baseline on the same table: rate above the calibrated maximum (with a margin),
    several unknown IDs (fuzzing state) or a DLC change."""
    over = x[:, 2] > np.log2(1 + margin)
    fuzz = (x[:, 7] >= 3) | (x[:, 8] >= 8)
    return (over | fuzz | (x[:, 4] == 1)).astype(np.float32)
