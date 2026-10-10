"""`jtbd cluster decide`: frozen criteria -> go, revise or rethink per level (research R12, T031).

The criteria file must be unchanged since the freeze (exit 3). A level below its threshold is
`revise` while a re-pilot is left (one, on the holdout split), else `rethink`. A level that is not
`go` is not produced (spec FR-024): without duplicates the task stops; without the specificity
relation more specific groups become siblings; without clusters the result holds groups only. A
second cluster level is considered only when the first one is `go`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import yaml

from mobility_model_zoo.productdev.jtbd.cluster import bench
from mobility_model_zoo.productdev.jtbd.cluster.metrics import analysis_dir
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import FrozenHashMismatch, ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import sha256_canonical
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json

THRESHOLD_KEYS = {"duplicate": "duplicate_kappa_min", "specificity": "specificity_kappa_min",
                  "cluster_level_1": "cluster_bcubed_f1_min", "cluster_level_2": "cluster_bcubed_f1_min"}


def decide_levels(levels: dict[str, Any], criteria: dict[str, Any], reruns_used: int
                  ) -> dict[str, Any]:
    """Pure rule: value >= threshold -> go; below -> revise while a rerun is left, else rethink. A
    level without data (no sets with a coarse partition) is `not_measured` and not produced."""
    max_reruns = int((criteria.get("revise") or {}).get("max_reruns", 1))
    out: dict[str, Any] = {}
    for level, key in THRESHOLD_KEYS.items():
        value = (levels.get(level) or {}).get("value")
        threshold = float(criteria[key])
        if level == "cluster_level_2" and out.get("cluster_level_1", {}).get("decision") != "go":
            decision = "not_measured"
        elif value is None:
            decision = "not_measured"
        elif value >= threshold:
            decision = "go"
        else:
            decision = "revise" if reruns_used < max_reruns else "rethink"
        out[level] = {"value": value, "threshold": threshold, "decision": decision}
    return out


def decide(settings: Settings) -> dict[str, Any]:
    manifest = bench.verify(settings)
    criteria_path = settings.base / bench.cfg(settings)["criteria"]
    if sha256_canonical(criteria_path) != manifest["hashes"]["criteria"]:
        raise FrozenHashMismatch(f"{criteria_path} changed since the freeze")
    if manifest["state"] != "piloted":
        raise ValidationFailed(f"benchmark is {manifest['state']}; run `jtbd cluster agreement` first")
    criteria = yaml.safe_load(criteria_path.read_text(encoding="utf-8"))
    agreement = read_json(analysis_dir(settings) / "agreement.json")
    reruns = int(manifest.get("reruns", 0))
    levels = decide_levels(agreement["levels"], criteria, reruns)
    revise = any(v["decision"] == "revise" for v in levels.values())
    produced = {k: v["decision"] == "go" for k, v in levels.items()}
    result = {
        "benchmark_version": settings.benchmark_version, "split": agreement["split"],
        "decided_at": datetime.now(UTC).isoformat(), "criteria_sha256": manifest["hashes"]["criteria"],
        "reruns_used": reruns, "levels": levels, "final": not revise,
        "duplicates_produced": produced["duplicate"],
        "specificity_produced": produced["specificity"],
        "cluster_levels_produced": (2 if produced["cluster_level_1"] and produced["cluster_level_2"]
                                    else 1 if produced["cluster_level_1"] else 0),
        "task_stopped": levels["duplicate"]["decision"] == "rethink",
    }
    write_json(analysis_dir(settings) / "decision.json", result)
    if revise:
        manifest = bench.set_state(settings, "revise", "a level is below its threshold")
        manifest["reruns"] = reruns + 1
        bench.save_manifest(settings, manifest)
    else:
        bench.set_state(settings, "decided", "every level decided")
    return result
