"""Scans: personal identifiers, special categories and corpus overlap (research R5, R6, R9).

The PII patterns are deliberately independent of the jtbd redaction module: the pre-send and
publication checks re-scan text with their own, broader set instead of trusting a stored flag.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Spaces before a dot are tolerated (PDF extraction: "name@dlr .de"), spaces after it are not.
    (
        "email",
        re.compile(
            r"[A-Za-z0-9._%+-]+\s?(?:@|\(at\)|\[at\])\s?[A-Za-z0-9-]+"
            r"(?:\s?(?:\.|\(dot\)|\[dot\])[A-Za-z0-9-]+)*\s?(?:\.|\(dot\)|\[dot\])"
            r"[A-Za-z]{2,}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "profile_url",
        re.compile(
            r"https?://(?:[a-z]+\.)?(?:reddit\.com/(?:u|user)|facebook\.com|twitter\.com|x\.com|"
            r"instagram\.com|linkedin\.com/in|mastodon\.[a-z.]+/@)[^\s)\]>]*",
            re.IGNORECASE,
        ),
    ),
    (
        "user_path_url",
        re.compile(
            r"https?://\S+?/(?:u|user|users|profile|profiles|member|members|people|author)/[^\s/)\]>]+",
            re.IGNORECASE,
        ),
    ),
    ("reddit_user", re.compile(r"(?<![\w/])/?u/[A-Za-z0-9_-]{3,20}\b")),
    # a handle starts with a letter or underscore: "@50 Hz", "@360 MHz" are not handles
    ("at_handle", re.compile(r"(?<![\w.@\[\]/])@[A-Za-z_][A-Za-z0-9_]{1,29}\b(?![{/])")),
    (
        "phone_labeled",
        re.compile(r"(?i)\b(?:tel|telefon|phone|fon|mobil|handy)\.?:?\s*[+\d][\d\s/().-]{6,}\d"),
    ),
    (
        "phone_international",
        # not followed by more hex or an ellipsis: "00112233…" is a payload, not a number
        re.compile(
            r"(?<![\w+\-/.])(?:\+|00)\d{1,3}[\s./-]?(?:\(?\d{1,5}\)?[\s./-]?){2,5}\d{2,}(?![\w…])"
        ),
    ),
    ("phone_de", re.compile(r"(?<![\w/.\-])(?<!ISSN )(?<!ISBN )0\d{2,5}[\s/-]\d{4,}(?:[\s-]\d{2,})*\b")),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,4})?\b")),
    (
        "postal_address_de",
        re.compile(
            r"\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|strasse|str\.|weg|platz|allee|gasse|ring|damm)\s\d{1,4}[a-z]?,?\s"
            r"\d{5}\s[A-ZÄÖÜ][a-zäöüß]+"
        ),
    ),
    ("licence_plate_de", re.compile(r"\b[A-ZÄÖÜ]{1,3}-[A-Z]{1,2}\s\d{1,4}[EH]?(?![\d.])\b")),
    (
        "tax_id_de",
        re.compile(
            r"(?i)\b(?:steuer-?id|steueridentifikationsnummer|tin)\W{0,3}\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b"
        ),
    ),
    (
        "date_of_birth",
        re.compile(
            r"(?i)\b(?:geb\.|geboren am|born on|date of birth|dob)\s*:?\s*\d{1,2}[./]\d{1,2}[./]\d{2,4}"
        ),
    ),
]


@dataclass(frozen=True)
class Hit:
    kind: str
    start: int
    end: int


URL_KINDS = {"profile_url", "user_path_url"}
# Placeholders used in documentation and examples, and addresses that are not personal.
PLACEHOLDER_NAMES = {"name", "user", "username", "someuser", "someone", "max", "erika.mustermann"}
# Code tokens that look like @handles: CSS at-rules (`@font-face` matches as `@font`) and Python
# decorators in specs and docs. They name no person.
CODE_AT_TOKENS = {"font", "media", "import", "keyframes", "supports", "page", "charset", "layer",
                  "container", "namespace", "pytest", "dataclass", "property", "staticmethod",
                  "classmethod", "cache"}
NON_PERSONAL_DOMAINS = {
    "example.org",
    "example.com",
    "example.net",
    "users.noreply.github.com",
    "github.com",
}


def _is_placeholder(kind: str, match: str) -> bool:
    m = match.strip().lower().replace(" ", "")
    if kind == "email":
        local, _, domain = m.partition("@")
        return (
            local in PLACEHOLDER_NAMES
            or domain in NON_PERSONAL_DOMAINS
            or any(domain.endswith("." + d) for d in NON_PERSONAL_DOMAINS)
        )
    if kind in ("at_handle", "reddit_user"):
        name = m.lstrip("/").removeprefix("u/").lstrip("@")
        return name in PLACEHOLDER_NAMES or (kind == "at_handle" and name in CODE_AT_TOKENS)
    return False


MASK = re.compile(r"https?://\S+|\b10\.\d{4,9}/\S+")


def pii(text: str, allow: Iterable[str] = ()) -> list[Hit]:
    """Identifier hits; matches that equal an allowlisted string (case-insensitive) are skipped.

    URLs and DOIs are checked only for profile and user-page links; for the other patterns they are
    masked, so numbers inside links and identifiers do not look like phone numbers.
    """
    allowed = {a.lower() for a in allow}
    masked = MASK.sub(lambda m: " " * len(m.group(0)), text)
    hits = []
    for kind, pattern in PII_PATTERNS:
        for m in pattern.finditer(text if kind in URL_KINDS else masked):
            if m.group(0).strip().lower() in allowed or _is_placeholder(kind, m.group(0)):
                continue
            hits.append(Hit(kind, m.start(), m.end()))
    return hits


# ---- special categories (Art. 9 GDPR) --------------------------------------------------------


def art9_flags(text: str, lexicon: dict[str, list[str]]) -> dict[str, int]:
    """Count lexicon matches per category (terms match at word starts, case-insensitive)."""
    low = text.lower()
    counts = {}
    for category, terms in lexicon.items():
        n = sum(len(re.findall(r"(?<![\wäöüß])" + re.escape(t.lower()), low)) for t in terms)
        if n:
            counts[category] = n
    return counts


# ---- corpus shingle index and overlap --------------------------------------------------------

SHINGLE = 8


def words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    return re.findall(r"[\wäöüß]+", text)


def _h(gram: Iterable[str]) -> str:
    return hashlib.blake2b(" ".join(gram).encode("utf-8"), digest_size=8).hexdigest()


def shingles(tokens: list[str], n: int = SHINGLE) -> list[str]:
    return [_h(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


@dataclass
class CorpusIndex:
    hashes: set[str]
    fingerprint: str
    n: int = SHINGLE

    @classmethod
    def build(cls, texts: Iterable[str], n: int = SHINGLE) -> CorpusIndex:
        hashes: set[str] = set()
        for text in texts:
            hashes.update(shingles(words(text), n))
        fp = hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()
        return cls(hashes=hashes, fingerprint=fp, n=n)

    def save(self, directory: Path) -> Path:
        target = directory / self.fingerprint[:16]
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.json").write_text(
            json.dumps({"n": self.n, "fingerprint": self.fingerprint, "hashes": sorted(self.hashes)})
        )
        return target

    @classmethod
    def load(cls, path: Path) -> CorpusIndex:
        data = json.loads((path / "index.json").read_text())
        return cls(hashes=set(data["hashes"]), fingerprint=data["fingerprint"], n=data["n"])


def longest_overlap(text: str, index: CorpusIndex) -> tuple[int, int, int]:
    """(words, start word, end word) of the longest run of consecutive corpus words in `text`."""
    tokens = words(text)
    marks = [h in index.hashes for h in shingles(tokens, index.n)]
    best = (0, 0, 0)
    run_start = None
    for i, hit in enumerate(marks + [False]):
        if hit and run_start is None:
            run_start = i
        elif not hit and run_start is not None:
            length = (i - 1) - run_start + index.n
            if length > best[0]:
                best = (length, run_start, run_start + length)
            run_start = None
    return best


def overlap_spans(text: str, index: CorpusIndex, threshold: int) -> list[tuple[int, int]]:
    """All word spans of at least `threshold` consecutive corpus words."""
    tokens = words(text)
    marks = [h in index.hashes for h in shingles(tokens, index.n)]
    spans, run_start = [], None
    for i, hit in enumerate(marks + [False]):
        if hit and run_start is None:
            run_start = i
        elif not hit and run_start is not None:
            length = (i - 1) - run_start + index.n
            if length >= threshold:
                spans.append((run_start, run_start + length))
            run_start = None
    return spans
