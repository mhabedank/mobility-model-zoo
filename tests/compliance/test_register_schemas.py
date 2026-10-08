"""Every register schema accepts a valid example and rejects the documented violations."""

import json
from pathlib import Path

import pytest
from compliance_helpers import controller, decision, route, source, source_class
from jsonschema import Draft202012Validator

from mobility_model_zoo.compliance.register import SCHEMA_DIR, schema

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "specs" / "006-compliance-harness" / "contracts" / "schemas"


def errors(stem, data):
    return list(Draft202012Validator(schema(stem)).iter_errors(data))


def test_contract_copies_identical():
    packaged = sorted(p.name for p in SCHEMA_DIR.glob("*.schema.json"))
    assert packaged == sorted(p.name for p in CONTRACT.glob("*.schema.json"))
    for name in packaged:
        assert (SCHEMA_DIR / name).read_bytes() == (CONTRACT / name).read_bytes(), name


def test_schemas_are_valid():
    for path in SCHEMA_DIR.glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text()))


def test_valid_examples():
    assert not errors("controller", controller())
    assert not errors("source-classes", {"classes": [source_class()]})
    assert not errors("sources", {"sources": [source()]})
    assert not errors("providers", {"routes": [route()]})
    assert not errors("decisions", {"decisions": [decision()]})


@pytest.mark.parametrize(
    "stem,data",
    [
        ("sources", {"sources": [source(permitted_use="always")]}),
        ("sources", {"sources": [source(redistribution="maybe")]}),
        ("sources", {"sources": [source(licence="CC-BY-NC-4.0")]}),  # NC must be benchmark_only
        ("sources", {"sources": [source(quote_allowed=True, licence="MIT")]}),
        ("source-classes", {"classes": [{**source_class(), "copyright_basis": "tdm_60d"}]}),  # D5
        ("source-classes", {"classes": [{**source_class(), "art9_handling": "allowed_by_decision"}]}),
        ("providers", {"routes": [route(access_path="browser")]}),
        ("providers", {"routes": [route(access_path="consumer_cli", allowed_for=["reference"])]}),
        (
            "waivers",
            {
                "waivers": [
                    {
                        "id": "w",
                        "check": "C-I1",
                        "scope": "s",
                        "rationale": "r",
                        "approved_by": "o",
                        "approved_at": "2026-10-08",
                    }
                ]
            },
        ),  # no expires_at
        (
            "waivers",
            {
                "waivers": [
                    {
                        "id": "w",
                        "check": "I1",
                        "scope": "s",
                        "rationale": "r",
                        "approved_by": "o",
                        "approved_at": "2026-10-08",
                        "expires_at": "2026-12-01",
                    }
                ]
            },
        ),  # id without C- prefix
        (
            "requests",
            {
                "requests": [
                    {
                        "id": "r",
                        "type": "complaint",
                        "received_at": "2026-10-08",
                        "deadline": "2026-11-08",
                        "identifier_hash": "0" * 64,
                        "stores_searched": [],
                        "action": "",
                        "suppression_added": False,
                        "answered_at": None,
                    }
                ]
            },
        ),
        ("controller", {**controller(), "commercial_activity": "consulting"}),
    ],
)
def test_invalid_examples(stem, data):
    assert errors(stem, data)
