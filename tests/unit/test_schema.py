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


@pytest.mark.parametrize("path", [
    "configs/decision-criteria.yaml",
    "specs/001-jtbd-extraction-pilot/contracts/decision-criteria.example.yaml",
    "tests/fixtures/mini-corpus/decision-criteria.yaml",
])
def test_decision_criteria_match_contract(contracts_dir, path):
    import yaml

    from jtbd_pilot.schema import DecisionCriteria

    doc = yaml.safe_load((contracts_dir.parents[2] / path).read_text())
    contract = json.loads((contracts_dir / "decision-criteria.schema.json").read_text())
    jsonschema.validate(doc, contract)
    DecisionCriteria.model_validate(doc)


def test_ensemble_orders_must_be_permutations_of_members(contracts_dir):
    import yaml

    from jtbd_pilot.schema import DecisionCriteria

    doc = yaml.safe_load((contracts_dir / "decision-criteria.example.yaml").read_text())
    doc["teacher_ensemble"]["quote_priority"] = doc["teacher_ensemble"]["quote_priority"][:-1]
    with pytest.raises(ValidationError, match="quote_priority"):
        DecisionCriteria.model_validate(doc)


def test_ensemble_manifest_rules():
    from jtbd_pilot.schema import LabelRunManifest

    base = {"run_id": "r", "role": "teacher_candidate", "backend": "ensemble", "model_id": "e",
            "model_version": "a+b", "family": "ensemble", "host": "local",
            "settings": {"temperature": 0, "structured_output": "post_validation"},
            "guideline_sha256": "0" * 64, "schema_sha256": "0" * 64, "criteria_sha256": "0" * 64,
            "split": "main", "started_at": "2026-10-01T00:00:00Z", "license_basis": "MIT"}
    LabelRunManifest.model_validate({**base, "derived_from": ["r1", "r2"]})
    with pytest.raises(ValidationError, match="derived_from"):
        LabelRunManifest.model_validate(base)
    with pytest.raises(ValidationError, match="role teacher_candidate"):
        LabelRunManifest.model_validate({**base, "role": "baseline", "license_basis": None,
                                         "derived_from": ["r1", "r2"]})
