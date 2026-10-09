"""External datasets: declarations (licences, permitted use), downloader and training guard."""

from __future__ import annotations

from pathlib import Path

from mobility_model_zoo.release.errors import ZooError


class UsageRefused(ZooError):
    """The declaration forbids this use (rejected, broken, benchmark only, target in the repo)."""

    exit_code = 3


def require_training_allowed(ds_id: str, root: Path | None = None) -> None:
    """Refuse training on a dataset unless it is declared `training_allowed` and `active` (FR-017)."""
    from mobility_model_zoo.datasets.registry import load

    src = load(root).get(ds_id)
    if src is None:
        raise UsageRefused(f"{ds_id}: no dataset declaration in topics/*/compliance/datasets.yaml")
    if src.permitted_use != "training_allowed":
        raise UsageRefused(f"{ds_id}: permitted use is {src.permitted_use}, not training_allowed")
    if src.status != "active":
        raise UsageRefused(f"{ds_id}: status is {src.status} ({src.reason})")
