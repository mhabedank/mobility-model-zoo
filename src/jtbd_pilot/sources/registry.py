"""Snapshot registry: enforces "crawl once" (FR-013a, constitution: Resources & Cost Discipline)."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from jtbd_pilot.config import Settings
from jtbd_pilot.errors import CrawlOnceRefused, UsageError
from jtbd_pilot.jsonio import append_jsonl, read_jsonl

TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    host = parts.hostname.lower() if parts.hostname else ""
    if parts.port and (scheme, parts.port) not in {("http", 80), ("https", 443)}:
        host = f"{host}:{parts.port}"
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    )
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def index_path(settings: Settings):
    return settings.snapshots_dir / "index.jsonl"


def entries(settings: Settings) -> list[dict]:
    return list(read_jsonl(index_path(settings)))


def latest_for(settings: Settings, url: str) -> dict | None:
    canonical = canonicalize_url(url)
    found = [e for e in entries(settings) if canonicalize_url(e["canonical_url"]) == canonical]
    return found[-1] if found else None


def check_can_fetch(settings: Settings, url: str, update: bool, reason: str | None) -> str | None:
    """Return the snapshot_id to supersede (update) or None. Raise if crawl once is violated."""
    existing = latest_for(settings, url)
    if existing and not update:
        raise CrawlOnceRefused(
            f"{canonicalize_url(url)} was already fetched as {existing['snapshot_id']}; "
            "use --update --reason <text> for a documented update"
        )
    if update:
        if not existing:
            raise UsageError(f"--update given but {url} has no snapshot yet")
        if not (reason and reason.strip()):
            raise UsageError("--update requires --reason")
        return existing["snapshot_id"]
    return None


def register(settings: Settings, snapshot_id: str, url: str, retrieved_at: str,
             supersedes: str | None) -> None:
    append_jsonl(
        index_path(settings),
        {
            "snapshot_id": snapshot_id,
            "canonical_url": canonicalize_url(url),
            "retrieved_at": retrieved_at,
            "supersedes": supersedes,
        },
    )
