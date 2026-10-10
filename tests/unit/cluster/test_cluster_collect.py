"""`jtbd cluster collect`: span run over stored chunks -> bundle (feature 009, T021)."""

import json
from datetime import UTC, datetime

import pytest
from helpers import copy_fixture, pilot

from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundle, sha256_hex
from mobility_model_zoo.productdev.jtbd.cluster.collect import origin_of
from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.freeze import load_manifest, schema_sha256
from mobility_model_zoo.productdev.jtbd.jsonio import write_json
from mobility_model_zoo.productdev.jtbd.schema import LabelRunManifest, RunSettings
from mobility_model_zoo.productdev.jtbd.sources.snapshot import load_snapshot

RUN = "run-student-span-main-cluster"


def write_span_run(settings, span=True):
    """First sentence of every chunk as one pain item, as a span model would return it."""
    frozen = load_manifest(settings)
    directory = settings.runs_dir / RUN
    for chunk_id, chunk in chunk_map(settings, "main").items():
        end = next((i + 1 for i, ch in enumerate(chunk.text) if ch in ".!?"), len(chunk.text))
        output = {"output_format_version": "jtbd-span-v1", "relevant": True,
                  "relevance_probability": 0.8, "dimensions": [],
                  "items": [{"kind": "pain", "quote": chunk.text[:end], "start": 0, "end": end,
                             "score": 0.7}]}
        write_json(directory / "parsed" / f"{chunk_id}.json", output)
    run_settings = {"dimensions": [], "model_sha256": "a" * 64} if span else {}
    manifest = LabelRunManifest(
        run_id=RUN, role="student" if span else "baseline", backend="span" if span else "mock",
        model_id="scout-large", model_version="a" * 12, family="xlm-roberta", host="local",
        settings=RunSettings(temperature=0.0, structured_output="post_validation", **run_settings),
        guideline_sha256=frozen["hashes"]["guideline"], schema_sha256=schema_sha256(),
        criteria_sha256=frozen["hashes"]["criteria"], split="main",
        started_at=datetime.now(UTC), finished_at=datetime.now(UTC), status="complete")
    write_json(directory / "manifest.json", manifest.model_dump(mode="json"))


@pytest.fixture
def config(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    write_span_run(load_settings(config))
    return config


def test_origin_drops_query_and_fragment():
    assert origin_of("https://forum.example/t/9?page=2#post-4") == "https://forum.example/t/9"


def test_collect_writes_a_valid_bundle(config, tmp_path):
    out = tmp_path / "bundle.jsonl"
    summary = pilot(config, "cluster", "collect", "--run", RUN, "--out", str(out))
    settings = load_settings(config)
    chunks = chunk_map(settings, "main")
    assert summary == {"bundle": str(out), "sources": len(chunks), "items": len(chunks)}
    sources = {s.source_id: s for s in read_bundle(out)}
    for chunk_id, chunk in chunks.items():
        source = sources[f"mini-v1:{chunk_id}"]
        assert source.source_class == chunk.source_type
        assert source.date == chunk.date.isoformat()
        assert source.text_sha256 == sha256_hex(chunk.text)
        assert source.origin == origin_of(load_snapshot(settings, chunk.snapshot_id).origin_url)
    assert "author" not in out.read_text()
    first = json.loads(out.read_text().splitlines()[0])
    assert first["output"]["output_format_version"] == "jtbd-span-v1"


def test_collect_refuses_a_non_span_run(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    write_span_run(load_settings(config), span=False)
    pilot(config, "cluster", "collect", "--run", RUN, "--out", str(tmp_path / "b.jsonl"), expect=2)


def test_extract_writes_a_span_run_that_collect_reads(tmp_path, tiny_span_model):
    """`jtbd cluster extract` (T063): a pool run without a candidate registry or frozen benchmark."""
    config = copy_fixture(tmp_path)
    model = tiny_span_model(())
    summary = pilot(config, "cluster", "extract", "--model-dir", str(model))
    settings = load_settings(config)
    assert summary["chunks"] == len(chunk_map(settings, "main"))
    run = summary["run_id"]
    assert run.startswith("run-student-scout-large-pool-")
    out = tmp_path / "pool.jsonl"
    assert pilot(config, "cluster", "collect", "--run", run, "--out", str(out))["sources"] == \
        summary["chunks"]
    pilot(config, "cluster", "extract", "--model-dir", str(model), "--split", "holdout", expect=1)
