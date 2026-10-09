"""F1 and F4: the site prints the numbers of the release, formatted exactly as on the model card."""

from __future__ import annotations

import json

from site_fixture import MODEL, VERSION

from mobility_model_zoo.site import check


def test_site_facts_match_sources_and_card(built):
    assert list(check.check_facts(built.reg, built.out)) == []
    assert list(check.check_card_parity(built.reg, built.out)) == []


def test_changed_source_value_is_f1(built):
    path = built.root / f"zoo/models/{MODEL}/results/{VERSION}/quality.json"
    data = json.loads(path.read_text())
    next(m for m in data["metrics"] if m["name"] == "comparison_composite")["value"] = 0.5
    path.write_text(json.dumps(data))
    found = list(check.check_facts(built.reg, built.out))
    assert any(f[0] == "F1" and "comparison_composite" in f[2] for f in found)


def test_number_not_on_the_card_is_f4(built):
    path = built.out / "_build" / "facts.json"
    rows = json.loads(path.read_text())
    rows[0]["value"] = "123.456"
    path.write_text(json.dumps(rows))
    assert any(f[0] == "F4" for f in check.check_card_parity(built.reg, built.out))
