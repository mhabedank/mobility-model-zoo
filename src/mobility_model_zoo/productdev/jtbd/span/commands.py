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


def train_command(settings: Settings, recipe_file: str | None, out: Path, device: str,
                  max_epochs: int | None = None) -> dict[str, Any]:
    """Train one candidate after every gate passes (FR-001, FR-005, FR-006, Principle IV)."""
    if settings.span_train is None:
        raise UsageError("span train needs the training dataset config (span_train section)")
    frozen = frozen_data(settings)
    recipe = load_recipe(settings, recipe_file)
    dims = recipe_dimensions(recipe)
    _, decision = pilot_decision(settings)
    passed = passed_attributes(decision)
    if dims != passed:
        raise ValidationFailed(f"the recipe's dimensions {dims} differ from the attribute "
                               f"dimensions that passed the pilot {passed}")
    bar = check_release_bar(settings, recipe)
    require_clean_tree(settings)
    rows = load_rows(settings)
    minimum = int(settings.span_train["min_usable_chunks"])
    if len(rows) < minimum:
        raise ValidationFailed(f"only {len(rows)} usable training rows, fewer than "
                               f"{minimum}; the model is not trained (FR-005)")
    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "val"]
    meta = {
        "dataset": {"name": settings.span_train.get("dataset"), "sha256": frozen["sha256"],
                    "train_chunks": len(train_rows), "val_chunks": len(val_rows)},
        "recipe": Path(recipe["_path"]).resolve().relative_to(settings.base.resolve()).as_posix(),
        "recipe_commit": head_commit(settings),
        **bar,
    }
    if max_epochs:
        meta["max_epochs_override"] = max_epochs
    from mobility_model_zoo.productdev.jtbd.span.train import train_candidate

    return train_candidate(recipe, dims, train_rows, val_rows, out, device, meta, max_epochs,
                           log=_log)


def tune_command(settings: Settings, model_dir: Path, recipe_file: str | None) -> dict[str, Any]:
    from mobility_model_zoo.productdev.jtbd.span.tune import tune_thresholds

    recipe = load_recipe(settings, recipe_file)
    grid = [float(v) for v in recipe["thresholds"]["unit_grid"]]
    return tune_thresholds(Path(model_dir), load_rows(settings, "val"), grid)
