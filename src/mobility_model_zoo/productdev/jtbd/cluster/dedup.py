"""Deduplication within kind (research R7).

Exact copies and must-links are merged first. Then, per kind, a sparse k-nearest-neighbour graph
of cosine similarities is built in blocks (never a dense n x n matrix) and every connected component
is grouped by average-linkage agglomerative clustering cut at `1 - t_dup`. With a connectivity
graph, scikit-learn averages distances over connected pairs only; the graph keeps the k most similar
neighbours, so the cut still separates items that are far apart.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from sklearn.cluster import AgglomerativeClustering


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def knn_graph(vectors: np.ndarray, k: int, floor: float, block: int = 512) -> sparse.csr_matrix:
    """Symmetric sparse graph: each row keeps its k most similar other rows with cosine >= floor.
    `vectors` must be L2-normalised. Memory is O(block x n) for the similarities."""
    n = len(vectors)
    rows, cols, vals = [], [], []
    kk = min(k, n - 1)
    if kk <= 0:
        return sparse.csr_matrix((n, n), dtype=np.float32)
    for start in range(0, n, block):
        sims = vectors[start:start + block] @ vectors.T
        for r in range(sims.shape[0]):
            sims[r, start + r] = -np.inf
        top = np.argpartition(-sims, kk - 1, axis=1)[:, :kk]
        for r in range(sims.shape[0]):
            for c in top[r]:
                if sims[r, c] >= floor:
                    rows.append(start + r)
                    cols.append(int(c))
                    vals.append(float(sims[r, c]))
    graph = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n), dtype=np.float32)
    return graph.maximum(graph.T).tocsr()


def _average_linkage(vectors: np.ndarray, graph: sparse.csr_matrix, t_dup: float) -> list[list[int]]:
    n = len(vectors)
    if n == 1:
        return [[0]]
    model = AgglomerativeClustering(n_clusters=None, distance_threshold=1.0 - t_dup,
                                    metric="cosine", linkage="average", connectivity=graph)
    labels = model.fit_predict(vectors)
    groups: dict[int, list[int]] = {}
    for i, label in enumerate(labels):
        groups.setdefault(int(label), []).append(i)
    return sorted(groups.values(), key=min)


def group_items(vectors: np.ndarray, kinds: Sequence[str], exact_keys: Sequence[str], *,
                k: int, floor: float, t_dup: float,
                must_link: Iterable[Sequence[int]] = ()) -> list[list[int]]:
    """Duplicate groups as lists of row indices, each group of one kind, sorted by first index.

    Rows are expected in a fixed order (by item id) so the result does not depend on input order.
    """
    n = len(kinds)
    uf = UnionFind(n)
    first: dict[tuple[str, str], int] = {}
    for i, (kind, key) in enumerate(zip(kinds, exact_keys, strict=True)):
        j = first.setdefault((kind, key), i)
        uf.union(i, j)
    for linked in must_link:
        linked = list(linked)
        for i in linked[1:]:
            if kinds[i] != kinds[linked[0]]:
                raise ValueError("a must-link may not join items of different kind")
            uf.union(linked[0], i)

    units: dict[int, list[int]] = {}
    for i in range(n):
        units.setdefault(uf.find(i), []).append(i)

    groups: list[list[int]] = []
    for kind in sorted(set(kinds)):
        unit_roots = sorted(r for r in units if kinds[r] == kind)
        if not unit_roots:
            continue
        unit_vectors = vectors[unit_roots]
        graph = knn_graph(unit_vectors, k, floor)
        for idx in _components(graph):
            if len(idx) == 1:
                groups.append(sorted(units[unit_roots[idx[0]]]))
                continue
            sub = graph[idx][:, idx]
            for part in _average_linkage(unit_vectors[idx], sub, t_dup):
                groups.append(sorted(i for p in part for i in units[unit_roots[idx[p]]]))
    return sorted(groups, key=min)


def _components(graph: sparse.csr_matrix) -> list[np.ndarray]:
    """Connected components as sorted index arrays, in order of their smallest index."""
    _, labels = connected_components(graph, directed=False)
    order = np.argsort(labels, kind="stable")
    _, starts = np.unique(labels[order], return_index=True)
    bounds = [*starts.tolist(), len(order)]
    parts = [np.sort(order[a:b]) for a, b in zip(bounds[:-1], bounds[1:], strict=True)]
    return sorted(parts, key=lambda idx: int(idx[0]))
