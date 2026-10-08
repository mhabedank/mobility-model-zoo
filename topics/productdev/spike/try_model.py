"""Try a local JTBD extraction model on your own text (spike, not a benchmark).

The model folder is built by topics/productdev/spike/build_local_model.sh and contains the MLX weights plus
`system_prompt.txt`, the exact system prompt the model was trained with. The prompt is formatted
like the training data (Qwen chat format) and decoded greedily. Texts longer than the training
chunks are split at paragraph ends into parts of at most 1,200 tokens, each labeled separately.
Generation stops when the model starts repeating the same quote (a known failure of the small
model); a cut-off answer keeps its complete items, duplicate items are removed, and items with
invalid values (for example an evidence type given as evidence scope) are dropped. All of this
is shown as notes.

Run:
  uv run --with mlx-lm python topics/productdev/spike/try_model.py "Der Bus fährt nur zweimal am Tag ..."
  uv run --with mlx-lm python topics/productdev/spike/try_model.py --file text.txt
  echo "..." | uv run --with mlx-lm python topics/productdev/spike/try_model.py
Options: --model <dir> (default data/models/spike-v3b-mlx-8bit), --json (raw JSON only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from mobility_model_zoo.productdev.jtbd.labeling.base import parse_json_text
from mobility_model_zoo.productdev.jtbd.quotes import locate
from mobility_model_zoo.productdev.jtbd.schema import ExtractionOutput, Item
from mobility_model_zoo.productdev.jtbd.spike import chatml

DEFAULT_MODEL = Path("data/models/spike-v3b-mlx-8bit")
PART_TOKENS = 1200  # training chunks had 300-1500 tokens; longer texts are split into parts


QUOTE = re.compile(r'"quote":\s*"((?:[^"\\]|\\.)*)"')
MAX_REPEATS = 2  # a third copy of the same quote means the model is looping


def _looping(text: str) -> bool:
    counts = Counter(QUOTE.findall(text))
    return bool(counts) and max(counts.values()) > MAX_REPEATS


def extract(model, tokenizer, system: str, text: str, max_tokens: int = 4096,
            progress: bool = False) -> tuple[str, float]:
    """Greedy answer; stops early when the model starts repeating the same quote.

    With `progress`, a status line on stderr shows generated tokens, items and speed.
    """
    from mlx_lm import stream_generate
    from mlx_lm.sample_utils import make_sampler

    start = time.time()
    answer = ""
    for n, step in enumerate(stream_generate(model, tokenizer, prompt=chatml(system, text),
                                             max_tokens=max_tokens,
                                             sampler=make_sampler(temp=0.0)), start=1):
        answer += step.text
        if progress and (n == 1 or n % 10 == 0):
            if n == 1:
                _status(f"prompt read ({step.prompt_tokens} tokens, {time.time() - start:.0f}s); "
                        "generating", end="\n")
            _status(f"  {n} tokens, {len(QUOTE.findall(answer))} items, "
                    f"{step.generation_tps:.0f} tokens/s, {time.time() - start:.0f}s")
        if n % 20 == 0 and _looping(answer):
            if progress:
                _status("  stopped: the model started repeating the same quote", end="\n")
            break
    if progress:
        _status(f"  done: {n} tokens in {time.time() - start:.0f}s", end="\n")
    return answer, time.time() - start


def _status(message: str, end: str = "") -> None:
    print(f"\r\033[K{message}", end=end, file=sys.stderr, flush=True)


def salvage(answer: str) -> tuple[dict | None, list[str]]:
    """The answer as a dict with duplicate items removed; a cut-off answer keeps its complete items.

    Inference-side clean-up for trying the model, recorded in the returned notes.
    """
    notes: list[str] = []
    candidate = parse_json_text(answer)
    if not isinstance(candidate, dict):
        relevant = re.search(r'"relevant":\s*(true|false)', answer)
        start = answer.find('"items"')
        if not relevant or start == -1:
            return None, ["no usable JSON"]
        decoder, items = json.JSONDecoder(strict=False), []
        pos = answer.find("[", start) + 1
        while True:
            pos = answer.find("{", pos)
            if pos == -1:
                break
            try:
                item, pos = decoder.raw_decode(answer, pos)
            except json.JSONDecodeError:
                break
            items.append(item)
        candidate = {"relevant": relevant.group(1) == "true", "items": items}
        notes.append("answer was cut off (token limit or looping); kept its complete items")
    items = candidate.get("items")
    if isinstance(items, list):
        seen, unique = set(), []
        for item in items:
            key = (item.get("kind"), item.get("quote")) if isinstance(item, dict) else id(item)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        if len(unique) < len(items):
            notes.append(f"removed {len(items) - len(unique)} duplicate items")
        valid = []
        for n, item in enumerate(unique, start=1):
            try:
                valid.append(Item.model_validate(item).model_dump())
            except Exception as exc:  # noqa: BLE001 - drop the item, keep the rest
                problems = "; ".join(f"{'.'.join(map(str, e['loc']))}={e.get('input')!r}"
                                     for e in exc.errors())
                notes.append(f"dropped item {n} with invalid values ({problems})")
        candidate["items"] = valid
    return candidate, notes


def split_text(text: str, tokenizer, max_tokens: int = PART_TOKENS) -> list[str]:
    """Paragraph-aligned parts of at most `max_tokens`, the size the model was trained on.

    A paragraph longer than that is split at sentence ends.
    """
    def size(t: str) -> int:
        return len(tokenizer.encode(t))

    pieces: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        if size(paragraph) <= max_tokens:
            pieces.append(paragraph)
            continue
        sentence_part = ""
        for sentence in re.split(r"(?<=[.!?…])\s+", paragraph):
            if sentence_part and size(sentence_part + " " + sentence) > max_tokens:
                pieces.append(sentence_part)
                sentence_part = sentence
            else:
                sentence_part = f"{sentence_part} {sentence}".strip()
        if sentence_part:
            pieces.append(sentence_part)
    parts, current = [], ""
    for piece in pieces:
        if current and size(current + "\n\n" + piece) > max_tokens:
            parts.append(current)
            current = piece
        else:
            current = f"{current}\n\n{piece}" if current else piece
    if current:
        parts.append(current)
    return parts


def show(text: str, answer: str, seconds: float) -> int:
    """Print one part's result; returns the number of items shown."""
    candidate, notes = salvage(answer)
    try:
        output = ExtractionOutput.model_validate(candidate)
    except Exception as exc:  # noqa: BLE001 - report any invalid answer
        print(f"Invalid output after {seconds:.1f}s: {str(exc)[:300]}\n\n{answer}")
        return 0
    print(f"relevant: {output.relevant}   items: {len(output.items)}   ({seconds:.1f}s)")
    for note in notes:
        print(f"note: {note}")
    used: list[tuple[int, int]] = []
    for n, item in enumerate(output.items, start=1):
        span = locate(item.quote, text, used)
        if span:
            used.append(span)
        print(f"\n{n}. {item.kind.upper()}  {item.statement}")
        print(f"   actor:    {item.actor} ({item.actor_type})")
        print(f"   evidence: {item.evidence_type}, {item.evidence_scope}")
        print(f"   quote:    \"{item.quote}\"" + ("" if span else "   [NOT VERBATIM]"))
    return len(output.items)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("text", nargs="?")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--json", action="store_true", help="print the raw model answer only")
    args = parser.parse_args()
    if args.file:
        text = args.file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    if not text.strip():
        parser.error("give a text, --file or stdin")

    from mlx_lm import load

    system = (args.model / "system_prompt.txt").read_text(encoding="utf-8")
    _status(f"loading {args.model} ...")
    model, tokenizer = load(str(args.model))
    parts = split_text(text, tokenizer)
    results, total = [], 0
    for n, part in enumerate(parts, start=1):
        if len(parts) > 1:
            _status(f"part {n}/{len(parts)} ({len(tokenizer.encode(part))} tokens)", end="\n")
            if not args.json:
                print(f"\n=== Part {n}/{len(parts)}: {part[:70].splitlines()[0]} ...")
        _status("reading the prompt (guideline, examples and your text) ...")
        answer, seconds = extract(model, tokenizer, system, part, progress=True)
        if args.json:
            output, notes = salvage(answer)
            results.append({"part": n, "text": part, "output": output, "notes": notes})
        else:
            total += show(part, answer, seconds)
    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0]["output"],
                         ensure_ascii=False, indent=2))
    elif len(parts) > 1:
        print(f"\n=== {total} items from {len(parts)} parts")


if __name__ == "__main__":
    main()
