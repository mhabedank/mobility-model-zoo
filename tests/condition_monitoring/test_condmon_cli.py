"""`condmon` task CLI (feature 005, T036; feature 021, T015)."""

import pytest
from typer.testing import CliRunner

from mobility_model_zoo.condition_monitoring.cli import app

runner = CliRunner()


@pytest.mark.parametrize("cmd", ["evaluate", "freeze"])
def test_sound_anomaly_benchmark_not_frozen_yet(cmd):
    assert runner.invoke(app, ["sound-anomaly", cmd]).exit_code == 5


@pytest.mark.parametrize("cmd", ["freeze", "evaluate", "reproduce", "export", "train"])
def test_activity_commands_are_real(cmd):
    res = runner.invoke(app, ["activity", cmd, "--help"])
    assert res.exit_code == 0
    assert "not frozen yet" not in res.output


def test_activity_train_refuses_without_a_frozen_benchmark(tmp_path, monkeypatch):
    from mobility_model_zoo.condition_monitoring import benchmark as bm

    monkeypatch.setattr(bm, "repo", lambda: tmp_path)
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    res = runner.invoke(app, ["activity", "train", "--seed", "0"])
    assert res.exit_code == 3


def test_sound_anomaly_train_reports_missing_dataset(tmp_path, monkeypatch):
    pytest.importorskip("tensorflow")
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    res = runner.invoke(app, ["sound-anomaly", "train", "--epochs", "1"])
    assert res.exit_code != 0
