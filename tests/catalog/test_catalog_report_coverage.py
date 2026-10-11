"""Coverage report (feature 009 US2, FR-026, SC-004, T030)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mobility_model_zoo.catalog import reports
from mobility_model_zoo.catalog.model import load, vocab
from mobility_model_zoo.release.cli import app

runner = CliRunner()


def test_counts_and_gaps(catalog_dir):
    rep = reports.coverage(load(catalog_dir))
    assert rep["entries"] == 12
    assert rep["by_permitted_use"] == {
        "benchmark_only": 2,
        "not_usable": 1,
        "training_allowed": 6,
        "undetermined": 3,
    }
    assert rep["licence_determined"] == {"entries": 11, "share": 0.9167}
    assert rep["derived_languages"] == [{"language": "en", "origin": "machine_translated", "entries": 1}]
    cells = {(c["language"], c["modality"]): c for c in rep["by_language_modality"]}
    assert ("en", "text") not in cells  # machine-translated English is not counted as original
    assert cells[("es", "text")]["entries"] == 2 and cells[("es", "text")]["volume"] == {"items": 41}
    assert cells[("pt", "video")]["volume"] == {"hours": 12}
    assert rep["gaps"]["modalities"] == ["graphic"]
    assert "es" not in rep["gaps"]["languages"] and "pl" not in rep["gaps"]["languages"]
    assert set(rep["gaps"]["languages"]) == set(vocab().targets) - {"es", "pl", "pt"}
    assert {"catalog_commit", "catalog_sha256", "vocab_version"} <= rep.keys()


def test_cli_writes_markdown_and_json(catalog_dir, tmp_path):
    out = tmp_path / "rep"
    res = runner.invoke(
        app, ["catalog", "--catalog", str(catalog_dir), "report", "coverage", "--out", str(out)]
    )
    assert res.exit_code == 0, res.output
    md = next(out.glob("*-coverage.md")).read_text()
    assert "## Licence determined" in md and "## Gaps" in md and "| es | text | 2 | 2 | 41 items |" in md
    data = json.loads(next(out.glob("*-coverage.json")).read_text())
    assert data["entries"] == 12
    assert "gaps (modalities): graphic" in res.stdout
