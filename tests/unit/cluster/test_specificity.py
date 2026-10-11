"""Specificity relation between duplicate groups with a stub NLI (feature 009, T037)."""

from __future__ import annotations

import numpy as np
from cluster_helpers import item, source_line

from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundle_lines
from mobility_model_zoo.productdev.jtbd.cluster.embed import TableEncoder
from mobility_model_zoo.productdev.jtbd.cluster.specificity import (
    TableNLI,
    candidate_pairs,
    choose_parents,
    specific_edges,
)
from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

NIGHT = "Parking downtown at night is impossible"
PARKING = "Parking is hard"
WORK = "Get to work on time"
SETTINGS = {"name": "spec-test", "encoder": {"backend": "table"},
            "neighbours": {"k": 10, "candidate_floor": 0.3},
            "thresholds": {"t_dup": 0.88, "t_spec": 0.75, "t_nli": 0.8}, "levels": [0.7]}
VECTORS = {NIGHT: [0.8, 0.6, 0.0], PARKING: [1.0, 0.0, 0.0], WORK: [0.0, 0.0, 1.0]}


def unit(*rows):
    return np.array([np.asarray(r, dtype=np.float32) / np.linalg.norm(r) for r in rows])


def test_one_way_entailment_makes_a_child():
    nli = TableNLI({(NIGHT, PARKING): 0.95, (PARKING, NIGHT): 0.1})
    assert specific_edges([(0, 1, 0.8)], [NIGHT, PARKING], nli, 0.8) == [(0, 1, 0.8)]
    swapped = TableNLI({(PARKING, NIGHT): 0.95})
    assert specific_edges([(0, 1, 0.8)], [NIGHT, PARKING], swapped, 0.8) == [(1, 0, 0.8)]


def test_entailment_both_ways_gives_no_link():
    nli = TableNLI({(NIGHT, PARKING): 0.95, (PARKING, NIGHT): 0.9})
    assert specific_edges([(0, 1, 0.8)], [NIGHT, PARKING], nli, 0.8) == []


def test_candidates_never_cross_kinds_and_stay_below_t_dup():
    vectors = unit([1, 0, 0], [0.8, 0.6, 0], [0.8, 0.6, 0.001], [0.79, 0.61, 0])
    kinds = ["pain", "pain", "job", "pain"]
    pairs = candidate_pairs(kinds, vectors, k=5, t_spec=0.75, t_dup=0.88)
    assert all(kinds[a] == kinds[b] for a, b, _ in pairs)
    assert all(0.75 <= s < 0.88 for _, _, s in pairs)
    assert (0, 1) in {(a, b) for a, b, _ in pairs} and (1, 3) not in {(a, b) for a, b, _ in pairs}


def test_one_parent_the_most_similar_general_candidate_ties_by_id():
    ids = ["dg-000001", "dg-000002", "dg-000003"]
    assert choose_parents([(0, 1, 0.80), (0, 2, 0.85)], ids) == {0: 2}
    assert choose_parents([(0, 2, 0.80), (0, 1, 0.80)], ids) == {0: 1}


def test_cycle_is_broken_at_its_weakest_edge_ties_by_id():
    ids = ["dg-000001", "dg-000002", "dg-000003"]
    edges = [(0, 1, 0.85), (1, 2, 0.78), (2, 0, 0.80)]  # A -> B -> C -> A
    assert choose_parents(edges, ids) == {0: 1, 2: 0}
    tied = [(0, 1, 0.80), (1, 2, 0.80), (2, 0, 0.80)]
    assert choose_parents(tied, ids) == {1: 2, 2: 0}


def run_stage(decision=None, nli=None):
    sources = read_bundle_lines([source_line("s1", [
        item("pain", NIGHT, 0), item("pain", PARKING, 100), item("job", WORK, 200)])], "test")
    stage = ClusterStage(SETTINGS, "0" * 64, TableEncoder(VECTORS, dim=3), decision,
                         nli or TableNLI({(NIGHT, PARKING): 0.95, (PARKING, NIGHT): 0.1}))
    return stage.run(sources)


def group_by_quote(result):
    quote = {i["item_id"]: i["quote"] for i in result["items"]}
    return {quote[g["representative"]]: g for g in result["groups"]}


def test_stage_links_the_more_specific_group_under_the_general_one():
    result = run_stage()
    groups = group_by_quote(result)
    assert groups[NIGHT]["parent"] == groups[PARKING]["group_id"]
    assert groups[PARKING]["children"] == [groups[NIGHT]["group_id"]]
    assert result["settings"]["specificity_produced"] is True
    assert result["settings"]["nli"] == {"model_id": "table-nli", "revision": "fixture"}
    assert result["checks"]["passed"], [c for c in result["checks"]["results"] if not c["passed"]]


def test_no_dg_parents_when_the_decision_withholds_specificity():
    result = run_stage(decision={"specificity_produced": False, "cluster_levels_produced": 1})
    assert not any((g["parent"] or "").startswith("dg-") for g in result["groups"])
    assert result["settings"]["specificity_produced"] is False
    assert result["settings"]["nli"] is None
