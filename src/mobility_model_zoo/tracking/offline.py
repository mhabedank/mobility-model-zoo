"""Offline run logs: tracking where no server is reachable, e.g. on the DGX Spark (FR-030, R17).

A run in offline mode writes what it would log, after the same guard, to an append-only log next to
its sidecar, never into a staged or published folder:

    <dir>/tracking.json         ->  <dir>/tracking/<id>.mmz-run.jsonl
    <name>.tracking.json        ->  <name>.tracking/<id>.mmz-run.jsonl

One JSON object per line (`seq`, `t`, `type`, ...), flushed per event; allow-listed artifacts are
copied to `<id>.mmz-run/`. `zoo tracking sync` replays the log into the store on the laptop.
No MLflow import here: the training container needs no tracking software.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from . import client as tc
from . import guard
from .client import _now_ms, _scrub, warn

FORMAT = "mmz-run/1"
SUFFIX = ".mmz-run.jsonl"
SAMPLE_SECONDS = 10.0


def log_dir(sidecar: Path) -> Path:
    """The folder of a sidecar's offline logs: the sidecar path without `.json`."""
    return Path(sidecar).with_suffix("")


def log_path(sidecar: Path, offline_id: str) -> Path:
    return log_dir(sidecar) / f"{offline_id}{SUFFIX}"


def _last_seq(path: Path) -> int:
    """The last complete event of an existing log; a partial last line (crash) is cut off first."""
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        data = data[: data.rfind(b"\n") + 1]
        path.write_bytes(data)
    last = -1
    for line in data.decode("utf-8").splitlines():
        if line.strip():
            last = int(json.loads(line)["seq"])
    return last


class OfflineRun:
    """The `TrackedRun` interface, written to an offline log. Construct through `tracking.run()`."""

    def __init__(self, experiment: str, offline_id: str, sidecar: Path):
        self.experiment = experiment
        self.offline_id = offline_id
        self.run_id = offline_id  # what callers continue a run with (span tune, via the sidecar)
        self.sidecar = Path(sidecar)
        self.path = log_path(self.sidecar, offline_id)
        self.degraded = False
        self.dropped = 0
        self.warnings: list[str] = []
        self._seq = 0
        self._lock = threading.Lock()
        self._sampler: _Sampler | None = None

    @classmethod
    def open(cls, experiment: str, name: str, task: str, sidecar: Path, offline_id: str | None = None):
        """A new run, or the run `offline_id` continued when its log is next to this sidecar."""
        if offline_id and log_path(sidecar, offline_id).is_file():
            run = cls(experiment, offline_id, sidecar)
            run._seq = _last_seq(run.path) + 1
            return run
        if offline_id:
            warn(f"offline log of run {offline_id} not found next to {Path(sidecar).name}; new run")
        run = cls(experiment, uuid.uuid4().hex, sidecar)
        run.path.parent.mkdir(parents=True, exist_ok=True)
        run._event("start", format=FORMAT, experiment=experiment, name=name, task=task)
        return run

    # ---- writing ---------------------------------------------------------------------------

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)
            warn(message)

    def _refused(self, e: guard.GuardRefused) -> None:
        if tc.STRICT:
            raise e
        self.dropped += 1
        self._warn(str(e))

    def _event(self, type_: str, **fields: Any) -> None:
        """Append one event; a write error (e.g. a full disk) degrades the run, never fails it."""
        if self.degraded:
            self.dropped += 1
            return
        with self._lock:
            line = json.dumps({"seq": self._seq, "t": _now_ms(), "type": type_, **fields})
            try:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    f.flush()
            except OSError as e:
                self.degraded = True
                self.dropped += 1
                self._warn(f"offline log not writable ({e.__class__.__name__}); run continues untracked")
                return
            self._seq += 1

    # ---- the TrackedRun interface ------------------------------------------------------------

    def log_params(self, params: dict[str, Any]) -> None:
        clean = {}
        for key, value in params.items():
            try:
                clean[key] = guard.check_param(key, value)
            except guard.GuardRefused as e:
                self._refused(e)
        if clean:
            self._event("params", values=clean)

    def set_tags(self, tags: dict[str, Any]) -> None:
        clean = {}
        for key, value in tags.items():
            if value is None:
                continue
            try:
                clean[key] = guard.check_tag(key, value)
            except guard.GuardRefused as e:
                self._refused(e)
        if clean:
            self._event("tags", values=clean)

    def set_tag(self, key: str, value: Any) -> None:
        self.set_tags({key: value})

    def log_metrics(self, metrics: dict[str, Any], step: int = 0, timestamp: int | None = None) -> None:
        clean = {}
        for key, value in metrics.items():
            try:
                clean[key] = guard.check_metric(key, value)
            except guard.GuardRefused as e:
                self._refused(e)
        if clean:
            extra = {"ts": timestamp} if timestamp else {}
            self._event("metrics", step=int(step), values=clean, **extra)

    def log_step(self, step: int, metrics: dict[str, Any]) -> None:
        self.log_metrics({k: v for k, v in metrics.items() if isinstance(v, int | float)}, step=step)

    def log_final(self, metrics: dict[str, Any]) -> None:
        self.log_metrics({k: v for k, v in metrics.items() if isinstance(v, int | float)})

    def log_artifact(self, path: Path, name: str | None = None) -> None:
        try:
            path = guard.check_artifact(Path(path), name)
        except guard.GuardRefused as e:
            self._refused(e)
            return
        published = name or path.name
        target = log_dir(self.sidecar) / f"{self.offline_id}.mmz-run" / published
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".json":
                data = _scrub(json.loads(path.read_text(encoding="utf-8")))
                target.write_text(json.dumps(data, indent=2), encoding="utf-8")
            else:
                shutil.copyfile(path, target)
        except (OSError, ValueError) as e:
            self._warn(f"artifact {published} not copied ({e.__class__.__name__})")
            return
        self._event("artifact", name=published)

    def log_input(
        self, name: str, digest: str, source: str, profile: dict[str, Any], context: str
    ) -> None:
        self._event(
            "input", name=name, digest=digest[:16], source=source, profile=profile, context=context
        )

    def start_system_metrics(self) -> None:
        if self.degraded:
            return
        self._sampler = _Sampler(self)
        self._sampler.start()

    def finish(self, status: str) -> None:
        if self._sampler is not None:
            self._sampler.stop()
        self._event("end", status=status)
        self.write_sidecar()
        if self.degraded:
            warn(f"offline run {self.offline_id} is incomplete ({self.dropped} value(s) dropped)")

    def write_sidecar(self) -> None:
        self.sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar = {
            "mode": "offline",
            "tracking_uri_host": "-",
            "experiment": self.experiment,
            "run_id": None,
            "offline_id": self.offline_id,
            "log": self.path.relative_to(self.sidecar.parent).as_posix(),
            "complete": not self.degraded,
            "dropped": self.dropped,
            "warnings": self.warnings,
        }
        self.sidecar.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")


# ---- system metrics without MLflow (research R7) ---------------------------------------------


def _gpu_sample() -> dict[str, float]:
    """GPU utilisation and power per device from `nvidia-smi`; nothing when it is missing."""
    if shutil.which("nvidia-smi") is None:
        return {}
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    values: dict[str, float] = {}
    for i, line in enumerate(out.strip().splitlines()):
        for field, key in zip(line.split(","), ("utilization_percentage", "power_watts"), strict=False):
            try:
                values[f"system/gpu_{i}_{key}"] = float(field.strip())
            except ValueError:
                continue  # "[N/A]" or "[Not Supported]" (memory queries on GB10)
    return values


def system_sample() -> dict[str, float]:
    """One sample under MLflow's own system metric names, so synced and live runs chart alike."""
    values: dict[str, float] = {}
    try:
        import psutil
    except ImportError:
        psutil = None
    if psutil is not None:
        mem = psutil.virtual_memory()
        values["system/cpu_utilization_percentage"] = float(psutil.cpu_percent(interval=None))
        values["system/system_memory_usage_megabytes"] = mem.used / 1e6
        values["system/system_memory_usage_percentage"] = float(mem.percent)
    values.update(_gpu_sample())
    return values


class _Sampler(threading.Thread):
    def __init__(self, tracked: OfflineRun, interval: float | None = None):
        super().__init__(daemon=True, name="mmz-tracking-sampler")
        self.tracked = tracked
        self.interval = interval or float(os.environ.get("MMZ_TRACKING_SAMPLE_SECONDS", SAMPLE_SECONDS))
        self._halt = threading.Event()

    def run(self) -> None:
        step = 0
        while not self._halt.wait(self.interval):
            sample = system_sample()
            if sample:
                self.tracked.log_metrics(sample, step=step)
                step += 1

    def stop(self) -> None:
        self._halt.set()
        self.join(timeout=5)
