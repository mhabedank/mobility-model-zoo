import pytest
from compliance_helpers import load, write

from mobility_model_zoo.compliance.findings import Finding, StageFailed, require, run_stages


def _stage(name, findings, calls):
    def fn(ctx):
        calls.append(name)
        return findings

    return (name, fn)


def test_runner_stops_after_first_failing_stage():
    calls: list[str] = []
    bad = Finding("C-M1", "a", "r", "f", "x")
    stages = [_stage("a", [], calls), _stage("b", [bad], calls), _stage("c", [], calls)]
    with pytest.raises(StageFailed) as e:
        run_stages(stages, None)
    assert calls == ["a", "b"]
    assert e.value.findings == [bad]
    assert e.value.failures == ["a / r / f / x [C-M1]"]


def test_all_stages_pass():
    calls: list[str] = []
    assert run_stages([_stage("a", [], calls), _stage("b", [], calls)], None) == ["a", "b"]


def _req(rec, waiver=False):
    return require(
        rec, "licence", check_id="C-I1", stage="ingest", record_id="s", waiver_ok=lambda c, r: waiver
    )


def test_missing_value_fails():
    assert _req({}).reason == "missing"
    assert _req({"licence": ""}).reason == "missing"


def test_unknown_needs_date_and_waiver():
    assert "unknown_checked_at" in _req({"licence": "unknown"}).reason
    dated = {"licence": "unknown", "unknown_checked_at": "2026-10-08"}
    assert "no valid waiver" in _req(dated).reason
    assert _req(dated, waiver=True) is None


def test_waiver_expiry(register_tree):
    write(
        register_tree,
        "compliance/waivers.yaml",
        {
            "waivers": [
                {
                    "id": "w1",
                    "check": "C-I1",
                    "scope": "s",
                    "rationale": "r",
                    "approved_by": "owner",
                    "approved_at": "2026-10-01",
                    "expires_at": "2026-12-01",
                },
                {
                    "id": "w2",
                    "check": "C-I2",
                    "scope": "s",
                    "rationale": "r",
                    "approved_by": "owner",
                    "approved_at": "2026-05-01",
                    "expires_at": "2026-10-01",
                },
            ]
        },
    )
    reg = load(register_tree)
    assert reg.waiver_ok("C-I1", "s")
    assert not reg.waiver_ok("C-I2", "s")  # expired
    assert not reg.waiver_ok("C-I1", "other")
