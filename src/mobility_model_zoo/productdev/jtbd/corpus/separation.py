"""Training sources never share a source with a benchmark or with spike data (feature 004, R2).

A training snapshot matches a benchmark snapshot (one used by a main or holdout chunk) when they
have the same snapshot ID, the same normalized origin URL or the same raw content hash, or when
one supersedes the other (directly or through a chain). Snapshots used by spike chunks are spike
data and never supply training chunks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from mobility_model_zoo.productdev.jtbd.config import Settings, load_settings
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks
from mobility_model_zoo.productdev.jtbd.errors import UsageError
from mobility_model_zoo.productdev.jtbd.jsonio import read_yaml
from mobility_model_zoo.productdev.jtbd.sources import registry

SPIKE_DATA = Path("data/spike")


def normalize_url(url: str) -> str:
    """Canonical URL without scheme and `www.` (http and https count as the same source)."""
    parts = urlsplit(registry.canonicalize_url(url))
    host = parts.netloc.removeprefix("www.")
    return f"{host}{parts.path}" + (f"?{parts.query}" if parts.query else "")


@dataclass
class SourceSet:
    direct_ids: set[str] = field(default_factory=set)  # the snapshots themselves
    snapshot_ids: set[str] = field(default_factory=set)  # plus their supersession family
    urls: set[str] = field(default_factory=set)
    hashes: set[str] = field(default_factory=set)


def _snapshot_meta(settings: Settings, snapshot_id: str) -> dict:
    path = settings.snapshots_dir / snapshot_id / "source.yaml"
    return read_yaml(path) if path.exists() else {}


def supersession_family(settings: Settings, snapshot_ids: set[str]) -> set[str]:
    """`snapshot_ids` plus every snapshot linked to them by `supersedes`, in both directions."""
    links: dict[str, set[str]] = {}
    for entry in registry.entries(settings):
        old = entry.get("supersedes")
        if old:
            links.setdefault(entry["snapshot_id"], set()).add(old)
            links.setdefault(old, set()).add(entry["snapshot_id"])
    family, todo = set(snapshot_ids), list(snapshot_ids)
    while todo:
        for other in links.get(todo.pop(), ()):
            if other not in family:
                family.add(other)
                todo.append(other)
    return family


def _urls_by_snapshot(settings: Settings) -> dict[str, str]:
    return {e["snapshot_id"]: e["canonical_url"] for e in registry.entries(settings)}


def source_set(settings: Settings, snapshot_ids: set[str]) -> SourceSet:
    """IDs, URLs and content hashes of `snapshot_ids`, and their supersession family (whose
    members are caught by the supersession rule, so their URLs and hashes are not added)."""
    family = supersession_family(settings, snapshot_ids)
    urls = _urls_by_snapshot(settings)
    found = SourceSet(direct_ids=set(snapshot_ids), snapshot_ids=family)
    for snapshot_id in snapshot_ids:
        meta = _snapshot_meta(settings, snapshot_id)
        for url in (meta.get("origin_url"), urls.get(snapshot_id)):
            if url:
                found.urls.add(normalize_url(url))
        if meta.get("raw_sha256"):
            found.hashes.add(meta["raw_sha256"])
    return found


def benchmark_settings(settings: Settings, exclude_benchmark: str | Path | None = None
                       ) -> Settings:
    path = exclude_benchmark or (settings.span_train or {}).get("exclude_benchmark")
    if not path:
        raise UsageError("no benchmark to exclude: give --exclude-benchmark or set "
                         "span_train.exclude_benchmark in the config")
    path = Path(path)
    return load_settings(path if path.is_absolute() else settings.base / path)


def benchmark_sources(settings: Settings, exclude_benchmark: str | Path | None = None
                      ) -> SourceSet:
    """Sources of every main and holdout chunk of the excluded benchmark."""
    bench = benchmark_settings(settings, exclude_benchmark)
    ids = {c.snapshot_id for c in load_chunks(bench) if c.split in ("main", "holdout")}
    return source_set(bench, ids)


def spike_snapshot_ids(settings: Settings) -> set[str]:
    directory = settings.base / SPIKE_DATA / "chunks"
    if not directory.exists():
        return set()
    return {json.loads(p.read_text(encoding="utf-8"))["snapshot_id"]
            for p in directory.glob("ch-*.json")}


def violations(settings: Settings, snapshot_id: str, benchmark: SourceSet,
               spike_ids: set[str]) -> list[str]:
    """Rules by which `snapshot_id` may not supply training chunks (empty: allowed)."""
    found = []
    own = source_set(settings, {snapshot_id})
    if snapshot_id in benchmark.direct_ids:
        found.append("snapshot_id")
    elif own.snapshot_ids & benchmark.direct_ids:
        found.append("supersession")
    if own.urls & benchmark.urls:
        found.append("origin_url")
    if own.hashes & benchmark.hashes:
        found.append("content_hash")
    if own.snapshot_ids & spike_ids:
        found.append("spike_data")
    return found
