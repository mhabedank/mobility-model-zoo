"""Fixtures of the website tests (see site_fixture.py)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_fixture import FIXTURE, SiteEnv  # noqa: E402

from mobility_model_zoo.release.registry import Registry  # noqa: E402


@pytest.fixture
def site_env(tmp_path: Path) -> SiteEnv:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return SiteEnv(root=root, reg=Registry(root), out=tmp_path / "site")


@pytest.fixture
def built(site_env: SiteEnv) -> SiteEnv:
    site_env.build()
    return site_env
