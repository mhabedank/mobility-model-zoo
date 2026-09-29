"""Verbatim quote locator (Principle II, FR-026).

Only the normalization allowed by the spec's Edge Cases is applied: runs of whitespace (including
line breaks) collapse to one space, and typographic quote characters map to ASCII quotes. Anything
else, including a translation or paraphrase, fails.
"""

from __future__ import annotations

QUOTE_MAP = {
    "„": '"', "“": '"', "”": '"', "‟": '"', "«": '"', "»": '"',
    "‚": "'", "‘": "'", "’": "'", "‛": "'", "‹": "'", "›": "'",
}


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Normalized text plus, for each normalized character, its index in the original text."""
    chars: list[str] = []
    index: list[int] = []
    in_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not in_space and chars:
                chars.append(" ")
                index.append(i)
            in_space = True
            continue
        in_space = False
        chars.append(QUOTE_MAP.get(ch, ch))
        index.append(i)
    if chars and chars[-1] == " ":
        chars.pop()
        index.pop()
    return "".join(chars), index


def normalize(text: str) -> str:
    return normalize_with_map(text)[0]


def locate(
    quote: str, text: str, used: list[tuple[int, int]] | None = None
) -> tuple[int, int] | None:
    """Return the (start, end) span of `quote` in `text`, preferring an occurrence not in `used`."""
    needle = normalize(quote)
    if not needle:
        return None
    haystack, index = normalize_with_map(text)
    spans = []
    start = haystack.find(needle)
    while start != -1:
        end_norm = start + len(needle) - 1
        spans.append((index[start], index[end_norm] + 1))
        start = haystack.find(needle, start + 1)
    if not spans:
        return None
    for span in spans:
        if not used or span not in used:
            return span
    return spans[0]


REPAIR_MIN_SCORE = 90.0


def repair(quote: str, text: str, min_score: float = REPAIR_MIN_SCORE) -> tuple[int, int] | None:
    """Span of the passage in `text` that `quote` most likely means, for training data only.

    Teacher quotes often differ from the source by PDF hyphenation, an ellipsis or a changed word.
    The caller replaces the quote with `text[start:end]`, so the repaired quote is verbatim again
    (Principle II). Returns None when no passage matches closely enough.
    """
    from rapidfuzz import fuzz

    needle = normalize(quote)
    haystack, index = normalize_with_map(text)
    if len(needle) < 10 or not haystack:
        return None
    match = fuzz.partial_ratio_alignment(needle, haystack)
    if match is None or match.score < min_score:
        return None
    start, end = match.dest_start, match.dest_end
    # The alignment window has the quote's length; widen or narrow both ends to the best fit.
    slack = max(5, len(needle) // 10)
    best = fuzz.ratio(needle, haystack[start:end])
    for s in range(max(0, start - slack), start + slack + 1):
        for e in range(max(s + 1, end - slack), min(len(haystack), end + slack) + 1):
            score = fuzz.ratio(needle, haystack[s:e])
            if score > best:
                best, start, end = score, s, e
    if not 0.8 <= (end - start) / len(needle) <= 1.25:
        return None
    return index[start], index[end - 1] + 1
