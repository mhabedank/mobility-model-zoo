"""picket-forest for Python users: calibrate, score, alarm (feature 013).

This is the Python reference of the picket-forest chain that runs on the device: a per-vehicle
calibration table learned from benign traffic, ten frame features relative to it, the rules that
decide, the alarm stage, and the forest score reported as information. It needs numpy, joblib and
scikit-learn only: no C compiler, no repository checkout, no pandas.

The features follow the device code (firmware/components/can_features/msml_cal.c and msml_alarm.c)
operation for operation, so scores and alarms are bit-exact with the device: times are integer
microseconds relative to the first frame, frame counts use 8 time buckets per CAN ID, log ratios are
rounded to 1/256 and stored as float32. The release gate checks this on the example captures, and
the firmware CI job checks it against the C library on recorded captures.

    from mobility_model_zoo.security.can_ids import picket_forest as pf

    model = pf.load_model("model.joblib")
    table = pf.load_table("calibration_table.json")
    capture = pf.load_capture("examples/01-fabrication.json")
    scores, alarms = pf.score(capture, table, model)
    print(pf.summary(capture, scores, alarms))

A capture is a dict of numpy arrays in bus order: `ts` (seconds), `can_id`, `dlc`, `data` (n x 8
bytes) and `y` (labels; zeros for benign traffic).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

FORMAT = "picket-forest-v2"
TABLE_FORMAT = "picket-forest-table-v1"

MIN_WINDOW_US = 250_000
WINDOW_PERIODS = 4
BUCKETS = 8
MIN_FRAMES = 5  # an ID needs this many benign frames to get a period
MAX_IDS = 128  # MSML_CAL_MAX_IDS
RULES_MARGIN = 0.25  # rules-only baseline: 25 % (fixed when the baseline was defined)
LOG_CAP = 8.0  # MSML_CAL_LOG_CAP
W_BUS = 256  # MSML_CAL_W_BUS
W_BUS_LONG = 2048  # MSML_CAL_W_BUS_LONG
UNKNOWN_RING = 64  # MSML_CAL_UNKNOWN_RING
MAX_SPAN_US = 2_000_000  # MSML_CAL_MAX_SPAN_US
ALARM_MAX_K = 16  # MSML_ALARM_MAX_K

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

_CANDUMP = re.compile(rb"\(\s*([0-9.]+)\)\s+\S+\s+([0-9A-Fa-f]{1,8})#([0-9A-Fa-f]*)")
_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


# ------------------------------------------------------------------------------ calibration --


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


def device_bus_rate(bus_rate: float) -> float:
    """The bus rate the device compares against: the float32 the table header encodes.

    The header writes the rate as the smallest float32 literal above the calibrated value (the
    literal form used for split thresholds), one float32 step above `Table.bus_rate`.
    """
    with np.errstate(all="ignore"):
        a = np.float32(bus_rate)
        if float(a) > bus_rate:
            a = np.nextafter(a, np.float32(-np.inf))
        return float(np.nextafter(a, np.float32(np.inf)))


# -------------------------------------------------------------------------------- features --


def _q_log2(num: np.ndarray, den: np.ndarray | float) -> np.ndarray:
    """log2(num / den) rounded to 1/256 and clipped to +-LOG_CAP; non-finite -> +LOG_CAP."""
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = np.log2(np.asarray(num, dtype=np.float64) / np.asarray(den, dtype=np.float64))
    finite = np.isfinite(r)
    r = np.floor(np.where(finite, r, 0.0) * 256.0 + 0.5) / 256.0
    r = np.clip(r, -LOG_CAP, LOG_CAP)
    return np.where(finite, r, LOG_CAP).astype(np.float32)


def features(cap: dict, table: Table, bus_rate: float | None = None) -> np.ndarray:
    """The ten calibrated features of every frame (float32, n x 10), as msml_cal_update computes them.

    Frames must be in bus order (non-decreasing timestamps). `bus_rate` is the calibrated rate the
    bus-rate feature compares against; the default is the value the device's table header encodes.
    """
    ts = to_us(cap["ts"]) if len(cap["ts"]) else np.zeros(0, np.int64)
    n = ts.size
    x = np.zeros((n, len(FEATURE_NAMES)), dtype=np.float32)
    if n == 0:
        return x
    if np.any(np.diff(ts) < 0):
        raise ValueError("frames must be in bus order (timestamps never decrease)")
    ids = np.asarray(cap["can_id"]).astype(np.int64)
    dlc = np.asarray(cap["dlc"]).astype(np.int64)
    data = np.asarray(cap["data"], dtype=np.uint8).reshape(n, 8)
    entries = table.entries()
    rate = device_bus_rate(table.bus_rate) if bus_rate is None else float(np.float32(bus_rate))

    x[:, 1] = LOG_CAP
    known = np.isin(ids, entries["id"].astype(np.int64))
    x[known, 0] = 1.0
    for e in entries:
        idx = np.flatnonzero(ids == int(e["id"]))
        if idx.size == 0:
            continue
        t = ts[idx]
        if e["period_us"] > 0 and idx.size > 1:
            x[idx[1:], 1] = _q_log2(np.diff(t).astype(np.float64), float(e["period_us"]))
        count = bucket_counts(t, int(e["window_us"])).astype(np.int64)
        max_count = int(e["max_count"])
        x[idx, 2] = _q_log2(count + 1.0, max_count + 1.0)
        x[idx, 3] = (count - max_count).astype(np.float32)
        x[idx, 4] = (dlc[idx] != int(e["dlc"])).astype(np.float32)
        if idx.size > 1:
            d = np.bitwise_xor(data[idx[1:]], data[idx[:-1]])
            x[idx[1:], 5] = _POPCOUNT[d].sum(axis=1).astype(np.float32)
            x[idx[1:], 6] = (d != 0).sum(axis=1).astype(np.float32)

    # unknown-ID frames among the last W frames (this one included) within MAX_SPAN, at most the
    # ring size; with timestamps in bus order the counted frames are the most recent unknown ones
    unk = np.flatnonzero(~known)
    if unk.size:
        frame = np.arange(n)
        upper = np.searchsorted(unk, frame, side="right")
        by_time = np.searchsorted(ts[unk], ts - MAX_SPAN_US, side="right")
        for col, w in ((7, W_BUS), (8, W_BUS_LONG)):
            lower = np.maximum(np.searchsorted(unk, frame - w + 1, side="left"), by_time)
            x[:, col] = np.clip(upper - lower, 0, UNKNOWN_RING).astype(np.float32)

    if n > W_BUS:
        span = (ts[W_BUS:] - ts[:-W_BUS]).astype(np.float64)
        with np.errstate(divide="ignore"):
            num = float(W_BUS) * 1e6 / span
        x[W_BUS:, 9] = _q_log2(num, float(np.float32(rate)))
    return x


def rules(x: np.ndarray, margin: float = RULES_MARGIN) -> np.ndarray:
    """Rules-only baseline on the same table: rate above the calibrated maximum (with a margin),
    several unknown IDs (fuzzing state) or a DLC change."""
    over = x[:, 2] > np.log2(1 + margin)
    fuzz = (x[:, 7] >= 3) | (x[:, 8] >= 8)
    return (over | fuzz | (x[:, 4] == 1)).astype(np.float32)


def alarms(
    ts_us: np.ndarray, flagged: np.ndarray, k: int, window_ms: float, holdoff_ms: float = 1000.0
) -> np.ndarray:
    """Alarm stage (msml_alarm.c): 1 where a frame raises an alarm. An alarm needs k flagged frames
    within window_ms; after it, alarms are suppressed for holdoff_ms."""
    ts = np.asarray(ts_us, dtype=np.int64)
    out = np.zeros(ts.size, dtype=np.uint8)
    k = min(max(int(k), 1), ALARM_MAX_K)
    window_us, holdoff_us = int(window_ms * 1000), int(holdoff_ms * 1000)
    ring: list[int] = []
    last_alarm = None
    for i in np.flatnonzero(np.asarray(flagged)):
        t = int(ts[i])
        ring.append(t)
        if len(ring) > k:
            ring.pop(0)
        if len(ring) < k or t - ring[0] > window_us:
            continue
        if last_alarm is not None and t - last_alarm < holdoff_us:
            continue
        last_alarm = t
        out[i] = 1
    return out


def vote_score(clf, X: np.ndarray) -> np.ndarray:
    """Share of trees voting "attack".

    This is what the emlearn C code computes on the device (hard voting per tree), which
    differs from scikit-learn's averaged leaf probabilities.
    """
    votes = np.zeros(X.shape[0], dtype=np.float32)
    for tree in clf.estimators_:
        votes += tree.predict(X).astype(np.float32)
    return votes / len(clf.estimators_)


def score(cap: dict, table: Table, model: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """(float32 forest score, uint8 alarm) per frame. The rules on the calibrated features decide;
    the forest score is information."""
    x = features(cap, table)
    s = vote_score(model["model"], x).astype(np.float32)
    flags = rules(x, model["rules_margin"]) > 0
    a = model["alarm"]
    return s, alarms(to_us(cap["ts"]), flags, a["k"], a["window_ms"], a["holdoff_ms"])


def summary(cap: dict, scores: np.ndarray, alarm: np.ndarray) -> str:
    """One deterministic line: frames, duration, every alarm with its frame and time, top score."""
    ts = to_us(cap["ts"]) if len(cap["ts"]) else np.zeros(0, np.int64)
    hits = np.flatnonzero(alarm)
    seconds = float(ts[-1]) / 1e6 if ts.size else 0.0
    text = f"{ts.size} frames, {seconds:.2f} s; {hits.size} alarm{'' if hits.size == 1 else 's'}"
    if hits.size:
        text += " at " + ", ".join(f"frame {int(i)} (t={ts[i] / 1e6:.3f} s)" for i in hits)
    top = float(np.max(scores)) if np.size(scores) else 0.0
    return text + f"; highest forest score {top:.3f}"


# ---------------------------------------------------------------------------------- files --


def load_model(path: str | Path) -> dict[str, Any]:
    """`model.joblib` of a picket-forest release (scikit-learn forest and decision parameters)."""
    import joblib

    saved = joblib.load(path)
    if not isinstance(saved, dict) or saved.get("format") != FORMAT:
        got = saved.get("format") if isinstance(saved, dict) else type(saved).__name__
        raise ValueError(f"{path}: not a {FORMAT} model file (format {got!r})")
    missing = [k for k in ("model", "threshold", "rules_margin", "alarm") if k not in saved]
    if missing:
        raise ValueError(f"{path}: {FORMAT} model file lacks {', '.join(missing)}")
    return saved


def save_table(table: Table, path: str | Path, note: str = "") -> None:
    """Write the calibration table as JSON (format picket-forest-table-v1)."""
    rows = [
        {
            "id": int(r["id"]),
            "period_us": int(r["period_us"]),
            "window_us": int(r["window_us"]),
            "max_count": int(r["max_count"]),
            "dlc": int(r["dlc"]),
        }
        for r in table.entries()
    ]
    doc = {
        "format": TABLE_FORMAT,
        "note": note,
        "seconds": float(table.seconds),
        "bus_rate": float(np.float32(table.bus_rate)),
        "ids": rows,
    }
    Path(path).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def load_table(path: str | Path) -> Table:
    """Read a calibration table written by `save_table` (or published with a release)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("format") != TABLE_FORMAT:
        raise ValueError(f"{path}: not a {TABLE_FORMAT} file (format {doc.get('format')!r})")
    t = Table(bus_rate=float(np.float32(doc["bus_rate"])), seconds=float(doc.get("seconds", 0.0)))
    for r in doc["ids"]:
        i = int(r["id"])
        if int(r["period_us"]) > 0:
            t.period[i] = int(r["period_us"])
        t.window[i] = int(r["window_us"])
        t.max_count[i] = int(r["max_count"])
        t.dlc[i] = int(r["dlc"])
    return t


_HEADER_ENTRY = re.compile(r"\{0x([0-9A-Fa-f]+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u\}")
_HEADER_RATE = re.compile(r"PICKET_FOREST_BUS_RATE\s*\(\s*([^)\s]+?)f?\s*\)")
_HEADER_MINUTES = re.compile(r"IDs,\s*([0-9.]+)\s*min")


def table_from_header(text: str) -> Table:
    """The calibration table a `picket_forest_table.h` encodes (the inverse of the header writer).

    The header holds the bus rate as the next float32 above the calibrated value, so the rate is
    stepped back; the benign time is only known to the 0.1 min the header comment prints.
    """
    rate = _HEADER_RATE.search(text)
    if rate is None:
        raise ValueError("no PICKET_FOREST_BUS_RATE in the table header")
    t = Table(bus_rate=float(np.nextafter(np.float32(rate.group(1)), np.float32(-np.inf))))
    minutes = _HEADER_MINUTES.search(text)
    t.seconds = float(minutes.group(1)) * 60 if minutes else 0.0
    for m in _HEADER_ENTRY.finditer(text):
        i, period, window, max_count, dlc = int(m.group(1), 16), *(int(m.group(k)) for k in range(2, 6))
        if period > 0:
            t.period[i] = period
        t.window[i] = window
        t.max_count[i] = max_count
        t.dlc[i] = dlc
    if not t.dlc:
        raise ValueError("no table entries in the header")
    return t


def load_capture(path: str | Path) -> dict[str, Any]:
    """An example capture of a release (`examples/*.json`: frames `[ts_us, can_id, dlc, [8 bytes]]`)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    frames = doc["frames"]
    n = len(frames)
    return {
        "id": Path(path).stem,
        "ts": np.array([f[0] for f in frames], dtype=np.float64) / 1e6,
        "can_id": np.array([f[1] for f in frames], dtype=np.uint32),
        "dlc": np.array([f[2] for f in frames], dtype=np.uint8),
        "data": np.array([f[3] for f in frames], dtype=np.uint8).reshape(n, 8),
        "y": np.zeros(n, dtype=np.int8),
    }


def read_candump(path: str | Path, name: str | None = None) -> dict[str, Any]:
    """A candump log (`candump -L`: lines `(ts) iface ID#DATA`) as a capture of benign frames.
    Lines that are not frames are skipped; payloads longer than 8 bytes are cut to 8."""
    ts, ids, dlc, data = [], [], [], []
    with open(path, "rb") as fh:
        for m in _CANDUMP.finditer(fh.read()):
            payload = bytes.fromhex(m.group(3).decode()[:16])
            ts.append(float(m.group(1)))
            ids.append(int(m.group(2), 16))
            dlc.append(len(payload))
            data.append(payload.ljust(8, b"\0"))
    n = len(ts)
    return {
        "id": name or Path(path).name,
        "ts": np.array(ts, dtype=np.float64),
        "can_id": np.array(ids, dtype=np.uint32),
        "dlc": np.array(dlc, dtype=np.uint8),
        "data": np.frombuffer(b"".join(data), dtype=np.uint8).reshape(n, 8).copy(),
        "y": np.zeros(n, dtype=np.int8),
    }
