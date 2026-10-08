"""Dataset declarations of all topics (feature 005 US3, research R10).

The declarations live in the compliance register, `topics/<topic>/compliance/datasets.yaml`, and
are validated against `compliance/schemas/datasets.schema.json`. This module reads them into the
in-memory `Source` form used by the downloader and the training guard.

Rules (constitution VI, data-model.md "Dataset declaration"):
* Data is never committed: `zoo data download` writes to $MMZ_DATA
  (default ~/.cache/mobility-model-zoo/datasets).
* `zoo data verify` compares the licence the publisher declares today (Zenodo, UCI) with the
  declaration; `manual` entries report their last check date.
* Training only uses `permitted_use: training_allowed` datasets with `status: active`.
* No dataset is published while its redistribution is `unclear`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Source:
    id: str
    topic: str
    title: str
    use_case: str
    license: str  # SPDX id or LicenseRef-…
    license_url: str | None
    homepage: str
    attribution: str
    citation: str
    provider: str  # zenodo | uci | bitbucket | url
    permitted_use: str  # training_allowed | benchmark_only
    redistribution: str  # allowed | not_allowed | unclear
    commercial_use: bool
    status: str  # active | broken_at_source | rejected
    license_check: str  # api | manual
    license_checked: str | None = None
    reason: str | None = None
    # where the files come from
    zenodo_record: str | None = None
    uci_id: int | None = None
    repo: str | None = None  # bitbucket workspace/repository
    urls: tuple[str, ...] = ()
    # only fetch these files from a Zenodo record (prefix match, empty = all)
    zenodo_files: tuple[str, ...] = ()
    # read only these members (glob, max count) out of the archive(s) via HTTP ranges
    zip_members: tuple[tuple[str, int], ...] = ()
    approx_size_mb: float = 0
    notes: str = ""
    used_by: tuple[str, ...] = field(default_factory=tuple)

    @property
    def broken(self) -> str:
        """Non-empty when the publisher's files are unusable; download refuses unless forced."""
        return (self.reason or "broken at source") if self.status == "broken_at_source" else ""


def _root(root: Path | None) -> Path:
    from mobility_model_zoo.edge.paths import repo_root

    return Path(root) if root else repo_root()


def declarations(root: Path | None = None) -> list[tuple[str, dict[str, Any]]]:
    """(topic, record) for every declaration of every topic file."""
    import yaml

    out = []
    for path in sorted((_root(root) / "topics").glob("*/compliance/datasets.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        out += [(path.parent.parent.name, rec) for rec in data.get("datasets") or []]
    return out


def validate(root: Path | None = None) -> list[str]:
    """Schema findings of the topic files plus ids declared twice. Empty when valid."""
    from mobility_model_zoo.compliance.register import Register

    reg = Register.load(_root(root))
    problems = [f.line() for f in reg.schema_findings() if "datasets.yaml" in f.line()]
    seen: dict[str, str] = {}
    for topic, rec in declarations(root):
        rid = rec.get("id")
        if rid in seen:
            problems.append(f"datasets: id {rid} declared in topics {seen[rid]} and {topic}")
        seen.setdefault(rid, topic)
    return problems


def to_source(topic: str, rec: dict[str, Any]) -> Source:
    loc = rec.get("locator") or {}
    return Source(
        id=rec["id"],
        topic=topic,
        title=rec["title"],
        use_case=rec.get("use_case", ""),
        license=rec["licence"],
        license_url=rec.get("licence_url"),
        homepage=rec["origin_url"],
        attribution=rec["attribution_text"],
        citation=rec.get("citation", ""),
        provider=rec["provider"],
        permitted_use=rec["permitted_use"],
        redistribution=rec["redistribution"],
        commercial_use=bool(rec["commercial_use"]),
        status=rec["status"],
        license_check=rec["license_check"],
        license_checked=rec.get("license_checked"),
        reason=rec.get("reason"),
        zenodo_record=str(loc["zenodo_record"]) if loc.get("zenodo_record") else None,
        uci_id=int(loc["uci_id"]) if loc.get("uci_id") else None,
        repo=loc.get("repo"),
        urls=tuple(loc.get("urls") or ()),
        zenodo_files=tuple(loc.get("zenodo_files") or ()),
        zip_members=tuple((g, int(n)) for g, n in loc.get("zip_members") or ()),
        approx_size_mb=rec.get("approx_size_mb", 0),
        notes=rec.get("notes", ""),
        used_by=tuple(rec.get("used_by") or ()),
    )


def load(root: Path | None = None) -> dict[str, Source]:
    """All declared datasets by id (active, broken at source and rejected)."""
    return {rec["id"]: to_source(topic, rec) for topic, rec in declarations(root)}


def __getattr__(name: str):
    # SOURCES: usable datasets (active or broken at source); REJECTED: id -> reason
    if name == "SOURCES":
        return {k: s for k, s in load().items() if s.status != "rejected"}
    if name == "REJECTED":
        return {k: s.reason or "" for k, s in load().items() if s.status == "rejected"}
    raise AttributeError(name)
