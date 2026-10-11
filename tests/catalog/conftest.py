"""Fixtures of the catalog tests (feature 009): copies of the synthetic fixture catalogs."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def catalog_dir(tmp_path: Path) -> Path:
    """A writable copy of tests/fixtures/catalog."""
    target = tmp_path / "catalog"
    shutil.copytree(FIXTURES / "catalog", target)
    return target


@pytest.fixture
def invalid_dir(tmp_path: Path) -> Path:
    target = tmp_path / "catalog-invalid"
    shutil.copytree(FIXTURES / "catalog-invalid", target)
    return target


@pytest.fixture(autouse=True)
def _no_catalog_env(monkeypatch):
    monkeypatch.delenv("MMZ_CATALOG", raising=False)
