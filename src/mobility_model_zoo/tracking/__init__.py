"""Experiment tracking (feature 017, specs/017-mlflow-data-transparency/contracts/tracking.md).

The only package that imports MLflow, and only when `MLFLOW_TRACKING_URI` is set: without it every
command behaves exactly as before. The repository stays the source of truth; the tracking store on
the Spark is the lab notebook and holds numbers, hashes and metadata only.
"""

from __future__ import annotations

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
