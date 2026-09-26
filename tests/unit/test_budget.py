import shutil

import pytest

from jtbd_pilot import budget
from jtbd_pilot.config import ModelEntry, load_settings
from jtbd_pilot.errors import BudgetRefused
from jtbd_pilot.jsonio import read_jsonl


@pytest.fixture
def settings(tmp_path, fixture_dir):
    work = tmp_path / "mini"
    shutil.copytree(fixture_dir, work)
    (work / "budget.yaml").write_text(
        "budget_eur: 20\nkey_cap_eur: 12\nopenrouter_fee: 0.0\nusd_to_eur: 1.0\n"
        "prices:\n  gpt:\n    input: 1.0\n    cached_input: 0.1\n    output: 4.0\n"
    )
    return load_settings(work / "pilot.yaml")


GPT = ModelEntry(model_id="gpt", family="openai-gpt", backend="openrouter", host="openai",
                 role="reference")
CLAUDE = ModelEntry(model_id="claude", family="anthropic-claude", backend="claude_cli",
                    host="subscription", role="reference")


def test_estimate_uses_prices_and_cached_input(settings):
    # 1000 chunks x (1000 uncached*1 + 5000 cached*0.1 + 1000 out*4) / 1e6 = 5.5 EUR
    assert budget.estimate_run(settings, GPT, 1000, 6000, 5000, 1000) == pytest.approx(5.5)


def test_subscription_and_local_cost_nothing(settings):
    assert budget.estimate_run(settings, CLAUDE, 1000, 6000, 0, 1500) == 0.0


def test_guard_refuses_over_key_cap(settings):
    budget.record(settings, "run-1", "openrouter", 10.0, 10.0)
    budget.guard(settings, 1.5, "openrouter")  # 11.5 <= 12
    with pytest.raises(BudgetRefused):
        budget.guard(settings, 2.5, "openrouter")  # 12.5 > 12


def test_guard_refuses_over_total_budget(settings):
    budget.record(settings, "vm", "manual", 9.0, 9.0)
    budget.record(settings, "run-1", "openrouter", 10.0, 10.0)
    with pytest.raises(BudgetRefused):
        budget.guard(settings, 1.5, "manual")  # 20.5 > 20


def test_ledger_is_append_only(settings):
    budget.record(settings, "a", "openrouter", 1.0, 0.8)
    budget.record(settings, "b", "manual", 1.0, None)
    rows = list(read_jsonl(settings.ledger_path))
    assert [r["item"] for r in rows] == ["a", "b"]
    assert rows[1]["cumulative_eur"] == pytest.approx(1.8)
