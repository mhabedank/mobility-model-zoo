"""The pilot's decision as a gate for training data and training (feature 004, FR-001, R5).

Reads `decision.json` of the benchmark a training dataset excludes (`span_train.exclude_benchmark`):
which label dimensions passed, and which teacher the pilot recommends.
"""

from __future__ import annotations

from typing import Any

from mobility_model_zoo.productdev.jtbd.config import ModelEntry, Settings
from mobility_model_zoo.productdev.jtbd.corpus.separation import benchmark_settings
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import load_manifest
from mobility_model_zoo.productdev.jtbd.jsonio import read_json

CORE = ("relevance", "item_matching", "kind")
ATTRIBUTES = ("actor_type", "evidence_type", "evidence_scope")


def pilot_decision(settings: Settings) -> tuple[Settings, dict[str, Any]]:
    """(benchmark settings, decision.json). Refuses while the pilot has not decided."""
    bench = benchmark_settings(settings)
    path = bench.analysis_dir / "decision.json"
    if not path.exists():
        raise ValidationFailed(f"the pilot has not decided yet ({path} is missing); training "
                               "data waits for the pilot (FR-001)")
    return bench, read_json(path)


def passed_attributes(decision: dict[str, Any]) -> list[str]:
    """Attribute dimensions that passed the pilot; refuses if a core dimension failed."""
    per_dim = decision.get("per_dimension") or {}
    failed_core = [d for d in CORE if not (per_dim.get(d) or {}).get("passed")]
    if failed_core:
        raise ValidationFailed(f"core dimensions failed the pilot: {failed_core}; the span model "
                               "cannot be trained (spec edge cases)")
    return [d for d in ATTRIBUTES if (per_dim.get(d) or {}).get("passed")]


def recommended_teacher(decision: dict[str, Any]) -> str:
    recommended = (decision.get("teacher_fitness") or {}).get("recommended")
    if not recommended:
        raise ValidationFailed("the pilot recommends no fit teacher; training data cannot be "
                               "generated (spec edge cases)")
    return recommended


def teacher_models(settings: Settings, decision: dict[str, Any]) -> set[str]:
    """Models allowed on the training split: the recommended teacher, and the members of the
    recommended ensemble (they label, the ensemble combines)."""
    recommended = recommended_teacher(decision)
    ensemble = settings.teacher_scoring().teacher_ensemble
    members = set(ensemble.members) if recommended == ensemble.model_id else set()
    return {recommended} | members


def check_teacher(settings: Settings, entry: ModelEntry, split: str,
                  frozen: dict[str, Any]) -> None:
    """`jtbd label --role teacher`: train split, recommended teacher, the decision's hashes."""
    if split != "train":
        raise ValidationFailed("role teacher labels the train split only")
    bench, decision = pilot_decision(settings)
    allowed = teacher_models(settings, decision)
    if entry.model_id not in allowed:
        raise ValidationFailed(f"{entry.model_id} is not the pilot's recommended teacher "
                               f"({sorted(allowed)})")
    check_hashes(bench, frozen)


def check_hashes(bench: Settings, frozen: dict[str, Any]) -> None:
    """Guideline and output schema must be those of the pilot's final decision."""
    decided = load_manifest(bench) or {}
    for key in ("guideline", "schema"):
        if (decided.get("hashes") or {}).get(key) != frozen["hashes"].get(key):
            raise ValidationFailed(f"the {key} differs from the one of the pilot's final decision "
                                   f"({decided.get('version')})")
