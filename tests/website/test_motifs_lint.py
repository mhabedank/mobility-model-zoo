"""The motif grammar (feature 016, FR-019; check M2)."""

from __future__ import annotations

import pytest

from mobility_model_zoo.site import motifs

GOOD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">'
    '<g transform="translate(10,0) skewX(-8)" stroke-linecap="square" fill="none"'
    ' stroke="var(--border-strong)" stroke-width="8">'
    '<path d="M16 48H80"/><path d="M48 20V76" stroke="var(--mark)" stroke-width="12"/>'
    '<path d="M14 20V76" stroke="var(--text)" stroke-width="4.5"/></g></svg>'
)


def write(tmp_path, text: str):
    p = tmp_path / "x.svg"
    p.write_text(text, encoding="utf-8")
    return p


def test_a_motif_in_the_grammar_passes(tmp_path):
    assert motifs.lint(write(tmp_path, GOOD)) == []


def test_every_shipped_motif_passes():
    assert motifs.lint_all() == []


@pytest.mark.parametrize(
    ("change", "word"),
    [
        (lambda s: s.replace('viewBox="0 0 96 96"', 'viewBox="0 0 100 100"'), "viewBox"),
        (lambda s: s.replace("skewX(-8)", "skewX(-12)"), "skewX"),
        (lambda s: s.replace('stroke-linecap="square"', 'stroke-linecap="round"'), "cut-capped"),
        (lambda s: s.replace('stroke-width="8"', 'stroke-width="7"'), "stroke-width 7"),
        (lambda s: s.replace("var(--text)", "#ff0000"), "colour"),
        (lambda s: s.replace("var(--mark)", "var(--text)"), "accent"),
        (lambda s: s.replace("</g>", '<text x="1" y="1">a</text></g>'), "<text"),
        (lambda s: s.replace("</g>", "<!-- " + "x" * 1600 + " --></g>"), "bytes"),
    ],
)
def test_each_broken_rule_is_named(tmp_path, change, word):
    findings = motifs.lint(write(tmp_path, change(GOOD)))
    assert findings and any(word in f for f in findings), findings
