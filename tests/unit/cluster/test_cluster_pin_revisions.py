"""Pinning model revisions in the cluster settings (feature 009, T008). No network."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "topics" / "productdev" / "scripts" / "cluster" / "pin_revisions.py"
spec = importlib.util.spec_from_file_location("pin_revisions", SCRIPT)
pin_revisions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pin_revisions)


def test_pin_replaces_null_revisions_and_keeps_comments():
    text = (
        "encoder:\n"
        "  model_id: intfloat/multilingual-e5-base\n"
        "  revision: null                  # pin (T008)\n"
        "  licence_basis: MIT\n"
        "nli:\n"
        "  model_id: org/nli\n"
        "  revision: abc123\n"
        "samplers:\n"
        "  - {name: labse, model_id: sentence-transformers/LaBSE, revision: null, licence_basis: x}\n"
    )
    out, changes = pin_revisions.pin(text, lambda m: f"sha-{m.split('/')[1]}")
    assert "  revision: sha-multilingual-e5-base                  # pin (T008)\n" in out
    assert "  revision: abc123\n" in out
    assert "model_id: sentence-transformers/LaBSE, revision: sha-LaBSE," in out
    assert changes == [("intfloat/multilingual-e5-base", "sha-multilingual-e5-base"),
                       ("sentence-transformers/LaBSE", "sha-LaBSE")]


def test_settings_files_exist():
    assert all(p.exists() for p in pin_revisions.FILES)
