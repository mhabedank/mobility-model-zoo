"""`zoo tracking import`: past results as runs marked `imported` (US5, FR-028, research R13).

One run per existing result, created once and found again by `tags.mmz.import_key`:
* `zoo/models/<model>/results/<version>/{quality,performance}.json` with the release record's date,
  benchmark, recipe commit and usage (`<model>@<version>`);
* `topics/productdev/benchmarks/cluster-v1/decision.json` (`cluster-v1/decision`);
* the condition-monitoring research reports, scalar numbers only (`<model>/research-report`).

Nothing is reconstructed: a value missing in the source stays missing, and no curve is invented.
Like `zoo data publish`, a server error raises (exit 8) instead of degrading quietly.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from . import guard
from .publish import TrackingUnavailable

SKIP_MODELS = frozenset({"sandbox-pipeline-tiny"})  # a test model of the release pipeline
# The model's task (model.yaml) decides the experiment, as for live runs.
EXPERIMENT_BY_TASK = {
    "jtbd": "productdev/jtbd-span",
    "jtbd-cluster": "productdev/jtbd-cluster",
    "can-ids": "security/can-ids",
    "sound-anomaly": "condition-monitoring/sound-anomaly",
    "activity": "condition-monitoring/activity",
}
DECISIONS = (("cluster-v1", "topics/productdev/benchmarks/cluster-v1/decision.json"),)
REPORTS = (
    ("hum-fan", "topics/condition-monitoring/reports/hum-fan/research-report.json"),
    ("pace-cnn", "topics/condition-monitoring/reports/pace-cnn/research-report.json"),
)


@dataclass
class Record:
    """One source record, ready to become one run."""

    key: str
    experiment: str
    model: str | None
    time_ms: int | None
    tags: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: list[Path] = field(default_factory=list)
    benchmark: str | None = None


@dataclass
class Action:
    key: str
    action: str  # created | exists | create (dry run)
    run_id: str | None = None
    note: str = ""


def _ms(value: Any) -> int | None:
    if isinstance(value, datetime):
        stamp = value if value.tzinfo else value.replace(tzinfo=UTC)
    elif isinstance(value, date):
        stamp = datetime(value.year, value.month, value.day, tzinfo=UTC)
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        stamp = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    else:
        return None
    return int(stamp.timestamp() * 1000)


def _git_date(root: Path, path: Path) -> int | None:
    out = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%cI", "--", str(path.relative_to(root))],
        capture_output=True,
        text=True,
        check=False,
    )
    return _ms(out.stdout.strip()) if out.returncode == 0 else None


def _model_info(root: Path, model: str) -> tuple[str | None, str | None]:
    path = root / "zoo/models" / model / "model.yaml"
    if not path.is_file():
        return None, None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("task"), data.get("topic")


def _numbers(metrics: dict[str, float], name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return  # missing values stay missing
    metrics[guard.sanitize_key(name)] = value


def model_records(root: Path) -> list[Record]:
    records = []
    for results in sorted((root / "zoo/models").glob("*/results/*")):
        model, version = results.parent.parent.name, results.name
        if model in SKIP_MODELS or not results.is_dir():
            continue
        task, topic = _model_info(root, model)
        if task not in EXPERIMENT_BY_TASK:
            continue
        release = root / "zoo/models" / model / "releases" / f"{version}.yaml"
        record = yaml.safe_load(release.read_text(encoding="utf-8")) if release.is_file() else {}
        record = record or {}
        benchmark = (record.get("evaluation") or {}).get("benchmark")
        usage = record.get("usage") or {}
        rec = Record(
            key=f"{model}@{version}",
            experiment=EXPERIMENT_BY_TASK[task],
            model=model,
            time_ms=_ms(record.get("date")),
            benchmark=benchmark,
        )
        rec.tags = {
            "mmz.task": task,
            "mmz.topic": topic,
            "mmz.model": model,
            "mmz.model_version": version,
            "mmz.benchmark": benchmark,
            "mmz.git_commit": (record.get("recipe") or {}).get("git_commit"),
        }
        rec.params = {"usage.class": usage.get("class"), "usage.licence": usage.get("licence")}
        for kind in ("quality", "performance"):
            path = results / f"{kind}.json"
            if not path.is_file():
                continue
            rec.artifacts.append(path)
            for metric in json.loads(path.read_text(encoding="utf-8")).get("metrics", []):
                name = metric.get("name", "")
                if guard.sanitize_key(name) in rec.metrics:  # the same name in both files
                    name = f"{kind}.{name}"
                _numbers(rec.metrics, name, metric.get("value"))
        records.append(rec)
    return records


def decision_records(root: Path) -> list[Record]:
    records = []
    for benchmark, rel in DECISIONS:
        path = root / rel
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rec = Record(
            key=f"{benchmark}/decision",
            experiment=EXPERIMENT_BY_TASK["jtbd-cluster"],
            model=None,
            time_ms=_ms(data.get("decided_at")),
            benchmark=data.get("benchmark_version") or benchmark,
        )
        rec.tags = {
            "mmz.task": "jtbd-cluster",
            "mmz.topic": "productdev",
            "mmz.benchmark": rec.benchmark,
        }
        rec.params = {"split": data.get("split"), "final": data.get("final")}
        for level, values in (data.get("levels") or {}).items():
            _numbers(rec.metrics, f"{level}.value", values.get("value"))
            _numbers(rec.metrics, f"{level}.threshold", values.get("threshold"))
            rec.params[f"{level}.decision"] = values.get("decision")
        _numbers(rec.metrics, "reruns_used", data.get("reruns_used"))
        records.append(rec)
    return records


def report_records(root: Path) -> list[Record]:
    records = []
    for model, rel in REPORTS:
        path = root / rel
        if not path.is_file():
            continue
        task, topic = _model_info(root, model)
        if task not in EXPERIMENT_BY_TASK:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rec = Record(
            key=f"{model}/research-report",
            experiment=EXPERIMENT_BY_TASK[task],
            model=model,
            time_ms=_git_date(root, path),
        )
        rec.tags = {"mmz.task": task, "mmz.topic": topic, "mmz.model": model}
        rec.params = {"report_version": data.get("version")}
        for name, value in data.items():
            _numbers(rec.metrics, name, value)  # scalar numbers only; texts and lists stay out
        records.append(rec)
    return records


def records(root: Path, models: list[str] | None = None) -> list[Record]:
    found = model_records(root) + decision_records(root) + report_records(root)
    if not models:
        return found
    # a model name, or the benchmark of a decision (`cluster-v1`)
    return [r for r in found if r.model in models or r.key.split("/")[0] in models]


def _resolve(benchmark: str, inventory) -> Any:
    from mobility_model_zoo.datasets.inventory import find

    if inventory is None:
        from . import _inventory

        try:
            inventory = _inventory()
        except Exception:  # noqa: BLE001 - an unreadable overview leaves the input unresolved
            return None
    rows = find(inventory, benchmark)
    return rows[0] if len(rows) == 1 and rows[0].sha256 else None


def _exists(client, exp_id: str, key: str) -> list:
    return client.search_runs([exp_id], filter_string=f"tags.`mmz.import_key` = '{key}'", max_results=5)


def _create(client, exp_id: str, rec: Record, inventory) -> str:
    from mlflow.entities import Dataset, DatasetInput, InputTag, Metric, Param

    tags = {**rec.tags, "mmz.imported": "true", "mmz.import_key": rec.key}
    row = _resolve(rec.benchmark, inventory) if rec.benchmark else None
    if rec.benchmark and row is None:
        tags["mmz.input_unresolved"] = rec.benchmark
    run = client.create_run(
        exp_id,
        start_time=rec.time_ms,
        run_name=rec.key,
        tags={k: guard.check_tag(k, v) for k, v in tags.items() if v is not None},
    )
    run_id = run.info.run_id
    ts = rec.time_ms or run.info.start_time
    metrics = [Metric(k, guard.check_metric(k, v), ts, 0) for k, v in rec.metrics.items()]
    params = [Param(k, guard.check_param(k, v)) for k, v in rec.params.items() if v is not None]
    for i in range(0, max(len(metrics), 1), 1000):
        client.log_batch(
            run_id, metrics=metrics[i : i + 1000], params=params if i == 0 else [], synchronous=True
        )
    if row is not None:
        dataset = Dataset(
            name=row.name,
            digest=row.sha256[:16],
            source_type="zoo",
            source=row.source,
            profile=json.dumps({"counts": row.counts, "distribution": row.distribution}, sort_keys=True),
        )
        client.log_inputs(
            run_id, [DatasetInput(dataset, [InputTag("mlflow.data.context", "evaluation")])]
        )
    for path in rec.artifacts:
        client.log_artifact(run_id, str(guard.check_artifact(path)))
    client.set_terminated(run_id, "FINISHED", end_time=ts)
    return run_id


def import_results(
    root: Path | None = None,
    models: list[str] | None = None,
    dry_run: bool = False,
    inventory=None,
) -> list[Action]:
    from mobility_model_zoo.edge.paths import repo_root

    from . import client as tc
    from . import config

    found = records(root or repo_root(), models)
    if not config.tracking_uri():
        if dry_run:
            return [Action(r.key, "create", note="no server asked (no tracking URI)") for r in found]
        raise TrackingUnavailable("no MLFLOW_TRACKING_URI; set it in .env (docs/tracking.md)")
    if not config.client_installed():
        raise TrackingUnavailable("the tracking client is not installed: uv sync --extra tracking")
    actions = []
    try:
        client = tc.new_client()
        for rec in found:
            exp = client.get_experiment_by_name(rec.experiment)
            existing = _exists(client, exp.experiment_id, rec.key) if exp else []
            if existing:
                actions.append(Action(rec.key, "exists", existing[0].info.run_id))
            elif dry_run:
                actions.append(Action(rec.key, "create"))
            else:
                exp_id = exp.experiment_id if exp else client.create_experiment(rec.experiment)
                actions.append(Action(rec.key, "created", _create(client, exp_id, rec, inventory)))
    except guard.GuardRefused:
        raise
    except Exception as e:  # noqa: BLE001
        raise TrackingUnavailable(f"tracking server: {e.__class__.__name__}: {str(e)[:200]}") from None
    return actions
