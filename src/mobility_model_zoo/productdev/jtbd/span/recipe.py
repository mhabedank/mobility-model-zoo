"""The span model recipe `configs/productdev/jtbd/span-xlmr.yaml` (data-model.md)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed

DEFAULT_RECIPE = Path("configs/productdev/jtbd/span-xlmr.yaml")
ATTRIBUTES = ("actor_type", "evidence_type", "evidence_scope")


def recipe_path(settings: Settings, path: str | Path | None = None) -> Path:
    path = Path(path or DEFAULT_RECIPE)
    return path if path.is_absolute() else settings.base / path


def load_recipe(settings: Settings, path: str | Path | None = None) -> dict[str, Any]:
    file = recipe_path(settings, path)
    if not file.exists():
        raise UsageError(f"recipe not found: {file}")
    recipe = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    recipe["_path"] = str(file)
    return recipe


def recipe_dimensions(recipe: dict[str, Any]) -> list[str]:
    """Attribute dimensions the model produces; set from the pilot's decision (T037)."""
    dims = recipe.get("dimensions")
    if dims is None:
        raise ValidationFailed("the recipe's `dimensions` is not set yet; set it to the attribute "
                               "dimensions that passed the pilot (T037)")
    unknown = set(dims) - set(ATTRIBUTES)
    if unknown:
        raise ValidationFailed(f"unknown dimensions in the recipe: {sorted(unknown)}")
    return [d for d in ATTRIBUTES if d in dims]


def git(settings: Settings, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=settings.base, capture_output=True, text=True)
    if done.returncode != 0:
        raise ValidationFailed(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def head_commit(settings: Settings) -> str:
    return git(settings, "rev-parse", "HEAD")


def require_clean_tree(settings: Settings, paths: tuple[str, ...] = ("src", "configs")) -> None:
    """Refuse uncommitted changes under `paths`, so a run is reproducible from its commit."""
    dirty = git(settings, "status", "--porcelain", "--", *paths)
    if dirty:
        raise ValidationFailed(f"uncommitted changes under {list(paths)}; commit them first:\n"
                               f"{dirty}")
