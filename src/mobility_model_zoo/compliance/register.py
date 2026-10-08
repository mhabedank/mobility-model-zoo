"""The compliance register: YAML records in git, validated against JSON Schemas (data-model.md).

Shared records live in `compliance/`, topic records in `topics/<topic>/compliance/`, release evidence
next to the release records as `zoo/models/<name>/releases/<version>.compliance.yaml`.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from mobility_model_zoo.compliance.findings import Finding, parse_date

SCHEMA_DIR = Path(__file__).parent / "schemas"

# file name in compliance/ or topics/<t>/compliance/ -> (schema stem, key that holds the records)
SHARED = {
    "controller.yaml": ("controller", None),
    "providers.yaml": ("providers", "routes"),
    "recipients.yaml": ("recipients", "recipients"),
    "decisions.yaml": ("decisions", "decisions"),
    "waivers.yaml": ("waivers", "waivers"),
    "requests.yaml": ("requests", "requests"),
    "suppression.yaml": ("suppression", "entries"),
    "legal-watch.yaml": ("legal-watch", "items"),
}
TOPIC = {
    "source-classes.yaml": ("source-classes", "classes"),
    "sources.yaml": ("sources", "sources"),
    "datasets.yaml": ("datasets", "datasets"),
}


@cache
def schema(stem: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / f"{stem}.schema.json").read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass
class Register:
    root: Path
    today: dt.date = field(default_factory=dt.date.today)
    files: dict[str, Any] = field(default_factory=dict)  # repo-relative path -> parsed content
    stems: dict[str, str] = field(default_factory=dict)  # repo-relative path -> schema stem

    @classmethod
    def load(cls, root: Path, today: dt.date | None = None) -> Register:
        reg = cls(root=root, today=today or dt.date.today())
        shared = root / "compliance"
        for name, (stem, _) in SHARED.items():
            reg._add(shared / name, stem)
        for topic_dir in sorted((root / "topics").glob("*/compliance")):
            for name, (stem, _) in TOPIC.items():
                reg._add(topic_dir / name, stem)
        for path in sorted((root / "zoo" / "models").glob("*/releases/*.compliance.yaml")):
            reg._add(path, "release-compliance")
        return reg

    def _add(self, path: Path, stem: str) -> None:
        if path.exists():
            rel = path.relative_to(self.root).as_posix()
            self.files[rel] = _load_yaml(path)
            self.stems[rel] = stem

    # ---- validation (check C-M1) -------------------------------------------------------------

    def schema_findings(self) -> list[Finding]:
        findings: list[Finding] = []
        if "compliance/controller.yaml" not in self.files:
            findings.append(Finding("C-M1", "meta", "compliance/controller.yaml", "-", "missing file"))
        for rel, data in self.files.items():
            validator = Draft202012Validator(schema(self.stems[rel]))
            for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
                where = "/".join(str(p) for p in err.absolute_path) or "-"
                findings.append(Finding("C-M1", "meta", rel, where, err.message))
        return findings

    # ---- lookups -----------------------------------------------------------------------------

    def _records(self, stem: str) -> list[tuple[str, dict[str, Any]]]:
        key = {**SHARED, **TOPIC}.get(f"{stem}.yaml", (stem, None))[1]
        out = []
        for rel, data in self.files.items():
            if self.stems[rel] != stem or not isinstance(data, dict):
                continue
            items = data.get(key, []) if key else [data]
            out += [(rel, item) for item in items or [] if isinstance(item, dict)]
        return out

    def records(self, stem: str) -> list[dict[str, Any]]:
        return [r for _, r in self._records(stem)]

    def located(self, stem: str) -> list[tuple[str, dict[str, Any]]]:
        return self._records(stem)

    def by_id(self, stem: str, record_id: str) -> dict[str, Any] | None:
        return next((r for r in self.records(stem) if r.get("id") == record_id), None)

    def controller(self) -> dict[str, Any]:
        return self.files.get("compliance/controller.yaml") or {}

    def source(self, source_id: str) -> dict[str, Any] | None:
        return self.by_id("sources", source_id) or self.by_id("datasets", source_id)

    def sources_for(self, model: str, version: str) -> list[dict[str, Any]]:
        tag = f"{model}@{version}"
        return [
            r for r in self.records("sources") + self.records("datasets") if tag in r.get("used_by", [])
        ]

    def route(self, route_id: str) -> dict[str, Any] | None:
        return self.by_id("providers", route_id)

    def decision(self, decision_id: str) -> dict[str, Any] | None:
        return self.by_id("decisions", decision_id)

    def release(self, model: str, version: str) -> dict[str, Any] | None:
        return self.files.get(f"zoo/models/{model}/releases/{version}.compliance.yaml")

    def waiver_for(self, check_id: str, record_id: str) -> dict[str, Any] | None:
        """An unexpired waiver for this check and record (scope '*' covers every record)."""
        for w in self.records("waivers"):
            if w.get("check") != check_id or w.get("scope") not in (record_id, "*"):
                continue
            expires = parse_date(w.get("expires_at"))
            if expires and expires >= self.today:
                return w
        return None

    def waiver_ok(self, check_id: str, record_id: str) -> bool:
        return self.waiver_for(check_id, record_id) is not None

    def lists(self, name: str) -> Any:
        path = self.root / "compliance" / "lists" / f"{name}.yaml"
        return _load_yaml(path) if path.exists() else None
