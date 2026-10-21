"""Gate rule 7: no Claude inputs behind a release (feature 021, T055; FR-027, research R21)."""

from mobility_model_zoo.release.claude_check import claude_findings, is_claude

CLAUDE_CLI = {"id": "claude-cli", "model_id": "claude-reference", "model_family": "claude"}
GPT = {"id": "gpt", "model_id": "gpt-mini-reference", "model_family": "gpt"}
DECISION = {
    "id": "D-claude-risk",
    "scope": ["scout@0.1.3", "benchmark:pilot-v2", "compliance/providers.yaml#claude-cli"],
}


def _check(**kw):
    args = {
        "model": "m",
        "version": "0.1.0",
        "teachers": [],
        "routes": [],
        "roles": {},
        "decisions": [],
        "evaluation_reference": "labels of the uci-har dataset",
    }
    return claude_findings(**{**args, **kw})


def test_a_release_without_teachers_or_routes_passes_and_says_so():
    failures, note = _check()
    assert failures == []
    assert note.startswith("no Claude inputs (0 teachers, 0 routes checked)")


def test_family_field_and_name_pattern_both_identify_claude():
    assert is_claude({"model_family": "claude"})
    assert is_claude({"model_id": "x", "hosting_provider": "Anthropic (Commercial Terms)"})
    assert is_claude({"model_id": "Claude-Sonnet"})
    assert not is_claude(GPT)


def test_a_claude_teacher_always_fails():
    failures, _ = _check(teachers=[{"model_id": "claude-reference"}], decisions=[DECISION])
    assert failures and "never a teacher" in failures[0]


def test_a_teacher_resolved_through_a_claude_route_fails():
    failures, _ = _check(
        teachers=[{"model_id": "opaque-id"}],
        provider_routes=[{"id": "r", "model_id": "opaque-id", "model_family": "claude"}],
    )
    assert failures


def test_a_claude_labeling_route_fails():
    failures, _ = _check(routes=[CLAUDE_CLI], roles={"claude-cli": {"labeling"}})
    assert failures and "roles labeling" in failures[0]


def test_frozen_reference_passes_only_with_a_decision_for_this_release():
    ok, note = _check(
        model="scout",
        version="0.1.3",
        routes=[CLAUDE_CLI, GPT],
        roles={"claude-cli": {"reference"}, "gpt": {"reference"}},
        decisions=[DECISION],
        evaluation_reference="consensus of claude-reference and gpt-mini-reference",
    )
    assert ok == []
    assert "Claude only claude-cli as frozen benchmark reference (D-claude-risk)" in note
    later, _ = _check(
        model="scout",
        version="0.2.0",
        routes=[CLAUDE_CLI],
        roles={"claude-cli": {"reference"}},
        decisions=[DECISION],
    )
    assert later and "no owner decision" in later[0]


def test_reference_plus_another_role_is_not_excepted():
    failures, _ = _check(
        model="scout",
        version="0.1.3",
        routes=[CLAUDE_CLI],
        roles={"claude-cli": {"reference", "teacher"}},
        decisions=[DECISION],
    )
    assert failures


def test_a_claude_evaluation_reference_without_a_decision_fails():
    failures, _ = _check(evaluation_reference="judged by claude")
    assert failures and "evaluation reference" in failures[0]


def test_gate_rule_7_reports_the_confirmation(mcu_env):
    from mobility_model_zoo.release.gate import Gate

    gate = Gate(mcu_env.reg, mcu_env.model, mcu_env.version)  # offline: hub None
    lines = []
    try:
        gate.run(lines.append)
    except Exception:
        pass
    rule7 = next(line for line in lines if line.startswith("rule  7"))
    assert "PASS: no Claude inputs" in rule7


def test_gate_rule_7_fails_on_a_claude_teacher(mcu_env):
    from mobility_model_zoo.release.gate import Gate

    record = mcu_env.record()
    record["provenance"]["teachers"] = [
        {"model_id": "claude-x", "license_basis": "-", "training_on_outputs_permitted": True}
    ]
    mcu_env.set_record(record)
    gate = Gate(mcu_env.reg, mcu_env.model, mcu_env.version)  # offline: hub None
    lines = []
    try:
        gate.run(lines.append)
    except Exception:
        pass
    rule7 = next(line for line in lines if line.startswith("rule  7"))
    assert "FAIL" in rule7 and "Claude" in rule7
