"""`zoo catalog query` (feature 009 US2, FR-025, T029)."""

from __future__ import annotations

import json

import jsonschema
from typer.testing import CliRunner

from mobility_model_zoo.catalog.model import load, schema
from mobility_model_zoo.catalog.query import select
from mobility_model_zoo.release.cli import app

runner = CliRunner()


def _ids(catalog_dir, **filters):
    return [e["id"] for e in select(load(catalog_dir).entries.values(), **filters)]


def test_and_across_or_within(catalog_dir):
    assert _ids(catalog_dir, lang=["es", "pt"], modality=["video"], use=["training_allowed"]) == [
        "pt-lecture-cycling"
    ]
    assert _ids(catalog_dir, lang=["es"], status=["cleared"]) == [
        "es-mitma-informe-2025",
        "es-mitma-informes",
    ]
    assert _ids(catalog_dir, use=["undetermined"]) == [
        "eu-maps-mixed",
        "fr-charts-mobilite",
        "jp-infographic-traffic",
    ]


def test_transcripts(catalog_dir):
    assert _ids(catalog_dir, transcripts="yes") == [
        "es-parlamento-comision-transportes",
        "fr-charts-mobilite",
        "pt-lecture-cycling",
    ]
    assert _ids(catalog_dir, lang=["en"]) == ["es-mitma-informes"]
    assert _ids(catalog_dir, lang=["en"], include_transcripts=True) == [
        "es-mitma-informes",
        "pt-lecture-cycling",
    ]


def test_origin_and_quality(catalog_dir):
    assert _ids(catalog_dir, origin=["machine_translated"]) == ["es-mitma-informes"]
    assert _ids(catalog_dir, min_quality=4) == []


def test_cli_formats(catalog_dir):
    args = [
        "catalog",
        "--catalog",
        str(catalog_dir),
        "query",
        "--lang",
        "es",
        "--lang",
        "pt",
        "--modality",
        "video",
        "--use",
        "training_allowed",
    ]
    ids = runner.invoke(app, args + ["--format", "ids"])
    assert ids.exit_code == 0 and ids.stdout.split() == ["pt-lecture-cycling"]
    js = runner.invoke(app, args + ["--format", "json"])
    data = json.loads(js.stdout)
    jsonschema.validate(data[0], schema("entry"))
    table = runner.invoke(app, args)
    assert table.exit_code == 0 and "pt-lecture-cycling\tpt\tPT\tvideo/lecture" in table.stdout
    assert runner.invoke(app, args + ["--format", "xml"]).exit_code == 2
