"""`zoo tracking sync`: offline run logs into the store (FR-030, research R17).

Per log (`<id>.mmz-run.jsonl`), keyed by `tags.mmz.offline_id`:
* not in the store -> create the run with the log's start time, replay every complete event;
* in the store -> replay only events with `seq` above its `mmz.offline_synced` tag;
* nothing new -> unchanged.

Every value passes the guard again before anything of the log is written, so a hand-edited log never
lands half. `mmz.offline_synced` is written with each batch, so an interrupted sync resumes. Like
`zoo data publish`, a server error raises (exit 8).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import guard
from .offline import FORMAT, SUFFIX
from .publish import TrackingUnavailable

ID = re.compile(r"^[0-9a-f]{32}$")
STATUSES = ("FINISHED", "FAILED", "KILLED")


class LogRefused(guard.GuardRefused):
    """A log that is malformed or holds a value the guard refuses; nothing of it is written."""


@dataclass
class Action:
    path: Path
    action: str  # created | updated | unchanged | create | update | refused
    experiment: str = ""
    name: str = ""
    events: int = 0
    running: bool = False
    note: str = ""


def find_logs(paths: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for p in map(Path, paths):
        if p.is_file() and p.name.endswith(SUFFIX):
            found.add(p)
        elif p.is_dir():
            found.update(f for f in p.rglob(f"*{SUFFIX}") if f.is_file())
    return sorted(found)


def read_log(path: Path) -> tuple[str, list[dict[str, Any]]]:
    """The offline id and the complete events; a partial last line is left for the next sync."""
    offline_id = path.name[: -len(SUFFIX)]
    if not ID.match(offline_id):
        raise LogRefused(f"{path.name}: not an offline log name")
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    lines = lines[:-1]  # the part after the last newline is empty or still being written
    events = []
    for n, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            raise LogRefused(f"{path.name}: line {n + 1} is not JSON") from None
        if not isinstance(event, dict) or event.get("seq") != len(events):
            raise LogRefused(f"{path.name}: line {n + 1} is out of sequence")
        events.append(event)
    if not events or events[0].get("type") != "start" or events[0].get("format") != FORMAT:
        raise LogRefused(f"{path.name}: no {FORMAT} start event")
    return offline_id, events


def _prepare(
    events: list[dict[str, Any]], folder: Path, params: dict[str, str]
) -> list[tuple[int, str, Any]]:
    """Check every event with the guard; (seq, kind, payload) ready to write, or LogRefused.
    `params` are the run's params in the store: MLflow params are write-once, so an equal value is
    skipped and a changed one refuses the log."""
    from mobility_model_zoo import tracking

    params = dict(params)
    ops: list[tuple[int, str, Any]] = []
    for e in events:
        seq, kind, t = e["seq"], e.get("type"), e.get("t")
        try:
            if kind == "start":
                if e.get("experiment") not in tracking.EXPERIMENTS:
                    raise LogRefused(f"unknown experiment {e.get('experiment')!r}")
                continue
            if kind == "params":
                for k, v in e["values"].items():
                    value = guard.check_param(k, v)
                    if k in params and params[k] != value:
                        raise LogRefused(f"param {k} changed after it was logged")
                    if k not in params:
                        params[k] = value
                        ops.append((seq, "param", (k, value)))
            elif kind == "tags":
                ops += [(seq, "tag", (k, guard.check_tag(k, v))) for k, v in e["values"].items()]
            elif kind == "metrics":
                ts, step = int(e.get("ts") or t), int(e.get("step", 0))
                ops += [
                    (seq, "metric", (k, guard.check_metric(k, v), ts, step))
                    for k, v in e["values"].items()
                ]
            elif kind == "input":
                name = guard.check_param("input", e["name"])
                digest, context = str(e["digest"])[:16], e["context"]
                if context not in ("training", "evaluation", "inventory") or not re.fullmatch(
                    r"[0-9a-f]{1,16}", digest
                ):
                    raise LogRefused(f"input {name}: bad digest or context")
                profile = json.dumps(e.get("profile") or {}, sort_keys=True)
                ops.append(
                    (
                        seq,
                        "input",
                        (name, digest, guard.check_param("source", e["source"]), profile, context),
                    )
                )
            elif kind == "artifact":
                path = guard.check_synced_artifact(folder / e["name"], e["name"])
                ops.append((seq, "artifact", (path, e["name"])))
            elif kind == "end":
                if e.get("status") not in STATUSES:
                    raise LogRefused(f"unknown status {e.get('status')!r}")
                ops.append((seq, "end", (e["status"], int(t))))
            else:
                raise LogRefused(f"unknown event type {kind!r}")
        except (KeyError, TypeError, ValueError) as err:
            raise LogRefused(f"event {seq}: malformed ({err.__class__.__name__})") from None
        except LogRefused as err:
            raise LogRefused(f"event {seq}: {err}") from None
        except guard.GuardRefused as err:
            raise LogRefused(f"event {seq}: {err}") from None
        if not ops or ops[-1][0] != seq:
            ops.append((seq, "noop", None))  # an empty event still counts as synced
    return ops


def _write(client, run_id: str, ops: list[tuple[int, str, Any]]) -> None:
    """Replay prepared events in order, batched; `mmz.offline_synced` goes with every batch."""
    from mlflow.entities import Dataset, DatasetInput, InputTag, Metric, Param, RunTag

    batch: dict[str, list] = {"metrics": [], "params": [], "tags": []}
    last = None

    def flush() -> None:
        if last is None:
            return
        tags = [*batch["tags"], RunTag("mmz.offline_synced", str(last))]
        client.log_batch(
            run_id, metrics=batch["metrics"], params=batch["params"], tags=tags, synchronous=True
        )
        for key in batch:
            batch[key] = []

    for seq, kind, payload in ops:
        if kind == "metric":
            batch["metrics"].append(Metric(*payload))
        elif kind == "param":
            batch["params"].append(Param(*payload))
        elif kind == "tag":
            batch["tags"].append(RunTag(*payload))
        else:
            flush()
            if kind == "input":
                name, digest, source, profile, context = payload
                dataset = Dataset(
                    name=name, digest=digest, source_type="zoo", source=source, profile=profile
                )
                client.log_inputs(
                    run_id, [DatasetInput(dataset, [InputTag("mlflow.data.context", context)])]
                )
            elif kind == "artifact":
                path, published = payload
                folder = published.rpartition("/")[0]
                client.log_artifact(run_id, str(path), folder or None)
            elif kind == "end":
                status, end_time = payload
                client.set_terminated(run_id, status, end_time=end_time)
        last = seq
        if len(batch["metrics"]) >= 1000 or len(batch["params"]) + len(batch["tags"]) >= 90:
            flush()
    flush()


def sync(paths: list[Path], dry_run: bool = False) -> list[Action]:
    from . import client as tc
    from . import config

    logs = find_logs(paths)
    if not config.tracking_uri():
        if dry_run:
            return [Action(p, "create", note="no server asked (no tracking URI)") for p in logs]
        raise TrackingUnavailable(
            "no MLFLOW_TRACKING_URI; start the server: scripts/mlflow/mlflow.sh up"
        )
    if not config.client_installed():
        raise TrackingUnavailable("the tracking client is not installed: uv sync --extra tracking")
    actions = []
    try:
        client = tc.new_client()
        for path in logs:
            actions.append(_sync_one(client, path, dry_run))
    except guard.GuardRefused:
        raise
    except Exception as e:  # noqa: BLE001
        raise TrackingUnavailable(f"tracking server: {e.__class__.__name__}: {str(e)[:200]}") from None
    return actions


def _sync_one(client, path: Path, dry_run: bool) -> Action:
    try:
        offline_id, events = read_log(path)
    except LogRefused as e:
        return Action(path, "refused", note=str(e))
    start = events[0]
    running = not any(e.get("type") == "end" for e in events)
    act = Action(path, "", start.get("experiment", ""), start.get("name", ""), running=running)
    exp = client.get_experiment_by_name(act.experiment)
    found = []
    if exp is not None:
        flt = f"tags.`mmz.offline_id` = '{offline_id}'"
        found = client.search_runs([exp.experiment_id], filter_string=flt, max_results=2)
    synced = int(found[0].data.tags.get("mmz.offline_synced", "-1")) if found else -1
    new = [e for e in events if e["seq"] > synced]
    if not new:
        act.action = "unchanged"
        return act
    params = dict(found[0].data.params) if found else {}
    try:
        ops = _prepare(new, path.parent / f"{offline_id}.mmz-run", params)
    except LogRefused as e:
        act.action, act.note = "refused", str(e)
        return act
    act.events = len(new) - (1 if synced < 0 else 0)  # the start event is not a logged value
    if dry_run:
        act.action = "update" if found else "create"
        return act
    if found:
        run_id = found[0].info.run_id
        act.action = "updated"
    else:
        exp_id = exp.experiment_id if exp else client.create_experiment(act.experiment)
        run = client.create_run(
            exp_id,
            start_time=int(start["t"]),
            run_name=guard.check_param("name", start.get("name") or offline_id),
            tags={"mmz.offline_id": offline_id},
        )
        run_id = run.info.run_id
        act.action = "created"
    _write(client, run_id, ops)
    return act
