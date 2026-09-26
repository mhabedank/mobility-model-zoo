import json

import jsonschema
import pytest
from pydantic import ValidationError

from jtbd_pilot.schema import ExtractionOutput, evidence_rank, wire_schema

IGNORED = {"title", "description", "$schema", "$id"}


def _norm(node):
    if isinstance(node, dict):
        out = {k: _norm(v) for k, v in node.items() if k not in IGNORED}
        if "enum" in out:
            out.pop("type", None)
        return out
    if isinstance(node, list):
        return [_norm(v) for v in node]
    return node


def test_wire_schema_equals_contract(contracts_dir):
    contract = json.loads((contracts_dir / "extraction-output.schema.json").read_text())
    assert _norm(wire_schema()) == _norm(contract)


def test_empty_items_is_valid(contracts_dir):
    doc = {"relevant": True, "items": []}
    ExtractionOutput.model_validate(doc)
    jsonschema.validate(doc, wire_schema())


def test_extra_keys_rejected():
    with pytest.raises(ValidationError):
        ExtractionOutput.model_validate({"relevant": False, "items": [], "persona": "x"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"relevant": False, "items": [], "persona": "x"}, wire_schema())


def test_evidence_rank_is_ordinal():
    assert [evidence_rank(v) for v in
            ("opinion", "anecdote", "routine", "observation", "measurement")] == [0, 1, 2, 3, 4]
