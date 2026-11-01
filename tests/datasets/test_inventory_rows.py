"""Entities and hashes of the data overview (feature 017 T007-T009, data-model.md)."""

import hashlib
import json
from pathlib import Path

import pytest

from mobility_model_zoo.datasets.inventory.hashes import (
    canonical_yaml_hash,
    dataset_hash,
    manifest_hash,
    sha256_text,
)
from mobility_model_zoo.datasets.inventory.rows import (
    HistoryEvent,
    InventoryRow,
    check_unique,
)

ROOT = Path(__file__).resolve().parents[2]


def row(**kw):
    base = dict(kind="benchmark", topic="t", id="x", version="x-v1", status="frozen", source="s")
    return InventoryRow(**{**base, **kw})


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "model"),
        ("status", "gone"),
        ("availability", "maybe"),
        ("integrity", "fine"),
        ("permitted_use", "anything"),
    ],
)
def test_enums_are_enforced(field, value):
    with pytest.raises(ValueError):
        row(**{field: value})


def test_counts_are_not_negative():
    with pytest.raises(ValueError):
        row(counts={"captures": -1})


def test_key_name_and_dict():
    r = row(counts={"captures": 3})
    assert r.key == ("benchmark", "x", "x-v1")
    assert r.name == "x@x-v1"
    assert r.to_dict()["counts"] == {"captures": 3}


def test_rows_are_unique():
    with pytest.raises(ValueError, match="duplicate"):
        check_unique([row(), row()])


def test_history_event_kinds():
    with pytest.raises(ValueError):
        HistoryEvent("2026-10-01", None, "s", "deleted")


def test_dataset_hash_is_order_independent_and_uses_checksums():
    files = [{"name": "b", "sha256": "bb"}, {"name": "a", "sha256": "aa"}]
    assert dataset_hash({"files": files}) == dataset_hash({"files": list(reversed(files))})
    assert dataset_hash({"files": files}) == sha256_text("a:aa\nb:bb")
    member = {"files": [{"name": "z.zip", "checksum": "md5:1"}]}
    assert dataset_hash(member) == sha256_text("z.zip:md5:1")


def test_manifest_hash_matches_recorded_based_on():
    """The overview names the same version as `based_on.manifest_sha256` (can-ids-v2 -> v1)."""
    bench = ROOT / "topics" / "security" / "benchmarks"
    v1 = json.loads((bench / "can-ids-v1" / "manifest.json").read_text())
    v2 = json.loads((bench / "can-ids-v2" / "manifest.json").read_text())
    assert manifest_hash(v1) == v2["based_on"]["manifest_sha256"]
    assert manifest_hash({"b": 1, "a": 2}) == hashlib.sha256(b'{"a": 2, "b": 1}').hexdigest()


def test_canonical_yaml_hash_ignores_key_order(tmp_path):
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_text("x: 1\ny: 2\n")
    b.write_text("y: 2\r\nx: 1\r\n")
    assert canonical_yaml_hash(a) == canonical_yaml_hash(b)
