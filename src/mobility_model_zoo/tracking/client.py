"""One tracked run: synchronous logging with a circuit breaker and a local sidecar (research R5).

MLflow's defaults retry for minutes and then raise, and its async mode drops failed batches without
a trace. A training run must never stall or fail because the server is gone (FR-020), and the owner
must learn when tracking was incomplete. So: short limits, one batch per step, the first failure
switches the run to "degraded" (every later call becomes a no-op, one warning), and the run's own
outputs get a `tracking.json` saying whether the store holds everything.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from . import config, guard

STRICT = False  # tests: guard refusals raise instead of being dropped


def warn(message: str) -> None:
    print(f"tracking: {message}", file=sys.stderr)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _scrub(value: Any) -> Any:
    """Paths inside a JSON artifact are reduced to their file name (no home or data paths)."""
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if (
        isinstance(value, str)
        and ("/" in value)
        and (value.startswith(("/", "~", "data/", "$MMZ_DATA")))
    ):
        return Path(value).name
    return value


class TrackedRun:
    """A run in the tracking store. Construct through `mobility_model_zoo.tracking.run()`."""

    def __init__(self, client, experiment: str, run_id: str, out_dir: Path | None = None):
        self.client = client
        self.experiment = experiment
        self.run_id = run_id
        self.out_dir = Path(out_dir) if out_dir else None
        self.degraded = False
        self.dropped = 0
        self.warnings: list[str] = []
        self._monitor = None

    # ---- guarded calls ---------------------------------------------------------------------

    def _refused(self, e: guard.GuardRefused) -> None:
        if STRICT:
            raise e
        self.dropped += 1
        self._warn(str(e))

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)
            warn(message)

    def _call(self, fn, *args, **kwargs) -> Any:
        """Run one client call unless the run is degraded; the first failure degrades it."""
        if self.degraded:
            self.dropped += 1
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 - any client failure must not reach the training run
            self.degraded = True
            self.dropped += 1
            self._warn(
                f"server unreachable ({e.__class__.__name__}); the run continues without tracking"
            )
            return None

    # ---- public API ------------------------------------------------------------------------

    def log_params(self, params: dict[str, Any]) -> None:
        from mlflow.entities import Param

        clean = []
        for key, value in params.items():
            try:
                clean.append(Param(key, guard.check_param(key, value)))
            except guard.GuardRefused as e:
                self._refused(e)
        for i in range(0, len(clean), 100):  # the server takes at most 100 params per batch
            self._call(self.client.log_batch, self.run_id, params=clean[i : i + 100], synchronous=True)

    def set_tags(self, tags: dict[str, Any]) -> None:
        from mlflow.entities import RunTag

        clean = []
        for key, value in tags.items():
            if value is None:
                continue
            try:
                clean.append(RunTag(key, guard.check_tag(key, value)))
            except guard.GuardRefused as e:
                self._refused(e)
        if clean:
            self._call(self.client.log_batch, self.run_id, tags=clean, synchronous=True)

    def set_tag(self, key: str, value: Any) -> None:
        self.set_tags({key: value})

    def log_metrics(self, metrics: dict[str, Any], step: int = 0, timestamp: int | None = None) -> None:
        from mlflow.entities import Metric

        ts = timestamp or _now_ms()
        clean = []
        for key, value in metrics.items():
            try:
                clean.append(Metric(key, guard.check_metric(key, value), ts, step))
            except guard.GuardRefused as e:
                self._refused(e)
        for i in range(0, len(clean), 1000):
            self._call(self.client.log_batch, self.run_id, metrics=clean[i : i + 1000], synchronous=True)

    def log_step(self, step: int, metrics: dict[str, Any]) -> None:
        """Metrics of one epoch, evaluation step or measurement batch: one request."""
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
        folder, _, filename = published.rpartition("/")
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / filename
            if path.suffix == ".json":
                copy.write_text(
                    json.dumps(_scrub(json.loads(path.read_text(encoding="utf-8"))), indent=2)
                )
            else:
                copy.write_bytes(path.read_bytes())
            self._call(self.client.log_artifact, self.run_id, str(copy), folder or None)

    def log_input(
        self, name: str, digest: str, source: str, profile: dict[str, Any], context: str
    ) -> None:
        from mlflow.entities import Dataset, DatasetInput, InputTag

        dataset = Dataset(
            name=name,
            digest=digest[:16],
            source_type="zoo",
            source=source,
            profile=json.dumps(profile, sort_keys=True),
        )
        tag = InputTag("mlflow.data.context", context)
        self._call(self.client.log_inputs, self.run_id, [DatasetInput(dataset, [tag])])

    def start_system_metrics(self) -> None:
        try:
            import psutil  # noqa: F401
            from mlflow.system_metrics.system_metrics_monitor import SystemMetricsMonitor
        except ImportError:
            return
        if self.degraded:
            return
        try:
            self._monitor = SystemMetricsMonitor(self.run_id, sampling_interval=10)
            self._monitor.start()
        except Exception as e:  # noqa: BLE001
            self._warn(f"system metrics off ({e.__class__.__name__})")

    def finish(self, status: str) -> None:
        if self._monitor is not None:
            try:
                self._monitor.finish()
            except Exception:  # noqa: BLE001
                pass
        self._call(self.client.set_terminated, self.run_id, status, _now_ms())
        self.write_sidecar()
        if self.degraded:
            warn(f"run {self.run_id} is incomplete in the store ({self.dropped} value(s) dropped)")

    def write_sidecar(self) -> None:
        if self.out_dir is None:
            return
        self.out_dir.mkdir(parents=True, exist_ok=True)
        sidecar = {
            "tracking_uri_host": config.uri_host(),
            "experiment": self.experiment,
            "run_id": self.run_id,
            "complete": not self.degraded,  # guard drops are deliberate, not losses
            "dropped": self.dropped,
            "warnings": self.warnings,
        }
        (self.out_dir / "tracking.json").write_text(
            json.dumps(sidecar, indent=2) + "\n", encoding="utf-8"
        )


class NoRun:
    """What `tracking.run()` yields without a tracking URI: every method does nothing."""

    run_id = None
    degraded = False

    def __getattr__(self, _name: str):
        return lambda *args, **kwargs: None


def experiment_id(client, name: str) -> str:
    found = client.get_experiment_by_name(name)
    if found is not None:
        return found.experiment_id
    return client.create_experiment(name)


def new_client():
    """An MlflowClient for the configured URI, with the zoo's short client limits."""
    config.apply_client_defaults()
    from mlflow.tracking import MlflowClient

    return MlflowClient(tracking_uri=config.tracking_uri())
