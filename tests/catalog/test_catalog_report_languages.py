"""Language report (feature 009 US6, FR-027, research R9, T072)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from mobility_model_zoo.catalog import reports
from mobility_model_zoo.catalog.model import load
from mobility_model_zoo.release.cli import app

runner = CliRunner()
REPO = Path(__file__).resolve().parents[2]


def test_rows_for_scout_large(catalog_dir):
    rep = reports.languages(load(catalog_dir), REPO)
    rows = {r["language"]: r for r in rep["languages"]}
    assert rows["es"]["entries"] == 3 and rows["es"]["cleared"] == 2
    scout = rows["es"]["models"]["scout-large"]
    assert scout == {
        "base_model": "FacebookAI/xlm-roberta-large",
        "base_covers": "yes",
        "training_share": 0.0,
    }
    assert rows["mt"]["models"]["scout-large"]["base_covers"] == "no" and rows["mt"]["entries"] == 0
    assert rows["de"]["models"]["scout-large"]["training_share"] == 0.28
    assert "zxx" not in rows and "und" not in rows
    assert {"catalog_commit", "catalog_sha256"} <= rep.keys()


def test_unknown_base_model(catalog_dir, tmp_path):
    zoo = tmp_path / "zoo-root"
    (zoo / "zoo" / "models" / "x").mkdir(parents=True)
    (zoo / "zoo" / "models" / "x" / "model.yaml").write_text(
        "base_model: someone/new-encoder\nlanguages: [es]\n"
    )
    rows = {r["language"]: r for r in reports.languages(load(catalog_dir), zoo)["languages"]}
    assert rows["es"]["models"]["x"]["base_covers"] == "unknown"


def test_cli(catalog_dir, tmp_path):
    out = tmp_path / "r"
    res = runner.invoke(
        app,
        [
            "catalog",
            "--catalog",
            str(catalog_dir),
            "report",
            "languages",
            "--out",
            str(out),
            "--zoo-root",
            str(REPO),
        ],
    )
    assert res.exit_code == 0, res.output
    md = next(out.glob("*-languages.md")).read_text()
    assert "Languages a current base model does not cover: mt" in md
    assert json.loads(next(out.glob("*-languages.json")).read_text())["languages"]
