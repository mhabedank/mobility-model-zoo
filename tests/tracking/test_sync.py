"""`zoo tracking sync`: offline logs into the store, incremental and idempotent (feature 017 T066,
T068; FR-030, research R17)."""

import json
import os

import pytest
from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture
from typer.testing import CliRunner

from mobility_model_zoo import tracking
from mobility_model_zoo.release.cli import app
from mobility_model_zoo.tracking import client as tc
from mobility_model_zoo.tracking import config
from mobility_model_zoo.tracking.sync import sync

runner = CliRunner()


@pytest.fixture
def offline_log(store, tmp_path, monkeypatch):  # noqa: F811
    """Write offline runs (as on the Spark) while the store fixture's URI is set aside."""
    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})

    def write(epochs=(0, 1), run_id=None, artifact=None):
        uri = os.environ.pop("MLFLOW_TRACKING_URI")
        os.environ["MMZ_TRACKING_OFFLINE"] = "1"
        try:
            sidecar = tmp_path / "data/models/span-c1.tracking.json"
            with tracking.run(
                "productdev/jtbd-span",
                "span-c1",
                "jtbd-span",
                sidecar=sidecar,
                run_id=run_id,
                tags={"mmz.kind": "train"},
            ) as r:
                if run_id is None:
                    r.log_params({"lr": 0.001})
                for epoch in epochs:
                    r.log_step(epoch, {"loss": 1.0 / (epoch + 1)})
                if artifact:
                    r.log_artifact(artifact)
            side = json.loads(sidecar.read_text())
            return sidecar.parent / side["log"], side["offline_id"]
        finally:
            del os.environ["MMZ_TRACKING_OFFLINE"]
            os.environ["MLFLOW_TRACKING_URI"] = uri

    return write


def _events(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_created_then_unchanged_with_times_and_steps(store, offline_log, tmp_path):  # noqa: F811
    cfg = tmp_path / "span_config.json"
    cfg.write_text(json.dumps({"best_epoch": 1}))
    log, oid = offline_log(artifact=cfg)
    [first] = sync([tmp_path / "data"])
    assert (first.action, first.running) == ("created", False)
    [run] = runs_of(store, "productdev/jtbd-span")
    events = _events(log)
    assert run.data.tags["mmz.offline_id"] == oid
    assert run.data.tags["mmz.offline_synced"] == str(events[-1]["seq"])
    assert run.data.tags["mmz.task"] == "jtbd-span" and run.data.params["lr"] == "0.001"
    assert run.info.status == "FINISHED"
    assert run.info.start_time == events[0]["t"] and run.info.end_time == events[-1]["t"]
    history = store.get_metric_history(run.info.run_id, "loss")
    assert [(m.step, m.value) for m in history] == [(0, 1.0), (1, 0.5)]
    assert [a.path for a in store.list_artifacts(run.info.run_id)] == ["span_config.json"]
    [again] = sync([tmp_path / "data"])
    assert again.action == "unchanged"


def test_a_grown_log_adds_only_new_events(store, offline_log, tmp_path):  # noqa: F811
    log, oid = offline_log(epochs=(0, 1))
    sync([tmp_path / "data"])
    offline_log(epochs=(2, 3), run_id=oid)  # e.g. the run continued (span tune) or more epochs
    [act] = sync([tmp_path / "data"])
    assert (act.action, act.events) == ("updated", 3)  # two epochs and the second end
    [run] = runs_of(store, "productdev/jtbd-span")
    history = store.get_metric_history(run.info.run_id, "loss")
    assert [m.step for m in history] == [0, 1, 2, 3]


def test_a_partial_last_line_waits_for_the_next_sync(store, offline_log, tmp_path):  # noqa: F811
    log, _ = offline_log()
    seq = len(_events(log))
    with log.open("a") as f:
        f.write(json.dumps({"seq": seq, "t": 1, "type": "tags", "values": {"mmz.candidate": "c1"}})[:-1])
    [first] = sync([tmp_path / "data"])
    assert first.action == "created"
    [run] = runs_of(store, "productdev/jtbd-span")
    assert "mmz.candidate" not in run.data.tags
    with log.open("a") as f:
        f.write("}\n")
    [second] = sync([tmp_path / "data"])
    assert (second.action, second.events) == ("updated", 1)
    [run] = runs_of(store, "productdev/jtbd-span")
    assert run.data.tags["mmz.candidate"] == "c1"


def test_a_hand_edited_log_is_refused_whole(store, offline_log, tmp_path):  # noqa: F811
    log, _ = offline_log()
    seq = len(_events(log))
    with log.open("a") as f:
        f.write(
            json.dumps({"seq": seq, "t": 1, "type": "metrics", "step": 2, "values": {"loss": 0.3}})
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "seq": seq + 1,
                    "t": 1,
                    "type": "params",
                    "values": {"quote": "the driver said this to me yesterday"},
                }
            )
            + "\n"
        )
    r = runner.invoke(app, ["tracking", "sync", str(tmp_path / "data")])
    assert r.exit_code == 7, r.output
    assert "refused" in r.stdout
    assert runs_of(store, "productdev/jtbd-span") == []  # nothing of the log was written


def test_a_changed_param_refuses_the_new_events(store, offline_log, tmp_path):  # noqa: F811
    log, _ = offline_log()
    sync([tmp_path / "data"])
    seq = len(_events(log))
    with log.open("a") as f:
        f.write(json.dumps({"seq": seq, "t": 1, "type": "params", "values": {"lr": 0.1}}) + "\n")
    [act] = sync([tmp_path / "data"])
    assert act.action == "refused" and "lr changed" in act.note


def test_running_log_and_dry_run(store, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setattr(tc, "STRICT", False)
    folder = tmp_path / "data/out/tracking"
    folder.mkdir(parents=True)
    log = folder / f"{'b' * 32}.mmz-run.jsonl"
    log.write_text(
        json.dumps(
            {
                "seq": 0,
                "t": 1000,
                "type": "start",
                "format": "mmz-run/1",
                "experiment": "spikes",
                "name": "s",
            }
        )
        + "\n"
        + json.dumps({"seq": 1, "t": 2000, "type": "metrics", "step": 0, "values": {"x": 1}})
        + "\n"
    )
    [dry] = sync([tmp_path / "data"], dry_run=True)
    assert (dry.action, dry.running) == ("create", True)
    assert runs_of(store, "spikes") == []
    r = runner.invoke(app, ["tracking", "sync", str(tmp_path / "data")])
    assert r.exit_code == 0, r.output
    assert "created" in r.stdout and "running" in r.stdout
    [run] = runs_of(store, "spikes")
    assert run.info.status == "RUNNING"


def test_without_uri_exit_8(tmp_path, monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    assert runner.invoke(app, ["tracking", "sync", str(tmp_path)]).exit_code == 8
    assert runner.invoke(app, ["tracking", "sync", str(tmp_path), "--dry-run"]).exit_code == 0
