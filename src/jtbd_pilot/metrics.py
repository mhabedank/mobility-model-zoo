"""Agreement statistics (FR-023, FR-024, FR-008, research.md R5).

- relevance, kind, actor type, evidence scope: Cohen's kappa
- evidence type: quadratic-weighted kappa (linear also reported)
- item existence: F1
- 95% bootstrap CIs, resampling by chunk
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Any

import numpy as np
from sklearn.metrics import cohen_kappa_score

from jtbd_pilot.config import Settings
from jtbd_pilot.consensus import load_consensus
from jtbd_pilot.corpus.store import chunk_map
from jtbd_pilot.jsonio import write_json
from jtbd_pilot.matching import match_items
from jtbd_pilot.runs import load_outputs
from jtbd_pilot.schema import (
    ACTOR_TYPES,
    EVIDENCE_ORDER,
    EVIDENCE_SCOPES,
    KINDS,
    evidence_rank,
)

DIMENSIONS = (
    "relevance", "item_matching", "kind", "actor_type", "evidence_type", "evidence_scope"
)
CATEGORY_LABELS = {
    "kind": list(KINDS),
    "actor_type": list(ACTOR_TYPES),
    "evidence_scope": list(EVIDENCE_SCOPES),
}


# ---- core statistics ----------------------------------------------------------------------
def kappa(a: list, b: list, labels: list | None = None, weights: str | None = None) -> float:
    """Cohen's kappa. Perfect agreement counts as 1.0 even when only one label occurs."""
    if not a:
        return math.nan
    if all(x == y for x, y in zip(a, b, strict=True)):
        return 1.0
    value = cohen_kappa_score(a, b, labels=labels, weights=weights)
    return float(value)


def f1(tp: float, fp: float, fn: float) -> float:
    denom = 2 * tp + fp + fn
    return (2 * tp / denom) if denom else math.nan


# Units: a list of (chunk_id, payload). Statistic functions take the payload list.
Units = list[tuple[str, Any]]


def kappa_stat(labels: list | None = None, weights: str | None = None) -> Callable[[list], float]:
    def stat(payloads: list) -> float:
        return kappa([p[0] for p in payloads], [p[1] for p in payloads], labels, weights)
    return stat


def f1_stat(payloads: list) -> float:
    tp = sum(p[0] for p in payloads)
    return f1(tp, sum(p[1] for p in payloads), sum(p[2] for p in payloads))


def bootstrap_ci(units: Units, stat: Callable[[list], float], resamples: int, seed: int
                 ) -> tuple[float, float]:
    by_chunk: dict[str, list] = defaultdict(list)
    for chunk_id, payload in units:
        by_chunk[chunk_id].append(payload)
    chunk_ids = sorted(by_chunk)
    if not chunk_ids or resamples <= 0:
        return (math.nan, math.nan)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(resamples):
        picks = rng.integers(0, len(chunk_ids), len(chunk_ids))
        sample = [p for i in picks for p in by_chunk[chunk_ids[i]]]
        value = stat(sample)
        if not math.isnan(value):
            values.append(value)
    if not values:
        return (math.nan, math.nan)
    return (float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5)))


def summarize(units: Units, stat: Callable[[list], float], metric: str, settings: Settings,
              unit_count: int | None = None) -> dict[str, Any]:
    score = stat([p for _, p in units])
    low, high = bootstrap_ci(units, stat, int(settings.pilot.get("bootstrap_resamples", 1000)),
                             int(settings.pilot.get("bootstrap_seed", 0)))
    n = unit_count if unit_count is not None else len(units)
    return {
        "metric": metric,
        "score": _r(score),
        "n": n,
        "ci_low": _r(low),
        "ci_high": _r(high),
        "underpowered": n < int(settings.pilot.get("underpowered_min_units", 30)),
    }


def _r(x: float) -> float | None:
    return None if x is None or math.isnan(x) else round(float(x), 6)


def composite(scores: Iterable[float | None]) -> float | None:
    values = [s for s in scores if s is not None]
    return round(sum(values) / len(values), 6) if values else None


# ---- reference agreement ----------------------------------------------------------------------
def reference_units(settings: Settings, run_a: str, run_b: str, chunk_ids: list[str]
                    ) -> dict[str, Units]:
    out_a, out_b = load_outputs(settings, run_a), load_outputs(settings, run_b)
    min_iou = float(settings.pilot.get("min_iou", 0.3))
    units: dict[str, Units] = {d: [] for d in DIMENSIONS}
    units["evidence_type_linear"] = []
    for chunk_id in chunk_ids:
        a, b = out_a[chunk_id], out_b[chunk_id]
        units["relevance"].append((chunk_id, (a.relevant, b.relevant)))
        tp = fp = fn = 0
        for m in match_items(a.items, b.items, min_iou):
            if m.a and m.b:
                tp += 1
                for dim in ("kind", "actor_type", "evidence_scope"):
                    units[dim].append((chunk_id, (getattr(m.a, dim), getattr(m.b, dim))))
                ranks = (evidence_rank(m.a.evidence_type), evidence_rank(m.b.evidence_type))
                units["evidence_type"].append((chunk_id, ranks))
            elif m.a:
                fp += 1
            else:
                fn += 1
        units["item_matching"].append((chunk_id, (tp, fp, fn)))
    return units


EVIDENCE_LABELS = list(range(len(EVIDENCE_ORDER)))


def dimension_stats(units: dict[str, Units], settings: Settings) -> dict[str, Any]:
    out = {
        "relevance": summarize(units["relevance"], kappa_stat([False, True]), "kappa", settings),
        "item_matching": summarize(
            units["item_matching"], f1_stat, "f1", settings,
            unit_count=sum(p[0] + p[1] + p[2] for _, p in units["item_matching"]),
        ),
    }
    for dim, labels in CATEGORY_LABELS.items():
        out[dim] = summarize(units[dim], kappa_stat(labels), "kappa", settings)
    out["evidence_type"] = summarize(
        units["evidence_type"], kappa_stat(EVIDENCE_LABELS, "quadratic"),
        "quadratic_weighted_kappa", settings,
    )
    out["evidence_type"]["linear"] = summarize(
        units["evidence_type"], kappa_stat(EVIDENCE_LABELS, "linear"), "linear_weighted_kappa",
        settings,
    )
    return {d: out[d] for d in DIMENSIONS}


def consensus_unit_stats(consensus: list[dict], contested: list[dict]) -> dict[str, float | None]:
    """Frontier-vs-frontier agreement restricted to consensus units (FR-031 ratio a)."""
    rel = [c for c in consensus if c["level"] == "relevance"]
    items = [c for c in consensus if c["level"] == "item"]
    scores: dict[str, float | None] = {
        "relevance": 1.0 if rel else None,
        "item_matching": 1.0 if items else None,
    }
    for dim in ("kind", "actor_type", "evidence_type", "evidence_scope"):
        scores[dim] = 1.0 if any(dim in c["values"] for c in items) else None
    return scores


def evidence_levels(consensus: list[dict], min_units: int) -> dict[str, Any]:
    counts = {level: 0 for level in EVIDENCE_ORDER}
    for c in consensus:
        if c["level"] == "item" and "evidence_type" in c["values"]:
            counts[c["values"]["evidence_type"]] += 1
    high = counts["observation"] + counts["measurement"]
    return {
        "counts": counts,
        "observation_plus_measurement": high,
        "underpowered_levels": ["observation", "measurement"] if high < min_units else [],
    }


def compute_agreement(settings: Settings, split: str = "main") -> dict[str, Any]:
    consensus, contested, meta = load_consensus(settings, split)
    if split == "main":
        from jtbd_pilot.freeze import verify_benchmark_frozen

        manifest = verify_benchmark_frozen(settings)
        version = manifest["version"]
    else:
        version = settings.active_version
    run_a, run_b = meta["reference_runs"]
    units = reference_units(settings, run_a, run_b, meta["chunks"])
    dims = dimension_stats(units, settings)
    chunks = chunk_map(settings, split)

    breakdowns: dict[str, dict[str, Any]] = {}
    groupings = {
        "language": lambda c: c.language,
        "source_type": lambda c: c.source_type,
        "region": lambda c: "non_EU" if c.region == "non_EU" else "EU",
    }
    for name, key_fn in groupings.items():
        groups: dict[str, list[str]] = defaultdict(list)
        for chunk_id in meta["chunks"]:
            groups[key_fn(chunks[chunk_id])].append(chunk_id)
        breakdowns[name] = {}
        for group, ids in sorted(groups.items()):
            idset = set(ids)
            sub = {d: [u for u in us if u[0] in idset] for d, us in units.items()}
            stats = dimension_stats(sub, settings)
            breakdowns[name][group] = {d: {"score": s["score"], "n": s["n"]}
                                       for d, s in stats.items()}

    min_units = int(settings.pilot.get("underpowered_min_units", 30))
    consensus_units = consensus_unit_stats(consensus, contested)
    result = {
        "benchmark_version": version,
        "split": split,
        "reference_runs": [run_a, run_b],
        "chunks": len(meta["chunks"]),
        "excluded_chunks": meta["excluded_chunks"],
        "invalid_quotes": meta["invalid_quotes"],
        "dimensions": dims,
        "composite_all_units": composite(d["score"] for d in dims.values()),
        "consensus_unit_scores": consensus_units,
        "composite_consensus_units": composite(consensus_units.values()),
        "breakdowns": breakdowns,
        "evidence_levels": evidence_levels(consensus, min_units),
        "contested_count": len(contested),
        "wording": "agreement between frontier reference models; not a comparison against "
                   "human ground truth",
    }
    write_json(settings.analysis_dir / f"agreement{'' if split == 'main' else '-' + split}.json",
               result)
    return result
