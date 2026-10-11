"""Zenodo harvester against trimmed recorded responses (feature 009): no network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import jsonschema
import pytest

from mobility_model_zoo.catalog import ingest, model
from mobility_model_zoo.catalog.checks import Throttle
from mobility_model_zoo.catalog.harvest import base, get
from mobility_model_zoo.catalog.harvest.zenodo import Zenodo, iso639_3
from mobility_model_zoo.catalog.model import read_yaml, schema

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "catalog-http" / "zenodo"
PAGE = json.loads((RECORDED / "records-es-rail.json").read_text(encoding="utf-8"))
EMPTY = json.loads((RECORDED / "records-empty.json").read_text(encoding="utf-8"))
DATASET = "https://zenodo.org/records/17553920"
ARTICLE = "https://zenodo.org/records/17229388"
PROPOSAL = "https://zenodo.org/records/8183787"


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch, tmp_path):
    """Never read a real .env (the worktree sits below the repository that has one)."""
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.chdir(tmp_path)


def api(calls: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "zenodo.org" and request.url.path == "/api/records"
        assert request.url.params["q"].endswith(" AND metadata.languages.id:(spa)")
        assert request.url.params["type"] in ("dataset", "publication")
        assert "mobility-model-zoo-crawler" in request.headers["User-Agent"]
        body = PAGE if request.url.params["page"] == "1" else EMPTY
        return httpx.Response(200, json=body)

    return handler


def run(root: Path, calls: list[httpx.Request], limit: int = 20) -> tuple[Path, Path]:
    return base.harvest(
        Zenodo(), root, base.Scope(languages=["es"], subdomains=["rail"]), limit=limit, run_id=None,
        say=print, transport=httpx.MockTransport(api(calls)),
        throttle=Throttle(clock=lambda: 0.0, sleep=lambda s: None),
    )


def lines(jsonl: Path) -> list[dict]:
    return [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_registry_and_attributes():
    h = get("zenodo")
    assert isinstance(h, Zenodo)
    assert (h.name, h.catalogue, h.env_keys, h.modalities) == (
        "zenodo", "Zenodo", (), ("structured_data", "text"))


def test_candidates_validate_and_follow_the_rules(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, calls)
    head = read_yaml(header)
    assert head["kind"] == "harvester:zenodo"
    assert head["scope"]["modalities"] == ["structured_data", "text"]
    found = lines(jsonl)
    # 3 terms x 2 types, each answered by the same page: deduplicated; the restricted record is skipped
    assert [c["landing_url"] for c in found] == [DATASET, ARTICLE, PROPOSAL]
    assert len(calls) == 6
    assert calls[0].url.params["q"].startswith('"ferrocarril"')
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    for cand in found:
        assert not list(validator.iter_errors(cand))
        assert "description" not in cand
        assert cand["level"] == "item" and "parent" not in cand
        assert cand["subdomains"] == ["rail"] and cand["topics"] == ["productdev"]
        assert cand["origin_area"] == "001"
        assert cand["personal_data"] == base.personal_data(cand["resource_type"]["genre"])
        assert cand["quality"]["score"] == 3 and "Zenodo" in cand["quality"]["rationale"]
        assert cand["identifiers"]["doi"].startswith("10.5281/zenodo.")
        assert cand["provenance"] == {"method": "harvest", "evidence": [cand["landing_url"]]}
        for route in cand["access"]:
            assert route["method"] == "direct_download" and route["url"] == cand["landing_url"]
            assert route["download_url"].startswith("https://zenodo.org/api/records/")
            assert (route["auth"], route["cost"], route["provider_hint"]) == ("none", "free", "zenodo")
    text = jsonl.read_text(encoding="utf-8")
    assert "Recorded abstract" not in text and "Author A" not in text
    by_url = {c["landing_url"]: c for c in found}

    dataset = by_url[DATASET]
    assert dataset["resource_type"] == {"modality": "structured_data", "genre": "table"}
    assert dataset["languages"] == [{"code": "es", "origin": "original"}]
    assert dataset["licence"]["id"] == "CC-BY-4.0" and dataset["licence"]["evidence_url"] == DATASET
    assert dataset["publisher"]["kind"] == "research"
    assert dataset["access"][0]["formats"] == ["text/csv"]
    assert dataset["access"][0]["size_bytes_est"] == 47656

    article = by_url[ARTICLE]
    assert article["resource_type"] == {"modality": "text", "genre": "paper"}
    assert article["licence"]["id"] == "unknown" and article["licence"]["evidence_url"] is None
    assert article["publisher"] == {"name": "Pontificia Universidad Católica del Ecuador",
                                    "kind": "research"}

    proposal = by_url[PROPOSAL]
    assert proposal["languages"] == [{"code": "und", "origin": "unknown"}]
    assert proposal["publisher"] == {"name": "Zenodo", "kind": "community"}


def test_ingest_accepts_every_line(tmp_path):
    root = tmp_path / "cat"
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text("catalog_id: t\nschema_version: 1\n", encoding="utf-8")
    jsonl, header = run(root, [])
    outcome = ingest.ingest(model.load(root), jsonl, header, "2026-10-11")
    assert outcome["rejected"] == 0, outcome["rejected_lines"]
    assert outcome["accepted"] == 3


def test_text_scope_only_asks_for_publications(tmp_path):
    calls: list[httpx.Request] = []
    scope = base.Scope(languages=["es"], subdomains=["rail"], modalities=["text"])
    jsonl, _ = base.harvest(Zenodo(), tmp_path, scope, limit=1, run_id=None, say=print,
                            transport=httpx.MockTransport(api(calls)),
                            throttle=Throttle(sleep=lambda s: None))
    assert [c.url.params["type"] for c in calls] == ["publication"]
    assert [c["landing_url"] for c in lines(jsonl)] == [ARTICLE]


def test_language_codes():
    assert iso639_3("es") == ["spa"]
    assert iso639_3("de") == ["deu", "ger"]
    assert iso639_3("ja") == ["jpn"]
