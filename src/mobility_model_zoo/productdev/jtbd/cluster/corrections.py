"""Human corrections of the structure (research R14, data-model "Correction", tasks T048, T049).

`corrections.yaml` in the map directory lists operations by item id, applied after the automatic
step on every run, in file order:

- `merge` (`items`: one item per group): the groups become one (must-link); refused across kinds.
- `split` (`sets`: item sets): the sets never share a group (cannot-link); the other members of a
  split group go to the nearest set.
- `move` (`item`, `under`: item id or null, `into`: `group` or `cluster`): the node of `item` is
  pinned under the group of `under` (a specificity link, refused across kinds) or, with
  `into: cluster`, under the level-1 cluster above `under` (allowed across kinds); null makes it a
  top-level node.
- `representative` (`item`): the item becomes its group's representative.

Each operation gets `applied`, `stale` (its items are missing) or `refused` (with a reason).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml

from mobility_model_zoo.productdev.jtbd.errors import UsageError

FILE = "corrections.yaml"
OPS = ("merge", "split", "move", "representative")
ITEM = "it-"


def _is_item(x: Any) -> bool:
    return isinstance(x, str) and x.startswith(ITEM) and len(x) == 15


def validate(op: Any) -> str | None:
    """Why the operation is malformed, or None."""
    if not isinstance(op, dict) or op.get("op") not in OPS:
        return f"`op` must be one of {', '.join(OPS)}"
    allowed = {"op", "note"} | {"merge": {"items"}, "split": {"sets"},
                                "move": {"item", "under", "into"},
                                "representative": {"item"}}[op["op"]]
    extra = set(op) - allowed
    if extra:
        return f"unknown keys for {op['op']}: {sorted(extra)}"
    if op["op"] == "merge":
        items = op.get("items")
        if not isinstance(items, list) or len(items) < 2 or not all(map(_is_item, items)):
            return "merge needs `items`: at least two item ids"
    elif op["op"] == "split":
        sets = op.get("sets")
        if (not isinstance(sets, list) or len(sets) < 2
                or not all(isinstance(s, list) and s and all(map(_is_item, s)) for s in sets)):
            return "split needs `sets`: at least two non-empty lists of item ids"
        flat = [i for s in sets for i in s]
        if len(flat) != len(set(flat)):
            return "split sets must not share an item"
    elif op["op"] == "move":
        if not _is_item(op.get("item")):
            return "move needs `item`: an item id"
        if op.get("under") is not None and not _is_item(op["under"]):
            return "move needs `under`: an item id or null"
        if op.get("into", "group") not in ("group", "cluster"):
            return "move `into` must be group or cluster"
        if op.get("under") == op["item"]:
            return "move `under` must name another item"
    elif not _is_item(op.get("item")):
        return "representative needs `item`: an item id"
    if "note" in op and not isinstance(op["note"], str):
        return "`note` must be text"
    return None


def load(map_dir: Path | str | None) -> list[dict[str, Any]]:
    if map_dir is None:
        return []
    path = Path(map_dir) / FILE
    if not path.exists():
        return []
    ops = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(ops, list):
        raise UsageError(f"{path}: expected a list of operations")
    for n, op in enumerate(ops):
        error = validate(op)
        if error:
            raise UsageError(f"{path}: operation {n}: {error}")
    return ops


def append(map_dir: Path | str, op: dict[str, Any]) -> int:
    """`jtbd cluster correct`: validate and append; returns the operation's index."""
    error = validate(op)
    if error:
        raise UsageError(error)
    ops = load(map_dir)
    ops.append(op)
    path = Path(map_dir) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(ops, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return len(ops) - 1


def _status(index: int, op: dict[str, Any], status: str, reason: str | None = None
            ) -> dict[str, Any]:
    out = {"index": index, "op": op["op"], "status": status}
    if reason:
        out["reason"] = reason
    return out


def apply_to_rows(ops: list[dict[str, Any]], rows: list[list[int]], ids: list[str],
                  kinds: list[str], vectors: np.ndarray) -> tuple[list[list[int]], dict[int, dict],
                                                                   set[int]]:
    """Merge and split operations on duplicate groups (lists of item rows). Returns the new rows,
    the status per operation index, and the item rows of corrected groups."""
    row_of = {iid: r for r, iid in enumerate(ids)}
    status: dict[int, dict] = {}
    touched: set[int] = set()
    groups = [list(g) for g in rows]
    for n, op in enumerate(ops):
        if op["op"] == "merge":
            present = [row_of[i] for i in op["items"] if i in row_of]
            if len(present) < 2:
                status[n] = _status(n, op, "stale", "fewer than two of its items are present")
                continue
            if len({kinds[r] for r in present}) > 1:
                status[n] = _status(n, op, "refused", "merging groups of different kind (FR-004)")
                continue
            target = {r for r in present}
            joined = [g for g in groups if target & set(g)]
            rest = [g for g in groups if not target & set(g)]
            merged = sorted(r for g in joined for r in g)
            groups = rest + [merged]
            touched.update(merged)
            status[n] = _status(n, op, "applied")
        elif op["op"] == "split":
            sets = [[row_of[i] for i in s if i in row_of] for s in op["sets"]]
            sets = [s for s in sets if s]
            if len(sets) < 2:
                status[n] = _status(n, op, "stale", "fewer than two of its sets are present")
                continue
            new_groups = []
            for g in groups:
                seeds = [[r for r in s if r in g] for s in sets]
                seeds = [s for s in seeds if s]
                if len(seeds) < 2:
                    new_groups.append(g)
                    continue
                seeded = {r for s in seeds for r in s}
                parts = [list(s) for s in seeds]
                for r in g:
                    if r in seeded:
                        continue
                    sims = [float(np.mean(vectors[s] @ vectors[r])) for s in seeds]
                    parts[int(np.argmax(sims))].append(r)
                for part in parts:
                    new_groups.append(sorted(part))
                    touched.update(part)
            groups = new_groups
            status[n] = _status(n, op, "applied")
    return sorted(groups, key=min), status, touched


def apply_to_result(ops: list[dict[str, Any]], result: dict[str, Any],
                    status: dict[int, dict]) -> set[str]:
    """Move and representative operations on a built result, in file order. Returns the ids of
    clusters whose children changed (their aggregates must be recomputed)."""
    group_of = {i["item_id"]: i["group_id"] for i in result["items"]}
    groups = {g["group_id"]: g for g in result["groups"]}
    clusters = {c["cluster_id"]: c for c in result["clusters"]}
    nodes = {**groups, **clusters}
    changed: set[str] = set()

    def mark(nid: str | None) -> None:
        if nid in clusters:
            changed.add(nid)

    def detach(nid: str) -> None:
        parent = nodes[nid]["parent"]
        if parent:
            nodes[parent]["children"].remove(nid)
            mark(parent)
        nodes[nid]["parent"] = None

    def attach(nid: str, parent: str) -> None:
        nodes[nid]["parent"] = parent
        nodes[parent]["children"] = sorted([*nodes[parent]["children"], nid])
        mark(parent)

    def ancestors(nid: str) -> list[str]:
        out, current = [], nodes[nid]["parent"]
        while current and current not in out:
            out.append(current)
            current = nodes[current]["parent"]
        return out

    for n, op in enumerate(ops):
        if op["op"] == "representative":
            gid = group_of.get(op["item"])
            if gid is None:
                status[n] = _status(n, op, "stale", "the item is missing")
                continue
            groups[gid]["representative"] = op["item"]
            groups[gid]["corrected"] = True
            status[n] = _status(n, op, "applied")
        elif op["op"] == "move":
            gid = group_of.get(op["item"])
            if gid is None:
                status[n] = _status(n, op, "stale", "the item is missing")
                continue
            if op.get("under") is None:
                for c in ancestors(gid):
                    mark(c)
                detach(gid)
                groups[gid]["corrected"] = True
                status[n] = _status(n, op, "applied")
                continue
            target_group = group_of.get(op["under"])
            if target_group is None:
                status[n] = _status(n, op, "stale", "the `under` item is missing")
                continue
            if op.get("into", "group") == "group":
                if groups[target_group]["kind"] != groups[gid]["kind"]:
                    status[n] = _status(n, op, "refused",
                                        "a specificity link across kinds (FR-004, FR-011)")
                    continue
                if target_group == gid or gid in ancestors(target_group):
                    status[n] = _status(n, op, "refused", "the move would create a cycle")
                    continue
                target = target_group
            else:
                above = [a for a in ancestors(target_group) if a in clusters]
                if not above:
                    status[n] = _status(n, op, "refused", "no cluster above the `under` item")
                    continue
                target = above[0]
            for c in ancestors(gid):
                mark(c)
            detach(gid)
            attach(gid, target)
            groups[gid]["corrected"] = True
            status[n] = _status(n, op, "applied")
    for cid in changed:
        clusters[cid]["corrected"] = True
    return changed
