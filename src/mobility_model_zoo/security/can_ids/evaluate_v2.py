"""Harness for benchmark `can-ids-v2`: `can-ids-v1` plus per-vehicle calibration (feature 010).

`can-ids-v2` keeps every capture, role and protocol constant of `can-ids-v1` and adds a
calibration plan: for each set and each vehicle that appears in it, benign captures recorded
separately from the set's test and validation captures (research R2 of feature 010). Detectors
that use the calibrated features get, per capture, the features relative to the table of that
capture's vehicle (`Xc`); the other detectors see the capture unchanged.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from mobility_model_zoo.security.can_ids import calibrated as cal
from mobility_model_zoo.security.can_ids import detectors as dets
from mobility_model_zoo.security.can_ids import evaluate as ev

BENCHMARK = "can-ids-v2"
BENIGN_FAMILIES = ("attack-free", "accessory")
ROAD_BENIGN = "benign"
UNKNOWN_VEHICLE = ev.UNKNOWN_VEHICLE
FA_GOAL = 3.0  # false alarms per hour (research R3)
ROAD_F1_GOAL = 0.70
MIN_EPISODE_RECALL = 0.5


class CalibrationOverlap(ValueError):
    """A calibration capture shares content with a test or validation capture of its set."""


# ---- calibration plan and frozen manifest ----------------------------------------------------


def calibration_plan(v1: dict) -> dict[str, dict[str, list[str]]]:
    """{set: {vehicle: [capture ids]}} from the frozen `can-ids-v1` manifest (deterministic)."""
    caps = v1["captures"]
    ctt = [c for c in caps if c["dataset"] == "can-train-and-test"]
    benign = [c for c in ctt if c["split"] == "train_01" and c["attack_family"] in BENIGN_FAMILIES]
    plan: dict[str, dict[str, list[str]]] = {}
    for s in sorted({c["set"] for c in ctt}):
        in_set = [c for c in ctt if c["set"] == s]
        known = {c["vehicle"] for c in in_set if c["role"] == "train"}
        held = {c["sha256"] for c in in_set if c["role"] in ("test", "validation")}
        plan[s] = {}
        for v in sorted({c["vehicle"] for c in in_set}):
            if v in known:
                pick = [c for c in benign if c["set"] == s and c["role"] == "train"]
            else:
                pick = [c for c in benign if c["vehicle"] == v and c["set"] != s]
            seen, ids = set(), []
            for c in sorted(pick, key=lambda c: c["id"]):
                if c["sha256"] in held or c["sha256"] in seen:
                    continue
                seen.add(c["sha256"])
                ids.append(c["id"])
            plan[s][v] = ids
    road = [c for c in caps if c["dataset"] == "road"]
    plan["road"] = {
        "road-vehicle": sorted(
            c["id"] for c in road if c["role"] == "train" and c["attack_family"] == ROAD_BENIGN
        )
    }
    return plan


def check_disjoint(manifest: dict) -> None:
    """Refuse a plan whose calibration content overlaps a test or validation capture."""
    by_id = {c["id"]: c for c in manifest["captures"]}
    for s, vehicles in manifest["calibration"].items():
        held = {
            c["sha256"]
            for c in manifest["captures"]
            if c["set"] == s and c["role"] in ("test", "validation")
        }
        for v, ids in vehicles.items():
            if not ids:
                raise CalibrationOverlap(f"{s}/{v}: no calibration capture")
            for i in ids:
                c = by_id[i]
                if c["sha256"] in held:
                    raise CalibrationOverlap(f"{s}/{v}: {i} overlaps a test or validation capture")
                if c["attack_frames"]:
                    raise CalibrationOverlap(f"{s}/{v}: {i} contains attack frames")


def build_manifest(v1: dict) -> dict[str, Any]:
    v1_sha = hashlib.sha256(json.dumps(v1, sort_keys=True).encode()).hexdigest()
    m = {k: v for k, v in v1.items() if k not in ("frozen_at", "benchmark")}
    m["benchmark"] = BENCHMARK
    m["based_on"] = {"benchmark": v1["benchmark"], "manifest_sha256": v1_sha}
    m["calibration"] = calibration_plan(v1)
    m["protocol"] = {
        **v1["protocol"],
        "calibration": (
            "per set and vehicle: benign train_01 captures (attack-free, accessory); the known vehicle "
            "uses its own set's train captures, an unknown vehicle the captures of the sets where it "
            "is known, minus any content in the set's test or validation captures; ROAD: ambient "
            "captures with role train"
        ),
    }
    check_disjoint(m)
    return m


def freeze(v1: dict, out_dir: Path) -> dict[str, Any]:
    """Write `manifest.json` of can-ids-v2 once; identical content is a no-op, a change refused."""
    from mobility_model_zoo.security.can_ids.benchmark import FrozenChanged, _dump

    m = build_manifest(v1)
    path = Path(out_dir) / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in old.items() if k != "frozen_at"} != json.loads(_dump(m)):
            raise FrozenChanged(f"{path} is frozen; a change makes a new benchmark version")
        return old
    m = {**m, "frozen_at": dt.date.today().isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(m), encoding="utf-8")
    return m


# ---- detectors on calibrated features --------------------------------------------------------


class CalForest(dets.Forest):
    """The picket-forest recipe on the calibrated features (`Xc`), optionally plus the raw ID."""

    def __init__(self, name, kind, description, with_id=False, shuffle=False):
        super().__init__(name, kind, description, ["dt_id_ms"], shuffle=shuffle)
        n = len(cal.FEATURE_NAMES)
        self.idx = list(range(n + 1)) if with_id else list(range(n))

    @staticmethod
    def _view(caps):
        return [{**c, "X": c["Xc"]} for c in caps]

    def fit(self, train, val):
        super().fit(self._view(train), self._view(val))

    def score(self, caps):
        return super().score(self._view(caps))


class Rules(dets.Detector):
    """Rules-only baseline on the same calibration table (no training)."""

    def fit(self, train, val):
        self.model = None

    def score(self, caps):
        return [cal.rules(c["Xc"][:, : len(cal.FEATURE_NAMES)]) for c in caps]


def exclude(v2: dict, captures: dict[str, str], benchmark: str) -> dict[str, Any]:
    """A new benchmark version without some captures (role `excluded` with the reason); the frozen
    source version is referenced by hash. Used for can-ids-v3 (feature 010)."""
    src_sha = hashlib.sha256(json.dumps(v2, sort_keys=True).encode()).hexdigest()
    m = json.loads(json.dumps({k: v for k, v in v2.items() if k != "frozen_at"}))
    m["benchmark"] = benchmark
    m["based_on"] = {"benchmark": v2["benchmark"], "manifest_sha256": src_sha}
    shas = {c["sha256"] for c in m["captures"] if c["id"] in captures}
    for c in m["captures"]:
        if c["sha256"] in shas:
            c["role"] = "excluded"
            c["excluded_reason"] = captures.get(c["id"]) or next(
                captures[x["id"]]
                for x in m["captures"]
                if x["sha256"] == c["sha256"] and x["id"] in captures
            )
    for vehicles in m["calibration"].values():
        for v, ids in vehicles.items():
            vehicles[v] = [i for i in ids if i not in captures]
    check_disjoint(m)
    return m


def registry() -> dict[str, dets.Detector]:
    base = dets.registry()
    return {
        "picket-forest-v2": CalForest(
            "picket-forest-v2", "model", "random forest on 10 calibrated, vehicle-relative features"
        ),
        "rules-v2": Rules(
            "rules-v2", "baseline", "rules on the calibration table (rate, unknown IDs, DLC)"
        ),
        "ctrl-forest-v2-with-id": CalForest(
            "ctrl-forest-v2-with-id", "control", "picket-forest-v2 plus the raw CAN ID", with_id=True
        ),
        "ctrl-shuffled-v2": CalForest(
            "ctrl-shuffled-v2", "control", "picket-forest-v2 trained on permuted labels", shuffle=True
        ),
        "ctrl-id-lookup": base["ctrl-id-lookup"],
        "bl-isolation-forest": base["bl-isolation-forest"],
        "picket-forest": base["picket-forest"],
    }


# ---- running ---------------------------------------------------------------------------------


def _with_xc(cap: dict, table: cal.Table) -> dict:
    xc = cal.features(cap, table)
    return {**cap, "Xc": np.column_stack([xc, cap["can_id"].astype(np.float32)])}


def tables(manifest: dict, sources, cache) -> dict[tuple[str, str], cal.Table]:
    by_id = {c["id"]: c for c in manifest["captures"]}
    out = {}
    for s, vehicles in manifest["calibration"].items():
        for v, ids in vehicles.items():
            out[(s, v)] = cal.calibrate([ev.load_capture(by_id[i], sources, cache) for i in ids])
    return out


def _load(e, sources, cache, tabs, s):
    return _with_xc(ev.load_capture(e, sources, cache), tabs[(s, e["vehicle"])])


def evaluate_set(det, manifest, s, sources, cache, tabs) -> dict[str, Any]:
    entries = [c for c in manifest["captures"] if c["set"] == s]
    calib_ids = {i for ids in manifest["calibration"][s].values() for i in ids}
    by_role = defaultdict(list)
    for e in entries:
        by_role[e["role"]].append(e)
    train = [_load(e, sources, cache, tabs, s) for e in by_role["train"] if e["id"] not in calib_ids]
    val = [_load(e, sources, cache, tabs, s) for e in by_role["validation"]]
    det.fit(train, val)
    del train
    calib = ev.calibrate(det, val, manifest["protocol"]["budgets_per_hour"])
    splits = {}
    for split in manifest["protocol"]["can_train_and_test_tests"]:
        caps = [_load(e, sources, cache, tabs, s) for e in by_role["test"] if e["split"] == split]
        if not caps:
            continue
        scores = det.score(caps)
        splits[ev.SPLIT_NAMES[split]] = ev.split_metrics(
            caps,
            scores,
            calib["threshold"],
            calib["points"],
            calib["benign_val"],
            manifest["protocol"]["recall_at_frame_fpr"],
        )
    return {"threshold": calib["threshold"], "info": det.info, "splits": splits}


def release_model(name, manifest, sources, cache, tabs):
    """Detector trained on the training captures of all four sets, threshold on all validation."""
    det = registry()[name]
    ctt = [c for c in manifest["captures"] if c["dataset"] == "can-train-and-test"]
    calib_ids = {
        i for s, v in manifest["calibration"].items() if s != "road" for ids in v.values() for i in ids
    }
    train = [
        _load(e, sources, cache, tabs, e["set"])
        for e in ctt
        if e["role"] == "train" and e["id"] not in calib_ids
    ]
    val = [_load(e, sources, cache, tabs, e["set"]) for e in ctt if e["role"] == "validation"]
    det.fit(train, val)
    del train
    return det, ev.calibrate(det, val, manifest["protocol"]["budgets_per_hour"])


def evaluate_road(det, calib, manifest, sources, cache, tabs) -> dict[str, Any]:
    road = [c for c in manifest["captures"] if c["dataset"] == "road"]
    out: dict[str, Any] = {}
    groups = {
        "in_scope": [e for e in road if e["role"] == "test" and e["attack_family"] != ROAD_BENIGN],
        "ambient": [e for e in road if e["role"] == "test" and e["attack_family"] == ROAD_BENIGN],
        "out_of_scope": [e for e in road if e["role"] == "out_of_scope"],
    }
    for label, entries in groups.items():
        caps = [_load(e, sources, cache, tabs, "road") for e in entries]
        scores = det.score(caps)
        out[label] = ev.split_metrics(
            caps,
            scores,
            calib["threshold"],
            calib["points"],
            calib["benign_val"],
            manifest["protocol"]["recall_at_frame_fpr"],
        )
    both = groups["in_scope"] + groups["ambient"]
    caps = [_load(e, sources, cache, tabs, "road") for e in both]
    out["in_scope_with_ambient"] = ev.split_metrics(
        caps,
        det.score(caps),
        calib["threshold"],
        calib["points"],
        calib["benign_val"],
        manifest["protocol"]["recall_at_frame_fpr"],
    )
    return out


def run(names, manifest, sources, cache) -> dict[str, Any]:
    check_disjoint(manifest)
    tabs = tables(manifest, sources, cache)
    result: dict[str, Any] = {
        "benchmark": manifest["benchmark"],
        "date": dt.date.today().isoformat(),
        "code_commit": ev.code_commit(),
        "calibration_minutes": {f"{s}/{v}": round(t.seconds / 60, 1) for (s, v), t in tabs.items()},
        "detectors": {},
    }
    sets = sorted(s for s in manifest["calibration"] if s != "road")
    for name in names:
        r: dict[str, Any] = {"sets": {}}
        for s in sets:
            r["sets"][s] = evaluate_set(registry()[name], manifest, s, sources, cache, tabs)
        r["aggregate"] = ev.aggregate(r["sets"])
        det, calib = release_model(name, manifest, sources, cache, tabs)
        r["road"] = evaluate_road(det, calib, manifest, sources, cache, tabs)
        r["road_threshold"] = calib["threshold"]
        result["detectors"][name] = r
    result["outcome"] = outcome(result)
    return result


# ---- goals and controls (research R3, R4) ------------------------------------------------------


def _fa(split_res: dict) -> float:
    return split_res["default_rule"]["false_alarms_per_hour"]


def goals(r: dict) -> dict[str, Any]:
    road_f1 = r["road"]["in_scope"]["frame"]["f1"]
    road_fa = _fa(r["road"]["ambient"])
    fa = {
        f"{s}/{split}": _fa(v["splits"][split])
        for s, v in r["sets"].items()
        for split in UNKNOWN_VEHICLE
        if split in v["splits"]
    }
    ep = [
        v["splits"][split]["default_rule"]["episode_recall"]
        for v in r["sets"].values()
        for split in UNKNOWN_VEHICLE
        if split in v["splits"]
    ]
    return {
        "road_f1": road_f1,
        "road_ambient_fa_per_hour": road_fa,
        "unknown_vehicle_fa_per_hour": fa,
        "unknown_vehicle_fa_worst": max(fa.values()),
        "unknown_vehicle_fa_median": float(np.median(list(fa.values()))),
        "unknown_vehicle_episode_recall_median": float(np.median(ep)),
        "met": {
            "road_f1": road_f1 >= ROAD_F1_GOAL,
            "unknown_vehicle_fa": max(fa.values()) < FA_GOAL and road_fa < FA_GOAL,
            "episode_recall": float(np.median(ep)) >= MIN_EPISODE_RECALL,
        },
    }


def outcome(result: dict) -> dict[str, Any]:
    d = result["detectors"]
    out: dict[str, Any] = {"goals": {n: goals(r) for n, r in d.items()}, "controls": []}
    m = "picket-forest-v2"
    if m not in d:
        return out
    g = out["goals"][m]
    agg = {n: r["aggregate"] for n, r in d.items()}

    def f1(n, split):
        return agg[n].get(split, {}).get("f1", {}).get("median")

    checks = []
    if "ctrl-forest-v2-with-id" in d:
        worse = [
            s for s in UNKNOWN_VEHICLE if (f1("ctrl-forest-v2-with-id", s) or 0) > (f1(m, s) or 0) + 0.05
        ]
        checks.append(("raw CAN ID adds no more than 0.05 F1 on unknown vehicles", not worse, worse))
    if "ctrl-id-lookup" in d:
        bad = [s for s in UNKNOWN_VEHICLE if (f1("ctrl-id-lookup", s) or 0) >= (f1(m, s) or 0)]
        road_bad = d["ctrl-id-lookup"]["road"]["in_scope"]["frame"]["f1"] >= g["road_f1"]
        checks.append(
            (
                "ctrl-id-lookup below picket-forest-v2 (unknown vehicles, ROAD)",
                not bad and not road_bad,
                bad,
            )
        )
    if "ctrl-shuffled-v2" in d and "bl-isolation-forest" in d:
        sub = {
            "ctrl-shuffled": d["ctrl-shuffled-v2"],
            "bl-isolation-forest": d["bl-isolation-forest"],
            "picket-forest": d[m],
        }
        leaks, superseded = ev.shuffled_leakage(sub)
        checks.append(("shuffled-label control (amended rule of feature 007)", not leaks, leaks))
        out["superseded_shuffle_violations"] = superseded
    if "rules-v2" in d:
        gr = out["goals"]["rules-v2"]
        beats = (
            g["road_f1"] > gr["road_f1"]
            or g["unknown_vehicle_fa_worst"] < gr["unknown_vehicle_fa_worst"]
        )
        checks.append(("forest beats rules-only on ROAD F1 or unknown-vehicle false alarms", beats, []))
    out["controls"] = [{"check": c, "passed": bool(p), "details": det} for c, p, det in checks]
    met = all(g["met"].values())
    controls_ok = all(c["passed"] for c in out["controls"])
    out["verdict"] = (
        "success" if met and controls_ok else ("goal missed" if not met else "control failed")
    )
    return out
