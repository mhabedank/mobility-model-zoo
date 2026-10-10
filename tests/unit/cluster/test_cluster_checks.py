"""Deterministic checks of a result (feature 009, T014)."""

import copy

from mobility_model_zoo.productdev.jtbd.cluster.checks import check_result, passed


def names(checks, failed_only=True):
    return {c["name"] for c in checks if not failed_only or not c["passed"]}


def quotes_of(result):
    return {i["item_id"]: i["quote"] for i in result["items"]}


def test_valid_result_passes(basic_result):
    checks = check_result(basic_result, quotes_of(basic_result))
    assert passed(checks), [c for c in checks if not c["passed"]]
    assert names(checks, failed_only=False) == {
        "schema", "every_item_in_exactly_one_group", "quotes_identical_to_input",
        "group_single_kind", "representative_is_member", "group_aggregates"}


def test_changed_quote_fails(basic_result):
    original = quotes_of(basic_result)
    broken = copy.deepcopy(basic_result)
    broken["items"][0]["quote"] += " (edited)"
    checks = check_result(broken, original)
    assert names(checks) == {"quotes_identical_to_input"}
    assert check_result(broken, None)[2].get("skipped")


def test_item_in_two_groups_fails(basic_result):
    broken = copy.deepcopy(basic_result)
    stolen = broken["groups"][0]["members"][0]
    broken["groups"][1]["members"].append(stolen)
    failed = names(check_result(broken, quotes_of(basic_result)))
    assert "every_item_in_exactly_one_group" in failed


def test_mixed_kind_group_fails(basic_result):
    broken = copy.deepcopy(basic_result)
    group = broken["groups"][0]
    other = next(i for i in broken["items"] if i["kind"] != group["kind"])
    other_group = next(g for g in broken["groups"] if g["group_id"] == other["group_id"])
    other_group["members"].remove(other["item_id"])
    group["members"].append(other["item_id"])
    other["group_id"] = group["group_id"]
    failed = names(check_result(broken, quotes_of(basic_result)))
    assert "group_single_kind" in failed
    assert "group_aggregates" in failed


def test_wrong_counts_and_representative_fail(basic_result):
    broken = copy.deepcopy(basic_result)
    broken["groups"][0]["counts"]["mentions"] += 1
    broken["groups"][1]["representative"] = broken["groups"][2]["members"][0]
    failed = names(check_result(broken, quotes_of(basic_result)))
    assert {"group_aggregates", "representative_is_member"} <= failed


def test_schema_violation_fails(basic_result):
    broken = copy.deepcopy(basic_result)
    broken["groups"][0]["group_id"] = "group-1"
    assert "schema" in names(check_result(broken, quotes_of(basic_result)))
