"""The character ranges B6 allows are drawn by the shipped font (research R7)."""

from __future__ import annotations

import unicodedata
from importlib import resources

import pytest

from mobility_model_zoo.site import og

ttLib = pytest.importorskip("fontTools.ttLib")
pytest.importorskip("brotli")  # woff2 needs it


def test_figtree_covers_the_allowed_ranges():
    path = resources.files("mobility_model_zoo.site").joinpath(
        "static/fonts/Figtree-variable-latin.woff2"
    )
    with resources.as_file(path) as font_file:
        cmap = ttLib.TTFont(font_file).getBestCmap()
    missing = [
        f"U+{cp:04X}"
        for lo, hi in og.LATIN_RANGES
        for cp in range(lo, hi + 1)
        if unicodedata.category(chr(cp))[0] != "C" and cp not in cmap
    ]
    assert missing == []
