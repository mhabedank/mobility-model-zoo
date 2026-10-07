"""`jtbd span freeze-data`: hashes and retention record, no silent refreeze (T026)."""

import yaml
from helpers import pilot
from span_helpers import teacher_env, write_recipe

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json


def test_freeze_writes_hashes_and_retention_and_refuses_changes(tmp_path):
    _, train, run = teacher_env(tmp_path)
    pilot(train, "span", "freeze-data", expect=1)  # no rows yet
    pilot(train, "span", "build-rows", "--run", run, "--recipe",
          str(write_recipe(tmp_path / "r.yaml", ["actor_type"])))
    out = pilot(train, "span", "freeze-data")
    settings = load_settings(train)
    frozen = read_json(settings.data_dir / "frozen.json")
    assert frozen["sha256"] == out["sha256"] and frozen["chunk_count"] == 5
    retention = yaml.safe_load((settings.data_dir / "retention.yaml").read_text())
    assert retention["published"] is False and retention["review_by"] > retention["frozen_at"]
    assert pilot(train, "span", "freeze-data")["sha256"] == out["sha256"]  # idempotent
    pilot(train, "span", "build-rows", "--run", run, "--recipe",
          str(write_recipe(tmp_path / "r2.yaml", [])))
    pilot(train, "span", "freeze-data", expect=1)  # rows changed
