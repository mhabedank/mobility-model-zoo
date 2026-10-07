"""`jtbd span train` gates and a one-epoch CPU run on the tiny encoder (T027, T029)."""

import json

import pytest
import yaml
from helpers import pilot
from span_helpers import git_commit_all, trained_env

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.span import SpanExtractor
from mobility_model_zoo.productdev.jtbd.span.extractor import MODEL_FILES


def train(config, recipe, out, expect=0, epochs="1"):
    return pilot(config, "span", "train", "--recipe", str(recipe), "--out", str(out),
                 "--max-epochs", epochs, expect=expect)


def test_one_epoch_run_writes_a_loadable_model_with_its_provenance(tmp_path):
    config, recipe, work = trained_env(tmp_path)
    out = train(config, recipe, work / "model")
    assert out["best"]["epoch"] == 1
    model_dir = work / "model"
    assert {p.name for p in model_dir.iterdir()} <= MODEL_FILES
    span_config = json.loads((model_dir / "span_config.json").read_text())
    frozen = read_json(load_settings(config).data_dir / "frozen.json")
    assert span_config["dataset"]["sha256"] == frozen["sha256"]
    assert span_config["dimensions"] == {"actor_type": [
        "individual", "worker", "organization", "public_sector", "society"]}
    assert span_config["training"]["best_epoch"] == 1
    assert span_config["training"]["lr"] == 1.5e-5
    assert len(span_config["recipe_commit"]) == 40
    assert span_config["max_epochs_override"] == 1
    extractor = SpanExtractor.from_pretrained(model_dir)
    assert extractor.dimensions == ["actor_type"]
    tuned = pilot(config, "span", "tune", "--model-dir", str(model_dir), "--recipe", str(recipe))
    assert set(tuned["thresholds"]) == {"unit", "relevance"}
    assert tuned["thresholds"]["relevance"] >= tuned["thresholds"]["unit"]
    assert json.loads((model_dir / "span_config.json").read_text())["thresholds"] == \
        tuned["thresholds"]


def test_refuses_when_dimensions_differ_from_the_pilot(tmp_path):
    config, _, work = trained_env(tmp_path)
    other = work / "recipe-all.yaml"
    raw = yaml.safe_load((work / "recipe.yaml").read_text())
    raw["dimensions"] = ["actor_type", "evidence_type"]
    other.write_text(yaml.safe_dump(raw))
    git_commit_all(work)
    train(config, other, work / "m", expect=1)


def test_refuses_an_uncommitted_or_silently_changed_release_bar(tmp_path):
    config, recipe, work = trained_env(tmp_path)
    raw = yaml.safe_load(recipe.read_text())
    fresh = work / "recipe-new.yaml"
    fresh.write_text(yaml.safe_dump(raw))
    train(config, fresh, work / "m", expect=1)  # release bar of this file never committed
    raw["release_bar"]["max_latency_s_9k"] = 20
    recipe.write_text(yaml.safe_dump(raw))
    git_commit_all(work, "loosen the bar")
    train(config, recipe, work / "m", expect=1)  # changed without a recorded rationale
    raw["release_bar_changes"] = [{"date": "2026-10-02", "change": "latency 10 -> 20 s",
                                   "rationale": "test"}]
    recipe.write_text(yaml.safe_dump(raw))
    git_commit_all(work, "record the change")
    train(config, recipe, work / "m")


def test_refuses_too_few_rows_unfrozen_data_and_failed_core_dimension(tmp_path):
    config, recipe, work = trained_env(tmp_path)
    settings = load_settings(config)
    raw = yaml.safe_load(config.read_text())
    raw["span_train"]["min_usable_chunks"] = 10
    config.write_text(yaml.safe_dump(raw))
    git_commit_all(work)
    train(config, recipe, work / "m", expect=1)
    raw["span_train"]["min_usable_chunks"] = 2
    config.write_text(yaml.safe_dump(raw))
    (settings.data_dir / "frozen.json").unlink()
    git_commit_all(work)
    train(config, recipe, work / "m", expect=1)
    pilot(config, "span", "freeze-data")
    bench = load_settings(work / "pilot.yaml")
    decision = read_json(bench.analysis_dir / "decision.json")
    decision["per_dimension"]["kind"]["passed"] = False
    write_json(bench.analysis_dir / "decision.json", decision)
    git_commit_all(work)
    train(config, recipe, work / "m", expect=1)


@pytest.mark.parametrize("missing", ["relevance", "kind"])
def test_core_dimension_names(missing):
    from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
    from mobility_model_zoo.productdev.jtbd.span.gates import passed_attributes

    with pytest.raises(ValidationFailed, match=missing):
        passed_attributes({"per_dimension": {missing: {"passed": False}}})


def test_failed_item_matching_does_not_stop_the_feature():
    from mobility_model_zoo.productdev.jtbd.span.gates import passed_attributes

    passed = {"passed": True}
    decision = {"per_dimension": {"relevance": passed, "kind": passed, "actor_type": passed,
                                  "evidence_type": {"passed": False},
                                  "item_matching": {"passed": False}}}
    assert passed_attributes(decision) == ["actor_type"]
