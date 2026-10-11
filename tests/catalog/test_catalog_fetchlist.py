"""Fetch lists and the hand-off to the registers (feature 009 US4, FR-028, T061)."""

from __future__ import annotations

import jsonschema
import pytest
from typer.testing import CliRunner

from mobility_model_zoo.catalog import fetchlist, states
from mobility_model_zoo.catalog.model import load, schema
from mobility_model_zoo.compliance.register import schema as register_schema
from mobility_model_zoo.datasets import UsageRefused
from mobility_model_zoo.release.cli import app

runner = CliRunner()
DAY = "2026-10-11"
FETCH_TIME = {
    "storage": "data/snapshots (outside git)",
    "retention_until": "2028-10-11",
    "crawl_manifest_sha256": None,
}


def _doc(catalog_dir):
    cat = load(catalog_dir)
    return cat, fetchlist.build(
        cat, sorted(cat.entries.values(), key=lambda e: e["id"]), "all", "(all)", DAY
    )


def test_only_cleared_entries_become_items(catalog_dir):
    cat, doc = _doc(catalog_dir)
    jsonschema.validate(doc, schema("fetch-list"))
    cleared = {e["id"] for e in cat.entries.values() if e["status"]["value"] == "cleared"}
    assert {i["entry_id"] for i in doc["items"]} == cleared
    refused = {r["entry_id"]: r["reason"] for r in doc["refused"]}
    assert set(refused) == set(cat.entries) - cleared
    assert refused["pl-radio-transport"].startswith("status verified")


def test_proposed_records_validate_against_the_registers(catalog_dir):
    _, doc = _doc(catalog_dir)
    by = {i["entry_id"]: i for i in doc["items"]}
    text = by["es-mitma-informes"]
    assert text["target_register"] == "sources"
    jsonschema.validate({"sources": [text["proposed_record"] | FETCH_TIME]}, register_schema("sources"))
    data = by["pl-stat-transport-tables"]
    assert data["target_register"] == "datasets"
    assert data["proposed_record"]["locator"] == {
        "urls": ["https://example.org/pl-stat-transport-tables/data.zip"]
    }
    jsonschema.validate(
        {"datasets": [data["proposed_record"] | FETCH_TIME]}, register_schema("datasets")
    )
    nc = by["br-podcast-mobilidade"]["proposed_record"]
    assert nc["permitted_use"] == "benchmark_only" and nc["licence"] == "CC-BY-NC-4.0"


def test_withdrawn_is_never_an_item(catalog_dir):
    cat = load(catalog_dir)
    e = cat.entries["pl-stat-transport-tables"]
    states.set_status(e, "withdrawn", DAY, "objection", request_id="REQ-1")
    doc = fetchlist.build(cat, [e], "x", "x", DAY)
    assert doc["items"] == [] and doc["refused"][0]["reason"].startswith("status withdrawn")


def test_cli_writes_the_list_and_refuses_an_empty_one(catalog_dir):
    ok = runner.invoke(
        app, ["catalog", "--catalog", str(catalog_dir), "fetchlist", "spanish", "--lang", "es"]
    )
    assert ok.exit_code == 0, ok.output
    [path] = (catalog_dir / "fetch-lists").glob("*-spanish.yaml")
    doc = fetchlist.read(path)
    assert {i["entry_id"] for i in doc["items"]} == {"es-mitma-informes", "es-mitma-informe-2025"}
    assert doc["selection"] == "--lang es"
    empty = runner.invoke(
        app, ["catalog", "--catalog", str(catalog_dir), "fetchlist", "none", "--lang", "ja"]
    )
    assert empty.exit_code == 3


def test_link_and_require_cleared(catalog_dir, tmp_path):
    import datetime as dt

    from mobility_model_zoo.catalog import require_cleared

    cat = load(catalog_dir)
    assert require_cleared("pl-stat-transport-tables", cat, dt.date(2026, 10, 20))["id"]
    with pytest.raises(UsageRefused):
        require_cleared("pl-stat-transport-tables", cat, dt.date(2027, 6, 1))  # verified > 180 days ago
    with pytest.raises(UsageRefused):
        require_cleared("eu-maps-mixed", cat)
    zoo = tmp_path / "zoo"
    (zoo / "topics" / "productdev" / "compliance").mkdir(parents=True)
    (zoo / "topics" / "productdev" / "compliance" / "datasets.yaml").write_text(
        "datasets:\n- id: pl-stat-transport-tables\n"
    )
    args = ["catalog", "--catalog", str(catalog_dir), "link", "pl-stat-transport-tables"]
    missing = runner.invoke(app, args + ["datasets:productdev:nope", "--zoo-root", str(zoo)])
    assert missing.exit_code == 3
    ok = runner.invoke(
        app, args + ["datasets:productdev:pl-stat-transport-tables", "--zoo-root", str(zoo)]
    )
    assert ok.exit_code == 0, ok.output
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert e["status"]["value"] == "fetched" and e["fetched"]["record_id"] == "pl-stat-transport-tables"
