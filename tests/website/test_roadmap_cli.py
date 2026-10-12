"""`zoo roadmap check` and `zoo roadmap pace` (feature 015, contracts/cli.md)."""

from __future__ import annotations

from typer.testing import CliRunner

from mobility_model_zoo.release.cli import app

runner = CliRunner()


def run(site_env, monkeypatch, *args):
    monkeypatch.chdir(site_env.root)
    return runner.invoke(app, ["roadmap", *args])


def test_check_passes_on_the_fixture(site_env, monkeypatch):
    result = run(site_env, monkeypatch, "check")
    assert result.exit_code == 0, result.output
    assert "roadmap: ok (4 open entries)" in result.output


def test_check_fails_with_a_finding(site_env, monkeypatch):
    site_env.edit_yaml(
        "zoo/roadmap/roadmap.yaml",
        lambda r: r.update(entries=[e for e in r["entries"] if e["id"] != "picket-forest"]),
    )
    result = run(site_env, monkeypatch, "check")
    assert result.exit_code != 0
    assert "RM2 picket-forest: registered and unpublished, but has no open entry" in result.output


def test_pace_refuses_an_open_quarter(site_env, monkeypatch):
    result = run(site_env, monkeypatch, "pace", "2026-Q4")
    assert result.exit_code != 0 and "has not ended yet" in result.output
    draft = run(site_env, monkeypatch, "pace", "2026-Q4", "--draft")
    assert draft.exit_code == 0 and "# Pace review Q4 2026 (draft)" in draft.output


def test_pace_rejects_a_bad_quarter(site_env, monkeypatch):
    result = run(site_env, monkeypatch, "pace", "Q4-2026")
    assert result.exit_code != 0 and "not a quarter id" in result.output
