"""Filters over catalog entries (FR-025): AND across options, OR within one option."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def permitted_use(entry: dict[str, Any]) -> str:
    return (entry.get("usage") or {}).get("permitted_use", "undetermined")


def languages(entry: dict[str, Any], include_transcripts: bool = False) -> set[str]:
    codes = {lang["code"] for lang in entry.get("languages") or []}
    if include_transcripts:
        codes |= set(((entry.get("content") or {}).get("transcripts") or {}).get("languages") or [])
    return codes


def _any(values: Iterable[str] | None, have: set[str]) -> bool:
    values = [v for v in values or [] if v]
    return not values or bool(set(values) & have)


def select(
    entries: Iterable[dict[str, Any]],
    *,
    lang: list[str] | None = None,
    area: list[str] | None = None,
    modality: list[str] | None = None,
    genre: list[str] | None = None,
    kind: list[str] | None = None,
    topic: list[str] | None = None,
    subdomain: list[str] | None = None,
    status: list[str] | None = None,
    use: list[str] | None = None,
    transcripts: str | None = None,
    origin: list[str] | None = None,
    min_quality: int | None = None,
    include_transcripts: bool = False,
) -> list[dict[str, Any]]:
    out = []
    for e in entries:
        rtype = e.get("resource_type") or {}
        trans = ((e.get("content") or {}).get("transcripts") or {}).get("available", "unknown")
        checks = [
            _any(lang, languages(e, include_transcripts)),
            _any(area, {str(e.get("origin_area"))}),
            _any(modality, {rtype.get("modality")}),
            _any(genre, {rtype.get("genre")}),
            _any(kind, {(e.get("publisher") or {}).get("kind")}),
            _any(topic, set(e.get("topics") or [])),
            _any(subdomain, set(e.get("subdomains") or [])),
            _any(status, {(e.get("status") or {}).get("value")}),
            _any(use, {permitted_use(e)}),
            transcripts is None or trans == transcripts,
            _any(origin, {lang.get("origin") for lang in e.get("languages") or []}),
            min_quality is None or (e.get("quality") or {}).get("score", 0) >= min_quality,
        ]
        if all(checks):
            out.append(e)
    return sorted(out, key=lambda e: e["id"])
