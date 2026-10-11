"""Specificity relation between duplicate groups (research R8, task T039).

Candidates are same-kind group pairs whose representatives are neighbours with cosine in
`[t_spec, t_dup)`. A multilingual NLI cross-encoder judges both directions: if A entails B with
probability >= `t_nli` and B does not entail A, A is more specific than B and becomes B's child.
Both directions entailing means the groups state the same need at the same level, so no link is
made. Each group takes as parent its most similar more-general candidate (ties by group id); a
cycle is broken at its weakest edge (ties by the child's id). The relation never crosses kinds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from mobility_model_zoo.productdev.jtbd.cluster.bundle import sha256_hex
from mobility_model_zoo.productdev.jtbd.cluster.dedup import knn_graph
from mobility_model_zoo.productdev.jtbd.cluster.embed import device_for, require_pinned


class NLI(Protocol):
    model_id: str
    revision: str

    def entailment(self, premises: list[str], hypotheses: list[str]) -> np.ndarray:
        """Probability that each premise entails its hypothesis."""
        ...


class TableNLI:
    """Fixed entailment probabilities by (premise, hypothesis); unknown pairs get `default`. Used by
    tests and dry runs, so nothing is downloaded there."""

    def __init__(self, table: dict[tuple[str, str], float], default: float = 0.0,
                 model_id: str = "table-nli", revision: str = "fixture"):
        self.table = table
        self.default = default
        self.model_id = model_id
        self.revision = revision

    def entailment(self, premises: list[str], hypotheses: list[str]) -> np.ndarray:
        return np.array([self.table.get((p, h), self.default)
                         for p, h in zip(premises, hypotheses, strict=True)], dtype=np.float32)


class HFNLI:
    """`transformers` sequence-classification NLI model on CPU at a pinned revision."""

    def __init__(self, settings: dict[str, Any]):
        require_pinned(settings, "nli model")
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.threads = int(settings.get("threads", 4))
        torch.set_num_threads(self.threads)
        torch.use_deterministic_algorithms(True, warn_only=True)
        self._torch = torch
        self.model_id = settings["model_id"]
        self.revision = settings["revision"]
        self.batch_size = int(settings.get("batch_size", 32))
        self.max_length = int(settings.get("max_length", 256))
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
        self.device = device_for(settings)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_id, revision=self.revision).eval().to(self.device)
        labels = {v.lower(): int(k) for k, v in self.model.config.id2label.items()}
        if "entailment" not in labels:
            raise ValueError(f"{self.model_id} has no `entailment` label: {sorted(labels)}")
        self.entailment_index = labels["entailment"]

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> HFNLI:
        return cls(settings)

    def entailment(self, premises: list[str], hypotheses: list[str]) -> np.ndarray:
        torch = self._torch
        out = []
        with torch.inference_mode():
            for i in range(0, len(premises), self.batch_size):
                enc = self.tokenizer(premises[i:i + self.batch_size],
                                     hypotheses[i:i + self.batch_size], padding=True,
                                     truncation=True, max_length=self.max_length,
                                     return_tensors="pt")
                enc = {k: v.to(self.device) for k, v in enc.items()}
                probs = torch.softmax(self.model(**enc).logits.float(), dim=-1)
                out.append(probs[:, self.entailment_index].cpu().numpy())
        return np.concatenate(out) if out else np.zeros(0, dtype=np.float32)


class CachedNLI:
    """Entailment probabilities by (model, revision, premise, hypothesis), kept in memory and, with
    a directory, on disk; tuning runs the same pairs at many thresholds."""

    def __init__(self, nli: NLI, cache_dir: Path | str | None = None):
        self.nli = nli
        self.model_id, self.revision = nli.model_id, nli.revision
        self.probs: dict[str, float] = {}
        self.path = None
        if cache_dir is not None:
            name = sha256_hex(f"{nli.model_id}@{nli.revision}")[:16]
            self.path = Path(cache_dir) / "nli" / f"{name}.json"
            if self.path.exists():
                self.probs = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def key(premise: str, hypothesis: str) -> str:
        return sha256_hex(premise + "\u241e" + hypothesis)

    def entailment(self, premises: list[str], hypotheses: list[str]) -> np.ndarray:
        keys = [self.key(p, h) for p, h in zip(premises, hypotheses, strict=True)]
        todo = {k: (p, h) for k, p, h in zip(keys, premises, hypotheses, strict=True)
                if k not in self.probs}
        if todo:
            pairs = list(todo.values())
            new = self.nli.entailment([p for p, _ in pairs], [h for _, h in pairs])
            self.probs.update({k: round(float(v), 6) for k, v in zip(todo, new, strict=True)})
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.probs, sort_keys=True), encoding="utf-8")
        return np.array([self.probs[k] for k in keys], dtype=np.float32)


def candidate_pairs(kinds: list[str], vectors: np.ndarray, *, k: int, t_spec: float, t_dup: float
                    ) -> list[tuple[int, int, float]]:
    """Same-kind neighbour pairs (i < j) of group representatives with cosine in [t_spec, t_dup)."""
    pairs = []
    for kind in sorted(set(kinds)):
        idx = [n for n, kd in enumerate(kinds) if kd == kind]
        if len(idx) < 2:
            continue
        graph = knn_graph(vectors[idx], k, t_spec).tocoo()
        for r, c, v in zip(graph.row, graph.col, graph.data, strict=True):
            if r < c and t_spec <= v < t_dup:
                pairs.append((idx[r], idx[c], float(v)))
    return sorted(pairs)


def specific_edges(pairs: list[tuple[int, int, float]], quotes: list[str], nli: NLI, t_nli: float
                   ) -> list[tuple[int, int, float]]:
    """Directed edges (child, parent, similarity): the child entails the parent, not vice versa."""
    if not pairs:
        return []
    premises = [quotes[a] for a, b, _ in pairs] + [quotes[b] for a, b, _ in pairs]
    hypotheses = [quotes[b] for a, b, _ in pairs] + [quotes[a] for a, b, _ in pairs]
    probs = nli.entailment(premises, hypotheses)
    n = len(pairs)
    edges = []
    for m, (a, b, sim) in enumerate(pairs):
        a_entails_b, b_entails_a = probs[m] >= t_nli, probs[n + m] >= t_nli
        if a_entails_b and not b_entails_a:
            edges.append((a, b, sim))
        elif b_entails_a and not a_entails_b:
            edges.append((b, a, sim))
    return edges


def choose_parents(edges: list[tuple[int, int, float]], ids: list[str]) -> dict[int, int]:
    """One parent per child: the most similar more-general candidate, ties by the parent's id;
    then cycles are broken by dropping their weakest edge, ties by the child's id."""
    best: dict[int, tuple[tuple[float, str], int, float]] = {}
    for child, parent, sim in edges:
        rank = (-round(sim, 6), ids[parent])
        if child not in best or rank < best[child][0]:
            best[child] = (rank, parent, sim)
    parent_of = {c: p for c, (_, p, _) in best.items()}
    weight = {c: s for c, (_, _, s) in best.items()}
    while True:
        cycle = _find_cycle(parent_of)
        if not cycle:
            return parent_of
        weakest = min(cycle, key=lambda c: (round(weight[c], 6), ids[c]))
        del parent_of[weakest]


def _find_cycle(parent_of: dict[int, int]) -> list[int]:
    """Children on one cycle of the parent map (each node has at most one parent), or []."""
    state: dict[int, int] = {}  # 1 = on the current path, 2 = done
    for start in sorted(parent_of):
        path, node = [], start
        while node in parent_of and state.get(node) is None:
            state[node] = 1
            path.append(node)
            node = parent_of[node]
        if state.get(node) == 1:
            return path[path.index(node):]
        for p in path:
            state[p] = 2
    return []


def specificity_links(kinds: list[str], ids: list[str], quotes: list[str], vectors: np.ndarray,
                      nli: NLI, *, k: int, t_spec: float, t_dup: float, t_nli: float
                      ) -> dict[int, int]:
    """Child row -> parent row over groups (rows in group id order)."""
    pairs = candidate_pairs(kinds, vectors, k=k, t_spec=t_spec, t_dup=t_dup)
    return choose_parents(specific_edges(pairs, quotes, nli, t_nli), ids)
