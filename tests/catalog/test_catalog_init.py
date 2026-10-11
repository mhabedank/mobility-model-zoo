"""`zoo catalog init` (feature 009 R1, T019)."""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from mobility_model_zoo.release.cli import app

runner = CliRunner()
REPO = Path(__file__).resolve().parents[2]


def test_init_creates_the_layout(tmp_path):
    target = tmp_path / "cat"
    res = runner.invoke(app, ["catalog", "init", str(target)])
    assert res.exit_code == 0, res.output
    for rel in (
        "catalog.yaml",
        "README.md",
        ".gitignore",
        "entries",
        "runs",
        "fetch-lists",
        "reports",
        "pilot",
        ".github/workflows/check.yml",
        ".github/workflows/recheck.yml",
    ):
        assert (target / rel).exists(), rel
    recheck = yaml.safe_load((target / ".github/workflows/recheck.yml").read_text())
    assert recheck[True]["schedule"][0]["cron"] == "0 4 1 * *"  # YAML 1.1 reads `on` as True
    assert "contents: write" in (target / ".github/workflows/recheck.yml").read_text()
    ok = runner.invoke(app, ["catalog", "--catalog", str(target), "validate"])
    assert ok.exit_code == 0, ok.output


def test_init_refuses_a_non_empty_directory(tmp_path):
    (tmp_path / "x").write_text("x")
    res = runner.invoke(app, ["catalog", "init", str(tmp_path)])
    assert res.exit_code == 3


def test_init_refuses_the_zoo_repository():
    res = runner.invoke(app, ["catalog", "init", str(REPO / "catalog-here")])
    assert res.exit_code == 3
    assert not (REPO / "catalog-here").exists()
