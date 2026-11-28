"""`zoo data publish`: the data overview as the `datasets` experiment (US3, FR-014-FR-016, R9).

One run per data version, keyed by `(mmz.id, mmz.version)`:
* not there -> create;
* same `mmz.sha256` -> update its metrics;
* new `mmz.sha256` -> new run, the old one tagged `mmz.superseded_by`;
* a `register` row (dataset not downloaded here) is updated in place and superseded once a run of
  a real version of the same id exists.

Publishing is the command's whole purpose, so a server error raises here (exit 8) instead of
degrading quietly as run logging does.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mobility_model_zoo.datasets.inventory.rows import REGISTER_VERSION, InventoryRow
from mobility_model_zoo.release.errors import ZooError

from . import guard

EXPERIMENT = "datasets"


class TrackingUnavailable(ZooError):
    exit_code = 8


@dataclass
class Action:
    row: str
    action: str  # create | update | supersede | skip
    run_id: str | None = None
    note: str = ""


def metrics_of(row: InventoryRow) -> dict[str, float]:
    out: dict[str, float] = {}
    if row.size_mb is not None:
        out["size_mb"] = row.size_mb
    elif row.approx_size_mb:
        out["approx_size_mb"] = float(row.approx_size_mb)
    if row.files is not None:
        out["files"] = row.files
    for key, value in row.counts.items():
        out[f"count.{guard.sanitize_key(key)}"] = value
    for dim, values in row.distribution.items():
        for value, n in values.items():
            out[f"dist.{guard.sanitize_key(dim)}.{guard.sanitize_key(value)}"] = n
    return out


def tags_of(row: InventoryRow) -> dict[str, str]:
    tags = {
        "mmz.kind": row.kind,
        "mmz.topic": row.topic,
        "mmz.id": row.id,
        "mmz.version": row.version,
        "mmz.sha256": row.sha256,
        "mmz.frozen_at": row.frozen_at,
        "mmz.permitted_use": row.permitted_use,
        "mmz.licence": row.licence,
    }
    return {k: v for k, v in tags.items() if v}


def _existing(client, exp_id: str, row: InventoryRow) -> list:
    flt = f"tags.`mmz.id` = '{row.id}' and tags.`mmz.version` = '{row.version}'"
    runs = client.search_runs([exp_id], filter_string=flt, max_results=50)
    return [r for r in runs if "mmz.superseded_by" not in r.data.tags]


def _real_versions(client, exp_id: str, row_id: str) -> list:
    flt = f"tags.`mmz.id` = '{row_id}'"
    runs = client.search_runs([exp_id], filter_string=flt, max_results=200)
    return [r for r in runs if r.data.tags.get("mmz.version") != REGISTER_VERSION]


def _write(client, run_id: str, row: InventoryRow, profile: bool) -> None:
    from mlflow.entities import Metric, Param, RunTag

    from .client import _now_ms

    ts = _now_ms()
    metrics = [Metric(k, guard.check_metric(k, v), ts, 0) for k, v in metrics_of(row).items()]
    tags = [RunTag(k, guard.check_tag(k, v)) for k, v in tags_of(row).items()]
    params = []
    for key, value in (
        ("source", row.source),
        ("status", row.status),
        ("availability", row.availability),
        ("redistribution", row.redistribution),
        ("used_by", ",".join(row.used_by)[:120] or None),
    ):
        if value is not None:
            try:
                params.append(Param(key, guard.check_param(key, value)))
            except guard.GuardRefused:
                continue
    existing = client.get_run(run_id).data.params
    params = [p for p in params if p.key not in existing]  # params are write-once in MLflow
    for i in range(0, max(len(metrics), 1), 1000):
        client.log_batch(
            run_id,
            metrics=metrics[i : i + 1000],
            tags=tags if i == 0 else [],
            params=params if i == 0 else [],
            synchronous=True,
        )
    if profile:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(
                json.dumps(
                    {"counts": row.counts, "distribution": row.distribution}, indent=2, sort_keys=True
                )
            )
            client.log_artifact(run_id, str(path))


def _log_input(client, run_id: str, row: InventoryRow) -> None:
    from mlflow.entities import Dataset, DatasetInput, InputTag

    if not row.sha256:
        return
    dataset = Dataset(
        name=row.name,
        digest=row.sha256[:16],
        source_type="zoo",
        source=row.source,
        profile=json.dumps({"counts": row.counts, "distribution": row.distribution}, sort_keys=True),
    )
    client.log_inputs(run_id, [DatasetInput(dataset, [InputTag("mlflow.data.context", "inventory")])])


def publish(rows: list[InventoryRow], dry_run: bool = False, profile: bool = False) -> list[Action]:
    from . import client as tc
    from . import config

    if not config.tracking_uri():
        if dry_run:
            return [Action(r.name, "create", note="no server asked (no tracking URI)") for r in rows]
        raise TrackingUnavailable("no MLFLOW_TRACKING_URI; set it in .env (docs/tracking.md)")
    if not config.client_installed():
        raise TrackingUnavailable("the tracking client is not installed: uv sync --extra tracking")
    try:
        client = tc.new_client()
        found = client.get_experiment_by_name(EXPERIMENT)
        if found is None and dry_run:
            return [Action(r.name, "create") for r in rows]
        exp_id = found.experiment_id if found else client.create_experiment(EXPERIMENT)
        return [_publish_row(client, exp_id, r, dry_run, profile) for r in rows]
    except guard.GuardRefused:
        raise
    except Exception as e:  # noqa: BLE001
        raise TrackingUnavailable(f"tracking server: {e.__class__.__name__}: {str(e)[:200]}") from None


def _publish_row(client, exp_id: str, row: InventoryRow, dry_run: bool, profile: bool) -> Action:
    if row.availability == "error":
        return Action(row.name, "skip", note="error row: " + "; ".join(row.notes)[:100])
    if row.version == REGISTER_VERSION and _real_versions(client, exp_id, row.id):
        # published from a machine that has the data; a machine without it adds nothing
        return Action(row.name, "skip", note="a downloaded version is already published")
    current = _existing(client, exp_id, row)
    same = [
        r
        for r in current
        if r.data.tags.get("mmz.sha256") == (row.sha256 or None)
        or (row.sha256 is None and "mmz.sha256" not in r.data.tags)
    ]
    if same:
        action = Action(row.name, "update", same[0].info.run_id)
        if not dry_run:
            _write(client, same[0].info.run_id, row, profile)
    else:
        action = Action(row.name, "supersede" if current else "create")
        if not dry_run:
            run = client.create_run(exp_id, run_name=row.name)
            action.run_id = run.info.run_id
            _write(client, action.run_id, row, profile)
            _log_input(client, action.run_id, row)
            for old in current:
                client.set_tag(old.info.run_id, "mmz.superseded_by", action.run_id)
            client.set_terminated(action.run_id, "FINISHED")
    if row.version != REGISTER_VERSION and not dry_run:
        flt = f"tags.`mmz.id` = '{row.id}' and tags.`mmz.version` = '{REGISTER_VERSION}'"
        for old in client.search_runs([exp_id], filter_string=flt, max_results=10):
            if "mmz.superseded_by" not in old.data.tags and action.run_id:
                client.set_tag(old.info.run_id, "mmz.superseded_by", action.run_id)
    return action
