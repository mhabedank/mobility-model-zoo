"""`jtbd cluster collect`: a span run over stored chunks -> an input bundle (research R2, R3).

Needs the `[jtbd]` extra (settings, chunk store, snapshots). Source ids are prefixed with the
config's benchmark version, because chunk ids repeat across data directories. No author field is
written; the thread or page URL without its query string is the independence key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from mobility_model_zoo.productdev.jtbd.cluster.bundle import (
    INPUT_FORMAT_VERSION,
    SPAN_FORMAT_VERSION,
    sha256_hex,
)
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.errors import UsageError
from mobility_model_zoo.productdev.jtbd.jsonio import read_json
from mobility_model_zoo.productdev.jtbd.runs import load_run_manifest, run_dir
from mobility_model_zoo.productdev.jtbd.sources.snapshot import load_snapshot


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def source_lines(settings: Settings, run_id: str) -> list[dict[str, Any]]:
    manifest = load_run_manifest(settings, run_id)
    if manifest.backend != "span":
        raise UsageError(f"run {run_id} has backend {manifest.backend}, not span")
    directory = run_dir(settings, run_id) / "parsed"
    excluded = {e.chunk_id for e in manifest.excluded_chunks}
    origins: dict[str, str] = {}
    lines = []
    for chunk_id, chunk in sorted(chunk_map(settings, manifest.split).items()):
        path = directory / f"{chunk_id}.json"
        if chunk_id in excluded or not path.exists():
            continue
        output = read_json(path)
        if output.get("output_format_version") != SPAN_FORMAT_VERSION:
            raise UsageError(f"{path}: not {SPAN_FORMAT_VERSION}")
        if chunk.snapshot_id not in origins:
            origins[chunk.snapshot_id] = origin_of(load_snapshot(settings, chunk.snapshot_id).origin_url)
        lines.append({
            "input_format_version": INPUT_FORMAT_VERSION,
            "source_id": f"{settings.benchmark_version}:{chunk_id}",
            "source_class": chunk.source_type,
            "date": chunk.date.isoformat(),
            "origin": origins[chunk.snapshot_id],
            "text_sha256": sha256_hex(chunk.text),
            "output": output,
        })
    return lines


def collect(settings: Settings, run_id: str, out: Path) -> dict[str, Any]:
    lines = source_lines(settings, run_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n"
                           for line in lines), encoding="utf-8")
    return {"bundle": str(out), "sources": len(lines),
            "items": sum(len(line["output"]["items"]) for line in lines)}
