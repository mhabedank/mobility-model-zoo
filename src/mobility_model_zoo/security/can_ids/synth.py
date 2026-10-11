"""Synthetic CAN traffic with one injected attack (feature 007, research R8).

Used for the published examples of picket-forest and for tests: no recorded dataset frame may be
published (ROAD and can-train-and-test have `redistribution: unclear`), but the examples must still
exercise every feature and the alarm stage. Deterministic per seed.

Benign traffic: a set of periodic identifiers (10-100 ms periods, about 2 % jitter) whose payloads
carry a rolling counter, a slowly changing signal and a checksum byte. Attacks:

- `fabrication`: extra frames on an existing identifier with a changed payload (spoofed signal);
- `dos`: identifier 0x000 every 0.2 ms;
- `fuzzing`: random identifiers and payloads every 0.5 ms;
- `scan`: sequential identifiers every 1 ms.

Output columns follow `can_train_and_test.parse_csv`: `ts` (s), `can_id`, `dlc`, `b0..b7`, `label`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ATTACKS = ("fabrication", "dos", "fuzzing", "scan")
PAYLOAD = [f"b{i}" for i in range(8)]


def _benign(rng: np.random.Generator, duration_s: float, n_ids: int = 12) -> list[tuple]:
    ids = rng.choice(np.arange(0x080, 0x700), size=n_ids, replace=False)
    periods = rng.choice([0.01, 0.02, 0.05, 0.1], size=n_ids)
    rows = []
    for can_id, period in zip(ids, periods, strict=True):
        t, counter, signal = float(rng.uniform(0, period)), 0, int(rng.integers(0, 200))
        while t < duration_s:
            signal = int(np.clip(signal + rng.integers(-2, 3), 0, 255))
            data = [counter & 0xFF, signal, signal >> 1, 0x10, 0x00, 0x00, int(can_id) & 0xFF]
            data.append(sum(data) & 0xFF)
            rows.append((t, int(can_id), 8, data, 0))
            counter += 1
            t += period * (1 + rng.normal(0, 0.02))
    return rows


def _attack(rng: np.random.Generator, attack: str, start: float, stop: float, rows: list) -> list:
    out = []
    if attack == "fabrication":
        target = rows[int(rng.integers(len(rows)))][1]
        t = start
        while t < stop:
            out.append((t, target, 8, [0xFF, 0xFF, 0x7F, 0x10, 0, 0, target & 0xFF, 0x00], 1))
            t += 0.002
    elif attack == "dos":
        t = start
        while t < stop:
            out.append((t, 0x000, 8, [0] * 8, 1))
            t += 0.0002
    elif attack == "fuzzing":
        t = start
        while t < stop:
            out.append((t, int(rng.integers(0, 0x800)), 8, rng.integers(0, 256, 8).tolist(), 1))
            t += 0.0005
    elif attack == "scan":
        t, can_id = start, 0
        while t < stop and can_id < 0x800:
            out.append((t, can_id, 8, [0] * 8, 1))
            can_id += 1
            t += 0.001
    else:
        raise ValueError(f"unknown attack {attack!r}; choose one of {ATTACKS}")
    return out


def generate(attack: str, n_frames: int = 2000, seed: int = 0) -> pd.DataFrame:
    """About `n_frames` frames of benign traffic with one attack episode in the middle third."""
    rng = np.random.default_rng(seed)
    rows: list = []
    duration = 1.0
    while len(rows) < n_frames:  # grow until the benign traffic is long enough
        duration *= 1.5
        rows = _benign(np.random.default_rng(seed), duration)
    rows.sort(key=lambda r: r[0])
    end = rows[int(n_frames * 0.8)][0]  # the attack ends well before the cut at n_frames
    start = end * (0.4 + 0.1 * rng.random())
    rows += _attack(rng, attack, start, start + end * 0.05, rows)
    rows.sort(key=lambda r: r[0])
    rows = rows[:n_frames]
    df = pd.DataFrame(
        {
            "ts": np.array([r[0] for r in rows], dtype=np.float64),
            "can_id": np.array([r[1] for r in rows], dtype=np.uint16),
            "dlc": np.array([r[2] for r in rows], dtype=np.uint8),
        }
    )
    payload = np.array([r[3] for r in rows], dtype=np.uint8)
    for i, c in enumerate(PAYLOAD):
        df[c] = payload[:, i]
    df["label"] = np.array([r[4] for r in rows], dtype=np.uint8)
    return df
