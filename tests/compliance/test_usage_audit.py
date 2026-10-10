"""`zoo compliance usage`: the audit of every model's usage class (feature 011, T035, SC-004)."""

import hashlib
import json
import time
from pathlib import Path

from typer.testing import CliRunner

from mobility_model_zoo.compliance.register import Register
from mobility_model_zoo.compliance.usage import audit
from mobility_model_zoo.release.cli import app

ROOT = Path(__file__).resolve().parents[2]
MODELS = {"scout-large", "sandbox-pipeline-tiny", "hum-fan", "pace-cnn", "picket-forest", "picket-mlp"}


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for sub in ("zoo", "compliance", "topics"):
        for path in sorted((root / sub).rglob("*")):
            if path.is_file():
                h.update(path.as_posix().encode() + path.read_bytes())
    return h.hexdigest()


def test_audit_covers_every_model_offline_fast_and_read_only():
    before = tree_hash(ROOT)
    start = time.monotonic()
    rows = audit(ROOT, Register.load(ROOT))
    assert time.monotonic() - start < 60
    assert {r["model"] for r in rows} == MODELS
    assert all(r["derived"] and r["declared"] for r in rows)
    assert tree_hash(ROOT) == before


def test_audit_of_the_zoo_today():
    rows = {r["model"]: r for r in audit(ROOT, Register.load(ROOT))}
    assert rows["hum-fan"]["derived"] == "commercial-share-alike"
    assert rows["hum-fan"]["restricting_inputs"][0]["id"] == "mimii"
    assert rows["scout-large"]["derived"] == "commercial"
    assert all(not r["findings"] for r in rows.values()), rows


def test_unresolved_free_text_licence_is_c_u1(tmp_path):
    from mobility_model_zoo.compliance.usage import Derivation, LicenceList, _add_source

    out = Derivation()
    _add_source(tmp_path, out, {"origin": "https://example.org/x", "license": "ask the author",
                                "permitted_use": "training_allowed"},
                LicenceList.load(ROOT), {}, {})
    assert [f.check_id for f in out.findings] == ["C-U1"]


def test_cli_text_and_json(monkeypatch):
    monkeypatch.chdir(ROOT)
    runner = CliRunner()
    result = runner.invoke(app, ["compliance", "usage", "--model", "hum-fan"])
    assert result.exit_code == 0, result.output
    assert "hum-fan  declared commercial-share-alike  derived commercial-share-alike" in result.output
    result = runner.invoke(app, ["compliance", "usage", "--json"])
    assert result.exit_code == 0
    assert {r["model"] for r in json.loads(result.output)} == MODELS
    result = runner.invoke(app, ["compliance", "usage", "--model", "nope"])
    assert result.exit_code == 2
