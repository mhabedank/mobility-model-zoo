"""Withdrawal after an objection (feature 009 US5, FR-021, T068)."""

from __future__ import annotations

import yaml
from typer.testing import CliRunner

from mobility_model_zoo.catalog import fetchlist
from mobility_model_zoo.catalog.model import load
from mobility_model_zoo.compliance import signals
from mobility_model_zoo.compliance.hashing import keyed_hash
from mobility_model_zoo.release.cli import app

runner = CliRunner()


def _zoo(tmp_path, kind="objection"):
    zoo = tmp_path / "zoo"
    (zoo / "compliance").mkdir(parents=True, exist_ok=True)
    (zoo / "compliance" / "requests.yaml").write_text(
        yaml.safe_dump(
            {
                "requests": [
                    {
                        "id": "r-2026-10-11-001",
                        "type": kind,
                        "received_at": "2026-10-11",
                        "deadline": "2026-11-10",
                        "identifier_hash": "0" * 64,
                        "stores_searched": [],
                        "action": "",
                        "suppression_added": False,
                        "answered_at": None,
                    }
                ]
            }
        )
    )
    (zoo / "compliance" / "suppression.yaml").write_text("entries: []\n")
    return zoo


def _withdraw(catalog_dir, zoo, request="r-2026-10-11-001"):
    return runner.invoke(
        app,
        [
            "catalog",
            "--catalog",
            str(catalog_dir),
            "withdraw",
            "pl-stat-transport-tables",
            "--request",
            request,
            "--zoo-root",
            str(zoo),
        ],
    )


def test_unknown_request_is_refused(catalog_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_SUPPRESSION_KEY", "k" * 64)
    assert _withdraw(catalog_dir, _zoo(tmp_path), "r-nope").exit_code == 3
    assert _withdraw(catalog_dir, _zoo(tmp_path, kind="access")).exit_code == 3


def test_withdraw_sets_status_and_suppresses(catalog_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_SUPPRESSION_KEY", "k" * 64)
    zoo = _zoo(tmp_path)
    res = _withdraw(catalog_dir, zoo)
    assert res.exit_code == 0, res.output
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert e["status"]["value"] == "withdrawn" and e["status"]["request_id"] == "r-2026-10-11-001"
    assert e["status"]["reason"]
    hashes = {
        x["hash"]
        for x in yaml.safe_load((zoo / "compliance" / "suppression.yaml").read_text())["entries"]
    }
    landing = keyed_hash(signals.canonical(e["landing_url"]))
    assert landing in hashes and len(hashes) == 3  # landing, access url, download url
    lists = signals.Lists(suppressed_url_hashes=hashes)
    verdict, _ = signals.check_url(e["landing_url"], lists, url_hash=lambda u: keyed_hash(u))
    assert ("C-F5", "URL on the suppression list") in verdict.reasons
    doc = fetchlist.build(load(catalog_dir), [e], "x", "x", "2026-10-11")
    assert doc["items"] == []


def test_withdraw_needs_the_key(catalog_dir, tmp_path, monkeypatch):
    monkeypatch.delenv("MMZ_SUPPRESSION_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    assert _withdraw(catalog_dir, _zoo(tmp_path)).exit_code == 5
