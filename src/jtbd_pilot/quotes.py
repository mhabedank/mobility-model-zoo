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
