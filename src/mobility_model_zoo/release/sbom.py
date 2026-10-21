"""CycloneDX bill of materials of a release's device code (compliance check C-G4).

Shared by the release exporters: picket-forest (security/can_ids/release_export.py) and the int8
models (edge/int8/release_export.py, feature 021 research R10). The SBOM lists every shipped C
source and header with its SHA-256, plus the libraries that generated or trained the code.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

SBOM_FILE = "sbom.cdx.json"


def library(name: str, version: str, description: str) -> dict[str, Any]:
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name}@{version}",
        "description": description,
    }


def file_components(out_dir: Path) -> list[dict[str, Any]]:
    """The C sources and headers in `out_dir` (recursively), sorted by path, with their SHA-256."""
    files = sorted(p for p in Path(out_dir).rglob("*") if p.is_file() and p.name != SBOM_FILE)
    return [
        {
            "type": "file",
            "name": p.relative_to(out_dir).as_posix(),
            "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}],
        }
        for p in files
        if p.suffix in (".c", ".h")
    ]


def sbom(
    out_dir: Path,
    *,
    name: str,
    description: str,
    libraries: list[dict[str, Any]],
    tool: str,
) -> dict[str, Any]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {"type": "firmware", "name": name, "description": description},
            "tools": [{"name": tool}],
        },
        "components": file_components(out_dir) + libraries,
    }
