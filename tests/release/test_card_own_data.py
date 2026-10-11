"""`card.own_data`: the snippet for the user's own data (feature 013)."""

from __future__ import annotations

from test_gate_rules import edit_model

from mobility_model_zoo.release import card as cards


def render(env) -> str:
    return cards.render(cards.CardInput(env.reg, env.model, env.version))


def test_own_data_is_rendered_with_repo_and_revision_filled(mcu_env):
    edit_model(
        mcu_env,
        lambda m: m["card"].update(own_data='table = load("{repo_id}", revision="{revision}")\n'),
    )
    section = cards.sections(cards.split_card(render(mcu_env))[1])["How to run it"]
    assert "### Use it on your own data" in section
    assert 'table = load("mobility-model-zoo/edge-fixture-tiny", revision="v0.1.0")' in section
    assert "{repo_id}" not in section and "{revision}" not in section


def test_no_own_data_no_heading(mcu_env):
    assert "Use it on your own data" not in render(mcu_env)


def test_run_output_is_read_back_from_a_rendered_card(mcu_env):
    card = cards.render(
        cards.CardInput(
            mcu_env.reg, mcu_env.model, mcu_env.version, how_to_run_output="3 frames\n1 alarm"
        )
    )
    assert cards.parse_card_run_output(card) == "3 frames\n1 alarm"
    assert cards.parse_card_run_output(render(mcu_env)) is None
