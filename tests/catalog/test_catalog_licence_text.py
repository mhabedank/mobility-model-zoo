"""Licence reading shared by the audit and check K5 (feature 009, audit 2026-10-14)."""

from __future__ import annotations

import pytest

from mobility_model_zoo.catalog import licence_text as lt


@pytest.mark.parametrize(
    ("text", "url", "expected"),
    [
        ("see https://creativecommons.org/licenses/by-sa/4.0/", None, "CC-BY-SA-4.0"),
        (
            "licence: http://publications.europa.eu/resource/authority/licence/CC_BY_4_0",
            None,
            "CC-BY-4.0",
        ),
        (
            "Licence Ouverte / Open Licence version 2.0, compatible with the Open Government Licence",
            None,
            "etalab-2.0",
        ),
        ("本データは公共データ利用規約（第1.0版）に基づき提供", None, "LicenseRef-Japan-PDL-1.0"),
        (
            "Condiciones de uso",
            "https://nap.transportes.gob.es/licencia-datos",
            "LicenseRef-Spain-MITRAMS-LDA",
        ),
        ("Tous droits réservés", None, "LicenseRef-proprietary"),
        ("nothing here", None, "unknown"),
    ],
)
def test_match_licence(text, url, expected):
    assert lt.match_licence(text, url) == expected


@pytest.mark.parametrize(
    ("url", "readable"),
    [
        (
            "https://data.europa.eu/data/datasets/abc-1?locale=en",
            "https://data.europa.eu/api/hub/search/datasets/abc-1",
        ),
        ("https://zenodo.org/records/6413901", "https://zenodo.org/api/records/6413901"),
        ("https://doi.org/10.1/x", "https://doi.org/10.1/x"),
    ],
)
def test_single_page_applications_are_read_through_their_api(url, readable):
    assert lt.readable_url(url) == readable


def test_reader_answers_become_catalog_ids():
    known = {"LicenseRef-Japan-PDL-1.0", "CC-BY-4.0"}
    assert lt.normalise("PDL-1.0", known) == "LicenseRef-Japan-PDL-1.0"
    assert lt.normalise("Licence-Ouverte-2.0", known) == "etalab-2.0"
    assert lt.normalise("CC BY 4.0", known) == "CC-BY-4.0"
    assert lt.normalise("LicenseRef-proprietary", known) == "LicenseRef-proprietary"
    assert lt.normalise("", known) == "unknown"


def test_conflict_only_against_an_open_stored_licence():
    assert lt.conflicts("CC-BY-NC-4.0", "LicenseRef-proprietary")
    assert not lt.conflicts("LicenseRef-proprietary", "LicenseRef-proprietary")
    assert not lt.conflicts("CC-BY-4.0", "unknown")
