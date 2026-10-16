"""The data overview of `zoo data stats|history|diff` (feature 017, specs/017-…/contracts/cli.md).

Everything is derived on each call from what the repository already holds: the topic registers,
`$MMZ_DATA/<id>/SOURCE.json`, frozen benchmark manifests, freeze files and release records, plus git
for history. Nothing is added to the registers, and no MLflow import happens here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mobility_model_zoo.release.errors import ZooError

from .rows import InventoryRow, check_unique


class IntegrityFailed(ZooError):
    """A frozen benchmark changed (constitution IX); exit code 7 (contracts/cli.md)."""

    exit_code = 7


@dataclass
class Inventory:
    rows: list[InventoryRow]
    hidden: int = 0  # rejected or broken datasets left out of the rows
    notes: list[str] = field(default_factory=list)

    @property
    def failed(self) -> list[InventoryRow]:
        return [r for r in self.rows if r.failed_integrity]


def _last_change(root: Path, row: InventoryRow) -> str | None:
    from . import history

    if not history.in_git(root):
        return None
    if row.kind == "dataset":
        return history.record_last_change(root, row.source, "datasets", row.id)
    return history.last_change(root, row.source)


def collect(
    root: Path | None = None,
    data_root: Path | None = None,
    kinds: list[str] | None = None,
    topics: list[str] | None = None,
    use: str | None = None,
    include_rejected: bool = False,
    verify: bool = False,
    integrity: bool = True,
) -> Inventory:
    """Every dataset, source collection, training set and benchmark version, filtered."""
    from mobility_model_zoo.datasets.registry import declarations
    from mobility_model_zoo.edge.paths import data_root as default_data_root
    from mobility_model_zoo.edge.paths import repo_root

    from . import benchmarks, sources, third_party, training_sets, used_by
    from . import integrity as checks

    root = Path(root) if root else repo_root()
    data_root = Path(data_root) if data_root else default_data_root()
    registry = {rec.get("id"): rec for _topic, rec in declarations(root)}

    rows = third_party.collect(root, data_root)
    collections = sources.collect(root)
    rows += collections
    source_use = {r.topic: r.permitted_use for r in collections}
    rows += training_sets.collect(root)
    bench_rows, notes = benchmarks.collect(root, registry, source_use)
    rows += bench_rows
    check_unique(rows)
    used_by.resolve(root, rows)
    for row in rows:
        row.last_change = _last_change(root, row)
    if integrity:
        checks.check(root, rows, verify=verify)

    hidden = [r for r in rows if r.kind == "dataset" and r.status in ("rejected", "broken_at_source")]
    if not include_rejected:
        rows = [r for r in rows if r not in hidden]
    if kinds:
        rows = [r for r in rows if r.kind in kinds]
    if topics:
        rows = [r for r in rows if r.topic in topics]
    if use:
        rows = [r for r in rows if r.permitted_use == use]
    rows.sort(key=lambda r: (r.topic, r.kind, r.id, r.version))
    return Inventory(rows=rows, hidden=0 if include_rejected else len(hidden), notes=notes)


def find(inventory: Inventory, ref: str) -> list[InventoryRow]:
    """Rows named by a dataset id, a family (`can-ids`), a version (`can-ids-v2`) or `id@version`."""
    if "@" in ref:
        return [r for r in inventory.rows if r.name == ref]
    exact = [r for r in inventory.rows if r.version == ref and r.kind != "dataset"]
    return exact or [r for r in inventory.rows if r.id == ref]
