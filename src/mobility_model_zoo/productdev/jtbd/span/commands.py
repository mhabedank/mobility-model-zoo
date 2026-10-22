"""`jtbd span train` and `jtbd span tune` with their gates (feature 004, T029)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.span.gates import passed_attributes, pilot_decision
from mobility_model_zoo.productdev.jtbd.span.recipe import (
    check_release_bar,
    head_commit,
    load_recipe,
    recipe_dimensions,
    require_clean_tree,
)
from mobility_model_zoo.productdev.jtbd.span.rows import frozen_data, load_rows


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def train_command(
    settings: Settings, recipe_file: str | None, out: Path, device: str, max_epochs: int | None = None
) -> dict[str, Any]:
    """Train one candidate after every gate passes (FR-001, FR-005, FR-006, Principle IV)."""
    if settings.span_train is None:
        raise UsageError("span train needs the training dataset config (span_train section)")
    frozen = frozen_data(settings)
    recipe = load_recipe(settings, recipe_file)
    dims = recipe_dimensions(recipe)
    _, decision = pilot_decision(settings)
    passed = passed_attributes(decision)
    if dims != passed:
        raise ValidationFailed(
            f"the recipe's dimensions {dims} differ from the attribute "
            f"dimensions that passed the pilot {passed}"
        )
    bar = check_release_bar(settings, recipe)
    require_clean_tree(settings)
    rows = load_rows(settings)
    minimum = int(settings.span_train["min_usable_chunks"])
    if len(rows) < minimum:
        raise ValidationFailed(
            f"only {len(rows)} usable training rows, fewer than "
            f"{minimum}; the model is not trained (FR-005)"
        )
    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "val"]
    meta = {
        "dataset": {
            "name": settings.span_train.get("dataset"),
            "sha256": frozen["sha256"],
            "train_chunks": len(train_rows),
            "val_chunks": len(val_rows),
        },
        "recipe": Path(recipe["_path"]).resolve().relative_to(settings.base.resolve()).as_posix(),
        "recipe_commit": head_commit(settings),
        **bar,
    }
    if max_epochs:
        meta["max_epochs_override"] = max_epochs
    from mobility_model_zoo import tracking
    from mobility_model_zoo.productdev.jtbd.span.train import train_candidate

    out = Path(out)
    dataset = meta["dataset"]["name"]
    with tracking.run(
        "productdev/jtbd-span",
        name=out.name,
        task="jtbd-span",
        topic="productdev",
        config_path=Path(recipe["_path"]),
        inputs=[tracking.data_ref("span-train", dataset, "training")],
        sidecar=tracking_sidecar(out),
        system_metrics=True,
        tags={
            "mmz.kind": "train",
            "mmz.training_set": dataset,
            "mmz.candidate": out.name,
            "mmz.model": settings.span_train.get("model"),
        },
    ) as run:
        run.log_params(
            {
                "device": device,
                "dimensions": ",".join(dims),
                "train_chunks": len(train_rows),
                "val_chunks": len(val_rows),
                "max_epochs_override": max_epochs or 0,
            }
        )
        result = train_candidate(
            recipe,
            dims,
            train_rows,
            val_rows,
            out,
            device,
            meta,
            max_epochs,
            log=_log,
            on_epoch=run.log_step,
        )
        best = result.get("best") or {}
        run.log_final({f"best.{k}": v for k, v in best.items()})
        run.log_artifact(out / "span_config.json")
    return result


def tracking_sidecar(model_dir: Path) -> Path:
    """`<model dir>.tracking.json`: next to the model directory, never inside it, because the
    directory is staged and published as it is (feature 017)."""
    model_dir = Path(model_dir)
    return model_dir.parent / f"{model_dir.name}.tracking.json"


def tune_command(settings: Settings, model_dir: Path, recipe_file: str | None) -> dict[str, Any]:
    from mobility_model_zoo import tracking
    from mobility_model_zoo.productdev.jtbd.span.tune import tune_thresholds
    from mobility_model_zoo.tracking.client import sidecar_run_id

    recipe = load_recipe(settings, recipe_file)
    grid = [float(v) for v in recipe["thresholds"]["unit_grid"]]
    model_dir = Path(model_dir)
    side = tracking_sidecar(model_dir)
    # continue the training run of this candidate when there is one, else a run of its own
    with tracking.run(
        "productdev/jtbd-span",
        name=f"{model_dir.name}-tune",
        task="jtbd-span",
        topic="productdev",
        run_id=sidecar_run_id(side),
        sidecar=side,
        tags={"mmz.kind": "tune", "mmz.candidate": model_dir.name},
    ) as run:
        result = tune_thresholds(model_dir, load_rows(settings, "val"), grid)
        run.log_params({f"threshold.{k}": v for k, v in (result.get("thresholds") or {}).items()})
        run.log_final({f"tuned.{k}": v for k, v in (result.get("validation") or {}).items()})
        run.log_artifact(model_dir / "span_config.json")
    return result
