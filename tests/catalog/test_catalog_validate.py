"""Offline checks K1, K2, K8, K9 and `zoo catalog validate` (feature 009 US1, T017)."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from mobility_model_zoo.catalog.model import licence_allowlist, load
from mobility_model_zoo.catalog.validate import k1, k9, offline
from mobility_model_zoo.release.cli import app

runner = CliRunner()


def _lines(findings):
    return [f.line() for f in findings]


def test_valid_fixture_catalog_has_no_failure(catalog_dir):
    cat = load(catalog_dir)
    assert len(cat.entries) == 12
    findings = offline(cat, allowlist=licence_allowlist())
    assert [f for f in findings if f.severity == "fail"] == []


def test_each_invalid_fixture_fails_with_its_check(invalid_dir):
    cat = load(invalid_dir)
    lines = _lines(offline(cat, allowlist=licence_allowlist()))
    expected = {
        "bad-no-licence": "K1 (entry): 'licence' is a required property",
        "bad-kind-blog": "K1 publisher.kind: 'blog' is not in vocab source-kinds",
        "bad-zxx-with-es": "K1 languages: zxx and und cannot be combined with other codes",
        "bad-missing-parent": "K2 parent: parent no-such-collection does not exist",
        "bad-evidence-null": "K1 licence.evidence_url",
        "bad-no-subdomain": "K1 subdomains: no mobility subdomain: out of scope (FR-003)",
        "bad-email-in-description": "K9 description: contact data (email)",
    }
    for eid, text in expected.items():
        assert any(line.startswith(f"FAIL {eid} ") and text in line for line in lines), (eid, lines)


def _entry(catalog_dir, eid="pl-stat-transport-tables"):
    return load(catalog_dir).entries[eid]


def test_genre_outside_its_modality_fails(catalog_dir):
    e = _entry(catalog_dir)
    e["resource_type"]["genre"] = "podcast"
    assert any("resource_type.genre" in line for line in _lines(k1(e)))


def test_sandbox_topic_fails(catalog_dir):
    e = _entry(catalog_dir)
    e["topics"] = ["sandbox"]
    assert any("topics[0]" in line for line in _lines(k1(e)))


def test_description_longer_than_600_chars_fails(catalog_dir):
    e = _entry(catalog_dir)
    e["description"] = "x" * 601
    assert any(line.startswith(f"FAIL {e['id']} K1 description") for line in _lines(k1(e)))


def test_und_cannot_be_combined(catalog_dir):
    e = _entry(catalog_dir)
    e["languages"] = [{"code": "und", "origin": "unknown"}, {"code": "pl", "origin": "original"}]
    assert any("cannot be combined" in line for line in _lines(k1(e)))


def test_k9_phone_fails_and_handles_warn(catalog_dir):
    e = _entry(catalog_dir)
    e["publisher"]["name"] = "Redaktion, Tel. +49 30 1234 5678"
    e["landing_url"] = "https://social.test/@mobilitaetsfan"
    e["access"][0]["url"] = "https://forum.test/user/heinz"
    findings = k9(e)
    assert any(f.severity == "fail" and f.field == "publisher.name" for f in findings)
    warns = [f for f in findings if f.severity == "warn"]
    assert {f.field for f in warns} >= {"landing_url", "access[0].url"}
    assert all(f.flag == "personal_data_in_metadata" for f in warns)


def test_cli_validate_exit_codes(catalog_dir, invalid_dir):
    ok = runner.invoke(app, ["catalog", "--catalog", str(catalog_dir), "validate"])
    assert ok.exit_code == 0, ok.output
    bad = runner.invoke(app, ["catalog", "--catalog", str(invalid_dir), "validate"])
    assert bad.exit_code == 1
    assert "FAIL bad-kind-blog K1" in bad.output


def test_validate_runs_without_a_zoo_checkout(catalog_dir, tmp_path, monkeypatch):
    """The licence allow-list comes from package data; --zoo-root makes the repository copy win."""
    import mobility_model_zoo.catalog.model as model

    monkeypatch.chdir(tmp_path)
    data = model.DATA_DIR / "lists" / "licence-allowlist.yaml"
    repo_copy = Path(__file__).resolve().parents[2] / "compliance" / "lists" / "licence-allowlist.yaml"
    created = not model.DATA_DIR.exists()
    if created:
        data.parent.mkdir(parents=True, exist_ok=True)
        data.write_text(repo_copy.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(model, "zoo_repo_root", lambda: None)
    try:
        assert {"id": "CC0-1.0"} in model.licence_allowlist()
        res = runner.invoke(app, ["catalog", "--catalog", str(catalog_dir), "validate"])
        assert res.exit_code == 0, res.output
        zoo = tmp_path / "zoo-root"
        (zoo / "compliance" / "lists").mkdir(parents=True)
        (zoo / "compliance" / "lists" / "licence-allowlist.yaml").write_text("licences:\n- {id: MIT}\n")
        assert model.licence_allowlist(zoo) == [{"id": "MIT"}]
    finally:
        if created:
            shutil.rmtree(model.DATA_DIR)


def test_missing_catalog_exits_5(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["catalog", "--catalog", str(tmp_path / "nope"), "validate"])
    assert res.exit_code == 5
    assert "catalog repository not found" in res.output
