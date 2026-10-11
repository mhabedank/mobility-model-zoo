"""Training guard, download refusals, SOURCE.json and licence verify (feature 005 T048)."""

import io
import json
import zipfile

import pytest
from typer.testing import CliRunner

from mobility_model_zoo.datasets import UsageRefused, require_training_allowed
from mobility_model_zoo.datasets import download as dl
from mobility_model_zoo.release.cli import app

runner = CliRunner()


@pytest.mark.parametrize("ds", ["syncan", "can-mirgu", "nope"])
def test_training_guard_refuses(ds):
    with pytest.raises(UsageRefused):
        require_training_allowed(ds)


def test_training_guard_allows_active_training_data():
    require_training_allowed("road")


def test_training_guard_checks_the_usage_class(tmp_path):
    """Non-commercial data trains non-commercial models only (constitution 2.1.0, feature 011)."""
    import yaml

    from mobility_model_zoo.datasets.registry import declarations

    rec = next(r for _, r in declarations() if r["id"] == "road")
    rec.update(licence="CC-BY-NC-4.0", commercial_use=False)
    d = tmp_path / "topics" / "security" / "compliance"
    d.mkdir(parents=True)
    (d / "datasets.yaml").write_text(yaml.safe_dump({"datasets": [rec]}))
    for name, cls in (("picket-x", "commercial"), ("picket-x-nc", "non-commercial")):
        (tmp_path / "zoo" / "models" / name).mkdir(parents=True)
        (tmp_path / "zoo" / "models" / name / "model.yaml").write_text(f"usage_class: {cls}\n")
    with pytest.raises(UsageRefused, match="non-commercial data cannot train picket-x"):
        require_training_allowed("road", tmp_path, model="picket-x")
    with pytest.raises(UsageRefused):
        require_training_allowed("road", tmp_path)  # no model named: commercial by default
    require_training_allowed("road", tmp_path, model="picket-x-nc")


def test_training_entry_points_call_the_guard(monkeypatch):
    from mobility_model_zoo.edge.int8 import keras_export

    monkeypatch.setattr(keras_export, "tf", lambda: pytest.fail("trained despite the guard"))
    with pytest.raises(UsageRefused):
        keras_export.train(lambda seed: None, "x", ["syncan"])


@pytest.mark.parametrize("ds", ["syncan", "can-mirgu"])
def test_download_refused(ds, tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    res = runner.invoke(app, ["data", "download", ds])
    assert res.exit_code == 3, res.output


def test_download_into_repository_refused(monkeypatch):
    from mobility_model_zoo.edge.paths import repo_root

    monkeypatch.setenv("MMZ_DATA", str(repo_root() / "data"))
    res = runner.invoke(app, ["data", "download", "uci-har"])
    assert res.exit_code == 3, res.output


def test_source_json(tmp_path, monkeypatch):
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as z:
        z.writestr("UCI HAR Dataset/README.txt", "hello")
    monkeypatch.setattr(dl, "verify", lambda src: (True, None))
    monkeypatch.setattr(
        dl,
        "remote_files",
        lambda src: [dl.RemoteFile(url="https://example.org/har.zip", name="har.zip")],
    )
    monkeypatch.setattr(dl, "_fetch", lambda f, dest: dest.write_bytes(payload.getvalue()))
    d = dl.download("uci-har")
    meta = json.loads((d / "SOURCE.json").read_text())
    assert {
        "id",
        "title",
        "license",
        "license_url",
        "attribution",
        "citation",
        "homepage",
        "retrieved_at",
    } <= set(meta)
    (f,) = meta["files"]
    assert {"name", "url", "sha256", "bytes"} <= set(f)
    assert (d / "extracted" / "UCI HAR Dataset" / "README.txt").exists()


def test_verify_fails_on_licence_change_and_reports_manual(monkeypatch):
    def record(rec):
        lic = "cc-by-nc-4.0" if str(rec) == "10462796" else "cc-by-4.0"
        return {"metadata": {"license": {"id": lic}}}

    monkeypatch.setattr(dl, "zenodo_record", record)
    res = runner.invoke(app, ["data", "verify", "road", "can-train-and-test"])
    assert res.exit_code == 1
    assert "[manual] can-train-and-test" in res.output and "2026-10-08" in res.output
    assert "road" in res.output
