"""The packaged format schemas equal the contracts (feature 009, T010)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "specs" / "009-jtbd-dedup-cluster" / "contracts"
PACKAGE = ROOT / "src" / "mobility_model_zoo" / "productdev" / "jtbd" / "cluster"
PAIRS = [("cluster-input.schema.json", "jtbd-cluster-input-v1.schema.json"),
         ("cluster-output.schema.json", "jtbd-cluster-v1.schema.json")]


@pytest.mark.parametrize(("contract", "packaged"), PAIRS)
def test_packaged_schema_equals_contract(contract, packaged):
    assert (PACKAGE / packaged).read_bytes() == (CONTRACTS / contract).read_bytes()
    Draft202012Validator.check_schema(json.loads((PACKAGE / packaged).read_text()))


def test_output_schema_pins_version_and_ids():
    schema = json.loads((PACKAGE / "jtbd-cluster-v1.schema.json").read_text())
    assert schema["properties"]["output_format_version"] == {"const": "jtbd-cluster-v1"}
    defs = schema["$defs"]
    assert defs["item_id"]["pattern"] == "^it-[0-9a-f]{12}$"
    assert defs["group_id"]["pattern"] == "^dg-[0-9]{6}$"
    assert defs["cluster_id"]["pattern"] == "^cl-[0-9]{6}$"
