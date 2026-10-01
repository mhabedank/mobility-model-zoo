"""FR-012: the release token never appears in any output of the release tool (T063)."""

from __future__ import annotations

import subprocess

from conftest import FakeRunner
from typer.testing import CliRunner

from mobility_model_zoo.release import cli
from mobility_model_zoo.release.usage import VenvRunner

SENTINEL = "hf_SENTINELTOKEN0123456789abcdefSECRET"


def test_check_build_preview_publish_never_print_the_token(zoo_env, monkeypatch):
    monkeypatch.chdir(zoo_env.root)
    monkeypatch.setenv("HF_RELEASE_TOKEN", SENTINEL)
    monkeypatch.setattr(cli, "_hub", lambda env_name: zoo_env.hub)
    monkeypatch.setattr(cli, "_runner", lambda: FakeRunner())
    runner = CliRunner()
    outputs = []
    for args in (
        ["check", zoo_env.model, zoo_env.version],
        ["build", zoo_env.model, zoo_env.version, "--out", "build"],
        ["preview", zoo_env.model, zoo_env.version, "--build", "build"],
        ["publish", zoo_env.model, zoo_env.version, "--confirm", f"{zoo_env.model}/v{zoo_env.version}"],
        ["publish", zoo_env.model, zoo_env.version, "--confirm", f"{zoo_env.model}/v{zoo_env.version}"],
    ):
        result = runner.invoke(cli.app, args)
        outputs.append(result.output)
    assert [o for o in outputs if SENTINEL in o] == []
    assert "already published" in outputs[-1]  # the last run was refused (exit 3), still no token


def test_usage_runner_redacts_the_token_from_errors(tmp_path, monkeypatch):
    runner = VenvRunner(tmp_path, SENTINEL)
    monkeypatch.setattr(runner, "_python", lambda: tmp_path / "python")
    runner._dir = tmp_path

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, "", f"401 for token {SENTINEL}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc, out, err = runner.run("print(1)")
    assert rc == 1 and SENTINEL not in err and "***" in err
