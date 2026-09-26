from jtbd_pilot.checks import check_output, has_quantity

RULES = ["irrelevant_no_items", "enum_values", "quantified_has_quantity"]
TEXT = "Fast die Hälfte der Ladesäulen war defekt. I waited forever."


def item(**kw):
    base = {"kind": "pain", "quote": "I waited forever.", "actor": "driver",
            "actor_type": "individual", "statement": "Long waits.", "evidence_type": "anecdote",
            "evidence_scope": "single"}
    base.update(kw)
    return base


def by_check(rows):
    return {(r["check"], r.get("item_index")): r["passed"] for r in rows}


def test_schema_valid_fails_on_non_json_and_missing_field():
    assert by_check(check_output("c", None, TEXT, RULES))[("schema_valid", None)] is False
    bad = {"relevant": True, "items": [{k: v for k, v in item().items() if k != "actor"}]}
    assert by_check(check_output("c", bad, TEXT, RULES))[("schema_valid", None)] is False


def test_irrelevant_with_items_fails():
    rows = check_output("c", {"relevant": False, "items": [item()]}, TEXT, RULES)
    assert by_check(rows)[("consistency.irrelevant_no_items", None)] is False


def test_quantified_needs_quantity():
    ok = item(quote="Fast die Hälfte der Ladesäulen war defekt.", evidence_scope="quantified")
    bad = item(evidence_scope="quantified")
    rows = by_check(check_output("c", {"relevant": True, "items": [ok, bad]}, TEXT, RULES))
    assert rows[("consistency.quantified_has_quantity", 0)] is True
    assert rows[("consistency.quantified_has_quantity", 1)] is False
    assert has_quantity("63% of couriers") and has_quantity("twice a week")


def test_enum_values_catch_unknown():
    doc = {"relevant": True, "items": [item(kind="wish")]}
    rows = by_check(check_output("c", doc, TEXT, RULES))
    assert rows[("consistency.enum_values", 0)] is False
    assert rows[("schema_valid", None)] is False


def test_quote_verbatim():
    rows = by_check(check_output("c", {"relevant": True, "items": [item(quote="I waited long.")]},
                                 TEXT, RULES))
    assert rows[("quote_verbatim", 0)] is False
