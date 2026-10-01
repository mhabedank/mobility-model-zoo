"""The zoo registry in the repository: topics, models, release records, results and examples.

Layout (specs/003-model-zoo-hf-release/data-model.md):

    zoo/topics.yaml
    zoo/models/<name>/model.yaml
    zoo/models/<name>/releases/<version>.yaml
    zoo/models/<name>/results/<version>/{quality,performance}.json
    zoo/models/<name>/examples/*.txt

Every file is validated against its JSON Schema when it is loaded.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from mobility_model_zoo.release.errors import GateFailed, UsageError

SCHEMAS = ("topics", "model", "release-record", "results")
VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
ORG = "mobility-model-zoo"
RESULT_KINDS = ("quality", "performance")


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps dates as strings, so records validate against `format: date`."""


_Loader.yaml_implicit_resolvers = {
    key: [r for r in resolvers if r[0] != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path) -> Any:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)


class _Dumper(yaml.SafeDumper):
    """SafeDumper that writes date strings unquoted (they are read back as strings by _Loader)."""


_Dumper.yaml_implicit_resolvers = _Loader.yaml_implicit_resolvers


def dump_yaml(data: Any) -> str:
    return yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100)


@cache
def schema(name: str) -> dict[str, Any]:
    text = resources.files("mobility_model_zoo.release").joinpath(f"schemas/{name}.schema.json")
    return json.loads(text.read_text(encoding="utf-8"))


def schema_errors(name: str, data: Any) -> list[str]:
    """All schema violations of `data`, as readable messages with the field path."""
    validator = jsonschema.Draft202012Validator(
        schema(name), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{where}: {err.message}")
    return errors


def parse_version(version: str) -> tuple[int, int, int]:
    m = VERSION.match(version)
    if not m:
        raise UsageError(f"not a semantic version MAJOR.MINOR.PATCH: {version!r}")
    return int(m[1]), int(m[2]), int(m[3])


def split_tag(tag: str) -> tuple[str, str]:
    """`<model>/v<version>` -> (model, version)."""
    model, sep, rest = tag.partition("/v")
    if not sep or not model or "/" in model:
        raise UsageError(f"release tags look like <model>/v<version>, got {tag!r}")
    parse_version(rest)
    return model, rest


@dataclass
class Registry:
    """Read and write access to `zoo/` below `root` (the repository root)."""

    root: Path

    @property
    def zoo(self) -> Path:
        return self.root / "zoo"

    # ---- paths ---------------------------------------------------------------------------------
    def model_dir(self, name: str) -> Path:
        return self.zoo / "models" / name

    def record_path(self, name: str, version: str) -> Path:
        return self.model_dir(name) / "releases" / f"{version}.yaml"

    def results_path(self, name: str, version: str, kind: str) -> Path:
        return self.model_dir(name) / "results" / version / f"{kind}.json"

    # ---- topics --------------------------------------------------------------------------------
    def topics_raw(self) -> dict[str, Any]:
        path = self.zoo / "topics.yaml"
        if not path.exists():
            raise UsageError(f"missing {path}")
        return load_yaml(path)

    def topics(self) -> list[dict[str, Any]]:
        data = self.topics_raw()
        errors = schema_errors("topics", data)
        if errors:
            raise GateFailed([f"zoo/topics.yaml {e}" for e in errors])
        return data["topics"]

    def topic(self, topic_id: str) -> dict[str, Any] | None:
        return next((t for t in self.topics() if t["id"] == topic_id), None)

    def write_topics(self, topics: list[dict[str, Any]]) -> None:
        (self.zoo / "topics.yaml").write_text(dump_yaml({"topics": topics}), encoding="utf-8")

    # ---- models --------------------------------------------------------------------------------
    def model_names(self) -> list[str]:
        base = self.zoo / "models"
        if not base.exists():
            return []
        return sorted(p.name for p in base.iterdir() if (p / "model.yaml").exists())

    def model_raw(self, name: str) -> dict[str, Any]:
        path = self.model_dir(name) / "model.yaml"
        if not path.exists():
            raise UsageError(f"unknown model {name!r} (no {path.relative_to(self.root)})")
        return load_yaml(path) or {}

    def model(self, name: str) -> dict[str, Any]:
        data = self.model_raw(name)
        errors = schema_errors("model", data)
        if errors:
            raise GateFailed([f"model.yaml {e}" for e in errors])
        return data

    # ---- release records -----------------------------------------------------------------------
    def versions(self, name: str) -> list[str]:
        """Every version that has a release record, sorted by semantic version."""
        base = self.model_dir(name) / "releases"
        if not base.exists():
            return []
        found = [p.stem for p in base.glob("*.yaml") if VERSION.match(p.stem)]
        return sorted(found, key=parse_version)

    def record_raw(self, name: str, version: str) -> dict[str, Any]:
        path = self.record_path(name, version)
        if not path.exists():
            raise UsageError(f"no release record {path.relative_to(self.root)}")
        return load_yaml(path) or {}

    def record(self, name: str, version: str) -> dict[str, Any]:
        data = self.record_raw(name, version)
        errors = schema_errors("release-record", data)
        if errors:
            raise GateFailed([f"releases/{version}.yaml {e}" for e in errors])
        return data

    def write_record(self, name: str, version: str, data: dict[str, Any]) -> None:
        path = self.record_path(name, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_yaml(data), encoding="utf-8")

    def published_versions(self, name: str) -> list[str]:
        out = []
        for version in self.versions(name):
            if (self.record_raw(name, version) or {}).get("published"):
                out.append(version)
        return out

    # ---- results and examples ------------------------------------------------------------------
    def results(self, name: str, version: str, kind: str) -> dict[str, Any]:
        path = self.results_path(name, version, kind)
        if not path.exists():
            raise UsageError(f"missing {path.relative_to(self.root)}")
        return json.loads(path.read_text(encoding="utf-8"))

    def examples(self, name: str) -> list[tuple[str, str]]:
        base = self.model_dir(name) / "examples"
        if not base.exists():
            return []
        return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(base.glob("*.txt"))]
