"""Compare two versions of one training set or benchmark family (FR-006).

Counts, distributions and member ids with their hashes; never content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.errors import UsageError

from .rows import InventoryRow, VersionDiff


def _delta(a: Any, b: Any) -> dict[str, Any]:
    out = {"a": a, "b": b}
    if isinstance(a, int | float) and isinstance(b, int | float):
        out["delta"] = round(b - a, 3)
    return out


def _members(root: Path, row: InventoryRow) -> dict[str, str]:
    """Member id -> hash: captures of a CAN benchmark, chunks of a JTBD pilot."""
    if row.kind != "benchmark" or not row.source.endswith(".json"):
        return {}
    m = json.loads((root / row.source).read_text(encoding="utf-8"))
    if "captures" in m:
        return {c["id"]: f"{c.get('sha256', '')}:{c.get('role', '')}" for c in m["captures"]}
    if "chunks" in m:
        out = {k: v for k, v in (m.get("chunks") or {}).items()}
        out.update({k: f"{v}:holdout" for k, v in (m.get("holdout_chunks") or {}).items()})
        return out
    return {}


def _blocks(root: Path, row: InventoryRow) -> dict[str, Any]:
    if row.kind != "benchmark" or not row.source.endswith(".json"):
        return {}
    m = json.loads((root / row.source).read_text(encoding="utf-8"))
    out = {f"protocol.{k}": v for k, v in (m.get("protocol") or {}).items()}
    out.update({f"hashes.{k}": v for k, v in (m.get("hashes") or {}).items()})
    return out


def diff(root: Path, a: InventoryRow, b: InventoryRow, members: bool = False) -> VersionDiff:
    if a.kind != b.kind or a.id != b.id:
        raise UsageError(f"cannot compare {a.kind} {a.name} with {b.kind} {b.name}: different families")
    out = VersionDiff(a=a.name, b=b.name, hashes={"a": a.sha256, "b": b.sha256})
    for key in sorted(set(a.counts) | set(b.counts)):
        out.counts[key] = _delta(a.counts.get(key, 0), b.counts.get(key, 0))
    for dim in sorted(set(a.distribution) | set(b.distribution)):
        da, db = a.distribution.get(dim, {}), b.distribution.get(dim, {})
        changed = {
            v: _delta(da.get(v, 0), db.get(v, 0))
            for v in sorted(set(da) | set(db))
            if da.get(v, 0) != db.get(v, 0)
        }
        if changed:
            out.distribution[dim] = changed
    pa, pb = _blocks(root, a), _blocks(root, b)
    out.protocol = {
        k: {"a": pa.get(k), "b": pb.get(k)} for k in sorted(set(pa) | set(pb)) if pa.get(k) != pb.get(k)
    }
    ma, mb = _members(root, a), _members(root, b)
    added = sorted(set(mb) - set(ma))
    removed = sorted(set(ma) - set(mb))
    changed = sorted(k for k in set(ma) & set(mb) if ma[k] != mb[k])
    out.members = {"added": added, "removed": removed, "changed": changed}
    if not members:
        out.members = {k: [f"{len(v)} member(s)"] if v else [] for k, v in out.members.items()}
    return out
