"""The model card of a microcontroller model (feature 005 T057, contracts/release-format.md).

Regenerate the golden file after an intended template change with:
    ZOO_UPDATE_GOLDEN=1 uv run pytest tests/release/test_card_mcu.py
"""

from __future__ import annotations

import os
from pathlib import Path

from test_card_build import normalized
from test_edge_rules import declare, source
from test_gate_rules import edit_model, edit_record

from mobility_model_zoo.release import card as cards
from mobility_model_zoo.release.gate import Gate, card_structure

GOLDEN = Path(__file__).resolve().parent / "fixtures/golden/edge-fixture-tiny-0.1.0.README.md"


def render(env) -> str:
    return cards.render(cards.CardInput(env.reg, env.model, env.version))


def test_mcu_card_matches_golden_file(mcu_env):
    gate = Gate(mcu_env.reg, mcu_env.model, mcu_env.version, hub=mcu_env.hub)
    gate.run(lambda line: None)
    card = normalized(gate.card, mcu_env)
    if os.environ.get("ZOO_UPDATE_GOLDEN"):
        GOLDEN.write_text(card, encoding="utf-8")
    assert card == GOLDEN.read_text(encoding="utf-8")


def test_front_matter_tags(mcu_env):
    front, _ = cards.split_card(render(mcu_env))
    assert {"tinyml", "microcontroller", "ESP32-S3"} <= set(front["tags"])
    assert front["language"] == []


def test_how_to_run_has_host_and_device_code(mcu_env):
    section = cards.sections(cards.split_card(render(mcu_env))[1])["How to run it"]
    assert "```python" in section and "run_model" in section
    assert "```c" in section and "mi_invoke(&mi_model_edge_fixture_tiny" in section
    assert "mobility-model-zoo/edge-fixture-tiny at v0.1.0" in section  # placeholders filled


def test_budget_and_measured_on(mcu_env):
    section = cards.sections(cards.split_card(render(mcu_env))[1])["Speed and memory"]
    assert "Budget: 16 KB RAM, 64 KB flash on ESP32-S3." in section
    assert "| Measured on |" in section
    assert "ESP32 in QEMU, 240 MHz (emulator)" in section
    assert "host simulator (simulator)" in section


def test_dataset_provenance_table(mcu_env):
    declare(mcu_env, "mimii")
    edit_model(
        mcu_env, lambda m: m.update(license="CC-BY-SA-4.0", license_exception="MIMII share-alike")
    )
    edit_record(mcu_env, lambda r: r["provenance"].update(sources=[source("mimii", "CC-BY-SA-4.0")]))
    section = cards.sections(cards.split_card(render(mcu_env))[1])["Training data provenance"]
    assert "| Dataset | Provider | License | Attribution |" in section
    assert "zenodo" in section and "CC-BY-SA-4.0" in section and "Purohit" in section
    assert "not redistributed with the model" in section


def test_mcu_card_structure(mcu_env):
    card = render(mcu_env)
    assert card_structure(card, "ground_truth") == []
    assert [line[3:] for line in card.splitlines() if line.startswith("## ")] == list(cards.SECTIONS)
