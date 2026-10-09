"""Evaluation harness of benchmark can-ids-v1 (feature 007, research R3, R5, R6, R10).

For every detector and every can-train-and-test set: fit on the set's training captures, choose
the score threshold (best F1) and the alarm operating points (false-alarm budgets 1 and 10 per
hour) on its validation captures, score the four test splits. Test captures never choose anything
(constitution III). The release model (training captures of all four sets) is scored on the ROAD
test captures, the strictest unknown-vehicle test.

Outputs: detector runs in $MMZ_DATA/derived/can-ids-v1/runs/ (scores never go into git), the
report and metrics under topics/security/reports/picket-forest/can-ids-v1/, and the quality
results of the release (only from a complete run).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mobility_model_zoo.edge.paths import REPO_ROOT, derived_dir
from mobility_model_zoo.security.can_ids import benchmark as bm
from mobility_model_zoo.security.can_ids import forest
from mobility_model_zoo.security.can_ids.detectors import Detector, make_capture, registry
from mobility_model_zoo.security.can_ids.forest_features import alarms, to_microseconds
from mobility_model_zoo.security.can_ids.metrics import (
    alarm_metrics,
    budget_operating_point,
    frame_metrics,
    recall_at_fpr,
)

DEFAULT_ALARM = {"k": 3, "window_ms": 200, "holdoff_ms": 1000}
SPLIT_NAMES = {
    "test_01_known_vehicle_known_attack": "known_vehicle_known_attack",
    "test_02_unknown_vehicle_known_attack": "unknown_vehicle_known_attack",
    "test_03_known_vehicle_unknown_attack": "known_vehicle_unknown_attack",
    "test_04_unknown_vehicle_unknown_attack": "unknown_vehicle_unknown_attack",
}
UNKNOWN_VEHICLE = ("unknown_vehicle_known_attack", "unknown_vehicle_unknown_attack")


def code_commit() -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "unknown"


# ---- loading captures -----------------------------------------------------------------------


def _frames(entry: dict, sources: dict[str, Path]) -> pd.DataFrame:
    """Frames of one manifest capture with ts in seconds (format of can_train_and_test)."""
    from mobility_model_zoo.security.can_ids import frames as fmt
    from mobility_model_zoo.security.can_ids.can_train_and_test import load

    if entry["dataset"] == "can-train-and-test":
        _, set_name, split, stem = entry["id"].split("/")
        return load(sources["can-train-and-test"], set_name, split)[stem]
    root = fmt.road_root(sources["road"])
    _, kind, stem = entry["id"].split("/")
    df = fmt.read_candump(root / kind / f"{stem}.log", f"{kind}/{stem}.log")
    if kind == "attacks":
        meta = json.loads((root / "attacks" / "capture_metadata.json").read_text())
        df["label"] = fmt.road_labels(df, meta.get(stem) or {})
    out = pd.DataFrame({"ts": df["ts_us"].to_numpy() / 1e6, "can_id": df["can_id"], "dlc": df["dlc"]})
    for c in fmt.PAYLOAD:
        out[c] = df[c]
    out["label"] = df["label"].astype(np.uint8)
    return out


def load_capture(entry: dict, sources: dict[str, Path], cache: Path | None) -> dict:
    """A harness capture; cached by content hash (features are deterministic per content)."""
    path = cache / f"{entry['sha256']}.npz" if cache else None
    if path is not None and path.exists():
        with np.load(path) as z:
            cap = {k: z[k] for k in z.files}
    else:
        cap = make_capture(_frames(entry, sources), entry["id"], entry["attack_family"])
        cap = {k: v for k, v in cap.items() if isinstance(v, np.ndarray)}
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(path, **cap)
    return {**cap, "id": entry["id"], "family": entry["attack_family"]}


# ---- scoring a split ------------------------------------------------------------------------


def _alarm_runs(caps, scores, thr, rule):
    return [
        (
            c["ts"],
            c["y"],
            alarms(to_microseconds(c["ts"]), s >= thr, rule["k"], rule["window_ms"], rule["holdoff_ms"]),
        )
        for c, s in zip(caps, scores, strict=True)
    ]


def split_metrics(caps, scores, thr, points, benign_val, fpr) -> dict[str, Any]:
    y = np.concatenate([c["y"] for c in caps])
    s = np.concatenate(scores)
    out: dict[str, Any] = {"captures": len(caps), "frame": frame_metrics(y, s, thr)}
    out["frame"]["recall_at_fpr"] = recall_at_fpr(y, s, benign_val, fpr) if benign_val.size else None
    out["default_rule"] = alarm_metrics(_alarm_runs(caps, scores, thr, DEFAULT_ALARM))
    out["budgets"] = {}
    for budget, point in points.items():
        if point is None:
            out["budgets"][budget] = {
                "rule": None,
                "episode_recall": 0.0,
                "note": "no rule within budget",
            }
            continue
        m = alarm_metrics(_alarm_runs(caps, scores, thr, point))
        out["budgets"][budget] = {"rule": {k: point[k] for k in ("k", "window_ms")}, **m}
    out["families"] = {}
    for fam in sorted({c["family"] for c in caps}):
        sel = [i for i, c in enumerate(caps) if c["family"] == fam]
        yf = np.concatenate([caps[i]["y"] for i in sel])
        sf = np.concatenate([scores[i] for i in sel])
        out["families"][fam] = {k: v for k, v in frame_metrics(yf, sf, thr).items() if k != "frames"}
    return out


def calibrate(det: Detector, val: list[dict], budgets: list[int]) -> dict[str, Any]:
    """Threshold (best F1) and alarm operating points on validation captures only."""
    sv = det.score(val)
    yv = np.concatenate([c["y"] for c in val])
    s = np.concatenate(sv)
    thr = forest.best_threshold(yv, s) if 0 < yv.sum() < yv.size else float(np.quantile(s, 0.999))
    points = {str(b): budget_operating_point(val, sv, thr, b) for b in budgets}
    return {"threshold": thr, "points": points, "benign_val": s[yv == 0]}


# ---- one detector on one set ----------------------------------------------------------------


def evaluate_set(det: Detector, entries: list[dict], sources, cache, protocol) -> dict[str, Any]:
    by_role = defaultdict(list)
    for e in entries:
        by_role[e["role"]].append(e)
    if not by_role["train"] or not by_role["validation"]:
        return {"missing": "no training or validation captures"}
    train = [load_capture(e, sources, cache) for e in by_role["train"]]
    val = [load_capture(e, sources, cache) for e in by_role["validation"]]
    det.fit(train, val)
    del train
    cal = calibrate(det, val, protocol["budgets_per_hour"])
    result: dict[str, Any] = {
        "threshold": cal["threshold"],
        "operating_points": {
            b: ({k: p[k] for k in ("k", "window_ms")} if p else None) for b, p in cal["points"].items()
        },
        "info": det.info,
        "size_bytes": det.size_bytes(),
        "splits": {},
    }
    host_us = []
    for split, name in SPLIT_NAMES.items():
        tests = [e for e in by_role["test"] if e["split"] == split]
        if not tests:
            result["splits"][name] = {"missing": "no test captures"}
            continue
        caps = [load_capture(e, sources, cache) for e in tests]
        scores, us = det.timed_score(caps)
        host_us.append(us)
        result["splits"][name] = split_metrics(
            caps,
            scores,
            cal["threshold"],
            cal["points"],
            cal["benign_val"],
            protocol["recall_at_frame_fpr"],
        )
    result["host_us_per_frame_python"] = float(np.mean(host_us)) if host_us else None
    return result


# ---- C-versus-Python check of picket-forest ---------------------------------------------------


def parity(det: Detector, entries: list[dict], sources, cache, threshold: float) -> dict[str, int]:
    """Score every test capture with the C chain built from this model; count mismatches."""
    from mobility_model_zoo.security.can_ids.scorer import build_scorer, run_scorer

    frames_total = mismatches = 0
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        forest.to_c(det.model, det.idx, threshold, DEFAULT_ALARM, work)
        exe = build_scorer(work, work / "build")
        for e in entries:
            if e["role"] != "test":
                continue
            cap = load_capture(e, sources, cache)
            df = pd.DataFrame({"ts": cap["ts"], "can_id": cap["can_id"], "dlc": cap["dlc"]})
            for i in range(8):
                df[f"b{i}"] = cap["data"][:, i]
            c_scores, _ = run_scorer(exe, df)
            py = det.score([cap])[0]
            frames_total += len(py)
            mismatches += int(np.count_nonzero(c_scores != py))
    return {"frames": frames_total, "mismatches": mismatches}


# ---- the whole benchmark ----------------------------------------------------------------------


def run(
    detectors: list[str],
    manifest: dict,
    sources: dict[str, Path],
    sets: list[str] | None = None,
    cache: Path | None = None,
    with_parity: bool = True,
) -> dict[str, Any]:
    bm.verify_captures(manifest, sources)
    protocol = manifest["protocol"]
    all_sets = sorted({c["set"] for c in manifest["captures"] if c["dataset"] == "can-train-and-test"})
    chosen = sets or all_sets
    regs = registry()
    out: dict[str, Any] = {
        "benchmark": manifest["benchmark"],
        "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "code_commit": code_commit(),
        "date": dt.date.today().isoformat(),
        "partial": sorted(chosen) != all_sets,
        "sets": chosen,
        "missing": [],
        "detectors": {},
    }
    for name in detectors:
        det_res = {"kind": regs[name].kind, "description": regs[name].description, "sets": {}}
        for set_name in chosen:
            entries = [
                c for c in manifest["captures"] if c["set"] == set_name and c["role"] != "dropped"
            ]
            if not entries:
                out["missing"].append(f"{name}/{set_name}")
                det_res["sets"][set_name] = {"missing": "set not in the benchmark"}
                continue
            det = registry()[name]
            res = evaluate_set(det, entries, sources, cache, protocol)
            if "missing" in res:
                out["missing"].append(f"{name}/{set_name}: {res['missing']}")
            elif name == "picket-forest" and with_parity:
                res["parity"] = parity(det, entries, sources, cache, res["threshold"])
            det_res["sets"][set_name] = res
        det_res["aggregate"] = aggregate(det_res["sets"])
        out["detectors"][name] = det_res
    if out["missing"]:
        out["partial"] = True
    out["outcome"] = outcome(out)
    return out


def _headline(split_res: dict, budget: str) -> float | None:
    b = (split_res.get("budgets") or {}).get(budget)
    return None if b is None else b.get("episode_recall")


def aggregate(sets: dict[str, dict]) -> dict[str, Any]:
    """Median over sets and worst set per split for the headline and attack-class F1."""
    agg: dict[str, Any] = {}
    for split in SPLIT_NAMES.values():
        rows = [
            s["splits"][split]
            for s in sets.values()
            if "splits" in s and "frame" in s["splits"].get(split, {})
        ]
        if not rows:
            continue
        vals: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            vals["f1"].append(r["frame"]["f1"])
            vals["auc_roc"].append(r["frame"]["auc_roc"])
            vals["mcc"].append(r["frame"]["mcc"])
            vals["fa_per_hour_default"].append(r["default_rule"]["false_alarms_per_hour"])
            vals["median_latency_ms_default"].append(r["default_rule"]["median_latency_ms"])
            for b in ("1", "10"):
                h = _headline(r, b)
                vals[f"episode_detection_fa{b}"].append(np.nan if h is None else h)
        agg[split] = {
            k: {
                "median": float(np.nanmedian(v)) if not np.all(np.isnan(v)) else None,
                "worst": float(np.nanmax(v) if k.startswith("fa_per_hour") else np.nanmin(v))
                if not np.all(np.isnan(v))
                else None,
                "sets": len(v),
            }
            for k, v in vals.items()
        }
    return agg


SHUFFLE_AUROC_MARGIN = 0.05  # over the label-free reference (research R10, amended 2026-10-09)
SHUFFLE_F1_SHARE = 0.5  # of picket-forest's F1 at the validation operating point


def _frame(det: dict, set_name: str, split: str) -> dict | None:
    s = det["sets"].get(set_name, {})
    return s.get("splits", {}).get(split, {}).get("frame")


def shuffled_leakage(dets: dict) -> tuple[list[str], list[str]]:
    """Leakage test of the shuffled-label control (research R10 as amended 2026-10-09).

    A forest trained on permuted labels still ranks rare frames high (small, noisy leaves in sparse
    regions), so it acts as a novelty detector and its AUROC is not expected at 0.5 when attacks are
    outliers. Leakage is therefore judged against the label-free reference (`bl-isolation-forest`)
    and at the validation operating point. Returns (leak reasons, findings of the superseded
    criterion "AUROC at most 0.6", reported but not used)."""
    leaks, superseded = [], []
    sh, ref, pf = (dets.get(n) for n in ("ctrl-shuffled", "bl-isolation-forest", "picket-forest"))
    if sh is None:
        return leaks, superseded
    if ref is None:
        return ["bl-isolation-forest not evaluated: the shuffled-label control cannot be judged"], []
    for set_name in sh["sets"]:
        for split in sh["sets"][set_name].get("splits", {}):
            f_sh, f_ref, f_pf = (_frame(d, set_name, split) for d in (sh, ref, pf))
            if f_sh is None or f_sh.get("auc_roc") is None:
                continue
            where = f"{set_name}/{split}"
            if f_sh["auc_roc"] > 0.6:
                superseded.append(f"{where}: AUROC {f_sh['auc_roc']:.2f} > 0.6")
            if f_ref and f_ref.get("auc_roc") is not None:
                if f_sh["auc_roc"] > f_ref["auc_roc"] + SHUFFLE_AUROC_MARGIN:
                    leaks.append(
                        f"ctrl-shuffled AUROC {f_sh['auc_roc']:.2f} exceeds the label-free reference "
                        f"({f_ref['auc_roc']:.2f}) by > {SHUFFLE_AUROC_MARGIN} on {where}: leakage"
                    )
            if f_pf and f_pf.get("f1") and (f_sh.get("f1") or 0) >= SHUFFLE_F1_SHARE * f_pf["f1"]:
                leaks.append(
                    f"ctrl-shuffled F1 {f_sh['f1']:.2f} reaches half of picket-forest's "
                    f"({f_pf['f1']:.2f}) on {where}: leakage"
                )
    return leaks, superseded


def outcome(result: dict) -> dict[str, Any]:
    """Success, partial or kill per research R10 (computed from the numbers, never by hand)."""
    dets = result["detectors"]
    if "picket-forest" not in dets:
        return {"verdict": "n/a", "reasons": ["picket-forest not evaluated"]}
    reasons, kill = [], False
    agg = {n: d["aggregate"] for n, d in dets.items()}
    leaks, superseded = shuffled_leakage(dets)
    if leaks:
        kill = True
        reasons += leaks
    pf = agg["picket-forest"]
    beaten_by = []
    for split in UNKNOWN_VEHICLE:
        if split not in pf:
            continue
        pf_f1, pf_h = pf[split]["f1"]["median"], pf[split]["episode_detection_fa10"]["median"]
        for name, a in agg.items():
            if name in ("picket-forest", "ctrl-shuffled") or split not in a:
                continue
            f1, h = a[split]["f1"]["median"], a[split]["episode_detection_fa10"]["median"]
            if name == "ctrl-id-lookup" and f1 is not None and pf_f1 is not None and f1 >= pf_f1:
                kill = True
                reasons.append(f"ctrl-id-lookup reaches picket-forest's F1 on {split}")
            if (f1 is not None and pf_f1 is not None and f1 >= pf_f1) or (
                h is not None and pf_h is not None and h >= pf_h
            ):
                beaten_by.append(f"{name} on {split}")
    if kill:
        verdict = "kill"
    elif beaten_by:
        verdict = "partial"
        reasons.append("matched or beaten by: " + ", ".join(beaten_by))
    else:
        verdict = "success"
        reasons.append("picket-forest exceeds every control and baseline on unknown vehicles")
    if result.get("partial"):
        reasons.append("partial run: the verdict is provisional")
    return {
        "verdict": verdict,
        "reasons": reasons,
        "superseded_shuffle_criterion": {
            "rule": "ctrl-shuffled attack-class AUROC at most 0.6 on every split (until 2026-10-09)",
            "violations": superseded,
        },
    }


# ---- ROAD with the release model --------------------------------------------------------------


def release_model(manifest: dict, sources, cache, store: Path | None = None) -> tuple[Detector, dict]:
    """picket-forest trained on the training captures of all four sets; threshold and alarm
    points on all validation captures (research R6). Cached by recipe and manifest hash."""
    import joblib

    entries = [c for c in manifest["captures"] if c["dataset"] == "can-train-and-test"]
    key = hashlib.sha256(
        json.dumps([forest.GRID, sorted(e["sha256"] for e in entries if e["role"] != "test")]).encode()
    ).hexdigest()[:16]
    path = (store or derived_dir("picket-forest") / "export") / f"release-{key}.joblib"
    if path.exists():
        det, cal = joblib.load(path)
        return det, cal
    det = registry()["picket-forest"]
    train = [load_capture(e, sources, cache) for e in entries if e["role"] == "train"]
    val = [load_capture(e, sources, cache) for e in entries if e["role"] == "validation"]
    det.fit(train, val)
    del train
    cal = calibrate(det, val, manifest["protocol"]["budgets_per_hour"])
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump((det, cal), path)
    return det, cal


def evaluate_road(manifest: dict, sources, cache, store: Path | None = None) -> dict[str, Any]:
    det, cal = release_model(manifest, sources, cache, store)
    road = [c for c in manifest["captures"] if c["dataset"] == "road"]
    out: dict[str, Any] = {"model": "release model (train_01 of all four sets)"}
    for label, role in (("in_scope", "test"), ("out_of_scope", "out_of_scope")):
        entries = [e for e in road if e["role"] == role]
        if not entries:
            continue
        caps = [load_capture(e, sources, cache) for e in entries]
        scores = det.score(caps)
        out[label] = split_metrics(
            caps,
            scores,
            cal["threshold"],
            cal["points"],
            cal["benign_val"],
            manifest["protocol"]["recall_at_frame_fpr"],
        )
    return out


# ---- report, metrics and quality results ------------------------------------------------------


def _fmt(v, digits=3) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    return f"{v:.{digits}f}" if isinstance(v, float) else str(v)


def pareto(result: dict) -> list[dict]:
    """Quality (headline at <= 10 false alarms/h, unknown vehicle, median) against size."""
    rows = []
    for name, d in result["detectors"].items():
        a = d["aggregate"].get("unknown_vehicle_known_attack", {})
        q = (a.get("episode_detection_fa10") or {}).get("median")
        sizes = [s.get("size_bytes") for s in d["sets"].values() if s.get("size_bytes")]
        us = [
            s.get("host_us_per_frame_python")
            for s in d["sets"].values()
            if s.get("host_us_per_frame_python")
        ]
        rows.append(
            {
                "detector": name,
                "quality": q,
                "size_kb": float(np.median(sizes)) / 1024 if sizes else None,
                "host_us": float(np.median(us)) if us else None,
            }
        )
    for r in rows:
        r["pareto"] = r["quality"] is not None and not any(
            o is not r
            and o["quality"] is not None
            and o["size_kb"] is not None
            and r["size_kb"] is not None
            and o["quality"] >= r["quality"]
            and o["size_kb"] <= r["size_kb"]
            and (o["quality"] > r["quality"] or o["size_kb"] < r["size_kb"])
            for o in rows
        )
    return sorted(rows, key=lambda r: -(r["quality"] or -1))


def write_report(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {**result, "pareto": pareto(result)}
    (out_dir / "metrics.json").write_text(json.dumps(result, indent=1, default=float) + "\n")
    o = result["outcome"]
    lines = [
        f"# can-ids-v1 evaluation{' (partial)' if result['partial'] else ''}",
        "",
        f"**Outcome (research R10): {o['verdict']}.** " + " ".join(o["reasons"]),
        "",
        "Shuffled-label control: leakage is judged against the label-free reference "
        f"`bl-isolation-forest` (AUROC margin {SHUFFLE_AUROC_MARGIN}) and at the validation operating "
        f"point (F1 below {SHUFFLE_F1_SHARE} of picket-forest's). A forest on permuted labels ranks "
        "rare frames high and so acts as a novelty detector; the original rule "
        f'"{o.get("superseded_shuffle_criterion", {}).get("rule", "")}" was amended after the '
        "first real-data run and is reported, not applied. Violations of the original rule: "
        + ("; ".join(o.get("superseded_shuffle_criterion", {}).get("violations", [])) or "none")
        + ".",
        "",
        f"Benchmark `{result['benchmark']}`, manifest `{result['manifest_sha256'][:16]}`, code "
        f"`{result['code_commit'][:12]}`, {result['date']}. Sets: {', '.join(result['sets'])}."
        + (f" Missing: {'; '.join(result['missing'])}." if result["missing"] else ""),
        "",
        "Reference: the attack labels of can-train-and-test (official splits) and the injection "
        "labels of ROAD. All metrics are attack-class metrics; nothing is support-weighted. "
        "Thresholds and alarm rules are chosen on validation captures, never on test captures.",
        "",
        "## Headline: attack episodes detected at a false-alarm budget",
        "",
        "Median over the sets (worst set in brackets). Episodes: attack frames separated by more "
        "than 1 s; an alarm up to 1 s after an episode still detects it.",
        "",
        "| Detector | Split | ≤ 1 FA/h | ≤ 10 FA/h | F1 (attack) | AUROC | Default rule FA/h |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, d in result["detectors"].items():
        for split, a in d["aggregate"].items():

            def cell(key, a=a):
                v = a.get(key) or {}
                return f"{_fmt(v.get('median'))} ({_fmt(v.get('worst'))})"

            lines.append(
                f"| `{name}` | {split} | {cell('episode_detection_fa1')}"
                f" | {cell('episode_detection_fa10')} | {cell('f1')} | {cell('auc_roc')}"
                f" | {cell('fa_per_hour_default')} |"
            )
    lines += [
        "",
        "## Quality against cost",
        "",
        "Quality: episodes detected at ≤ 10 false alarms per hour, unknown vehicle and known "
        "attacks, median over sets. Size: pickled model; host time: Python scoring per frame "
        "(not device latency). Pareto-optimal detectors are marked.",
        "",
        "| Detector | Quality | Size (KB) | Host µs/frame | Pareto |",
        "|---|---|---|---|---|",
    ]
    for r in result["pareto"]:
        lines.append(
            f"| `{r['detector']}` | {_fmt(r['quality'])} | {_fmt(r['size_kb'], 1)} | "
            f"{_fmt(r['host_us'], 2)} | {'yes' if r['pareto'] else ''} |"
        )
    pf = result["detectors"].get("picket-forest", {}).get("sets", {})
    checks = [(s, r["parity"]) for s, r in pf.items() if "parity" in r]
    if checks:
        lines += [
            "",
            "## Deterministic check: C versus Python",
            "",
            "picket-forest's C chain (host build, `-ffp-contract=off`) against the Python "
            "reference on every test frame.",
            "",
            "| Set | Frames | Mismatches |",
            "|---|---|---|",
        ]
        lines += [f"| {s} | {p['frames']} | {p['mismatches']} |" for s, p in checks]
    road = result.get("road")
    if road:
        lines += [
            "",
            "## ROAD (a fifth vehicle from another dataset)",
            "",
            f"Model: {road['model']}. Masquerade and accelerator captures are out of scope "
            "and reported separately.",
            "",
            "| Part | Captures | F1 (attack) | ≤ 10 FA/h detection | Default rule FA/h |",
            "|---|---|---|---|---|",
        ]
        for part in ("in_scope", "out_of_scope"):
            r = road.get(part)
            if r:
                lines.append(
                    f"| {part} | {r['captures']} | {_fmt(r['frame']['f1'])} | "
                    f"{_fmt(_headline(r, '10'))} | {_fmt(r['default_rule']['false_alarms_per_hour'])} |"
                )
    lines += ["", "## Per attack family (picket-forest, attack-class recall, median over sets)", ""]
    fams: dict[tuple, list] = defaultdict(list)
    for s in pf.values():
        for split, r in (s.get("splits") or {}).items():
            for fam, m in (r.get("families") or {}).items():
                fams[(split, fam)].append(m["recall"])
    lines += ["| Split | Family | Recall |", "|---|---|---|"]
    lines += [
        f"| {sp} | {fa} | {_fmt(float(np.nanmedian(v)))} |" for (sp, fa), v in sorted(fams.items())
    ]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")


def write_quality(result: dict, path: Path, model: str, version: str) -> None:
    """quality.json of the release from a complete run (refused for partial runs)."""
    if result["partial"]:
        raise ValueError("a partial run cannot feed the quality results")
    agg = result["detectors"]["picket-forest"]["aggregate"]
    today = result["date"]
    ref = "can-train-and-test attack labels (official splits)"
    n_sets = len(result["sets"])
    metrics = []
    for split, a in agg.items():
        for key, label in (
            ("episode_detection_fa10", "share of attack episodes detected at <= 10 false alarms/h"),
            ("episode_detection_fa1", "share of attack episodes detected at <= 1 false alarm/h"),
            ("f1", "attack-class F1 per frame"),
            ("fa_per_hour_default", "false alarms per hour of the default alarm rule"),
        ):
            for agg_name in ("median", "worst"):
                v = (a.get(key) or {}).get(agg_name)
                if v is None:
                    continue
                metrics.append(
                    {
                        "name": f"{key}_{split}_{agg_name}",
                        "value": float(v),
                        "unit": None,
                        "description": (
                            f"{label}, {split.replace('_', ' ')}, {agg_name} over {n_sets} sets"
                        ),
                        "reference": ref,
                        "benchmark": result["benchmark"],
                        "n_items": n_sets,
                        "hardware": None,
                        "date": today,
                    }
                )
    road = (result.get("road") or {}).get("in_scope")
    if road:
        for key, v, label in (
            ("f1_road", road["frame"]["f1"], "attack-class F1 per frame on ROAD"),
            (
                "episode_detection_fa10_road",
                _headline(road, "10"),
                "episodes detected at <= 10 FA/h on ROAD",
            ),
        ):
            if v is not None:
                metrics.append(
                    {
                        "name": key,
                        "value": float(v),
                        "unit": None,
                        "description": label,
                        "reference": "ROAD injection labels",
                        "benchmark": result["benchmark"],
                        "n_items": road["captures"],
                        "hardware": None,
                        "date": today,
                    }
                )
    data = {
        "kind": "quality",
        "model": model,
        "version": version,
        "synthetic": False,
        "source_run": f"topics/security/reports/picket-forest/can-ids-v1 ({result['code_commit'][:12]})",
        "metrics": metrics,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")
