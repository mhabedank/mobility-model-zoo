"""Thresholds on the validation rows only (feature 004, FR-010, T028).

The unit threshold is chosen from the recipe's grid by validation score; then the relevance
threshold (at least the unit threshold) as the median of the candidates that tie for the best
relevance agreement on the validation chunks. Ported from the spike's tune_span_threshold.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

from mobility_model_zoo.productdev.jtbd.span.extractor import CONFIG_FILE, SpanExtractor
from mobility_model_zoo.productdev.jtbd.span.train import (
    decide,
    score_rows,
    validation_metrics,
)


def tune_thresholds(model_dir: Path, val_rows: list[dict[str, Any]], unit_grid: list[float]
                    ) -> dict[str, Any]:
    if not val_rows:
        raise ValueError("no validation rows to tune on")
    extractor = SpanExtractor.from_pretrained(model_dir)
    dims = extractor.dimensions
    scored = score_rows(extractor, val_rows)
    unit_table = []
    for threshold in unit_grid:
        metrics = validation_metrics(val_rows, scored, dims, threshold, threshold)
        unit_table.append({"unit": threshold, **metrics})
    best_unit = max(unit_table, key=lambda r: (r["score"], -r["unit"]))["unit"]
    candidates = sorted({round(u["score"], 4) for s in scored.values() for u in s
                         if u["score"] >= best_unit} | {best_unit})
    relevance_table = []
    for threshold in candidates:
        correct = sum(decide(scored[r["chunk_id"]], best_unit, threshold)[0] == r["relevant"]
                      for r in val_rows)
        relevance_table.append({"relevance": threshold, "correct": correct})
    top = max(r["correct"] for r in relevance_table)
    best_relevance = median(r["relevance"] for r in relevance_table if r["correct"] == top)
    final = validation_metrics(val_rows, scored, dims, best_unit, best_relevance)
    config = json.loads((model_dir / CONFIG_FILE).read_text(encoding="utf-8"))
    config["thresholds"] = {"unit": best_unit, "relevance": best_relevance}
    config["threshold_tuning"] = {"rows": len(val_rows), "unit_table": unit_table,
                                  "relevance_correct_max": top, "validation": final}
    (model_dir / CONFIG_FILE).write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n",
                                         encoding="utf-8")
    return {"thresholds": config["thresholds"], "validation": final, "val_rows": len(val_rows)}
