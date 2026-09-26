"""Disagreement categories (FR-027, SC-004) and the free-text sample (FR-025).

Categories are stored separately from contested.jsonl, whose hash is part of the frozen benchmark.
Workflow: `--export` writes a CSV, the reviewer fills in `category` and `note`, `--import` reads it
back, `--check` fails while any contested entry has no category.
"""

from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.consensus import load_consensus
from jtbd_pilot.corpus.store import chunk_map
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.jsonio import read_jsonl, read_yaml, write_jsonl, write_yaml
from jtbd_pilot.runs import load_outputs

SEED_CATEGORIES = {
    "evidence_boundary_anecdote_routine": "Anecdote vs routine: regularity cue read differently",
    "evidence_boundary_observation_measurement": "Observation vs measurement: is the number from "
    "a defined measurement?",
    "pain_vs_negated_gain": "Present problem labeled as missing gain, or the reverse",
    "item_split_merge": "One model splits what the other keeps as one item",
    "actor_type_boundary": "Actor type boundary (e.g. worker vs individual, public sector vs "
    "organization)",
    "relevance_near_miss": "Near-miss judged relevant by one model",
    "quote_span_choice": "Different quote span for the same content",
    "reference_b_clearly_wrong": "The GPT mini-tier reference is clearly wrong (deviation check)",
    "reference_a_clearly_wrong": "The Claude reference is clearly wrong",
}
CONTEXT_CHARS = 200
FIELDS = ["id", "chunk_id", "dimensions", "quote", "context", "value_a", "value_b", "category",
          "note"]


def _paths(settings: Settings) -> dict[str, Path]:
    base = settings.analysis_dir
    return {
        "categories": base / "categories.yaml",
        "assignments": base / "contested-categories.jsonl",
        "review": base / "contested-review.csv",
        "freetext": base / "freetext-sample.csv",
    }


def categories(settings: Settings) -> dict[str, str]:
    path = _paths(settings)["categories"]
    if not path.exists():
        write_yaml(path, {"categories": SEED_CATEGORIES})
    return read_yaml(path)["categories"]


def assignments(settings: Settings) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in read_jsonl(_paths(settings)["assignments"])}


def _context(text: str, span: list[int] | None) -> str:
    if not span:
        return text[: 2 * CONTEXT_CHARS]
    start, end = max(0, span[0] - CONTEXT_CHARS), min(len(text), span[1] + CONTEXT_CHARS)
    return text[start:end]


def export_review(settings: Settings) -> dict[str, Any]:
    _, contested, _ = load_consensus(settings, "main")
    chunks = chunk_map(settings)
    done = assignments(settings)
    categories(settings)
    path = _paths(settings)["review"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for entry in contested:
            prior = done.get(entry["id"], {})
            writer.writerow({
                "id": entry["id"],
                "chunk_id": entry["chunk_id"],
                "dimensions": ",".join(entry["dimensions"]),
                "quote": entry.get("quote", ""),
                "context": _context(chunks[entry["chunk_id"]].text, entry.get("span")),
                "value_a": entry["values"].get("a"),
                "value_b": entry["values"].get("b"),
                "category": prior.get("category", ""),
                "note": prior.get("note", ""),
            })
    return {"exported": len(contested), "path": str(path)}


def import_review(settings: Settings, csv_path: Path) -> dict[str, Any]:
    allowed = categories(settings)
    _, contested, _ = load_consensus(settings, "main")
    known = {c["id"] for c in contested}
    current = assignments(settings)
    errors = []
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            category = (row.get("category") or "").strip()
            if not category:
                continue
            if row["id"] not in known:
                errors.append(f"unknown contested id {row['id']}")
            elif category not in allowed:
                errors.append(f"{row['id']}: unknown category {category!r} (add it to "
                              f"categories.yaml first)")
            else:
                current[row["id"]] = {"id": row["id"], "category": category,
                                      "note": (row.get("note") or "").strip()}
    if errors:
        raise ValidationFailed(f"{len(errors)} problem(s): {errors[:10]}")
    write_jsonl(_paths(settings)["assignments"], [current[k] for k in sorted(current)])
    return {"categorized": len(current), "contested": len(known)}


def summarize(settings: Settings) -> dict[str, Any]:
    _, contested, _ = load_consensus(settings, "main")
    done = assignments(settings)
    counts = Counter(done[c["id"]]["category"] for c in contested if c["id"] in done)
    examples: dict[str, list[str]] = defaultdict(list)
    for c in contested:
        if c["id"] in done and len(examples[done[c["id"]]["category"]]) < 3:
            examples[done[c["id"]]["category"]].append(c["id"])
    return {
        "contested": len(contested),
        "categorized": sum(1 for c in contested if c["id"] in done),
        "uncategorized": [c["id"] for c in contested if c["id"] not in done],
        "counts": dict(counts.most_common()),
        "examples": dict(examples),
        "descriptions": categories(settings),
    }


def check_categories(settings: Settings) -> dict[str, Any]:
    result = summarize(settings)
    if result["uncategorized"]:
        raise ValidationFailed(f"{len(result['uncategorized'])} contested entries without a "
                               f"category, e.g. {result['uncategorized'][:5]}")
    return result


def export_freetext_sample(settings: Settings, size: int = 30, seed: int = 20260925
                           ) -> dict[str, Any]:
    """Stratified sample of matched pairs showing actor and statement from both references."""
    consensus, _, meta = load_consensus(settings, "main")
    run_a, run_b = meta["reference_runs"]
    out_a, out_b = load_outputs(settings, run_a), load_outputs(settings, run_b)
    chunks = chunk_map(settings)
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for c in consensus:
        if c["level"] == "item":
            chunk = chunks[c["chunk_id"]]
            strata[(chunk.language, chunk.source_type)].append(c)
    rng = random.Random(seed)
    for rows in strata.values():
        rng.shuffle(rows)
    picked: list[dict] = []
    while len(picked) < size and any(strata.values()):
        for key in sorted(strata):
            if strata[key] and len(picked) < size:
                picked.append(strata[key].pop())
    path = _paths(settings)["freetext"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["item_key", "chunk_id", "quote", "actor_a", "actor_b", "statement_a",
                         "statement_b", "systematic_divergence_note"])
        for c in picked:
            a = out_a[c["chunk_id"]].items[c["refs"]["a"]]
            b = out_b[c["chunk_id"]].items[c["refs"]["b"]]
            writer.writerow([c["item_key"], c["chunk_id"], c["quote"], a.actor, b.actor,
                             a.statement, b.statement, ""])
    return {"sampled": len(picked), "path": str(path)}
