"""`security` task CLI (feature 005, T036)."""

import json

import pytest
from typer.testing import CliRunner

from mobility_model_zoo.security.cli import app

runner = CliRunner()


def test_frames_writes_common_format_outside_the_repo(tmp_path, monkeypatch):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    root = tmp_path / "road" / "extracted" / "road"
    (root / "ambient").mkdir(parents=True)
    (root / "attacks").mkdir()
    (root / "ambient" / "drive.log").write_text("(0.0) can0 100#00\n(0.1) can0 100#01\n")
    (root / "attacks" / "fuzzing_attack_1.log").write_text("(5.0) can0 2AA#FF\n")
    meta = {"fuzzing_attack_1": {"injection_interval": [0, 1], "injection_id": "XXX"}}
    (root / "attacks" / "capture_metadata.json").write_text(json.dumps(meta))
    res = runner.invoke(app, ["can-ids", "frames", "road"])
    assert res.exit_code == 0, res.output
    out = tmp_path / "derived" / "frames" / "road"
    attacks = pd.read_parquet(out / "attacks" / "fuzzing_attack_1.parquet")
    assert attacks["label"].tolist() == [1]
    assert (out / "ambient" / "drive.parquet").exists()


def test_unknown_dataset_is_a_usage_error():
    assert runner.invoke(app, ["can-ids", "frames", "nope"]).exit_code == 2


@pytest.mark.parametrize("argv", [["can-ids", "evaluate", "picket-mlp"], ["can-ids", "freeze"]])
def test_benchmark_not_frozen_yet(argv):
    assert runner.invoke(app, argv).exit_code == 5


def test_mlp_needs_train_subcommand():
    assert runner.invoke(app, ["can-ids", "mlp"]).exit_code == 2
