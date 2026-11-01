"""Experiment tracking of the CAN intrusion detection runs (feature 017; no-op without a URI).

Evaluations on a frozen benchmark, the picket-forest release trainings and the chain measurements
each become one run of the `security/can-ids` experiment. Only numbers and the export's
`config.json` are logged; model files, C sources and test vectors never are (FR-023).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

EXPERIMENT = "security/can-ids"
TASK = "can-ids"


def evaluation(result: dict[str, Any], benchmark: str, detector: str) -> None:
    from mobility_model_zoo import tracking

    tracking.record(
        EXPERIMENT,
        f"evaluate-{detector}-{benchmark}"[:120],
        TASK,
        "evaluate",
        {k: v for k, v in result.items() if k in ("detectors", "road", "partial")},
        topic="security",
        inputs=[tracking.data_ref("can-ids", benchmark, "evaluation")],
        tags={"mmz.benchmark": benchmark, "mmz.candidate": detector},
        params={"sets": ",".join(result.get("sets") or [])[:120] or "all"},
    )


def protocol_evaluation(results: dict[str, Any], dataset: str) -> None:
    """The pre-benchmark protocol evaluation on the raw splits: a spike, never a benchmark result."""
    from mobility_model_zoo import tracking

    tracking.record(
        "spikes",
        "picket-forest-protocol-evaluation",
        TASK,
        "evaluate",
        results,
        topic="security",
        inputs=[tracking.dataset_ref(dataset, "evaluation")],
        tags={"mmz.spike": "true", "mmz.model": "picket-forest"},
    )


def training(
    config: dict[str, Any], benchmark: str, export_dir: Path, model_version: str | None
) -> None:
    """A picket-forest release training: train and calibration roles of the frozen benchmark."""
    from mobility_model_zoo import tracking

    tracking.record(
        EXPERIMENT,
        f"picket-forest-export-{benchmark}"[:120],
        TASK,
        "train",
        {k: v for k, v in config.items() if k not in ("hyperparameters",)},
        topic="security",
        inputs=[tracking.data_ref("can-ids", benchmark, "training")],
        tags={
            "mmz.model": "picket-forest",
            "mmz.model_version": model_version,
            "mmz.training_set": f"{benchmark}:train+calibration",
        },
        params={f"hp.{k}": v for k, v in (config.get("hyperparameters") or {}).items()},
        artifacts=((Path(export_dir) / "config.json", "export-config.json"),),
    )


def measurement(metrics: list[dict[str, Any]], target: str, board: str | None, version: str) -> None:
    from mobility_model_zoo import tracking

    values = {m["name"]: m["value"] for m in metrics if isinstance(m.get("value"), int | float)}
    hardware = next((m.get("hardware") for m in metrics if m.get("hardware")), None)
    tracking.record(
        EXPERIMENT,
        f"measure-picket-forest-{target}"[:120],
        TASK,
        "measure",
        values,
        topic="security",
        tags={
            "mmz.model": "picket-forest",
            "mmz.model_version": version,
            "mmz.hardware": (board or hardware or target)[:60],
        },
        params={"target": target},
    )
