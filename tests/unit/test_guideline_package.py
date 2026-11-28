"""Owner-approved guideline packages (constitution 3.2.0, Principle XI; scout-large roadmap phase 2)."""

import json

import pytest
import yaml
from helpers import copy_fixture, pilot
from typer.testing import CliRunner

from mobility_model_zoo.productdev.jtbd import guideline_package as gp
from mobility_model_zoo.productdev.jtbd.cli import app
from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.errors import ClaudeGateError, FrozenHashMismatch, UsageError

BRIEF = {
    "teacher_task": "Finde Jobs, Pains und Gains.",
    "teacher_task_en": "Find jobs, pains and gains.",
    "reader": "Ein Produkt Manager",
    "reader_en": "A product manager.",
    "domain": {"owner": "Folge der Definition.", "owner_en": "Follow the definition.",
               "drafted_by": "claude", "approval": "owner, today",
               "definition": "Mobility is the movement of people and goods.",
               "sources": [{"source": "Wikipedia (de)", "url": "https://example.org",
                            "licence": "CC-BY-SA-4.0"}]},
    "kind": {"drafted_by": "claude", "approval": "owner, today", "previous_approval": "earlier",
             "job": "What an actor wants to get done.", "pain": "What bothers the actor."},
    "mode": {"values": ["bus", "car"], "rule": "Every mode named in the quote.", "owner_choice": "x"},
    "pilot_thresholds": {"core": {"relevance_kappa": 0.75}},
    "assembly": {"rule": "Code assembles."},
}
EXAMPLES = {"examples": [
    {"id": "e01", "language": "en", "shows": ["empty"], "text": "Buses run.", "relevant": False,
     "items": [], "links": []},
    {"id": "e02", "language": "de", "shows": ["typical"], "text": "Der Bus kommt nie.", "relevant": True,
     "items": [{"id": "i1", "kind": "pain", "quote": "Der Bus kommt nie."}], "links": []},
]}


@pytest.fixture
def sources(tmp_path):
    brief, examples = tmp_path / "brief.yaml", tmp_path / "examples.yaml"
    brief.write_text(yaml.safe_dump(BRIEF, allow_unicode=True, sort_keys=False), encoding="utf-8")
    examples.write_text(yaml.safe_dump(EXAMPLES, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return brief, examples, tmp_path / "package"


def test_assemble_is_deterministic_and_prints_only_operative_text(sources):
    brief, examples, out = sources
    first = gp.assemble(brief, examples, out)
    guideline = (out / "guideline.md").read_text(encoding="utf-8")
    assert gp.assemble(brief, examples, out) == first
    assert first["contains_claude_drafts"] is True
    assert sorted(first["files"]) == ["examples/01-e01.yaml", "examples/02-e02.yaml", "guideline.md"]
    for printed in ("Find jobs, pains and gains.", "A product manager.", "Follow the definition.",
                    "Mobility is the movement", "Wikipedia (de)", "CC-BY-SA-4.0", "`bus`, `car`"):
        assert printed in guideline
    for hidden in ("Finde Jobs", "Ein Produkt Manager", "Folge der Definition", "drafted_by",
                   "owner, today", "earlier", "relevance_kappa", "Code assembles", "owner_choice"):
        assert hidden not in guideline
    example = yaml.safe_load((out / "examples/02-e02.yaml").read_text(encoding="utf-8"))
    assert "shows" not in example and "language" not in example
    assert example["items"][0]["quote"] == "Der Bus kommt nie."


def test_claude_drafts_need_approval(sources):
    brief, examples, out = sources
    gp.assemble(brief, examples, out)
    with pytest.raises(ClaudeGateError):
        gp.check(out)
    record = gp.approve(out, "Owner Name")
    assert record["approved_by"] == "Owner Name"
    status = gp.check(out)
    assert status["approved"] is True and status["approved_by"] == "Owner Name"


def test_package_without_claude_drafts_needs_no_approval(sources, tmp_path):
    brief, examples, out = sources
    plain = {k: v for k, v in BRIEF.items() if k not in ("domain", "kind")}
    brief.write_text(yaml.safe_dump(plain, allow_unicode=True), encoding="utf-8")
    gp.assemble(brief, examples, out)
    assert gp.check(out)["approved"] is False


def test_changed_file_or_source_is_refused(sources):
    brief, examples, out = sources
    gp.assemble(brief, examples, out)
    gp.approve(out, "Owner Name")
    guideline = out / "guideline.md"
    original = guideline.read_text(encoding="utf-8")
    guideline.write_text(original + "\nextra rule\n", encoding="utf-8")
    with pytest.raises(FrozenHashMismatch):
        gp.check(out)
    guideline.write_text(original, encoding="utf-8")
    (out / "examples/99-extra.yaml").write_text("text: x\n", encoding="utf-8")
    with pytest.raises(FrozenHashMismatch):
        gp.check(out)
    (out / "examples/99-extra.yaml").unlink()
    gp.check(out)
    brief.write_text(brief.read_text(encoding="utf-8") + "\nlanguage: {rule: x}\n", encoding="utf-8")
    with pytest.raises(FrozenHashMismatch):
        gp.check(out)


def test_reassembly_after_change_drops_the_approval(sources):
    brief, examples, out = sources
    gp.assemble(brief, examples, out)
    gp.approve(out, "Owner Name")
    data = yaml.safe_load(examples.read_text(encoding="utf-8"))
    data["examples"][1]["text"] = "Der Bus kommt nie pünktlich."
    data["examples"][1]["items"][0]["quote"] = "Der Bus kommt nie pünktlich."
    examples.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    gp.assemble(brief, examples, out)
    assert not (out / "approval.json").exists()
    with pytest.raises(ClaudeGateError):
        gp.check(out)


def test_approve_needs_a_name(sources):
    brief, examples, out = sources
    gp.assemble(brief, examples, out)
    with pytest.raises(UsageError):
        gp.approve(out, "  ")


@pytest.mark.parametrize("name", ["<dein Name>", "<your name>", "{name}", "Name", "TODO"])
def test_placeholder_names_are_not_an_approval(sources, name):
    brief, examples, out = sources
    gp.assemble(brief, examples, out)
    with pytest.raises(UsageError):
        gp.approve(out, name)
    gp.approve(out, "Owner Name")
    record = json.loads((out / "approval.json").read_text(encoding="utf-8"))
    record["approved_by"] = name
    (out / "approval.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ClaudeGateError):
        gp.check(out)


def test_require_for_run_ignores_guidelines_outside_a_package(tmp_path):
    guideline = tmp_path / "guideline-v2.md"
    guideline.write_text("old guideline\n", encoding="utf-8")
    gp.require_for_run(guideline, tmp_path / "examples")


def test_require_for_run_wants_the_package_examples(sources, tmp_path):
    brief, examples, out = sources
    gp.assemble(brief, examples, out)
    gp.approve(out, "Owner Name")
    with pytest.raises(UsageError):
        gp.require_for_run(out / "guideline.md", tmp_path / "other-examples")
    gp.require_for_run(out / "guideline.md", out / "examples")


def test_cli_exit_codes(sources):
    brief, examples, out = sources
    runner = CliRunner()
    result = runner.invoke(app, ["guide", "assemble", "--brief", str(brief), "--examples", str(examples),
                                 "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert runner.invoke(app, ["guide", "check", "--package", str(out)]).exit_code == 7
    approve = ["guide", "approve", "--package", str(out), "--by", "Owner Name"]
    assert runner.invoke(app, approve).exit_code == 0
    assert runner.invoke(app, ["guide", "check", "--package", str(out)]).exit_code == 0
    (out / "guideline.md").write_text("changed\n", encoding="utf-8")
    assert runner.invoke(app, ["guide", "check", "--package", str(out)]).exit_code == 3


def _make_fixture_a_package(config):
    """Turn the fixture's guideline directory into an assembled package with Claude drafts."""
    settings = load_settings(config)
    package = settings.paths["guideline"].parent
    files = {"guideline.md": gp.sha256_bytes(settings.paths["guideline"].read_bytes())}
    for path in sorted(settings.paths["examples"].glob("*.yaml")):
        files[f"examples/{path.name}"] = gp.sha256_bytes(path.read_bytes())
    manifest = {"template_version": 1, "contains_claude_drafts": True,
                "sources": {"brief": {"path": "guideline.md", "sha256": files["guideline.md"]}},
                "files": files}
    (package / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    return package


def test_label_run_refuses_an_unapproved_package_before_anything_else(tmp_path):
    config = copy_fixture(tmp_path)
    package = _make_fixture_a_package(config)
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a", expect=7)
    gp.approve(package, "Owner Name")
    # Approved: the run gets past the package check and stops at the missing freeze, as before.
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a", expect=3)
