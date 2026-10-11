"""data.europa.eu harvester against trimmed recorded responses (feature 009): no network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import jsonschema
import pytest

from mobility_model_zoo.catalog import ingest, model
from mobility_model_zoo.catalog.checks import Throttle
from mobility_model_zoo.catalog.harvest import base, get
from mobility_model_zoo.catalog.harvest.data_europa import (
    TITLE_LANGUAGE_NOTE,
    DataEuropa,
    _area,
    _licence_id,
    _route,
    ckan_licence,
    dane_gov_pl_licence,
)
from mobility_model_zoo.catalog.model import read_yaml, schema

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "catalog-http" / "data-europa"
PAGE = json.loads((RECORDED / "search-es-rail.json").read_text(encoding="utf-8"))
EMPTY = json.loads((RECORDED / "search-empty.json").read_text(encoding="utf-8"))
ANDALUCIA = "https://data.europa.eu/data/datasets/-91ff7a79-ceb3-45a7-9686-c992634343ce-_100358_es"
BALEARES = ("https://data.europa.eu/data/datasets/"
            "https-intranet-caib-es-opendatacataleg-dataset-cc8dff66-fcad-45a9-b51f-424979f91980")
ZARAGOZA = "https://data.europa.eu/data/datasets/https-www-zaragoza-es-web-espacio-de-datos-servicio-catalogo-6308"


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch, tmp_path):
    """Never read a real .env (the worktree sits below the repository that has one)."""
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.chdir(tmp_path)


def api(calls: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "data.europa.eu" and request.url.path == "/api/hub/search/search"
        assert request.url.params["filters"] == "dataset"
        assert "mobility-model-zoo-crawler" in request.headers["User-Agent"]
        body = PAGE if request.url.params["page"] == "0" else EMPTY
        return httpx.Response(200, json=body)

    return handler


def run(root: Path, calls: list[httpx.Request], limit: int = 20) -> tuple[Path, Path]:
    return base.harvest(
        DataEuropa(), root, base.Scope(languages=["es"], subdomains=["rail"]), limit=limit, run_id=None,
        say=print, transport=httpx.MockTransport(api(calls)),
        throttle=Throttle(clock=lambda: 0.0, sleep=lambda s: None),
    )


def lines(jsonl: Path) -> list[dict]:
    return [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_registry_and_attributes():
    h = get("data-europa")
    assert isinstance(h, DataEuropa)
    assert (h.name, h.catalogue, h.env_keys, h.modalities) == (
        "data-europa", "data.europa.eu", (), ("structured_data",))


def test_candidates_validate_and_follow_the_rules(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, calls)
    assert jsonl.exists() and header.exists()
    head = read_yaml(header)
    assert head["kind"] == "harvester:data-europa" and head["scope"]["modalities"] == ["structured_data"]
    found = lines(jsonl)
    # three terms for rail in es, each answered by the same page: deduplicated by landing URL;
    # the English-only Eurostat dataset is filtered out
    assert {c["landing_url"] for c in found} == {ANDALUCIA, BALEARES, ZARAGOZA}
    assert len(found) == 3 and len(calls) == 3
    assert all(c.url.params["q"] in ("ferrocarril", "tren de cercanías", "transporte ferroviario")
               for c in calls)
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    for cand in found:
        assert not list(validator.iter_errors(cand))
        assert "description" not in cand
        assert cand["level"] == "collection" and "parent" not in cand
        assert cand["subdomains"] == ["rail"] and cand["topics"] == ["productdev"]
        assert cand["origin_area"] == "ES" and cand["publisher"]["kind"] == "government"
        assert cand["personal_data"] == base.personal_data(cand["resource_type"]["genre"])
        assert cand["quality"]["score"] == 3 and "data.europa.eu" in cand["quality"]["rationale"]
        assert cand["provenance"] == {"method": "harvest", "evidence": [cand["landing_url"]]}
        assert all(r["auth"] == "none" and r["cost"] == "free" and r["provider_hint"] == "url"
                   for r in cand["access"])
        assert "@" not in json.dumps(cand)  # publisher e-mails never copied
    assert "Descripcion registrada" not in jsonl.read_text(encoding="utf-8")
    by_url = {c["landing_url"]: c for c in found}

    andalucia = by_url[ANDALUCIA]
    assert andalucia["title"] == {"original": "Ferrocarril (g09_21_Ferrocarril)",
                                  "en": "Railway (g09_21_Ferrocarril)"}
    assert andalucia["languages"] == [{"code": "es", "origin": "original"}]
    assert andalucia["licence"]["id"] == "CC-BY-4.0"
    assert andalucia["licence"]["evidence_url"] == ANDALUCIA
    assert andalucia["resource_type"] == {"modality": "structured_data", "genre": "geodata"}
    assert [r["method"] for r in andalucia["access"]] == ["api", "api", "page_by_page"]

    baleares = by_url[BALEARES]
    assert [lang["code"] for lang in baleares["languages"]] == ["es", "en"]
    assert baleares["licence"]["id"] == "CC-BY-4.0"
    csv = baleares["access"][0]
    assert csv["method"] == "direct_download" and csv["download_url"].endswith("estacio.csv")
    assert csv["formats"] == ["text/csv"] and csv["size_bytes_est"] == 20480

    zaragoza = by_url[ZARAGOZA]
    # no declared language: the original title language counts, with a note (owner decision 2026-10-11)
    assert zaragoza["languages"] == [{"code": "es", "origin": "original"}]
    assert zaragoza["quality"]["rationale"].endswith(TITLE_LANGUAGE_NOTE)
    assert TITLE_LANGUAGE_NOTE not in baleares["quality"]["rationale"]
    assert zaragoza["licence"]["id"] == "unknown" and zaragoza["licence"]["evidence_url"] is None
    assert {r["method"] for r in zaragoza["access"]} == {"api"}


def test_ingest_accepts_every_line(tmp_path):
    root = tmp_path / "cat"
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text("catalog_id: t\nschema_version: 1\n", encoding="utf-8")
    jsonl, header = run(root, [])
    outcome = ingest.ingest(model.load(root), jsonl, header, "2026-10-11")
    assert outcome["rejected"] == 0, outcome["rejected_lines"]
    assert outcome["accepted"] == 3


def test_limit_stops_early(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, _ = run(tmp_path, calls, limit=2)
    assert len(lines(jsonl)) == 2 and len(calls) == 1


def test_licence_and_area_mapping():
    spdx_url = {"resource": "http://spdx.org/licenses/CC-BY-4.0", "id": "CC_BY_4_0"}
    assert _licence_id(spdx_url) == "CC-BY-4.0"
    assert _licence_id("http://publications.europa.eu/resource/authority/licence/CC_BYNCSA_4_0") == \
        "CC-BY-NC-SA-4.0"
    assert _licence_id("CC0") == "CC0-1.0"
    assert _licence_id("http://www.opendefinition.org/licenses/cc-by") == "CC-BY-4.0"
    assert _licence_id("https://www.ine.es/aviso_legal") == "unknown"
    eurostat = PAGE["result"]["results"][3]
    assert _area(eurostat) == "EU"
    assert _area({"country": {"id": "EUROPE"}}) == "150"
    assert _area({}) == "001"
    wms = _route({"media_type": "https://www.iana.org/assignments/media-types/text/wms",
                  "access_url": ["https://example.org/wms"]})
    assert wms is not None and wms["method"] == "api" and wms["download_url"] is None


def test_other_modality_yields_nothing(tmp_path):
    calls: list[httpx.Request] = []
    scope = base.Scope(languages=["es"], subdomains=["rail"], modalities=["audio"])
    jsonl, _ = base.harvest(DataEuropa(), tmp_path, scope, limit=5, run_id=None, say=print,
                            transport=httpx.MockTransport(api(calls)),
                            throttle=Throttle(sleep=lambda s: None))
    assert lines(jsonl) == [] and calls == []


def dane(attrs: dict | None, calls: list[httpx.Request], status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "api.dane.gov.pl" and request.url.path == "/1.4/datasets/4187"
        return httpx.Response(status, json={"data": {"attributes": attrs or {}}})

    return httpx.Client(transport=httpx.MockTransport(handler))


DANE_ID = "https-dane-gov-pl-pl-dataset-4187-26820b94f4ef"


def test_dane_gov_pl_licence_read_from_the_portal_api():
    calls: list[httpx.Request] = []
    lic = dane_gov_pl_licence(DANE_ID, dane({"license_name": "CC BY 4.0", "license_chosen": 2}, calls))
    assert lic["id"] == "CC-BY-4.0"
    assert lic["evidence_url"] == "https://dane.gov.pl/pl/dataset/4187"
    assert lic["commercial_use"] == "yes" and lic["attribution_required"] == "yes"
    assert len(calls) == 1


@pytest.mark.parametrize("attrs", [
    {"license_name": "CC BY 4.0", "license_condition_custom_description": "Only with written consent."},
    {"license_name": "CC0 1.0", "license_condition_db_or_copyrighted": "Database rights apply."},
    {"license_name": None},
])
def test_dane_gov_pl_extra_conditions_or_no_licence_stay_unknown(attrs):
    lic = dane_gov_pl_licence(DANE_ID, dane(attrs, []))
    assert lic["id"] == "unknown" and lic["evidence_url"] is None


def test_dane_gov_pl_other_datasets_and_failures():
    calls: list[httpx.Request] = []
    andalucia = "-91ff7a79-ceb3-45a7-9686-c992634343ce-_100358_es"
    assert dane_gov_pl_licence(andalucia, dane({}, calls)) is None
    assert calls == []
    assert dane_gov_pl_licence(DANE_ID, dane({}, calls, status=503), say=lambda m: None) is None


def ckan(result: dict | None, calls: list[httpx.Request], status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "data.gov.lv"
        assert request.url.path == "/dati/api/3/action/package_show"
        assert request.url.params["id"] == "019e39ed-9d72"
        return httpx.Response(status, json={"success": status == 200, "result": result})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ckan_licence_read_from_a_national_portal():
    calls: list[httpx.Request] = []
    result = {"name": "eksporta-dati", "license_id": "CC-BY-4.0",
              "license_url": "https://creativecommons.org/licenses/by/4.0/"}
    lic = ckan_licence("data-gov-lv", "019e39ed-9d72~~1", ckan(result, calls))
    assert lic["id"] == "CC-BY-4.0"
    assert lic["evidence_url"] == "https://data.gov.lv/dati/lv/dataset/eksporta-dati"
    assert lic["url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert len(calls) == 1


def test_ckan_licence_unknown_other_portals_and_failures():
    calls: list[httpx.Request] = []
    unspecified = ckan({"name": "x", "license_id": "notspecified"}, calls)
    lic = ckan_licence("data-gov-lv", "019e39ed-9d72", unspecified)
    assert lic["id"] == "unknown" and lic["evidence_url"] is None
    assert ckan_licence("open-data-bulgaria", "4571", ckan({}, calls)) is None
    assert len(calls) == 1
    failing = ckan({}, calls, status=500)
    assert ckan_licence("data-gov-lv", "019e39ed-9d72", failing, say=lambda m: None) is None
