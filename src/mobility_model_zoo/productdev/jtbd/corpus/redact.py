"""Removal of usernames and direct identifiers before labeling (FR-012, research.md R7).

Pattern-based redaction is followed by a manual review of every chunk (`mark-reviewed`) and a hard
check (`redact-check`) before freezing.

Training datasets (feature 004, research R4, config `span_train.redaction.review: sampled`) add an
automated identifier scan of every chunk and review by hand a stratified sample plus every chunk of
an always-review source type (`review-sample`). The pilot keeps full review.
"""

from __future__ import annotations

import math
import random
import re
from datetime import UTC, datetime
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks, save_chunk
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json

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


# Scan only (sampled review): identifiers the redaction patterns do not replace, such as links to
# user pages. A hit fails `redact-check` and must be fixed by hand.
SCAN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("user_path_url", re.compile(
        r"https?://\S+?/(?:u|user|users|profile|profiles|member|members|people|author)/[^\s/)\]>]+"
        r"|https?://\S+?/~[A-Za-z0-9_.-]+", re.IGNORECASE)),
]


def identifier_scan(text: str) -> list[str]:
    """Every pattern hit: residual redaction patterns plus the scan-only patterns."""
    return residual_patterns(text) + [name for name, pattern in SCAN_PATTERNS
                                      if pattern.search(text)]


def sample_path(settings: Settings):
    return settings.chunks_dir / "review-sample.json"


def review_sample(settings: Settings, seed: int) -> dict[str, Any]:
    """Draw the manual-review sample once: a stratified share (language x source type) plus
    every chunk of an always-review source type. Redrawing is refused."""
    if settings.redaction_review != "sampled":
        raise UsageError("review-sample needs span_train.redaction.review: sampled in the config")
    path = sample_path(settings)
    if path.exists():
        raise ValidationFailed(f"the review sample was already drawn ({path}); it is not redrawn")
    policy = settings.span_train["redaction"].get("sample") or {}
    fraction, minimum = float(policy.get("fraction", 0.10)), int(policy.get("min", 100))
    always = set(policy.get("always_review_source_types") or [])
    chunks = load_chunks(settings)
    if not chunks:
        raise ValidationFailed("no chunks to sample")
    forced = sorted(c.chunk_id for c in chunks if c.source_type in always)
    rng = random.Random(seed)
    strata: dict[tuple[str, str], list[str]] = {}
    for chunk in chunks:
        strata.setdefault((chunk.language, chunk.source_type), []).append(chunk.chunk_id)
    for ids in strata.values():
        rng.shuffle(ids)
    wanted = min(len(chunks), max(minimum, math.ceil(fraction * len(chunks))))
    sampled: list[str] = []
    order = sorted(strata)
    while len(sampled) < wanted:
        for key in order:
            if strata[key] and len(sampled) < wanted:
                sampled.append(strata[key].pop())
    record = {"seed": seed, "drawn_at": datetime.now(UTC).isoformat(), "fraction": fraction,
              "min": minimum, "always_review_source_types": sorted(always),
              "sampled": sorted(sampled), "always_review": forced,
              "chunk_ids": sorted(set(sampled) | set(forced))}
    write_json(path, record)
    return {"chunks": len(chunks), "sampled": len(sampled), "always_review": len(forced),
            "to_review": len(record["chunk_ids"]), "path": str(path)}


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
    mode = settings.redaction_review
    sampled = mode == "sampled"
    to_review: set[str] | None = None
    if sampled:
        if not sample_path(settings).exists():
            raise ValidationFailed("draw the manual-review sample first: `jtbd corpus "
                                   "review-sample --seed <n>`")
        to_review = set(read_json(sample_path(settings))["chunk_ids"])
    for chunk in chunks:
        problems = (residual_patterns(chunk.text) if mode == "full"
                    else identifier_scan(chunk.text))
        if mode == "model":
            if chunk.redaction.model_review_at is None:
                problems.append("no_model_review")
        else:
            needs_review = to_review is None or chunk.chunk_id in to_review
            if needs_review and chunk.redaction.manual_review_at is None:
                problems.append("no_manual_review")
        chunk.redaction.check_passed = not problems
        save_chunk(settings, chunk)
        if problems:
            failures.append({"chunk_id": chunk.chunk_id, "problems": problems})
    if failures:
        raise ValidationFailed(f"redact-check failed for {len(failures)} chunk(s): {failures}")
    result = {"checked": len(chunks), "passed": len(chunks)}
    if to_review is not None:
        result["reviewed_by_hand"] = len(to_review)
    return result
