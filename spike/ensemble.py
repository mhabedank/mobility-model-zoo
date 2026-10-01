# ruff: noqa: E501 - table output
"""Offline test of teacher ensembles on the 35 evaluation chunks (no model calls, no cost).

Combines the stored outputs of several teacher runs with `jtbd_pilot.ensemble.combine` (the
pilot's `pilot ensemble`) and scores each combination against the Claude consensus exactly like a
single model:
- relevance: majority vote (ties count as relevant),
- items: items of all models are grouped by span overlap (IoU >= min_iou, one item per model and
  group); a group is kept when at least `min_votes` models found it,
- attributes: majority vote inside the group; ties go to the model that is strongest on that
  dimension (DIM_PRIORITY),
- quote: from the model with the most verbatim quotes (QUOTE_PRIORITY); near-miss quotes are
  repaired to the verbatim source passage, as in the SFT export.
Single models are scored with the same quote repair so the comparison is fair.

The strategies are fixed below before looking at their results; picking the best of many
strategies on 35 chunks would overstate its score.

Run: uv run python spike/ensemble.py
     uv run python spike/ensemble.py --export data/spike/sft/sft-ensemble.jsonl   (train split)
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from jtbd_pilot.config import load_settings
from jtbd_pilot.consensus import load_consensus
from jtbd_pilot.corpus.store import chunk_map
from jtbd_pilot.ensemble import combine
from jtbd_pilot.jsonio import write_json, write_jsonl
from jtbd_pilot.labeling.prompt import build_system_prompt
from jtbd_pilot.metrics import CATEGORY_LABELS, EVIDENCE_LABELS, composite, f1_stat, kappa_stat
from jtbd_pilot.runs import ChunkOutput, load_outputs
from jtbd_pilot.scoring import RELEVANCE_LABELS, score_units

ROOT = Path(__file__).resolve().parent.parent
RUN = "run-teacher_candidate-{}-{}-3223351c"
MODELS = {  # short name -> model_id
    "mimo": "teacher-or-mimo-v2.6-pro",
    "deepseek": "teacher-or-deepseek-v4.1-flash",
    "glm53": "teacher-or-glm-5.3",
    "glmflash": "teacher-or-glm-5.3-flash",
    "qwen38": "teacher-qwen3.8",
}
# Measured single-model strengths on these chunks (spike findings), used only to break ties.
DIM_PRIORITY = {
    "kind": ["deepseek", "mimo", "glm53", "qwen38", "glmflash"],
    "actor_type": ["mimo", "deepseek", "glm53", "glmflash", "qwen38"],
    "evidence_type": ["glm53", "glmflash", "mimo", "qwen38", "deepseek"],
    "evidence_scope": ["mimo", "glmflash", "qwen38", "deepseek", "glm53"],
}
QUOTE_PRIORITY = ["deepseek", "qwen38", "mimo", "glmflash", "glm53"]
STRATEGIES = [  # name, models, min_votes
    ("single mimo", ["mimo"], 1),
    ("single deepseek", ["deepseek"], 1),
    ("single qwen38 (local)", ["qwen38"], 1),
    ("mimo+deepseek, union", ["mimo", "deepseek"], 1),
    ("top3 (mimo, deepseek, glm53), >=2", ["mimo", "deepseek", "glm53"], 2),
    ("top3, union", ["mimo", "deepseek", "glm53"], 1),
    ("all5, >=2", list(MODELS), 2),
    ("all5, >=3", list(MODELS), 3),
    ("cheap: mimo+deepseek+glmflash+qwen38, >=2", ["mimo", "deepseek", "glmflash", "qwen38"], 2),
]
EXPORT = ("cheap: mimo+deepseek+glmflash+qwen38, >=2", ["mimo", "deepseek", "glmflash", "qwen38"], 2)


def scores(outputs: dict[str, ChunkOutput], consensus, contested, chunk_ids, min_iou) -> dict:
    units, _ = score_units(consensus, contested, chunk_ids, outputs, min_iou)
    stats = {"relevance": kappa_stat(RELEVANCE_LABELS), "item_matching": f1_stat,
             "evidence_type": kappa_stat(EVIDENCE_LABELS, "quadratic"),
             **{d: kappa_stat(labels) for d, labels in CATEGORY_LABELS.items()}}
    dims = {}
    for d, stat in stats.items():
        payloads = [p for _, p in units[d]]
        dims[d] = round(float(stat(payloads)), 3) if payloads else None
    tp = sum(p[0] for _, p in units["item_matching"])
    fp = sum(p[1] for _, p in units["item_matching"])
    fn = sum(p[2] for _, p in units["item_matching"])
    without_rel = composite(v for k, v in dims.items() if k != "relevance")
    return {"dims": dims, "composite": composite(dims.values()), "without_relevance": without_rel,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "items": sum(len(o.items) for o in outputs.values())}


def export(settings, out: Path, min_iou: float) -> None:
    """Training data from the fixed EXPORT strategy on the train split (same format as export_sft)."""
    from jtbd_pilot.spike import chatml

    name, models, min_votes = EXPORT
    chunks = chunk_map(settings, "train")
    outputs = {m: load_outputs(settings, RUN.format(MODELS[m], "train")) for m in models}
    combined = combine(outputs, models, min_votes, chunks, min_iou, DIM_PRIORITY, QUOTE_PRIORITY)
    system = build_system_prompt(settings)
    rows, skipped = [], []
    for chunk_id, out_ in sorted(combined.items()):
        if out_.relevant is None:
            skipped.append(chunk_id)
            continue
        items = [{"kind": it.kind, "quote": " ".join(it.quote.split()), "actor": it.actor,
                  "actor_type": it.actor_type, "statement": it.statement,
                  "evidence_type": it.evidence_type, "evidence_scope": it.evidence_scope}
                 for it in out_.items]
        answer = json.dumps({"relevant": out_.relevant, "items": items}, ensure_ascii=False)
        user = chunks[chunk_id].text
        rows.append({"chunk_id": chunk_id,
                     "messages": [{"role": "system", "content": system},
                                  {"role": "user", "content": user},
                                  {"role": "assistant", "content": answer}],
                     "prompt": chatml(system, user), "output": answer})
    write_jsonl(out, rows)
    stats = {"strategy": name, "runs": {m: RUN.format(MODELS[m], "train") for m in models},
             "examples": len(rows), "items": sum(len(json.loads(r["output"])["items"]) for r in rows),
             "skipped_chunks_without_output": skipped, "path": str(out),
             "exported_at": datetime.now(UTC).isoformat()}
    write_json(out.with_suffix(".stats.json"), stats)
    print(json.dumps(stats, indent=2))


def main() -> None:
    settings = load_settings(ROOT / "configs/spike-v1.yaml")
    min_iou = float(settings.pilot.get("min_iou", 0.3))
    consensus, contested, meta = load_consensus(settings, "main")
    chunks = chunk_map(settings, "main")
    if "--export" in sys.argv:
        export(settings, Path(sys.argv[sys.argv.index("--export") + 1]), min_iou)
        return
    outputs = {m: load_outputs(settings, RUN.format(mid, "main")) for m, mid in MODELS.items()}
    rows = []
    for name, models, min_votes in STRATEGIES:
        combined = combine(outputs, models, min_votes, chunks, min_iou, DIM_PRIORITY, QUOTE_PRIORITY)
        rows.append({"strategy": name, **scores(combined, consensus, contested, meta["chunks"], min_iou)})
    out = ROOT / "data/spike/ensemble.json"
    out.write_text(json.dumps(rows, indent=2))
    dims = ["relevance", "item_matching", "kind", "actor_type", "evidence_type", "evidence_scope"]
    print("| Strategie | " + " | ".join(dims) + " | Gesamt | ohne Rel. | Precision | Recall | Items |")
    for r in rows:
        print(f"| {r['strategy']} | " + " | ".join(f"{r['dims'][d]:.2f}" for d in dims)
              + f" | {r['composite']:.2f} | {r['without_relevance']:.2f} | {r['precision']:.2f} | {r['recall']:.2f} | {r['items']} |")


if __name__ == "__main__":
    main()
