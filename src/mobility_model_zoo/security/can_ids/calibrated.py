"""Per-vehicle calibration and vehicle-relative frame features for picket-forest 0.2.0.

A device first learns a fixed table from benign traffic of its vehicle (research R1 of feature
010): per CAN ID the median interval, the usual DLC and the largest number of frames seen in a
time window, plus the set of known IDs and the bus frame rate. Frame features are then expressed
relative to this table, so a model trained on some vehicles applies to another vehicle once that
vehicle is calibrated.

Rates are measured as frame counts in time windows of at least `MIN_WINDOW_S`, not as single
inter-frame gaps: counts are robust to logger timestamp jitter and batching (can-train-and-test
attack captures carry compressed timestamps; commaCarSegments logs in 10 ms batches).

Every feature is computable in a streaming way with bounded state (a ring of recent timestamps per
ID, counters of unknown IDs over the last bus frames); no raw CAN ID, no absolute time and no
bus-level inter-frame gap is a feature.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MIN_WINDOW_S = 0.25  # count window per ID: max(MIN_WINDOW_S, WINDOW_PERIODS x median interval)
WINDOW_PERIODS = 4
W_BUS = 256  # bus frames for the short unknown-ID count and the bus rate
W_BUS_LONG = 2048  # bus frames for the long unknown-ID count
MIN_FRAMES = 5  # an ID needs this many benign frames to get a period
LOG_CAP = 8.0  # log2 ratios are clipped to +-LOG_CAP

FEATURE_NAMES = [
    "known_id",
    "log_dt_period",  # log2(interval to the previous frame of this ID / calibrated median interval)
    "log_count_ratio",  # log2((frames of this ID in its window + 1) / (calibrated max + 1))
    "count_excess",  # frames of this ID in its window minus the calibrated maximum
    "dlc_changed_cal",  # DLC differs from the calibrated DLC of this ID
    "hamming",  # bits changed against the previous frame of this ID
    "bytes_changed",
    "unknown_count",  # unknown-ID frames among the last W_BUS bus frames
    "unknown_count_long",  # unknown-ID frames among the last W_BUS_LONG bus frames
    "log_bus_rate",  # log2(bus rate over the last W_BUS frames / calibrated bus rate)
]


@dataclass
class Table:
    """Calibration table of one vehicle."""

    period: dict[int, float] = field(default_factory=dict)  # median interval, s
    window: dict[int, float] = field(default_factory=dict)  # count window, s
    max_count: dict[int, int] = field(default_factory=dict)  # most frames seen in the window
    dlc: dict[int, int] = field(default_factory=dict)
    bus_rate: float = 0.0  # frames per second
    seconds: float = 0.0  # benign time used

    @property
    def known(self) -> set[int]:
        return set(self.dlc)


def _window(period: float | None) -> float:
    return MIN_WINDOW_S if period is None else max(MIN_WINDOW_S, WINDOW_PERIODS * period)


def _counts(ts: np.ndarray, window: float) -> np.ndarray:
    """Frames in (t - window, t] for every frame of one ID (ts sorted)."""
    return np.arange(ts.size) - np.searchsorted(ts, ts - window, side="right") + 1


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
        yield ts, ids, dlc


def calibrate(caps: list[dict], max_seconds: float | None = None) -> Table:
    """Learn the table from benign captures only (a capture with attack frames is refused)."""
    t = Table()
    parts = list(_trim(caps, max_seconds))
    intervals: dict[int, list[np.ndarray]] = {}
    dlcs: dict[int, list[np.ndarray]] = {}
    frames = 0
    for ts, ids, dlc in parts:
        t.seconds += float(ts[-1] - ts[0])
        frames += ts.size
        for i in np.unique(ids):
            sel = ids == i
            intervals.setdefault(int(i), []).append(np.diff(ts[sel]))
            dlcs.setdefault(int(i), []).append(dlc[sel])
    for i, d in intervals.items():
        d = np.concatenate(d)
        t.dlc[i] = int(np.bincount(np.concatenate(dlcs[i])).argmax())
        if d.size >= MIN_FRAMES:
            t.period[i] = float(np.median(d))
        t.window[i] = _window(t.period.get(i))
    for ts, ids, _ in parts:
        for i in np.unique(ids):
            c = int(_counts(ts[ids == i], t.window[int(i)]).max())
            t.max_count[int(i)] = max(t.max_count.get(int(i), 0), c)
    t.bus_rate = frames / t.seconds if t.seconds > 0 else 0.0
    return t


def _log_ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.log2(num / den)
    r[~np.isfinite(r)] = LOG_CAP
    return np.clip(r, -LOG_CAP, LOG_CAP)


def _window_sum(flags: np.ndarray, w: int) -> np.ndarray:
    csum = np.r_[0.0, np.cumsum(flags)]
    idx = np.arange(flags.size)
    return csum[idx + 1] - csum[np.maximum(idx + 1 - w, 0)]


def features(cap: dict, table: Table) -> np.ndarray:
    """Vehicle-relative features of every frame of a capture (float32, n x len(FEATURE_NAMES))."""
    ts = cap["ts"]
    ids = cap["can_id"].astype(np.int64)
    dlc = cap["dlc"].astype(np.int64)
    data = cap["data"]
    n = ts.size
    known = np.fromiter((i in table.dlc for i in ids), bool, n)
    period = np.fromiter((table.period.get(int(i), np.nan) for i in ids), float, n)
    cal_dlc = np.fromiter((table.dlc.get(int(i), -1) for i in ids), int, n)
    max_count = np.fromiter((table.max_count.get(int(i), 0) for i in ids), float, n)

    prev = np.full(n, -1)
    count = np.zeros(n)
    for i in np.unique(ids):
        idx = np.flatnonzero(ids == i)
        prev[idx[1:]] = idx[:-1]
        count[idx] = _counts(ts[idx], table.window.get(int(i), MIN_WINDOW_S))
    has_prev = prev >= 0
    dt = np.where(has_prev, ts - ts[np.maximum(prev, 0)], np.nan)

    x = np.zeros((n, len(FEATURE_NAMES)), np.float32)
    x[:, 0] = known
    x[:, 1] = np.where(has_prev & np.isfinite(period), _log_ratio(dt, period), LOG_CAP)
    x[:, 2] = np.where(known, _log_ratio(count + 1, max_count + 1), 0.0)
    x[:, 3] = np.where(known, count - max_count, 0.0)
    x[:, 4] = (cal_dlc >= 0) & (cal_dlc != dlc)
    diff = np.where(has_prev[:, None], data ^ data[np.maximum(prev, 0)], 0).astype(np.uint8)
    x[:, 5] = np.unpackbits(diff, axis=1).sum(axis=1)
    x[:, 6] = (diff != 0).sum(axis=1)
    unk = (~known).astype(np.float64)
    x[:, 7] = _window_sum(unk, W_BUS)
    x[:, 8] = _window_sum(unk, W_BUS_LONG)
    back = np.arange(n) - W_BUS
    bspan = np.where(back >= 0, ts - ts[np.maximum(back, 0)], np.nan)
    rate = np.full(n, table.bus_rate or np.nan)
    x[:, 9] = np.where(back >= 0, _log_ratio(W_BUS / bspan, rate), 0.0)
    return x


def rules(x: np.ndarray, margin: float = 0.25) -> np.ndarray:
    """Rules-only baseline on the same table: rate above the calibrated maximum (with a margin),
    several unknown IDs in a short span (fuzzing state) or a DLC change."""
    over = x[:, 2] > np.log2(1 + margin)
    fuzz = (x[:, 7] >= 3) | (x[:, 8] >= 8)
    return (over | fuzz | (x[:, 4] == 1)).astype(np.float32)
