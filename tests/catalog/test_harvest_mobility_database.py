"""Mobility Database harvester against trimmed recorded responses (feature 009): no network."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import jsonschema
import pytest

from mobility_model_zoo.catalog import ingest, model
from mobility_model_zoo.catalog.checks import Throttle
from mobility_model_zoo.catalog.harvest import base, get
from mobility_model_zoo.catalog.harvest.mobility_database import (
    MobilityDatabase,
    feed_in_scope,
    feed_licence,
    provider_of,
)
from mobility_model_zoo.catalog.model import read_yaml, schema
from mobility_model_zoo.release.errors import CredentialError, UsageError

RECORDED = Path(__file__).resolve().parents[1] / "fixtures" / "catalog-http" / "mobility-database"
KEY = "MOBILITYDATABASE_REFRESH_TOKEN"
DUMMY = "dummy-refresh-token"
PAGE = "https://mobilitydatabase.org/feeds/{}/{}"


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch, tmp_path):
    """Never read a real .env (the worktree sits below the repository that has one)."""
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(KEY, DUMMY)


def recorded(name: str):
    return json.loads((RECORDED / name).read_text(encoding="utf-8"))


def api(calls: list[httpx.Request], token_status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "api.mobilitydatabase.org"
        if request.url.path == "/v1/tokens":
            assert request.method == "POST" and json.loads(request.content) == {"refresh_token": DUMMY}
            if token_status != 200:
                return httpx.Response(token_status, json={"detail": "invalid token"})
            return httpx.Response(200, json=recorded("tokens.json"))
        assert request.method == "GET" and request.headers["Authorization"] == "Bearer test-access-token"
        endpoint = request.url.path.removeprefix("/v1/")
        assert endpoint in ("gtfs_feeds", "gtfs_rt_feeds")
        country = request.url.params["country_code"]
        if request.url.params["offset"] != "0" or not (RECORDED / f"{endpoint}-{country}.json").exists():
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=recorded(f"{endpoint}-{country}.json"))

    return handler


def run(root: Path, calls: list[httpx.Request], *, areas=("ES", "JP"), limit: int = 20, **kw):
    scope = base.Scope(areas=list(areas), **kw)
    return base.harvest(MobilityDatabase(), root, scope, limit=limit, run_id=None, say=print,
                        transport=httpx.MockTransport(api(calls)),
                        throttle=Throttle(clock=lambda: 0.0, sleep=lambda s: None))


def lines(jsonl: Path) -> list[dict]:
    return [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_registry_and_attributes():
    h = get("mobility-database")
    assert isinstance(h, MobilityDatabase)
    assert (h.name, h.catalogue, h.env_keys, h.modalities) == (
        "mobility-database", "Mobility Database", (KEY,), ("structured_data",))


def test_candidates_validate_and_follow_the_rules(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, header = run(tmp_path, calls)
    assert jsonl.exists() and header.exists()
    head = read_yaml(header)
    assert head["kind"] == "harvester:mobility-database" and head["scope"]["areas"] == ["ES", "JP"]
    assert len(calls) == 5  # token + two endpoints x two countries, one page each
    found = lines(jsonl)
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    for cand in found:
        assert not list(validator.iter_errors(cand))
        assert "description" not in cand
        assert cand["level"] == "collection" and cand["subdomains"] == ["public_transport"]
        assert cand["languages"] == [{"code": "zxx", "origin": "original"}]
        assert cand["resource_type"]["modality"] == "structured_data"
        assert cand["personal_data"] == {"expectation": "none", "categories": []}
        assert cand["landing_url"].startswith("https://mobilitydatabase.org/feeds/gtfs")
        assert 1 <= len(cand["access"]) <= 5
        assert all(r["method"] == "feed" and r["cost"] == "free" for r in cand["access"])
        assert all(r["provider_hint"] == "mobilitydatabase" for r in cand["access"])
        lic = cand["licence"]
        assert (lic["evidence_url"] is None) == (lic["id"] == "unknown")
        assert "@" not in json.dumps(cand, ensure_ascii=False)
    by_title = {c["title"]["original"]: c for c in found}
    # inactive (AISA, 三条市) and mostly-French feeds (Nouvelle-Aquitaine, Pays Basque-Adour) are skipped
    assert len(found) == 8
    assert not any(k.startswith(("AISA", "Nouvelle", "Syndicat", "三条市")) for k in by_title)
    assert [c["origin_area"] for c in found] == ["ES"] * 4 + ["JP"] * 4

    emt = by_title["Empresa Malagueña de Transportes (EMT): GTFS and GTFS Realtime feeds"]
    assert emt["landing_url"] == PAGE.format("gtfs", "mdb-2212")
    assert emt["publisher"] == {"name": "Empresa Malagueña de Transportes (EMT)", "kind": "company"}
    assert emt["resource_type"]["genre"] == "gtfs"
    zip_, pb = ["application/zip"], ["application/x-protobuf"]
    assert [r["formats"] for r in emt["access"]] == [zip_, pb, pb, pb]
    assert emt["access"][0]["download_url"] == emt["access"][0]["url"]
    assert all(r["download_url"] is None for r in emt["access"][1:])
    assert emt["licence"]["id"] == "unknown" and emt["licence"]["evidence_url"] is None
    assert emt["identifiers"]["other"] == [f"mobilitydatabase:mdb-{n}" for n in (2212, 2213, 2214, 2215)]

    crtm = next(c for t, c in by_title.items() if t.startswith("Consorcio Regional"))
    assert crtm["publisher"]["kind"] == "government"
    assert crtm["licence"]["id"] == "unknown" and crtm["licence"]["url"] == "https://www.crtm.es/licencia-de-uso"

    ferry = by_title["El Transbordador de Vizcaya: GTFS feeds"]
    assert ferry["licence"]["id"] == "CC-BY-4.0"
    assert ferry["licence"]["evidence_url"] == "https://creativecommons.org/licenses/by/4.0/"

    alava = by_title["Alavabus: GTFS feeds"]
    assert alava["access"][0]["auth"] == "api_key" and "API key" in alava["access"][0]["notes"]

    city = by_title["一関市: GTFS feeds"]
    assert city["publisher"]["kind"] == "government" and city["licence"]["id"] == "CC-BY-4.0"

    mie = by_title["三重交通: GTFS feeds"]
    assert mie["publisher"]["kind"] == "company"
    assert len(mie["access"]) == 5 and len(mie["identifiers"]["other"]) == 6  # routes capped at five

    kurobe = by_title["黒部市: GTFS Realtime feeds"]
    assert kurobe["resource_type"]["genre"] == "gtfs_rt" and kurobe["licence"]["id"] == "CC0-1.0"
    assert kurobe["landing_url"].startswith("https://mobilitydatabase.org/feeds/gtfs_rt/")


def test_ingest_accepts_every_line(tmp_path):
    root = tmp_path / "cat"
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text("catalog_id: t\nschema_version: 1\n", encoding="utf-8")
    jsonl, header = run(root, [])
    outcome = ingest.ingest(model.load(root), jsonl, header, "2026-10-11")
    assert outcome["rejected"] == 0, outcome["rejected_lines"]
    assert outcome["accepted"] == 8


def test_limit_stops_early(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, _ = run(tmp_path, calls, limit=2)
    assert len(lines(jsonl)) == 2
    assert {c.url.params.get("country_code") for c in calls[1:]} == {"ES"}


@pytest.mark.parametrize("areas", [(), ("EU",)])
def test_needs_a_country(tmp_path, areas):
    calls: list[httpx.Request] = []
    with pytest.raises(UsageError, match="country"):
        run(tmp_path, calls, areas=areas)
    assert calls == []


def test_missing_key_is_exit_5(tmp_path, monkeypatch):
    monkeypatch.delenv(KEY)
    calls: list[httpx.Request] = []
    with pytest.raises(CredentialError, match=KEY) as err:
        run(tmp_path, calls)
    assert err.value.exit_code == 5 and calls == []


def test_refused_token_is_a_credential_error(tmp_path):
    calls: list[httpx.Request] = []
    with pytest.raises(CredentialError, match=KEY):
        base.harvest(MobilityDatabase(), tmp_path, base.Scope(areas=["ES"]), limit=5, run_id=None,
                     say=print, transport=httpx.MockTransport(api(calls, token_status=401)),
                     throttle=Throttle(sleep=lambda s: None))
    assert len(calls) == 1


def test_other_subdomain_yields_nothing(tmp_path):
    calls: list[httpx.Request] = []
    jsonl, _ = run(tmp_path, calls, subdomains=["cycling"])
    assert lines(jsonl) == [] and calls == []


def test_mapping_helpers():
    long = {"provider": "A OÜ, B AS, C OÜ, D AS, E OÜ"}
    assert provider_of(long) == "A OÜ and 4 others"
    assert provider_of({"provider": "Renfe, Cercanías"}) == "Renfe, Cercanías"
    spdx_but_unlisted = {"source_info": {"license_id": "CC-BY-2.0", "license_is_spdx": True,
                                         "license_url": "https://creativecommons.org/licenses/by/2.1/jp/"}}
    assert feed_licence(spdx_but_unlisted)[0] == "CC-BY-2.0"
    etalab = {"source_info": {"license_id": "etalab-2.0", "license_is_spdx": True}}
    assert feed_licence(etalab)[0] == "etalab-2.0"
    cc0 = "http://creativecommons.org/publicdomain/zero/1.0/"
    assert feed_licence({"source_info": {"license_url": cc0}}) == ("CC0-1.0", cc0)
    assert feed_licence({"source_info": None}) == ("unknown", None)
    cross_border = {"status": "active", "locations": [{"country_code": "FR"}, {"country_code": "FR"},
                                                      {"country_code": "ES"}]}
    assert not feed_in_scope(cross_border, "ES") and feed_in_scope(cross_border, "FR")
    assert not feed_in_scope({"status": "deprecated", "locations": []}, "ES")


def test_secret_query_parameters_never_reach_the_catalog():
    from mobility_model_zoo.catalog.harvest.base import strip_secrets

    url = "https://transport.data.gouv.fr/resources/1/download?token=abc&format=zip&apiKey=x"
    assert strip_secrets(url) == "https://transport.data.gouv.fr/resources/1/download?format=zip"
    assert strip_secrets("https://example.org/feed.zip") == "https://example.org/feed.zip"
