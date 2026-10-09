"""Input bundles: validation, item ids, exact copies, independence (feature 009, T012)."""

import pytest
from cluster_helpers import BUNDLES, item, source_line, write_bundle

from mobility_model_zoo.productdev.jtbd.cluster.bundle import (
    exact_copy_key,
    independence_keys,
    item_id,
    items_from,
    normalise_quote,
    read_bundle,
    read_bundles,
)
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed


def test_item_id_is_stable_and_shaped():
    a = item_id("s1", 0, 10, "pain")
    assert a == item_id("s1", 0, 10, "pain")
    assert a.startswith("it-") and len(a) == 15
    assert a != item_id("s1", 0, 10, "job")
    assert a != item_id("s1", 0, 11, "pain")


def test_exact_copy_key_ignores_case_whitespace_and_edge_punctuation():
    assert normalise_quote("  „Der Bus  kommt\nzu spät!“ ") == "der bus kommt zu spät"
    assert exact_copy_key("pain", "The bus is late.") == exact_copy_key("pain", '"the  BUS is late"')
    assert exact_copy_key("pain", "The bus is late.") != exact_copy_key("job", "The bus is late.")
    assert exact_copy_key("pain", "The bus is late.") != exact_copy_key("pain", "The bus is early.")


def test_basic_bundle_reads():
    sources = read_bundle(BUNDLES / "basic.jsonl")
    assert len(sources) == 23
    items = items_from(sources)
    assert [i.item_id for i in items] == sorted(i.item_id for i in items)
    assert all(i.quote == i.quote for i in items)


def test_other_output_version_is_refused_with_line():
    with pytest.raises(ValidationFailed, match=r"bad_version\.jsonl:1: output format 'jtbd-span-v0'"):
        read_bundle(BUNDLES / "bad_version.jsonl")


def test_schema_violation_names_the_line(tmp_path):
    line = source_line("s1", [item("pain", "Too expensive.")])
    del line["source_class"]
    path = write_bundle(tmp_path / "b.jsonl", [source_line("s0", []), line])
    with pytest.raises(ValidationFailed, match=r"b\.jsonl:2: .*source_class"):
        read_bundle(path)


def test_invalid_span_output_is_refused(tmp_path):
    bad = item("pain", "Too expensive.")
    bad["kind"] = "wish"
    path = write_bundle(tmp_path / "b.jsonl", [source_line("s1", [bad])])
    with pytest.raises(ValidationFailed, match=r"\(output\)"):
        read_bundle(path)


def test_invalid_date_is_refused(tmp_path):
    path = write_bundle(tmp_path / "b.jsonl", [source_line("s1", [], date="09.10.2026")])
    with pytest.raises(ValidationFailed, match="date"):
        read_bundle(path)


def test_duplicate_source_ids_are_refused(tmp_path):
    path = write_bundle(tmp_path / "b.jsonl", [source_line("s1", []), source_line("s1", [])])
    with pytest.raises(ValidationFailed, match="duplicate source_id"):
        read_bundle(path)
    other = write_bundle(tmp_path / "c.jsonl", [source_line("s1", [])])
    single = write_bundle(tmp_path / "d.jsonl", [source_line("s1", [])])
    with pytest.raises(ValidationFailed, match="two bundles"):
        read_bundles([other, single])


def test_independence_keys():
    sources = read_bundle(BUNDLES / "basic.jsonl")
    keys = independence_keys(sources)
    # same text under two source ids: one key
    assert keys["s11"] == keys["s12"] == ("s11", False)
    # post and quoting reply in one thread: the thread is the key
    assert keys["s13"] == keys["s14"] == ("https://forum.example/t/9", True)
    assert keys["s05"] == ("s05", False)


def test_items_carry_date_attributes_and_keys():
    by_source = {}
    for it in items_from(read_bundle(BUNDLES / "basic.jsonl")):
        by_source.setdefault(it.source_id, []).append(it)
    assert by_source["s15"][0].date is None
    assert by_source["s01"][0].date == "2026-03-01"
    assert by_source["s01"][0].attributes == {"actor_type": "individual"}
    assert by_source["s23"][0].attributes == {}  # scout produced no attribute dimensions
    assert "s16" not in by_source  # relevant: false, no items


def test_quotes_are_copied_unchanged(tmp_path):
    quote = "  Der Bus kommt   zu spät!  "
    path = write_bundle(tmp_path / "b.jsonl", [source_line("s1", [item("pain", quote)])])
    (it,) = items_from(read_bundle(path))
    assert it.quote == quote
