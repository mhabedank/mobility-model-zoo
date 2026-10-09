"""Metrics for frame-level intrusion detection, including operational false-alarm rates."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
)

GRACE_S = 1.0  # an alarm up to 1 s after an episode still detects it (benchmark protocol)
EPISODE_GAP_S = 1.0
ALARM_GRID = [(k, w) for k in (1, 2, 3, 5, 8) for w in (50, 200, 1000)]
ALARM_HOLDOFF_MS = 1000


def alarm_events(ts: np.ndarray, flagged: np.ndarray, merge_s: float = 1.0) -> int:
    """Count alarm events: flagged frames closer than merge_s seconds count as one event."""
    t = ts[flagged.astype(bool)]
    if t.size == 0:
        return 0
    return int(1 + np.count_nonzero(np.diff(t) > merge_s))


def frame_metrics(y: np.ndarray, score: np.ndarray, threshold: float = 0.5) -> dict:
    pred = score >= threshold
    out = {
        "frames": int(y.size),
        "attack_frames": int(y.sum()),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "fpr": float(np.mean(pred[y == 0])) if np.any(y == 0) else float("nan"),
        "mcc": float(matthews_corrcoef(y, pred)) if 0 < y.sum() < y.size else float("nan"),
    }
    out["auc_pr"] = float(average_precision_score(y, score)) if 0 < y.sum() < y.size else float("nan")
    return out


def false_alarms_per_hour(
    captures: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    threshold: float = 0.5,
    merge_s: float = 1.0,
) -> float:
    """False alarm events per hour over benign frames.

    captures: list of (ts_seconds, y, score). Only benign frames are considered; a false alarm
    event is a cluster of benign frames flagged within merge_s seconds.
    """
    events, seconds = 0, 0.0
    for ts, y, score in captures:
        benign = y == 0
        events += alarm_events(ts[benign], score[benign] >= threshold, merge_s)
        seconds += float(ts[-1] - ts[0]) if ts.size > 1 else 0.0
    return events / (seconds / 3600.0) if seconds > 0 else float("nan")


def attack_episodes(ts: np.ndarray, y: np.ndarray, gap_s: float = 1.0) -> list[tuple[float, float]]:
    """Group attack frames into episodes; a gap longer than gap_s starts a new episode."""
    t = ts[y == 1]
    if t.size == 0:
        return []
    cut = np.flatnonzero(np.diff(t) > gap_s)
    starts = np.r_[t[0], t[cut + 1]]
    ends = np.r_[t[cut], t[-1]]
    return list(zip(starts.tolist(), ends.tolist(), strict=False))


def alarm_metrics(
    captures: list[tuple[np.ndarray, np.ndarray, np.ndarray]], grace_s: float = 1.0
) -> dict:
    """Event-level metrics for alarms.

    captures: list of (ts_seconds, y, alarm). An alarm is true if it falls inside an attack
    episode or up to grace_s after it ends: while an attack runs, the detector may also flag the
    legitimate frames whose timing the attack disturbs, and that is not a false alarm in
    operation. An episode is detected if a true alarm falls inside [start, end + grace_s].
    """
    false_alarms, seconds, episodes, detected, latencies = 0, 0.0, 0, 0, []
    for ts, y, alarm in captures:
        seconds += float(ts[-1] - ts[0]) if ts.size > 1 else 0.0
        t_alarm = ts[alarm.astype(bool)]
        eps = attack_episodes(ts, y)
        ok = np.zeros(t_alarm.size, dtype=bool)
        for start, end in eps:
            inside = (t_alarm >= start) & (t_alarm <= end + grace_s)
            ok |= inside
            episodes += 1
            if inside.any():
                detected += 1
                latencies.append(float(t_alarm[inside][0] - start))
        false_alarms += int(np.count_nonzero(~ok))
    hours = seconds / 3600.0
    return {
        "episodes": episodes,
        "episode_recall": detected / episodes if episodes else float("nan"),
        "median_latency_ms": float(np.median(latencies) * 1000) if latencies else float("nan"),
        "p95_latency_ms": float(np.percentile(latencies, 95) * 1000) if latencies else float("nan"),
        "false_alarms_per_hour": false_alarms / hours if hours > 0 else float("nan"),
    }


def recall_at_fpr(y: np.ndarray, score: np.ndarray, benign_val_scores: np.ndarray, fpr: float = 0.001) -> float:
    """Attack-class recall at the threshold that gives `fpr` on benign validation frames.

    The threshold comes from validation data passed in by the caller, never from the test frames.
    """
    thr = float(np.quantile(np.asarray(benign_val_scores, dtype=np.float64), 1.0 - fpr))
    attacks = score[y == 1]
    return float(np.mean(attacks > thr)) if attacks.size else float("nan")


def budget_operating_point(
    val_caps: list[dict], val_scores: list[np.ndarray], thr: float, budget_per_hour: float
) -> dict | None:
    """Alarm rule with the highest episode recall whose false alarms per hour on the validation
    captures stay within the budget (ties: faster alarm). None if no rule fits."""
    from mobility_model_zoo.security.can_ids.forest_features import alarms, to_microseconds

    best = None
    for k, w in ALARM_GRID:
        runs = [
            (c["ts"], c["y"], alarms(to_microseconds(c["ts"]), sc >= thr, k, w, ALARM_HOLDOFF_MS))
            for c, sc in zip(val_caps, val_scores, strict=True)
        ]
        m = alarm_metrics(runs)
        if not m["false_alarms_per_hour"] <= budget_per_hour:  # also rejects NaN
            continue
        rank = (m["episode_recall"], -np.nan_to_num(m["median_latency_ms"], nan=np.inf))
        if best is None or rank > best[0]:
            best = (rank, {"k": k, "window_ms": w, "holdoff_ms": ALARM_HOLDOFF_MS, "validation": m})
    return best[1] if best else None
