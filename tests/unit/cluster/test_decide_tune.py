"""Decisions per level, tuning on development data, scoring on test (feature 009, T025, T033)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml
from bench_helpers import answer_units, make_env
from cluster_helpers import SETTINGS

from mobility_model_zoo.productdev.jtbd.cluster import bench, decide, label, metrics, score, tune
from mobility_model_zoo.productdev.jtbd.cluster.embed import TableEncoder
from mobility_model_zoo.productdev.jtbd.errors import FrozenHashMismatch, UsageError

CRITERIA = {"duplicate_kappa_min": 0.6, "specificity_kappa_min": 0.4, "cluster_bcubed_f1_min": 0.6,
            "revise": {"max_reruns": 1}}


def levels(dup, spec, c1, c2=None):
    return {"duplicate": {"value": dup}, "specificity": {"value": spec},
            "cluster_level_1": {"value": c1}, "cluster_level_2": {"value": c2}}


def test_go_revise_rethink():
    out = decide.decide_levels(levels(0.7, 0.3, 0.65, 0.7), CRITERIA, reruns_used=0)
    assert {k: v["decision"] for k, v in out.items()} == {
        "duplicate": "go", "specificity": "revise", "cluster_level_1": "go", "cluster_level_2": "go"}
    out = decide.decide_levels(levels(0.5, 0.3, 0.5, 0.9), CRITERIA, reruns_used=1)
    assert {k: v["decision"] for k, v in out.items()} == {
        "duplicate": "rethink", "specificity": "rethink", "cluster_level_1": "rethink",
        "cluster_level_2": "not_measured"}
    assert decide.decide_levels(levels(0.7, 0.5, 0.7, None), CRITERIA, 0)["cluster_level_2"][
        "decision"] == "not_measured"


# ---- the whole measurement chain on the synthetic benchmark --------------------------------------


def pair_truth(pool):
    """Fictional truth: same topic word and kind -> same."""
    def topic(q):
        return next(w for w in ("bus", "tram", "parking", "bike", "charging", "train") if w in q)
    return lambda p: "same" if topic(pool[p["a"]]["quote"]) == topic(pool[p["b"]]["quote"]) \
        else "different"


@pytest.fixture
def labelled(tmp_path):
    env = make_env(tmp_path / "env")
    env.build()
    s = env.settings()
    bench.freeze(s)
    truth = pair_truth(bench.load_pool(s))
    for split in ("dev", "test"):
        for model in ("mock-a", "mock-b"):
            flip = (lambda p: "different") if model == "mock-b" and split == "test" else truth

            def answer(p, t=truth, f=flip):  # every fourth pair (by id) may disagree
                return t(p) if int(p["pair_id"][3:], 16) % 4 else f(p)

            answer_units(env, model, split, pair_label=answer)
            label.label(env.settings(), model, split)
    return env


def test_agreement_decide_and_state(labelled):
    s = labelled.settings()
    dev = metrics.run_agreement(s, "dev")
    assert dev["split"] == "dev" and bench.load_manifest(s)["state"] == "frozen"
    result = metrics.run_agreement(s, "test")
    assert set(result["levels"]) == set(metrics.LEVELS)
    assert bench.load_manifest(s)["state"] == "piloted"
    assert (metrics.analysis_dir(s) / "consensus-test.jsonl").exists()
    decision = decide.decide(s)
    assert decision["levels"]["cluster_level_1"]["decision"] == "go"  # both put each set in one cluster
    state = bench.load_manifest(s)["state"]
    assert state == ("revise" if not decision["final"] else "decided")


def test_decide_refuses_changed_criteria(labelled):
    s = labelled.settings()
    metrics.run_agreement(s, "test")
    (labelled.root / "criteria.yaml").write_text(yaml.safe_dump({**CRITERIA, "x": 1}))
    with pytest.raises(FrozenHashMismatch):
        decide.decide(s)


def test_one_rerun_then_rethink(labelled):
    s = labelled.settings()
    path = metrics.analysis_dir(s) / "agreement.json"
    metrics.run_agreement(s, "test")
    data = json.loads(path.read_text())
    data["levels"]["duplicate"]["value"] = 0.3
    path.write_text(json.dumps(data))
    first = decide.decide(s)
    assert first["levels"]["duplicate"]["decision"] == "revise" and not first["final"]
    manifest = bench.load_manifest(s)
    assert manifest["state"] == "revise" and manifest["reruns"] == 1
    bench.freeze(s)  # nothing changed: the same guideline is frozen again for the re-pilot
    bench.set_state(s, "piloted", "re-pilot (test shortcut)")
    second = decide.decide(s)
    assert second["levels"]["duplicate"]["decision"] == "rethink"
    assert second["task_stopped"] is True and bench.load_manifest(s)["state"] == "decided"


@pytest.mark.parametrize("split", ["test", "holdout"])
def test_tune_refuses_test_and_holdout(labelled, split):
    with pytest.raises(UsageError) as exc:
        tune.tune(labelled.settings(), SETTINGS, split)
    assert exc.value.exit_code == 2


def test_tune_writes_grid_and_chosen_value(labelled, tmp_path):
    s = labelled.settings()
    metrics.run_agreement(s, "dev")
    out = tune.tune(s, SETTINGS, "dev", out=tmp_path / "tuned.yaml")
    tuned = yaml.safe_load((tmp_path / "tuned.yaml").read_text())
    assert tuned["thresholds"]["t_dup"] == out["t_dup"]
    assert [r["t_dup"] for r in tuned["tuning"]["grid"]] == list(tune.GRID)
    assert tuned["tuning"]["split"] == "dev" and tuned["name"].endswith("-tuned")


def test_grid_prefers_best_f1_then_higher_threshold():
    rows = [{"t_dup": 0.8, "f1": 0.5}, {"t_dup": 0.85, "f1": 0.7}, {"t_dup": 0.9, "f1": 0.7},
            {"t_dup": 0.95, "f1": None}]
    assert tune.choose(rows)["t_dup"] == 0.9


def test_grid_search_on_fixed_vectors():
    from cluster_helpers import item, source_line

    from mobility_model_zoo.productdev.jtbd.cluster.bundle import items_from, read_bundle_lines

    lines = [source_line("s1", [item("pain", "Bus late"), item("pain", "Bus delayed", 20),
                                item("pain", "Seats dirty", 40)])]
    items = items_from(read_bundle_lines(lines))
    vec = {"Bus late": [1, 0], "Bus delayed": [0.9, 0.436], "Seats dirty": [0, 1]}
    vectors = np.array([vec[i.quote] for i in items], dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    ids = {i.quote: i.item_id for i in items}
    pairs = [{"pair_id": "p1", "a": ids["Bus late"], "b": ids["Bus delayed"]},
             {"pair_id": "p2", "a": ids["Bus late"], "b": ids["Seats dirty"]}]
    settings = {"neighbours": {"k": 5, "candidate_floor": 0.0}}
    rows = tune.grid_search(vectors, items, pairs, {"p1": "same", "p2": "different"}, settings)
    assert {r["t_dup"]: r["f1"] for r in rows}[0.88] == 1.0   # cosine 0.9 merges at 0.88
    assert {r["t_dup"]: r["f1"] for r in rows}[0.95] == 0.0


def test_score_writes_named_agreement_and_limits_candidates(labelled):
    s = labelled.settings()
    metrics.run_agreement(s, "test")
    out = score.score(s, SETTINGS)
    report = json.loads(Path(out["score"]).read_text())
    assert "mock-a and mock-b" in report["statement"] and "cluster-test" in report["statement"]
    assert report["deterministic_checks"] and report["candidate"]["encoder"] == "table"
    assert "ratio_to_reference" in report["levels"]["duplicate"]
    score.score(s, SETTINGS)  # same candidate, same settings: allowed
    for n, enc in enumerate(("enc-1", "enc-2", "enc-3")):
        fake = {"candidate": {"name": f"other-{n}", "encoder": enc, "settings_sha256": "x"}}
        (metrics.analysis_dir(s) / f"score-other-{n}.json").write_text(json.dumps(fake))
    with pytest.raises(UsageError, match="encoders were already scored") as exc:
        score.score(s, SETTINGS, encoder=TableEncoder({}, dim=16, model_id="a-fourth-encoder"))
    assert exc.value.exit_code == 2


def test_stage_reads_the_decision(tmp_path):
    from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

    settings = yaml.safe_load(SETTINGS.read_text())
    settings["encoder"]["table"] = str(SETTINGS.parent / settings["encoder"]["table"])
    decision = {"task_stopped": False, "specificity_produced": False, "cluster_levels_produced": 1}
    (tmp_path / "decision.json").write_text(json.dumps(decision))
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.safe_dump({**settings, "decision": "decision.json"}))
    stage = ClusterStage.from_settings(path)
    assert stage.specificity_allowed is False and stage.cluster_levels_allowed == 1
    (tmp_path / "decision.json").write_text(json.dumps({**decision, "task_stopped": True}))
    with pytest.raises(UsageError, match="task is stopped"):
        ClusterStage.from_settings(path)
