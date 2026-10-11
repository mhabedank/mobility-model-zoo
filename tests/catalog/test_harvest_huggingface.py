"""Hugging Face Hub harvester against trimmed recorded responses (feature 009): no network."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import jsonschema
import pytest

from mobility_model_zoo.catalog import ingest, model
from mobility_model_zoo.catalog.checks import Throttle
from mobility_model_zoo.catalog.harvest import base, get
from mobility_model_zoo.catalog.harvest.huggingface import HuggingFace, matches, resource_type
from mobility_model_zoo.catalog.model import read_yaml, schema

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "catalog-http" / "huggingface"
DATASETS = json.loads((RECORDED / "datasets.json").read_text(encoding="utf-8"))
HUB = "https://huggingface.co/datasets/"
MADRID = HUB + "dcdc-upm/fatal_traffic_accidents_in_the_city_of_madrid_2024"
FORECAST = HUB + "example-user-1/PublicTransportAI"
AFRICA = HUB + "electricsheepafrica/africa-owid-share-with-convenient-access-to-public-transport"
REPORTS = HUB + "DSTI/traffic-accidents-reports-800"
RAILWAY = HUB + "sirlab-ai/railway-forest-daylight__63k3mlcn"


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch, tmp_path):
    """Never read a real .env (the worktree sits below the repository that has one)."""
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.chdir(tmp_path)


def flat(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def hub(calls: list[httpx.Request]):
    """Imitates the Hub search: substring of the id, optional `language:` filter."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "huggingface.co" and request.url.path == "/api/datasets"
        assert request.url.params["full"] == "true"
        term = flat(request.url.params["search"])
        wanted = request.url.params.get("filter")
        body = [d for d in DATASETS if term in flat(d["id"]) and (not wanted or wanted in d["tags"])]
        return httpx.Response(200, json=body)

    return handler


def run(root: Path, calls: list[httpx.Request], *, limit: int = 20, **kw) -> tuple[Path, Path]:
    pilot = {"languages": ["es", "en"], "subdomains": ["public_transport", "safety", "rail"]}
    scope = base.Scope(**(pilot | kw))
    return base.harvest(HuggingFace(), root, scope, limit=limit, run_id=None, say=print,
                        transport=httpx.MockTransport(hub(calls)),
                        throttle=Throttle(clock=lambda: 0.0, sleep=lambda s: None))


def lines(jsonl: Path) -> list[dict]:
    return [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_registry_and_attributes():
    h = get("huggingface")
    assert isinstance(h, HuggingFace)
    assert (h.name, h.catalogue, h.env_keys) == ("huggingface", "Hugging Face Hub", ())
    assert "structured_data" in h.modalities and "text" in h.modalities


def test_candidates_validate_and_follow_the_rules(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, calls)
    assert jsonl.exists() and header.exists()
    assert read_yaml(header)["kind"] == "harvester:huggingface"
    filters = {c.url.params.get("filter") for c in calls}
    assert filters == {"language:es", "language:en"}
    # Spanish runs search the English and the ASCII-folded Spanish terms
    assert {"public transport", "transporte publico", "tram"} <= {c.url.params["search"] for c in calls}
    found = lines(jsonl)
    # `tram` finds `tramites-bo` on the Hub, but only whole words count
    assert [c["landing_url"] for c in found] == [MADRID, FORECAST, AFRICA, REPORTS, RAILWAY]
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    for cand in found:
        assert not list(validator.iter_errors(cand))
        assert "description" not in cand
        assert cand["level"] == "collection" and cand["origin_area"] == "001"
        assert cand["provenance"] == {"method": "harvest", "evidence": [cand["landing_url"]]}
        route = cand["access"][0]
        assert len(cand["access"]) == 1 and route["method"] == "api"
        assert route["url"] == cand["landing_url"]
        assert route["provider_hint"] == "huggingface" and route["cost"] == "free"
        lic = cand["licence"]
        assert (lic["evidence_url"] is None) == (lic["id"] == "unknown")
        if lic["id"] != "unknown":
            assert lic["evidence_url"] == cand["landing_url"]
    by_url = {c["landing_url"]: c for c in found}

    madrid = by_url[MADRID]
    assert madrid["subdomains"] == ["safety"]
    assert madrid["languages"] == [{"code": "es", "origin": "original"}]
    assert madrid["publisher"] == {"name": "dcdc-upm", "kind": "research"}
    assert madrid["licence"]["id"] == "unknown"  # `other`: the card links the city's terms
    assert madrid["licence"]["url"] == "https://datos.madrid.es/egob/catalogo/aviso-legal"
    assert madrid["resource_type"] == {"modality": "structured_data", "genre": "table"}
    assert madrid["access"][0]["formats"] == ["application/vnd.apache.parquet"]
    assert madrid["content"]["published"] == "2025-09-01"

    forecast = by_url[FORECAST]
    assert forecast["subdomains"] == ["public_transport"] and forecast["licence"]["id"] == "Apache-2.0"
    assert [lang["code"] for lang in forecast["languages"]] == ["en", "pt"]
    assert forecast["resource_type"]["genre"] == "time_series"
    assert forecast["publisher"]["kind"] == "community"

    assert by_url[AFRICA]["licence"]["id"] == "CC-BY-4.0"
    assert by_url[AFRICA]["licence"]["attribution_required"] == "yes"

    reports = by_url[REPORTS]
    assert reports["resource_type"] == {"modality": "text", "genre": "article"}
    assert reports["licence"]["id"] == "MIT"

    railway = by_url[RAILWAY]
    assert railway["access"][0]["auth"] == "account" and "gated" in railway["access"][0]["notes"]
    assert railway["resource_type"] == {"modality": "structured_data", "genre": "sensor_data"}
    assert all(by_url[u]["access"][0]["auth"] == "none" for u in (MADRID, FORECAST, AFRICA, REPORTS))


def test_ingest_accepts_every_line(tmp_path):
    root = tmp_path / "cat"
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text("catalog_id: t\nschema_version: 1\n", encoding="utf-8")
    jsonl, header = run(root, [])
    outcome = ingest.ingest(model.load(root), jsonl, header, "2026-10-11")
    assert outcome["rejected"] == 0, outcome["rejected_lines"]
    assert outcome["accepted"] == 5


def test_limit_and_modality(tmp_path):
    jsonl, _ = run(tmp_path, [], limit=1)
    assert [c["landing_url"] for c in lines(jsonl)] == [MADRID]
    jsonl, _ = run(tmp_path, [], modalities=["text"])
    assert [c["landing_url"] for c in lines(jsonl)] == [REPORTS]


def test_security_subdomain_sets_the_topic():
    item = {"id": "example-org/can-bus-intrusion-detection",
            "tags": ["license:cc-by-4.0", "modality:tabular"]}
    cand = HuggingFace().candidate(item, "vehicle_security", None)
    assert cand is not None and cand["topics"] == ["security"]
    assert cand["languages"] == [{"code": "und", "origin": "unknown"}]


def test_whole_word_match():
    assert matches("public transport", "someone/PublicTransportAI")
    assert matches("public transport", "org/public_transport_NZ_latest")
    assert matches("tram", "org/trams-of-europe")
    assert not matches("tram", "org/tramites-bo")
    assert not matches("bus network", "org/business-network")
    assert matches("EV charging", "org/ev-charging-sessions")


def test_resource_type():
    assert resource_type(["modality:audio"]) is None
    assert resource_type(["modality:image"]) == ("image", "photo")
    assert resource_type(["task_categories:text-classification", "modality:tabular"]) == (
        "structured_data", "table")
    assert resource_type(["format:json"]) == ("structured_data", "json_xml_dump")
    assert resource_type([]) == ("structured_data", "table")
