"""Create snapshots: fetch a URL once, or register a manually obtained file.

Each snapshot directory holds raw.<ext> (never modified), text.txt (derived) and source.yaml
(SourceSnapshot fields).
"""

from __future__ import annotations

import hashlib
import io
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
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


# Post bodies of forum software, by XPath. Quoted earlier posts are removed (their text is
# already in the thread), and author names stay out of the text.
FORUM_POSTS = (
    ("phpbb", "//div[@class='content'][ancestor::div[starts-with(@id, 'post_content') or "
              "starts-with(@id, 'p')]]"),
    ("mylittleforum", "//div[@class='thread-posting']//div[@class='body']"),
    ("phpbb-postbody", "//div[contains(concat(' ', normalize-space(@class), ' '), ' postbody ')]"
                       "//div[@class='content']"),
    ("woltlab", "//div[contains(concat(' ', normalize-space(@class), ' '), ' messageText ')]"),
    ("vbulletin5", "//div[contains(concat(' ', normalize-space(@class), ' '), "
                   "' js-post__content-text ')]"),
    # Consultation portals (Baden-Württemberg Beteiligungsportal): comments only, not the bill.
    ("comment-list", "//*[contains(concat(' ', normalize-space(@class), ' '), ' comment__text ')]"),
)
QUOTE_XPATH = (".//blockquote | .//div[contains(@class, 'quote')] | .//cite"
               " | .//span[@class='citation']")
# Never part of a post's text: signatures can carry names and links.
DROP_XPATH = ".//div[contains(@class, 'signature')]"
MIN_FORUM_POSTS = 2


def _post_text(node) -> str:
    for br in node.xpath(".//br"):
        br.tail = "\n" + (br.tail or "")
    lines = (" ".join(line.split()) for line in node.text_content().splitlines())
    return "\n".join(line for line in lines if line).strip()


def _key(text: str) -> str:
    return " ".join(text.split())[:200]


def forum_posts(html_text: str) -> str | None:
    """The thread's post texts, one block per post, if the page is a known forum layout.

    A quote is dropped when its text is already in another post of the page (a reply quoting an
    earlier post); a quote of something not on the page (for example an e-mail) is kept.
    """
    import copy

    import lxml.html

    try:
        tree = lxml.html.fromstring(html_text)
    except (ValueError, lxml.etree.ParserError):
        return None
    for _name, xpath in FORUM_POSTS:
        posts = tree.xpath(xpath)
        if len(posts) < MIN_FORUM_POSTS:
            continue
        for post in posts:
            for node in post.xpath(DROP_XPATH):
                node.drop_tree()
        own = []
        for post in posts:
            bare = copy.deepcopy(post)
            for quote in bare.xpath(QUOTE_XPATH):
                quote.drop_tree()
            own.append(_key(_post_text(bare)))
        texts = []
        for n, post in enumerate(posts):
            others = " ".join(k for m, k in enumerate(own) if m != n)
            for quote in post.xpath(QUOTE_XPATH):
                if quote.getparent() is None:
                    continue
                body = copy.deepcopy(quote)
                for cite in body.xpath(".//cite"):
                    cite.drop_tree()  # "alice wrote:" is not part of the quoted text
                quoted = _key(_post_text(body))[:80]
                if not quoted or quoted in others or quote.tag == "cite":
                    quote.drop_tree()
            text = _post_text(post)
            if text:
                texts.append(text)
        texts = _drop_previews(texts)
        if len(texts) >= MIN_FORUM_POSTS:
            return "\n\n".join(texts)
    return None


_PREVIEW_END = re.compile(r"\s*(?:\[…\]|\[\.\.\.\]|…)?\s*(?:Weiterlesen|Read more|Mehr anzeigen)\s*$")


_TOGGLE = re.compile(r"^.*?(?:\[…\]|…)\s*\n(?:Weiterlesen|Read more)\n(.*?)\n?"
                     r"(?:Einklappen|Show less)?$", re.S)


def _drop_previews(texts: list[str]) -> list[str]:
    """Drop truncated previews ("… Weiterlesen") and texts repeated verbatim (moderation
    notices). A post holding preview and full text keeps only the full text."""
    texts = [m.group(1).strip() if (m := _TOGGLE.match(t)) else t for t in texts]
    counts: dict[str, int] = {}
    for text in texts:
        counts[_key(text)] = counts.get(_key(text), 0) + 1
    texts = [t for t in texts if counts[_key(t)] == 1]
    kept = []
    for n, text in enumerate(texts):
        if _PREVIEW_END.search(text):
            stem = _key(_PREVIEW_END.sub("", text).rstrip(" .…[]"))[:60]
            if any(m != n and _key(other).startswith(stem) for m, other in enumerate(texts)):
                continue
        kept.append(text)
    return kept


def docx_text(raw: bytes) -> str:
    """Paragraph texts of a .docx file (standard library only)."""
    import zipfile
    from xml.etree import ElementTree

    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    paragraphs = ("".join(t.text or "" for t in p.iter(f"{ns}t")).strip()
                  for p in root.iter(f"{ns}p"))
    return "\n\n".join(p for p in paragraphs if p).strip()


def extract_text(raw: bytes, ext: str) -> str:
    if ext == "docx":
        return docx_text(raw)
    if ext == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if ext == "xml":
        from xml.etree import ElementTree

        def local(tag: object) -> str:
            return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""

        root = ElementTree.fromstring(raw)
        # JATS (<body>) and Akoma Ntoso parliamentary records (<debateBody>), with or without
        # XML namespaces; paragraphs are <p>.
        body = next((e for e in root.iter() if local(e.tag) in ("body", "debateBody")), root)
        parts = [" ".join(p.itertext()).strip() for p in body.iter() if local(p.tag) == "p"]
        return "\n\n".join(p for p in parts if p).strip()
    if ext in {"html", "htm"}:
        import trafilatura

        html_text = raw.decode("utf-8", errors="replace")
        posts = forum_posts(html_text)
        if posts:
            return posts
        text = trafilatura.extract(html_text, include_comments=True)
        return (text or "").strip()
    if ext == "json":
        for extract in (regulations_comment, lemmy_comments, embedded_document):
            text = extract(raw)
            if text is not None:
                return text
    return raw.decode("utf-8", errors="replace").strip()


def regulations_comment(raw: bytes) -> str | None:
    """The comment text of a regulations.gov API v4 comment document (no submitter name)."""
    import html
    import json
    import re

    try:
        doc = json.loads(raw)
        comment = doc["data"]["attributes"]["comment"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(comment, str):
        return None
    text = re.sub(r"<br\s*/?>|</p>", "\n", comment, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line).strip()


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


def robots_allows(robots_txt: str, url: str, agent: str = USER_AGENT) -> bool:
    """RFC 9309 matching: the group for our agent (else `*`), `*` and `$` wildcards, the longest
    matching rule wins, and Allow wins a tie. (urllib.robotparser knows no wildcards and uses the
    first match, so it wrongly blocks paths such as Zenodo's `Allow: /api/records/*/files`.)"""
    import re

    parts = urlsplit(url)
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []
    for raw_line in robots_txt.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif key in ("allow", "disallow") and agents:
            rules.append((key, value))
    if agents:
        groups.append((agents, rules))
    token = agent.split("/")[0].lower()
    chosen = [r for a, r in groups if any(x != "*" and x in token for x in a)]
    if not chosen:
        chosen = [r for a, r in groups if "*" in a]
    best: tuple[int, bool] | None = None
    for key, pattern in (rule for group in chosen for rule in group):
        if not pattern:
            continue  # an empty Disallow allows everything
        regex = "^" + re.escape(pattern).replace(r"\*", ".*")
        if regex.endswith(r"\$"):
            regex = regex[:-2] + "$"
        if re.match(regex, path):
            candidate = (len(pattern), key == "allow")
            if best is None or candidate > best:
                best = candidate
    return True if best is None else best[1]


def _robots_allows(url: str) -> bool:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        response = httpx.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=20,
                             follow_redirects=True)
    except httpx.HTTPError:
        return True
    if response.status_code >= 400:
        return True
    return robots_allows(response.text, url)


def _ext_for(content_type: str, url: str) -> str:
    content_type = content_type.lower()
    if "wordprocessingml" in content_type or ".docx" in url.lower():
        return "docx"
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


def lemmy_comments(raw: bytes) -> str | None:
    """Post title, post body and comment texts of a Lemmy API v3 comment list, in thread order.

    Author names, deleted and removed comments are left out; Markdown quotes ("> ...") of other
    comments are dropped.
    """
    import json

    try:
        doc = json.loads(raw)
        views = doc["comments"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(views, list) or not views or "comment" not in views[0]:
        return None
    post = views[0].get("post") or {}
    parts = [post.get("name") or "", post.get("body") or ""]
    for view in sorted(views, key=lambda v: v["comment"].get("path", "")):
        comment = view["comment"]
        if comment.get("deleted") or comment.get("removed"):
            continue
        lines = [line for line in (comment.get("content") or "").splitlines()
                 if not line.lstrip().startswith(">")]
        parts.append("\n".join(" ".join(line.split()) for line in lines if line.strip()))
    return "\n\n".join(part.strip() for part in parts if part.strip())


def embedded_document(raw: bytes) -> str | None:
    """A document delivered base64-encoded inside JSON (UK Parliament Committees API:
    `{"data": "<base64 HTML>", "fileDataFormat": ...}`), extracted like the file itself."""
    import base64
    import json

    try:
        doc = json.loads(raw)
        payload = base64.b64decode(doc["data"], validate=True)
    except (ValueError, KeyError, TypeError):
        return None
    name = str(doc.get("fileName") or "")
    kind = "pdf" if payload[:4] == b"%PDF" or name.lower().endswith(".pdf") else "html"
    return extract_text(payload, kind)
