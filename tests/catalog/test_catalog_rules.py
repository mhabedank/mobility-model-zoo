"""Usage rules U1-U6 and K8 (feature 009 research R5, FR-011, T036)."""

from __future__ import annotations

import copy

import pytest

from mobility_model_zoo.catalog import rules
from mobility_model_zoo.catalog.model import licence_allowlist, load

ALLOW = licence_allowlist()


@pytest.fixture
def entry(catalog_dir):
    return copy.deepcopy(load(catalog_dir).entries["pl-stat-transport-tables"])


def _apply(e):
    usage, flags = rules.apply(e, ALLOW, "2026-10-11")
    return usage, flags


def test_u1_signal_withdrawal_and_terms(entry):
    entry["signals"]["tdmrep"] = "deny"
    usage, _ = _apply(entry)
    assert (usage["permitted_use"], usage["redistribution"], usage["rule"]) == (
        "not_usable",
        "not_allowed",
        "U1",
    )
    assert "tdmrep" in usage["rationale"]
    entry["signals"]["tdmrep"] = "absent"
    entry["platform_terms"] = {
        "url": "https://example.org/terms",
        "ml_use": "not_allowed",
        "automated_access": "allowed",
        "checked_at": "2026-10-11",
    }
    assert _apply(entry)[0]["rule"] == "U1"
    entry["platform_terms"] = None
    entry["status"]["value"] = "withdrawn"
    assert _apply(entry)[0]["rule"] == "U1"


@pytest.mark.parametrize("lid", ["unknown", "mixed"])
def test_u2_unknown_or_mixed(entry, lid):
    entry["licence"]["id"] = lid
    usage, flags = _apply(entry)
    assert (usage["permitted_use"], usage["redistribution"], usage["rule"]) == (
        "undetermined",
        "unclear",
        "U2",
    )
    assert flags == []


def test_u3_allowlist_and_share_alike(entry):
    usage, _ = _apply(entry)
    assert (usage["permitted_use"], usage["redistribution"], usage["rule"]) == (
        "training_allowed",
        "allowed",
        "U3",
    )
    assert "share_alike" not in usage
    entry["licence"]["id"] = "CC-BY-SA-4.0"
    assert _apply(entry)[0]["share_alike"] is True


@pytest.mark.parametrize("lid", ["CC-BY-NC-4.0", "CC-BY-ND-4.0", "CC-BY-NC-SA-4.0"])
def test_u4_nc_nd(entry, lid):
    entry["licence"]["id"] = lid
    usage, _ = _apply(entry)
    assert (usage["permitted_use"], usage["redistribution"], usage["rule"]) == (
        "benchmark_only",
        "not_allowed",
        "U4",
    )


def test_u3_skips_licences_that_never_train(entry):
    never = next(item["id"] for item in ALLOW if item.get("trains") is False)
    entry["licence"]["id"] = never
    usage, _ = _apply(entry)
    assert usage["rule"] != "U3" and usage["permitted_use"] != "training_allowed"


@pytest.mark.parametrize(
    ("lid", "rule"), [("CC-BY-SA-3.0-CZ", "U3"), ("CC-BY-2.0-FR", "U3"), ("CC-BY-2.1-JP", "U6")]
)
def test_u3_counts_a_jurisdiction_port_as_its_listed_version(entry, lid, rule):
    entry["licence"]["id"] = lid
    usage, _ = _apply(entry)
    assert usage["rule"] == rule
    if rule == "U3":
        assert usage["permitted_use"] == "training_allowed"


def test_u5_proprietary_with_source_class(entry):
    entry["licence"]["id"] = "LicenseRef-proprietary"
    entry["publisher"]["kind"] = "parliament"
    usage, flags = _apply(entry)
    assert (usage["permitted_use"], usage["rule"]) == ("benchmark_only", "U5")
    assert "parliamentary-records" in usage["rationale"] and flags == []


def test_u6_flags_for_the_owner(entry):
    entry["licence"]["id"] = "LicenseRef-proprietary"
    entry["publisher"]["kind"] = "media"
    usage, flags = _apply(entry)
    assert (usage["permitted_use"], usage["rule"]) == ("undetermined", "U6")
    assert flags == ["owner_decision_needed"]


def test_every_outcome_is_documented(entry):
    usage, _ = _apply(entry)
    assert {"rule", "rules_version", "rationale", "decided_at", "evidence_url"} <= usage.keys()
    assert usage["rules_version"] == rules.table()["version"]


def test_owner_decision_survives_but_not_an_opt_out(entry):
    entry["usage"] = {
        "permitted_use": "training_allowed",
        "redistribution": "unclear",
        "rule": "U0",
        "rationale": "owner decision: x",
        "decided_at": "2026-10-11",
    }
    entry["licence"]["id"] = "LicenseRef-proprietary"
    assert _apply(entry)[0]["rule"] == "U0"
    entry["signals"]["robots"] = "deny"
    assert _apply(entry)[0]["rule"] == "U1"


def test_k8_detects_stale_usage(entry):
    assert rules.k8(entry, ALLOW) == []
    entry["licence"]["id"] = "CC-BY-NC-4.0"
    [finding] = rules.k8(entry, ALLOW)
    assert finding.check == "K8" and "rules decide benchmark_only/not_allowed/U4" in finding.message
