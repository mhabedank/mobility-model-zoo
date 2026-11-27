"""Claude gate (constitution Principle XI, decision D-claude-ban).

No test calls a model: backends are mocks or are stopped before they are built.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mobility_model_zoo.productdev.jtbd.config import ModelEntry, load_settings
from mobility_model_zoo.productdev.jtbd.errors import ClaudeGateError
from mobility_model_zoo.productdev.jtbd.labeling import gate
from mobility_model_zoo.productdev.jtbd.labeling.base import make_backend

REPO = Path(__file__).resolve().parents[2]
PILOT_V1 = str(REPO / "configs/productdev/jtbd/pilot-v1.yaml")


def entry(**kw) -> ModelEntry:
    base = {"model_id": "m", "family": "fam", "backend": "mock", "host": "local", "role": "reference"}
    return ModelEntry(**{**base, **kw})


@pytest.fixture
def settings(tmp_path, fixture_dir):
    work = tmp_path / "mini"
    shutil.copytree(fixture_dir, work)
    return load_settings(work / "pilot.yaml")


# ---- (a) what fails ---------------------------------------------------------------------------

@pytest.mark.parametrize("kw", [
    {"family": "anthropic-claude"},
    {"backend": "claude_cli"},
    {"backend": "anthropic_api"},
    {"api_model": "opus"},
    {"api_model": "anthropic/claude-sonnet-4.5"},
    {"api_model": "Claude-Haiku"},
    {"model_id": "claude-reference"},
    {"api_model": "fable-5-1"},
])
def test_claude_entries_fail(kw):
    result = gate.check_entry(entry(**kw))
    assert result.status == "fail"
    assert result.reason


@pytest.mark.parametrize("resolved", [
    "anthropic/claude-opus-4", "claude-3-5-sonnet-20241022", "us.anthropic.claude-v2", "SONNET",
])
def test_claude_resolved_names_fail(resolved):
    assert gate.check_resolved(entry(), resolved).status == "fail"


@pytest.mark.parametrize("resolved", [
    "sha256:4f1d0c0ffee", "deepseek/deepseek-v4-pro", "gpt-oss:120b", "corpus-model", "opusculum",
])
def test_other_resolved_names_pass(resolved):
    assert gate.check_resolved(entry(), resolved).status == "pass"


# ---- (b) the registered non-Claude references pass -------------------------------------------

def test_registered_references_pass():
    settings = load_settings(PILOT_V1)
    for model_id in ("ref-qwen3.8-27b", "ref-deepseek-v4.1-flash", "gpt-mini-reference"):
        assert gate.check_entry(settings.model(model_id)).status == "pass", model_id
        assert settings.model(model_id).benchmark_labeler
    for model_id in ("ref-qwen3.8-27b", "ref-deepseek-v4.1-flash"):
        assert settings.model(model_id).teacher_banned, model_id
    assert gate.check_entry(settings.model("claude-reference")).status == "fail"


# ---- (c) make_backend stops before building a Claude backend ----------------------------------

def test_make_backend_refuses_before_construction(settings, monkeypatch):
    import mobility_model_zoo.productdev.jtbd.labeling.claude_cli as claude_cli

    def boom(*_a, **_k):
        raise AssertionError("a Claude backend was constructed")

    monkeypatch.setattr(claude_cli, "ClaudeCliBackend", boom)
    claude = entry(model_id="c", family="anthropic-claude", backend="claude_cli")
    with pytest.raises(ClaudeGateError):
        make_backend(settings, claude, "claude_cli", None)


def test_make_backend_checks_the_resolved_model(settings, monkeypatch):
    from mobility_model_zoo.productdev.jtbd.labeling import mock

    model = make_backend(settings, settings.model("mock-a"), "mock", None)
    assert model.call("s", "u", {}, "ch-001").model_version == "mock-mock-a"

    real_call = mock.MockBackend.call

    def renamed(self, *a, **k):
        result = real_call(self, *a, **k)
        result.model_version = "anthropic/claude-opus-4"
        return result

    monkeypatch.setattr(mock.MockBackend, "call", renamed)
    model = make_backend(settings, settings.model("mock-a"), "mock", None)
    with pytest.raises(ClaudeGateError):
        model.call("s", "u", {}, "ch-001")


def test_gate_error_exit_code():
    assert ClaudeGateError.exit_code == 7


# ---- (d) stored run records ------------------------------------------------------------------

def test_require_pass_accepts_only_passing_records():
    gate.require_pass({"run_id": "r", "gate": {"status": "pass", "reason": ""}})
    with pytest.raises(ClaudeGateError):
        gate.require_pass({"run_id": "r", "gate": {"status": "fail", "reason": "family"}})
    with pytest.raises(ClaudeGateError):
        gate.require_pass({"run_id": "r"})


def test_require_pass_rechecks_the_recorded_model():
    record = {"run_id": "r", "gate": {"status": "pass", "reason": ""}, "family": "anthropic-claude",
              "backend": "claude_cli", "model_id": "claude-reference", "model_version": "x"}
    with pytest.raises(ClaudeGateError):
        gate.require_pass(record)


# ---- (e) `jtbd label` -----------------------------------------------------------------------

CLAUDE_ENTRY = """\
- model_id: claude-x
  family: anthropic-claude
  backend: claude_cli
  host: subscription
  role: reference
  benchmark_labeler: true
"""


@pytest.fixture
def config(tmp_path):
    from helpers import copy_fixture

    cfg = copy_fixture(tmp_path)
    models = cfg.parent / "models.yaml"
    models.write_text(models.read_text() + CLAUDE_ENTRY)
    return cfg


@pytest.mark.parametrize("dry_run", [False, True])
def test_label_refuses_a_claude_entry_with_exit_7(config, dry_run):
    from helpers import pilot

    args = ["--dry-run"] if dry_run else []
    pilot(config, *args, "label", "--role", "reference", "--backend", "claude_cli",
          "--model", "claude-x", expect=7)


def test_label_refuses_a_claude_backend_with_exit_7(config):
    from helpers import pilot

    pilot(config, "label", "--role", "reference", "--backend", "anthropic_api", "--model", "mock-a",
          expect=7)


def test_label_refuses_the_registered_claude_reference_with_exit_7():
    from mobility_model_zoo.productdev.jtbd.cli import app

    result = CliRunner().invoke(app, ["--config", PILOT_V1, "--dry-run", "label", "--role", "reference",
                                      "--backend", "claude_cli", "--model", "claude-reference"])
    assert result.exit_code == 7, result.output


def test_label_records_the_gate_in_the_manifest(config):
    from helpers import pilot, run_ids

    pilot(config, "freeze")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a")
    run = run_ids(config)["mock-a"]
    manifest = json.loads((load_settings(config).runs_dir / run / "manifest.json").read_text())
    assert manifest["gate"] == {"status": "pass", "reason": ""}
    assert manifest["requested_model"] == "mock-a"
    assert manifest["resolved_model"] == manifest["model_version"]
    gate.require_pass(manifest)
