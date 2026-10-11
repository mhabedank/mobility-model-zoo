"""Fixtures for the release tool: a temporary repository with a valid sandbox registry, a git
history that contains the recipe, and a FakeHub whose staging repo holds the staged files.
The helpers live in release_env.py (unique module name, see there)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_env import (  # noqa: E402,F401
    FIXTURES,
    MODEL,
    STAGED,
    VERSION,
    FakeRunner,
    ZooEnv,
    git,
    lines,
    make_env,
    make_mcu_env,
    make_mcu_forest_env,
)


@pytest.fixture
def zoo_env(tmp_path: Path) -> ZooEnv:
    return make_env(tmp_path)


@pytest.fixture
def mcu_env(tmp_path: Path) -> ZooEnv:
    return make_mcu_env(tmp_path)


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()


@pytest.fixture
def mcu_forest_env(tmp_path: Path) -> ZooEnv:
    import shutil

    pytest.importorskip("emlearn")
    pytest.importorskip("sklearn")
    if not (shutil.which("cc") or shutil.which("gcc")):
        pytest.skip("needs a C compiler")
    return make_mcu_forest_env(tmp_path)
