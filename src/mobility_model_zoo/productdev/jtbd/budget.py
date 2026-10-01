"""Cash budget ledger and pre-call guard (constitution: Resources & Cost Discipline, SC-009).

The ledger is append-only JSONL. Each row is one charge: a completed (or interrupted) label run,
a frontier perf sample, or a manual item such as the reference VM.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import ModelEntry, Settings
from mobility_model_zoo.productdev.jtbd.errors import BudgetRefused, UsageError
from mobility_model_zoo.productdev.jtbd.jsonio import append_jsonl, read_jsonl

PAID_BACKENDS = {"openrouter"}


def ledger_rows(settings: Settings) -> list[dict[str, Any]]:
    return list(read_jsonl(settings.ledger_path))


def _charge(row: dict[str, Any]) -> float:
    actual = row.get("actual_eur")
    return float(actual if actual is not None else row.get("estimated_eur") or 0.0)


def spent(settings: Settings, backend: str | None = None) -> float:
    rows = ledger_rows(settings)
    if backend:
        rows = [r for r in rows if r.get("backend") == backend]
    return round(sum(_charge(r) for r in rows), 6)


def estimate_run(
    settings: Settings,
    model: ModelEntry,
    n_chunks: int,
    avg_in: float,
    avg_cached_in: float,
    avg_out: float,
) -> float:
    """Estimated EUR for a run. Subscription (claude_cli), local (ollama) and mock runs cost 0."""
    if model.backend not in PAID_BACKENDS:
        return 0.0
    budget = settings.budget()
    price = (budget.get("prices") or {}).get(model.model_id)
    if not price or any(price.get(k) is None for k in ("input", "output")):
        raise UsageError(
            f"no price for {model.model_id} in {settings.paths['budget']}; fill it in (T046)"
        )
    cached_price = price.get("cached_input")
    if cached_price is None:
        cached_price = price["input"]
    uncached = max(avg_in - avg_cached_in, 0.0)
    per_chunk = (
        uncached * price["input"] + avg_cached_in * cached_price + avg_out * price["output"]
    ) / 1_000_000
    fee = float(budget.get("openrouter_fee", 0.0))
    return round(per_chunk * n_chunks * (1 + fee), 6)


def guard(settings: Settings, estimated_eur: float, backend: str) -> None:
    """Refuse when the run would exceed the total budget or, for paid keys, the key cap."""
    budget = settings.budget()
    total_cap = float(budget["budget_eur"])
    total_after = spent(settings) + estimated_eur
    if total_after > total_cap:
        raise BudgetRefused(
            f"run would bring total spend to EUR {total_after:.2f}, above the budget of "
            f"EUR {total_cap:.2f}"
        )
    if backend in PAID_BACKENDS:
        key_cap = float(budget["key_cap_eur"])
        key_after = spent(settings, backend) + estimated_eur
        if key_after > key_cap:
            raise BudgetRefused(
                f"run would bring {backend} spend to EUR {key_after:.2f}, above the key cap of "
                f"EUR {key_cap:.2f}"
            )


def record(
    settings: Settings,
    item: str,
    backend: str,
    estimated_eur: float,
    actual_eur: float | None,
) -> dict[str, Any]:
    row = {
        "ts": datetime.now(UTC).isoformat(),
        "item": item,
        "backend": backend,
        "estimated_eur": round(estimated_eur, 6),
        "actual_eur": None if actual_eur is None else round(actual_eur, 6),
    }
    row["cumulative_eur"] = round(spent(settings) + _charge(row), 6)
    row["cap_eur"] = float(settings.budget()["budget_eur"])
    append_jsonl(settings.ledger_path, row)
    return row


def summary(settings: Settings) -> dict[str, Any]:
    budget = settings.budget()
    return {
        "budget_eur": budget["budget_eur"],
        "key_cap_eur": budget["key_cap_eur"],
        "spent_eur": spent(settings),
        "spent_openrouter_eur": spent(settings, "openrouter"),
        "remaining_eur": round(float(budget["budget_eur"]) - spent(settings), 6),
        "rows": len(ledger_rows(settings)),
    }
