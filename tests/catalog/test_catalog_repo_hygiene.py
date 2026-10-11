"""Catalog entries never live in the public repository (feature 009 R1, FR-032, T020)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
ALLOWED = ("tests/fixtures/catalog/", "tests/fixtures/catalog-invalid/")


def test_no_catalog_entries_outside_the_fixtures():
    files = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "*.yaml", "*.yml"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    offenders = []
    for rel in files:
        if rel.startswith(ALLOWED):
            continue
        try:
            data = yaml.safe_load((REPO / rel).read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError, FileNotFoundError):
            continue
        if isinstance(data, dict) and "schema_version" in data and "landing_url" in data:
            offenders.append(rel)
    assert offenders == []


def test_no_entries_directory_in_the_repository():
    assert not (REPO / "entries").exists()
    assert not (REPO / "catalog").exists()
