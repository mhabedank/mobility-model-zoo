"""The cluster stage: scout outputs in, one `jtbd-cluster-v1` result out (spec FR-013).

User story 1 builds duplicate groups. Specificity, clusters, continuity, corrections and
annotations are added by later user stories; until then `clusters` is empty and group ids are
assigned in order of each group's smallest item id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from mobility_model_zoo.productdev.jtbd.cluster.bundle import (
    INPUT_FORMAT_VERSION,
    Item,
    Source,
    file_sha256,
    items_from,
)
from mobility_model_zoo.productdev.jtbd.cluster.checks import (
    aggregate,
    check_result,
    independence_rule,
    passed,
)
from mobility_model_zoo.productdev.jtbd.cluster.dedup import group_items
from mobility_model_zoo.productdev.jtbd.cluster.embed import EmbeddingCache, Encoder, make_encoder
from mobility_model_zoo.productdev.jtbd.errors import UsageError

OUTPUT_FORMAT_VERSION = "jtbd-cluster-v1"
SETTINGS_KEYS = {"name", "encoder", "nli", "neighbours", "thresholds", "levels", "representative",
                 "settings_changes", "tuning", "decision"}


def load_decision(settings: dict[str, Any], base: Path) -> dict[str, Any] | None:
    """The agreement pilot's decision (`decision.json`, task T031) named by `decision:` in the
    settings. A level that is not `go` is not produced (spec FR-024); a stopped task refuses to run."""
    name = settings.get("decision")
    if not name:
        return None
    path = Path(name) if Path(name).is_absolute() else base / name
    if not path.exists():
        raise UsageError(f"decision file not found: {path}")
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("task_stopped"):
        raise UsageError(f"{path}: the duplicate level ended `rethink`; the task is stopped")
    return decision


def load_stage_settings(path: Path | str) -> tuple[dict[str, Any], str]:
    path = Path(path)
    if not path.exists():
        raise UsageError(f"stage settings not found: {path}")
    raw = path.read_bytes()
    settings = yaml.safe_load(raw) or {}
    unknown = set(settings) - SETTINGS_KEYS
    if unknown:
        raise UsageError(f"stage settings {path} have unknown keys: {sorted(unknown)}")
    for key in ("encoder", "neighbours", "thresholds"):
        if key not in settings:
            raise UsageError(f"stage settings {path} lack `{key}`")
    return settings, file_sha256(path)


def representative(indices: list[int], vectors: np.ndarray) -> int:
    """Member with the highest mean cosine to the other members (research R9). Rows are sorted by
    item id, so the smaller row index wins a tie."""
    if len(indices) == 1:
        return indices[0]
    sub = vectors[indices]
    sims = sub @ sub.T
    mean = (sims.sum(axis=1) - np.diag(sims)) / (len(indices) - 1)
    best = max(range(len(indices)), key=lambda j: (round(float(mean[j]), 6), -indices[j]))
    return indices[best]


class ClusterStage:
    def __init__(self, settings: dict[str, Any], settings_sha256: str, encoder: Encoder,
                 decision: dict[str, Any] | None = None):
        self.settings = settings
        self.settings_sha256 = settings_sha256
        self.encoder = encoder
        # Levels the pilot allows; user stories 3 and later produce only these (spec FR-024).
        self.decision = decision
        self.specificity_allowed = bool(decision is None or decision.get("specificity_produced"))
        self.cluster_levels_allowed = (len(settings.get("levels") or []) if decision is None
                                       else int(decision.get("cluster_levels_produced", 0)))

    @classmethod
    def from_settings(cls, path: Path | str, encoder: Encoder | None = None) -> ClusterStage:
        settings, digest = load_stage_settings(path)
        base = Path(path).resolve().parent
        decision = load_decision(settings, base)
        if encoder is None:
            encoder = make_encoder(settings["encoder"], base=base)
        return cls(settings, digest, encoder, decision)

    def run(self, sources: list[Source], map_dir: Path | str | None = None,
            bundle_paths: list[Path | str] | None = None) -> dict[str, Any]:
        items = items_from(sources)
        cache = EmbeddingCache(map_dir, self.encoder.model_id, self.encoder.revision,
                               getattr(self.encoder, "variant", ""))
        vectors = cache.get([i.quote for i in items], self.encoder) if items else np.zeros((0, 1))
        thresholds = self.settings["thresholds"]
        neighbours = self.settings["neighbours"]
        rows = group_items(
            vectors, [i.kind for i in items], [i.exact_copy_key for i in items],
            k=int(neighbours["k"]), floor=float(neighbours["candidate_floor"]),
            t_dup=float(thresholds["t_dup"]),
        ) if items else []

        groups, group_of = [], {}
        for n, members in enumerate(rows, start=1):
            gid = f"dg-{n:06d}"
            for r in members:
                group_of[items[r].item_id] = gid
            groups.append(self._group(gid, [items[r] for r in members],
                                      items[representative(members, vectors)].item_id))

        result = {
            "output_format_version": OUTPUT_FORMAT_VERSION,
            "settings": self._settings_block(),
            "inputs": self._inputs_block(sources, items, bundle_paths),
            "items": [i.as_dict(group_of[i.item_id]) for i in items],
            "groups": groups,
            "clusters": [],
            "checks": {"passed": True, "corrections": []},
        }
        bundle_quotes = {i.item_id: i.quote for i in items}
        checks = check_result(result, bundle_quotes)
        result["checks"] = {"passed": passed(checks), "corrections": [], "results": checks}
        if map_dir is not None:
            write_result(Path(map_dir), result)
        return result

    @staticmethod
    def _group(gid: str, members: list[Item], rep: str) -> dict[str, Any]:
        rule = independence_rule([m.origin_based for m in members])
        agg = aggregate([m.as_dict(gid) for m in members], rule)
        return {
            "group_id": gid, "kind": members[0].kind,
            "members": sorted(m.item_id for m in members), "representative": rep,
            "parent": None, "children": [], **agg,
            "statement": None, "assignments": [], "corrected": False,
        }

    def _settings_block(self) -> dict[str, Any]:
        enc = self.settings["encoder"]
        return {
            "settings_sha256": self.settings_sha256,
            "name": self.settings.get("name"),
            "encoder": {"model_id": self.encoder.model_id, "revision": self.encoder.revision,
                        "backend": enc.get("backend", "transformers")},
            "nli": None,
            "thresholds": self.settings["thresholds"],
            "neighbours": self.settings["neighbours"],
            "specificity_produced": False,
            "cluster_levels_produced": 0,
        }

    @staticmethod
    def _inputs_block(sources: list[Source], items: list[Item],
                      bundle_paths: list[Path | str] | None) -> dict[str, Any]:
        paths = [str(p) for p in bundle_paths or []]
        return {
            "input_format_version": INPUT_FORMAT_VERSION,
            "bundles": [file_sha256(p) for p in paths],
            "bundle_paths": paths,
            "sources": len(sources),
            "items": len(items),
        }


def write_result(map_dir: Path, result: dict[str, Any]) -> Path:
    map_dir.mkdir(parents=True, exist_ok=True)
    path = map_dir / "result.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path
