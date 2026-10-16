"""`zoo data publish` and `zoo tracking status|audit` (feature 017 T035; contracts/cli.md)."""

from tracking_helpers import store  # noqa: F401 - pytest fixture
from typer.testing import CliRunner

from mobility_model_zoo.release.cli import app

runner = CliRunner()


def test_without_uri_exit_8(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    from mobility_model_zoo.tracking import config

    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    assert runner.invoke(app, ["tracking", "status"]).exit_code == 8
    assert runner.invoke(app, ["tracking", "audit"]).exit_code == 8
    assert runner.invoke(app, ["data", "publish"]).exit_code == 8
    assert runner.invoke(app, ["data", "publish", "--dry-run"]).exit_code == 0


def test_publish_status_audit(store):  # noqa: F811
    r = runner.invoke(app, ["data", "publish", "--kind", "benchmark"])
    assert r.exit_code == 0, r.output
    assert r.stdout.count("create") == 6
    r = runner.invoke(app, ["tracking", "status", "--json"])
    assert r.exit_code == 0, r.output
    assert '"datasets": 6' in r.stdout
    r = runner.invoke(app, ["tracking", "audit"])
    assert r.exit_code == 0, r.output


def test_unreachable_server_exit_8(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:9")
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    assert runner.invoke(app, ["tracking", "status"]).exit_code == 8
    assert runner.invoke(app, ["data", "publish", "--kind", "benchmark"]).exit_code == 8
