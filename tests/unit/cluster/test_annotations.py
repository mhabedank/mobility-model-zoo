"""Statements and assignments by node id (feature 009, T053)."""

from __future__ import annotations

import pytest

from mobility_model_zoo.productdev.jtbd.cluster import annotation as annotations
from mobility_model_zoo.productdev.jtbd.errors import UsageError


def result():
    return {"groups": [{"group_id": "dg-000001", "statement": None, "assignments": []}],
            "clusters": [{"cluster_id": "cl-000001", "statement": None, "assignments": []}]}


def test_statements_and_several_schemes_are_merged_by_node_id(tmp_path):
    annotations.append(tmp_path, {"node": "cl-000001", "statement": {
        "text": "Commuters need reliable trains", "by": "person", "at": "2026-10-11"}})
    annotations.append(tmp_path, {"node": "cl-000001", "assignments": [
        {"scheme": "job-map-step", "value": "execute", "origin": "person"},
        {"scheme": "persona", "value": "commuter", "origin": "model:persona-v1"}]})
    annotations.append(tmp_path, {"node": "cl-000001", "assignments": [
        {"scheme": "job-map-step", "value": "monitor", "origin": "person"}]})
    res = result()
    assert annotations.merge(res, annotations.load(tmp_path)) == []
    cluster = res["clusters"][0]
    assert cluster["statement"]["text"] == "Commuters need reliable trains"
    assert cluster["assignments"] == [
        {"scheme": "job-map-step", "value": "monitor", "origin": "person"},
        {"scheme": "persona", "value": "commuter", "origin": "model:persona-v1"}]
    assert res["groups"][0]["statement"] is None  # never written without an annotation


def test_annotations_on_a_removed_id_are_orphaned(tmp_path):
    annotations.append(tmp_path, {"node": "dg-000009", "assignments": [
        {"scheme": "persona", "value": "parent", "origin": "person"}]})
    assert annotations.merge(result(), annotations.load(tmp_path)) == ["dg-000009"]


@pytest.mark.parametrize("line", [
    {"node": "x-1", "assignments": [{"scheme": "s", "value": "v", "origin": "person"}]},
    {"node": "dg-000001"},
    {"node": "dg-000001", "statement": {"text": "t", "by": "someone", "at": "2026-10-11"}},
    {"node": "dg-000001", "statement": {"text": "t", "by": "person", "at": "11.10.2026"}},
    {"node": "dg-000001", "assignments": [{"scheme": "s", "value": "v", "origin": "bot"}]},
])
def test_invalid_lines_are_refused(tmp_path, line):
    with pytest.raises(UsageError):
        annotations.append(tmp_path, line)
