"""Consensus and contested set from two reference runs (FR-021, FR-022, Principle III).

An item can be in the consensus for some dimensions and contested for others. Contested entries
are kept and reported, never dropped.
"""

from __future__ import annotations

from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.freeze import freeze_benchmark
from jtbd_pilot.jsonio import read_json, read_jsonl, write_json, write_jsonl
from jtbd_pilot.matching import match_items, match_runs
from jtbd_pilot.runs import load_outputs, load_run_manifest
from jtbd_pilot.schema import ATTRIBUTE_DIMENSIONS


def suffix(split: str) -> str:
    return "" if split == "main" else f"-{split}"


def consensus_paths(settings: Settings, split: str = "main") -> dict[str, Any]:
    base = settings.analysis_dir
    sfx = suffix(split)
    return {
        "consensus": base / f"consensus{sfx}.jsonl",
        "contested": base / f"contested{sfx}.jsonl",
        "meta": base / f"consensus-meta{sfx}.json",
    }


def build_consensus(settings: Settings, run_a: str, run_b: str) -> dict[str, Any]:
    man_a, man_b = load_run_manifest(settings, run_a), load_run_manifest(settings, run_b)
    if man_a.role != "reference" or man_b.role != "reference":
        raise ValidationFailed("consensus needs two runs with role=reference")
    if man_a.family == man_b.family:
        raise ValidationFailed("reference runs must come from different model families")
    if man_a.split != man_b.split:
        raise ValidationFailed("reference runs must cover the same split")
    split = man_a.split
    match_runs(settings, run_a, run_b)
    out_a, out_b = load_outputs(settings, run_a), load_outputs(settings, run_b)
    min_iou = float(settings.pilot.get("min_iou", 0.3))

    consensus: list[dict] = []
    contested: list[dict] = []
    excluded = sorted(
        c for c in set(out_a) | set(out_b)
        if out_a.get(c) is None or out_b.get(c) is None
        or out_a[c].relevant is None or out_b[c].relevant is None
    )
    chunks = sorted((set(out_a) & set(out_b)) - set(excluded))
    for chunk_id in chunks:
        a, b = out_a[chunk_id], out_b[chunk_id]
        if a.relevant == b.relevant:
            consensus.append({"chunk_id": chunk_id, "level": "relevance", "value": a.relevant})
        else:
            contested.append({
                "id": f"{chunk_id}:relevance", "chunk_id": chunk_id, "level": "relevance",
                "dimensions": ["relevance"], "values": {"a": a.relevant, "b": b.relevant},
                "category": None,
            })
        for k, m in enumerate(match_items(a.items, b.items, min_iou)):
            key = f"{chunk_id}#{k}"
            if m.a and m.b:
                attrs_a, attrs_b = m.a.attrs(), m.b.attrs()
                agreed = {d: attrs_a[d] for d in ATTRIBUTE_DIMENSIONS if attrs_a[d] == attrs_b[d]}
                disagreed = [d for d in ATTRIBUTE_DIMENSIONS if attrs_a[d] != attrs_b[d]]
                span = (min(m.a.span[0], m.b.span[0]), max(m.a.span[1], m.b.span[1]))
                consensus.append({
                    "chunk_id": chunk_id, "level": "item", "item_key": key, "span": list(span),
                    "quote": m.a.quote, "values": agreed, "refs": {"a": m.a.index, "b": m.b.index},
                    "iou": round(m.iou, 6),
                })
                if disagreed:
                    contested.append({
                        "id": f"{key}:attributes", "chunk_id": chunk_id, "level": "item",
                        "item_key": key, "span": list(span), "quote": m.a.quote,
                        "dimensions": disagreed,
                        "values": {"a": {d: attrs_a[d] for d in disagreed},
                                   "b": {d: attrs_b[d] for d in disagreed}},
                        "category": None,
                    })
            else:
                item, side = (m.a, "a") if m.a else (m.b, "b")
                contested.append({
                    "id": f"{key}:existence", "chunk_id": chunk_id, "level": "item",
                    "item_key": key, "span": list(item.span), "quote": item.quote,
                    "dimensions": ["item_existence"], "found_by": side,
                    "values": {side: item.attrs(), ("b" if side == "a" else "a"): None},
                    "category": None,
                })
    paths = consensus_paths(settings, split)
    write_jsonl(paths["consensus"], consensus)
    write_jsonl(paths["contested"], contested)
    meta = {
        "reference_runs": [run_a, run_b],
        "run_backends": {run_a: man_a.backend, run_b: man_b.backend},
        "split": split,
        "chunks": chunks,
        "excluded_chunks": excluded,
        "invalid_quotes": {
            run_a: sum(1 for o in out_a.values() for i in o.items if not i.valid),
            run_b: sum(1 for o in out_b.values() for i in o.items if not i.valid),
        },
    }
    write_json(paths["meta"], meta)
    return {
        "split": split,
        "consensus_relevance": sum(1 for c in consensus if c["level"] == "relevance"),
        "consensus_items": sum(1 for c in consensus if c["level"] == "item"),
        "contested": len(contested),
        "excluded_chunks": excluded,
    }


def load_consensus(settings: Settings, split: str = "main") -> tuple[list[dict], list[dict], dict]:
    paths = consensus_paths(settings, split)
    if not paths["meta"].exists():
        raise ValidationFailed(f"no consensus for split {split}: run `pilot consensus` first")
    return (list(read_jsonl(paths["consensus"])), list(read_jsonl(paths["contested"])),
            read_json(paths["meta"]))


def freeze_benchmark_from_analysis(settings: Settings) -> dict[str, Any]:
    paths = consensus_paths(settings, "main")
    if not paths["meta"].exists():
        raise ValidationFailed("no main-split consensus: run `pilot consensus` first")
    meta = read_json(paths["meta"])
    manifest = freeze_benchmark(settings, meta["reference_runs"], meta["run_backends"],
                                paths["consensus"], paths["contested"])
    return {"version": manifest["version"], "state": manifest["state"],
            "test_only": manifest["test_only"], "benchmark": manifest["benchmark"]}
