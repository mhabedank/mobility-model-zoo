"""Clusters over duplicate groups (feature 009, T038)."""

from __future__ import annotations

from cluster_helpers import item, source_line

from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundle_lines
from mobility_model_zoo.productdev.jtbd.cluster.checks import hierarchy_checks
from mobility_model_zoo.productdev.jtbd.cluster.embed import TableEncoder
from mobility_model_zoo.productdev.jtbd.cluster.specificity import TableNLI
from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

# Two topics: commuting by train (job, pain, gain, and a more specific pain) and parking.
JOB = "Get to work on time by train"
LATE = "The train is often late"
LATE_MONDAY = "The train is always late on Monday mornings"
GAIN = "A direct train would save me twenty minutes"
PARK_JOB = "Find a parking space near the office"
PARK_PAIN = "There are never free parking spaces near work"
VECTORS = {
    JOB: [1.0, 0.0, 0.0, 0.0],
    LATE: [0.95, 0.31, 0.0, 0.0],
    LATE_MONDAY: [0.85, 0.53, 0.0, 0.0],
    GAIN: [0.9, 0.0, 0.43, 0.0],
    PARK_JOB: [0.3, 0.0, 0.0, 0.95],
    PARK_PAIN: [0.3, 0.0, 0.3, 0.9],
}
SETTINGS = {"name": "hier-test", "encoder": {"backend": "table"},
            "neighbours": {"k": 10, "candidate_floor": 0.2},
            "thresholds": {"t_dup": 0.99, "t_spec": 0.75, "t_nli": 0.8}, "levels": [0.80, 0.30]}


def run(levels=None):
    quotes = [("job", JOB), ("pain", LATE), ("pain", LATE_MONDAY), ("gain", GAIN),
              ("job", PARK_JOB), ("pain", PARK_PAIN)]
    sources = read_bundle_lines([source_line(f"s{n}", [item(kind, quote)], origin=f"https://x/{n}")
                                 for n, (kind, quote) in enumerate(quotes)], "test")
    settings = {**SETTINGS, "levels": levels if levels is not None else SETTINGS["levels"]}
    nli = TableNLI({(LATE_MONDAY, LATE): 0.95})
    return ClusterStage(settings, "0" * 64, TableEncoder(VECTORS, dim=4), None, nli).run(sources)


def by_quote(result):
    quote = {i["item_id"]: i["quote"] for i in result["items"]}
    return {quote[g["representative"]]: g for g in result["groups"]}


def cluster_of_group(result, gid):
    """The level-1 cluster above a group, through `dg-` parents."""
    nodes = {g["group_id"]: g for g in result["groups"]}
    nodes.update({c["cluster_id"]: c for c in result["clusters"]})
    current = nodes[gid].get("parent")
    while current and current.startswith("dg-"):
        current = nodes[current].get("parent")
    return current


def test_clusters_mix_kinds_and_child_groups_follow_their_parent():
    result = run()
    groups = by_quote(result)
    assert groups[LATE_MONDAY]["parent"] == groups[LATE]["group_id"]
    commute = cluster_of_group(result, groups[JOB]["group_id"])
    assert commute is not None
    for quote in (LATE, GAIN, LATE_MONDAY):
        assert cluster_of_group(result, groups[quote]["group_id"]) == commute
    cluster = next(c for c in result["clusters"] if c["cluster_id"] == commute)
    assert groups[LATE_MONDAY]["group_id"] not in cluster["children"]
    assert cluster["kinds"] == {"gain": 1, "job": 1, "pain": 2}
    assert cluster["counts"]["mentions"] == 4


def test_level_2_holds_only_level_1_clusters_or_top_level_groups():
    result = run()
    level_of = {c["cluster_id"]: c["level"] for c in result["clusters"]}
    groups = {g["group_id"]: g for g in result["groups"]}
    assert set(level_of.values()) == {1, 2}
    for c in result["clusters"]:
        for child in c["children"]:
            if child.startswith("cl-"):
                assert level_of[child] < c["level"]
            else:
                assert groups[child]["parent"] == c["cluster_id"]
                assert not any(child in g["children"] for g in groups.values())


def test_aggregates_forest_and_kind_filter():
    result = run()
    assert all(c["passed"] for c in hierarchy_checks(result)), hierarchy_checks(result)
    assert result["checks"]["passed"]
    for kind in ("job", "pain", "gain"):
        ids = [g["group_id"] for g in result["groups"] if g["kind"] == kind]
        assert len(ids) == len(set(ids))
        assert sorted(ids) == sorted({i["group_id"] for i in result["items"] if i["kind"] == kind})


def test_cluster_ids_in_order_of_their_smallest_item():
    result = run()
    order = {i["item_id"]: n for n, i in enumerate(result["items"])}
    groups = {g["group_id"]: g for g in result["groups"]}
    nodes = {**groups, **{c["cluster_id"]: c for c in result["clusters"]}}

    def first_item(nid):
        node = nodes[nid]
        own = [order[m] for m in node.get("members", [])]
        return min(own + [first_item(c) for c in node["children"]])

    keys = [(first_item(c["cluster_id"]), c["level"]) for c in result["clusters"]]
    assert keys == sorted(keys)


def test_no_levels_no_clusters():
    result = run(levels=[])
    assert result["clusters"] == [] and result["settings"]["cluster_levels_produced"] == 0


def test_broken_parent_link_is_reported():
    result = run()
    child = next(g for g in result["groups"] if (g["parent"] or "").startswith("dg-"))
    child["parent"] = None
    failed = {c["name"] for c in hierarchy_checks(result) if not c["passed"]}
    assert "parent_children_agree" in failed
