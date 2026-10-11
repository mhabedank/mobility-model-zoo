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


# ---- feature 012: the share line on the preview image (B6) -----------------------------------
def test_share_line_too_long_fails(reg):
    edit(reg, lambda p: p.update(share_line="x" * 95))
    assert any("share_line" in f and "too long" in f for f in rule_17(reg))  # the schema says 90


def test_share_line_with_placeholder_fails(reg):
    edit(reg, lambda p: p.update(share_line="Runs in {metric:performance.peak_ram_gb}"))
    assert any("metric placeholder" in f for f in rule_17(reg))


def test_long_tagline_without_share_line_fails(reg):
    edit(reg, lambda p: p.pop("share_line"))
    found = [f for f in rule_17(reg) if f.startswith("B6 scout-large")]
    assert found and found[0].endswith("; add share_line to site.yaml")


def test_output_format_without_documentation_fails(reg):
    """A release whose output format is not documented would break the format page (B5)."""
    path = reg.model_dir("scout-large") / "releases" / "0.1.2.yaml"
    record = load_yaml(path)
    record["output_format_version"] = "jtbd-span-v9"
    path.write_text(dump_yaml(record), encoding="utf-8")
    assert "B5 scout-large: output format jtbd-span-v9 has no zoo/formats/jtbd-span-v9.yaml" in rule_17(
        reg
    )


# ---- feature 013: depth budgets of the website text ---------------------------------------------
@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda p: p["differentiators"][0].update(text=" ".join(["w"] * 21)), "differentiators[0].text"),
        (lambda p: p["differentiators"][0].update(title="one two three four five six"), "title"),
        (lambda p: p.update(audience=" ".join(["w"] * 26)), "audience"),
        (lambda p: p["differentiators"].append({"title": "Five", "text": "five"}), "differentiators"),
        (lambda p: p.update(tagline="An experimental extractor."), "release status"),
    ],
)
def test_depth_budgets_of_the_site_text(reg, mutate, needle):
    edit(reg, mutate)
    assert any(needle in f for f in rule_17(reg))
