"""A real MLflow server round trip (feature 017 T038, quickstart §3-§4, §8).

Slow: starts `mlflow server` (the full package, through uvx) on a temporary SQLite store, as
scripts/mlflow/mlflow.sh does on the laptop, publishes the data overview twice, logs a tracked run
with a dataset input, finds it by dataset name, checks the host header guard, syncs an offline run
log and runs the audit. Needs network once to fetch the server package.
"""

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request

import pytest

pytestmark = pytest.mark.slow

SERVER = "mlflow==3.17.1"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    if shutil.which("uvx") is None:
        pytest.skip("uvx not installed")
    pytest.importorskip("mlflow")
    root = tmp_path_factory.mktemp("mlflow")
    port = _free_port()
    proc = subprocess.Popen(
        [
            "uvx",
            "--from",
            SERVER,
            "mlflow",
            "server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--backend-store-uri",
            f"sqlite:///{root}/mlflow.db",
            "--artifacts-destination",
            str(root / "artifacts"),
        ],  # default allowed hosts, as scripts/mlflow/mlflow.sh (research R2)
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(180):
        try:
            urllib.request.urlopen(f"{url}/health", timeout=1)
            break
        except OSError:
            time.sleep(1)
    else:
        proc.kill()
        pytest.skip("mlflow server did not start")
    yield url
    proc.terminate()
    proc.wait(timeout=30)


def _status(url: str, host: str) -> int:
    req = urllib.request.Request(
        f"{url}/api/2.0/mlflow/experiments/search?max_results=1", headers={"Host": host}
    )
    try:
        return urllib.request.urlopen(req, timeout=5).status
    except urllib.error.HTTPError as e:
        return e.code


def test_round_trip(server, tmp_path, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", server)
    from typer.testing import CliRunner

    from mobility_model_zoo import tracking
    from mobility_model_zoo.release.cli import app
    from mobility_model_zoo.tracking import client as tc

    runner = CliRunner()
    first = runner.invoke(app, ["data", "publish", "--profile"])
    assert first.exit_code == 0, first.output
    second = runner.invoke(app, ["data", "publish"])
    assert second.exit_code == 0 and "create" not in second.stdout

    with tracking.run(
        "security/can-ids",
        "round-trip",
        "can-ids",
        out_dir=tmp_path,
        inputs=[tracking.data_ref("can-ids", "can-ids-v3", "evaluation")],
        tags={"mmz.kind": "evaluate", "mmz.benchmark": "can-ids-v3"},
    ) as r:
        for step in range(3):
            r.log_step(step, {"loss": 1.0 / (step + 1)})
    assert json.loads((tmp_path / "tracking.json").read_text())["complete"] is True

    cl = tc.new_client()
    exp = cl.get_experiment_by_name("security/can-ids").experiment_id
    found = cl.search_runs([exp], filter_string="datasets.name = 'can-ids@can-ids-v3'")
    assert [x.info.run_name for x in found] == ["round-trip"]
    digest = found[0].inputs.dataset_inputs[0].dataset.digest
    assert len(digest) == 16  # research R9, open item 2

    port = server.rsplit(":", 1)[1]
    assert _status(server, "evil.example") == 403  # research R2, open item 1
    assert _status(server, f"127.0.0.1:{port}") == 200
    assert _status(server, f"mlflow:{port}") == 403  # no container host since 2026-10-16

    audit = runner.invoke(app, ["tracking", "audit"])
    assert audit.exit_code == 0, audit.output
    assert os.environ["MLFLOW_TRACKING_URI"] == server


def test_offline_log_syncs_into_a_real_server(server, tmp_path, monkeypatch):
    """A Spark-style offline run (FR-030, research R17) lands once, with its curve and status."""
    from typer.testing import CliRunner

    from mobility_model_zoo import tracking
    from mobility_model_zoo.release.cli import app
    from mobility_model_zoo.tracking import client as tc
    from mobility_model_zoo.tracking import config

    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.setenv("MMZ_TRACKING_OFFLINE", "1")
    sidecar = tmp_path / "data/models/span-c9.tracking.json"
    with tracking.run("productdev/jtbd-span", "span-c9", "jtbd-span", sidecar=sidecar) as r:
        for epoch in range(3):
            r.log_step(epoch, {"loss": 1.0 / (epoch + 1)})
    monkeypatch.delenv("MMZ_TRACKING_OFFLINE")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", server)

    runner = CliRunner()
    first = runner.invoke(app, ["tracking", "sync", str(tmp_path / "data")])
    assert first.exit_code == 0 and "created" in first.stdout, first.output
    second = runner.invoke(app, ["tracking", "sync", str(tmp_path / "data")])
    assert second.exit_code == 0 and "unchanged" in second.stdout, second.output

    cl = tc.new_client()
    exp = cl.get_experiment_by_name("productdev/jtbd-span").experiment_id
    offline_id = json.loads(sidecar.read_text())["offline_id"]
    [run] = cl.search_runs([exp], filter_string=f"tags.`mmz.offline_id` = '{offline_id}'")
    assert run.info.status == "FINISHED"
    assert [m.step for m in cl.get_metric_history(run.info.run_id, "loss")] == [0, 1, 2]
    assert runner.invoke(app, ["tracking", "audit"]).exit_code == 0
