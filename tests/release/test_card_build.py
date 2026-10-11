"""The card for the sandbox fixture matches its golden file and follows contracts/model-card.md (T040).

Regenerate the golden file after an intended template change with:
    ZOO_UPDATE_GOLDEN=1 uv run pytest tests/release/test_card_build.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from release_env import FakeRunner

from mobility_model_zoo.release import card as cards
from mobility_model_zoo.release.gate import Gate, card_structure

GOLDEN = Path(__file__).resolve().parent / "fixtures/golden/sandbox-pipeline-tiny-0.1.0.README.md"
TEMPLATE = Path(cards.__file__).resolve().parent / "templates/model_card.md.j2"


def normalized(card: str, env) -> str:
    """Replace the per-run git commit and staging revision with fixed values."""
    record = env.record()
    return card.replace(record["recipe"]["git_commit"], "<git-commit>").replace(
        record["staging"]["revision"], "<staging-revision>"
    )


def test_card_matches_golden_file(zoo_env):
    gate = Gate(zoo_env.reg, zoo_env.model, zoo_env.version, hub=zoo_env.hub, runner=FakeRunner())
    gate.run(lambda line: None)
    card = normalized(gate.card, zoo_env)
    if os.environ.get("ZOO_UPDATE_GOLDEN"):
        GOLDEN.write_text(card, encoding="utf-8")
    assert card == GOLDEN.read_text(encoding="utf-8")


def test_every_section_present_and_in_order(zoo_env):
    card = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version))
    assert card_structure(card) == []
    headings = [line[3:] for line in card.splitlines() if line.startswith("## ")]
    assert headings == list(cards.SECTIONS)


def test_template_has_no_literal_numbers():
    text = TEMPLATE.read_text(encoding="utf-8")
    without_tags = re.sub(r"{[{%].*?[}%]}", "", text)
    assert not re.findall(r"(?<![\w.-])\d+\.\d+(?![\w.-])", without_tags)


def test_no_accuracy_and_the_agreement_sentence(zoo_env):
    card = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version))
    assert "accuracy" not in card.lower()
    assert "These numbers are agreement with" in card
    assert "they are not measured against human ground truth." in card


def test_metrics_without_optional_fields_render(zoo_env):
    """`n_items`, `hardware`, `reference` and `benchmark` are optional in the results schema; the
    card leaves the cell empty instead of failing (found with scout-large 0.1.0, 2026-10-07)."""
    import json

    path = zoo_env.reg.results_path(zoo_env.model, zoo_env.version, "performance")
    data = json.loads(path.read_text(encoding="utf-8"))
    for metric in data["metrics"]:
        metric.pop("n_items", None)
    path.write_text(json.dumps(data), encoding="utf-8")
    qpath = zoo_env.reg.results_path(zoo_env.model, zoo_env.version, "quality")
    quality = json.loads(qpath.read_text(encoding="utf-8"))
    for key in ("n_items", "reference", "benchmark"):
        quality["metrics"][0].pop(key, None)
    qpath.write_text(json.dumps(quality), encoding="utf-8")
    card = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version))
    assert card_structure(card) == []


def test_figures_link_the_release_tag_and_must_exist(zoo_env):
    from mobility_model_zoo.release.registry import dump_yaml

    data = zoo_env.reg.model_raw(zoo_env.model)
    data["card"]["figures"] = [{"path": "docs/figures/speed.png", "alt": "Speed"}]
    (zoo_env.reg.model_dir(zoo_env.model) / "model.yaml").write_text(dump_yaml(data), encoding="utf-8")
    card = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version))
    tag = f"{zoo_env.model}/v{zoo_env.version}"
    raw = "https://raw.githubusercontent.com/mhabedank/mobility-model-zoo"
    assert f"![Speed]({raw}/refs/tags/{tag}/docs/figures/speed.png)" in card
    import pytest

    from mobility_model_zoo.release.errors import GateFailed

    gate = Gate(zoo_env.reg, zoo_env.model, zoo_env.version, hub=zoo_env.hub, runner=FakeRunner())
    with pytest.raises(GateFailed) as exc:
        gate.run(lambda line: None)
    assert any("figure docs/figures/speed.png is not in the repository" in f for f in exc.value.failures)


# ---- feature 014: short forms on the card ------------------------------------------------------
def _section(card: str, title: str) -> str:
    return card.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0]


def test_card_without_short_forms_renders_the_status_sentence_only(zoo_env):
    """model.yaml of an older tag has no short forms: no 'Not for', no short limits, no error."""
    card = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version))
    assert "**Not for:**" not in card
    limits = _section(card, "Limitations and risks")
    assert limits.lstrip().startswith("**Experimental: not ready for production use.**")
    assert "Not met yet" not in limits and "Known limits in short" not in limits


def test_card_short_forms_under_summary_and_on_top_of_the_limits(zoo_env):
    model = zoo_env.reg.model_raw(zoo_env.model)
    model["card"].update(
        not_for=["Production use", "Texts outside mobility"],
        limits_short=["Seed {metric:quality.schema_valid_rate} only."],
        unmet_criteria=[
            {
                "criterion": "Schema validity",
                "measured": "{metric:quality.schema_valid_rate}",
                "target": {"op": ">=", "value": 2, "unit": "", "source": "docs/adding-a-model.md"},
            },
            {"criterion": "Real weights", "note": "random weights"},
        ],
    )
    card = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version, model=model))
    summary = _section(card, "Summary")
    assert "**Not for:**" in summary and "- Texts outside mobility" in summary
    limits = _section(card, "Limitations and risks")
    assert (
        limits.index("Not met yet")
        < limits.index("Known limits in short")
        < limits.index("All limitations")
    )
    assert "- **Real weights**: random weights" in limits
    assert "(target ≥ 2)" in limits and "{metric:" not in card
