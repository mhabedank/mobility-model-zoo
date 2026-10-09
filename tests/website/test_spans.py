"""Quotes against their offsets (check B3) and shareable example sources (B4)."""

from __future__ import annotations

import json

import pytest
from site_fixture import MODEL, VERSION

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.site import examples
from mobility_model_zoo.site.schema_doc import output_format

TEXT = "We wait. The bus is late. We like trams."


def item(kind, quote, start):
    return {"kind": kind, "quote": quote, "start": start, "end": start + len(quote), "score": 0.9}


def test_segments_cover_the_text_in_order():
    out = {"items": [item("gain", "We like trams.", 26), item("pain", "The bus is late.", 9)]}
    segs = examples.spans(MODEL, "x.txt", TEXT, out)
    assert "".join(s["text"] for s in segs) == TEXT
    assert [s.get("kind") for s in segs if s["marked"]] == ["pain", "gain"]


def test_quote_not_at_its_offsets_is_b3():
    with pytest.raises(GateFailed, match="B3 .*does not equal"):
        examples.spans(MODEL, "x.txt", TEXT, {"items": [item("pain", "The bus is late.", 8)]})


def test_overlapping_quotes_are_b3():
    out = {"items": [item("pain", "The bus is late.", 9), item("job", "bus is late.", 13)]}
    with pytest.raises(GateFailed, match="B3 .*overlaps"):
        examples.spans(MODEL, "x.txt", TEXT, out)


def test_empty_items_render_as_a_valid_result(site_env):
    def empty(d):
        out = json.loads(d["outputs"]["03-cargo-bike.txt"])
        out.update(relevant=False, items=[])
        d["outputs"]["03-cargo-bike.txt"] = json.dumps(out)

    site_env.edit_cache(empty)
    site_env.build()
    assert "No items. An empty list is a valid result." in site_env.html(f"models/{MODEL}/index.html")


def test_non_synthetic_example_is_b4(site_env):
    site_env.edit_yaml(
        f"zoo/models/{MODEL}/examples/SOURCES.yaml",
        lambda d: d["examples"][0].update(source="forum-snapshot-17"),
    )
    schema = output_format(site_env.reg, "jtbd-span-v1")["schema"]
    with pytest.raises(GateFailed, match="B4"):
        examples.load(site_env.reg, MODEL, VERSION, schema, offline=True)


def test_viewer_only_for_span_formats():
    assert examples.is_span_format(
        {"properties": {"items": {"items": {"properties": {"quote": {}, "start": {}, "end": {}}}}}}
    )
    assert not examples.is_span_format({"properties": {"output": {"type": "array"}}})
