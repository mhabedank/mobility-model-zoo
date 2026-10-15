"""Derived entities of the data overview (specs/017-mlflow-data-transparency/data-model.md).

Every value is computed from the registers, manifests, freeze files and release records on each
call; nothing here is stored. Rows hold counts and hashes, never dataset content (FR-008).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

KINDS = ("dataset", "source-collection", "training-set", "benchmark")
STATUSES = ("active", "rejected", "broken_at_source", "frozen", "decided", "building")
USES = ("training_allowed", "benchmark_only")
AVAILABILITY = ("measured", "register-only", "partial", "error")
INTEGRITY = ("ok", "mismatch", "unchecked", "changed-after-freeze")
EVENTS = ("registered", "field-changed", "frozen", "superseded", "revised", "excluded", "retrieved")

# A dataset that is not downloaded on this machine has no retrieval date and no measured hash.
REGISTER_VERSION = "register"


@dataclass
class InventoryRow:
    kind: str
    topic: str
    id: str
    version: str
    status: str
    source: str  # repository path the row was read from (register, manifest or freeze config)
    licence: str | None = None
    permitted_use: str | None = None
    redistribution: str | None = None
    size_mb: float | None = None
    approx_size_mb: float | None = None
    files: int | None = None
    counts: dict[str, int | float] = field(default_factory=dict)
    distribution: dict[str, dict[str, int]] = field(default_factory=dict)
    frozen_at: str | None = None
    sha256: str | None = None
    last_change: str | None = None
    lineage: list[dict[str, str]] = field(default_factory=list)
    used_by: list[str] = field(default_factory=list)
    availability: str = "measured"
    integrity: str = "unchecked"
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name, value, allowed in (
            ("kind", self.kind, KINDS),
            ("status", self.status, STATUSES),
            ("availability", self.availability, AVAILABILITY),
            ("integrity", self.integrity, INTEGRITY),
        ):
            if value not in allowed:
                raise ValueError(f"{self.key}: {name} {value!r} not in {allowed}")
        if self.permitted_use is not None and self.permitted_use not in USES:
            raise ValueError(f"{self.key}: permitted_use {self.permitted_use!r} not in {USES}")
        if any(v < 0 for v in self.counts.values()):
            raise ValueError(f"{self.key}: negative count")

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.kind, self.id, self.version)

    @property
    def name(self) -> str:
        """`<id>@<version>`, the dataset name in the tracking store (contracts/tracking.md)."""
        return f"{self.id}@{self.version}"

    @property
    def failed_integrity(self) -> bool:
        return self.integrity in ("mismatch", "changed-after-freeze")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoryEvent:
    date: str
    commit: str | None
    subject: str  # <kind>:<id>@<version>
    event: str
    field: str | None = None
    old: Any = None
    new: Any = None

    def __post_init__(self) -> None:
        if self.event not in EVENTS:
            raise ValueError(f"event {self.event!r} not in {EVENTS}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VersionDiff:
    a: str
    b: str
    counts: dict[str, dict[str, Any]] = field(default_factory=dict)
    distribution: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    members: dict[str, list[str]] = field(default_factory=dict)
    hashes: dict[str, str | None] = field(default_factory=dict)
    protocol: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_unique(rows: list[InventoryRow]) -> None:
    """`(kind, id, version)` is unique (data-model.md, InventoryRow validation)."""
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if row.key in seen:
            raise ValueError(f"duplicate inventory row {row.key}")
        seen.add(row.key)
