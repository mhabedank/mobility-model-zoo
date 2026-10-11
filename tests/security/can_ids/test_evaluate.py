"""The can-ids-v1 harness on a tiny synthetic benchmark (feature 007, T012)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from mobility_model_zoo.release.registry import schema_errors
from mobility_model_zoo.security.can_ids import benchmark as bm
from mobility_model_zoo.security.can_ids import detectors as dets
from mobility_model_zoo.security.can_ids import evaluate as ev
from mobility_model_zoo.security.can_ids.synth import generate

SPLITS = (
    "train_01",
    "test_01_known_vehicle_known_attack",
    "test_02_unknown_vehicle_known_attack",
    "test_03_known_vehicle_unknown_attack",
    "test_04_unknown_vehicle_unknown_attack",
)
FAST = ["picket-forest", "ctrl-shuffled", "ctrl-id-lookup", "bl-can-logic"]


def _write_csv(path: Path, df) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        "".join(f"{b:02X}" for b in row) for row in df[[f"b{i}" for i in range(8)]].to_numpy(np.uint8)
    ]
    lines = ["timestamp,arbitration_id,data_field,attack"]
    lines += [
        f"{1000 + t:.6f},{i:03X},{d},{y}"
        for t, i, d, y in zip(df["ts"], df["can_id"], data, df["label"], strict=True)
    ]
    path.write_text("\n".join(lines) + "\n")


@pytest.fixture(scope="module")
def bench(tmp_path_factory):
    root = tmp_path_factory.mktemp("bench")
    ctt = root / "can-train-and-test" / "extracted"
    seed = 0
    for s in ("set_01", "set_02"):
        for split in SPLITS:
            caps = (
                ("DoS-1", "DoS-2", "fuzzing-1", "fuzzing-2")
                if split == "train_01"
                else ("DoS-1", "scan-1")
            )
            for cap in caps:
                seed += 1
                attack = {"DoS": "dos", "fuzzing": "fuzzing", "scan": "scan"}[cap.split("-")[0]]
                _write_csv(ctt / s / split / f"{cap}.csv", generate(attack, n_frames=2500, seed=seed))
    road = root / "road" / "extracted" / "road"
    (road / "ambient").mkdir(parents=True)
    (road / "attacks").mkdir()
    meta = {}
    for name in ("fuzzing_attack_2", "correlated_signal_attack_2_masquerade"):
        lines = [f"({k * 0.01:.6f}) can0 2AA#{(k * 3 + len(name)) % 256:02X}" for k in range(300)]
        (road / "attacks" / f"{name}.log").write_text("\n".join(lines) + "\n")
        meta[name] = {"injection_interval": [1.0, 1.5], "injection_id": "XXX"}
    (road / "attacks" / "capture_metadata.json").write_text(json.dumps(meta))
    lines = [f"({k * 0.01:.6f}) can0 100#{k % 256:02X}" for k in range(300)]
    (road / "ambient" / "ambient_drive_0.log").write_text("\n".join(lines) + "\n")
    sources = {"can-train-and-test": ctt, "road": root / "road"}
    manifest = bm.freeze(sources, root / "manifest")
    return root, sources, manifest


# find_spec, not importorskip: importing emlearn changes numpy's error state for the whole session
@pytest.mark.skipif(importlib.util.find_spec("emlearn") is None, reason="emlearn missing (C parity)")
def test_full_run_report_and_quality(bench, tmp_path):
    root, sources, manifest = bench
    res = ev.run(FAST, manifest, sources, cache=tmp_path / "cache")
    res["road"] = ev.evaluate_road(manifest, sources, tmp_path / "cache", tmp_path / "store")
    assert not res["partial"] and res["outcome"]["verdict"] in ("success", "partial", "kill")
    pf = res["detectors"]["picket-forest"]
    for s in ("set_01", "set_02"):
        assert pf["sets"][s]["parity"]["mismatches"] == 0
        assert set(pf["sets"][s]["splits"]) == set(ev.SPLIT_NAMES.values())
    ev.write_report(res, tmp_path / "report")
    text = (tmp_path / "report" / "report.md").read_text()
    metrics_text = (tmp_path / "report" / "metrics.json").read_text()
    assert "weighted" not in metrics_text  # no support-weighted metric anywhere
    assert "Quality against cost" in text and "C versus Python" in text and "ROAD" in text
    assert "Outcome (research R10)" in text
    q = tmp_path / "quality.json"
    ev.write_quality(res, q, "picket-forest", "0.1.0")
    data = json.loads(q.read_text())
    assert schema_errors("results", data) == []
    assert all(m["benchmark"] == "can-ids-v1" and m["reference"] for m in data["metrics"])


def test_partial_run_refuses_quality(bench, tmp_path):
    _, sources, manifest = bench
    res = ev.run(["bl-can-logic"], manifest, sources, sets=["set_01"], cache=tmp_path / "cache")
    assert res["partial"]
    with pytest.raises(ValueError, match="partial"):
        ev.write_quality(res, tmp_path / "q.json", "picket-forest", "0.1.0")


def test_missing_set_is_reported(bench, tmp_path):
    _, sources, manifest = bench
    res = ev.run(["bl-can-logic"], manifest, sources, sets=["set_01", "set_09"], cache=tmp_path / "c")
    assert res["partial"] and any("set_09" in m for m in res["missing"])


def test_each_set_trains_only_on_its_own_training_captures(bench, tmp_path, monkeypatch):
    _, sources, manifest = bench
    seen = []

    class Spy(dets.Detector):
        def fit(self, train, val):
            seen.append(({c["id"] for c in train}, {c["id"] for c in val}))

        def score(self, caps):
            return [np.zeros(len(c["y"]), np.float32) for c in caps]

    monkeypatch.setattr(ev, "registry", lambda: {"spy": Spy("spy", "control", "records fit inputs")})
    ev.run(["spy"], manifest, sources, cache=tmp_path / "cache")
    roles = {c["id"]: (c["set"], c["role"]) for c in manifest["captures"]}
    for train_ids, val_ids in seen:
        sets = {roles[i][0] for i in train_ids | val_ids}
        assert len(sets) == 1
        assert {roles[i][1] for i in train_ids} == {"train"}
        assert {roles[i][1] for i in val_ids} == {"validation"}


def test_changed_capture_stops_the_run(bench, tmp_path):
    root, sources, manifest = bench
    path = sources["can-train-and-test"] / "set_02" / "test_01_known_vehicle_known_attack" / "DoS-1.csv"
    original = path.read_text()
    path.write_text(original.replace(",0\n", ",1\n", 1))
    try:
        with pytest.raises(bm.CaptureChanged):
            ev.run(["bl-can-logic"], manifest, sources, cache=tmp_path / "cache")
    finally:
        path.write_text(original)


def _dets(sh_auc, ref_auc, sh_f1, pf_f1):
    def det(auc, f1):
        return {"sets": {"set_01": {"splits": {"s": {"frame": {"auc_roc": auc, "f1": f1}}}}}}

    return {
        "ctrl-shuffled": det(sh_auc, sh_f1),
        "bl-isolation-forest": det(ref_auc, 0.0),
        "picket-forest": det(0.99, pf_f1),
    }


def test_shuffled_control_is_judged_against_the_label_free_reference():
    # novelty effect: high AUROC, but not above the label-free reference -> no leak
    leaks, superseded = ev.shuffled_leakage(_dets(0.85, 0.9, 0.1, 0.9))
    assert leaks == [] and superseded  # the original rule is still reported
    leaks, _ = ev.shuffled_leakage(_dets(0.97, 0.9, 0.1, 0.9))
    assert any("label-free reference" in r for r in leaks)
    leaks, _ = ev.shuffled_leakage(_dets(0.5, 0.9, 0.5, 0.9))
    assert any("half of picket-forest" in r for r in leaks)


def test_shuffled_control_needs_the_reference():
    d = _dets(0.5, 0.5, 0.0, 0.9)
    del d["bl-isolation-forest"]
    leaks, _ = ev.shuffled_leakage(d)
    assert leaks and "cannot be judged" in leaks[0]


def test_headline_counts_zero_when_the_test_split_exceeds_the_budget():
    within = {"budgets": {"10": {"episode_recall": 0.8, "false_alarms_per_hour": 9.0}}}
    over = {"budgets": {"10": {"episode_recall": 1.0, "false_alarms_per_hour": 3000.0}}}
    assert ev._headline(within, "10") == 0.8
    assert ev._headline(over, "10") == 0.0
    assert ev._headline({"budgets": {}}, "10") is None


def test_rejudge_recomputes_without_training(bench, tmp_path):
    _, sources, manifest = bench
    res = ev.run(["bl-can-logic"], manifest, sources, sets=["set_01"], cache=tmp_path / "c")
    again = ev.rejudge(json.loads(json.dumps(res, default=float)))
    assert again["outcome"]["verdict"] == res["outcome"]["verdict"] and again["judged_at_commit"]
