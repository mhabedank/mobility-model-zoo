"""Podcast Index harvester against synthetic API responses (feature 009, research R6).

The owner has no Podcast Index key yet: the responses follow the official OpenAPI document and are
not recordings (see tests/fixtures/catalog-http/podcast-index/README.md).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import jsonschema
import pytest

from mobility_model_zoo.catalog import ingest, model
from mobility_model_zoo.catalog.checks import Throttle
from mobility_model_zoo.catalog.harvest import base, get
from mobility_model_zoo.catalog.harvest import podcast_index as pi
from mobility_model_zoo.catalog.model import schema
from mobility_model_zoo.release.errors import CredentialError

HTTP = Path(__file__).resolve().parents[1] / "fixtures" / "catalog-http" / "podcast-index"
RECORDED = {"bicicleta": "search-bicicleta.json", "carril bici": "search-carril-bici.json"}
KEY, SECRET = "TESTKEY0000000000000", "test-secret-0000"


@pytest.fixture
def keys(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PODCASTINDEX_API_KEY", KEY)
    monkeypatch.setenv("PODCASTINDEX_API_SECRET", SECRET)


def transport(requests: list[httpx.Request], status: int = 200) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if status != 200:
            return httpx.Response(status, content=(HTTP / "unauthorized.json").read_bytes())
        name = RECORDED.get(request.url.params["q"])
        body = (HTTP / name).read_bytes() if name else b'{"status": "true", "feeds": [], "count": 0}'
        return httpx.Response(200, content=body, headers={"Content-Type": "application/json"})

    return httpx.MockTransport(handle)


def run(tmp_path: Path, limit: int = 30, status: int = 200):
    requests: list[httpx.Request] = []
    jsonl, header = base.harvest(
        pi.PodcastIndex(),
        tmp_path,
        base.Scope(languages=["es"], subdomains=["cycling"]),
        limit=limit,
        run_id=None,
        say=print,
        transport=transport(requests, status),
        throttle=Throttle(sleep=lambda s: None),
    )
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    return rows, jsonl, header, requests


def test_registry_and_contract():
    h = get("podcast-index")
    assert isinstance(h, pi.PodcastIndex)
    assert h.env_keys == ("PODCASTINDEX_API_KEY", "PODCASTINDEX_API_SECRET") and h.modalities == (
        "audio",
    )


def test_auth_headers(keys, tmp_path):
    _, _, _, requests = run(tmp_path)
    assert len(requests) == 3  # one search per term: bicicleta, ciclismo urbano, carril bici
    for request in requests:
        stamp = request.headers["X-Auth-Date"]
        assert stamp.isdigit()
        assert request.headers["X-Auth-Key"] == KEY
        assert (
            request.headers["Authorization"] == hashlib.sha1((KEY + SECRET + stamp).encode()).hexdigest()
        )
        assert request.headers["User-Agent"].startswith("mobility-model-zoo-crawler/")
        assert request.url.path == "/api/1.0/search/byterm"
        assert "clean" in request.url.params and request.url.params["max"] == str(pi.MAX_RESULTS)
        assert SECRET not in str(request.url)


def test_auth_header_value():
    headers = pi.auth_headers(
        "UXKCGDSYGUUEVQJSYDZH", "yzJe2eE7XV-3eY576dyRZ6wXyAbndh6LUrCZ8KN|", at=1613713388.9
    )
    assert headers["X-Auth-Date"] == "1613713388"
    expected = hashlib.sha1(
        b"UXKCGDSYGUUEVQJSYDZHyzJe2eE7XV-3eY576dyRZ6wXyAbndh6LUrCZ8KN|1613713388"
    ).hexdigest()
    assert headers["Authorization"] == expected


def test_candidates_validate_and_ingest(keys, tmp_path):
    rows, jsonl, header, _ = run(tmp_path)
    # kept: es-ES association, es-mx person, es Atom feed; dropped: pt-br, music medium, dead, duplicate
    assert [r["title"]["original"] for r in rows] == [
        "Pedaleando la ciudad",
        "Bici y barrio",
        "Movilidad en dos ruedas",
    ]
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    for row in rows:
        assert not list(validator.iter_errors(row))
        assert "description" not in row
        assert row["level"] == "collection"
        assert row["resource_type"] == {"modality": "audio", "genre": "podcast"}
        assert row["subdomains"] == ["cycling"]
        assert row["licence"]["id"] == "unknown" and row["licence"]["evidence_url"] is None
        assert row["personal_data"] == {"expectation": "present", "categories": ["voices", "names"]}
        assert row["content"]["transcripts"] == {"available": "unknown"}
        assert row["content"]["frequency"] == "IRREG"
        route = row["access"][0]
        assert route["method"] == "feed" and route["auth"] == "none" and route["cost"] == "free"
        assert row["provenance"]["evidence"][0].startswith("https://podcastindex.org/podcast/")
    root = tmp_path / "cat"
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text("catalog_id: t\nschema_version: 1\n", encoding="utf-8")
    outcome = ingest.ingest(model.load(root), jsonl, header, "2026-10-11")
    assert outcome["rejected"] == 0, outcome["rejected_lines"]
    assert outcome["accepted"] == 3


def test_mapping(keys, tmp_path):
    rows, jsonl, _, _ = run(tmp_path)
    assoc, person, radio = rows
    assert assoc["languages"] == [{"code": "es", "origin": "original"}] and assoc["origin_area"] == "ES"
    assert assoc["publisher"] == {"name": "Asociación Ciclista Ejemplo", "kind": "association"}
    assert assoc["landing_url"] == "https://pedaleando.example.org/"
    assert assoc["content"]["volume"] == {"items": 42} and assoc["content"]["updated"] == "2025-10-08"
    assert assoc["access"][0]["formats"] == ["application/rss+xml"]
    assert assoc["identifiers"]["other"] == [
        "podcastindex:9000001",
        "podcast-guid:00000000-0000-4000-8000-000000000001",
        "itunes:1000000001",
    ]
    assert person["origin_area"] == "MX"
    assert person["publisher"] == {"name": "Persona Ejemplo", "kind": "individual"}
    assert radio["publisher"] == {"name": "Radio Ejemplo FM", "kind": "media"}
    assert radio["origin_area"] == "001"
    assert radio["landing_url"] == "https://podcastindex.org/podcast/9000006"
    assert radio["access"][0]["formats"] == ["application/atom+xml"]
    assert "volume" not in radio["content"] and "updated" not in radio["content"]
    text = jsonl.read_text(encoding="utf-8")
    assert "@example.org" not in text and "persona.ejemplo" not in text
    assert "must never be stored" not in text and "Pessoa Exemplo" not in text


@pytest.mark.parametrize(
    ("author", "owner", "expected"),
    [
        ("Ana Ejemplo", "", ("Ana Ejemplo", "individual")),
        ("ana@example.org", "Ana Ejemplo", ("Ana Ejemplo", "individual")),
        ("", "", ("unknown publisher", "individual")),
        ("Ayuntamiento de Ejemplo", "", ("Ayuntamiento de Ejemplo", "government")),
        ("Universidad de Ejemplo", "", ("Universidad de Ejemplo", "research")),
        ("Ejemplo Media S.L.", "", ("Ejemplo Media S.L.", "media")),
        ("Ejemplo Consulting S.L.", "", ("Ejemplo Consulting S.L.", "company")),
        ("Ana Ejemplo (https://example.org/ana)", "", ("Ana Ejemplo", "individual")),
    ],
)
def test_publisher(author, owner, expected):
    assert pi.publisher({"author": author, "ownerName": owner}) == expected


def test_area_and_licence_field():
    assert pi.area("es-ES") == "ES" and pi.area("pt-br") == "BR" and pi.area("es") == "001"
    assert pi.area("en-XX") == "001" and pi.area(None) == "001"
    feed = {
        "id": 1,
        "title": "T",
        "url": "https://feeds.example.org/t.xml",
        "language": "es",
        "license": "CC BY 4.0",
    }
    cand = pi.PodcastIndex().to_candidate(feed, "cycling")
    assert cand["licence"]["id"] == "CC-BY-4.0"
    assert cand["licence"]["evidence_url"] == "https://podcastindex.org/podcast/1"


def test_missing_keys(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PODCASTINDEX_API_KEY", raising=False)
    monkeypatch.delenv("PODCASTINDEX_API_SECRET", raising=False)
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    with pytest.raises(CredentialError, match="PODCASTINDEX_API_KEY"):
        run(tmp_path)


def test_rejected_signature(keys, tmp_path):
    with pytest.raises(CredentialError, match="PODCASTINDEX_API_KEY"):
        run(tmp_path, status=401)


def test_limit(keys, tmp_path):
    rows = run(tmp_path, limit=1)[0]
    assert len(rows) == 1
