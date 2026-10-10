"""Gate rules for microcontroller models and dataset sources (feature 005 T056)."""

import copy
import json
from pathlib import Path

import pytest
import yaml
from test_gate_rules import edit_model, edit_record
from test_gate_rules import run_gate as _run_gate

from mobility_model_zoo.datasets.registry import declarations

ROOT = Path(__file__).resolve().parents[2]
GT_SENTENCE = (
    "Quality is measured against the labels of the datasets named below, on test data not used for "
    "training."
)


def run_gate(env, **kwargs):
    """The gate with its per-rule results, also when it fails."""
    from mobility_model_zoo.release.errors import GateFailed

    try:
        return _run_gate(env, **kwargs)
    except GateFailed as e:
        return e.gate


def failures(gate, rule):
    status, reason = gate.results[rule]
    return reason if status == "FAIL" else ""


def declare(env, *ids, **changes):
    """Copy real declarations into the fixture repository (topic sandbox)."""
    recs = [copy.deepcopy(r) for _, r in declarations(ROOT) if r["id"] in ids]
    for r in recs:
        r.update(changes.get(r["id"], {}))
    d = env.root / "topics" / "sandbox" / "compliance"
    d.mkdir(parents=True, exist_ok=True)
    (d / "datasets.yaml").write_text(yaml.safe_dump({"datasets": recs}), encoding="utf-8")


def source(ds, licence, use="training_allowed"):
    return {
        "origin": f"dataset {ds}",
        "license": licence,
        "permitted_use": use,
        "count": 10,
        "dataset": ds,
    }


# ---- the mcu fixture ---------------------------------------------------------------------------


def test_mcu_fixture_passes_offline_and_online(mcu_env):
    gate = run_gate(mcu_env)
    assert {s for s, _ in gate.results.values()} <= {"PASS", "SKIP"}, gate.results
    gate = run_gate(mcu_env, online=True)
    bad = {n: r for n, r in gate.results.items() if r[0] == "FAIL"}
    assert not bad, bad
    assert gate.results[12][0] == "PASS" and gate.results[13][0] == "PASS"
    assert gate.results[15][0] == "PASS"
    assert len(gate.example_outputs) == 3


# ---- rule 1 ------------------------------------------------------------------------------------


def test_rule1_mcu_needs_device_usage(mcu_env):
    edit_model(mcu_env, lambda m: m["card"].pop("device_usage"))
    assert "device_usage" in failures(run_gate(mcu_env), 1)


def test_rule1_python_needs_languages(zoo_env):
    edit_model(zoo_env, lambda m: m.update(languages=[]))
    assert "languages" in failures(run_gate(zoo_env), 1)


def test_rule1_budget_must_match_runtime(mcu_env):
    edit_record(mcu_env, lambda r: r["performance"].update(budget={"ram_gb": 1, "gpu": False}))
    assert "ram_kb" in failures(run_gate(mcu_env), 1)


# ---- rule 6 ------------------------------------------------------------------------------------


def test_rule6_undeclared_dataset(mcu_env):
    edit_record(mcu_env, lambda r: r["provenance"].update(sources=[source("road", "CC-BY-4.0")]))
    assert "not declared" in failures(run_gate(mcu_env), 6)


def test_rule6_licence_differs(mcu_env):
    declare(mcu_env, "road")
    edit_record(mcu_env, lambda r: r["provenance"].update(sources=[source("road", "CC0-1.0")]))
    assert "differs" in failures(run_gate(mcu_env), 6)


def test_rule6_share_alike_needs_same_model_licence(mcu_env):
    declare(mcu_env, "mimii")
    edit_record(mcu_env, lambda r: r["provenance"].update(sources=[source("mimii", "CC-BY-SA-4.0")]))
    assert "C-K2: dataset mimii (CC-BY-SA-4.0) makes the model share-alike" in failures(
        run_gate(mcu_env), 6)


def test_rule6_non_commercial_training_source(mcu_env):
    declare(mcu_env, "tue-can-v2")
    edit_record(
        mcu_env, lambda r: r["provenance"].update(sources=[source("tue-can-v2", "CC-BY-NC-4.0")])
    )
    # declared commercial: refused because the dataset is non-commercial (and rejected)
    assert "makes the model non-commercial, but it is declared commercial" in failures(
        run_gate(mcu_env), 6)


def test_rule6_hum_fan_like_settings_pass(mcu_env):
    declare(mcu_env, "mimii")
    edit_model(
        mcu_env,
        lambda m: m.update(license="CC-BY-SA-4.0", license_exception="trained on MIMII (CC BY-SA 4.0)",
                           usage_class="commercial-share-alike"),
    )
    usage = {"class": "commercial-share-alike", "licence": "CC-BY-SA-4.0", "restricting_inputs": [
        {"kind": "dataset", "id": "mimii", "licence": "CC-BY-SA-4.0", "restriction": "share-alike"}]}
    edit_record(mcu_env, lambda r: r.update(usage=usage))
    edit_record(mcu_env, lambda r: r["provenance"].update(sources=[source("mimii", "CC-BY-SA-4.0")]))
    assert failures(run_gate(mcu_env), 6) == ""


# ---- rule 10 -----------------------------------------------------------------------------------


def test_rule10_ground_truth_sentence_and_accuracy(mcu_env):
    gate = run_gate(mcu_env)
    assert failures(gate, 10) == ""
    assert GT_SENTENCE in " ".join(gate.card.split())
    assert "int8_accuracy" in gate.card


def test_rule10_model_consensus_keeps_the_ban(mcu_env):
    edit_record(mcu_env, lambda r: r["evaluation"].update(reference_kind="model_consensus"))
    reason = failures(run_gate(mcu_env), 10)
    assert "accuracy" in reason


# ---- rules 12/13 -------------------------------------------------------------------------------


def _edit_example(env, fn, name="01-random.json"):
    p = env.reg.model_dir(env.model) / "examples" / name
    ex = json.loads(p.read_text())
    fn(ex)
    p.write_text(json.dumps(ex))


def test_rule13_changed_expected_byte_fails(mcu_env):
    _edit_example(mcu_env, lambda ex: ex["expected"].__setitem__(0, ex["expected"][0] ^ 1))
    gate = run_gate(mcu_env, online=True)
    assert "differs" in failures(gate, 12) and "differs" in failures(gate, 13)


def test_rule13_unclear_redistribution_source_fails(mcu_env):
    declare(mcu_env, "road")
    _edit_example(mcu_env, lambda ex: ex.update(source="road"))
    assert "redistribution unclear" in failures(run_gate(mcu_env), 13)


def test_rule13_needs_three_examples(mcu_env):
    (mcu_env.reg.model_dir(mcu_env.model) / "examples" / "03-random.json").unlink()
    assert "at least 3" in failures(run_gate(mcu_env), 13)


# ---- rule 15 -----------------------------------------------------------------------------------


def _edit_performance(env, fn):
    path = env.reg.model_dir(env.model) / "results" / env.version / "performance.json"
    data = json.loads(path.read_text())
    fn(data)
    path.write_text(json.dumps(data))


def test_rule15_missing_flash_fails(mcu_env):
    _edit_performance(
        mcu_env, lambda d: d.update(metrics=[m for m in d["metrics"] if m["name"] != "flash_kb"])
    )
    assert "flash_kb" in failures(run_gate(mcu_env), 15)


def test_rule15_stable_needs_a_real_board_latency(mcu_env):
    edit_record(mcu_env, lambda r: r.update(status="released"))
    assert "real-board" in failures(run_gate(mcu_env), 15)


def test_rule15_experimental_with_emulator_passes(mcu_env):
    assert failures(run_gate(mcu_env), 15) == ""


# ---- regression --------------------------------------------------------------------------------


def test_python_fixture_unchanged(zoo_env, runner):
    gate = run_gate(zoo_env, online=True, runner=runner)
    # 15: mcu only; 16: no compliance register in fixtures; 17: sandbox models have no website page
    assert all(s == "PASS" for n, (s, _) in gate.results.items() if n not in (15, 16, 17)), gate.results


@pytest.mark.parametrize("path", sorted(ROOT.glob("zoo/models/*/releases/*.yaml")), ids=lambda p: p.name)
def test_published_records_validate(path):
    from mobility_model_zoo.release.registry import Registry, schema_errors

    if path.name.endswith(".compliance.yaml"):
        pytest.skip("compliance record")
    record = Registry(ROOT).record_raw(path.parent.parent.name, path.stem)
    if not record.get("published"):
        pytest.skip("draft: `zoo check --offline` reports what is missing")
    assert schema_errors("release-record", record) == []
