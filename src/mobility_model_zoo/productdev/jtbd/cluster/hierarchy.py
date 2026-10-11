"""Clusters over duplicate groups (research R9, task T040).

Only top-level groups (no `dg-` parent) are clustered; a child group follows its parent. Each unit
gets the normalised mean of the vectors of all items below it. Units of every kind are clustered by
average linkage on a sparse k-nearest-neighbour graph, cut at `1 - t` for each configured level
threshold, finest first; a coarser level clusters the finer level's clusters together with the
units that stayed alone. A cluster has at least two children, so a unit that joins nothing keeps
its place one level up.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from mobility_model_zoo.productdev.jtbd.cluster.dedup import _average_linkage, _components, knn_graph


def representative(indices: list[int], vectors: np.ndarray) -> int:
    """Row with the highest mean cosine to the other rows (research R9). Rows are sorted by item id,
    so the smaller row index wins a tie."""
    if len(indices) == 1:
        return indices[0]
    sub = vectors[indices]
    sims = sub @ sub.T
    mean = (sims.sum(axis=1) - np.diag(sims)) / (len(indices) - 1)
    best = max(range(len(indices)), key=lambda j: (round(float(mean[j]), 6), -indices[j]))
    return indices[best]


def centroid(rows: list[int], vectors: np.ndarray) -> np.ndarray:
    mean = vectors[rows].mean(axis=0)
    norm = float(np.linalg.norm(mean))
    return (mean / norm if norm else mean).astype(np.float32)


def partition_units(unit_vectors: np.ndarray, *, k: int, floor: float, threshold: float
                    ) -> list[list[int]]:
    """Units grouped by average linkage cut at `1 - threshold`, in order of their first index."""
    if len(unit_vectors) == 0:
        return []
    graph = knn_graph(unit_vectors, k, min(floor, threshold))
    parts: list[list[int]] = []
    for idx in _components(graph):
        if len(idx) == 1:
            parts.append([int(idx[0])])
            continue
        sub = graph[idx][:, idx]
        parts += [sorted(int(idx[p]) for p in part)
                  for part in _average_linkage(unit_vectors[idx], sub, threshold)]
    return sorted(parts, key=min)


@dataclass
class Node:
    """A unit of the hierarchy: a top-level group (`key` its group id) or a cluster."""
    key: str
    rows: list[int]
    level: int = 0
    children: list[Node] = field(default_factory=list)


def build_levels(units: list[Node], vectors: np.ndarray, thresholds: list[float], *, k: int,
                 floor: float) -> list[Node]:
    """Clusters of all levels (level 1 = first threshold). Cluster keys stay empty; the caller
    numbers them."""
    clusters: list[Node] = []
    current = list(units)
    for level, threshold in enumerate(thresholds, start=1):
        if len(current) < 2:
            break
        vecs = np.stack([centroid(u.rows, vectors) for u in current])
        nxt = []
        for part in partition_units(vecs, k=k, floor=floor, threshold=threshold):
            if len(part) == 1:
                nxt.append(current[part[0]])
                continue
            children = [current[p] for p in part]
            node = Node("", sorted(r for c in children for r in c.rows), level, children)
            clusters.append(node)
            nxt.append(node)
        current = nxt
    return clusters
