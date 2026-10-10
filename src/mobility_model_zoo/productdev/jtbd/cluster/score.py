"""`jtbd cluster score`: one candidate on the test split, per level (research R12, task T033).

The stage runs on the test pool; its groups (and, from user story 3 on, specificity links and
clusters) imply a label for each benchmark pair and a partition of each set. Scores are agreement
with the consensus of the two reference models on the named benchmark version, with the ratio to
the reference-vs-reference value per level; contested pairs are counted and scored neutrally. At
most three candidates, counted by encoder model id, are ever scored on test (research R5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd.cluster import bench
from mobility_model_zoo.productdev.jtbd.cluster.embed import Encoder
from mobility_model_zoo.productdev.jtbd.cluster.label import reference_runs
from mobility_model_zoo.productdev.jtbd.cluster.metrics import (
    analysis_dir,
    candidate_pair_labels,
    score_candidate,
)
from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, read_jsonl, write_json

MAX_CANDIDATES = 3


def check_candidate_limit(directory: Path, name: str, encoder_id: str, settings_sha: str) -> None:
    """A fourth encoder exits 2; the same candidate again only with an unchanged settings hash."""
    earlier = [read_json(p) for p in sorted(directory.glob("score-*.json"))]
    for e in earlier:
        if e["candidate"]["name"] == name and e["candidate"]["settings_sha256"] != settings_sha:
            raise UsageError(f"{name} was scored on test with other settings; a candidate is scored "
                             "again only with unchanged settings")
    encoders = {e["candidate"]["encoder"] for e in earlier}
    if encoder_id not in encoders and len(encoders) >= MAX_CANDIDATES:
        raise UsageError(f"{MAX_CANDIDATES} encoders were already scored on test "
                         f"({', '.join(sorted(encoders))}); no further candidate is scored")


def score(settings: Settings, settings_path: Path, encoder: Encoder | None = None) -> dict[str, Any]:
    bench.verify(settings)
    out = analysis_dir(settings)
    agreement_path = out / "agreement.json"
    if not agreement_path.exists():
        raise ValidationFailed("no agreement on test; run `jtbd cluster agreement --split test`")
    agreement = read_json(agreement_path)
    if agreement["split"] != "test" and agreement["split"] != "holdout":
        raise ValidationFailed("scores are computed against the test (or holdout) consensus")
    split = agreement["split"]
    stage = ClusterStage.from_settings(settings_path, encoder=encoder)
    name = stage.settings.get("name") or settings_path.stem
    check_candidate_limit(out, name, stage.encoder.model_id, stage.settings_sha256)
    result = stage.run(bench.pool_sources(settings, split))
    group_of = {i["item_id"]: i["group_id"] for i in result["items"]}
    parent_of = {g["group_id"]: g.get("parent") for g in result["groups"]}
    cluster_of = None
    if result["clusters"]:
        top = {}
        for c in result["clusters"]:
            if c["level"] == 1:
                for child in c["children"]:
                    top[child] = c["cluster_id"]
        cluster_of = {i: top[g] for i, g in group_of.items() if g in top}
    pairs = {p["pair_id"]: p for p in bench.load_pairs(settings, split)}
    predicted = candidate_pair_labels(pairs.values(), group_of, parent_of)
    consensus = list(read_jsonl(out / f"consensus-{split}.jsonl"))
    contested = list(read_jsonl(out / f"contested-{split}.jsonl"))
    runs = reference_runs(settings, split)
    reference_sets = {m: {r["set_id"]: r for r in read_jsonl(path / "sets.jsonl")}
                      for m, path in runs.items()}
    sets = {s["set_id"]: s["items"] for s in bench.load_sets(settings, split)}
    scores = score_candidate(predicted, consensus, contested, pairs, group_of, sets, cluster_of,
                             reference_sets, agreement["levels"])
    refs = " and ".join(agreement["references"])
    report = {
        "benchmark_version": settings.benchmark_version, "split": split,
        "scored_at": datetime.now(UTC).isoformat(),
        "candidate": {"name": name, "settings": str(settings_path),
                      "settings_sha256": stage.settings_sha256, "encoder": stage.encoder.model_id,
                      "revision": stage.encoder.revision},
        "statement": f"agreement with the consensus of {refs} on {settings.benchmark_version} "
                     f"({split}); not measured against human labels",
        "levels_produced": {"duplicate": True,
                            "specificity": any(g.get("parent") for g in result["groups"]),
                            "clusters": bool(result["clusters"])},
        **scores,
        "reference_vs_reference": {k: v.get("value") for k, v in agreement["levels"].items()},
        "deterministic_checks": result["checks"]["results"],
    }
    write_json(out / f"score-{name}.json", report)
    return {"score": str(out / f"score-{name}.json"),
            "duplicate": scores["levels"]["duplicate"],
            "consensus_pairs": scores["consensus_pairs"], "contested_pairs": scores["contested_pairs"]}
