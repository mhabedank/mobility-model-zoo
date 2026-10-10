"""Deduplication within kind (feature 009, T016)."""

import numpy as np
import pytest
from scipy import sparse

from mobility_model_zoo.productdev.jtbd.cluster import dedup
from mobility_model_zoo.productdev.jtbd.cluster.dedup import group_items, knn_graph


def unit(*rows):
    m = np.asarray(rows, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def angle(deg):
    r = np.radians(deg)
    return [np.cos(r), np.sin(r), 0.0]


def run(vectors, kinds, keys=None, **kw):
    params = {"k": 10, "floor": 0.0, "t_dup": 0.9, **kw}
    keys = keys or [str(i) for i in range(len(kinds))]
    return group_items(vectors, kinds, keys, **params)


def test_exact_copies_merge_before_similarity():
    v = unit([1, 0, 0], [0, 1, 0])  # orthogonal, but the same exact-copy key
    assert run(v, ["pain", "pain"], ["same", "same"]) == [[0, 1]]


def test_kinds_never_share_a_group_even_at_cosine_one():
    v = unit([1, 0, 0], [1, 0, 0], [1, 0, 0])
    assert run(v, ["pain", "job", "pain"]) == [[0, 2], [1]]


def test_exact_copy_key_does_not_cross_kinds():
    v = unit([1, 0, 0], [1, 0, 0])
    assert run(v, ["pain", "job"], ["k", "k"]) == [[0], [1]]


def test_average_linkage_does_not_chain():
    # A-B and B-C are close (cos 0.95), A-C are not (cos 0.81): average linkage keeps C apart
    # (mean distance of C to {A, B} is 0.12 > 1 - t_dup), where a threshold graph would chain
    v = unit(angle(0), angle(18), angle(36))
    groups = run(v, ["job"] * 3)
    assert len(groups) == 2
    assert sorted(len(g) for g in groups) == [1, 2]


def test_groups_of_one_are_kept():
    v = unit([1, 0, 0], [0, 1, 0], [0, 0, 1])
    assert run(v, ["gain"] * 3) == [[0], [1], [2]]


def test_output_does_not_depend_on_input_order():
    rng = np.random.default_rng(1)
    base = rng.standard_normal((20, 12))
    v = unit(*np.repeat(base, 3, axis=0) + 0.02 * rng.standard_normal((60, 12)))
    kinds = ["pain"] * 30 + ["job"] * 30
    groups = run(v, kinds)
    perm = rng.permutation(60)
    groups_p = run(v[perm], [kinds[i] for i in perm])
    as_sets = {frozenset(g) for g in groups}
    assert {frozenset(int(perm[i]) for i in g) for g in groups_p} == as_sets
    assert len(groups) == 20


def test_must_link_merges_and_refuses_cross_kind():
    v = unit([1, 0, 0], [0, 1, 0])
    assert run(v, ["pain", "pain"], must_link=[[0, 1]]) == [[0, 1]]
    with pytest.raises(ValueError, match="different kind"):
        run(v, ["pain", "job"], must_link=[[0, 1]])


def test_neighbour_graph_is_sparse_and_symmetric():
    rng = np.random.default_rng(2)
    v = unit(*rng.standard_normal((5000, 16)))
    graph = knn_graph(v, k=5, floor=-1.0, block=512)
    assert sparse.issparse(graph)
    assert graph.nnz <= 2 * 5 * 5000
    assert (graph != graph.T).nnz == 0
    assert graph.diagonal().sum() == 0


def test_no_dense_matrix_for_5000_items(monkeypatch):
    calls = []
    real = knn_graph

    def spy(vectors, k, floor, block=512):
        calls.append(block)
        return real(vectors, k, floor, block)

    monkeypatch.setattr(dedup, "knn_graph", spy)
    rng = np.random.default_rng(3)
    v = unit(*rng.standard_normal((5000, 16)))
    groups = run(v, ["pain"] * 5000, k=10, floor=0.5, t_dup=0.88)
    assert calls == [512]
    assert sum(len(g) for g in groups) == 5000
