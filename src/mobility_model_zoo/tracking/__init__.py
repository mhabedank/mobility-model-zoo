"""Experiment tracking (feature 017, specs/017-mlflow-data-transparency/contracts/tracking.md).

The only package that imports MLflow, and only when `MLFLOW_TRACKING_URI` is set: without it every
command behaves exactly as before. The repository stays the source of truth; the tracking store on
the Spark is the lab notebook and holds numbers, hashes and metadata only.

    from mobility_model_zoo import tracking

    with tracking.run("productdev/jtbd-span", name="span-xlmr-c1", task="jtbd-span",
                      config_path="configs/productdev/jtbd/span-xlmr.yaml",
                      inputs=[tracking.data_ref("span-train", "span-train-v1", "training")],
                      out_dir=out, system_metrics=True) as r:
        r.log_step(epoch, {"loss": 0.41})
"""

from __future__ import annotations

import socket
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

EXPERIMENTS = (
    "datasets",
    "productdev/jtbd-span",
    "productdev/jtbd-cluster",
    "security/can-ids",
    "condition-monitoring/sound-anomaly",
    "condition-monitoring/activity",
    "edge/hil-bench",
    "spikes",
)
# A model's task id where its experiment has another name (the span model of task `jtbd`).
TASK_EXPERIMENT = {"jtbd": "jtbd-span"}
# Host names mapped to the hardware labels the zoo uses in task documents and results.
HARDWARE = (
    ("spark", "dgx-spark"),
    ("dgx", "dgx-spark"),
    ("macbook", "macbook"),
    ("runner", "ci-runner"),
)


@dataclass(frozen=True)
class DataRef:
    """A data version a run used, resolved from the overview (or unresolved, with a tag)."""

    name: str  # <id>@<version>
    context: str  # training | evaluation | inventory
    sha256: str | None = None
    source: str = ""
    profile: dict[str, Any] | None = None


def enabled() -> bool:
    from .config import enabled as _enabled

    return _enabled()


def _git(*args: str) -> str | None:
    from mobility_model_zoo.edge.paths import repo_root

    out = subprocess.run(
        ["git", "-C", str(repo_root()), *args], capture_output=True, text=True, check=False
    )
    return out.stdout.strip() if out.returncode == 0 else None


def hardware() -> str:
    import os

    if os.environ.get("MMZ_HARDWARE"):
        return os.environ["MMZ_HARDWARE"]
    host = socket.gethostname().lower()
    for marker, label in HARDWARE:
        if marker in host:
            return label
    return "host"


def flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    """Nested configuration as `a.b.c` keys; lists of scalars become one comma-joined value."""
    out: dict[str, Any] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(data, list):
        if all(isinstance(v, str | int | float | bool) for v in data):
            out[prefix] = ",".join(str(v) for v in data)
        else:
            for i, v in enumerate(data):
                out.update(flatten(v, f"{prefix}.{i}"))
    else:
        out[prefix] = data
    return out


@cache
def _inventory():
    from mobility_model_zoo.datasets.inventory import collect

    return collect(integrity=False, include_rejected=True)


def data_ref(id_: str, version: str, context: str) -> DataRef:
    """The data version `<id>@<version>` as a run input, with its hash and counts when known."""
    from mobility_model_zoo.datasets.inventory import find

    name = f"{id_}@{version}"
    try:
        rows = find(_inventory(), name) or find(_inventory(), version)
    except Exception:  # noqa: BLE001 - an unreadable overview must not stop a run
        rows = []
    if len(rows) != 1:
        return DataRef(name=name, context=context)
    row = rows[0]
    profile = {"counts": row.counts, "distribution": row.distribution}
    return DataRef(row.name, context, row.sha256, row.source, profile)


def dataset_ref(id_: str, context: str) -> DataRef:
    """A third-party dataset as a run input, in the version this machine holds (its retrieval
    date), or unresolved when it is not downloaded here."""
    from mobility_model_zoo.datasets.inventory import find

    try:
        rows = [r for r in find(_inventory(), id_) if r.kind == "dataset"]
    except Exception:  # noqa: BLE001
        rows = []
    if len(rows) != 1 or not rows[0].sha256:
        return DataRef(name=f"{id_}@register", context=context)
    row = rows[0]
    return DataRef(row.name, context, row.sha256, row.source, {"counts": row.counts})


def model_experiment(model: str) -> tuple[str, str, str]:
    """(experiment, topic, task) of a zoo model from `zoo/models/<model>/model.yaml`; models of a
    task without its own experiment go to `spikes`."""
    import yaml

    from mobility_model_zoo.edge.paths import repo_root

    path = repo_root() / "zoo" / "models" / model / "model.yaml"
    try:
        rec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return "spikes", "sandbox", model
    topic, task = str(rec.get("topic", "")), str(rec.get("task", ""))
    task = TASK_EXPERIMENT.get(task, task)
    name = f"{topic}/{task}"
    return (name if name in EXPERIMENTS else "spikes"), topic, task


@contextmanager
def run(
    experiment: str,
    name: str,
    task: str,
    config_path: str | Path | None = None,
    inputs: tuple[DataRef, ...] | list[DataRef] = (),
    out_dir: Path | None = None,
    sidecar: Path | None = None,
    system_metrics: bool = False,
    tags: dict[str, Any] | None = None,
    topic: str | None = None,
    run_id: str | None = None,
) -> Iterator[Any]:
    """A tracked run, or a no-op without a tracking URI. Never raises into the caller's work
    because of tracking; exceptions of the caller's own code pass through unchanged."""
    from . import client as tc
    from .config import enabled as _enabled

    if not _enabled():
        yield tc.NoRun()
        return
    # the sidecar: `tracking.json` in out_dir, or an explicit file (next to a model directory
    # that is uploaded as it is)
    side = Path(sidecar) if sidecar else (Path(out_dir) / "tracking.json" if out_dir else None)
    if experiment not in EXPERIMENTS:
        raise ValueError(f"unknown experiment {experiment} (add it to tracking.EXPERIMENTS)")
    import os

    cl = None
    rid = None
    try:
        cl = tc.new_client()
        if run_id:
            rid = run_id
        else:
            exp = tc.experiment_id(cl, experiment)
            rid = cl.create_run(exp, run_name=name).info.run_id
    except Exception as e:  # noqa: BLE001
        tc.warn(f"server unreachable ({e.__class__.__name__}); the run continues without tracking")
        try:
            yield tc.NoRun()
        finally:
            if side is not None:
                tr = tc.TrackedRun(None, experiment, None, side)
                tr.degraded = True
                tr.warnings.append("server unreachable at start")
                tr.write_sidecar()
        return
    tr = tc.TrackedRun(cl, experiment, rid, side)
    base_tags = {
        "mmz.task": task,
        "mmz.topic": topic or experiment.split("/")[0],
        "mmz.git_commit": _git("rev-parse", "HEAD"),
        "mmz.git_clean": "true" if _git("status", "--porcelain") == "" else "false",
        "mmz.hardware": hardware(),
        **(tags or {}),
    }
    if not run_id:
        tr.set_tags(base_tags)
    if config_path:
        _log_config(tr, Path(config_path))
    for ref in inputs:
        if ref.sha256:
            tr.log_input(ref.name, ref.sha256, ref.source, ref.profile or {}, ref.context)
        else:
            tr.set_tag("mmz.input_unresolved", ref.name)
            tc.warn(f"input {ref.name} not found in the data overview; logged as unresolved")
    if system_metrics and os.environ.get("MMZ_TRACKING_SYSTEM_METRICS", "1") != "0":
        tr.start_system_metrics()
    status = "FINISHED"
    try:
        yield tr
    except KeyboardInterrupt:
        status = "KILLED"
        raise
    except BaseException:
        status = "FAILED"
        raise
    finally:
        tr.finish(status)


def _log_config(tr, path: Path) -> None:
    import yaml

    from mobility_model_zoo.edge.paths import repo_root

    full = path if path.is_absolute() else repo_root() / path
    try:
        data = yaml.safe_load(full.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        tr._warn(f"config {path} unreadable ({e.__class__.__name__})")
        return
    from .guard import GuardRefused, check_param, sanitize_key

    rel = full.relative_to(repo_root()).as_posix() if full.is_relative_to(repo_root()) else path.name
    params = {"config": rel}
    for key, value in flatten(data).items():
        key = ".".join(sanitize_key(part) for part in key.split("."))[:120]
        try:
            check_param(key, value)
        except GuardRefused:
            continue  # free text of a committed file; the config copy below holds it
        params[key] = value
    tr.log_params(params)
    if full.is_relative_to(repo_root() / "configs"):
        tr.log_artifact(full, f"config/{full.name}")


def numeric_leaves(data: Any, prefix: str = "", limit: int = 500) -> dict[str, float]:
    """Every number in a nested result as a metric (`a.b.c`), at most `limit`; booleans and text
    are left out (they are not metrics, and text never goes into the store)."""
    from .guard import sanitize_key

    out: dict[str, float] = {}

    def walk(value: Any, key: str) -> None:
        if len(out) >= limit:
            return
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{key}.{sanitize_key(k)}" if key else sanitize_key(k))
        elif isinstance(value, int | float) and not isinstance(value, bool):
            if value == value and abs(value) != float("inf"):
                out[key[:120]] = float(value)

    walk(data, prefix)
    return out


def record(
    experiment: str,
    name: str,
    task: str,
    kind: str,
    result: dict[str, Any],
    *,
    topic: str | None = None,
    inputs: tuple[DataRef, ...] | list[DataRef] = (),
    tags: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    artifacts: tuple[tuple[Path, str | None], ...] = (),
    config_path: str | Path | None = None,
) -> str | None:
    """A finished result (evaluation, measurement, export) as one run: its numbers as metrics.
    A no-op without a tracking URI; never raises because of the server."""
    if not enabled():
        return None
    with run(
        experiment,
        name,
        task,
        config_path=config_path,
        inputs=inputs,
        topic=topic,
        tags={"mmz.kind": kind, **(tags or {})},
    ) as r:
        if params:
            r.log_params(params)
        r.log_final(numeric_leaves(result))
        for path, published in artifacts:
            if Path(path).is_file():
                r.log_artifact(Path(path), published)
    return r.run_id
