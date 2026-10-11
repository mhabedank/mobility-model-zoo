"""The cluster stage: scout outputs in, one `jtbd-cluster-v1` result out (spec FR-013).

Duplicate groups within kind (user story 1), then the specificity relation between groups of one
kind and clusters across kinds (user story 3), each only where the agreement pilot's decision allows
it (spec FR-024). Continuity, corrections and annotations are added by later user stories; until
then group and cluster ids are assigned in order of each node's smallest item id.
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
from mobility_model_zoo.productdev.jtbd.cluster.hierarchy import Node, build_levels, representative
from mobility_model_zoo.productdev.jtbd.cluster.specificity import HFNLI, NLI, specificity_links
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


def spec_neighbours(neighbours: dict[str, Any]) -> int:
    """Neighbours per group that are specificity candidates (`k_spec`, default 5). The NLI model
    runs on both directions of every candidate pair, so this bounds the stage's cost: with the
    deduplication's k = 30, the dev pool alone gave about 73,000 pairs (2026-10-11)."""
    return int(neighbours.get("k_spec", 5))


class ClusterStage:
    def __init__(self, settings: dict[str, Any], settings_sha256: str, encoder: Encoder,
                 decision: dict[str, Any] | None = None, nli: NLI | None = None):
        self.settings = settings
        self.settings_sha256 = settings_sha256
        self.encoder = encoder
        self.nli = nli
        # Levels the pilot allows; user stories 3 and later produce only these (spec FR-024).
        self.decision = decision
        self.specificity_allowed = bool(decision is None or decision.get("specificity_produced"))
        self.cluster_levels_allowed = (len(settings.get("levels") or []) if decision is None
                                       else int(decision.get("cluster_levels_produced", 0)))

    @classmethod
    def from_settings(cls, path: Path | str, encoder: Encoder | None = None,
                      nli: NLI | None = None) -> ClusterStage:
        """`nli: null` in the settings means no specificity relation (e.g. a commercial-use line
        without a commercially usable NLI model); otherwise the model is loaded only if the
        decision allows the relation."""
        settings, digest = load_stage_settings(path)
        return cls.from_dict(settings, digest, Path(path).resolve().parent, encoder, nli)

    @classmethod
    def from_dict(cls, settings: dict[str, Any], digest: str, base: Path,
                  encoder: Encoder | None = None, nli: NLI | None = None) -> ClusterStage:
        """Paths in the settings (decision, encoder table) are relative to `base`."""
        decision = load_decision(settings, base)
        if encoder is None:
            encoder = make_encoder(settings["encoder"], base=base)
        allowed = decision is None or decision.get("specificity_produced")
        if nli is None and settings.get("nli") and allowed:
            nli = HFNLI.from_settings(settings["nli"])
        return cls(settings, digest, encoder, decision, nli)

    def run(self, sources: list[Source], map_dir: Path | str | None = None,
            bundle_paths: list[Path | str] | None = None) -> dict[str, Any]:
        """Automatic structure, then the map's corrections, stable ids and annotations (user
        stories 4 and 5; only with a map directory)."""
        from mobility_model_zoo.productdev.jtbd.cluster import annotation, continuity, corrections

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
        ops = corrections.load(map_dir)
        rows, status, touched = corrections.apply_to_rows(
            ops, rows, [i.item_id for i in items], [i.kind for i in items], vectors)

        groups, group_of = [], {}
        for n, members in enumerate(rows, start=1):
            gid = f"dg-{n:06d}"
            for r in members:
                group_of[items[r].item_id] = gid
            groups.append(self._group(gid, [items[r] for r in members],
                                      items[representative(members, vectors)].item_id))
            groups[-1]["corrected"] = bool(touched & set(members))
        serial = [i.as_dict(group_of[i.item_id]) for i in items]

        produced_spec = self._link_specific(groups, rows, items, vectors)
        levels = [float(t) for t in (self.settings.get("levels") or [])][:self.cluster_levels_allowed]
        clusters = self._cluster(groups, rows, items, serial, vectors, levels)

        result = {
            "output_format_version": OUTPUT_FORMAT_VERSION,
            "settings": self._settings_block(produced_spec, len({c["level"] for c in clusters})),
            "inputs": self._inputs_block(sources, items, bundle_paths),
            "items": serial,
            "groups": groups,
            "clusters": clusters,
            "checks": {"passed": True, "corrections": []},
        }
        if corrections.apply_to_result(ops, result, status):
            self._refresh_clusters(result, items, vectors)
        changes: dict[str, Any] = {}
        if map_dir is not None:
            state, changes = continuity.apply(result, continuity.load_state(map_dir))
            changes["orphaned_annotations"] = annotation.merge(result, annotation.load(map_dir))
        statuses = [status[n] for n in sorted(status)]
        changes["stale_corrections"] = [s["index"] for s in statuses if s["status"] == "stale"]
        changes["refused_corrections"] = [s["index"] for s in statuses if s["status"] == "refused"]
        bundle_quotes = {i.item_id: i.quote for i in items}
        checks = check_result(result, bundle_quotes)
        result["checks"] = {"passed": passed(checks), "corrections": statuses, "results": checks}
        if map_dir is not None:
            write_result(Path(map_dir), result)
            continuity.write(map_dir, state, changes)
        return result

    def _refresh_clusters(self, result: dict[str, Any], items: list[Item],
                          vectors: np.ndarray) -> None:
        """After moves: drops clusters left without children and recomputes the aggregates,
        kinds and representative of every cluster from the items below it."""
        row_of = {i.item_id: r for r, i in enumerate(items)}
        serial = {i["item_id"]: i for i in result["items"]}
        groups = {g["group_id"]: g for g in result["groups"]}
        while True:
            clusters = {c["cluster_id"]: c for c in result["clusters"]}
            empty = [cid for cid, c in clusters.items() if not c["children"]]
            if not empty:
                break
            for cid in empty:
                parent = clusters[cid]["parent"]
                if parent in clusters:
                    clusters[parent]["children"].remove(cid)
            result["clusters"] = [c for c in result["clusters"] if c["cluster_id"] not in empty]
        nodes = {**groups, **{c["cluster_id"]: c for c in result["clusters"]}}

        def below(nid: str) -> tuple[list[str], list[str]]:
            node = nodes[nid]
            item_ids = list(node.get("members", []))
            group_ids = [nid] if nid in groups else []
            for child in node["children"]:
                i, g = below(child)
                item_ids += i
                group_ids += g
            return item_ids, group_ids

        for c in result["clusters"]:
            item_ids, group_ids = below(c["cluster_id"])
            rows = sorted(row_of[i] for i in item_ids)
            rule = independence_rule([items[r].origin_based for r in rows])
            kinds: dict[str, int] = {}
            for gid in group_ids:
                kinds[groups[gid]["kind"]] = kinds.get(groups[gid]["kind"], 0) + 1
            c.update(aggregate([serial[items[r].item_id] for r in rows], rule))
            c["kinds"] = dict(sorted(kinds.items()))
            c["representative"] = items[representative(rows, vectors)].item_id

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

    def _link_specific(self, groups: list[dict[str, Any]], rows: list[list[int]],
                       items: list[Item], vectors: np.ndarray) -> bool:
        """Sets `dg-` parents and children (research R8); False if the relation is not produced."""
        if not (self.specificity_allowed and self.nli is not None and groups):
            return False
        thresholds = self.settings["thresholds"]
        reps = [next(r for r in members if items[r].item_id == g["representative"])
                for g, members in zip(groups, rows, strict=True)]
        links = specificity_links(
            [g["kind"] for g in groups], [g["group_id"] for g in groups],
            [items[r].quote for r in reps], vectors[reps], self.nli,
            k=spec_neighbours(self.settings["neighbours"]), t_spec=float(thresholds["t_spec"]),
            t_dup=float(thresholds["t_dup"]), t_nli=float(thresholds["t_nli"]))
        for child, parent in sorted(links.items()):
            groups[child]["parent"] = groups[parent]["group_id"]
            groups[parent]["children"].append(groups[child]["group_id"])
        for g in groups:
            g["children"].sort()
        return True

    def _cluster(self, groups: list[dict[str, Any]], rows: list[list[int]], items: list[Item],
                 serial: list[dict[str, Any]], vectors: np.ndarray, levels: list[float]
                 ) -> list[dict[str, Any]]:
        """Clusters of top-level groups (research R9); children follow their parent group."""
        if not levels or len(groups) < 2:
            return []
        index = {g["group_id"]: n for n, g in enumerate(groups)}

        def below(n: int) -> list[int]:
            out = list(rows[n])
            for child in groups[n]["children"]:
                out += below(index[child])
            return out

        tops = [Node(g["group_id"], sorted(below(n))) for n, g in enumerate(groups)
                if g["parent"] is None]
        neighbours = self.settings["neighbours"]
        nodes = build_levels(tops, vectors, levels, k=int(neighbours["k"]),
                             floor=float(neighbours["candidate_floor"]))
        for n, node in enumerate(sorted(nodes, key=lambda x: (x.rows[0], x.level)), start=1):
            node.key = f"cl-{n:06d}"
        kind_of = {g["group_id"]: g["kind"] for g in groups}
        clusters = []
        for node in sorted(nodes, key=lambda x: x.key):
            for child in node.children:
                if child.key.startswith("dg-"):
                    groups[index[child.key]]["parent"] = node.key
            below_groups = self._groups_below(node, groups, index)
            rule = independence_rule([items[r].origin_based for r in node.rows])
            kinds: dict[str, int] = {}
            for gid in below_groups:
                kinds[kind_of[gid]] = kinds.get(kind_of[gid], 0) + 1
            clusters.append({
                "cluster_id": node.key, "level": node.level, "parent": None,
                "children": sorted(c.key for c in node.children),
                "representative": items[representative(node.rows, vectors)].item_id,
                **aggregate([serial[r] for r in node.rows], rule),
                "kinds": dict(sorted(kinds.items())),
                "statement": None, "assignments": [], "corrected": False,
            })
        by_id = {c["cluster_id"]: c for c in clusters}
        for c in clusters:
            for child in c["children"]:
                if child in by_id:
                    by_id[child]["parent"] = c["cluster_id"]
        return clusters

    @staticmethod
    def _groups_below(node: Node, groups: list[dict[str, Any]], index: dict[str, int]) -> list[str]:
        out = []

        def walk_group(gid: str) -> None:
            out.append(gid)
            for child in groups[index[gid]]["children"]:
                walk_group(child)

        def walk(n: Node) -> None:
            if n.key.startswith("dg-"):
                walk_group(n.key)
            for c in n.children:
                walk(c)

        walk(node)
        return out

    def _settings_block(self, specificity_produced: bool = False,
                        cluster_levels_produced: int = 0) -> dict[str, Any]:
        enc = self.settings["encoder"]
        nli = ({"model_id": self.nli.model_id, "revision": self.nli.revision}
               if specificity_produced and self.nli is not None else None)
        return {
            "settings_sha256": self.settings_sha256,
            "name": self.settings.get("name"),
            "encoder": {"model_id": self.encoder.model_id, "revision": self.encoder.revision,
                        "backend": enc.get("backend", "transformers"),
                        "threads": getattr(self.encoder, "threads", None),
                        "device": getattr(self.encoder, "device", None)},
            "nli": nli,
            "thresholds": self.settings["thresholds"],
            "neighbours": self.settings["neighbours"],
            "levels": [float(t) for t in (self.settings.get("levels") or [])],
            "specificity_produced": specificity_produced,
            "cluster_levels_produced": cluster_levels_produced,
            # Without a decision file every level is produced but none was measured (FR-024).
            "measured": self.decision is not None,
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
