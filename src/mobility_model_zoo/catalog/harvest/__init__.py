"""Harvesters: deterministic discovery from catalogue APIs (research R6).

`run_harvester` looks a harvester up by name; each module defines one class with the attributes of
`base.Harvester`.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path

from mobility_model_zoo.catalog.harvest.base import Scope, harvest
from mobility_model_zoo.release.errors import UsageError

REGISTRY = {
    "data-europa": ("data_europa", "DataEuropa"),
    "mobility-database": ("mobility_database", "MobilityDatabase"),
    "openalex": ("openalex", "OpenAlex"),
    "zenodo": ("zenodo", "Zenodo"),
    "huggingface": ("huggingface", "HuggingFace"),
    "wikimedia-commons": ("wikimedia_commons", "WikimediaCommons"),
    "podcast-index": ("podcast_index", "PodcastIndex"),
}


def get(name: str):
    if name not in REGISTRY:
        raise UsageError(f"unknown harvester {name} (known: {', '.join(REGISTRY)})")
    module, cls = REGISTRY[name]
    try:
        mod = importlib.import_module(f"mobility_model_zoo.catalog.harvest.{module}")
    except ModuleNotFoundError as e:
        raise UsageError(f"harvester {name} is not implemented yet") from e
    return getattr(mod, cls)()


def run_harvester(
    root: Path,
    name: str,
    *,
    languages: list[str],
    areas: list[str],
    subdomains: list[str],
    limit: int,
    run_id: str | None,
    say: Callable[[str], None],
    **kw,
) -> tuple[Path, Path]:
    harvester = get(name)
    scope = Scope(languages=languages, areas=areas, subdomains=subdomains)
    return harvest(harvester, root, scope, limit=limit, run_id=run_id, say=say, **kw)
