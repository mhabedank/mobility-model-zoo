"""Wikimedia Commons harvester against recorded API responses (feature 009, research R6)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import jsonschema
import pytest

from mobility_model_zoo.catalog import ingest, model
from mobility_model_zoo.catalog.checks import Throttle
from mobility_model_zoo.catalog.harvest import base, get
from mobility_model_zoo.catalog.harvest import wikimedia_commons as wc
from mobility_model_zoo.catalog.model import schema

HTTP = Path(__file__).resolve().parents[1] / "fixtures" / "catalog-http" / "wikimedia-commons"
RECORDED = {
    ("bicicleta", "0"): "search-bicicleta-0.json",
    ("bicicleta", "3"): "search-bicicleta-3.json",
    ("carril bici", "0"): "search-carril-bici.json",
}
EMPTY = {"batchcomplete": True}


def transport(requests: list[httpx.Request], lag_first: bool = False) -> httpx.MockTransport:
    lagged = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if lag_first and not lagged:
            lagged.append(request)
            return httpx.Response(
                200, headers={"Retry-After": "5"}, content=(HTTP / "maxlag.json").read_bytes()
            )
        params = request.url.params
        term = params["gsrsearch"].rsplit(" filetype:", 1)[0]
        name = RECORDED.get((term, params.get("gsroffset", "0")))
        body = (HTTP / name).read_bytes() if name else json.dumps(EMPTY).encode()
        return httpx.Response(200, content=body, headers={"Content-Type": "application/json"})

    return httpx.MockTransport(handle)


def run(tmp_path: Path, limit: int = 30, **kw) -> tuple[list[dict], Path, Path, list[httpx.Request]]:
    requests: list[httpx.Request] = []
    jsonl, header = base.harvest(
        wc.WikimediaCommons(),
        tmp_path,
        base.Scope(languages=["es"], subdomains=["cycling"]),
        limit=limit,
        run_id=None,
        say=print,
        transport=transport(requests, **kw),
        throttle=Throttle(sleep=lambda s: None),
    )
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    return rows, jsonl, header, requests


def by_title(rows: list[dict]) -> dict[str, dict]:
    return {r["title"]["original"]: r for r in rows}


def test_registry_and_contract():
    h = get("wikimedia-commons")
    assert isinstance(h, wc.WikimediaCommons)
    assert h.env_keys == () and set(h.modalities) == {"image", "graphic", "video", "audio"}


def test_candidates_validate_and_ingest(tmp_path):
    rows, jsonl, header, requests = run(tmp_path)
    assert len(rows) == 7
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    for row in rows:
        assert not list(validator.iter_errors(row))
        assert "description" not in row
        assert row["level"] == "item" and "parent" not in row
        assert row["subdomains"] == ["cycling"]
        assert row["publisher"] == {"name": "Wikimedia Commons contributors", "kind": "community"}
        assert row["origin_area"] == "001"
        route = row["access"][0]
        assert route["method"] == "direct_download" and route["provider_hint"] == "url"
        assert route["url"] == row["landing_url"] == row["provenance"]["evidence"][0]
        assert route["url"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert (
            route["download_url"].startswith("https://upload.wikimedia.org/")
            and "utm_" not in route["download_url"]
        )
        assert isinstance(route["size_bytes_est"], int) and route["formats"][0].startswith("image/")
    root = tmp_path / "cat"
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text("catalog_id: t\nschema_version: 1\n", encoding="utf-8")
    outcome = ingest.ingest(model.load(root), jsonl, header, "2026-10-11")
    assert outcome["rejected"] == 0, outcome["rejected_lines"]
    assert outcome["accepted"] == 7


def test_no_uploader_or_description_is_stored(tmp_path):
    rows, jsonl, _, requests = run(tmp_path)
    text = jsonl.read_text(encoding="utf-8")
    for leaked in (
        "Uploader A",
        "Uploader_A",
        "uploader-a@example.org",
        "Partes de una bicicleta",
        "Número de viajes",
        "Photographs by",
    ):
        assert leaked not in text
    for request in requests:  # Artist is never even requested
        assert "Artist" not in request.url.params["iiextmetadatafilter"]
        assert request.url.params["maxlag"] == "5"
        assert int(request.url.params["gsrlimit"]) <= wc.BATCH
        assert request.headers["User-Agent"].startswith("mobility-model-zoo-crawler/")


def test_classification_and_languages(tmp_path):
    rows = by_title(run(tmp_path)[0])
    expect = {
        "Commuting by bicycle": ("image", "photo", "zxx"),
        "Bicycle diagram-es": ("graphic", "diagram", "es"),
        "Gráfico uso de la bicicleta en Madrid 2010-2020": ("graphic", "chart", "es"),
        "Bicicletas en la plaza (2015)": ("image", "photo", "zxx"),  # "Patrimonio gráfico" is no chart
        "Ciclismo urbano en Buenos Aires": ("image", "photo", "zxx"),
        "Mapa ubicación Carril bici Castellana": ("image", "map", "es"),
        "Bike lane network diagram": ("graphic", "diagram", "und"),
    }
    assert set(rows) == set(expect)
    for title, (modality, genre, lang) in expect.items():
        row = rows[title]
        assert (row["resource_type"]["modality"], row["resource_type"]["genre"]) == (modality, genre), (
            title
        )
        assert [x["code"] for x in row["languages"]] == [lang], title
        transcripts = row["content"]["transcripts"]["available"]
        assert transcripts == ("no" if genre == "photo" else "unknown")
        if genre == "photo":
            assert row["personal_data"] == {"expectation": "possible", "categories": ["faces"]}


def test_licence_mapping(tmp_path):
    rows = by_title(run(tmp_path)[0])
    expect = {
        "Commuting by bicycle": "CC-BY-SA-4.0",
        "Bicycle diagram-es": "CC-BY-SA-3.0",
        "Gráfico uso de la bicicleta en Madrid 2010-2020": "LicenseRef-US-PD",
        "Bicicletas en la plaza (2015)": "unknown",
        "Ciclismo urbano en Buenos Aires": "CC-BY-2.5-AR",  # jurisdiction port kept
        "Mapa ubicación Carril bici Castellana": "GFDL-1.2-or-later",
        "Bike lane network diagram": "CC0-1.0",
    }
    for title, lid in expect.items():
        lic = rows[title]["licence"]
        assert lic["id"] == lid, title
        if lid == "unknown":
            assert lic["evidence_url"] is None
        else:
            assert lic["evidence_url"] == rows[title]["landing_url"]
    gfdl = rows["Mapa ubicación Carril bici Castellana"]["licence"]
    assert gfdl["share_alike"] is True and gfdl["attribution_required"] == "yes"


@pytest.mark.parametrize(
    ("short", "url", "categories", "expected"),
    [
        ("CC BY-SA 4.0", "", "", "CC-BY-SA-4.0"),  # no URL: from the short name
        ("CC BY-NC 2.0", "", "", "CC-BY-NC-2.0"),
        ("Public domain", "", "PD-old-70", "LicenseRef-public-domain"),
        ("Public domain", "", "PD-USGov-NASA", "LicenseRef-US-PD"),
        (
            "Public Domain Mark",
            "https://creativecommons.org/publicdomain/mark/1.0/",
            "",
            "LicenseRef-public-domain",
        ),
        ("CC0", "", "", "CC0-1.0"),
        ("GFDL 1.3", "", "", "GFDL-1.3-or-later"),
        ("Attribution", "", "", "LicenseRef-Commons-Attribution"),
        ("OGL 3", "", "", "LicenseRef-OGL-UK-3.0"),
        ("", "", "", "unknown"),
        ("All rights reserved", "", "", "unknown"),
    ],
)
def test_licence_names(short, url, categories, expected):
    assert wc.licence_id(short, url, categories) == expected


@pytest.mark.parametrize(
    ("title", "categories", "mime", "expected"),
    [
        ("Ridership chart 2019", "", "image/png", ("graphic", "chart")),
        ("Gráfica de viajes", "", "image/png", ("graphic", "chart")),
        ("Line", "Line charts of transport", "image/png", ("graphic", "chart")),
        ("Infografía movilidad", "", "image/png", ("graphic", "infographic")),
        ("Metro network", "Transport diagrams", "image/png", ("graphic", "diagram")),
        ("Some logo", "", "image/svg+xml", ("graphic", "diagram")),
        ("Plano de la red de metro", "", "image/jpeg", ("image", "map")),
        ("Tram map ride", "Maps of tram lines", "video/webm", ("video", "footage")),
        ("Station announcement", "", "audio/ogg", ("audio", "field_recording")),
        (
            "Street with bikes",
            "Photographs by someone|Patrimonio gráfico de X",
            "image/jpeg",
            ("image", "photo"),
        ),
    ],
)
def test_classify(title, categories, mime, expected):
    assert wc.classify(title, categories, mime) == expected


def test_maxlag_retry(tmp_path, monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr(wc, "sleep", waits.append)
    rows, _, _, requests = run(tmp_path, lag_first=True)
    assert waits == [5.0] and len(rows) == 7


def test_limit_and_modality_scope(tmp_path):
    rows = run(tmp_path, limit=2)[0]
    assert len(rows) == 2
    requests: list[httpx.Request] = []
    jsonl, _ = base.harvest(
        wc.WikimediaCommons(),
        tmp_path,
        base.Scope(languages=["es"], subdomains=["cycling"], modalities=["graphic"]),
        limit=30,
        run_id="graphic-only",
        say=print,
        transport=transport(requests),
        throttle=Throttle(sleep=lambda s: None),
    )
    lines = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    assert lines and {x["resource_type"]["modality"] for x in lines} == {"graphic"}


@pytest.mark.parametrize(
    ("modalities", "filetypes"),
    [
        ([], "bitmap|drawing|video|audio"),
        (["graphic"], "bitmap|drawing"),
        (["video", "audio"], "video|audio"),
    ],
)
def test_file_types_follow_the_modality_scope(tmp_path, modalities, filetypes):
    requests: list[httpx.Request] = []
    base.harvest(
        wc.WikimediaCommons(),
        tmp_path,
        base.Scope(languages=["es"], subdomains=["cycling"], modalities=modalities),
        limit=5,
        run_id=None,
        say=print,
        transport=transport(requests),
        throttle=Throttle(sleep=lambda s: None),
    )
    assert requests
    assert {r.url.params["gsrsearch"].rsplit(" filetype:", 1)[1] for r in requests} == {filetypes}


def test_ogg_video_becomes_footage_and_validates():
    page = {
        "pageid": 42,
        "title": "File:Tranvía de Zaragoza.ogv",
        "imageinfo": [
            {
                "url": "https://upload.wikimedia.org/x/Tranv%C3%ADa_de_Zaragoza.ogv",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Tranv%C3%ADa_de_Zaragoza.ogv",
                "mime": "application/ogg",
                "size": 1000,
                "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}},
            }
        ],
    }
    cand = wc.WikimediaCommons().to_candidate(page, "es", "public_transport", [])
    assert cand["resource_type"] == {"modality": "video", "genre": "footage"}
    assert cand["access"][0]["formats"] == ["video/ogg"]
    assert cand["personal_data"] == {"expectation": "possible", "categories": ["faces", "voices"]}
    assert cand["content"]["transcripts"] == {"available": "unknown"}
    jsonschema.validate(cand, schema("candidate"))
    sound = dict(page, title="File:Anuncio estación.oga")
    assert wc.WikimediaCommons().to_candidate(sound, "es", "rail", [])["resource_type"] == {
        "modality": "audio",
        "genre": "field_recording",
    }

