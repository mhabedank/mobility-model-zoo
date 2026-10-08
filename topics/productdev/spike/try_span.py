"""Try the fast encoder span model (topics/productdev/spike/span_model.py) on your own text (spike, not a benchmark).

Prints relevance and each job, pain or gain with actor type, evidence and the verbatim quote, and
the time the model needed after loading. Texts of any length are processed in overlapping
512-token windows in one batch.

Run:
  uv run --with torch --with transformers --with sentencepiece --with protobuf \
      python topics/productdev/spike/try_span.py --file data/interviews/fiktiv-interview-fussgaenger-berlin.txt
Options: --model <dir> (default data/models/span-lt-fixed), --json, --device cpu|mps.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from span_model import load, predict  # noqa: E402

DEFAULT_MODEL = Path("data/models/span-lt-fixed")


def as_json(text: str, relevant: bool, prob: float, spans, seconds: float) -> dict:
    return {"relevant": relevant, "relevance_probability": round(prob, 3),
            "seconds": round(seconds, 3),
            "items": [{**asdict(s), "quote": text[s.start:s.end]} for s in spans]}


def as_text(text: str, relevant: bool, prob: float, spans, seconds: float, note: str = "") -> str:
    lines = [f"relevant: {relevant} (p={prob:.2f})   items: {len(spans)}   ({seconds:.2f}s{note})"]
    for n, s in enumerate(spans, start=1):
        lines += ["", f"{n}. {s.kind.upper()}  ({s.actor_type}; {s.evidence_type}, "
                      f"{s.evidence_scope}; confidence {s.score:.2f})",
                  f"   \"{' '.join(text[s.start:s.end].split())}\""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("text", nargs="?")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    args = parser.parse_args()
    text = (args.file.read_text(encoding="utf-8") if args.file
            else args.text or sys.stdin.read()).strip()
    if not text:
        parser.error("give a text, --file or stdin")

    start = time.time()
    model, tokenizer = load(args.model, args.device)
    predict(model, tokenizer, "Warm-up.", args.device)
    loaded = time.time() - start
    start = time.time()
    relevant, prob, spans = predict(model, tokenizer, text, args.device)
    seconds = time.time() - start

    if args.json:
        print(json.dumps(as_json(text, relevant, prob, spans, seconds), ensure_ascii=False,
                         indent=2))
    else:
        print(as_text(text, relevant, prob, spans, seconds,
                      f" on {args.device}; model loaded in {loaded:.1f}s"))


if __name__ == "__main__":
    main()
