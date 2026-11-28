"""Offline run logs: written next to the sidecar, guarded, without MLflow (feature 017 T065, T068;
FR-030, research R17)."""

import json
import os
import subprocess
import sys
import time

import pytest

from mobility_model_zoo import tracking
from mobility_model_zoo.tracking import client as tc
from mobility_model_zoo.tracking import config


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.setenv("MMZ_TRACKING_OFFLINE", "1")
    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    monkeypatch.setattr(tc, "STRICT", False)


def _events(sidecar):
    side = json.loads(sidecar.read_text())
    log = sidecar.parent / side["log"]
    return side, [json.loads(line) for line in log.read_text().splitlines()]


def _train(sidecar, epochs=2, run_id=None, **kw):
    with tracking.run(
        "productdev/jtbd-span", name="span-c1", task="jtbd-span", sidecar=sidecar, run_id=run_id, **kw
    ) as r:
        r.log_params({"lr": 0.001})
        for epoch in range(epochs):
            r.log_step(epoch, {"loss": 1.0 / (epoch + 1)})
    return r


def test_log_next_to_the_sidecar_never_in_the_model_folder(offline, tmp_path):
    model = tmp_path / "models/span-c1"
    model.mkdir(parents=True)
    (model / "span_config.json").write_text("{}")
    sidecar = tmp_path / "models/span-c1.tracking.json"
    _train(sidecar)
    assert sorted(p.name for p in model.iterdir()) == ["span_config.json"]
    side, events = _events(sidecar)
    assert side["mode"] == "offline" and side["complete"] and side["run_id"] is None
    assert side["log"] == f"span-c1.tracking/{side['offline_id']}.mmz-run.jsonl"
    assert [e["seq"] for e in events] == list(range(len(events)))
    assert events[0] == {**events[0], "type": "start", "format": "mmz-run/1", "name": "span-c1"}
    assert events[-1]["type"] == "end" and events[-1]["status"] == "FINISHED"
    tags = next(e for e in events if e["type"] == "tags")["values"]
    assert tags["mmz.task"] == "jtbd-span" and "mmz.git_commit" in tags
    steps = [(e["step"], e["values"]) for e in events if e["type"] == "metrics"]
    assert steps == [(0, {"loss": 1.0}), (1, {"loss": 0.5})]


def test_guard_drops_are_counted_and_failures_marked(offline, tmp_path):
    sidecar = tmp_path / "out/tracking.json"
    with pytest.raises(RuntimeError):
        with tracking.run("productdev/jtbd-span", "c1", "jtbd-span", out_dir=tmp_path / "out") as r:
            r.log_params({"note": "a sentence with far too many words in it"})
            r.log_metrics({"loss": float("nan")})
            raise RuntimeError("training failed")
    side, events = _events(sidecar)
    assert side["dropped"] == 2 and side["complete"]  # deliberate drops, not losses
    assert events[-1]["status"] == "FAILED"
    assert not any(e["type"] == "params" for e in events)


def test_a_continued_run_appends_and_a_partial_line_is_cut(offline, tmp_path):
    sidecar = tmp_path / "models/span-c1.tracking.json"
    _train(sidecar)
    side, before = _events(sidecar)
    log = sidecar.parent / side["log"]
    with log.open("a") as f:
        f.write('{"seq": 99, "t": 1, "type": "met')  # a crash mid-write
    run_id = tc.sidecar_run_id(sidecar)
    assert run_id == side["offline_id"]
    with tracking.run(
        "productdev/jtbd-span", "span-c1-tune", "jtbd-span", sidecar=sidecar, run_id=run_id
    ) as r:
        r.log_final({"tuned.f1": 0.7})
    side2, after = _events(sidecar)
    assert side2["offline_id"] == side["offline_id"]
    assert [e["seq"] for e in after] == list(range(len(after)))
    assert after[len(before)]["values"] == {"tuned.f1": 0.7}
    assert sum(e["type"] == "start" for e in after) == 1


def test_modes_do_not_continue_each_other(offline, tmp_path):
    sidecar = tmp_path / "x.tracking.json"
    sidecar.write_text(json.dumps({"mode": "live", "run_id": "a" * 32}))
    assert tc.sidecar_run_id(sidecar) is None


def test_a_run_without_folder_logs_under_data_tracking(offline, tmp_path, monkeypatch):
    import mobility_model_zoo.edge.paths as paths

    monkeypatch.setattr(paths, "repo_root", lambda: tmp_path)
    tracking.record("security/can-ids", "eval c1", "can-ids", "evaluate", {"f1": {"median": 0.9}})
    [sidecar] = (tmp_path / "data/tracking").glob("*.tracking.json")
    assert sidecar.name.startswith("eval_c1-")
    side, events = _events(sidecar)
    assert side["mode"] == "offline"
    assert [e["values"] for e in events if e["type"] == "metrics"] == [{"f1.median": 0.9}]


def test_system_metrics_sampler(offline, tmp_path, monkeypatch):
    pytest.importorskip("psutil")
    monkeypatch.setenv("MMZ_TRACKING_SAMPLE_SECONDS", "0.05")
    sidecar = tmp_path / "out/tracking.json"
    with tracking.run(
        "productdev/jtbd-span", "c1", "jtbd-span", out_dir=tmp_path / "out", system_metrics=True
    ):
        time.sleep(0.4)
    _, events = _events(sidecar)
    assert any("system/cpu_utilization_percentage" in e.get("values", {}) for e in events)
    monkeypatch.setenv("MMZ_TRACKING_SYSTEM_METRICS", "0")
    sidecar.unlink()
    with tracking.run(
        "productdev/jtbd-span", "c2", "jtbd-span", out_dir=tmp_path / "out", system_metrics=True
    ):
        time.sleep(0.2)
    _, events = _events(sidecar)
    assert not any(k.startswith("system/") for e in events for k in e.get("values", {}))


def test_offline_mode_imports_no_mlflow(tmp_path):
    code = (
        "import sys; from pathlib import Path; from mobility_model_zoo import tracking\n"
        "from mobility_model_zoo.tracking import config; config._dotenv_keys = lambda: {}\n"
        f"with tracking.run('spikes', 'x', 'spike', out_dir=Path({str(tmp_path)!r})) as r:\n"
        "    r.log_step(0, {'loss': 1.0})\n"
        "print('mlflow' in sys.modules)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "MLFLOW_TRACKING_URI"}
    env["MMZ_TRACKING_OFFLINE"] = "1"
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"
    assert (tmp_path / "tracking.json").is_file()


def test_a_uri_wins_over_offline(monkeypatch):
    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    monkeypatch.setenv("MMZ_TRACKING_OFFLINE", "1")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    assert not config.offline()
    monkeypatch.delenv("MLFLOW_TRACKING_URI")
    assert config.offline()
