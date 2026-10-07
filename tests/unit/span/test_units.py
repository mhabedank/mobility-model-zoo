"""Sentence and clause units and token windows (T007)."""

from span_helpers import tiny_tokenizer

from mobility_model_zoo.productdev.jtbd.span.units import (
    unit_token_index,
    units,
    windows,
)


def texts(text, spans):
    return [text[a:b] for a, b in spans]


def test_units_split_sentences_and_clauses():
    text = "Der Bus fährt um 18 Uhr.  Danach nichts mehr! Warum? Wir warten; es ist kalt."
    assert texts(text, units(text)) == [
        "Der Bus fährt um 18 Uhr.", "Danach nichts mehr!", "Warum?", "Wir warten;",
        "es ist kalt."]


def test_single_line_break_is_not_an_end_but_blank_line_is():
    text = "The charger at the depot\nwas broken\n\nNext paragraph without a stop"
    assert texts(text, units(text)) == ["The charger at the depot\nwas broken",
                                        "Next paragraph without a stop"]


def test_units_trim_whitespace_and_skip_empty():
    text = "  First.   \n\n   \n\n  Second.  "
    assert texts(text, units(text)) == ["First.", "Second."]
    assert units("   ") == []


def test_windows_cover_every_token_and_offsets_map_back():
    tokenizer = tiny_tokenizer()
    text = " ".join(["Ich pendle jeden Tag 40 Kilometer zur Arbeit."] * 60)
    enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    rows = windows(tokenizer, text, max_length=64, stride=16)
    assert len(rows["input_ids"]) > 2
    assert all(len(r) == 64 for r in rows["input_ids"])
    covered = {tuple(o) for row in rows["offset_mapping"] for o in row if o[1] > o[0]}
    assert covered == {tuple(o) for o in enc["offset_mapping"]}
    for row, ids in zip(rows["offset_mapping"], rows["input_ids"], strict=True):
        assert row[0] == (0, 0) and ids[0] == tokenizer.cls_token_id
        for (s, e) in row:
            if e > s:
                assert text[s:e].strip()


def test_short_text_gives_one_window():
    tokenizer = tiny_tokenizer()
    rows = windows(tokenizer, "Der Bus.", max_length=64, stride=16)
    assert len(rows["input_ids"]) == 1
    assert sum(rows["attention_mask"][0]) == 2 + len(tokenizer("Der Bus.",
                                                               add_special_tokens=False)["input_ids"])


def test_unit_token_index_assigns_overlapping_tokens():
    spans = [(0, 10), (11, 20), (21, 30)]
    tokens = [(0, 3), (4, 10), (11, 15), (16, 20)]
    assert unit_token_index(spans, tokens) == [((0, 10), [0, 1]), ((11, 20), [2, 3])]
