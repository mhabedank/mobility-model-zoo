"""Version hashes of the data overview (data-model.md "Hashes").

The benchmark hash is the formula the zoo already uses for `based_on.manifest_sha256` and run
records (`security/can_ids/evaluate.py`), so the overview and the runs name the same version.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")).hexdigest()


def manifest_hash(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def dataset_hash(source_json: dict[str, Any]) -> str:
    """sha256 over sorted `name:sha256` lines of SOURCE.json files (`name:checksum` for files read
    member by member out of a remote archive, which have no sha256 of their own)."""
    lines = []
    for f in source_json.get("files") or []:
        digest = f.get("sha256") or f.get("checksum") or ""
        lines.append(f"{f.get('name', '')}:{digest}")
    return sha256_text("\n".join(sorted(lines)))


def canonical_yaml_hash(path: Path) -> str:
    """Same rule as `productdev.jtbd.freeze.sha256_canonical` for YAML: sorted keys, LF endings."""
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return sha256_text(json.dumps(data, sort_keys=True, default=str))


def training_set_hash(frozen: dict[str, Any]) -> str | None:
    return frozen.get("sha256")
