"""Unicode word tokens with character offsets, and token IoU (feature 025, research R5).

The brief matches items at token IoU >= 0.5. Tokens are runs of Unicode word characters (`\\w+`), so
the result does not depend on any model's tokenizer; punctuation is never a token.
"""

from __future__ import annotations

import re
from functools import lru_cache

WORD = re.compile(r"\w+")

Span = tuple[int, int]


@lru_cache(maxsize=4096)
def tokenize(text: str) -> tuple[Span, ...]:
    return tuple(m.span() for m in WORD.finditer(text))


def token_set(tokens: tuple[Span, ...], span: Span) -> frozenset[int]:
    """Indices of the tokens that overlap the character span `[start, end)`."""
    start, end = span
    return frozenset(i for i, (s, e) in enumerate(tokens) if s < end and e > start)


def iou(a: frozenset[int], b: frozenset[int]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def span_iou(text: str, a: Span, b: Span) -> float:
    toks = tokenize(text)
    return iou(token_set(toks, a), token_set(toks, b))
