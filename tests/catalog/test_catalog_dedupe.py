"""Duplicate detection K3 (feature 009 research R7, T018)."""

from __future__ import annotations

import copy

from mobility_model_zoo.catalog.model import load
from mobility_model_zoo.catalog.validate import DedupeIndex, k3


def _pair(catalog_dir):
    cat = load(catalog_dir)
    a = cat.entries["pl-stat-transport-tables"]
    b = copy.deepcopy(a)
    b["id"] = "pl-stat-copy"
    b["landing_url"] = "https://example.org/other-page"
    b["access"] = [dict(a["access"][0], url="https://example.org/other-data")]
    b["title"] = {"original": "Something entirely different", "en": "Different"}
    return cat, a, b


def test_same_canonical_url_is_an_exact_duplicate(catalog_dir):
    cat, a, b = _pair(catalog_dir)
    b["landing_url"] = "https://www.example.org/pl-stat-transport-tables/"
    idx = DedupeIndex.build([a])
    assert idx.exact(b)[0] == a["id"]


def test_same_doi_is_an_exact_duplicate(catalog_dir):
    cat, a, b = _pair(catalog_dir)
    a["identifiers"] = {"doi": "10.1234/ABC.5"}
    b["identifiers"] = {"doi": "10.1234/abc.5"}
    assert DedupeIndex.build([a]).exact(b)[0] == a["id"]


def test_similar_title_and_publisher_only_warns(catalog_dir):
    cat, a, b = _pair(catalog_dir)
    b["title"] = {"original": "Statystyka transportu.", "en": "x"}
    idx = DedupeIndex.build([a])
    assert idx.exact(b) is None
    assert idx.similar(b) == [a["id"]]


def test_dissimilar_title_gives_nothing(catalog_dir):
    cat, a, b = _pair(catalog_dir)
    idx = DedupeIndex.build([a])
    assert idx.exact(b) is None and idx.similar(b) == []


def test_k3_on_a_catalog(catalog_dir):
    cat, a, b = _pair(catalog_dir)
    b["landing_url"] = a["landing_url"]
    cat.entries[b["id"]] = b
    findings = k3(cat)
    assert any(
        f.check == "K3" and f.severity == "fail" and "duplicate of" in f.message for f in findings
    )
    b.setdefault("relations", {})["duplicate_of"] = a["id"]
    assert not [f for f in k3(cat) if f.severity == "fail"]
