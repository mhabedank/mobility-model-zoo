"""Frozen prompts and wire schemas for reference labeling of pairs and sets (task T028, R11).

The system prompt is the cluster guideline followed by its examples; pair batches and sets go in
the user message as JSON. Only quotes, kinds and ids are sent, never the text around a quote.
`prompt_sha256` and `wire_schema_sha256` are part of the benchmark manifest.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import yaml

from mobility_model_zoo.productdev.jtbd.config import Settings

PAIR_LABELS = ("same", "a_more_specific", "b_more_specific", "different")

PAIR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["pairs"],
    "properties": {"pairs": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["pair_id", "label"],
        "properties": {"pair_id": {"type": "string"}, "label": {"enum": list(PAIR_LABELS)}}}}},
}

SET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["clusters", "coarse"],
    "properties": {
        "clusters": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["cluster_id", "members"],
            "properties": {"cluster_id": {"type": "string"},
                           "members": {"type": "array", "items": {"type": "string"}}}}},
        "coarse": {"anyOf": [{"type": "null"}, {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["group_id", "clusters"],
            "properties": {"group_id": {"type": "string"},
                           "clusters": {"type": "array", "items": {"type": "string"}}}}}]},
    },
}

PAIR_TASK = (
    "Task: label each pair below with exactly one of same, a_more_specific, b_more_specific, "
    "different, following section 1 of the guideline. Answer with JSON "
    '{"pairs": [{"pair_id": "...", "label": "..."}]} and one entry per pair_id given.'
)
SET_TASK = (
    "Task: group the items below into clusters following section 2 of the guideline. Every item id "
    "must appear in exactly one cluster. Answer with JSON "
    '{"clusters": [{"cluster_id": "c1", "members": ["..."]}], "coarse": null} or, when several '
    'clusters clearly serve one broader goal, with "coarse": [{"group_id": "g1", "clusters": '
    '["c1", "c2"]}] in which every cluster id appears exactly once.'
)


def system_prompt(settings: Settings) -> str:
    cluster = settings.cluster or {}
    guideline = (settings.base / cluster["guideline"]).read_text(encoding="utf-8").strip()
    examples = yaml.safe_load((settings.base / cluster["examples"]).read_text(encoding="utf-8"))
    rendered = yaml.safe_dump(examples, allow_unicode=True, sort_keys=False, width=100).strip()
    return f"{guideline}\n\n## Examples\n\n```yaml\n{rendered}\n```\n"


def pair_message(pairs: list[dict[str, Any]], pool: dict[str, dict[str, Any]]) -> str:
    body = [{"pair_id": p["pair_id"], "kind": pool[p["a"]]["kind"],
             "a": pool[p["a"]]["quote"], "b": pool[p["b"]]["quote"]} for p in pairs]
    return PAIR_TASK + "\n\n" + json.dumps({"pairs": body}, ensure_ascii=False, indent=1)


def set_message(item_ids: list[str], pool: dict[str, dict[str, Any]]) -> str:
    body = [{"id": i, "kind": pool[i]["kind"], "quote": pool[i]["quote"]} for i in item_ids]
    return SET_TASK + "\n\n" + json.dumps({"items": body}, ensure_ascii=False, indent=1)


def _sha(text: str) -> str:
    from mobility_model_zoo.productdev.jtbd.freeze import sha256_text

    return sha256_text(text)


def prompt_sha256(settings: Settings) -> str:
    return _sha(system_prompt(settings) + PAIR_TASK + SET_TASK)


def wire_schema_sha256() -> str:
    return _sha(json.dumps({"pairs": PAIR_SCHEMA, "sets": SET_SCHEMA}, sort_keys=True))


# ---- validation of answers -----------------------------------------------------------------------


def pair_answer_errors(answer: Any, pair_ids: list[str]) -> list[str]:
    """Every pair id given exactly once, labels from the four allowed values."""
    if not isinstance(answer, dict) or not isinstance(answer.get("pairs"), list):
        return ["answer is not {\"pairs\": [...]}"]
    errors, seen = [], []
    for entry in answer["pairs"]:
        if not isinstance(entry, dict) or entry.get("label") not in PAIR_LABELS:
            errors.append(f"invalid entry {str(entry)[:80]}")
            continue
        seen.append(entry.get("pair_id"))
    missing = sorted(set(pair_ids) - set(seen))
    extra = sorted(set(seen) - set(pair_ids))
    repeated = sorted({p for p in seen if seen.count(p) > 1})
    for name, ids in (("missing", missing), ("unknown", extra), ("repeated", repeated)):
        if ids:
            errors.append(f"{name} pair ids: {', '.join(ids[:5])}")
    return errors


def set_answer_errors(answer: Any, item_ids: list[str]) -> list[str]:
    """Clusters cover every item exactly once with known ids; a coarse grouping, if given, covers
    every cluster exactly once."""
    if not isinstance(answer, dict) or not isinstance(answer.get("clusters"), list):
        return ["answer is not {\"clusters\": [...], \"coarse\": ...}"]
    errors, members, cluster_ids = [], [], []
    for c in answer["clusters"]:
        if not isinstance(c, dict) or not isinstance(c.get("members"), list) or not c["members"]:
            errors.append(f"invalid cluster {str(c)[:80]}")
            continue
        cluster_ids.append(c.get("cluster_id"))
        members += c["members"]
    missing = sorted(set(item_ids) - set(members))
    extra = sorted(set(members) - set(item_ids))
    repeated = sorted({m for m in members if members.count(m) > 1})
    for name, ids in (("missing", missing), ("unknown", extra), ("repeated", repeated)):
        if ids:
            errors.append(f"{name} items: {', '.join(map(str, ids[:5]))}")
    if len(set(cluster_ids)) != len(cluster_ids):
        errors.append("cluster ids repeat")
    coarse = answer.get("coarse")
    if coarse is not None:
        if not isinstance(coarse, list):
            return [*errors, "coarse is neither null nor a list"]
        grouped = [c for g in coarse if isinstance(g, dict) for c in g.get("clusters") or []]
        if Counter(grouped) != Counter(cluster_ids):
            errors.append("coarse groups do not cover every cluster exactly once")
    return errors
