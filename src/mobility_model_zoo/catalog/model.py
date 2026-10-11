"""Loading and writing catalog entries, vocabularies and the index version (data-model.md, R1, R10).

The entries live in the private repository `mobility-model-zoo-catalog`, one YAML file per entry
under `entries/<origin_area lower>/<id>.yaml`. This module refuses to write entries anywhere inside
the public zoo repository.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.datasets import UsageRefused
from mobility_model_zoo.release.errors import CredentialError

PACKAGE = Path(__file__).resolve().parent
SCHEMA_DIR = PACKAGE / "schemas"
VOCAB_DIR = PACKAGE / "vocab"
DATA_DIR = PACKAGE / "data"
ENV = "MMZ_CATALOG"
DEFAULT = Path("../mobility-model-zoo-catalog")

# Key order of a written entry: the order of the data-model table.
KEY_ORDER = [
    "id",
    "schema_version",
    "level",
    "parent",
    "title",
    "description",
    "languages",
    "origin_area",
    "publisher",
    "landing_url",
    "resource_type",
    "topics",
    "subdomains",
    "licence",
    "platform_terms",
    "signals",
    "usage",
    "personal_data",
    "access",
    "content",
    "quality",
    "relations",
    "identifiers",
    "provenance",
    "status",
    "checks",
    "fetched",
]


def today() -> str:
    return dt.date.today().isoformat()


@cache
def schema(stem: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / f"{stem}.schema.json").read_text(encoding="utf-8"))


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


# ---- zoo repository and package data -----------------------------------------------------------


def zoo_repo_root() -> Path | None:
    """The public repository this package was installed from (editable install), if any."""
    root = PACKAGE.parents[2]
    return root if (root / "zoo" / "topics.yaml").is_file() else None


def _is_zoo_checkout(path: Path) -> bool:
    return (path / "zoo" / "topics.yaml").is_file() and (path / "src" / "mobility_model_zoo").is_dir()


def inside_zoo_repo(path: Path) -> bool:
    """True for any path in a checkout of the public zoo repository (including worktrees in it)."""
    path = path.resolve()
    return any(_is_zoo_checkout(p) for p in (path, *path.parents))


def compliance_list(name: str, zoo_root: Path | None = None) -> Any:
    """A file of compliance/lists: the zoo checkout's copy if given, else the package data (wheel),
    else the repository this package runs from (editable install). None if it exists nowhere."""
    candidates = []
    if zoo_root is not None:
        candidates.append(zoo_root / "compliance" / "lists" / f"{name}.yaml")
    candidates.append(DATA_DIR / "lists" / f"{name}.yaml")
    repo = zoo_repo_root()
    if repo is not None:
        candidates.append(repo / "compliance" / "lists" / f"{name}.yaml")
    for path in candidates:
        if path.is_file():
            return read_yaml(path)
    return None


def licence_allowlist(zoo_root: Path | None = None) -> list[dict[str, Any]]:
    data = compliance_list("licence-allowlist", zoo_root)
    if data is None:
        raise CredentialError("licence allow-list not found (package data missing; pass --zoo-root)")
    return data["licences"]


# ---- vocabularies --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Vocab:
    languages: dict[str, str]
    targets: list[str]
    countries: dict[str, str]
    regions: dict[str, str]
    kinds: dict[str, str]
    modalities: dict[str, dict[str, Any]]
    subdomains: dict[str, str]
    frequencies: dict[str, str]
    topics: list[str]
    version: int

    @property
    def areas(self) -> set[str]:
        return set(self.countries) | set(self.regions)

    def genres(self, modality: str) -> list[str]:
        return list((self.modalities.get(modality) or {}).get("genres", []))


@cache
def vocab() -> Vocab:
    files = {p.stem: read_yaml(p) for p in sorted(VOCAB_DIR.glob("*.yaml"))}
    return Vocab(
        languages={str(k): v for k, v in files["languages"]["codes"].items()},
        targets=list(files["languages"]["targets"]),
        countries={str(k): v for k, v in files["areas"]["countries"].items()},
        regions={str(k): v for k, v in files["areas"]["regions"].items()},
        kinds=files["source-kinds"]["kinds"],
        modalities=files["resource-types"]["modalities"],
        subdomains=files["subdomains"]["subdomains"],
        frequencies=files["frequencies"]["frequencies"],
        topics=list(files["topics"]["topics"]),
        version=max(int(f.get("version", 1)) for f in files.values()),
    )


# ---- catalog -------------------------------------------------------------------------------------


def resolve(path: Path | str | None) -> Path:
    """Catalog root: option, then $MMZ_CATALOG, then ../mobility-model-zoo-catalog."""
    for candidate in (path, os.environ.get(ENV), DEFAULT):
        if candidate:
            p = Path(candidate).expanduser()
            if (p / "catalog.yaml").is_file():
                return p.resolve()
            if path is not None and candidate == path:
                break
    raise CredentialError(
        f"catalog repository not found: {path or os.environ.get(ENV) or DEFAULT} "
        f"(no catalog.yaml; set --catalog or ${ENV}, or run `zoo catalog init`)"
    )


def entry_path(root: Path, entry: dict[str, Any]) -> Path:
    return root / "entries" / str(entry["origin_area"]).lower() / f"{entry['id']}.yaml"


def ordered(entry: dict[str, Any]) -> dict[str, Any]:
    out = {k: entry[k] for k in KEY_ORDER if k in entry}
    out.update({k: v for k, v in entry.items() if k not in out})
    return out


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


@dataclass
class Catalog:
    root: Path
    config: dict[str, Any]
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)
    paths: dict[str, Path] = field(default_factory=dict)
    load_errors: list[tuple[str, str]] = field(default_factory=list)  # (file, reason)

    @property
    def commit(self) -> str | None:
        """HEAD of the catalog repository; None when the catalog root is not a repository root."""
        try:
            top = subprocess.run(
                ["git", "-C", str(self.root), "rev-parse", "--show-toplevel", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
        except (OSError, subprocess.CalledProcessError):
            return None
        if len(top) != 2 or Path(top[0]).resolve() != self.root.resolve():
            return None
        return top[1]

    @property
    def sha256(self) -> str:
        h = hashlib.sha256()
        for entry_id in sorted(self.entries):
            h.update(canonical_json(self.entries[entry_id]).encode("utf-8"))
            h.update(b"\n")
        return h.hexdigest()

    def version(self) -> dict[str, Any]:
        return {
            "catalog_commit": self.commit,
            "catalog_sha256": self.sha256,
            "vocab_version": vocab().version,
        }

    def write_entry(self, entry: dict[str, Any]) -> Path:
        if inside_zoo_repo(self.root):
            raise UsageRefused(
                f"{self.root}: catalog entries must not be written into the public zoo repository (R1)"
            )
        path = entry_path(self.root, entry)
        old = self.paths.get(entry["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_yaml(ordered(entry)), encoding="utf-8")
        if old is not None and old != path and old.exists():
            old.unlink()
        self.entries[entry["id"]] = entry
        self.paths[entry["id"]] = path
        return path


def load(path: Path | str | None = None) -> Catalog:
    root = resolve(path)
    cat = Catalog(root=root, config=read_yaml(root / "catalog.yaml") or {})
    for file in sorted((root / "entries").glob("**/*.yaml")):
        rel = file.relative_to(root).as_posix()
        try:
            data = read_yaml(file)
        except yaml.YAMLError as e:
            cat.load_errors.append((rel, f"invalid YAML: {e}"))
            continue
        if not isinstance(data, dict) or "id" not in data:
            cat.load_errors.append((rel, "not an entry (no id)"))
            continue
        if data["id"] in cat.entries:
            cat.load_errors.append((rel, f"duplicate id {data['id']} (also {cat.paths[data['id']]})"))
            continue
        cat.entries[data["id"]] = data
        cat.paths[data["id"]] = file
    return cat
