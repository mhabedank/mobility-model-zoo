"""Labeler schemas of pilot-v3: one per pass, and the merged labeler output (feature 025, research R3).

The wire schemas that a labeler sees are the JSON files in `schemas/`, copies of the feature's
contracts. They carry no `title` or `description`, because any text a teacher reads must be inside
the owner-approved package (constitution 3.2.0, research R2). The Pydantic models parse answers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mobility_model_zoo.productdev.jtbd.freeze import sha256_text

SCHEMAS = Path(__file__).parent / "schemas"

KINDS = ("job", "pain", "gain")
ACTOR_TYPES = ("individual", "worker", "organization", "public_sector", "society")
EVIDENCE_TYPES = ("opinion", "anecdote", "routine", "observation", "measurement")
EVIDENCE_SCOPES = ("single", "multiple", "quantified")
JOB_KINDS = ("functional", "emotional", "social")
MODES = (
    "walk",
    "bicycle",
    "micromobility",
    "motorcycle",
    "car",
    "taxi_ridehailing",
    "bus",
    "tram_metro",
    "train",
    "coach",
    "public_transport",
    "truck_van",
    "air",
    "water",
    "other",
)
IMPROVE = (
    "time",
    "cost",
    "effort",
    "reliability",
    "safety",
    "comfort",
    "access",
    "information",
    "flexibility",
    "environment",
    "other",
)
RELATIONS = ("causes", "in_order_to", "before", "during")
DIMENSIONS = (
    "actor_type",
    "evidence_type",
    "evidence_scope",
    "job_kind",
    "mode",
    "improve",
    "states_solution",
    "executor_role",
    "situation",
)
RELATION_FIELDS = ("actor_pair", "means_end", "order")
RELATION_FIELD = {
    "causes": "actor_pair",
    "in_order_to": "means_end",
    "before": "order",
    "during": "order",
}

Kind = Literal["job", "pain", "gain"]
ActorType = Literal["individual", "worker", "organization", "public_sector", "society"]
EvidenceType = Literal["opinion", "anecdote", "routine", "observation", "measurement"]
EvidenceScope = Literal["single", "multiple", "quantified"]
JobKind = Literal["functional", "emotional", "social"]
Mode = Literal[
    "walk",
    "bicycle",
    "micromobility",
    "motorcycle",
    "car",
    "taxi_ridehailing",
    "bus",
    "tram_metro",
    "train",
    "coach",
    "public_transport",
    "truck_van",
    "air",
    "water",
    "other",
]
Improve = Literal[
    "time",
    "cost",
    "effort",
    "reliability",
    "safety",
    "comfort",
    "access",
    "information",
    "flexibility",
    "environment",
    "other",
]
Relation = Literal["causes", "in_order_to", "before", "during"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Pass1Item(_Strict):
    kind: Kind
    quote: str = Field(min_length=1)
    actor_type: ActorType
    evidence_type: EvidenceType
    evidence_scope: EvidenceScope


class Pass1Answer(_Strict):
    relevant: bool
    items: list[Pass1Item]


class Pass2Item(_Strict):
    index: int = Field(ge=0)
    job_kind: JobKind | None
    mode: list[Mode]
    improve: list[Improve]
    states_solution: bool
    executor_role: str | None
    situation: str | None


class Pass2Answer(_Strict):
    items: list[Pass2Item]


class Link(_Strict):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_: int = Field(alias="from", ge=0)
    to: int = Field(ge=0)
    relation: Relation


class Pass3Answer(_Strict):
    links: list[Link]


PASS_MODELS: dict[int, type[BaseModel]] = {1: Pass1Answer, 2: Pass2Answer, 3: Pass3Answer}


def wire_schema(pass_no: int) -> dict[str, Any]:
    """The JSON schema a labeler answers in pass `pass_no`, without `$schema` and `$id`."""
    schema = json.loads((SCHEMAS / f"labeler-pass{pass_no}.schema.json").read_text(encoding="utf-8"))
    schema.pop("$schema", None)
    schema.pop("$id", None)
    return schema


def labeler_schema_sha256(pass_no: int) -> str:
    return sha256_text(json.dumps(wire_schema(pass_no), sort_keys=True, ensure_ascii=False))


def _empty_attrs() -> dict[str, Any]:
    return {
        "job_kind": None,
        "mode": [],
        "improve": [],
        "states_solution": False,
        "executor_role": None,
        "situation": None,
    }


def merge(pass1: Pass1Answer, pass2: Pass2Answer | None, pass3: Pass3Answer | None) -> dict[str, Any]:
    """One labeler output per chunk: pass-1 items with their pass-2 attributes, and pass-3 links.

    Offsets, scores and the language are added by code afterwards (`v3.passes`). A missing pass leaves
    its fields empty, which the guideline counts as a correct answer.
    """
    items = [{**item.model_dump(), **_empty_attrs()} for item in pass1.items]
    for attrs in pass2.items if pass2 else []:
        if attrs.index >= len(items):
            raise ValueError(f"pass 2 names item {attrs.index}, but pass 1 has {len(items)} items")
        items[attrs.index].update(attrs.model_dump(exclude={"index"}))
    links = []
    for link in pass3.links if pass3 else []:
        if link.from_ >= len(items) or link.to >= len(items):
            raise ValueError(f"link {link.from_}->{link.to} names an item pass 1 does not have")
        links.append({"from": link.from_, "to": link.to, "relation": link.relation})
    return {"relevant": pass1.relevant, "items": items, "links": links}
