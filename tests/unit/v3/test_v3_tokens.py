"""Unicode word tokens and token IoU (feature 025, T013, research R5)."""

import pytest

from mobility_model_zoo.productdev.jtbd.v3 import tokens as tk


def test_tokens_have_offsets_and_handle_german_and_digits():
    text = "Straße, Übergänge: Zug um 7:12 – double-park!"
    toks = tk.tokenize(text)
    assert [text[s:e] for s, e in toks] == [
        "Straße",
        "Übergänge",
        "Zug",
        "um",
        "7",
        "12",
        "double",
        "park",
    ]


def test_token_set_of_a_span_counts_partial_overlap():
    text = "Der Bus kommt nie."
    toks = tk.tokenize(text)
    assert tk.token_set(toks, (0, 7)) == frozenset({0, 1})  # "Der Bus"
    assert tk.token_set(toks, (5, 9)) == frozenset({1, 2})  # "us k" touches Bus and kommt
    assert tk.token_set(toks, (17, 18)) == frozenset()  # the full stop only


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ({0, 1, 2, 3}, {0, 1, 2, 3}, 1.0),
        ({0, 1, 2, 3}, {2, 3, 4, 5}, 2 / 6),
        ({0, 1}, {2, 3}, 0.0),
        (set(), set(), 0.0),
    ],
)
def test_iou(a, b, expected):
    assert tk.iou(frozenset(a), frozenset(b)) == pytest.approx(expected)


def test_span_iou_uses_tokens_not_characters():
    text = "Der Stau kostet mich jeden Morgen zwanzig Minuten"
    full = (0, len(text))
    shorter = (0, text.index(" zwanzig"))  # 6 of 8 tokens
    assert tk.span_iou(text, full, shorter) == pytest.approx(6 / 8)
