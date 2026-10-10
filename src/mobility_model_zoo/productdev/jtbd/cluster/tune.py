"""`jtbd cluster tune`: thresholds from development data only (research R12, task T032).

Grid over `t_dup` from 0.80 to 0.95 in steps of 0.01 on the development pairs the references agree
on, chosen by duplicate pair F1 (ties: the higher threshold, which merges less). The chosen value
and the full grid go into a new settings file; the test and holdout splits are refused (exit 2).
Specificity and cluster thresholds are tuned in task T043.
"""

from __future__ import annotations

import copy
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
    pair_prf,
)
from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage, load_stage_settings
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_jsonl

GRID = tuple(round(0.80 + 0.01 * i, 2) for i in range(16))


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


def tune(settings: Settings, settings_path: Path, split: str, out: Path | None = None,
         encoder: Encoder | None = None) -> dict[str, Any]:
    if split != "dev":
        raise UsageError("thresholds are tuned on the development split only (--split dev)")
    stage_settings, digest = load_stage_settings(settings_path)
    rows_dev = read_jsonl(analysis_dir(settings) / "consensus-dev.jsonl")
    consensus = {r["pair_id"]: r["label"] for r in rows_dev}
    if not consensus:
        raise ValidationFailed("no development consensus; run `jtbd cluster agreement --split dev`")
    stage = ClusterStage.from_settings(settings_path, encoder=encoder)
    items = items_from(bench.pool_sources(settings, "dev"))
    cache = EmbeddingCache(settings.data_dir / "cache", stage.encoder.model_id, stage.encoder.revision,
                           getattr(stage.encoder, "variant", ""))
    vectors = cache.get([i.quote for i in items], stage.encoder)
    pairs = [p for p in bench.load_pairs(settings, "dev") if p["pair_id"] in consensus]
    rows = grid_search(vectors, items, pairs, consensus, stage_settings)
    best = choose(rows)
    tuned = copy.deepcopy(stage_settings)
    tuned["name"] = f"{stage_settings.get('name', settings_path.stem)}-tuned"
    tuned["thresholds"]["t_dup"] = best["t_dup"]
    tuned["tuning"] = {
        "split": "dev", "benchmark_version": settings.benchmark_version, "metric": "duplicate pair F1",
        "base_settings": str(settings_path), "base_settings_sha256": digest,
        "consensus_pairs": len(pairs), "chosen": {"t_dup": best["t_dup"]}, "grid": rows,
        "tuned_at": datetime.now(UTC).isoformat(),
    }
    tuned.setdefault("settings_changes", []).append(
        f"t_dup {stage_settings['thresholds']['t_dup']} -> {best['t_dup']} by tuning on dev")
    target = out or settings_path.with_name(f"{settings_path.stem}-tuned.yaml")
    target.write_text("# Tuned on the development split by `jtbd cluster tune` (task T032).\n"
                      + yaml.safe_dump(tuned, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {"settings": str(target), "t_dup": best["t_dup"], "f1": best["f1"], "pairs": len(pairs)}
