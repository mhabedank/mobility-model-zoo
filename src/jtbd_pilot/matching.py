"""Deterministic one-to-one item matching (FR-020, research.md R4).

Score = character-span IoU. A same-kind bonus far below any meaningful IoU difference only breaks
ties; kind is never a precondition. Pairs below `min_iou` stay unmatched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from scipy.optimize import linear_sum_assignment

from jtbd_pilot.config import Settings
from jtbd_pilot.jsonio import write_jsonl
from jtbd_pilot.runs import load_outputs

KIND_TIE_BREAK = 1e-9


class Spanned(Protocol):
    span: tuple[int, int] | None
    kind: str


@dataclass
class Match:
    a: Any | None
    b: Any | None
    iou: float
    same_kind: bool | None


def iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def match_items(items_a: list, items_b: list, min_iou: float) -> list[Match]:
    """Match items that have a located span. Items without span are ignored (counted elsewhere)."""
    a = [x for x in items_a if x.span is not None]
    b = [x for x in items_b if x.span is not None]
    matches: list[Match] = []
    used_a: set[int] = set()
    used_b: set[int] = set()
    if a and b:
        weights = np.zeros((len(a), len(b)))
        raw = np.zeros((len(a), len(b)))
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                value = iou(x.span, y.span)
                raw[i, j] = value
                if value >= min_iou:
                    weights[i, j] = value + (KIND_TIE_BREAK if x.kind == y.kind else 0.0)
        rows, cols = linear_sum_assignment(weights, maximize=True)
        for i, j in zip(rows, cols, strict=True):
            if weights[i, j] > 0:
                matches.append(Match(a[i], b[j], float(raw[i, j]), a[i].kind == b[j].kind))
                used_a.add(i)
                used_b.add(j)
    matches.sort(key=lambda m: (m.a.span[0], m.b.span[0]))
    for i, x in enumerate(a):
        if i not in used_a:
            matches.append(Match(x, None, 0.0, None))
    for j, y in enumerate(b):
        if j not in used_b:
            matches.append(Match(None, y, 0.0, None))
    return matches


def match_runs(settings: Settings, run_a: str, run_b: str) -> dict[str, Any]:
    out_a, out_b = load_outputs(settings, run_a), load_outputs(settings, run_b)
    min_iou = float(settings.pilot.get("min_iou", 0.3))
    rows = []
    for chunk_id in sorted(set(out_a) & set(out_b)):
        if out_a[chunk_id].relevant is None or out_b[chunk_id].relevant is None:
            continue
        for m in match_items(out_a[chunk_id].items, out_b[chunk_id].items, min_iou):
            rows.append({
                "chunk_id": chunk_id, "run_a": run_a, "run_b": run_b,
                "item_a": m.a.index if m.a else None, "item_b": m.b.index if m.b else None,
                "iou": round(m.iou, 6), "same_kind": m.same_kind,
            })
    write_jsonl(settings.analysis_dir / "matches" / f"{run_a}__{run_b}.jsonl", rows)
    matched = sum(1 for r in rows if r["item_a"] is not None and r["item_b"] is not None)
    return {"run_a": run_a, "run_b": run_b, "matched": matched,
            "unmatched_a": sum(1 for r in rows if r["item_b"] is None),
            "unmatched_b": sum(1 for r in rows if r["item_a"] is None)}
