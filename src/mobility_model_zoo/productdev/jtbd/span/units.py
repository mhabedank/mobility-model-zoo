"""Sentence and clause units, and overlapping token windows (research R6).

Inference half of the span model: standard library plus a `transformers` tokenizer only. Training
uses the same functions, so training-time units and windows are exactly the published ones.
"""

from __future__ import annotations

import re
from typing import Any

# Sentence and clause ends: . ! ? ; followed by whitespace, or a blank line. A single line break
# is not an end, because PDF text breaks lines inside sentences.
UNIT_SPLIT = r"(?<=[.!?;])\s+|\n\s*\n"
_UNIT_END = re.compile(UNIT_SPLIT)

MAX_LENGTH = 512
STRIDE = 128


def units(text: str) -> list[tuple[int, int]]:
    """Sentence and clause spans of `text` as character offsets, whitespace trimmed."""
    spans, start = [], 0
    for match in [*_UNIT_END.finditer(text), None]:
        end = match.start() if match else len(text)
        a, b = start, end
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if b > a:
            spans.append((a, b))
        if match:
            start = match.end()
    return spans


def windows(tokenizer: Any, text: str, max_length: int = MAX_LENGTH,
            stride: int = STRIDE) -> dict[str, list[list]]:
    """Overlapping windows of `max_length` tokens (`stride` tokens overlap) covering all of `text`.

    Built by hand: `return_overflowing_tokens` in transformers 5 stops after two windows. Each
    window holds `max_length - 2` content tokens between the start and end token. Special and
    padding tokens get the offset (0, 0).
    """
    enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offsets = enc["input_ids"], enc["offset_mapping"]
    size = max_length - 2
    starts = list(range(0, max(len(ids) - stride, 1), size - stride)) or [0]
    rows: dict[str, list[list]] = {"input_ids": [], "attention_mask": [], "offset_mapping": []}
    for start in starts:
        part = ids[start:start + size]
        span = [tuple(o) for o in offsets[start:start + size]]
        pad = max_length - len(part) - 2
        rows["input_ids"].append([tokenizer.cls_token_id, *part, tokenizer.sep_token_id]
                                 + [tokenizer.pad_token_id] * pad)
        rows["attention_mask"].append([1] * (len(part) + 2) + [0] * pad)
        rows["offset_mapping"].append([(0, 0), *span, (0, 0)] + [(0, 0)] * pad)
    return rows


def unit_token_index(spans: list[tuple[int, int]],
                     tokens: list[tuple[int, int]]) -> list[tuple[tuple[int, int], list[int]]]:
    """For each unit, the indices of the (sorted, non-special) tokens that overlap it.

    Units without a token are left out.
    """
    out, position = [], 0
    for a, b in spans:
        idx = []
        while position < len(tokens) and tokens[position][0] < b:
            if tokens[position][1] > a:
                idx.append(position)
            position += 1
        if idx:
            out.append(((a, b), idx))
    return out
