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
    """A tracked run: live with a tracking URI, an offline log with `MMZ_TRACKING_OFFLINE=1`, else
    a no-op. Never raises into the caller's work because of tracking; exceptions of the caller's
    own code pass through unchanged. `run_id` continues a run (live id or offline id)."""
    from . import client as tc
    from .config import enabled as _enabled
    from .config import offline as _offline

    live = _enabled()
    if not live and not _offline():
        yield tc.NoRun()
        return
    # the sidecar: `tracking.json` in out_dir, or an explicit file (next to a model directory
    # that is uploaded as it is)
    side = Path(sidecar) if sidecar else (Path(out_dir) / "tracking.json" if out_dir else None)
    if experiment not in EXPERIMENTS:
        raise ValueError(f"unknown experiment {experiment} (add it to tracking.EXPERIMENTS)")

    if not live:
        if side is None:
            tc.warn("offline tracking needs an output folder; this run is not tracked")
            yield tc.NoRun()
            return
        from .offline import OfflineRun

        tr = OfflineRun.open(experiment, name, task, side, run_id)
        continued = tr.offline_id == run_id
        yield from _tracked(
            tr,
            None if continued else (task, topic, experiment, tags),
            config_path,
            inputs,
            system_metrics,
        )
        return

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
    yield from _tracked(
        tr, None if run_id else (task, topic, experiment, tags), config_path, inputs, system_metrics
    )


def _tracked(tr, new_run, config_path, inputs, system_metrics) -> Iterator[Any]:
    """Shared by live and offline runs: base tags (new runs only), config, inputs, status."""
    import os

    from . import client as tc

    if new_run is not None:
        task, topic, experiment, tags = new_run
        tr.set_tags(_base_tags(task, topic, experiment, tags))
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


def _base_tags(task: str, topic: str | None, experiment: str, tags: dict[str, Any] | None) -> dict:
    return {
        "mmz.task": task,
        "mmz.topic": topic or experiment.split("/")[0],
        "mmz.git_commit": _git("rev-parse", "HEAD"),
        "mmz.git_clean": "true" if _git("status", "--porcelain") == "" else "false",
        "mmz.hardware": hardware(),
        **(tags or {}),
    }


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
