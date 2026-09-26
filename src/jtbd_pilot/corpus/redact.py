"""Removal of usernames and direct identifiers before labeling (FR-012, research.md R7).

Pattern-based redaction is followed by a manual review of every chunk (`mark-reviewed`) and a hard
check (`redact-check`) before freezing.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.corpus.store import load_chunks, save_chunk
from jtbd_pilot.errors import UsageError, ValidationFailed

PATTERNS_VERSION = "redact-v2"

# Order matters: profile URLs before emails before bare handles.
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "profile_url",
        re.compile(
            r"https?://(?:[a-z]+\.)?(?:reddit\.com/(?:u|user)|facebook\.com|twitter\.com|x\.com|"
            r"instagram\.com|linkedin\.com/in|mastodon\.[a-z.]+/@)[^\s)\]>]*",
            re.IGNORECASE,
        ),
        "[PROFILE_URL]",
    ),
    # PDF extraction can insert spaces around dots ("name@dlr .de"), so they are tolerated.
    (
        "email",
        re.compile(r"[A-Za-z0-9._%+-]+\s?@\s?[A-Za-z0-9-]+"
                   r"(?:\s?\.\s?[A-Za-z0-9-]+)*\s?\.\s?[A-Za-z]{2,}\b"),
        "[EMAIL]",
    ),
    ("reddit_user", re.compile(r"(?<![\w/])/?u/[A-Za-z0-9_-]{3,20}\b"), "[USER]"),
    ("at_handle", re.compile(r"(?<![\w.@\[])@[A-Za-z0-9_.]{2,30}\b"), "[USER]"),
    (
        "phone_labeled",
        re.compile(
            r"(?i)\b(?:tel|telefon|phone|fon|mobil|handy)\.?:?\s*[+\d][\d\s/().-]{6,}\d"
        ),
        "[PHONE]",
    ),
    (
        "phone_international",
        re.compile(r"(?<![\w+])(?:\+|00)\d{1,3}[\s./-]?(?:\(?\d{1,5}\)?[\s./-]?){2,5}\d{2,}"),
        "[PHONE]",
    ),
]


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for name, pattern, placeholder in PATTERNS:
        text, n = pattern.subn(placeholder, text)
        if n:
            counts[name] = counts.get(name, 0) + n
    return text, counts


def residual_patterns(text: str) -> list[str]:
    return [name for name, pattern, _ in PATTERNS if pattern.search(text)]


def redact_all(settings: Settings) -> dict[str, Any]:
    totals: dict[str, int] = {}
    changed = []
    for chunk in load_chunks(settings):
        new_text, counts = redact_text(chunk.text)
        chunk.redaction.patterns_version = PATTERNS_VERSION
        if new_text != chunk.text:
            chunk.text = new_text
            chunk.redaction.check_passed = False
            changed.append(chunk.chunk_id)
        for key, value in counts.items():
            totals[key] = totals.get(key, 0) + value
        save_chunk(settings, chunk)
    return {"changed_chunks": changed, "replacements": totals}


def mark_reviewed(settings: Settings, chunk_ids: list[str], all_chunks: bool) -> dict[str, Any]:
    if not chunk_ids and not all_chunks:
        raise UsageError("give chunk ids or --all")
    now = datetime.now(UTC)
    marked = []
    for chunk in load_chunks(settings):
        if all_chunks or chunk.chunk_id in chunk_ids:
            chunk.redaction.manual_review_at = now
            save_chunk(settings, chunk)
            marked.append(chunk.chunk_id)
    missing = sorted(set(chunk_ids) - set(marked))
    if missing:
        raise ValidationFailed(f"unknown chunk ids: {missing}")
    return {"marked": marked}


def redact_check(settings: Settings) -> dict[str, Any]:
    failures = []
    chunks = load_chunks(settings)
    for chunk in chunks:
        problems = residual_patterns(chunk.text)
        if chunk.redaction.manual_review_at is None:
            problems.append("no_manual_review")
        chunk.redaction.check_passed = not problems
        save_chunk(settings, chunk)
        if problems:
            failures.append({"chunk_id": chunk.chunk_id, "problems": problems})
    if failures:
        raise ValidationFailed(f"redact-check failed for {len(failures)} chunk(s): {failures}")
    return {"checked": len(chunks), "passed": len(chunks)}
