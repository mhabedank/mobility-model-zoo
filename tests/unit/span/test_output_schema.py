"""The packaged jtbd-span-v1 schema equals the contract and enforces its rules (T006)."""

import copy
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "specs/004-production-span-model/contracts/span-output.schema.json"
PACKAGED = ROOT / "src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v1.schema.json"

VALID = {
    "output_format_version": "jtbd-span-v1",
    "relevant": True,
    "relevance_probability": 0.8,
    "dimensions": ["actor_type"],
    "items": [{"kind": "pain", "quote": "Bus", "start": 0, "end": 3, "score": 0.9,
               "actor_type": "individual"}],
}


def schema():
    return json.loads(PACKAGED.read_text())


def test_packaged_schema_equals_contract():
    assert PACKAGED.read_bytes() == CONTRACT.read_bytes()


def test_valid_example_validates():
    jsonschema.validate(VALID, schema())


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(extra=1),
    lambda d: d["items"][0].update(extra=1),
    lambda d: d.update(output_format_version="jtbd-span-v2"),
    lambda d: d["items"][0].update(kind="wish"),
    lambda d: d["items"][0].pop("quote"),
    lambda d: d.update(dimensions=["actor"]),
], ids=["extra-top", "extra-item", "version", "kind", "no-quote", "dimension"])
def test_invalid_examples_fail(mutate):
    doc = copy.deepcopy(VALID)
    mutate(doc)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, schema())
