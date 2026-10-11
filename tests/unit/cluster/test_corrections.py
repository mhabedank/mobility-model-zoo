"""Human corrections (feature 009, T046)."""

from __future__ import annotations

import numpy as np
import pytest

from mobility_model_zoo.productdev.jtbd.cluster import corrections
from mobility_model_zoo.productdev.jtbd.errors import UsageError


def it(n):
    return f"it-{n:012x}"


IDS = [it(n) for n in range(6)]
KINDS = ["pain", "pain", "pain", "pain", "job", "job"]
VECTORS = np.eye(6, dtype=np.float32)


def test_merge_split_stale_and_refused_in_file_order():
    rows = [[0], [1, 2, 3], [4], [5]]
    ops = [
        {"op": "merge", "items": [it(0), it(1)]},                  # pain + pain: applied
        {"op": "merge", "items": [it(0), it(4)]},                  # pain + job: refused
        {"op": "split", "sets": [[it(0)], [it(3)]]},              # undoes part of the merge
        {"op": "merge", "items": [it(98), it(99)]},                # items missing: stale
    ]
    groups, status, touched = corrections.apply_to_rows(ops, rows, IDS, KINDS, VECTORS)
    assert [status[n]["status"] for n in range(4)] == ["applied", "refused", "applied", "stale"]
    assert "kind" in status[1]["reason"]
    assert not any({0, 3} <= set(g) for g in groups)            # the cannot-link holds
    assert sorted(r for g in groups for r in g) == list(range(6))  # every item still placed
    assert {0, 3} <= touched


def test_split_assigns_the_rest_to_the_nearest_seed():
    vectors = np.array([[1, 0], [0, 1], [0.9, 0.1], [0.1, 0.9]], dtype=np.float32)
    ops = [{"op": "split", "sets": [[it(0)], [it(1)]]}]
    groups, _, _ = corrections.apply_to_rows(ops, [[0, 1, 2, 3]], IDS[:4], KINDS[:4], vectors)
    assert groups == [[0, 2], [1, 3]]


def result():
    items = [{"item_id": it(n), "group_id": f"dg-00000{n + 1}"} for n in range(4)]
    groups = [{"group_id": f"dg-00000{n + 1}", "kind": k, "members": [it(n)],
               "representative": it(n), "parent": None, "children": [], "corrected": False}
              for n, k in enumerate(["pain", "pain", "job", "gain"])]
    groups[0]["parent"] = groups[2]["parent"] = "cl-000001"
    clusters = [{"cluster_id": "cl-000001", "level": 1, "parent": None,
                 "children": ["dg-000001", "dg-000003"], "corrected": False}]
    return {"items": items, "groups": groups, "clusters": clusters}


def test_moves_respect_kinds_and_clusters():
    res = result()
    ops = [
        {"op": "move", "item": it(1), "under": it(0)},                     # pain under pain
        {"op": "move", "item": it(3), "under": it(0)},                     # gain under pain: refused
        {"op": "move", "item": it(3), "under": it(2), "into": "cluster"},  # gain into a cluster
        {"op": "move", "item": it(0), "under": it(1)},                     # would be a cycle
        {"op": "representative", "item": it(7)},                           # missing: stale
    ]
    status: dict[int, dict] = {}
    changed = corrections.apply_to_result(ops, res, status)
    assert [status[n]["status"] for n in range(5)] == [
        "applied", "refused", "applied", "refused", "stale"]
    groups = {g["group_id"]: g for g in res["groups"]}
    assert groups["dg-000002"]["parent"] == "dg-000001"
    assert groups["dg-000001"]["children"] == ["dg-000002"]
    assert groups["dg-000004"]["parent"] == "cl-000001"
    assert res["clusters"][0]["children"] == ["dg-000001", "dg-000003", "dg-000004"]
    assert changed == {"cl-000001"} and res["clusters"][0]["corrected"]
    assert groups["dg-000002"]["corrected"] and not groups["dg-000003"]["corrected"]


def test_move_to_top_level_and_representative():
    res = result()
    status: dict[int, dict] = {}
    corrections.apply_to_result([{"op": "move", "item": it(0), "under": None},
                                 {"op": "representative", "item": it(2)}], res, status)
    groups = {g["group_id"]: g for g in res["groups"]}
    assert groups["dg-000001"]["parent"] is None
    assert res["clusters"][0]["children"] == ["dg-000003"]
    assert groups["dg-000003"]["representative"] == it(2) and groups["dg-000003"]["corrected"]


def test_file_is_validated_and_appended(tmp_path):
    assert corrections.append(tmp_path, {"op": "merge", "items": [it(0), it(1)], "note": "same"}) == 0
    assert corrections.append(tmp_path, {"op": "move", "item": it(2), "under": None}) == 1
    assert [o["op"] for o in corrections.load(tmp_path)] == ["merge", "move"]
    with pytest.raises(UsageError):
        corrections.append(tmp_path, {"op": "merge", "items": [it(0)]})
    with pytest.raises(UsageError):
        corrections.append(tmp_path, {"op": "split", "sets": [[it(0)], [it(0)]]})
    (tmp_path / corrections.FILE).write_text("- op: rename\n")
    with pytest.raises(UsageError, match="operation 0"):
        corrections.load(tmp_path)
