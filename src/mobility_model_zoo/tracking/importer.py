"""`zoo tracking import`: past results as runs marked `imported` (FR-028, research R13).

One run per source record, created once (keyed by `mmz.import_key`):
* every model version with `zoo/models/<model>/results/<version>/` (quality and performance metrics,
  release date, benchmark, recipe commit from the release record), except sandbox test models;
* the cluster-v1 decision (`topics/productdev/benchmarks/cluster-v1/decision.json`);
* the condition-monitoring research reports
  (`topics/condition-monitoring/reports/*/research-report.json`).

Start, end and metric times are the record's date. Nothing is reconstructed: no curves, and a value
missing from a record stays missing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from . import guard

SANDBOX = {"sandbox-pipeline-tiny"}


@dataclass
class Source:
    key: str  # mmz.import_key
    experiment: str
    task: str
    topic: str
    name: str
    date: str  # ISO date of the record
    metrics: dict[str, float]
    tags: dict[str, str]
    benchmark: str | None = None
    artifacts: tuple[Path, ...] = ()


def _ms(day: str) -> int:
    return int(datetime.fromisoformat(str(day)[:10]).replace(tzinfo=UTC).timestamp() * 1000)


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and value == value


def _results_metrics(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    if not path.is_file():
        return out
    for m in json.loads(path.read_text(encoding="utf-8")).get("metrics") or []:
        if not _number(m.get("value")):
            continue
        key = guard.sanitize_key(m["name"])
        if key in out and m.get("hardware"):
            key = f"{key}.{guard.sanitize_key(m['hardware'])}"[:120]
        out[key] = float(m["value"])
    return out


def sources(root: Path) -> list[Source]:
    from . import model_experiment

    out: list[Source] = []
    for results in sorted((root / "zoo" / "models").glob("*/results/*")):
        model, version = results.parents[1].name, results.name
        if model in SANDBOX or not results.is_dir():
            continue
        experiment, topic, task = model_experiment(model)
        record_path = root / "zoo" / "models" / model / "releases" / f"{version}.yaml"
        record = yaml.safe_load(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
        quality, performance = results / "quality.json", results / "performance.json"
        metrics = {**_results_metrics(quality), **_results_metrics(performance)}
        benchmark = (record.get("evaluation") or {}).get("benchmark")
        dates = [
            m.get("date")
            for p in (quality, performance)
            if p.is_file()
            for m in json.loads(p.read_text(encoding="utf-8")).get("metrics") or []
            if m.get("date")
        ]
        out.append(
            Source(
                key=f"{model}@{version}",
                experiment=experiment,
                task=task,
                topic=topic,
                name=f"{model}-{version}",
                date=str(record.get("date") or max(dates, default="1970-01-01")),
                metrics=metrics,
                tags={
                    "mmz.model": model,
                    "mmz.model_version": version,
                    "mmz.benchmark": benchmark,
                    "mmz.git_commit": (record.get("recipe") or {}).get("git_commit"),
                },
                benchmark=benchmark,
                artifacts=tuple(p for p in (quality, performance) if p.is_file()),
            )
        )
    decision = root / "topics" / "productdev" / "benchmarks" / "cluster-v1" / "decision.json"
    if decision.is_file():
        d = json.loads(decision.read_text(encoding="utf-8"))
        levels = {f"{k}.value": v.get("value") for k, v in (d.get("levels") or {}).items()}
        levels |= {f"{k}.threshold": v.get("threshold") for k, v in (d.get("levels") or {}).items()}
        out.append(
            Source(
                key="cluster-v1/decision",
                experiment="productdev/jtbd-cluster",
                task="jtbd-cluster",
                topic="productdev",
                name="cluster-v1-decision",
                date=str(d.get("decided_at") or "")[:10],
                metrics={k: float(v) for k, v in levels.items() if _number(v)},
                tags={"mmz.benchmark": d.get("benchmark_version")},
                benchmark=d.get("benchmark_version"),
            )
        )
    for report in sorted(
        (root / "topics" / "condition-monitoring" / "reports").glob("*/research-report.json")
    ):
        model = report.parent.name
        experiment, topic, task = model_experiment(model)
        data = json.loads(report.read_text(encoding="utf-8"))
        last = _git_date(root, report) or "1970-01-01"
        out.append(
            Source(
                key=f"{model}/research-report",
                experiment=experiment,
                task=task,
                topic=topic,
                name=f"{model}-research-report",
                date=last,
                metrics={guard.sanitize_key(k): float(v) for k, v in data.items() if _number(v)},
                tags={"mmz.model": model},
            )
        )
    return out


def _git_date(root: Path, path: Path) -> str | None:
    from mobility_model_zoo.datasets.inventory import history

    return history.last_change(root, path.relative_to(root).as_posix()) if history.in_git(root) else None


def import_all(
    root: Path | None = None, models: list[str] | None = None, dry_run: bool = False
) -> list[tuple[str, str]]:
    """(import key, `created` | `exists` | `would create`) per source."""
    from mlflow.entities import Metric, RunTag

    from mobility_model_zoo.edge.paths import repo_root

    from . import client as tc
    from . import data_ref

    root = Path(root) if root else repo_root()
    chosen = [s for s in sources(root) if not models or s.tags.get("mmz.model") in models]
    cl = tc.new_client()
    results = []
    for src in chosen:
        found = cl.get_experiment_by_name(src.experiment)
        if found is not None:
            existing = cl.search_runs(
                [found.experiment_id],
                filter_string=f"tags.`mmz.import_key` = '{src.key}'",
                max_results=1,
            )
            if existing:
                results.append((src.key, "exists"))
                continue
        if dry_run:
            results.append((src.key, "would create"))
            continue
        exp = found.experiment_id if found else cl.create_experiment(src.experiment)
        ts = _ms(src.date)
        tags = {
            "mmz.kind": "import",
            "mmz.imported": "true",
            "mmz.import_key": src.key,
            "mmz.task": src.task,
            "mmz.topic": src.topic,
            **{k: v for k, v in src.tags.items() if v},
        }
        run = cl.create_run(exp, start_time=ts, run_name=src.name)
        rid = run.info.run_id
        clean_tags = [RunTag(k, guard.check_tag(k, v)) for k, v in tags.items()]
        metrics = [
            Metric(guard.check_key(k), guard.check_metric(k, v), ts, 0) for k, v in src.metrics.items()
        ]
        cl.log_batch(rid, metrics=metrics[:1000], tags=clean_tags, synchronous=True)
        if src.benchmark:
            family = src.benchmark.rsplit("-v", 1)[0]
            ref = data_ref(family, src.benchmark, "evaluation")
            if ref.sha256:
                from mlflow.entities import Dataset, DatasetInput, InputTag

                ds = Dataset(
                    ref.name,
                    ref.sha256[:16],
                    "zoo",
                    ref.source,
                    profile=json.dumps(ref.profile or {}, sort_keys=True),
                )
                cl.log_inputs(rid, [DatasetInput(ds, [InputTag("mlflow.data.context", "evaluation")])])
        for path in src.artifacts:
            cl.log_artifact(rid, str(guard.check_artifact(path)))
        cl.set_terminated(rid, "FINISHED", end_time=ts)
        results.append((src.key, "created"))
    return results
