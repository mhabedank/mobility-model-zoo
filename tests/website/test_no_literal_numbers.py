"""F2: numbers on the website come from release results, never from hand-written text."""

from __future__ import annotations

from pathlib import Path

from mobility_model_zoo.release.registry import Registry
from mobility_model_zoo.site import check

REPO = Path(__file__).resolve().parents[2]


def test_repository_site_texts_and_templates_have_no_literal_numbers():
    assert list(check.check_literal_numbers(Registry(REPO))) == []


def test_free_standing_numbers_are_found_but_names_are_not():
    found = check.literal_numbers(
        "takes 8.1 s, 0.72 against {metric:quality.x}; M3 Pro, jtbd-span-v1, "
        "GPT-5.4 mini, a 9,240-character text, 1,260 per minute"
    )
    assert found == ["8.1", "0.72", "1,260"]


def test_template_text_ignores_attributes_expressions_and_svg():
    text = check.template_text(
        '<p class="x" width="24">{{ 0.72 }} Step {% if 1 %}</p><svg><path d="M1 2"/></svg>'
    )
    assert check.literal_numbers(text) == []


def test_literal_number_in_site_yaml_is_f2(site_env):
    site_env.edit_yaml(
        "zoo/models/scout-large/site.yaml",
        lambda p: p["differentiators"][0].update(text="It reaches 0.72."),
    )
    found = list(check.check_literal_numbers(site_env.reg))
    assert found and found[0][0] == "F2" and "0.72" in found[0][2]
