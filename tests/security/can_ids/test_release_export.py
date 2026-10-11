"""Release export of picket-forest on the tiny synthetic benchmark (feature 007, T026/T027)."""

from __future__ import annotations

import hashlib
import importlib.util
import json

import pytest
from test_evaluate import bench  # noqa: F401  (module fixture)

from mobility_model_zoo.security.can_ids import release_export, scorer

# find_spec, not importorskip: importing emlearn changes numpy's error state for the whole session
pytestmark = pytest.mark.skipif(importlib.util.find_spec("emlearn") is None, reason="emlearn missing")


@pytest.fixture(scope="module")
def exported(bench, tmp_path_factory):  # noqa: F811
    _, sources, manifest = bench
    out = tmp_path_factory.mktemp("export") / "export"
    config = release_export.export(out, manifest, sources, out.parent / "cache", out.parent / "store")
    return out, config


def test_export_writes_every_staged_file(exported):
    out, config = exported
    for name in (*scorer.HEADERS, "model.joblib", "config.json", "sbom.cdx.json"):
        assert (out / name).is_file(), name
    assert sorted(p.name for p in (out / "c").iterdir()) == sorted(scorer.SOURCES)
    assert config["parity_c_vs_python"]["mismatches"] == 0 and config["parity_c_vs_python"]["frames"] > 0
    assert config["benchmark"] == "can-ids-v1" and len(config["manifest_sha256"]) == 64
    assert {"k", "window_ms", "holdoff_ms", "selected_on"} <= set(config["alarm"])


def test_sbom_lists_every_c_file_with_its_hash(exported):
    out, _ = exported
    bom = json.loads((out / "sbom.cdx.json").read_text())
    assert bom["bomFormat"] == "CycloneDX"
    files = {c["name"]: c["hashes"][0]["content"] for c in bom["components"] if c["type"] == "file"}
    staged = [p for p in out.rglob("*") if p.suffix in (".c", ".h")]
    assert set(files) == {p.relative_to(out).as_posix() for p in staged}
    for p in staged:
        assert files[p.relative_to(out).as_posix()] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert {c["name"] for c in bom["components"] if c["type"] == "library"} == {
        "emlearn",
        "scikit-learn",
    }


def test_examples_are_checked_by_the_staged_scorer(exported, tmp_path):
    out, _ = exported
    paths = release_export.write_examples(out, tmp_path / "examples")
    assert [p.name for p in paths] == ["01-fabrication.json", "02-dos.json", "03-fuzzing.json"]
    exe = scorer.build_scorer(out, tmp_path / "build", sources_dir=out / "c")
    for p in paths:
        assert scorer.check_example(exe, json.loads(p.read_text())) is None
