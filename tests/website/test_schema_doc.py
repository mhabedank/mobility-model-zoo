"""The output format documentation comes from the schema (research R7; check B5)."""

from __future__ import annotations

import pytest

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.site.schema_doc import output_format

PATHS = [
    "output_format_version",
    "relevant",
    "relevance_probability",
    "dimensions",
    "items",
    "items[].kind",
    "items[].quote",
    "items[].start",
    "items[].end",
    "items[].score",
    "items[].actor_type",
    "items[].evidence_type",
    "items[].evidence_scope",
]


def test_rows_follow_the_schema(site_env):
    fmt = output_format(site_env.reg, "jtbd-span-v1")
    assert [r["path"] for r in fmt["rows"]] == PATHS
    rows = {r["path"]: r for r in fmt["rows"]}
    assert rows["items[].actor_type"]["enum"] == [
        "individual",
        "worker",
        "organization",
        "public_sector",
        "society",
    ]
    assert rows["items[].start"]["required"] and not rows["items[].actor_type"]["required"]
    assert all(r["meaning"] for r in fmt["rows"])
    assert fmt["produced_by"] == [{"name": "scout-large", "version": "0.1.2"}]


def test_schema_field_without_meaning_is_b5(site_env):
    site_env.edit_yaml("zoo/formats/jtbd-span-v1.yaml", lambda d: d["fields"].pop("items[].score"))
    with pytest.raises(GateFailed, match="B5 .*items\\[\\].score has no meaning"):
        output_format(site_env.reg, "jtbd-span-v1")


def test_meaning_without_schema_field_is_b5(site_env):
    site_env.edit_yaml(
        "zoo/formats/jtbd-span-v1.yaml",
        lambda d: d["fields"].update({"items[].actor": {"meaning": "x"}}),
    )
    with pytest.raises(GateFailed, match="B5 .*items\\[\\].actor, which is not in the schema"):
        output_format(site_env.reg, "jtbd-span-v1")
