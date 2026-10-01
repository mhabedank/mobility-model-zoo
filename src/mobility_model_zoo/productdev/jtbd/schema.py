"""Pydantic models: the single source of truth for every record shape.

`wire_schema()` exports the extraction-output JSON Schema that is sent to every backend and that
must equal contracts/extraction-output.schema.json (checked in tests/unit/test_schema.py).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

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
BackendName = Literal["claude_cli", "openrouter", "ollama", "openai_compat", "ensemble", "mock"]


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
    derived_from: list[str] | None = Field(default=None, min_length=2)

    @model_validator(mode="after")
    def _rules(self) -> LabelRunManifest:
        if self.role == "teacher_candidate" and not self.license_basis:
            raise ValueError("teacher_candidate runs require license_basis")
        if self.backend == "ollama" and not self.quantization:
            raise ValueError("ollama runs require quantization")
        if self.backend == "ensemble":
            if not self.derived_from:
                raise ValueError("ensemble runs require derived_from (FR-019b)")
            if self.role != "teacher_candidate":
                raise ValueError("ensemble runs must have role teacher_candidate")
        return self

    @model_serializer(mode="wrap")
    def _omit_derived_from(self, handler):
        data = handler(self)
        if data.get("derived_from") is None:
            data.pop("derived_from", None)  # the contract allows only an array
        return data


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


class TeacherFitness(BaseModel):
    """FR-031a: when a teacher candidate is fit to generate training data."""

    model_config = ConfigDict(extra="forbid")

    min_quality_ratio: float = Field(ge=0)
    min_schema_valid: float = Field(ge=0, le=1)
    tie_margin: float = Field(ge=0)
    score_view: Literal["repaired"]


class QuoteRepair(BaseModel):
    """FR-026a: repair of near-miss teacher quotes, for the teacher scoring view only."""

    model_config = ConfigDict(extra="forbid")

    min_score: float = Field(ge=0, le=100)
    min_length_ratio: float = Field(gt=0)
    max_length_ratio: float = Field(gt=0)


class TeacherEnsemble(BaseModel):
    """FR-019b: offline ensemble of the single teacher candidates.

    There is no configurable order: members are processed, and ties broken, in alphabetical order
    of their model IDs, so no spike measurement can enter the rule.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str
    members: list[str] = Field(min_length=2)
    min_votes: int = Field(ge=1)

    @model_validator(mode="after")
    def _rules(self) -> TeacherEnsemble:
        if len(set(self.members)) != len(self.members):
            raise ValueError("teacher_ensemble.members must be unique")
        if self.min_votes > len(self.members):
            raise ValueError("teacher_ensemble.min_votes exceeds the number of members")
        return self


class TeacherScoring(BaseModel):
    """Teacher-scoring configuration (FR-019b, FR-026a), frozen with the decision criteria."""

    model_config = ConfigDict(extra="forbid")

    version: str
    quote_repair: QuoteRepair
    teacher_ensemble: TeacherEnsemble
    rationale: str | None = None


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
    teacher_fitness: TeacherFitness
    rationale: str | None = None
