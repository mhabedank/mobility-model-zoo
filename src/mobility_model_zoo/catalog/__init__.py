"""Mobility resource index (feature 009): a metadata-only catalogue of mobility resources in every
language and modality, so that later features can fetch them for training.

Entries live in the private repository mobility-model-zoo-catalog, never in this public repository
(research R1). This package holds the schemas, vocabularies, licence rules and the `zoo catalog` CLI.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from mobility_model_zoo.catalog.model import Catalog, load
from mobility_model_zoo.datasets import UsageRefused

RECHECK_DAYS = 180

__all__ = ["Catalog", "load", "require_cleared"]


def require_cleared(entry_id: str, catalog: Catalog, today: dt.date | None = None) -> dict[str, Any]:
    """The entry, if it is cleared and was verified within the last 180 days; else UsageRefused."""
    entry = catalog.entries.get(entry_id)
    if entry is None:
        raise UsageRefused(f"{entry_id}: no such catalog entry")
    status = (entry.get("status") or {}).get("value")
    if status != "cleared":
        raise UsageRefused(f"{entry_id}: status is {status}, not cleared")
    verified = (entry.get("provenance") or {}).get("last_verified")
    today = today or dt.date.today()
    if not verified or (today - dt.date.fromisoformat(verified)).days > RECHECK_DAYS:
        raise UsageRefused(f"{entry_id}: last verified {verified or 'never'}; run `zoo catalog check`")
    return entry
