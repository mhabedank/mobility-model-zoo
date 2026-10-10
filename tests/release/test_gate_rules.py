"""Each gate rule fails on its broken fixture and passes on the valid one (T021, T041)."""

from __future__ import annotations

import pytest
from conftest import FakeRunner, ZooEnv

from mobility_model_zoo.release.errors import GateFailed, ImmutabilityRefused
from mobility_model_zoo.release.gate import Gate


def run_gate(env: ZooEnv, online: bool = False, runner=None, card=None) -> Gate:
    gate = Gate(
        env.reg,
        env.model,
        env.version,
        hub=env.hub if online else None,
        runner=runner if online else None,
        card=card,
    )
    gate.run(lambda line: None)
    return gate


def edit_model(env: ZooEnv, fn) -> None:
    from mobility_model_zoo.release.registry import dump_yaml

    data = env.reg.model_raw(env.model)
    fn(data)
    (env.reg.model_dir(env.model) / "model.yaml").write_text(dump_yaml(data), encoding="utf-8")


def edit_record(env: ZooEnv, fn) -> None:
    data = env.record()
    fn(data)
    env.set_record(data)


def test_valid_fixture_passes_offline(zoo_env):
    gate = run_gate(zoo_env)
    assert {s for s, _ in gate.results.values()} <= {"PASS", "SKIP"}
    assert gate.results[5][0] == "SKIP" and gate.results[12][0] == "SKIP"


def test_valid_fixture_passes_online(zoo_env, runner):
    gate = run_gate(zoo_env, online=True, runner=runner)
    # Rule 15 (device evidence) is for mcu models; rule 16 (compliance) skips in fixture registries
    # without a compliance register.
    skipped = {15, 16, 17}  # rule 17 (site text, feature 008) skips sandbox models
    assert all(s == "PASS" for n, (s, _) in gate.results.items() if n not in skipped), gate.results
    assert gate.results[15][0] == "SKIP" and gate.results[16][0] == "SKIP"
    assert len(gate.example_outputs) == 3


BROKEN = {
    1: lambda env: edit_model(env, lambda m: m.pop("license")),
    2: lambda env: edit_model(env, lambda m: m.update(variant="other")),  # name must end with it
    3: lambda env: edit_record(env, lambda r: r.update(status="released")),
    6: lambda env: edit_record(
        env,
        lambda r: r["provenance"]["teachers"].append(
            {"model_id": "x", "license_basis": "proprietary", "training_on_outputs_permitted": False}
        ),
    ),
    7: lambda env: edit_record(env, lambda r: r["provenance"].update(spike_data=True)),
    8: lambda env: edit_record(env, lambda r: r["recipe"].update(git_commit="1" * 40)),
    11: lambda env: edit_record(
        env,
        lambda r: r["files"].append({"path": "data/labels.jsonl", "sha256": "0" * 64, "size_bytes": 1}),
    ),
    14: lambda env: edit_record(env, lambda r: r.update(sandbox=False)),
}


@pytest.mark.parametrize("rule", sorted(BROKEN))
def test_offline_rule_fails_on_its_broken_fixture(zoo_env, rule):
    BROKEN[rule](zoo_env)
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env)
    assert any(f.startswith(f"rule {rule}:") for f in exc.value.failures), exc.value.failures


def test_rule_4_already_published_is_an_immutability_refusal(zoo_env):
    edit_record(
        zoo_env,
        lambda r: r.update(
            published={
                "repo_commit": "2" * 40,
                "tag": "v0.1.0",
                "published_at": "2026-10-01T10:00:00Z",
                "card_sha256": "3" * 64,
            }
        ),
    )
    with pytest.raises(ImmutabilityRefused):
        run_gate(zoo_env)


def test_rule_4_existing_tag_on_the_hub(zoo_env, runner):
    hub = zoo_env.hub
    sha = hub.seed("mobility-model-zoo/sandbox-pipeline-tiny", {"x": b"1"}, private=True)
    hub.repos["mobility-model-zoo/sandbox-pipeline-tiny"].tags["v0.1.0"] = sha
    with pytest.raises(ImmutabilityRefused):
        run_gate(zoo_env, online=True, runner=runner)


def test_rule_5_staged_file_mismatch(zoo_env, runner):
    hub = zoo_env.hub
    hub.seed("mobility-model-zoo/sandbox-pipeline-tiny-staging", {"config.json": b"changed"})
    edit_record(
        zoo_env, lambda r: r["staging"].update(revision=hub.repos[r["staging"]["repo"]].branches["main"])
    )
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env, online=True, runner=runner)
    assert any(f.startswith("rule 5:") and "config.json" in f for f in exc.value.failures)


def test_rule_5_public_staging_repo(zoo_env, runner):
    zoo_env.hub.repos["mobility-model-zoo/sandbox-pipeline-tiny-staging"].private = False
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env, online=True, runner=runner)
    assert any(f.startswith("rule 5:") and "public" in f for f in exc.value.failures)


def test_rule_9_quality_metric_without_reference(zoo_env):
    import json

    path = zoo_env.reg.results_path(zoo_env.model, zoo_env.version, "quality")
    data = json.loads(path.read_text())
    data["metrics"][0]["reference"] = None
    path.write_text(json.dumps(data))
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env)
    assert any(f.startswith("rule 9:") for f in exc.value.failures)


def test_rule_9_card_number_not_in_results(zoo_env):
    from mobility_model_zoo.release import card as cards

    text = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version))
    tampered = text.replace("| `item_f1` | 0.5 |", "| `item_f1` | 0.9 |")
    assert tampered != text
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env, card=tampered)
    assert any(f.startswith("rule 9:") and "item_f1" in f for f in exc.value.failures)


def test_rule_10_hub_warning_counts_as_failure(zoo_env, runner):
    zoo_env.hub.validation = {"errors": [], "warnings": ["unknown pipeline_tag"]}
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env, online=True, runner=runner)
    assert any(f.startswith("rule 10:") and "warning" in f for f in exc.value.failures)


def test_rule_10_accuracy_is_forbidden(zoo_env):
    from mobility_model_zoo.release import card as cards

    text = cards.render(cards.CardInput(zoo_env.reg, zoo_env.model, zoo_env.version))
    with pytest.raises(GateFailed) as exc:
        run_gate(
            zoo_env,
            card=text.replace(
                "## Limitations and risks\n", "## Limitations and risks\n\nAccuracy 99%.\n"
            ),
        )
    assert any(f.startswith("rule 10:") and "accuracy" in f for f in exc.value.failures)


def test_rule_12_failing_usage_example(zoo_env):
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env, online=True, runner=FakeRunner(returncode=1))
    assert any(f.startswith("rule 12:") for f in exc.value.failures)


def test_rule_13_needs_three_examples(zoo_env):
    (zoo_env.reg.model_dir(zoo_env.model) / "examples" / "03-delay-app.txt").unlink()
    with pytest.raises(GateFailed) as exc:
        run_gate(zoo_env)
    assert any(f.startswith("rule 13:") for f in exc.value.failures)


def test_rule_12_runs_against_the_staged_files(zoo_env, runner):
    run_gate(zoo_env, online=True, runner=runner)
    record = zoo_env.record()
    assert all(record["staging"]["repo"] in code for code in runner.calls)
    assert all(record["staging"]["revision"] in code for code in runner.calls)
