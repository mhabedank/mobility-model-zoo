"""Configuration loading.

A pilot config file (e.g. configs/pilot-v1.yaml) names every other file. Paths in it are resolved
against `root`, which is itself relative to the config file's directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from jtbd_pilot.errors import UsageError
from jtbd_pilot.schema import DecisionCriteria

DEFAULT_CONFIG = Path("configs/pilot-v1.yaml")


@dataclass
class ModelEntry:
    model_id: str
    family: str
    backend: str
    host: str
    role: str
    api_model: str | None = None
    benchmark_labeler: bool = False
    quantization: str | None = None
    license_basis: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Settings:
    config_path: Path
    base: Path
    benchmark_version: str
    test_fixture: bool
    paths: dict[str, Path]
    pilot: dict[str, Any]

    # ---- derived paths -------------------------------------------------------------------------
    @property
    def data_dir(self) -> Path:
        return self.paths["data"]

    @property
    def snapshots_dir(self) -> Path:
        return self.data_dir / "snapshots"

    @property
    def chunks_dir(self) -> Path:
        return self.data_dir / "chunks"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def active_version(self) -> str:
        """Benchmark version named in benchmarks/current, else the configured one."""
        pointer = self.paths["benchmarks"] / "current"
        if pointer.exists():
            return pointer.read_text(encoding="utf-8").strip()
        return self.benchmark_version

    @property
    def analysis_dir(self) -> Path:
        return self.data_dir / "analysis" / self.active_version

    @property
    def ledger_path(self) -> Path:
        return self.data_dir / "budget" / "ledger.jsonl"

    @property
    def benchmarks_dir(self) -> Path:
        return self.paths["benchmarks"]

    @property
    def reports_dir(self) -> Path:
        return self.paths["reports"]

    # ---- loaded config files -------------------------------------------------------------------
    def load_yaml(self, key: str) -> Any:
        path = self.paths[key]
        if not path.exists():
            raise UsageError(f"config file missing: {path}")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def criteria(self) -> DecisionCriteria:
        return DecisionCriteria.model_validate(self.load_yaml("criteria"))

    def budget(self) -> dict[str, Any]:
        return self.load_yaml("budget")

    def domain(self) -> dict[str, Any]:
        return self.load_yaml("domain")

    def models(self) -> dict[str, ModelEntry]:
        raw = self.load_yaml("models") or {}
        entries: dict[str, ModelEntry] = {}
        for item in raw.get("models", []):
            fields = ModelEntry.__dataclass_fields__
            known = {k: item[k] for k in fields if k in item and k != "extra"}
            extra = {k: v for k, v in item.items() if k not in ModelEntry.__dataclass_fields__}
            entry = ModelEntry(**known, extra=extra)
            if not entry.api_model:
                entry.api_model = entry.model_id if entry.backend == "mock" else None
            entries[entry.model_id] = entry
        return entries

    def model(self, model_id: str) -> ModelEntry:
        models = self.models()
        if model_id not in models:
            raise UsageError(f"model {model_id!r} is not listed in {self.paths['models']}")
        return models[model_id]


def load_settings(config_path: Path | str | None = None) -> Settings:
    load_dotenv(override=False)
    path = Path(config_path or os.environ.get("PILOT_CONFIG", DEFAULT_CONFIG)).resolve()
    if not path.exists():
        raise UsageError(f"config not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    base = (path.parent / raw.get("root", ".")).resolve()
    paths = {key: (base / value).resolve() for key, value in (raw.get("paths") or {}).items()}
    required = {"guideline", "examples", "domain", "models", "criteria", "budget", "data",
                "benchmarks", "reports"}
    missing = required - paths.keys()
    if missing:
        raise UsageError(f"config {path} is missing paths: {sorted(missing)}")
    return Settings(
        config_path=path,
        base=base,
        benchmark_version=raw.get("benchmark_version", "pilot-v1"),
        test_fixture=bool(raw.get("test_fixture", False)),
        paths=paths,
        pilot=raw.get("pilot") or {},
    )
