"""Pydantic models: the single source of truth for every record shape.

`wire_schema()` exports the extraction-output JSON Schema that is sent to every backend and that
must equal contracts/extraction-output.schema.json (checked in tests/unit/test_schema.py).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Kind = Literal["job", "pain", "gain"]
ActorType = Literal["individual", "worker", "organization", "public_sector", "society"]
EvidenceType = Literal["opinion", "anecdote", "routine", "observation", "measurement"]
EvidenceScope = Literal["single", "multiple", "quantified"]

EVIDENCE_ORDER: tuple[str, ...] = ("opinion", "anecdote", "routine", "observation", "measurement")
KINDS: tuple[str, ...] = ("job", "pain", "gain")
ACTOR_TYPES: tuple[str, ...] = ("individual", "worker", "organization", "public_sector", "society")
EVIDENCE_SCOPES: tuple[str, ...] = ("single", "multiple", "quantified")
ATTRIBUTE_DIMENSIONS: tuple[str, ...] = ("kind", "actor_type", "evidence_type", "evidence_scope")

SourceType = Literal["paper", "reddit", "forum_review", "transcript"]
SubArea = Literal[
    "public_transport_rural",
    "logistics_delivery",
    "emobility_charging",
    "car_ownership_use",
    "sharing_platforms",
    "none",
]
Region = Literal["DACH", "EU_other", "non_EU"]
Language = Literal["de", "en"]
RelevanceIntent = Literal["relevant", "irrelevant", "near_miss"]
PermittedUses = Literal["benchmark_only", "training_allowed"]
Split = Literal["main", "holdout", "train"]
Role = Literal["reference", "teacher_candidate", "baseline"]
BackendName = Literal["claude_cli", "openrouter", "ollama", "openai_compat", "mock"]


def evidence_rank(value: str) -> int:
    """Ordinal position of an evidence type (opinion=0 ... measurement=4)."""
    return EVIDENCE_ORDER.index(value)


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Kind
    quote: str = Field(
        min_length=1,
        description="Verbatim substring of the chunk text, in the source language.",
    )
    actor: str = Field(
        min_length=1,
        description="Who has the job, pain or gain, as named or described in the text.",
    )
    actor_type: ActorType
    statement: str = Field(min_length=1, description="Normalized statement in English.")
    evidence_type: EvidenceType = Field(
        description="Ordinal, lowest to highest. Take the lower grade when uncertain."
    )
    evidence_scope: EvidenceScope


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relevant: bool = Field(description="Whether the chunk is relevant to the problem domain.")
    items: list[Item]


def wire_schema() -> dict:
    """Strict JSON Schema for structured output, derived from ExtractionOutput."""
    raw = ExtractionOutput.model_json_schema()
    return _clean(raw)


def _clean(node):
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "title":
                continue
            out[key] = _clean(value)
        if "enum" in out and out.get("type") == "string":
            out.pop("type")
        return out
    if isinstance(node, list):
        return [_clean(v) for v in node]
    return node


class Redaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patterns_version: str
    manual_review_at: datetime | None = None
    check_passed: bool = False


class SourceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(pattern=r"^snap-[0-9a-f]{12}$")
    origin_url: str
    source_type: SourceType
    retrieved_at: datetime
    raw_path: str
    text_path: str | None = None
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    license: str
    legal_basis: str
    access_terms_checked: str
    permitted_uses: PermittedUses
    retention_until: date
    supersedes: str | None = None
    update_reason: str | None = None

    @model_validator(mode="after")
    def _rules(self) -> SourceSnapshot:
        if self.source_type == "reddit" and self.permitted_uses != "benchmark_only":
            raise ValueError("Reddit snapshots must be permitted_uses=benchmark_only")
        if self.supersedes and not (self.update_reason and self.update_reason.strip()):
            raise ValueError("update_reason is required when supersedes is set")
        return self


class ChunkRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(pattern=r"^ch-[0-9]{3,}$")
    snapshot_id: str = Field(pattern=r"^snap-[0-9a-f]{12}$")
    ranges: list[tuple[int, int]] = Field(min_length=1)
    text: str = Field(min_length=1)
    token_count: int | None = None
    split: Split = "main"
    sub_area: SubArea
    source_type: SourceType
    region: Region
    country: str = Field(pattern=r"^[A-Z]{2}$")
    language: Language
    date: date
    license: str
    relevance_intent: RelevanceIntent
    redaction: Redaction


class RunSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    temperature: float | Literal["not_settable"]
    structured_output: Literal["json_schema_strict", "json_schema_grammar", "post_validation"]
    max_output_tokens: int | None = None
    seed: int | None = None
    max_retries: int = 2


class ExcludedChunk(BaseModel):
    chunk_id: str
    reason: str


class LabelRunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    role: Role
    backend: BackendName
    model_id: str
    model_version: str
    family: str
    host: str
    quantization: str | None = None
    settings: RunSettings
    guideline_sha256: str
    schema_sha256: str
    criteria_sha256: str
    prompt_sha256: str | None = None
    split: Split
    started_at: datetime
    finished_at: datetime | None = None
    cost_eur: float = 0.0
    excluded_chunks: list[ExcludedChunk] = Field(default_factory=list)
    license_basis: str | None = None
    deviations: list[str] = Field(default_factory=list)
    status: Literal["running", "complete", "invalid_version_change"] = "running"

    @model_validator(mode="after")
    def _rules(self) -> LabelRunManifest:
        if self.role == "teacher_candidate" and not self.license_basis:
            raise ValueError("teacher_candidate runs require license_basis")
        if self.backend == "ollama" and not self.quantization:
            raise ValueError("ollama runs require quantization")
        return self


class DecisionThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relevance_kappa: float
    evidence_type_weighted_kappa: float
    kind_kappa: float
    actor_type_kappa: float
    evidence_scope_kappa: float
    item_matching_f1: float


class FinetuningRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_quality_ratio: float
    min_throughput_ratio: float
    quality_reference: Literal["frontier_vs_frontier_composite"]
    throughput_reference: Literal["frontier_reference_chunks_per_min"]


class DecisionCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    thresholds: DecisionThresholds
    rethink_below: dict[str, float]
    revise_band: dict[str, tuple[float, float]]
    max_reruns: int
    rerun_decision_split: Literal["holdout"] = "holdout"
    finetuning_optional: FinetuningRule
    underpowered_min_units: int
    rationale: str | None = None
