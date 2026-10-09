"""Paths of the edge tooling in the zoo repository (feature 005, research R5, R10, R16).

The repository root is found by walking up to `pyproject.toml`, so the code works from any module
location. Downloaded data and derived files live outside the repository in $MMZ_DATA.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path


@cache
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "zoo").is_dir():
            return parent
    return Path.cwd()


def data_root() -> Path:
    """Downloaded datasets and derived files; never inside the repository."""
    root = os.environ.get("MMZ_DATA")
    return (
        Path(root).expanduser() if root else Path.home() / ".cache" / "mobility-model-zoo" / "datasets"
    )


def derived_dir(name: str) -> Path:
    return data_root() / "derived" / name


REPO_ROOT = repo_root()
HIL_DIR = REPO_ROOT / "hil"
BENCH_FIRMWARE = REPO_ROOT / "firmware" / "bench"
MODELZOO_SRC = BENCH_FIRMWARE / "lib" / "modelzoo" / "src"  # generated, gitignored
BUILD_DIR = REPO_ROOT / "build"
EDGE_MODELS = BUILD_DIR / "edge" / "models"  # reference models built for the bench (gitignored)
CUSTOM_MODELS = BUILD_DIR / "edge" / "custom"  # imported models (`edge import-tflite`)
