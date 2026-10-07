"""`jtbd span record` fills the release record from the measured data (T045)."""

import json
import shutil
from pathlib import Path

import jsonschema
import yaml
from helpers import pilot, run_ids
from span_helpers import build_tiny_model, git_commit_all, teacher_env, write_recipe

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads(
    (ROOT / "specs/003-model-zoo-hf-release/contracts/release-record.schema.json").read_text())
DRAFT = ROOT / "zoo/models/scout-large/releases/0.1.0.yaml"


def test_record_fills_every_field_feature_004_delivers(tmp_path):
    bench, train, _ = teacher_env(tmp_path)
    work = bench.parent
    recipe = write_recipe(work / "recipe.yaml", ["actor_type"], dataset_config="span.yaml",
                          benchmark_config="pilot.yaml")
    pilot(bench, "agreement")
    pilot(bench, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    pilot(bench, "score", "--run", run_ids(bench)["mock-small"])
    target = work / "zoo/models/scout-large/releases/0.1.0.yaml"
    target.parent.mkdir(parents=True)
    shutil.copy(DRAFT, target)
    git_commit_all(work)
    model = build_tiny_model(work / "model", ("actor_type",))
    config = json.loads((model / "span_config.json").read_text())
    config.update(recipe_commit="a" * 40, recipe="configs/productdev/jtbd/span-xlmr.yaml")
    (model / "span_config.json").write_text(json.dumps(config))
    run = pilot(bench, "span", "label", "--model-dir", str(model), "--candidate-change", "c1",
                "--recipe", str(recipe))["run_id"]
    pilot(bench, "score", "--run", run)
    (work / "text.txt").write_text("Der Bus fährt. " * 600)
    pilot(bench, "perf", "--backend", "span", "--model-dir", str(model), "--hardware", "ref vm",
          "--text", str(work / "text.txt"))
    dataset = load_settings(train)
    candidates = read_json(dataset.data_dir / "analysis/candidates.json")
    candidates["candidates"][0]["selected"] = True
    write_json(dataset.data_dir / "analysis/candidates.json", candidates)
    write_json(dataset.data_dir / "analysis/provenance.json", {"sources": [
        {"origin": "https://example.net/a", "license": "CC-BY-4.0",
         "permitted_use": "training_allowed", "count": 5}]})
    out = pilot(bench, "span", "record", "--version", "0.1.0", "--recipe", str(recipe))
    assert out["teachers"] == ["mock-teacher-y"]
    record = yaml.safe_load(target.read_text())
    assert record["recipe"] == {"git_commit": "a" * 40,
                                "config": "configs/productdev/jtbd/span-xlmr.yaml",
                                "doc": "docs/recipes/scout-large.md"}
    assert record["performance"]["budget"] == {"ram_gb": 4, "gpu": False}
    assert record["performance"]["hardware"].startswith("ref vm (")
    assert record["provenance"]["spike_data"] is False
    assert record["provenance"]["teachers"][0]["training_on_outputs_permitted"] is True
    assert record["evaluation"]["benchmark"] == "mini-v1"
    assert "mock-a and mock-b" in record["evaluation"]["reference"]
    errors = [e for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(record)]
    # Only what `zoo stage` writes is still missing.
    assert {tuple(e.absolute_path)[:1] for e in errors} <= {("files",), ("staging",)}, \
        [e.message for e in errors]
