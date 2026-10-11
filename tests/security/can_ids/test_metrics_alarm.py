"""Event-level alarm metrics (feature 007, FR-008, research R3/R4)."""

import numpy as np
import pytest

from mobility_model_zoo.security.can_ids.metrics import (
    alarm_metrics,
    budget_operating_point,
    frame_metrics,
    recall_at_fpr,
)


def _cap(n=1000, period=0.01, attacks=()):
    """Timestamps every `period` s; `attacks` = list of (first, last) frame indices labelled 1."""
    ts = np.arange(n) * period
    y = np.zeros(n, np.uint8)
    for a, b in attacks:
        y[a : b + 1] = 1
    return ts, y


def test_one_frame_episode_with_alarm_in_grace_window():
    ts, y = _cap(attacks=[(100, 100)])
    alarm = np.zeros_like(y)
    alarm[150] = 1  # 0.5 s after the single attack frame, inside the 1 s grace
    m = alarm_metrics([(ts, y, alarm)])
    assert m["episodes"] == 1 and m["episode_recall"] == 1.0
    assert m["median_latency_ms"] == pytest.approx(500.0)
    assert m["p95_latency_ms"] == pytest.approx(500.0)


def test_alarm_on_first_attack_frame_is_zero_latency():
    ts, y = _cap(attacks=[(200, 260)])
    alarm = np.zeros_like(y)
    alarm[200] = 1
    m = alarm_metrics([(ts, y, alarm)])
    assert m["median_latency_ms"] == pytest.approx(0.0)


def test_latency_defined_whenever_an_episode_is_detected():
    ts, y = _cap(n=5000, attacks=[(100, 110), (1000, 1200), (3000, 3001)])
    alarm = np.zeros_like(y)
    alarm[[105, 1250, 3001]] = 1  # inside, in grace, last frame
    m = alarm_metrics([(ts, y, alarm)])
    assert m["episode_recall"] == 1.0
    assert not np.isnan(m["median_latency_ms"]) and not np.isnan(m["p95_latency_ms"])
    assert m["median_latency_ms"] == pytest.approx(50.0)  # latencies 50, 2500 (grace), 10 ms


def test_false_alarms_outside_episode_and_grace():
    ts, y = _cap(n=360_000, period=0.01, attacks=[(1000, 1010)])  # one hour of traffic
    alarm = np.zeros_like(y)
    alarm[[1005, 1150, 5000, 9000]] = 1  # 1150 is 1.4 s after the end: outside the grace
    m = alarm_metrics([(ts, y, alarm)])
    assert m["episode_recall"] == 1.0
    assert m["false_alarms_per_hour"] == pytest.approx(3.0, rel=1e-3)


def test_frame_metrics_report_mcc_and_attack_class_only():
    y = np.array([0, 0, 0, 0, 1, 1])
    m = frame_metrics(y, np.array([0, 0, 0, 1, 1, 0.0]), 0.5)
    assert m["precision"] == pytest.approx(0.5) and m["recall"] == pytest.approx(0.5)
    assert -1.0 <= m["mcc"] <= 1.0
    assert not any("weighted" in k for k in m)


def test_recall_at_fpr_uses_the_given_benign_validation_scores():
    val_benign = np.linspace(0, 1, 1001)  # threshold for FPR 0.001 is about 0.999
    y = np.array([0, 0, 1, 1, 1])
    score = np.array([0.1, 0.2, 0.9995, 0.5, 1.0])
    r = recall_at_fpr(y, score, val_benign, fpr=0.001)
    assert r == pytest.approx(2 / 3)


def test_budget_operating_point_picks_best_recall_within_budget():
    ts, y = _cap(n=360_000, attacks=[(1000, 1100), (50_000, 50_050)])
    rng = np.random.default_rng(0)
    score = rng.random(len(y)) * 0.4  # benign noise below the threshold
    score[rng.choice(len(y), 30, replace=False)] = 0.9  # 30 isolated benign false positives
    score[y == 1] = 0.9
    point = budget_operating_point([{"ts": ts, "y": y}], [score], thr=0.5, budget_per_hour=1)
    assert point is not None
    assert point["validation"]["false_alarms_per_hour"] <= 1
    assert point["validation"]["episode_recall"] == 1.0
    assert point["k"] > 1  # single-frame alarms would fire on the isolated false positives
    # every frame flagged on dense traffic (1 ms): every rule alarms once per hold-off -> over budget
    ts2, y2 = _cap(n=360_000, period=0.001, attacks=[(1000, 1100)])
    assert budget_operating_point([{"ts": ts2, "y": y2}], [np.ones(len(y2))], 0.5, 1) is None
