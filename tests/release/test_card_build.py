"""The card for the sandbox fixture matches its golden file and follows contracts/model-card.md (T040).

Regenerate the golden file after an intended template change with:
    ZOO_UPDATE_GOLDEN=1 uv run pytest tests/release/test_card_build.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from conftest import FakeRunner

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
