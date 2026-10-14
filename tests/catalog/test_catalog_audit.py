"""Independent re-check and duplicate audit (feature 009 SC-005, SC-008, research R8, T075)."""

from __future__ import annotations

import httpx
from typer.testing import CliRunner

from mobility_model_zoo.catalog import audit
from mobility_model_zoo.catalog.model import load
from mobility_model_zoo.release.cli import app

runner = CliRunner()
FAST = audit.Throttle(sleep=lambda s: None)
PAGES = {
    "CC-BY-4.0": '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>',
    "CC-BY-NC-4.0": "Licensed under CC BY-NC 4.0.",
    "CC0-1.0": "Dedicated to the public domain under CC0.",
    "LicenseRef-proprietary": "© Example. All rights reserved.",
    "mixed": "Licences vary per dataset.",
    "etalab-2.0": "Licence Ouverte / Etalab 2.0",
}


def _web(cat, override=None):
    by_url = {
        e["licence"]["evidence_url"]: e["licence"]["id"]
        for e in cat.entries.values()
        if e["licence"].get("evidence_url")
    }

    def handler(req):
        lid = by_url.get(str(req.url))
        body = (override or {}).get(lid, PAGES.get(lid, "nothing here"))
        return httpx.Response(
            200, text=f"<html><body>{body}</body></html>", headers={"content-type": "text/html"}
        )

    return httpx.MockTransport(handler)


def test_matcher_reads_common_licences():
    assert audit.match_licence("see https://creativecommons.org/licenses/by-sa/4.0/ ") == "CC-BY-SA-4.0"
    assert audit.match_licence("CC BY-NC-ND 4.0") == "CC-BY-NC-ND-4.0"
    assert audit.match_licence("Todos los derechos reservados") == "LicenseRef-proprietary"
    assert audit.match_licence("nothing") == "unknown"


def test_agreement_passes_on_the_fixture_with_a_second_reader(catalog_dir):
    cat = load(catalog_dir)
    seen = []

    def reader(text):
        seen.append(text)
        return audit.match_licence(text)

    rep = audit.run(
        cat, sample=30, dup_sample=50, seed=9, transport=_web(cat), reader=reader, throttle=FAST
    )
    assert rep["agreement"]["matcher"] == 1.0 and rep["agreement"]["model"] == 1.0
    assert rep["passed"], rep["failures"]
    assert rep["duplicate_audit"]["rate"] == 0.0 and rep["duplicate_audit"]["sample"] == 12
    assert len(rep["sample_ids"]) == len(seen) == 11  # every entry with a determined licence
    assert "All rights reserved" not in str(rep)  # page text is never stored


def test_cleared_entry_read_as_unusable_fails(catalog_dir):
    cat = load(catalog_dir)
    rep = audit.run(
        cat, sample=30, seed=9, transport=_web(cat, {"CC0-1.0": "All rights reserved"}), throttle=FAST
    )
    assert "global-street-photos" in rep["unusable_cleared"] and not rep["passed"]


def test_duplicates_are_counted(catalog_dir):
    cat = load(catalog_dir)
    e = cat.entries["eu-maps-mixed"]
    e["landing_url"] = cat.entries["pl-stat-transport-tables"]["landing_url"]
    rep = audit.run(cat, sample=0, dup_sample=50, seed=9, transport=_web(cat), throttle=FAST)
    assert rep["duplicate_audit"]["rate"] > 0.02 and not rep["passed"]


def test_cli_writes_report(catalog_dir, monkeypatch):
    import mobility_model_zoo.catalog.audit as mod

    real_run = mod.run
    monkeypatch.setattr(
        mod, "run", lambda cat, **kw: real_run(cat, transport=_web(cat), throttle=FAST, **kw)
    )
    res = runner.invoke(
        app, ["catalog", "--catalog", str(catalog_dir), "audit", "--sample", "5", "--seed", "3"]
    )
    assert res.exit_code == 0, res.output
    md = next((catalog_dir / "reports").glob("*-audit.md")).read_text()
    assert "Deterministic matcher: 100%" in md and "Local model: not run" in md


def test_unreadable_evidence_is_reported_apart(catalog_dir):
    """Audit 2026-10-14: a Zenodo record that did not answer counted as a disagreement."""
    cat = load(catalog_dir)

    def handler(req):
        return httpx.Response(503)

    rep = audit.run(cat, sample=30, seed=9, transport=httpx.MockTransport(handler), throttle=FAST)
    assert rep["unread"] == rep["sample_ids"] and rep["agreement"]["matcher"] is None
    assert rep["unusable_cleared"] == []
    assert "Evidence not readable" in audit.render(rep)
