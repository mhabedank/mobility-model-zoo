"""Score the encoder span model on the spike's 35 evaluation chunks (spike, not a benchmark).

Same scoring as ensemble.py and eval_local_model.py (agreement with the Claude
reference), plus the time per chunk after loading.

Run: uv run --with torch --with transformers --with sentencepiece --with protobuf \
         python topics/productdev/spike/eval_span.py [--model data/models/span-xlmr] [--device cpu|mps]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "spike"))

from ensemble import scores  # noqa: E402
from span_model import load, predict  # noqa: E402

from mobility_model_zoo.productdev.jtbd.config import load_settings  # noqa: E402
from mobility_model_zoo.productdev.jtbd.consensus import load_consensus  # noqa: E402
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map  # noqa: E402
from mobility_model_zoo.productdev.jtbd.runs import ChunkOutput, LocatedItem  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=ROOT / "data/models/span-xlmr")
    parser.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    args = parser.parse_args()
    settings = load_settings(ROOT / "configs/productdev/jtbd/spike-v1.yaml")
    consensus, contested, meta = load_consensus(settings, "main")
    chunks = chunk_map(settings, "main")
    model, tokenizer = load(args.model, args.device)
    predict(model, tokenizer, "Warm-up.", args.device)

    outputs, seconds = {}, 0.0
    for chunk_id, chunk in sorted(chunks.items()):
        start = time.time()
        relevant, _, spans = predict(model, tokenizer, chunk.text, args.device)
        seconds += time.time() - start
        items = [LocatedItem(n, s.kind, chunk.text[s.start:s.end], "", s.actor_type, "",
                             s.evidence_type, s.evidence_scope, (s.start, s.end))
                 for n, s in enumerate(spans)]
        outputs[chunk_id] = ChunkOutput(chunk_id, relevant, items)
    result = {"model": str(args.model), "device": args.device, "chunks": len(chunks),
              "mean_seconds_per_chunk": round(seconds / len(chunks), 3),
              **scores(outputs, consensus, contested, meta["chunks"],
                       float(settings.pilot.get("min_iou", 0.3)))}
    (args.model / f"eval-{args.device}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
