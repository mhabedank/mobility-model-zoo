import json

import pytest
import yaml
from helpers import copy_fixture, pilot, run_ids

from jtbd_pilot.config import load_settings
from jtbd_pilot.corpus.autochunk import cut_ranges, usable
from jtbd_pilot.corpus.store import load_chunks, save_chunk
from jtbd_pilot.jsonio import read_jsonl
from jtbd_pilot.sources.snapshot import create_snapshot

PROSE = ("Die Buslinie im Landkreis fährt nur zweimal am Tag. Viele Pendler nehmen deshalb das Auto. "
         * 60)


def test_cut_ranges_respects_bounds_and_sentences():
    ranges = cut_ranges(PROSE * 3)
    assert len(ranges) >= 3
    for start, end in ranges:
        assert 1400 <= end - start <= 5800
        assert (PROSE * 3)[start:end].rstrip().endswith(".")
    assert usable(PROSE[:3000])
    assert not usable("doi:10.1/x https://a et al. 2020 " * 100)


def _spike_config(tmp_path):
    config = copy_fixture(tmp_path)
    data = yaml.safe_load(config.read_text())
    data["pilot"]["spike"] = True
    config.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    models = config.parent / "models.yaml"
    models.write_text(models.read_text() + (
        "- model_id: mock-teacher\n  family: fam-t\n  backend: mock\n  host: local\n"
        "  role: teacher_candidate\n  license_basis: Apache-2.0\n"))
    return config


def test_autochunk_enforces_permitted_uses(tmp_path):
    config = _spike_config(tmp_path)
    settings = load_settings(config)
    for chunk in load_chunks(settings):
        (settings.chunks_dir / f"{chunk.chunk_id}.json").unlink()
    meta = {"source_type": "paper", "license": "x", "legal_basis": "x", "access_terms_checked": "x",
            "retention_until": "2028-01-01"}
    ok = create_snapshot(settings, PROSE.encode() * 4, "txt", "https://e.org/a",
                         {**meta, "permitted_uses": "training_allowed"})
    bench = create_snapshot(settings, PROSE.encode() * 3 + b" Ende.", "txt", "https://e.org/b",
                            {**meta, "permitted_uses": "benchmark_only"})
    base = {"sub_area": "public_transport_rural", "language": "de", "region": "DACH",
            "country": "DE", "date": "2025-01-01"}
    snap_map = tmp_path / "map.yaml"
    snap_map.write_text(yaml.safe_dump({"snapshots": {
        bench["snapshot_id"]: {**base, "use": "train"}}}))
    pilot(config, "corpus", "autochunk", "--map", str(snap_map), "--train", "2", "--eval", "0",
          "--seed", "1", expect=1)
    snap_map.write_text(yaml.safe_dump({"snapshots": {
        ok["snapshot_id"]: {**base, "use": "train"}, bench["snapshot_id"]: {**base, "use": "eval"}}}))
    result = pilot(config, "corpus", "autochunk", "--map", str(snap_map), "--train", "2",
                   "--eval", "1", "--seed", "1")
    assert result["train"] == 2 and result["main"] == 1
    chunks = load_chunks(settings)
    assert {c.snapshot_id for c in chunks if c.split == "train"} == {ok["snapshot_id"]}
    assert {c.snapshot_id for c in chunks if c.split == "main"} == {bench["snapshot_id"]}


def test_single_reference_scoring_and_sft_export(tmp_path):
    config = _spike_config(tmp_path)
    settings = load_settings(config)
    # ch-005 becomes a training chunk; the teacher answers like mock-a
    chunk = {c.chunk_id: c for c in load_chunks(settings)}["ch-005"]
    chunk.split = "train"
    save_chunk(settings, chunk)
    teacher_dir = config.parent / "mock" / "mock-teacher"
    teacher_dir.mkdir()
    answer = json.loads((config.parent / "mock" / "mock-a" / "ch-005.json").read_text())
    answer["items"].append({**answer["items"][0], "quote": "not in the text at all"})
    (teacher_dir / "ch-005.json").write_text(json.dumps(answer))

    pilot(config, "freeze")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a")
    ref = run_ids(config)["mock-a"]
    pilot(config, "consensus", "--single", ref)
    pilot(config, "freeze", "--benchmark")
    pilot(config, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    score = pilot(config, "score", "--run", run_ids(config)["mock-small"])
    assert score["frontier_composite_all_units"] is None
    assert score["dimensions"]["relevance"]["n"] == 4

    pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock", "--model",
          "mock-teacher", "--split", "train")
    out = tmp_path / "sft.jsonl"
    stats = pilot(config, "spike", "export-sft", "--run", run_ids(config)["mock-teacher"],
                  "--out", str(out))
    assert stats["examples"] == 1 and stats["dropped_unverified_items"] == 1
    row = next(read_jsonl(out))
    assert row["prompt"].startswith("<|im_start|>system") and row["prompt"].endswith(
        "<|im_start|>assistant\n")
    assert len(json.loads(row["output"])["items"]) == 2
    report = pilot(config, "spike", "report", "--sft-stats", str(out.with_suffix(".stats.json")))
    text = open(report["report"]).read()
    assert "Technical spike" in text and "mock-small" in text


def test_single_reference_refused_outside_spike(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a")
    pilot(config, "consensus", "--single", run_ids(config)["mock-a"], expect=1)


def test_openai_compat_backend(monkeypatch, tmp_path):
    from jtbd_pilot.config import ModelEntry
    from jtbd_pilot.labeling import openai_compat

    class Resp:
        id, model, usage = "r1", "served", None
        choices = [type("C", (), {"message": type("M", (), {"content": '{"relevant": false, '
                                                            '"items": []}'})()})()]

        def model_dump(self):
            return {"id": "r1"}

    captured = {}

    class Client:
        def __init__(self, base_url, api_key):
            captured["base_url"] = base_url
            self.chat = type("Ch", (), {"completions": type("Co", (), {
                "create": staticmethod(lambda **kw: captured.update(kw) or Resp())})()})()

    monkeypatch.setattr("openai.OpenAI", Client)
    settings = load_settings(copy_fixture(tmp_path))
    entry = ModelEntry(model_id="spike-base", family="qwen", backend="openai_compat", host="spark",
                       role="baseline", api_model="spike-base",
                       extra={"base_url": "http://spark:8000/v1"})
    result = openai_compat.OpenAICompatBackend(settings, entry).call("sys", "text", {"a": 1}, "c1")
    assert result.parsed_candidate == {"relevant": False, "items": []}
    assert captured["base_url"] == "http://spark:8000/v1" and captured["temperature"] == 0
    assert captured["response_format"]["type"] == "json_schema"
    from jtbd_pilot.errors import UsageError

    with pytest.raises(UsageError):
        openai_compat.OpenAICompatBackend(settings, ModelEntry(
            model_id="x", family="q", backend="openai_compat", host="s", role="baseline",
            api_model="x"))


def test_claude_result_event_from_event_list():
    from jtbd_pilot.labeling.claude_cli import result_event

    events = [{"type": "system", "model": "claude-opus-5"},
              {"type": "result", "structured_output": {"a": 1}, "modelUsage": {"claude-opus-5": {}}}]
    assert result_event(events)["structured_output"] == {"a": 1}
    assert result_event({"structured_output": 2})["structured_output"] == 2
