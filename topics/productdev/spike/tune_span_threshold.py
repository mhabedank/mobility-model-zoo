"""Choose a span model's unit and relevance thresholds on its validation chunks (span_model.json).

Run: uv run --with torch --with transformers --with sentencepiece --with protobuf \
         python spike/tune_span_threshold.py data/models/<model> data/models/spark/rows-<rows>.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from span_model import load, predict  # noqa: E402
from train_span import evaluate  # noqa: E402

THRESHOLDS = (0.2, 0.3, 0.4, 0.5, 0.6)


def main() -> None:
    model_dir, rows_path = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    val = [r for r in rows if r["split"] == "val"]
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model, tokenizer = load(model_dir, device)
    results = {}
    for threshold in THRESHOLDS:
        model.threshold = threshold
        results[threshold] = evaluate(model, tokenizer, val, device)
        print(threshold, results[threshold], flush=True)
    best = max(results, key=lambda t: results[t]["score"])
    # Relevance: the lowest confidence of a chunk's best item that classifies the most validation
    # chunks correctly, in the middle of the best range.
    model.threshold = best
    model.relevance_threshold = 0.0
    best_scores = [(r["relevant"], max((s.score for s in predict(model, tokenizer, r["text"],
                                                                     device)[2]), default=0.0))
                   for r in val]
    accuracy = {t: sum((score >= t) == gold for gold, score in best_scores)
                for t in (best, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9) if t >= best}
    top = [t for t, a in accuracy.items() if a == max(accuracy.values())]
    relevance_threshold = sorted(top)[len(top) // 2]
    print(f"relevance accuracy by threshold: {accuracy}")
    meta_path = model_dir / "span_model.json"
    meta = json.loads(meta_path.read_text())
    meta.update(unit_threshold=best, relevance_threshold=relevance_threshold,
                threshold_tuning={str(k): v for k, v in results.items()},
                relevance_tuning={str(k): v for k, v in accuracy.items()})
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"unit_threshold = {best}, relevance_threshold = {relevance_threshold}")


if __name__ == "__main__":
    main()
