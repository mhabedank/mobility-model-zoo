"""Named budgets on one shared ledger (feature 004, T004) and the training dataset config (T003)."""

import shutil
from pathlib import Path

import pytest
import yaml

from mobility_model_zoo.productdev.jtbd import budget
from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.errors import BudgetRefused, UsageError
from mobility_model_zoo.productdev.jtbd.jsonio import read_jsonl

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def work(tmp_path, fixture_dir):
    work = tmp_path / "mini"
    shutil.copytree(fixture_dir, work)
    (work / "budget.yaml").write_text("budget_eur: 20\nkey_cap_eur: 12\nprices: {}\n")
    (work / "budget-span.yaml").write_text(
        "budget_eur: 5\nkey_cap_eur: 4\napi_key_env: KEY_SPAN\nprices: {}\n")
    raw = yaml.safe_load((work / "pilot.yaml").read_text())
    raw["budget_name"] = "span-test"
    raw["paths"]["budget"] = "budget-span.yaml"
    raw["paths"]["ledger"] = "store/budget/ledger.jsonl"
    (work / "span.yaml").write_text(yaml.safe_dump(raw))
    return work


def test_rows_carry_the_budget_name_and_budgets_are_counted_apart(work):
    pilot = load_settings(work / "pilot.yaml")
    span = load_settings(work / "span.yaml")
    assert pilot.budget_name == "pilot-v1"
    budget.record(pilot, "run-p", "openrouter", 3.0, 3.0)
    budget.record(span, "run-s", "openrouter", 2.0, 2.0)
    rows = list(read_jsonl(span.ledger_path))
    assert [r["budget"] for r in rows] == ["pilot-v1", "span-test"]
    assert budget.spent(pilot) == 3.0
    assert budget.spent(span) == 2.0
    assert budget.summary(span)["budget"] == "span-test"


def test_rows_without_a_name_belong_to_the_pilot(work):
    pilot = load_settings(work / "pilot.yaml")
    span = load_settings(work / "span.yaml")
    pilot.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    pilot.ledger_path.write_text('{"item": "old", "backend": "openrouter", "actual_eur": 1.5}\n')
    assert budget.spent(pilot) == 1.5
    assert budget.spent(span) == 0.0


def test_guard_uses_the_named_budget_caps(work):
    span = load_settings(work / "span.yaml")
    budget.guard(span, 3.9, "openrouter")
    with pytest.raises(BudgetRefused):
        budget.guard(span, 4.1, "openrouter")  # key cap 4 of the named budget


def test_unknown_top_level_and_span_train_keys_fail(work):
    raw = yaml.safe_load((work / "pilot.yaml").read_text())
    (work / "bad.yaml").write_text(yaml.safe_dump({**raw, "surprise": 1}))
    with pytest.raises(UsageError, match="unknown keys"):
        load_settings(work / "bad.yaml")
    (work / "bad2.yaml").write_text(yaml.safe_dump({**raw, "span_train": {"surprise": 1}}))
    with pytest.raises(UsageError, match="unknown span_train keys"):
        load_settings(work / "bad2.yaml")


def test_span_train_v1_config_loads_with_sampled_review():
    settings = load_settings(REPO / "configs/productdev/jtbd/span-train-v1.yaml")
    assert settings.budget_name == "span-xlmr-0.1.0"
    assert settings.redaction_review == "sampled"
    assert settings.span_train["min_usable_chunks"] == 600
    assert settings.span_train["validation"]["seed"] == 20261002
    assert settings.budget()["api_key_env"] == "OPENROUTER_API_KEY_SPAN"
    assert settings.data_dir.name == "span-train-v1"


def test_pilot_configs_keep_full_review():
    for name in ("pilot-v1.yaml", "spike-v1.yaml"):
        settings = load_settings(REPO / "configs/productdev/jtbd" / name)
        assert settings.span_train is None
        assert settings.redaction_review == "full"
        assert settings.budget_name == "pilot-v1"
