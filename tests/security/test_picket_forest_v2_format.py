"""The published examples of picket-forest 0.2.0 follow the documented format picket-forest-v2."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from mobility_model_zoo.release.registry import Registry
from mobility_model_zoo.site import schema_doc

REPO = Path(__file__).resolve().parents[2]


def test_examples_validate_against_the_schema():
    schema = json.loads(
        (REPO / "src/mobility_model_zoo/security/can_ids/picket-forest-v2.schema.json").read_text()
    )
    examples = sorted((REPO / "zoo/models/picket-forest/examples").glob("*.json"))
    assert len(examples) >= 3
    for path in examples:
        example = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(example)
        assert len(example["expected_scores"]) == len(example["frames"]), path.name
        assert all(0 <= i < len(example["frames"]) for i in example["expected_alarms"]), path.name
        assert example["expected_alarms"] == sorted(example["expected_alarms"]), path.name


def test_format_documentation_matches_the_schema():
    fmt = schema_doc.output_format(Registry(REPO), "picket-forest-v2")  # raises B5 on a mismatch
    assert fmt is not None and fmt["produced_by"]


def test_model_page_shows_the_device_examples():
    from mobility_model_zoo.site import examples

    reg = Registry(REPO)
    fmt = schema_doc.output_format(reg, "picket-forest-v2")
    shown = examples.device(reg, "picket-forest", "0.2.0", fmt["schema"])
    assert [e["file"] for e in shown] == ["01-fabrication.json", "02-dos.json", "03-fuzzing.json"]
    for e in shown:
        assert e["device"] and e["what"]["kind"] == "frames" and e["what"]["shown"] == examples.HEAD
        assert json.loads(e["json"])["expected_alarms"]
        assert e["url"].endswith(
            f"/blob/picket-forest/v0.2.0/zoo/models/picket-forest/examples/{e['file']}"
        )
