"""`jtbd cluster tune`: thresholds from development data only (research R12, tasks T032, T043).

Three steps, each on the development split and each fixing its value before the next:

1. `t_dup` from 0.80 to 0.95 in steps of 0.01 on the development pairs the references agree on,
   chosen by duplicate pair F1 (ties: the higher threshold, which merges less).
2. `t_spec` (0.65-0.85, step 0.05) and `t_nli` (0.6-0.9, step 0.1), chosen by the F1 of the
   directed "more specific" relation on agreed not-same pairs (ties: the higher `t_nli`, then the
   higher `t_spec`, which link less). Skipped when the decision withholds the relation or the
   settings name no NLI model.
3. The level-1 cluster threshold (0.45-0.85, step 0.05), chosen by the mean B-cubed F1 against
   each reference's partition of the development sets (ties: the higher threshold). Skipped when
   the decision produces no cluster level; a second level is kept as configured.

The chosen values and every grid go into a new settings file; test and holdout are refused (exit 2).
"""

from __future__ import annotations

import copy
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from mobility_model_zoo.productdev.jtbd.cluster import bench
from mobility_model_zoo.productdev.jtbd.cluster.bundle import items_from
from mobility_model_zoo.productdev.jtbd.cluster.dedup import group_items
from mobility_model_zoo.productdev.jtbd.cluster.embed import EmbeddingCache, Encoder
from mobility_model_zoo.productdev.jtbd.cluster.metrics import (
    analysis_dir,
    candidate_pair_labels,
    level1_partition,
    pair_prf,
    set_bcubed,
    specificity_prf,
)
from mobility_model_zoo.productdev.jtbd.cluster.specificity import NLI, CachedNLI
from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage, load_stage_settings
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_jsonl

GRID = tuple(round(0.80 + 0.01 * i, 2) for i in range(16))
SPEC_GRID = tuple((round(0.65 + 0.05 * i, 2), round(0.6 + 0.1 * j, 1))
                  for i in range(5) for j in range(4))
CLUSTER_GRID = tuple(round(0.45 + 0.05 * i, 2) for i in range(9))


def _round(x: float | None) -> float | None:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def grid_search(vectors: np.ndarray, items, pairs: list[dict], gold: dict[str, str],
                settings: dict[str, Any], grid: tuple[float, ...] = GRID) -> list[dict[str, Any]]:
    neighbours = settings["neighbours"]
    rows = []
    gold_same = {p: g == "same" for p, g in gold.items()}
    for t_dup in grid:
        groups = group_items(vectors, [i.kind for i in items], [i.exact_copy_key for i in items],
                             k=int(neighbours["k"]), floor=float(neighbours["candidate_floor"]),
                             t_dup=t_dup)
        group_of = {items[r].item_id: str(n) for n, members in enumerate(groups) for r in members}
        predicted = candidate_pair_labels(pairs, group_of)
        scores = pair_prf({p: predicted.get(p) == "same" for p in gold}, gold_same)
        rows.append({"t_dup": t_dup, **scores})
    return rows


def choose(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [r for r in rows if r["f1"] is not None]
    if not scored:
        raise ValidationFailed("no development pair has a defined F1; label the dev split first")
    return max(scored, key=lambda r: (r["f1"], r["t_dup"]))


class _Precomputed:
    """The candidate's encoder behind the benchmark's embedding cache, so grid runs never embed
    a quote twice."""

    def __init__(self, encoder: Encoder, cache: EmbeddingCache):
        self.encoder, self.cache = encoder, cache
        self.model_id, self.revision = encoder.model_id, encoder.revision
        self.variant = getattr(encoder, "variant", "")

    def embed(self, quotes: list[str]) -> np.ndarray:
        return self.cache.get(quotes, self.encoder)


def spec_search(run, pairs: list[dict], gold: dict[str, str]) -> list[dict[str, Any]]:
    """`run(thresholds, levels)` gives a stage result; scored on agreed not-same pairs."""
    spec_gold = {p: g for p, g in gold.items() if g != "same"}
    rows = []
    for t_spec, t_nli in SPEC_GRID:
        result = run({"t_spec": t_spec, "t_nli": t_nli}, [])
        group_of = {i["item_id"]: i["group_id"] for i in result["items"]}
        parent_of = {g["group_id"]: g["parent"] for g in result["groups"]}
        predicted = candidate_pair_labels(pairs, group_of, parent_of)
        links = sum(1 for g in result["groups"] if (g["parent"] or "").startswith("dg-"))
        rows.append({"t_spec": t_spec, "t_nli": t_nli, "links": links,
                     **specificity_prf(predicted, spec_gold)})
    return rows


def choose_spec(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    scored = [r for r in rows if r["f1"] is not None]
    return max(scored, key=lambda r: (r["f1"], r["t_nli"], r["t_spec"])) if scored else None


def cluster_search(run, sets: dict[str, list[str]], reference_sets: dict[str, dict[str, dict]]
                   ) -> list[dict[str, Any]]:
    rows = []
    for threshold in CLUSTER_GRID:
        result = run({}, [threshold])
        value, n = set_bcubed(level1_partition(result), sets, reference_sets)
        rows.append({"level_1": threshold, "bcubed_f1": _round(value), "n": n,
                     "clusters": len(result["clusters"])})
    return rows


def choose_cluster(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    scored = [r for r in rows if r["bcubed_f1"] is not None]
    return max(scored, key=lambda r: (r["bcubed_f1"], r["level_1"])) if scored else None


def tracked_decision(settings: Settings) -> Path | None:
    path = bench.manifest_path(settings).parent / "decision.json"
    return path if path.exists() else None


def tune(settings: Settings, settings_path: Path, split: str, out: Path | None = None,
         encoder: Encoder | None = None, nli: NLI | None = None) -> dict[str, Any]:
    if split != "dev":
        raise UsageError("thresholds are tuned on the development split only (--split dev)")
    from mobility_model_zoo.productdev.jtbd.cluster.label import reference_runs

    stage_settings, digest = load_stage_settings(settings_path)
    rows_dev = read_jsonl(analysis_dir(settings) / "consensus-dev.jsonl")
    consensus = {r["pair_id"]: r["label"] for r in rows_dev}
    if not consensus:
        raise ValidationFailed("no development consensus; run `jtbd cluster agreement --split dev`")
    target = out or settings_path.with_name(f"{settings_path.stem}-tuned.yaml")
    decision_path = tracked_decision(settings)
    if decision_path is not None and not stage_settings.get("decision"):
        stage_settings["decision"] = os.path.relpath(decision_path, settings_path.resolve().parent)
    stage = ClusterStage.from_dict(stage_settings, digest, settings_path.resolve().parent,
                                   encoder=encoder, nli=nli)
    sources = bench.pool_sources(settings, "dev")
    items = items_from(sources)
    cache = EmbeddingCache(settings.data_dir / "cache", stage.encoder.model_id, stage.encoder.revision,
                           getattr(stage.encoder, "variant", ""))
    vectors = cache.get([i.quote for i in items], stage.encoder)
    pairs = [p for p in bench.load_pairs(settings, "dev") if p["pair_id"] in consensus]
    rows = grid_search(vectors, items, pairs, consensus, stage_settings)
    best = choose(rows)

    tuned = copy.deepcopy(stage_settings)
    tuned["thresholds"]["t_dup"] = best["t_dup"]
    encoder_view = _Precomputed(stage.encoder, cache)
    cached_nli = CachedNLI(stage.nli, settings.data_dir / "cache") if stage.nli else None

    def run(thresholds: dict[str, float], levels: list[float]) -> dict[str, Any]:
        variant = copy.deepcopy(tuned)
        variant["thresholds"].update(thresholds)
        variant["levels"] = levels
        return ClusterStage(variant, digest, encoder_view, stage.decision, cached_nli).run(sources)

    record: dict[str, Any] = {"chosen": {"t_dup": best["t_dup"]}, "grid": rows}
    if stage.specificity_allowed and cached_nli is not None:
        spec_rows = spec_search(run, pairs, consensus)
        spec = choose_spec(spec_rows)
        record["specificity_grid"] = spec_rows
        if spec is not None:
            tuned["thresholds"].update(t_spec=spec["t_spec"], t_nli=spec["t_nli"])
            record["chosen"].update(t_spec=spec["t_spec"], t_nli=spec["t_nli"])
    else:
        record["specificity_grid"] = "not tuned: " + (
            "the decision withholds the relation" if not stage.specificity_allowed
            else "no NLI model in the settings")
    levels = list(tuned.get("levels") or [])
    if stage.cluster_levels_allowed >= 1 and levels:
        sets = {s["set_id"]: s["items"] for s in bench.load_sets(settings, "dev")}
        refs = {m: {r["set_id"]: r for r in read_jsonl(path / "sets.jsonl")}
                for m, path in reference_runs(settings, "dev").items()}
        cluster_rows = cluster_search(run, sets, refs)
        chosen = choose_cluster(cluster_rows)
        record["cluster_grid"] = cluster_rows
        if chosen is not None:
            levels[0] = chosen["level_1"]
            record["chosen"]["level_1"] = chosen["level_1"]
        tuned["levels"] = levels[:stage.cluster_levels_allowed]
    else:
        record["cluster_grid"] = "not tuned: the decision produces no cluster level"
        tuned["levels"] = []

    tuned["name"] = f"{stage_settings.get('name', settings_path.stem)}-tuned"
    tuned["tuning"] = {
        "split": "dev", "benchmark_version": settings.benchmark_version,
        "metric": "duplicate pair F1, then specificity F1, then cluster level 1 B-cubed F1",
        "base_settings": str(settings_path), "base_settings_sha256": digest,
        "consensus_pairs": len(pairs), **record, "tuned_at": datetime.now(UTC).isoformat(),
    }
    tuned.setdefault("settings_changes", []).append(
        "thresholds and levels tuned on dev: " + ", ".join(
            f"{k} {v}" for k, v in record["chosen"].items()))
    target.write_text("# Tuned on the development split by `jtbd cluster tune` (tasks T032, "
                      "T043).\n" + yaml.safe_dump(tuned, sort_keys=False, allow_unicode=True),
                      encoding="utf-8")
    return {"settings": str(target), **record["chosen"], "f1": best["f1"], "pairs": len(pairs)}
