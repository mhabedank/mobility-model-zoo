"""Stable group and cluster ids across runs (research R13, task T050).

`state.json` in the map directory holds, per id prefix (`dg`, `cl`), the counter of issued ids and
the previous run's membership (item ids below each node), plus the settings hash. After a run, the
new nodes are matched one to one to the previous nodes by Jaccard overlap of their item ids
(`scipy.optimize.linear_sum_assignment`, overlap > 0); ties go to the older id. A matched node keeps
its id; every other node gets the next id from the counter, which never reuses an id. That gives
the merge rule (the surviving id is the one with the most previous members, the others are merged
into it) and the split rule (the part with the most previous members keeps the id). `changes.json`
lists what changed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

STATE_FILE = "state.json"
CHANGES_FILE = "changes.json"
PREFIXES = {"dg": "groups", "cl": "clusters"}


def _number(node_id: str) -> int:
    return int(node_id.split("-", 1)[1])


def match(previous: dict[str, set[str]], new: list[set[str]]) -> dict[int, str]:
    """New node index -> previous id, one to one, maximising Jaccard overlap; older ids win ties."""
    prev_ids = sorted(previous, key=_number)
    if not prev_ids or not new:
        return {}
    weight = np.zeros((len(new), len(prev_ids)))
    for i, members in enumerate(new):
        for j, pid in enumerate(prev_ids):
            both = len(members & previous[pid])
            if both:
                jaccard = both / len(members | previous[pid])
                weight[i, j] = round(jaccard, 9) + 1e-12 * (len(prev_ids) - j)
    rows, cols = linear_sum_assignment(-weight)
    return {int(i): prev_ids[j] for i, j in zip(rows, cols, strict=True) if weight[i, j] > 0}


def assign(prefix: str, new: list[set[str]], previous: dict[str, set[str]], counter: int
           ) -> tuple[list[str], int, dict[str, list]]:
    """Final ids for the new nodes (in their order), the new counter and the changes."""
    matched = match(previous, new)
    ids: list[str] = []
    for i in range(len(new)):
        if i in matched:
            ids.append(matched[i])
        else:
            counter += 1
            ids.append(f"{prefix}-{counter:06d}")
    changes: dict[str, list] = {"new": [], "grown": [], "shrunk": [], "merged": [], "split": [],
                                "removed": []}
    for i, nid in enumerate(ids):
        if i not in matched:
            if not any(new[i] & members for members in previous.values()):
                changes["new"].append(nid)
            continue
        before, after = previous[nid], new[i]
        if after > before:
            changes["grown"].append(nid)
        elif after < before:
            changes["shrunk"].append(nid)
        elif after != before:
            changes["grown" if len(after) >= len(before) else "shrunk"].append(nid)
    kept = set(matched.values())
    members_of = dict(zip(ids, new, strict=True))
    for pid in sorted(previous, key=_number):
        overlapping = [ids[i] for i, members in enumerate(new) if members & previous[pid]]
        if pid not in kept:
            if overlapping:
                into = max(overlapping, key=lambda n: (len(previous[pid] & members_of[n]),
                                                       -_number(n)))
                changes["merged"].append({"into": into, "from": [pid]})
            else:
                changes["removed"].append(pid)
        elif len(overlapping) > 1:
            changes["split"].append({"from": pid, "into": sorted(overlapping, key=_number)})
    merged: dict[str, list[str]] = {}
    for m in changes["merged"]:
        merged.setdefault(m["into"], []).extend(m["from"])
    changes["merged"] = [{"into": k, "from": sorted(v, key=_number)} for k, v in sorted(merged.items())]
    return ids, counter, changes


def load_state(map_dir: Path | str | None) -> dict[str, Any] | None:
    if map_dir is None:
        return None
    path = Path(map_dir) / STATE_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _below(result: dict[str, Any]) -> dict[str, set[str]]:
    """Item ids below every node."""
    groups = {g["group_id"]: g for g in result["groups"]}
    clusters = {c["cluster_id"]: c for c in result["clusters"]}
    memo: dict[str, set[str]] = {}

    def walk(nid: str) -> set[str]:
        if nid not in memo:
            node = groups.get(nid) or clusters[nid]
            out = set(node.get("members", []))
            for child in node.get("children", []):
                out |= walk(child)
            memo[nid] = out
        return memo[nid]

    for nid in [*groups, *clusters]:
        walk(nid)
    return memo


def apply(result: dict[str, Any], state: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Renames the result's provisional ids to stable ones in place; returns (state, changes)."""
    below = _below(result)
    state = state or {}
    rename: dict[str, str] = {}
    new_state: dict[str, Any] = {"settings_sha256": result["settings"]["settings_sha256"],
                                 "counters": {}, "nodes": {}}
    changes: dict[str, Any] = {}
    for prefix, key in PREFIXES.items():
        id_key = "group_id" if prefix == "dg" else "cluster_id"
        provisional = [n[id_key] for n in result[key]]
        previous = {k: set(v) for k, v in (state.get("nodes", {}).get(prefix) or {}).items()}
        counter = int((state.get("counters") or {}).get(prefix, 0))
        ids, counter, node_changes = assign(prefix, [below[p] for p in provisional], previous,
                                            counter)
        rename.update(zip(provisional, ids, strict=True))
        new_state["counters"][prefix] = counter
        new_state["nodes"][prefix] = {i: sorted(below[p]) for p, i in zip(provisional, ids,
                                                                            strict=True)}
        for kind, values in node_changes.items():
            changes.setdefault(kind, []).extend(values)
    _rename(result, rename)
    previous_hash = state.get("settings_sha256")
    changes["settings_changed"] = bool(previous_hash) and previous_hash != new_state["settings_sha256"]
    if changes["settings_changed"]:
        changes["previous_settings_sha256"] = previous_hash
    return new_state, changes


def _rename(result: dict[str, Any], rename: dict[str, str]) -> None:
    def r(x):
        return rename.get(x, x) if isinstance(x, str) else x

    for item in result["items"]:
        item["group_id"] = r(item["group_id"])
    for node in [*result["groups"], *result["clusters"]]:
        for key in ("group_id", "cluster_id", "parent"):
            if key in node:
                node[key] = r(node[key])
        node["children"] = sorted(r(c) for c in node["children"])
    result["groups"].sort(key=lambda g: g["group_id"])
    result["clusters"].sort(key=lambda c: c["cluster_id"])


def write(map_dir: Path | str, state: dict[str, Any], changes: dict[str, Any]) -> None:
    map_dir = Path(map_dir)
    map_dir.mkdir(parents=True, exist_ok=True)
    (map_dir / STATE_FILE).write_text(json.dumps(state, indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
    (map_dir / CHANGES_FILE).write_text(json.dumps(changes, indent=1, sort_keys=True) + "\n",
                                        encoding="utf-8")
