"""Release gate for emlearn tree models (feature 007, T021, SC-006)."""

import json

from edge_fixture_forest import flip_first_score_bit
from test_edge_rules import declare, failures, run_gate


def _examples(env):
    return sorted((env.reg.model_dir(env.model) / "examples").glob("*.json"))


def test_forest_fixture_passes_offline_and_online(mcu_forest_env):
    gate = run_gate(mcu_forest_env)
    assert {s for s, _ in gate.results.values()} <= {"PASS", "SKIP"}, gate.results
    gate = run_gate(mcu_forest_env, online=True)
    bad = {n: r for n, r in gate.results.items() if r[0] == "FAIL"}
    assert not bad, bad
    for rule in (12, 13, 15):
        assert gate.results[rule][0] == "PASS", gate.results[rule]
    assert len(gate.example_outputs) == 3


def test_one_flipped_score_bit_fails_rules_12_and_13(mcu_forest_env):
    first = _examples(mcu_forest_env)[0]
    original = first.read_text()
    flip_first_score_bit(first)
    gate = run_gate(mcu_forest_env, online=True)
    assert "score of frame 0" in failures(gate, 12)
    assert "score of frame 0" in failures(gate, 13)
    first.write_text(original)
    gate = run_gate(mcu_forest_env, online=True)
    assert failures(gate, 12) == "" and failures(gate, 13) == ""


def test_changed_alarms_fail(mcu_forest_env):
    path = _examples(mcu_forest_env)[1]
    ex = json.loads(path.read_text())
    ex["expected_alarms"] = [*ex["expected_alarms"], len(ex["frames"]) - 1]
    path.write_text(json.dumps(ex))
    assert "alarms at frames" in failures(run_gate(mcu_forest_env, online=True), 13)


def test_example_from_unclear_dataset_fails(mcu_forest_env):
    declare(mcu_forest_env, "road")
    path = _examples(mcu_forest_env)[2]
    ex = json.loads(path.read_text())
    ex["source"] = "road"
    path.write_text(json.dumps(ex))
    assert "redistribution unclear" in failures(run_gate(mcu_forest_env), 13)


def test_staged_source_must_match_the_recipe_commit(mcu_forest_env):
    env = mcu_forest_env
    files = dict(env.files)
    files["c/picket_forest.c"] = files["c/picket_forest.c"] + b"\n/* changed */\n"
    repo = env.reg.model_raw(env.model)["repos"]["staging"]
    record = env.record()
    record["staging"]["revision"] = env.hub.seed(repo, files, private=True)
    env.set_record(record)
    assert "differs from" in failures(run_gate(env, online=True), 12)


def test_int8_fixture_unchanged(mcu_env):
    gate = run_gate(mcu_env, online=True)
    assert not {n: r for n, r in gate.results.items() if r[0] == "FAIL"}
