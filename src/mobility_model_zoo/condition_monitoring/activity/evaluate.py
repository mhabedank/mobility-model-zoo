"""pace-cnn evaluation on the frozen benchmark uci-har-v1 (feature 021, research R5, R6, R21, R22).

    uv run condmon activity evaluate [--version 0.1.0]
    uv run condmon activity reproduce

`evaluate` runs the frozen test split through the bit-exact int8 host reference of every
pre-registered run and writes

    topics/condition-monitoring/reports/pace-cnn/<version>/evaluation.json   full results
    topics/condition-monitoring/reports/pace-cnn/<version>/verdict.json      status by rule
    topics/condition-monitoring/reports/pace-cnn/<version>/README.md         short summary
    zoo/models/pace-cnn/results/<version>/quality.json                       card metrics

It needs no TensorFlow: the float results and the interpreter check come from the run reports that
`train` wrote. The status is derived from the committed criteria record, never chosen by hand; the
budget criteria use `zoo/models/pace-cnn/results/<version>/performance.json` once it exists.
Per-subject results are reported by rank only, never under the dataset's subject numbers (FR-028).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import numpy as np

from mobility_model_zoo.condition_monitoring import benchmark as bm
from mobility_model_zoo.condition_monitoring.activity import train as pace

REFERENCE = "labels of the uci-har dataset"
INT8_HARDWARE = "host (bit-exact int8 reference)"
FLOAT_HARDWARE = "host (float32 Keras model, informative)"
# Facts about this release that the criteria refer to: 0.1.0 is trained and measured on UCI HAR
# only, so transfer to mobility data is not tested (spec FR-001, FR-019).
FACTS = {"transfer_tested": False}
BUDGET_METRICS = ("flash_kb", "ram_kb", "latency_us")


class EvaluationRefused(Exception):
    pass


class DeterministicCheckFailed(Exception):
    pass


# ---- paths -------------------------------------------------------------------------------------


def report_dir(version: str) -> Path:
    return bm.repo() / "topics" / bm.TOPIC / "reports" / pace.NAME / version


def results_dir(version: str) -> Path:
    return bm.repo() / "zoo" / "models" / pace.NAME / "results" / version


def run_dir(seed: int) -> Path:
    from mobility_model_zoo.edge.paths import derived_dir

    return derived_dir(pace.NAME) / f"seed-{seed}"


def reproduction_file() -> Path:
    from mobility_model_zoo.edge.paths import derived_dir

    return derived_dir(pace.NAME) / "reproduction.json"


# ---- metrics -----------------------------------------------------------------------------------


def f1_per_class(y: np.ndarray, pred: np.ndarray, n: int) -> list[float]:
    """F1 of each class (a class absent from labels and predictions counts as 0), as in
    `keras_export.macro_f1`."""
    out = []
    for c in range(n):
        tp = int(((pred == c) & (y == c)).sum())
        fp = int(((pred == c) & (y != c)).sum())
        fn = int(((pred != c) & (y == c)).sum())
        out.append(2 * tp / max(2 * tp + fp + fn, 1))
    return out


def confusion(y: np.ndarray, pred: np.ndarray, n: int) -> list[list[int]]:
    m = np.zeros((n, n), np.int64)
    np.add.at(m, (y, pred), 1)
    return m.tolist()


def int8_predictions(npz: Path, x_norm: np.ndarray) -> np.ndarray:
    from mobility_model_zoo.edge.int8.model import QModel
    from mobility_model_zoo.edge.int8.quant import quantize
    from mobility_model_zoo.edge.int8.reference import run_batch

    qm = QModel.load(npz)
    xq = quantize(x_norm.reshape(len(x_norm), -1), qm.input_scale, qm.input_zp)
    return run_batch(qm, xq).argmax(1)


def normalised(manifest: dict, x: np.ndarray) -> np.ndarray:
    mean = np.asarray(manifest["normalisation"]["mean"], np.float32)
    std = np.asarray(manifest["normalisation"]["std"], np.float32)
    return ((x - mean) / std)[:, None, :, :].astype(np.float32)


# ---- verdict -----------------------------------------------------------------------------------


def _compare(value: float, op: str, threshold: float) -> bool:
    return {">=": value >= threshold, ">": value > threshold, "<": value < threshold}[op]


def _budgets(criteria: dict, performance: dict | None) -> dict[str, Any]:
    """Budget evidence on the reference board: values, origin, whether they are met."""
    b = criteria["budgets"]
    threshold = (
        f"flash_kb <= {b['flash_kb']}, ram_kb <= {b['ram_kb']}, latency_us <= {b['latency_us']} "
        f"on {b['reference_hardware']}"
    )
    if performance is None:
        return {"threshold": threshold, "measured": None, "note": "not measured"}
    rows = {m["name"]: m for m in performance["metrics"]}
    if any(n not in rows for n in BUDGET_METRICS):
        return {"threshold": threshold, "measured": None, "note": "not measured"}
    measured = {n: rows[n]["value"] for n in BUDGET_METRICS}
    origins = sorted({rows[n].get("origin", "unknown") for n in BUDGET_METRICS})
    within = all(measured[n] <= b[n] for n in BUDGET_METRICS)
    out = {"threshold": threshold, "measured": {**measured, "origin": ", ".join(origins)}}
    if origins != ["real_board"]:
        out["note"] = f"not measured on the reference board (origin {', '.join(origins)})"
        out["real_board"] = False
    else:
        out["real_board"] = True
    out["within"] = within
    return out


def derive_verdict(
    criteria: dict, metrics: dict, performance: dict | None, facts: dict
) -> dict[str, Any]:
    """Each success and kill criterion with its measured value; `released` only if every success
    criterion is met and no kill criterion fires (FR-018, contracts/records.md)."""
    budgets = _budgets(criteria, performance)
    rows, reasons = [], []
    for c in criteria["success"]:
        row: dict[str, Any] = {"id": c["id"]}
        if "metric" in c:
            value = metrics[c["metric"]]
            row |= {
                "measured": value,
                "threshold": f"{c['metric']} {c['op']} {c['value']}",
                "met": _compare(value, c["op"], c["value"]),
            }
            reason = f"{c['id']} {c['metric']} = {value:.4f} (needs {c['op']} {c['value']})"
        elif "budgets_on_reference_board" in c:
            row |= {"measured": budgets["measured"], "threshold": budgets["threshold"]}
            row["met"] = bool(budgets.get("real_board") and budgets.get("within"))
            if "note" in budgets:
                row["note"] = budgets["note"]
            reason = f"{c['id']} budgets on the reference board: " + (
                budgets.get("note") or f"exceeded ({budgets['measured']})"
            )
        else:  # a fact about the release
            value = facts[c["fact"]]
            row |= {"measured": value, "threshold": f"{c['fact']} = {c['value']}"}
            row["met"] = value == c["value"]
            reason = f"{c['id']} {c['fact'].replace('_', ' ')}: {value} (UCI HAR only)"
        rows.append(row)
        if not row["met"]:
            reasons.append(reason)
    fired, kill_rows = [], []
    for k in criteria["kill"]:
        if "metric" in k:
            value = metrics[k["metric"]]
            hit = _compare(value, k["op"], k["value"])
            kill_rows.append({"id": k["id"], "measured": value, "fired": hit})
        elif "difference" in k:
            a, b = (s.strip() for s in k["difference"].split("-"))
            value = metrics[a] - metrics[b]
            hit = _compare(value, k["op"], k["value"])
            kill_rows.append({"id": k["id"], "measured": value, "fired": hit})
        else:  # budgets exceeded on the reference board
            hit = bool(budgets.get("real_board") and budgets.get("within") is False)
            row = {"id": k["id"], "measured": budgets["measured"], "fired": hit}
            if "note" in budgets:
                row["note"] = budgets["note"]
            kill_rows.append(row)
        if hit:
            fired.append(k["id"])
            reasons.append(f"{k['id']} kill criterion fired ({kill_rows[-1]['measured']})")
    released = all(r["met"] for r in rows) and not fired
    return {
        "criteria_version": criteria["version"],
        "criteria": rows,
        "kill": {"fired": fired, "outcome": "kill" if fired else "none"},
        "kill_checks": kill_rows,
        "status": "released" if released else "experimental",
        "reasons": reasons,
    }


# ---- runs --------------------------------------------------------------------------------------


def load_criteria() -> tuple[dict, Path]:
    import yaml

    path = pace.criteria_path()
    if not path.exists():
        raise EvaluationRefused(f"criteria record {path} is missing")
    return yaml.safe_load(path.read_text(encoding="utf-8")), path


def load_runs(criteria: dict, criteria_file: Path, manifest_file: Path) -> list[dict]:
    """The run reports of every pre-registered seed; refuse runs of another manifest or criteria."""
    manifest_sha = bm.file_sha256(manifest_file)
    criteria_sha = bm.file_sha256(criteria_file)
    seeds = [criteria["seeds"]["candidate"], *criteria["seeds"]["spread"]]
    runs = []
    for seed in seeds:
        path = run_dir(seed) / f"{pace.NAME}.report.json"
        if not path.exists():
            raise EvaluationRefused(
                f"run of seed {seed} is missing: condmon activity train --seed {seed}"
            )
        rep = json.loads(path.read_text(encoding="utf-8"))
        if rep.get("manifest_sha256") != manifest_sha:
            raise EvaluationRefused(f"seed {seed} was trained on another benchmark manifest")
        if (
            rep.get("criteria_version") != criteria["version"]
            or rep.get("criteria_sha256") != criteria_sha
        ):
            raise EvaluationRefused(f"seed {seed} was trained under another criteria version")
        if rep.get("seed", seed) != seed:
            raise EvaluationRefused(f"{path} holds seed {rep.get('seed')}, not {seed}")
        runs.append(rep)
    return runs


def fidelity_check(parts: dict) -> dict:
    """Informative check of the input preparation (research R11): the gravity separation of
    `prepare.py` applied to the training subjects' total acceleration, compared with the
    dataset's body acceleration."""
    from mobility_model_zoo.condition_monitoring.activity import prepare

    return prepare.fidelity_report(parts["train"].x)


def _quality_rows(values: dict, n_test: int, n_subjects: int, n_runs: int, date: str) -> list[dict]:
    def row(name, description, n_items, hardware=INT8_HARDWARE, unit=None):
        return {
            "name": name,
            "value": values[name],
            "unit": unit,
            "description": description,
            "reference": REFERENCE,
            "benchmark": pace.BENCHMARK["id"],
            "n_items": n_items,
            "hardware": hardware,
            "date": date,
        }

    rows = [
        row("int8_macro_f1", "int8 macro-F1 over the six activities, test subjects", n_test),
        row("int8_accuracy", "int8 accuracy, test subjects", n_test),
        row("int8_f1_min_class", "lowest int8 F1 of the six activities", n_test),
    ]
    rows += [
        row(f"int8_f1_{c}", f"int8 F1 of activity {c.replace('_', ' ')}", n_test) for c in pace.LABELS
    ]
    rows += [
        row(
            "int8_macro_f1_worst_subject",
            "int8 macro-F1 of the worst test subject",
            n_subjects,
        ),
        row(
            "int8_macro_f1_subject_range",
            "best minus worst test subject, int8 macro-F1",
            n_subjects,
        ),
        row("int8_macro_f1_seed_min", "lowest int8 macro-F1 over the five seeds", n_runs),
        row("int8_macro_f1_seed_mean", "mean int8 macro-F1 over the five seeds", n_runs),
        row("int8_macro_f1_seed_max", "highest int8 macro-F1 over the five seeds", n_runs),
        row(
            "float_macro_f1",
            "float macro-F1 of the same model before quantisation (informative)",
            n_test,
            FLOAT_HARDWARE,
        ),
        row(
            "float_accuracy", "float accuracy before quantisation (informative)", n_test, FLOAT_HARDWARE
        ),
        row(
            "tflite_interpreter_mismatches",
            "test windows where the int8 host reference and the TFLite reference interpreter "
            "disagree (deterministic check)",
            n_test,
            unit="windows",
        ),
    ]
    return rows


def _readme(version: str, values: dict, verdict: dict, n_test: int) -> str:
    lines = [
        f"# pace-cnn {version}: evaluation on uci-har-v1",
        "",
        "Generated by `uv run condmon activity evaluate`; do not edit. All values are int8 results "
        f"on the bit-exact host reference, measured against the {REFERENCE} on {n_test} test "
        "windows, unless the name starts with `float_`.",
        "",
        f"- **Status (by rule):** `{verdict['status']}`",
        f"- **int8 macro-F1:** {values['int8_macro_f1']:.4f}",
        f"- **int8 accuracy:** {values['int8_accuracy']:.4f}",
        f"- **Lowest class F1:** {values['int8_f1_min_class']:.4f}",
        f"- **Worst test subject, macro-F1:** {values['int8_macro_f1_worst_subject']:.4f}",
        f"- **Seed spread, macro-F1:** {values['int8_macro_f1_seed_min']:.4f} – "
        f"{values['int8_macro_f1_seed_max']:.4f}",
        f"- **Interpreter mismatches:** {values['tflite_interpreter_mismatches']}",
        "",
        "## Missed criteria",
        "",
    ]
    lines += [f"- {r}" for r in verdict["reasons"]] or ["- none"]
    lines += ["", "Files: `evaluation.json` (all results), `verdict.json` (criteria and status).", ""]
    return "\n".join(lines)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def evaluate(version: str = "0.1.0") -> dict:
    criteria, criteria_file = load_criteria()
    manifest_file = pace.manifest_path()
    try:
        manifest = bm.load_manifest(manifest_file)
    except bm.NotFrozen as e:
        raise EvaluationRefused(str(e)) from None
    runs = load_runs(criteria, criteria_file, manifest_file)
    try:
        parts = pace.frozen_splits(manifest)
    except bm.SplitChanged as e:
        raise EvaluationRefused(str(e)) from None
    bad = {
        r["seed"]: r["tflite_interpreter_mismatches"] for r in runs if r["tflite_interpreter_mismatches"]
    }
    if bad:
        raise DeterministicCheckFailed(f"interpreter mismatches per seed: {bad}")

    test = parts["test"]
    x = normalised(manifest, test.x)
    n_classes = len(pace.LABELS)
    seeds = [r["seed"] for r in runs]
    preds = {s: int8_predictions(run_dir(s) / f"{pace.NAME}.npz", x) for s in seeds}
    seed_f1 = {s: float(np.mean(f1_per_class(test.y, preds[s], n_classes))) for s in seeds}

    cand = criteria["seeds"]["candidate"]
    cand_run = next(r for r in runs if r["seed"] == cand)
    pred = preds[cand]
    per_class = f1_per_class(test.y, pred, n_classes)
    per_subject = sorted(
        float(np.mean(f1_per_class(test.y[m], pred[m], n_classes)))
        for m in (test.subjects == s for s in sorted(set(test.subjects.tolist())))
    )
    values: dict[str, Any] = {
        "int8_macro_f1": float(np.mean(per_class)),
        "int8_accuracy": float((pred == test.y).mean()),
        "int8_f1_min_class": float(min(per_class)),
        **{f"int8_f1_{c}": float(f) for c, f in zip(pace.LABELS, per_class, strict=True)},
        "int8_macro_f1_worst_subject": per_subject[0],
        "int8_macro_f1_subject_range": per_subject[-1] - per_subject[0],
        "int8_macro_f1_seed_min": min(seed_f1.values()),
        "int8_macro_f1_seed_mean": float(np.mean(list(seed_f1.values()))),
        "int8_macro_f1_seed_max": max(seed_f1.values()),
        "float_macro_f1": float(cand_run["float_macro_f1"]),
        "float_accuracy": float(cand_run["float_accuracy"]),
        "tflite_interpreter_mismatches": int(cand_run["tflite_interpreter_mismatches"]),
    }

    perf_path = results_dir(version) / "performance.json"
    performance = json.loads(perf_path.read_text()) if perf_path.exists() else None
    verdict = derive_verdict(criteria, values, performance, FACTS)

    # The evaluation is a deterministic function of the runs: date it by the latest run.
    date = max(r["trained_at"] for r in runs)[:10]
    n_test, n_subjects = int(len(test.y)), len(set(test.subjects.tolist()))
    reproduction = json.loads(reproduction_file().read_text()) if reproduction_file().exists() else None
    evaluation = {
        "model": pace.NAME,
        "version": version,
        "benchmark": pace.BENCHMARK["id"],
        "reference": REFERENCE,
        "criteria_version": criteria["version"],
        "model_sha256": cand_run["npz_sha256"],
        "weights_sha256": cand_run.get("weights_sha256"),
        "runs": [
            {
                "seed": r["seed"],
                "manifest_sha256": r["manifest_sha256"],
                "criteria_version": r["criteria_version"],
                "criteria_commit": r["criteria_commit"],
                "npz_sha256": r["npz_sha256"],
                "weights_sha256": r.get("weights_sha256"),
                "trained_at": r["trained_at"],
                "int8_macro_f1": seed_f1[r["seed"]],
                "tflite_interpreter_mismatches": r["tflite_interpreter_mismatches"],
            }
            for r in runs
        ],
        "test": {"windows": n_test, "subjects": n_subjects},
        "metrics": values,
        "per_class": [
            {"class": c, "f1": float(f), "support": int((test.y == i).sum())}
            for i, (c, f) in enumerate(zip(pace.LABELS, per_class, strict=True))
        ],
        "confusion_matrix": {
            "labels": pace.LABELS,
            "rows": "dataset label",
            "columns": "int8 prediction",
            "counts": confusion(test.y, pred, n_classes),
        },
        "per_subject_macro_f1": per_subject,
        "validation": cand_run.get("validation"),
        "fidelity": fidelity_check(parts),
        "reproduction": reproduction,
        "date": date,
    }
    quality = {
        "kind": "quality",
        "model": pace.NAME,
        "version": version,
        "synthetic": False,
        "source_run": (
            f"condmon activity evaluate, seeds {seeds}, criteria v{criteria['version']}, "
            f"benchmark {pace.BENCHMARK['id']}"
        ),
        "metrics": _quality_rows(values, n_test, n_subjects, len(runs), date),
    }
    out = report_dir(version)
    _write_json(out / "evaluation.json", evaluation)
    _write_json(out / "verdict.json", verdict)
    (out / "README.md").write_text(_readme(version, values, verdict, n_test), encoding="utf-8")
    _write_json(results_dir(version) / "quality.json", quality)
    return verdict


def reproduce() -> dict:
    """Retrain the candidate seed into a temporary folder and compare its model parameters with
    the stored run (FR-013). The result is written next to the runs and copied into
    `evaluation.json` by the next `evaluate`."""
    import tempfile

    criteria, _ = load_criteria()
    seed = criteria["seeds"]["candidate"]
    stored_path = run_dir(seed) / f"{pace.NAME}.report.json"
    if not stored_path.exists():
        raise EvaluationRefused(f"run of seed {seed} is missing")
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        again = pace.main(["--seed", str(seed), "--out", tmp])
    identical = again["weights_sha256"] == stored["weights_sha256"]
    result: dict[str, Any] = {
        "seed": seed,
        "identical": identical,
        "compared": "weights_sha256: model parameters without the meta block, which holds the "
        "training time",
        "checked_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tensorflow": again.get("tensorflow"),
        "platform": again.get("platform"),
    }
    if not identical:
        keys = ("int8_macro_f1", "int8_accuracy", "float_macro_f1", "float_accuracy")
        result["deviation"] = {k: again[k] - stored[k] for k in keys}
    _write_json(reproduction_file(), result)
    return result
