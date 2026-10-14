"""Licence reading shared by the audit and check K5 (feature 009, audit 2026-10-14)."""

from __future__ import annotations

import httpx
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


def _client(routes: dict[str, httpx.Response]) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.host}{request.url.path}"
        return routes.get(key, httpx.Response(404))

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_a_doi_is_read_with_the_licence_its_registry_records():
    client = _client(
        {
            "doi.org/10.5281/zenodo.1": httpx.Response(200, text="<html>JS app</html>"),
            "api.datacite.org/dois/10.5281/zenodo.1": httpx.Response(
                200,
                json={
                    "data": {
                        "attributes": {
                            "rightsList": [
                                {
                                    "rights": "Creative Commons Attribution 4.0 International",
                                    "rightsUri": "https://creativecommons.org/licenses/by/4.0/legalcode",
                                }
                            ]
                        }
                    }
                },
            ),
        }
    )
    text = lt.evidence_text("https://doi.org/10.5281/zenodo.1", client)
    assert text.startswith("DataCite rights:") and lt.match_licence(text) == "CC-BY-4.0"


def test_a_zenodo_record_is_read_through_its_api_excerpt():
    client = _client(
        {
            "zenodo.org/api/records/7": httpx.Response(
                200,
                json={
                    "metadata": {"title": "T", "license": {"id": "cc-by-4.0"}, "description": "x" * 9000}
                },
            )
        }
    )
    text = lt.evidence_text("https://zenodo.org/records/7", client)
    assert "cc-by-4.0" in text and len(text) < 200 and lt.match_licence(text) == "CC-BY-4.0"


def test_excerpt_keeps_the_licence_passage_of_a_long_page():
    text = "intro " * 2000 + "This work is licensed under CC BY-SA 3.0." + " footer" * 500
    short = lt.excerpt(text, 6000)
    assert len(short) <= 6000 and "CC BY-SA 3.0" in short
