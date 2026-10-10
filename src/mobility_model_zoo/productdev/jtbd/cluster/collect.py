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


def extract(settings: Settings, model_dir: Path, split: str = "main") -> dict[str, Any]:
    """`jtbd cluster extract`: run a released span model over the stored chunks of one split and
    write a span run for the benchmark pool (task T063). Unlike `jtbd span label` it registers no
    candidate and needs no frozen extraction benchmark: the run is pool input, not an evaluation."""
    import platform
    from datetime import UTC, datetime

    from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
    from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
    from mobility_model_zoo.productdev.jtbd.jsonio import write_json
    from mobility_model_zoo.productdev.jtbd.schema import LabelRunManifest, RunSettings
    from mobility_model_zoo.productdev.jtbd.span.evaluate import MODEL_ID, model_sha256
    from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor

    if split == "holdout":
        raise ValidationFailed("the holdout split never enters the cluster pool")
    sha = model_sha256(model_dir)
    run_id = f"run-student-{MODEL_ID}-pool-{sha[:12]}-{split}"
    run_path = settings.runs_dir / run_id
    chunks = chunk_map(settings, split)
    extractor = SpanExtractor.from_pretrained(model_dir)
    started = datetime.now(UTC)
    for chunk_id, chunk in sorted(chunks.items()):
        path = run_path / "parsed" / f"{chunk_id}.json"
        if not path.exists():  # resumable
            write_json(path, extractor.extract(chunk.text))
    manifest = LabelRunManifest(
        run_id=run_id, role="student", backend="span", model_id=MODEL_ID, model_version=sha[:12],
        family="xlm-roberta", host=platform.node() or "local",
        settings=RunSettings(temperature=0.0, structured_output="post_validation", max_retries=0,
                             dimensions=extractor.dimensions, model_sha256=sha,
                             thresholds=extractor.thresholds),
        guideline_sha256="-", schema_sha256="-", criteria_sha256="-", split=split,
        started_at=started, finished_at=datetime.now(UTC), status="complete",
        deviations=["cluster pool run (feature 009, T063): not an evaluation of the model"])
    data = manifest.model_dump(mode="json")
    data["settings"] = {k: v for k, v in data["settings"].items() if v is not None}
    write_json(run_path / "manifest.json", data)
    return {"run_id": run_id, "chunks": len(chunks), "model_sha256": sha}
