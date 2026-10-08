"""Categorize the contested set (001 T063) with a local model instead of by hand.

The owner does not review entries by hand (decision of 2026-10-06). A local model on the DGX Spark
reads each chunk once, together with the guideline and every contested entry of that chunk, and
assigns one category from data/analysis/<version>/categories.yaml plus a short note. The model only
analyses the disagreement; it labels nothing and its weights do not change. Answers are cached in
contested-llm.jsonl, so the run can be resumed. The filled-in CSV is then read with
`jtbd categorize --import`.

    uv run python scripts/pilot/categorize_contested.py [--version pilot-v1]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[2]
MODEL = "qwen3.8:27b"
PROMPT = """You analyse disagreements between two annotation models, A and B, that labeled the same
text under the guideline below. For each contested entry, choose the ONE category that best
explains the disagreement and write a short note (max 25 words, English).

How to read an entry:
- dimensions "item_existence": only one model extracted an item with this quote. value_a or
  value_b is empty for the model that did not. Decide whether the statement qualifies as an item
  under the guideline (then "missed_item"), is borderline ("extraction_threshold"), is the same
  content the other model quoted with a different span ("quote_span_choice"), split or merged
  differently ("item_split_merge"), or whether the extracting model is clearly wrong.
- other dimensions: both models extracted the item but disagree on the named attribute(s).

Categories:
{categories}

Guideline:
{guideline}

Text (chunk {chunk_id}):
<<<
{text}
>>>

Contested entries:
{entries}

Answer only with JSON: {{"entries": [{{"id": "...", "category": "...", "note": "..."}}]}}
"""


def schema(keys: list[str]) -> dict:
    return {"type": "object", "properties": {"entries": {"type": "array", "items": {
        "type": "object", "properties": {"id": {"type": "string"},
                                         "category": {"enum": keys},
                                         "note": {"type": "string"}},
        "required": ["id", "category", "note"]}}}, "required": ["entries"]}


def ask(base_url: str, prompt: str, keys: list[str]) -> list[dict]:
    response = httpx.post(f"{base_url}/api/chat", timeout=1200, json={
        "model": MODEL, "stream": False, "think": False, "format": schema(keys),
        "options": {"temperature": 0, "num_ctx": 32768},
        "messages": [{"role": "user", "content": prompt}]})
    response.raise_for_status()
    return json.loads(response.json()["message"]["content"]).get("entries", [])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="pilot-v1")
    parser.add_argument("--guideline", default="guideline/guideline-v1.md")
    args = parser.parse_args()
    analysis = ROOT / "data/analysis" / args.version
    rows = list(csv.DictReader((analysis / "contested-review.csv").open(encoding="utf-8")))
    cats = yaml.safe_load((analysis / "categories.yaml").read_text())["categories"]
    keys = sorted(cats)
    guideline = (ROOT / args.guideline).read_text(encoding="utf-8")
    cache_path = analysis / "contested-llm.jsonl"
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            r = json.loads(line)
            cache[r["id"]] = r
    by_chunk = defaultdict(list)
    for row in rows:
        by_chunk[row["chunk_id"]].append(row)
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    base_url = os.environ["OLLAMA_HOST"].rstrip("/")
    todo = [c for c, rs in by_chunk.items() if any(r["id"] not in cache for r in rs)]
    print(f"{len(rows)} entries in {len(by_chunk)} chunks, {len(todo)} chunks to do", flush=True)
    with cache_path.open("a", encoding="utf-8") as out:
        for n, chunk_id in enumerate(sorted(todo), 1):
            text = json.loads((ROOT / "data/chunks" / f"{chunk_id}.json").read_text())["text"]
            pending = [r for r in by_chunk[chunk_id] if r["id"] not in cache]
            for start in range(0, len(pending), 25):
                batch = pending[start:start + 25]
                entries = "\n".join(json.dumps({k: r[k] for k in ("id", "dimensions", "quote",
                                                                   "value_a", "value_b")},
                                               ensure_ascii=False) for r in batch)
                prompt = PROMPT.format(categories="\n".join(f"- {k}: {v}" for k, v in cats.items()),
                                       guideline=guideline, chunk_id=chunk_id, text=text,
                                       entries=entries)
                wanted = {r["id"] for r in batch}
                answers = [a for a in ask(base_url, prompt, keys) if a.get("id") in wanted]
                for a in answers:
                    cache[a["id"]] = a
                    out.write(json.dumps(a, ensure_ascii=False) + "\n")
                out.flush()
            print(f"{n}/{len(todo)}", flush=True)
    missing = [r["id"] for r in rows if r["id"] not in cache]
    for row in rows:
        if row["id"] in cache:
            row["category"] = cache[row["id"]]["category"]
            row["note"] = "[model " + MODEL + "] " + cache[row["id"]]["note"]
    filled = analysis / "contested-review-filled.csv"
    with filled.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"filled": str(filled), "missing": len(missing)}))
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
