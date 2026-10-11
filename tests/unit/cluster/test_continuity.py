"""Stable ids across runs (feature 009, T045)."""

from __future__ import annotations

from mobility_model_zoo.productdev.jtbd.cluster.continuity import apply, assign


def ids(*names):
    return {f"it-{n:012x}" for n in names}


PREVIOUS = {"dg-000001": ids(1, 2), "dg-000002": ids(3), "dg-000003": ids(4, 5, 6)}


def test_unchanged_groups_keep_their_id():
    new = [ids(1, 2), ids(3), ids(4, 5, 6)]
    names, counter, changes = assign("dg", new, PREVIOUS, 3)
    assert names == ["dg-000001", "dg-000002", "dg-000003"] and counter == 3
    assert all(not v for v in changes.values())


def test_a_new_item_joining_a_group_keeps_the_id_and_a_new_group_gets_a_new_id():
    new = [ids(1, 2, 7), ids(3), ids(4, 5, 6), ids(8)]
    names, counter, changes = assign("dg", new, PREVIOUS, 3)
    assert names == ["dg-000001", "dg-000002", "dg-000003", "dg-000004"] and counter == 4
    assert changes["grown"] == ["dg-000001"] and changes["new"] == ["dg-000004"]


def test_merge_keeps_the_id_with_most_previous_members():
    new = [ids(3, 4, 5, 6), ids(1, 2)]
    names, _, changes = assign("dg", new, PREVIOUS, 3)
    assert names[0] == "dg-000003"
    assert changes["merged"] == [{"into": "dg-000003", "from": ["dg-000002"]}]


def test_merge_tie_goes_to_the_older_id():
    previous = {"dg-000001": ids(1), "dg-000002": ids(2)}
    names, _, changes = assign("dg", [ids(1, 2)], previous, 2)
    assert names == ["dg-000001"]
    assert changes["merged"] == [{"into": "dg-000001", "from": ["dg-000002"]}]


def test_split_keeps_the_id_on_the_larger_part_and_counts_on():
    new = [ids(1, 2), ids(3), ids(4, 5), ids(6)]
    names, counter, changes = assign("dg", new, PREVIOUS, 3)
    assert names == ["dg-000001", "dg-000002", "dg-000003", "dg-000004"] and counter == 4
    assert changes["split"] == [{"from": "dg-000003", "into": ["dg-000003", "dg-000004"]}]
    assert changes["shrunk"] == ["dg-000003"]


def test_counters_never_reuse_an_id():
    new = [ids(1, 2), ids(3)]  # dg-000003 removed
    names, counter, changes = assign("dg", new, PREVIOUS, 3)
    assert changes["removed"] == ["dg-000003"]
    later, counter, _ = assign("dg", [ids(1, 2), ids(3), ids(9)],
                               {"dg-000001": ids(1, 2), "dg-000002": ids(3)}, counter)
    assert later[2] == "dg-000004"


def result_with(groups):
    items = [{"item_id": i, "group_id": gid} for gid, members in groups for i in sorted(members)]
    return {"settings": {"settings_sha256": "a" * 64}, "items": items, "clusters": [],
            "groups": [{"group_id": gid, "members": sorted(m), "parent": None, "children": []}
                       for gid, m in groups]}


def test_apply_renames_the_result_and_reports_changes():
    first = result_with([("dg-000001", ids(1, 2)), ("dg-000002", ids(3))])
    state, changes = apply(first, None)
    assert changes["new"] == ["dg-000001", "dg-000002"] and not changes["settings_changed"]
    second = result_with([("dg-000001", ids(3)), ("dg-000002", ids(1, 2, 4))])  # provisional ids
    state2, changes2 = apply(second, {**state, "settings_sha256": "b" * 64})
    assert {g["group_id"]: set(g["members"]) for g in second["groups"]} == {
        "dg-000001": ids(1, 2, 4), "dg-000002": ids(3)}
    assert {i["item_id"]: i["group_id"] for i in second["items"]}[f"it-{4:012x}"] == "dg-000001"
    assert changes2["grown"] == ["dg-000001"] and changes2["settings_changed"] is True
    assert state2["counters"]["dg"] == 2
