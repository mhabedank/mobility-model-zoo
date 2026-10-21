"""Shared CycloneDX SBOM generator (feature 021, T035; research R10)."""

import hashlib

import pytest

from mobility_model_zoo.release import sbom


def _folder(tmp_path):
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "net.c").write_text("int x;\n")
    (tmp_path / "c" / "net.h").write_text("extern int x;\n")
    (tmp_path / "model.npz").write_bytes(b"\0")
    (tmp_path / "sbom.cdx.json").write_text("{}")
    return tmp_path


def test_lists_every_shipped_source_with_its_hash(tmp_path):
    d = _folder(tmp_path)
    doc = sbom.sbom(
        d,
        name="net",
        description="a test",
        libraries=[sbom.library("tensorflow", "2.21.0", "training")],
        tool="tests",
    )
    assert doc["bomFormat"] == "CycloneDX" and doc["specVersion"] == "1.5"
    assert doc["metadata"]["component"] == {"type": "firmware", "name": "net", "description": "a test"}
    files = [c for c in doc["components"] if c["type"] == "file"]
    assert [f["name"] for f in files] == ["c/net.c", "c/net.h"]  # not the npz, not the SBOM itself
    want = hashlib.sha256(b"int x;\n").hexdigest()
    assert files[0]["hashes"] == [{"alg": "SHA-256", "content": want}]
    libs = [c for c in doc["components"] if c["type"] == "library"]
    assert libs == [
        {
            "type": "library",
            "name": "tensorflow",
            "version": "2.21.0",
            "purl": "pkg:pypi/tensorflow@2.21.0",
            "description": "training",
        }
    ]


def test_picket_forest_keeps_its_sbom(tmp_path):
    pytest.importorskip("emlearn")
    from mobility_model_zoo.security.can_ids.release_export import sbom as forest_sbom

    doc = forest_sbom(_folder(tmp_path))
    assert doc["metadata"]["component"]["name"] == "picket-forest"
    assert doc["metadata"]["tools"] == [{"name": "mobility_model_zoo.security.can_ids.release_export"}]
    assert [c["name"] for c in doc["components"] if c["type"] == "library"] == [
        "emlearn",
        "scikit-learn",
    ]
    assert [c["name"] for c in doc["components"] if c["type"] == "file"] == ["c/net.c", "c/net.h"]
