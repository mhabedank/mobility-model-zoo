"""Create snapshots: fetch a URL once, or register a manually obtained file.

Each snapshot directory holds raw.<ext> (never modified), text.txt (derived) and source.yaml
(SourceSnapshot fields).
"""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import robotparser
from urllib.parse import urlsplit

import httpx

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_yaml, write_yaml
from mobility_model_zoo.productdev.jtbd.schema import SourceSnapshot
from mobility_model_zoo.productdev.jtbd.sources import registry

USER_AGENT = "jtbd-pilot/0.1 (non-commercial research; crawl-once)"
MIN_TEXT_CHARS = 1500
BLOCK_MARKERS = (
    "checking your browser",
    "recaptcha",
    "enable javascript",
    "{{res.",
    "access denied",
    "just a moment...",
)


def check_extracted(text: str) -> None:
    """Refuse bot-challenge pages and empty extractions so they never become snapshots."""
    head = text[:3000].lower()
    marker = next((m for m in BLOCK_MARKERS if m in head), None)
    if marker or len(text.strip()) < MIN_TEXT_CHARS:
        reason = f"block-page marker {marker!r}" if marker else f"only {len(text.strip())} chars"
        raise ValidationFailed(
            f"extracted text looks unusable ({reason}); nothing was stored. Download the document "
            "manually and use `jtbd source register`, or use an official API URL")


def extract_text(raw: bytes, ext: str) -> str:
    if ext == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if ext == "xml":
        from xml.etree import ElementTree

        root = ElementTree.fromstring(raw)
        body = root.find(".//body")
        parts = [" ".join(p.itertext()).strip() for p in (body if body is not None else root).iter("p")]
        return "\n\n".join(p for p in parts if p).strip()
    if ext in {"html", "htm"}:
        import trafilatura

        text = trafilatura.extract(raw.decode("utf-8", errors="replace"), include_comments=True)
        return (text or "").strip()
    return raw.decode("utf-8", errors="replace").strip()


def create_snapshot(
    settings: Settings,
    raw: bytes,
    ext: str,
    url: str,
    meta: dict[str, Any],
    *,
    update: bool = False,
    reason: str | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    supersedes = registry.check_can_fetch(settings, url, update, reason)
    if meta.get("source_type") == "reddit" and meta.get("permitted_uses") != "benchmark_only":
        raise ValidationFailed("Reddit content is always permitted_uses=benchmark_only")
    sha = hashlib.sha256(raw).hexdigest()
    snapshot_id = f"snap-{sha[:12]}"
    directory = settings.snapshots_dir / snapshot_id
    if directory.exists():
        raise ValidationFailed(f"snapshot {snapshot_id} already exists with identical content")
    extracted = text if text is not None else extract_text(raw, ext)
    check_extracted(extracted)
    retrieved_at = datetime.now(UTC).isoformat()
    record = SourceSnapshot.model_validate(
        {
            "snapshot_id": snapshot_id,
            "origin_url": url,
            "retrieved_at": retrieved_at,
            "raw_path": f"snapshots/{snapshot_id}/raw.{ext}",
            "text_path": f"snapshots/{snapshot_id}/text.txt",
            "raw_sha256": sha,
            "supersedes": supersedes,
            "update_reason": reason if supersedes else None,
            **meta,
        }
    )
    directory.mkdir(parents=True)
    (directory / f"raw.{ext}").write_bytes(raw)
    (directory / "text.txt").write_text(extracted, encoding="utf-8")
    write_yaml(directory / "source.yaml", record.model_dump(mode="json"))
    registry.register(settings, snapshot_id, url, retrieved_at, supersedes)
    return record.model_dump(mode="json")


def _robots_allows(url: str) -> bool:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    parser = robotparser.RobotFileParser()
    try:
        response = httpx.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=20,
                             follow_redirects=True)
    except httpx.HTTPError:
        return True
    if response.status_code >= 400:
        return True
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def _ext_for(content_type: str, url: str) -> str:
    content_type = content_type.lower()
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        return "pdf"
    if "html" in content_type:
        return "html"
    if "json" in content_type:
        return "json"
    if "xml" in content_type:
        return "xml"
    return "txt"


def fetch_url(
    settings: Settings, url: str, meta: dict[str, Any], *, update: bool = False,
    reason: str | None = None
) -> dict[str, Any]:
    if meta.get("source_type") == "reddit":
        raise UsageError("Reddit threads must be fetched with `jtbd source reddit` (official API)")
    registry.check_can_fetch(settings, url, update, reason)
    if not _robots_allows(url):
        raise ValidationFailed(f"robots.txt disallows fetching {url}")
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)
    if response.status_code >= 400:
        raise ValidationFailed(f"fetch failed with HTTP {response.status_code}: {url}")
    ext = _ext_for(response.headers.get("content-type", ""), url)
    return create_snapshot(settings, response.content, ext, url, meta, update=update, reason=reason)


def register_file(
    settings: Settings, path: Path, url: str, meta: dict[str, Any], *, update: bool = False,
    reason: str | None = None
) -> dict[str, Any]:
    if not path.exists():
        raise UsageError(f"file not found: {path}")
    ext = path.suffix.lstrip(".").lower() or "txt"
    return create_snapshot(settings, path.read_bytes(), ext, url, meta, update=update,
                           reason=reason)


def load_snapshot(settings: Settings, snapshot_id: str) -> SourceSnapshot:
    path = settings.snapshots_dir / snapshot_id / "source.yaml"
    if not path.exists():
        raise ValidationFailed(f"unknown snapshot {snapshot_id}")
    return SourceSnapshot.model_validate(read_yaml(path))


def snapshot_text(settings: Settings, snapshot_id: str) -> str:
    return (settings.snapshots_dir / snapshot_id / "text.txt").read_text(encoding="utf-8")


def list_snapshots(settings: Settings, permitted_uses: str | None = None) -> list[dict[str, Any]]:
    out = []
    for entry in registry.entries(settings):
        snap = load_snapshot(settings, entry["snapshot_id"])
        if permitted_uses and snap.permitted_uses != permitted_uses:
            continue
        out.append(
            {
                "snapshot_id": snap.snapshot_id,
                "origin_url": snap.origin_url,
                "source_type": snap.source_type,
                "permitted_uses": snap.permitted_uses,
                "retention_until": str(snap.retention_until),
                "supersedes": snap.supersedes,
            }
        )
    return out
