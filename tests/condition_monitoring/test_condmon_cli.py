"""`condmon` task CLI (feature 005, T036)."""

import pytest
from typer.testing import CliRunner

from mobility_model_zoo.condition_monitoring.cli import app

runner = CliRunner()


@pytest.mark.parametrize("task", ["sound-anomaly", "activity"])
@pytest.mark.parametrize("cmd", ["evaluate", "freeze"])
def test_benchmark_not_frozen_yet(task, cmd):
    assert runner.invoke(app, [task, cmd]).exit_code == 5


def test_train_reports_missing_dataset(tmp_path, monkeypatch):
    pytest.importorskip("tensorflow")
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    res = runner.invoke(app, ["activity", "train", "--epochs", "1"])
    assert res.exit_code != 0
    assert "zoo data download uci-har" in str(res.exception) + res.output
