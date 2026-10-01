import shutil

import pytest

from mobility_model_zoo.productdev.jtbd import perf
from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import write_json


def test_percentiles():
    values = [100, 200, 300, 400, 500]
    assert perf.percentile(values, 50) == 300
    assert perf.percentile(values, 95) == pytest.approx(480)
    assert perf.percentile([], 50) is None


def test_rss_from_proc_fixture(tmp_path):
    for pid, cmd, rss in (("10", b"ollama\0runner", 2048), ("11", b"ollama\0serve", 1024),
                          ("12", b"python", 4096)):
        d = tmp_path / pid
        d.mkdir()
        (d / "cmdline").write_bytes(cmd)
        (d / "status").write_text(f"Name:\tx\nVmRSS:\t{rss} kB\n")
    assert perf.ollama_rss_mb(tmp_path) == pytest.approx(3.0)
    assert perf.ollama_rss_mb(tmp_path / "missing") is None


def test_digest_mismatch_refused(tmp_path, fixture_dir, monkeypatch):
    work = tmp_path / "mini"
    shutil.copytree(fixture_dir, work)
    models = work / "models.yaml"
    models.write_text(models.read_text() + (
        "- model_id: tiny\n  api_model: tiny:1b\n  family: fam-t\n  backend: ollama\n"
        "  host: spark\n  role: baseline\n  quantization: Q4_K_M\n"))
    settings = load_settings(work / "pilot.yaml")
    write_json(settings.runs_dir / "run-baseline-tiny-main-x" / "manifest.json", {
        "run_id": "run-baseline-tiny-main-x", "role": "baseline", "backend": "ollama",
        "model_id": "tiny", "model_version": "sha256:aaa", "family": "fam-t", "host": "spark",
        "quantization": "Q4_K_M",
        "settings": {"temperature": 0, "structured_output": "json_schema_grammar"},
        "guideline_sha256": "0" * 64, "schema_sha256": "0" * 64, "criteria_sha256": "0" * 64,
        "split": "main", "started_at": "2026-09-26T00:00:00+00:00", "status": "complete"})
    monkeypatch.setattr(perf, "resolve_host", lambda host: "http://vm:11434")
    monkeypatch.setattr(perf, "model_digest", lambda url, model: "sha256:bbb")
    with pytest.raises(ValidationFailed, match="differs from quality run"):
        perf.perf_local(settings, "tiny", "vm", 0, None, "test-vm")
