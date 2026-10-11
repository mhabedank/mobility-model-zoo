"""Model card of an emlearn tree model (feature 007, T024).

Regenerate the golden file after an intended template change with:
    ZOO_UPDATE_GOLDEN=1 uv run pytest tests/release/test_card_emlearn.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from test_card_build import normalized

from mobility_model_zoo.release import card as cards
from mobility_model_zoo.release.gate import card_structure

GOLDEN = Path(__file__).resolve().parent / "fixtures/golden/edge-fixture-forest-0.1.0.README.md"


def render(env) -> str:
    return cards.render(cards.CardInput(env.reg, env.model, env.version))


def test_forest_card_matches_golden_file(mcu_forest_env):
    card = normalized(render(mcu_forest_env), mcu_forest_env)
    if os.environ.get("ZOO_UPDATE_GOLDEN"):
        GOLDEN.write_text(card, encoding="utf-8")
    assert card == GOLDEN.read_text(encoding="utf-8")


def test_examples_show_frames_and_alarms(mcu_forest_env):
    section = cards.sections(cards.split_card(render(mcu_forest_env))[1])["Examples"]
    assert "CAN frames in bus order" in section and "| Time (µs) | ID | DLC | Data |" in section
    assert re.search(r"raises \d+ alarm", section)
    assert "int8 values" not in section


def test_device_usage_names_emlearn(mcu_forest_env):
    section = cards.sections(cards.split_card(render(mcu_forest_env))[1])["How to run it"]
    assert "emlearn" in section and "picket_forest_process" in section


def test_forest_card_structure(mcu_forest_env):
    assert card_structure(render(mcu_forest_env), "ground_truth") == []
