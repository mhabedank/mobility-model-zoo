"""The span-model chain end to end on the tiny encoder and the mini corpus (T034).

rows -> train (1 epoch, CPU) -> tune -> span label -> check -> score -> perf -> select ->
results -> release-check, each with the exit code of contracts/cli.md (quickstart 1-2).
"""

import json

import jsonschema
from helpers import pilot, run_ids
from span_helpers import git_commit_all, trained_env

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json
from mobility_model_zoo.productdev.jtbd.span import SpanExtractor
from mobility_model_zoo.productdev.jtbd.span.extractor import SCHEMA_PATH


def test_span_chain_end_to_end(tmp_path):
    train, recipe, work = trained_env(tmp_path, dataset_config="span.yaml",
                                      benchmark_config="pilot.yaml")
    bench = work / "pilot.yaml"
    model = work / "models" / "c1"
    pilot(train, "span", "train", "--recipe", str(recipe), "--out", str(model),
          "--max-epochs", "1")
    tuned = pilot(train, "span", "tune", "--model-dir", str(model), "--recipe", str(recipe))
    assert tuned["val_rows"] >= 1

    extractor = SpanExtractor.from_pretrained(model)
    out = extractor.extract("Der letzte Bus fährt um 18 Uhr. Wir warten lange.")
    jsonschema.validate(out, json.loads(SCHEMA_PATH.read_text()))

    pilot(bench, "agreement")
    pilot(bench, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    pilot(bench, "score", "--run", run_ids(bench)["mock-small"])
    git_commit_all(work, "trained c1")
    run = pilot(bench, "span", "label", "--model-dir", str(model), "--candidate-change",
                "c1: recipe defaults", "--recipe", str(recipe))["run_id"]
    rates = pilot(bench, "check", "--run", run)["pass_rates"]
    assert rates["quote_verbatim"]["rate"] == 1.0 and rates["schema_valid"]["rate"] == 1.0
    score = pilot(bench, "score", "--run", run)
    assert score["produced_dimensions"] == ["actor_type"]

    (work / "text.txt").write_text("Der letzte Bus fährt um 18 Uhr. " * 280)
    perf = pilot(bench, "perf", "--backend", "span", "--model-dir", str(model), "--hardware",
                 "ci", "--text", str(work / "text.txt"))
    assert perf["model_sha256"] == read_json(
        load_settings(bench).runs_dir / run / "manifest.json")["settings"]["model_sha256"]
    selection = pilot(bench, "span", "select", "--recipe", str(recipe))
    assert [r["candidate_id"] for r in selection["ranking"]] == ["c1"]

    # The random tiny model rarely beats the baseline; results are written for the evaluated
    # candidate either way here, and release-check gives the verdict.
    candidates_file = load_settings(train).data_dir / "analysis/candidates.json"
    candidates = read_json(candidates_file)
    candidates["candidates"][0]["selected"] = True
    candidates_file.write_text(json.dumps(candidates))
    perf_file = next((load_settings(bench).analysis_dir / "perf").glob("*.json"))
    pilot(bench, "span", "results", "--run", run, "--perf", str(perf_file), "--version", "0.1.0",
          "--recipe", str(recipe))
    git_commit_all(work, "results")
    verdict = selection["ranking"][0]["meets_bar"]
    pilot(bench, "span", "release-check", "--version", "0.1.0", "--recipe", str(recipe),
          expect=0 if verdict else 1)
    check = read_json(load_settings(train).data_dir / "analysis/release-check-0.1.0.json")
    assert check["passed"] is verdict
