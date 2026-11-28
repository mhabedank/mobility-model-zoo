"""Configuration and the no-op path (feature 017 T030, T033; FR-010, FR-011)."""

import os
import subprocess
import sys

from mobility_model_zoo import tracking
from mobility_model_zoo.tracking import config


def test_no_uri_means_no_op_and_no_sidecar(tmp_path, monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    with tracking.run("security/can-ids", "x", "can-ids", out_dir=tmp_path / "out") as r:
        r.log_step(0, {"loss": 1.0})
        r.log_artifact(tmp_path / "anything")
    assert r.run_id is None
    assert not (tmp_path / "out").exists()


def test_no_uri_never_imports_mlflow(tmp_path):
    code = (
        "import sys; from mobility_model_zoo import tracking\n"
        "import mobility_model_zoo.tracking.config as c\n"
        "c._dotenv_keys = lambda: {}  # a developer's .env must not matter\n"
        "with tracking.run('spikes', 'x', 'spike') as r: r.log_step(0, {'a': 1})\n"
        "assert 'mlflow' not in sys.modules"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("MLFLOW_")}
    subprocess.run([sys.executable, "-c", code], check=True, cwd=tmp_path, env=env)


def test_dotenv_supplies_only_mlflow_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.delenv("UNRELATED_SECRET", raising=False)
    monkeypatch.delenv("MMZ_TRACKING_IGNORE_DOTENV")  # this test reads a .env on purpose
    (tmp_path / ".env").write_text(
        "MLFLOW_TRACKING_URI=http://127.0.0.1:5000\nUNRELATED_SECRET=keep-out\n"
    )
    monkeypatch.chdir(tmp_path)
    assert config.tracking_uri() == "http://127.0.0.1:5000"
    assert "UNRELATED_SECRET" not in os.environ


def test_uri_host_hides_everything_but_host_and_port():
    assert config.uri_host("http://user:pw@127.0.0.1:5000/path") == "127.0.0.1:5000"
    assert config.uri_host("http://mlflow:5000") == "mlflow:5000"


def test_client_defaults_do_not_override_the_user(monkeypatch):
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_TIMEOUT", "99")
    config.apply_client_defaults()
    assert os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] == "99"


def test_unknown_experiment_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file://{tmp_path}")
    import pytest

    with pytest.raises(ValueError):
        with tracking.run("my/experiment", "x", "t"):
            pass


def test_flatten():
    data = {"a": {"b": 1, "c": [1, 2]}, "d": [{"e": True}]}
    assert tracking.flatten(data) == {"a.b": 1, "a.c": "1,2", "d.0.e": True}
