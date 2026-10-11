"""Pair, specificity and B-cubed metrics, agreement and candidate scores (feature 009, T023)."""

from __future__ import annotations

import math

import pytest

from mobility_model_zoo.productdev.jtbd import metrics as jtbd_metrics
from mobility_model_zoo.productdev.jtbd.cluster import metrics as m

BOOT = {"resamples": 200, "seed": 1}


def test_pair_prf_hand_case():
    gold = {"p1": True, "p2": True, "p3": False, "p4": False}
    pred = {"p1": True, "p2": False, "p3": True, "p4": False}
    out = m.pair_prf(pred, gold)
    assert (out["precision"], out["recall"], out["f1"]) == (0.5, 0.5, 0.5)


def test_bcubed_worked_example():
    # gold {a,b,c} {d,e}; predicted {a,b} {c,d,e}: per-item precision 1,1,1/3,2/3,2/3 and recall
    # 2/3,2/3,1/3,1,1 (Amigo et al. 2009, B-cubed definition)
    gold = {"a": 1, "b": 1, "c": 1, "d": 2, "e": 2}
    pred = {"a": "x", "b": "x", "c": "y", "d": "y", "e": "y"}
    p, r, f = m.bcubed(pred, gold)
    assert p == pytest.approx(11 / 15) and r == pytest.approx(11 / 15) and f == pytest.approx(11 / 15)


def test_bcubed_extremes():
    gold = {"a": 1, "b": 1, "c": 2, "d": 3}
    one = {i: 0 for i in gold}
    p, r, _ = m.bcubed(one, gold)
    assert r == 1.0 and p == pytest.approx((2 / 4 * 2 + 1 / 4 * 2) / 4)
    singletons = {i: i for i in gold}
    p, r, _ = m.bcubed(singletons, gold)
    assert p == 1.0 and r == pytest.approx((1 / 2 * 2 + 1 + 1) / 4)
    assert m.bcubed(gold, gold) == (1.0, 1.0, 1.0)


def test_specificity_needs_the_same_direction():
    gold = {"p1": "a_more_specific", "p2": "b_more_specific", "p3": "different"}
    pred = {"p1": "a_more_specific", "p2": "a_more_specific", "p3": "b_more_specific"}
    out = m.specificity_prf(pred, gold)
    assert (out["precision"], out["recall"]) == (round(1 / 3, 4), 0.5)


def test_agreement_reuses_the_jtbd_kappa():
    assert m.kappa is jtbd_metrics.kappa


def test_agreement_per_level():
    a = {"p1": "same", "p2": "different", "p3": "a_more_specific", "p4": "same"}
    b = {"p1": "same", "p2": "different", "p3": "a_more_specific", "p4": "different"}
    sets = {"s1": {"clusters": [{"cluster_id": "c1", "members": ["x", "y"]},
                                {"cluster_id": "c2", "members": ["z"]}], "coarse": None}}
    out = m.agreement(a, b, sets, sets, BOOT)
    assert out["duplicate"]["n"] == 4 and out["duplicate"]["contested"] == 1
    assert out["specificity"]["n"] == 2 and out["specificity"]["value"] == 1.0
    assert out["cluster_level_1"]["value"] == 1.0 and out["cluster_level_1"]["n"] == 1
    assert out["cluster_level_2"]["n"] == 0 and out["cluster_level_2"]["value"] is None


def test_consensus_and_contested():
    agreed, contested = m.consensus({"p1": "same", "p2": "same"}, {"p1": "same", "p2": "different"},
                                    ("ref-a", "ref-b"))
    assert agreed == [{"pair_id": "p1", "label": "same"}]
    assert contested == [{"pair_id": "p2", "labels": {"ref-a": "same", "ref-b": "different"}}]


def test_candidate_labels_follow_groups_and_parents():
    pairs = [{"pair_id": "p1", "a": "i1", "b": "i2"}, {"pair_id": "p2", "a": "i1", "b": "i3"},
             {"pair_id": "p3", "a": "i3", "b": "i1"}, {"pair_id": "p4", "a": "i1", "b": "i4"}]
    group_of = {"i1": "g1", "i2": "g1", "i3": "g2", "i4": "g3"}
    labels = m.candidate_pair_labels(pairs, group_of, {"g1": "g2"})
    assert labels == {"p1": "same", "p2": "a_more_specific", "p3": "b_more_specific",
                      "p4": "different"}


def test_contested_pairs_are_not_scored_and_ratio_is_per_level():
    pairs = {f"p{n}": {"pair_id": f"p{n}", "a": f"i{n}a", "b": f"i{n}b"} for n in range(4)}
    consensus = [{"pair_id": "p0", "label": "same"}, {"pair_id": "p1", "label": "different"},
                 {"pair_id": "p2", "label": "same"}]
    contested = [{"pair_id": "p3", "labels": {}}]
    predicted = {"p0": "same", "p1": "different", "p2": "different", "p3": "same"}
    group_of = {"i0a": "g", "i0b": "g", "i1a": "h", "i1b": "k", "i2a": "m", "i2b": "n",
                "i3a": "z", "i3b": "z"}
    out = m.score_candidate(predicted, consensus, contested, pairs, group_of, {}, None, {},
                            {"duplicate": {"value": 0.8}, "specificity": {"value": 0.5}})
    dup = out["levels"]["duplicate"]
    assert out["consensus_pairs"] == 3 and out["contested_pairs"] == 1
    assert (dup["precision"], dup["recall"]) == (1.0, 0.5)
    assert dup["ratio_to_reference"] == round(dup["kappa"] / 0.8, 4)
    assert "cluster_level_1" not in out["levels"]


def test_nan_is_reported_as_none():
    assert m._r(math.nan) is None
