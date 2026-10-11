"""Discovery runs → entries (feature 009 FR-019, FR-022, research R7, T039)."""

from __future__ import annotations

import copy
import json

import pytest
import yaml
from typer.testing import CliRunner

from mobility_model_zoo.catalog import ingest
from mobility_model_zoo.catalog.model import load
from mobility_model_zoo.release.cli import app

runner = CliRunner()
DAY = "2026-10-11"


def _candidate(n: int, **over):
    c = {
        "level": "item",
        "title": {"original": f"Informe de tráfico número {n}", "en": f"Traffic report number {n}"},
        "languages": [{"code": "es", "origin": "original"}],
        "origin_area": "ES",
        "publisher": {"name": f"Ayuntamiento de Ejemplo {n}", "kind": "government"},
        "landing_url": f"https://example.org/new/{n}",
        "resource_type": {"modality": "text", "genre": "report"},
        "topics": ["productdev"],
        "subdomains": ["road"],
        "licence": {
            "id": "CC-BY-4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "evidence_url": f"https://example.org/new/{n}",
            "attribution_required": "yes",
            "commercial_use": "yes",
            "derivatives": "yes",
        },
        "personal_data": {"expectation": "possible", "categories": ["names"]},
        "access": [
            {
                "method": "direct_download",
                "url": f"https://example.org/new/{n}/pdf",
                "auth": "none",
                "cost": "free",
            }
        ],
        "quality": {"score": 3, "rationale": "harvested from a test; authority: government"},
        "provenance": {"method": "harvest", "evidence": [f"https://example.org/new/{n}"]},
    }
    c.update(over)
    return c


def _run_files(tmp_path, lines, scope=None):
    jsonl = tmp_path / "run.jsonl"
    jsonl.write_text("".join(json.dumps(x) + "\n" if isinstance(x, dict) else x + "\n" for x in lines))
    header = tmp_path / "run.yaml"
    header.write_text(
        yaml.safe_dump(
            {
                "id": "2026-10-11-test",
                "date": DAY,
                "kind": "agent",
                "scope": scope
                or {
                    "languages": ["es", "ja"],
                    "areas": ["ES"],
                    "subdomains": ["road"],
                    "modalities": ["text", "video"],
                },
                "method": "test",
                "agent": {"tool": "claude-code", "model_id": "claude-opus-5-5"},
                "cost": {"cash_eur": 0},
                "outcome": {},
            }
        )
    )
    return jsonl, header


@pytest.fixture
def ten(catalog_dir):
    cat = load(catalog_dir)
    existing = cat.entries["es-mitma-informes"]
    lines = [_candidate(i) for i in range(1, 8)]
    lines.append(_candidate(8, landing_url="https://www.example.org/es-mitma-informes/"))  # same address
    doi_twin = _candidate(9, identifiers={"doi": "10.5555/abc"})
    lines.append(doi_twin)
    bad = _candidate(10)
    bad["provenance"] = {"method": "harvest", "evidence": []}
    lines.append(bad)
    return cat, existing, lines


def test_ten_candidates(ten, tmp_path):
    cat, existing, lines = ten
    # the DOI twin matches an entry that carries the same DOI
    existing["identifiers"] = {"doi": "10.5555/ABC"}
    cat.write_entry(existing)
    jsonl, header = _run_files(tmp_path, lines)
    out = ingest.ingest(cat, jsonl, header, DAY)
    assert (out["proposed"], out["accepted"], out["merged"], out["rejected"]) == (10, 7, 2, 1)
    assert out["rejected_lines"][0]["line"] == 10 and "evidence" in out["rejected_lines"][0]["reason"]
    stored = yaml.safe_load(header.read_text())["outcome"]
    cells = {(c["language"], c["modality"]): c for c in stored["by_cell"]}
    assert cells[("ja", "video")] == {
        "language": "ja",
        "modality": "video",
        "proposed": 0,
        "accepted": 0,
    }
    assert cells[("es", "text")]["accepted"] == 7
    merged = load(cat.root).entries["es-mitma-informes"]
    assert any(a["url"].endswith("/new/9/pdf") for a in merged["access"])
    new = [
        e
        for e in load(cat.root).entries.values()
        if e["provenance"]["added_by"] == "run:2026-10-11-test"
    ]
    assert len(new) == 7 and all(e["status"]["value"] == "candidate" for e in new)
    assert all(e["id"].startswith("es-ayuntamiento-de-ejemplo-") for e in new)


def test_fuzzy_match_is_flagged_not_merged(catalog_dir, tmp_path):
    cat = load(catalog_dir)
    twin = _candidate(
        1,
        title={"original": "Informes de movilidad", "en": "Mobility reports"},
        publisher={"name": "Ministerio de Ejemplo", "kind": "government"},
    )
    jsonl, header = _run_files(tmp_path, [twin])
    out = ingest.ingest(cat, jsonl, header, DAY)
    assert out["accepted"] == 1
    new = next(
        e for e in load(cat.root).entries.values() if e["provenance"]["added_by"].startswith("run:")
    )
    assert "possible_duplicate" in new["status"]["flags"]
    assert "es-mitma-informes" in new["relations"]["possible_duplicates"]


@pytest.mark.parametrize("field", ["status", "usage", "signals", "checks", "fetched"])
def test_candidates_must_not_carry_derived_fields(catalog_dir, tmp_path, field):
    cat = load(catalog_dir)
    jsonl, header = _run_files(tmp_path, [_candidate(1, **{field: {"value": "cleared"}})])
    assert ingest.ingest(cat, jsonl, header, DAY)["rejected"] == 1


def test_cli_exits_1_when_more_than_20_percent_fail(catalog_dir, tmp_path):
    lines = [
        _candidate(1),
        _candidate(2),
        "{not json",
        copy.deepcopy(_candidate(3)) | {"subdomains": []},
    ]
    jsonl, header = _run_files(tmp_path, lines)
    res = runner.invoke(
        app, ["catalog", "--catalog", str(catalog_dir), "ingest", str(jsonl), "--run", str(header)]
    )
    assert res.exit_code == 1 and "> 20%" in res.output


def test_new_adds_one_owner_entry(catalog_dir, tmp_path):
    f = tmp_path / "one.yaml"
    f.write_text(yaml.safe_dump(_candidate(42)))
    res = runner.invoke(app, ["catalog", "--catalog", str(catalog_dir), "new", "--from", str(f)])
    assert res.exit_code == 0, res.output
    e = next(e for e in load(catalog_dir).entries.values() if e["landing_url"].endswith("/new/42"))
    assert e["provenance"]["added_by"] == "owner"
    again = runner.invoke(app, ["catalog", "--catalog", str(catalog_dir), "new", "--from", str(f)])
    assert again.exit_code == 0 and "merged" in again.output


def test_ids_are_unique_and_short():
    taken = {"es-x-y"}
    c = _candidate(1, publisher={"name": "X", "kind": "government"}, title={"original": "y", "en": "Y"})
    assert ingest.make_id(c, taken) == "es-x-y-2"
    long = _candidate(1, title={"original": "t", "en": "word " * 40})
    assert len(ingest.make_id(long, set())) <= 80
    ja = _candidate(
        1,
        title={"original": "公共交通", "en": "公共交通"},
        publisher={"name": "交通局", "kind": "government"},
    )
    assert len(ingest.make_id(ja, set())) >= 3
