"""Pilot evaluation and frozen criteria (feature 009 spec Riskiest Assumption, T057)."""

from __future__ import annotations

import subprocess

import pytest
import yaml
from typer.testing import CliRunner

from mobility_model_zoo.catalog import pilot
from mobility_model_zoo.catalog.model import load
from mobility_model_zoo.datasets import UsageRefused
from mobility_model_zoo.release.cli import app

runner = CliRunner()
CRITERIA = {"min_determined_licence_share": 0.30, "min_training_allowed": 1, "min_languages_passing": 2}


def _git(root, *args):
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.test",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.test",
            "GIT_AUTHOR_DATE": "2026-10-01T00:00:00",
            "GIT_COMMITTER_DATE": "2026-10-01T00:00:00",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
        },
    )


@pytest.fixture
def piloted(catalog_dir):
    """Fixture entries become the output of run 2026-10-05-pilot; pilot file committed before it."""
    cat = load(catalog_dir)
    for e in cat.entries.values():
        e["provenance"]["added_by"] = "run:2026-10-05-pilot"
        cat.write_entry(e)
    (catalog_dir / "runs").mkdir()
    (catalog_dir / "runs" / "2026-10-05-pilot.yaml").write_text(
        yaml.safe_dump({"id": "2026-10-05-pilot", "date": "2026-10-05", "kind": "agent"})
    )
    (catalog_dir / "pilot").mkdir()
    pf = catalog_dir / "pilot" / "pilot-v1.yaml"
    pf.write_text(
        yaml.safe_dump(
            {
                "languages": ["es", "pl", "ja"],
                "modalities": ["text", "video"],
                "runs": ["2026-10-05-pilot"],
                "criteria": CRITERIA,
                "criteria_changes": [],
            }
        )
    )
    _git(catalog_dir, "init", "-q")
    _git(catalog_dir, "add", "-A")
    _git(catalog_dir, "commit", "-qm", "pilot")
    return catalog_dir, pf


def test_pass_and_fail_per_language(piloted):
    root, pf = piloted
    result = pilot.evaluate(load(root), pf)
    by = {r["language"]: r for r in result["languages"]}
    assert by["es"]["passed"] and by["es"]["accepted"] == 3 and by["es"]["training_allowed"] == 2
    assert by["pl"]["passed"]  # pl-stat (training_allowed) and pl-radio
    assert not by["ja"]["passed"]  # one entry, licence unknown
    assert result["passed"]  # 2 of 3 languages


def test_overall_fail_when_two_languages_miss(piloted):
    root, pf = piloted
    data = yaml.safe_load(pf.read_text())
    data["languages"] = ["es", "ja", "ko"]
    pf.write_text(yaml.safe_dump(data))
    assert not pilot.evaluate(load(root), pf)["passed"]
    res = runner.invoke(
        app, ["catalog", "--catalog", str(root), "pilot", "evaluate", "pilot/pilot-v1.yaml"]
    )
    assert res.exit_code == 1 and "overall: FAIL" in res.stdout


def test_changed_criteria_need_a_rationale(piloted):
    root, pf = piloted
    data = yaml.safe_load(pf.read_text())
    data["criteria"]["min_training_allowed"] = 0
    pf.write_text(yaml.safe_dump(data))
    _git(root, "commit", "-qam", "lower the bar")
    # the commit date is before the run date in this fixture; move the run before it
    run = root / "runs" / "2026-10-05-pilot.yaml"
    run.write_text(yaml.safe_dump({"id": "2026-10-05-pilot", "date": "2026-09-01", "kind": "agent"}))
    with pytest.raises(UsageRefused):
        pilot.evaluate(load(root), pf)
    data["criteria_changes"] = [
        {"date": "2026-10-01", "change": "min_training_allowed 1 → 0", "rationale": "test"}
    ]
    pf.write_text(yaml.safe_dump(data))
    pilot.evaluate(load(root), pf)
