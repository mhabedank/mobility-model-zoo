"""Labeler schemas of pilot-v3 (feature 025, T011)."""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml
from pydantic import ValidationError

from mobility_model_zoo.productdev.jtbd.v3 import schema as v3

REPO = Path(__file__).resolve().parents[3]
CONTRACTS = REPO / "specs/025-pilot-v3-benchmark/contracts"
BRIEF = yaml.safe_load(
    (REPO / "topics/productdev/guideline/scout-v3/brief.yaml").read_text(encoding="utf-8")
)
SPAN_V2 = json.loads(
    (REPO / "src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v2.schema.json").read_text(
        encoding="utf-8"
    )
)


def _keys(node):
    if isinstance(node, dict):
        yield from node.keys()
        for value in node.values():
            yield from _keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _keys(value)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_wire_schema_equals_contract_and_has_no_text(n):
    contract = json.loads((CONTRACTS / f"labeler-pass{n}.schema.json").read_text(encoding="utf-8"))
    contract.pop("$schema")
    contract.pop("$id")
    assert v3.wire_schema(n) == contract
    assert not {"title", "description"} & set(_keys(v3.wire_schema(n)))
    assert len(v3.labeler_schema_sha256(n)) == 64


def test_value_lists_follow_the_brief():
    assert v3.MODES == tuple(BRIEF["mode"]["values"])
    assert v3.IMPROVE == tuple(BRIEF["improve"]["values"])


def test_models_reject_unknown_values_and_keys():
    v3.Pass1Answer.model_validate({"relevant": False, "items": []})
    with pytest.raises(ValidationError):
        v3.Pass1Answer.model_validate(
            {
                "relevant": True,
                "items": [
                    {
                        "kind": "wish",
                        "quote": "x",
                        "actor_type": "individual",
                        "evidence_type": "opinion",
                        "evidence_scope": "single",
                    }
                ],
            }
        )
    with pytest.raises(ValidationError):
        v3.Pass2Answer.model_validate(
            {
                "items": [
                    {
                        "index": 0,
                        "job_kind": None,
                        "mode": ["rocket"],
                        "improve": [],
                        "states_solution": False,
                        "executor_role": None,
                        "situation": None,
                    }
                ]
            }
        )
    with pytest.raises(ValidationError):
        v3.Pass3Answer.model_validate({"links": [{"from": 0, "to": 1, "relation": "after"}]})
    with pytest.raises(ValidationError):
        v3.Pass3Answer.model_validate({"links": [], "extra": 1})


def _answers():
    p1 = v3.Pass1Answer.model_validate(
        {
            "relevant": True,
            "items": [
                {
                    "kind": "pain",
                    "quote": "Der Bus kommt nie",
                    "actor_type": "individual",
                    "evidence_type": "routine",
                    "evidence_scope": "single",
                },
                {
                    "kind": "gain",
                    "quote": "ein Bus jede Stunde",
                    "actor_type": "individual",
                    "evidence_type": "opinion",
                    "evidence_scope": "single",
                },
            ],
        }
    )
    p2 = v3.Pass2Answer.model_validate(
        {
            "items": [
                {
                    "index": 0,
                    "job_kind": None,
                    "mode": ["bus"],
                    "improve": ["reliability"],
                    "states_solution": False,
                    "executor_role": None,
                    "situation": "im Dorf",
                },
                {
                    "index": 1,
                    "job_kind": None,
                    "mode": ["bus"],
                    "improve": ["access"],
                    "states_solution": True,
                    "executor_role": None,
                    "situation": None,
                },
            ]
        }
    )
    p3 = v3.Pass3Answer.model_validate({"links": []})
    return p1, p2, p3


def test_merge_maps_onto_jtbd_span_v2():
    text = "Der Bus kommt nie im Dorf. Ich will ein Bus jede Stunde."
    merged = v3.merge(*_answers())
    assert [i["mode"] for i in merged["items"]] == [["bus"], ["bus"]]
    # Code adds offsets, scores and the language; the result must be a valid jtbd-span-v2 output.
    for item in merged["items"]:
        start = text.index(item["quote"])
        item.update(start=start, end=start + len(item["quote"]), score=1.0)
        for key in ("executor_role", "situation"):
            if item[key] is not None:
                pos = text.index(item[key])
                item[key] = {"text": item[key], "start": pos, "end": pos + len(item[key])}
    output = {
        "output_format_version": "jtbd-span-v2",
        "language": "de",
        "relevance_probability": 1.0,
        "dimensions": list(v3.DIMENSIONS),
        "relations": list(v3.RELATION_FIELDS),
        **merged,
    }
    jsonschema.validate(output, SPAN_V2)


def test_merge_without_pass2_or_pass3():
    p1, _, _ = _answers()
    merged = v3.merge(p1, None, None)
    assert merged["links"] == [] and all(i["mode"] == [] for i in merged["items"])
    assert all(i["executor_role"] is None and i["states_solution"] is False for i in merged["items"])


def test_merge_refuses_unknown_index():
    p1, p2, _ = _answers()
    bad = v3.Pass2Answer.model_validate({"items": [dict(p2.items[0].model_dump(), index=5)]})
    with pytest.raises(ValueError):
        v3.merge(p1, bad, None)
