"""Card lint (C-C1, C-C2) with the repository's card-lint.yaml."""

from pathlib import Path

import pytest
import yaml

from mobility_model_zoo.compliance.release_checks import card_lint

LINT = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "compliance/lists/card-lint.yaml").read_text()
)
SECTIONS = [
    "Intended use",
    "Out-of-scope use",
    "Limitations and risks",
    "Training data and attribution",
    "Teacher and labeling models",
    "Privacy and personal data",
]


def card(extra="", drop=None, topic_sections=()):
    body = "\n".join(
        f"## {s}\n\nText for {s}. See PRIVACY.md and COPYRIGHT_POLICY.md.\n"
        for s in [*SECTIONS, *topic_sections]
        if s != drop
    )
    return f"---\nlicense: apache-2.0\n---\n# Model\n\n{body}\n## Summary\n\n{extra}\n"


def ids(text, topic="productdev"):
    return {c for c, _, _ in card_lint(text, topic, LINT)}


def test_clean_card_passes():
    assert ids(card()) == set()


def test_missing_section():
    assert ids(card(drop="Out-of-scope use")) == {"C-C1"}


@pytest.mark.parametrize(
    "phrase",
    [
        "suitable as a safety function",
        "This model is production-ready.",
        "certified for use",
        "this model is anonymous",
        "for screening job applicants",
    ],
)
def test_forbidden_wording(phrase):
    assert ids(card(extra=phrase)) == {"C-C2"}


def test_negated_out_of_scope_line_is_allowed():
    text = card().replace("Text for Out-of-scope use.", "- Not for screening job applicants.")
    assert ids(text) == set()


def test_security_topic_needs_dual_use_and_disclaimer():
    assert ids(card(), topic="security") == {"C-C1"}
    ok = card(topic_sections=["Dual-use considerations"]) + "\nNot developed under ISO/SAE 21434.\n"
    assert ids(ok, topic="security") == set()
