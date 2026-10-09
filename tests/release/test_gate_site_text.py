"""Gate rule 17 (feature 008): a release cannot be published with website text that would break
the site build."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mobility_model_zoo.release.gate import Gate
from mobility_model_zoo.release.registry import Registry, dump_yaml, load_yaml

SITE_FIXTURE = Path(__file__).resolve().parents[1] / "website" / "fixtures" / "registry"


@pytest.fixture
def reg(tmp_path: Path) -> Registry:
    shutil.copytree(SITE_FIXTURE, tmp_path / "repo")
    return Registry(tmp_path / "repo")


def rule_17(reg: Registry, name: str = "scout-large", version: str = "0.1.2") -> list[str]:
    gate = Gate(reg, name, version)
    gate.model, gate.record = reg.model_raw(name), reg.record_raw(name, version)
    return gate.rule_17()


def edit(reg: Registry, fn) -> None:
    path = reg.model_dir("scout-large") / "site.yaml"
    data = load_yaml(path)
    fn(data)
    path.write_text(dump_yaml(data), encoding="utf-8")


def test_valid_site_text_passes(reg):
    assert rule_17(reg) == []


def test_missing_site_text_fails(reg):
    (reg.model_dir("scout-large") / "site.yaml").unlink()
    assert any("site.yaml is missing" in f for f in rule_17(reg))


def test_unresolvable_placeholder_fails(reg):
    edit(reg, lambda p: p["differentiators"][0].update(text="{metric:quality.not_measured}"))
    assert any("not_measured" in f for f in rule_17(reg))


def test_missing_quickstart_example_fails(reg):
    edit(reg, lambda p: p.update(quickstart_example="09-none.txt"))
    assert any("09-none.txt" in f for f in rule_17(reg))


def test_sandbox_models_skip(reg):
    from mobility_model_zoo.release.gate import Skip

    with pytest.raises(Skip):
        rule_17(reg, "sandbox-pipeline-tiny", "0.1.0")
