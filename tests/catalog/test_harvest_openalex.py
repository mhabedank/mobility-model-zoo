"""OpenAlex harvester against trimmed recorded responses (feature 009, T040/T051): no network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import jsonschema
import pytest

from mobility_model_zoo.catalog import ingest, model
from mobility_model_zoo.catalog.checks import Throttle
from mobility_model_zoo.catalog.harvest import base, get
from mobility_model_zoo.catalog.harvest.openalex import OpenAlex, licence_id, search_filter
from mobility_model_zoo.catalog.model import read_yaml, schema
from mobility_model_zoo.release.errors import CredentialError

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "catalog-http" / "openalex"
PAGE_1 = json.loads((RECORDED / "works-es-rail-1.json").read_text(encoding="utf-8"))
PAGE_2 = json.loads((RECORDED / "works-es-rail-2.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch, tmp_path):
    """Never read a real .env (the worktree sits below the repository that has one)."""
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENALEX_API_KEY", "dummy")


def openalex_api(remaining: int = 9000, calls: list[httpx.Request] | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        assert request.url.host == "api.openalex.org" and request.url.path == "/works"
        assert request.headers["Authorization"] == "Bearer dummy"
        assert "api_key" not in request.url.params
        flt = request.url.params["filter"]
        assert "language:es" in flt and "open_access.is_oa:true" in flt and "has_doi:true" in flt
        assert "title_and_abstract.search:ferrocarril|" in flt
        assert "topics.subfield.id:3313|" in flt
        assert "abstract" not in request.url.params["select"]
        body = PAGE_1 if request.url.params["cursor"] == "*" else PAGE_2
        headers = {"x-ratelimit-limit": "10000", "x-ratelimit-remaining": str(remaining),
                   "x-ratelimit-credits-used": "10"}
        return httpx.Response(200, json=body, headers=headers)

    return handler


def run(root: Path, *, limit: int = 20, budget: base.Budget | None = None, remaining: int = 9000,
        calls: list[httpx.Request] | None = None) -> tuple[Path, Path]:
    return base.harvest(
        OpenAlex(), root, base.Scope(languages=["es"], subdomains=["rail"]), limit=limit, run_id=None,
        say=print, transport=httpx.MockTransport(openalex_api(remaining, calls)),
        throttle=Throttle(sleep=lambda s: None), budget=budget,
    )


def lines(jsonl: Path) -> list[dict]:
    return [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_registry_and_attributes():
    h = get("openalex")
    assert isinstance(h, OpenAlex)
    assert (h.name, h.catalogue, h.env_keys, h.modalities) == (
        "openalex", "OpenAlex", ("OPENALEX_API_KEY",), ("text",))


def test_candidates_validate_and_carry_no_personal_data(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, calls=calls)
    found = lines(jsonl)
    assert len(found) == 6 and len(calls) == 2  # two pages through the cursor
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    for cand in found:
        assert not list(validator.iter_errors(cand))
        assert "description" not in cand
        assert cand["level"] == "item" and cand["parent"] is None
        assert cand["resource_type"] == {"modality": "text", "genre": "paper"}
        assert cand["subdomains"] == ["rail"]
        assert cand["languages"] == [{"code": "es", "origin": "original"}]
        assert cand["publisher"]["kind"] == "research"
        assert cand["landing_url"].startswith("https://doi.org/10.")
        assert cand["identifiers"]["doi"].startswith("10.")
        assert cand["identifiers"]["other"][0].startswith("openalex:W")
    text = jsonl.read_text(encoding="utf-8")
    assert "Author A" not in text and "orcid" not in text.lower() and "abstract" not in text
    first = found[0]
    assert first["title"] == {"original": "Urbanismo y ferrocarril", "en": "Urbanismo y ferrocarril"}
    assert first["origin_area"] == "ES"  # first institution's country
    assert first["publisher"]["name"] == "Instituto Andaluz del Patrimonio Histórico"
    assert first["content"] == {"published": "2005-10-01"}
    assert first["access"][0]["method"] == "direct_download"
    assert first["access"][0]["formats"] == ["application/pdf"]
    by_id = {c["identifiers"]["other"][0]: c for c in found}
    assert by_id["openalex:W4230090886"]["origin_area"] == "US"
    assert by_id["openalex:W2028509171"]["origin_area"] == "001"  # no institution
    no_pdf = next(c for c in found if c["identifiers"]["other"] == ["openalex:W844043465"])
    assert no_pdf["access"][0]["method"] == "page_by_page" and "download_url" not in no_pdf["access"][0]
    assert read_yaml(header)["cost"]["notes"] == "free API tier"


def test_licence_mapping(tmp_path):
    jsonl, _ = run(tmp_path)
    by_id = {c["identifiers"]["other"][0]: c["licence"] for c in lines(jsonl)}
    assert by_id["openalex:W41037268"]["id"] == "unknown"
    assert by_id["openalex:W41037268"]["evidence_url"] is None
    assert by_id["openalex:W4230090886"]["id"] == "CC-BY-4.0"
    assert by_id["openalex:W4230090886"]["evidence_url"].startswith("https://")
    assert by_id["openalex:W2028509171"]["id"] == "CC-BY-NC-4.0"
    assert by_id["openalex:W2028509171"]["commercial_use"] == "no"
    assert by_id["openalex:W844043465"]["id"] == "CC-BY-NC-ND-4.0"
    assert by_id["openalex:W844043465"]["derivatives"] == "no"
    assert [licence_id(v) for v in ("cc-by-sa", "cc-by-nc-sa", "cc-by-nd", "cc0", "public-domain")] == [
        "CC-BY-SA-4.0", "CC-BY-NC-SA-4.0", "CC-BY-ND-4.0", "CC0-1.0", "LicenseRef-public-domain"]
    for unknown in (None, "", "other-oa", "publisher-specific-oa", "implied-oa", "unspecified-oa"):
        assert licence_id(unknown) == "unknown"


def test_search_filter_quotes_latin_phrases_only():
    got = search_filter(["ferrocarril", "tren de cercanías", "a,b|c"])
    assert got == 'ferrocarril|"tren de cercanías"|"a b c"'
    assert search_filter(["公共交通", "鉄道 乗客数"]) == "公共交通|鉄道 乗客数"


def test_own_budget_stops_early(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, budget=base.Budget(15, 0.8), calls=calls)  # one 10-credit page
    assert len(calls) == 1 and len(lines(jsonl)) == 3
    assert read_yaml(header)["cost"]["notes"].startswith("stopped early")


def test_tiny_budget_stops_before_any_request(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, budget=base.Budget(2, 0.8), calls=calls)
    assert calls == [] and lines(jsonl) == []
    assert "stopped early" in read_yaml(header)["cost"]["notes"]


def test_account_remaining_below_20_percent_stops(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, remaining=1500, calls=calls)  # 15% of 10,000 left after page 1
    assert len(calls) == 1 and len(lines(jsonl)) == 3
    notes = read_yaml(header)["cost"]["notes"]
    assert notes.startswith("stopped early") and "1500 of 10000" in notes


def test_429_stops_early(tmp_path):
    def refused(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "budget"})

    jsonl, header = base.harvest(
        OpenAlex(), tmp_path, base.Scope(languages=["es"], subdomains=["rail"]), limit=5, run_id=None,
        say=print, transport=httpx.MockTransport(refused), throttle=Throttle(sleep=lambda s: None),
    )
    assert lines(jsonl) == [] and "429" in read_yaml(header)["cost"]["notes"]


def test_limit_is_respected(tmp_path):
    jsonl, _ = run(tmp_path, limit=2)
    assert len(lines(jsonl)) == 2


def test_run_ingests_without_rejections(tmp_path):
    root = tmp_path / "cat"
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text("catalog_id: t\nschema_version: 1\n", encoding="utf-8")
    jsonl, header = run(root)
    outcome = ingest.ingest(model.load(root), jsonl, header, "2026-10-11")
    assert outcome["rejected"] == 0, outcome["rejected_lines"]
    assert outcome["accepted"] + outcome["merged"] == 6


def test_missing_key_names_the_variable(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    with pytest.raises(CredentialError, match="OPENALEX_API_KEY"):
        run(tmp_path)
