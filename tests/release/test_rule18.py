"""Gate rule 18 (feature 013): a release states its status in short form. `experimental` names every
unmet criterion with its measured value, `released` names none; `not_for` and `limits_short` exist."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mobility_model_zoo.release.gate import Gate, Skip
from mobility_model_zoo.release.registry import Registry, dump_yaml, load_yaml

SITE_FIXTURE = Path(__file__).resolve().parents[1] / "website" / "fixtures" / "registry"


@pytest.fixture
def reg(tmp_path: Path) -> Registry:
    shutil.copytree(SITE_FIXTURE, tmp_path / "repo")
    return Registry(tmp_path / "repo")


def rule_18(reg: Registry, name: str = "scout-large", version: str = "0.1.2") -> list[str]:
    gate = Gate(reg, name, version)
    gate.model, gate.record = reg.model_raw(name), reg.record_raw(name, version)
    return gate.rule_18()


def edit(reg: Registry, fn, rel: str = "model.yaml") -> None:
    path = reg.model_dir("scout-large") / rel
    data = load_yaml(path)
    fn(data)
    path.write_text(dump_yaml(data), encoding="utf-8")


def test_fixture_passes(reg):
    assert rule_18(reg) == []


def test_short_forms_are_required(reg):
    edit(reg, lambda m: m["card"].pop("not_for"))
    edit(reg, lambda m: m["card"].pop("limits_short"))
    failures = rule_18(reg)
    assert any("not_for" in f for f in failures) and any("limits_short" in f for f in failures)


def test_experimental_needs_unmet_criteria(reg):
    edit(reg, lambda m: m["card"].pop("unmet_criteria"))
    assert any("experimental" in f for f in rule_18(reg))


def test_released_has_none(reg):
    edit(reg, lambda r: r.update(status="released"), "releases/0.1.2.yaml")
    assert any("released" in f for f in rule_18(reg))


def test_measured_must_resolve_and_source_must_exist(reg):
    item = {
        "criterion": "Item matching",
        "measured": "{metric:quality.not_measured}",
        "target": {"op": ">=", "value": 0.7, "unit": "", "source": "topics/none.md"},
    }
    edit(reg, lambda m: m["card"].update(unmet_criteria=[item]))
    failures = rule_18(reg)
    assert any("not_measured" in f for f in failures) and any("topics/none.md" in f for f in failures)


def test_sandbox_models_skip(reg):
    with pytest.raises(Skip):
        rule_18(reg, "sandbox-pipeline-tiny", "0.1.0")
