"""The tracking scripts parse, and nothing points at a server on the Spark (feature 017 T062, T067)."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = (
    "scripts/mlflow/mlflow.sh",
    "scripts/spark/tracking-pull.sh",
    "topics/productdev/scripts/spark/train_span.sh",
)


@pytest.mark.parametrize("script", SCRIPTS)
def test_bash_syntax(script):
    if shutil.which("bash") is None:
        pytest.skip("no bash")
    subprocess.run(["bash", "-n", str(ROOT / script)], check=True)


def test_nothing_runs_as_a_service_on_the_spark():
    assert not (ROOT / "scripts/spark/mlflow").exists()
    train = (ROOT / "topics/productdev/scripts/spark/train_span.sh").read_text()
    for gone in ("MLFLOW_TRACKING_URI_CONTAINER", "mmz-tracking", "jtbd,tracking"):
        assert gone not in train
    assert "-e MMZ_TRACKING_OFFLINE=1" in train


def test_server_listens_on_loopback_only():
    server = (ROOT / "scripts/mlflow/mlflow.sh").read_text()
    assert "--host 127.0.0.1" in server and "0.0.0.0" not in server
