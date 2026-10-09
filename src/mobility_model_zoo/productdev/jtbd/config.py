"""Configuration loading.

A config file (e.g. configs/productdev/jtbd/pilot-v1.yaml) names every other file. Paths in it
are resolved against `root`, which is itself relative to the config file's directory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from mobility_model_zoo.productdev.jtbd.errors import UsageError
from mobility_model_zoo.productdev.jtbd.schema import DecisionCriteria, TeacherScoring

DEFAULT_CONFIG = Path("configs/productdev/jtbd/pilot-v1.yaml")
# Each config spends from one named budget (its own budget file); the ledger is shared and
# its rows carry the budget name. Rows without a name belong to the pilot budget.
DEFAULT_BUDGET = "pilot-v1"
TOP_LEVEL_KEYS = {"root", "benchmark_version", "test_fixture", "paths", "pilot", "budget_name",
                  "span_train", "cluster"}
# Defaults of a training dataset config (feature 004, data-model.md "Training dataset").
SPAN_TRAIN_DEFAULTS: dict[str, Any] = {
    "redaction": {"version": "redact-v2", "review": "full"},
    "composition_targets": {},
    "validation": {"fraction_of_snapshots": 0.10, "seed": 0},
    "min_usable_chunks": 600,
    "retention": {},
}
SPAN_TRAIN_KEYS = {"dataset", "exclude_benchmark", *SPAN_TRAIN_DEFAULTS}
# Benchmark config of the jtbd-cluster task (feature 009, data-model.md "Benchmark").
CLUSTER_KEYS = {"pool", "split_by", "dev_fraction", "seed", "pairs", "sets", "reference_models",
                "batch_size", "guideline", "examples", "criteria", "retention"}


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
    budget_name: str = DEFAULT_BUDGET
    span_train: dict[str, Any] | None = None
    cluster: dict[str, Any] | None = None

    # ---- derived paths -------------------------------------------------------------------------
    @property
    def data_dir(self) -> Path:
        return self.paths["data"]

    @property
    def snapshots_dir(self) -> Path:
        """Snapshots are shared across configs (crawl once); overridable via paths.snapshots."""
        return self.paths.get("snapshots", self.data_dir / "snapshots")

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
        # One cash budget across pilot and spikes: a spike config points this at the pilot ledger.
        return self.paths.get("ledger", self.data_dir / "budget" / "ledger.jsonl")

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

    def teacher_scoring(self) -> TeacherScoring:
        return TeacherScoring.model_validate(self.load_yaml("teacher_scoring"))

    def budget(self) -> dict[str, Any]:
        return self.load_yaml("budget")

    @property
    def redaction_review(self) -> str:
        """How chunks are reviewed after pattern redaction: `full` (every chunk by hand),
        `sampled` (a sample by hand, training datasets, research R4) or `model` (every chunk by a
        local model, `jtbd corpus pii-review`; decision of 2026-10-06)."""
        if self.span_train is not None:
            return self.span_train.get("redaction", {}).get("review", "full")
        return self.pilot.get("redaction_review", "full")

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
    unknown = set(raw) - TOP_LEVEL_KEYS
    if unknown:
        raise UsageError(f"config {path} has unknown keys: {sorted(unknown)}")
    base = (path.parent / raw.get("root", ".")).resolve()
    paths = {key: (base / value).resolve() for key, value in (raw.get("paths") or {}).items()}
    required = {"guideline", "examples", "domain", "models", "criteria", "teacher_scoring",
                "budget", "data", "benchmarks", "reports"}
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
        budget_name=raw.get("budget_name") or DEFAULT_BUDGET,
        span_train=_span_train(path, raw.get("span_train")),
        cluster=_cluster(path, raw.get("cluster")),
    )


def _span_train(path: Path, raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    unknown = set(raw) - SPAN_TRAIN_KEYS
    if unknown:
        raise UsageError(f"config {path} has unknown span_train keys: {sorted(unknown)}")
    merged = {**SPAN_TRAIN_DEFAULTS, **raw}
    if merged["redaction"].get("review") not in ("full", "sampled", "model"):
        raise UsageError("span_train.redaction.review must be `full`, `sampled` or `model`")
    return merged


def _cluster(path: Path, raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    unknown = set(raw) - CLUSTER_KEYS
    if unknown:
        raise UsageError(f"config {path} has unknown cluster keys: {sorted(unknown)}")
    return raw
