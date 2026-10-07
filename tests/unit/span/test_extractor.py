"""SpanExtractor on the tiny random model (T012)."""

import json
import shutil

import jsonschema
import pytest
from safetensors.torch import load_file, save_file

from mobility_model_zoo.productdev.jtbd.span import SpanExtractor
from mobility_model_zoo.productdev.jtbd.span.extractor import MODEL_FILES, SCHEMA_PATH

TEXT = ("Im Landkreis fährt der letzte Bus um 18 Uhr. Wer abends aus der Stadt zurück will, "
        "muss ein Taxi nehmen. The charger at the depot was broken again; we lost two hours.")


@pytest.fixture(params=[("actor_type", "evidence_type", "evidence_scope"), ("actor_type",), ()],
                ids=["all", "actor-only", "none"])
def dims(request):
    return request.param


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def test_output_is_schema_valid_with_only_produced_dimensions(tiny_span_model, dims, schema):
    model = SpanExtractor.from_pretrained(tiny_span_model(dims))
    out = model.extract(TEXT)
    jsonschema.validate(out, schema)
    assert out["dimensions"] == list(dims) == model.dimensions
    assert out["items"], "the tiny model has thresholds 0, so every unit is an item"
    for item in out["items"]:
        assert set(item) == {"kind", "quote", "start", "end", "score", *dims}
        assert item["quote"] == TEXT[item["start"]:item["end"]]
    starts = [i["start"] for i in out["items"]]
    assert starts == sorted(starts)
    assert all(a["end"] <= b["start"] for a, b in zip(out["items"], out["items"][1:], strict=False))


def test_extract_is_deterministic(tiny_span_model):
    model = SpanExtractor.from_pretrained(tiny_span_model())
    assert model.extract(TEXT) == model.extract(TEXT)


def test_save_and_load_round_trip(tiny_span_model, tmp_path):
    model = SpanExtractor.from_pretrained(tiny_span_model())
    model.save_pretrained(tmp_path / "copy")
    assert SpanExtractor.from_pretrained(tmp_path / "copy").extract(TEXT) == model.extract(TEXT)
    names = {p.name for p in (tmp_path / "copy").iterdir()}
    assert names <= MODEL_FILES
    assert {"model.safetensors", "config.json", "span_config.json", "tokenizer.json"} <= names
    assert not any(n.endswith((".pt", ".bin", ".pkl")) for n in names)


def test_extra_attribute_head_raises(tiny_span_model, tmp_path):
    work = shutil.copytree(tiny_span_model(("actor_type",)), tmp_path / "bad")
    state = load_file(str(work / "model.safetensors"))
    state["heads.attrs.evidence_scope.weight"] = state["heads.attrs.actor_type.weight"][:3].clone()
    state["heads.attrs.evidence_scope.bias"] = state["heads.attrs.actor_type.bias"][:3].clone()
    save_file(state, str(work / "model.safetensors"))
    with pytest.raises(ValueError, match="attribute heads"):
        SpanExtractor.from_pretrained(work)


def test_unknown_output_format_raises(tiny_span_model, tmp_path):
    work = shutil.copytree(tiny_span_model(), tmp_path / "bad")
    config = json.loads((work / "span_config.json").read_text())
    (work / "span_config.json").write_text(json.dumps({**config,
                                                       "output_format_version": "jtbd-span-v9"}))
    with pytest.raises(ValueError, match="output_format_version"):
        SpanExtractor.from_pretrained(work)


@pytest.mark.parametrize("text", ["", "   \n\t "])
def test_empty_text_is_irrelevant_and_empty(tiny_span_model, text):
    out = SpanExtractor.from_pretrained(tiny_span_model()).extract(text)
    assert out["relevant"] is False and out["items"] == [] and out["relevance_probability"] == 0.0


def test_long_text_over_several_windows(tiny_span_model, schema):
    text = " ".join([TEXT] * 120)  # about 20,000 characters
    assert len(text) > 19_000
    out = SpanExtractor.from_pretrained(tiny_span_model()).extract(text)
    jsonschema.validate(out, schema)
    assert len(out["items"]) == 4 * 120  # four units per copy of TEXT
    assert all(i["quote"] == text[i["start"]:i["end"]] for i in out["items"])


def test_high_thresholds_give_an_empty_valid_result(tiny_span_model, tmp_path, schema):
    work = shutil.copytree(tiny_span_model(), tmp_path / "strict")
    config = json.loads((work / "span_config.json").read_text())
    config["thresholds"] = {"unit": 1.01, "relevance": 1.01}
    (work / "span_config.json").write_text(json.dumps(config))
    out = SpanExtractor.from_pretrained(work).extract(TEXT)
    jsonschema.validate(out, schema)
    assert out["relevant"] is False and out["items"] == []
