"""Rules for the one-line text on preview images (feature 012, check B6, data-model.md)."""

from __future__ import annotations

import pytest

from mobility_model_zoo.site import og


def errors(text: str, from_tagline: bool = False) -> list[str]:
    return og.share_line_errors("scout-large", text, from_tagline)


def test_ninety_characters_pass_and_ninety_one_fail():
    assert errors("a" * 90) == []
    assert errors("a" * 91) == ["B6 scout-large: share line has 91 characters, at most 90"]


def test_placeholder_fails():
    assert errors("Uses {metric:performance.peak_ram_gb} of memory") == [
        "B6 scout-large: share line contains a metric placeholder"
    ]


def test_free_standing_number_fails_digits_in_names_pass():
    assert errors("Runs in 8 s") == ['B6 scout-large: share line contains the number "8"']
    assert errors("Runs on an M3 Pro and emits jtbd-span-v1") == []


@pytest.mark.parametrize("ch", ["€", "–", "’", "é", "ß"])
def test_characters_in_the_fonts_pass(ch):
    assert errors(f"Price in {ch}") == []


def test_character_outside_the_fonts_fails():
    assert errors("Text → items") == ["B6 scout-large: character U+2192 is not in the site fonts"]


def test_whitespace_is_collapsed_before_counting():
    line, from_tagline = og.share_line({"share_line": "Finds   jobs,\n pains  and gains."})
    assert (line, from_tagline) == ("Finds jobs, pains and gains.", False)


def test_tagline_is_the_fallback_and_asks_for_a_share_line():
    line, from_tagline = og.share_line({"tagline": "t" * 96})
    assert from_tagline
    assert errors(line, from_tagline) == [
        "B6 scout-large: share line has 96 characters, at most 90; add share_line to site.yaml"
    ]
    assert og.share_line({"tagline": "Short.", "share_line": "Shorter."}) == ("Shorter.", False)
