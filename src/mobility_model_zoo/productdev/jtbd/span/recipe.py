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


def release_bar_commit(settings: Settings, recipe: dict[str, Any]) -> str:
    """The first commit whose recipe file contains `release_bar` (Principle IV)."""
    rel = Path(recipe["_path"]).resolve().relative_to(settings.base.resolve()).as_posix()
    commits = git(settings, "log", "--format=%H", "--reverse", "-S", "release_bar:", "--", rel)
    if not commits:
        raise ValidationFailed(f"the release bar in {rel} is not committed; commit it before "
                               "training (Principle IV)")
    return commits.splitlines()[0]


def check_release_bar(settings: Settings, recipe: dict[str, Any]) -> dict[str, Any]:
    """The release bar was committed before this run and has not changed since, unless every
    change is recorded in `release_bar_changes` with date and rationale."""
    commit = release_bar_commit(settings, recipe)
    done = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                          cwd=settings.base, capture_output=True, text=True)
    if done.returncode != 0:
        raise ValidationFailed(f"the release bar commit {commit[:12]} is not an ancestor of HEAD")
    rel = Path(recipe["_path"]).resolve().relative_to(settings.base.resolve()).as_posix()
    original = (yaml.safe_load(git(settings, "show", f"{commit}:{rel}")) or {}).get("release_bar")
    changes = recipe.get("release_bar_changes") or []
    if recipe.get("release_bar") != original:
        complete = [c for c in changes if isinstance(c, dict) and c.get("date")
                    and c.get("rationale")]
        if not complete:
            raise ValidationFailed("release_bar changed since it was committed "
                                   f"({commit[:12]}); record the change with date and rationale "
                                   "in release_bar_changes (Principle IV)")
    return {"release_bar_commit": commit, "release_bar_changes": changes}
