import json

from helpers import copy_fixture, pilot, run_ids

from jtbd_pilot.config import load_settings


def test_refuses_without_freeze(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a",
          expect=3)


def test_budget_refusal(tmp_path):
    config = copy_fixture(tmp_path)
    settings = load_settings(config)
    settings.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    settings.ledger_path.write_text(json.dumps(
        {"item": "vm", "backend": "manual", "estimated_eur": 25, "actual_eur": 25}) + "\n")
    pilot(config, "freeze")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a",
          expect=4)


def test_role_rules(tmp_path):
    config = copy_fixture(tmp_path)
    models = config.parent / "models.yaml"
    models.write_text(models.read_text() + (
        "- model_id: mock-teacher\n  family: fam-a\n  backend: mock\n  host: local\n"
        "  role: teacher_candidate\n  license_basis: MIT\n"
        "- model_id: mock-a-as-teacher\n  family: fam-z\n  backend: mock\n  host: local\n"
        "  role: teacher_candidate\n  benchmark_labeler: true\n  license_basis: MIT\n"))
    pilot(config, "freeze")
    pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock",
          "--model", "mock-teacher", expect=1)
    pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock",
          "--model", "mock-a-as-teacher", expect=1)
    pilot(config, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-a",
          expect=1)


def test_holdout_locked(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a",
          "--split", "holdout", expect=1)


def test_resume_and_raw_never_overwritten(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    first = pilot(config, "label", "--role", "reference", "--backend", "mock", "--model",
                  "mock-a", "--limit", "2")
    assert first["processed_now"] == 2 and first["status"] == "running"
    run = run_ids(config)["mock-a"]
    raw_dir = load_settings(config).runs_dir / run / "raw"
    before = {p.name: p.read_bytes() for p in raw_dir.iterdir()}
    second = pilot(config, "label", "--role", "reference", "--backend", "mock", "--model",
                   "mock-a")
    assert second["processed_now"] == 3 and second["status"] == "complete"
    after = {p.name: p.read_bytes() for p in raw_dir.iterdir()}
    assert all(after[k] == v for k, v in before.items())


def test_schema_failure_is_excluded_not_repaired(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    result = pilot(config, "label", "--role", "baseline", "--backend", "mock", "--model",
                   "mock-small")
    assert result["excluded"] == 1


def test_model_version_change_stops_run(tmp_path, monkeypatch):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    from jtbd_pilot.labeling import mock

    calls = {"n": 0}
    original = mock.MockBackend.call

    def flaky(self, *args):
        result = original(self, *args)
        calls["n"] += 1
        if calls["n"] == 3:
            result.model_version = "mock-other"
        return result

    monkeypatch.setattr(mock.MockBackend, "call", flaky)
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a",
          expect=6)
    manifest = json.loads((load_settings(config).runs_dir / run_ids(config)["mock-a"]
                           / "manifest.json").read_text())
    assert manifest["status"] == "invalid_version_change"
