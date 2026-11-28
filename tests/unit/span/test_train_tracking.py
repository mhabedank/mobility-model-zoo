"""`jtbd span train` and `tune` with experiment tracking on (feature 017 T040, T042, T045)."""

import json

from helpers import pilot
from span_helpers import trained_env
from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture

from mobility_model_zoo.productdev.jtbd.span.extractor import MODEL_FILES


def test_training_and_tuning_are_one_tracked_run(store, tmp_path):  # noqa: F811
    config, recipe, work = trained_env(tmp_path)
    model_dir = work / "model"
    out = pilot(
        config, "span", "train", "--recipe", str(recipe), "--out", str(model_dir), "--max-epochs", "2"
    )
    assert {p.name for p in model_dir.iterdir()} <= MODEL_FILES  # the sidecar stays outside
    side = json.loads((work / "model.tracking.json").read_text())
    assert side["complete"] is True

    [run] = runs_of(store, "productdev/jtbd-span")
    assert run.info.run_id == side["run_id"] and run.info.status == "FINISHED"
    tags = run.data.tags
    assert tags["mmz.kind"] == "train" and tags["mmz.candidate"] == "model"
    assert tags["mmz.training_set"]
    assert run.data.params["dimensions"] == "actor_type"
    loss = store.get_metric_history(run.info.run_id, "loss")
    assert [m.step for m in loss] == [1, 2]  # one point per epoch
    assert run.data.metrics["best.epoch"] == out["best"]["epoch"]
    assert "span_config.json" in [a.path for a in store.list_artifacts(run.info.run_id)]

    pilot(config, "span", "tune", "--model-dir", str(model_dir), "--recipe", str(recipe))
    [same] = runs_of(store, "productdev/jtbd-span")  # tuning continues the training run
    assert "threshold.unit" in same.data.params
    assert any(k.startswith("tuned.") for k in same.data.metrics)


def test_without_tracking_the_outputs_are_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    from mobility_model_zoo.tracking import config as tracking_config

    monkeypatch.setattr(tracking_config, "_dotenv_keys", lambda: {})
    config, recipe, work = trained_env(tmp_path)
    pilot(
        config,
        "span",
        "train",
        "--recipe",
        str(recipe),
        "--out",
        str(work / "model"),
        "--max-epochs",
        "1",
    )
    assert not (work / "model.tracking.json").exists()
