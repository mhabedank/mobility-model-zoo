"""Fetch a Reddit thread through the official Reddit Data API (research.md R2).

Reddit text is always benchmark_only. Thread IDs may be found with Arctic Shift search, but text is
never downloaded from Arctic Shift. Author names are not written to the extracted text
(data minimization); the raw API response is kept unmodified as the snapshot.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from jtbd_pilot.config import Settings
from jtbd_pilot.errors import UsageError, ValidationFailed
from jtbd_pilot.sources.snapshot import create_snapshot

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
MIN_INTERVAL_S = 0.6  # stays below 100 queries per minute
LEGAL_BASIS = "§ 60d UrhG, Reddit Data API (Reddit for Researchers)"

_last_call = 0.0


def _pace() -> None:
    global _last_call
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def _token(client: httpx.Client, user_agent: str) -> str:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not secret:
        raise UsageError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set (see .env.example)")
    _pace()
    response = client.post(
        TOKEN_URL,
        auth=(client_id, secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": user_agent},
    )
    if response.status_code != 200:
        raise ValidationFailed(f"Reddit token request failed: HTTP {response.status_code}")
    return response.json()["access_token"]


def flatten_thread(listing: list[dict[str, Any]]) -> str:
    """Post and comment tree as plain text, without author names; ids mark reply structure."""
    post = listing[0]["data"]["children"][0]["data"]
    lines = [f"[post t3_{post['id']}] {post.get('title', '').strip()}"]
    if post.get("selftext"):
        lines.append(post["selftext"].strip())

    def walk(children: list[dict[str, Any]], depth: int) -> None:
        for child in children:
            if child.get("kind") != "t1":
                continue
            data = child["data"]
            body = (data.get("body") or "").strip()
            if body and body not in {"[deleted]", "[removed]"}:
                marker = f"[comment t1_{data['id']} reply-to {data['parent_id']}]"
                lines.append(f"\n{'  ' * depth}{marker}")
                lines.append("\n".join(f"{'  ' * depth}{line}" for line in body.splitlines()))
            replies = data.get("replies")
            if isinstance(replies, dict):
                walk(replies["data"]["children"], depth + 1)

    walk(listing[1]["data"]["children"], 0)
    return "\n".join(lines).strip()


def fetch_thread(
    settings: Settings,
    thread_id: str,
    retention_until: str,
    *,
    update: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    thread_id = thread_id.removeprefix("t3_")
    url = f"https://www.reddit.com/comments/{thread_id}"
    user_agent = os.environ.get("REDDIT_USER_AGENT", "jtbd-pilot/0.1 (research)")
    with httpx.Client(timeout=60) as client:
        token = _token(client, user_agent)
        _pace()
        response = client.get(
            f"{API}/comments/{thread_id}",
            params={"limit": 500, "raw_json": 1},
            headers={"Authorization": f"bearer {token}", "User-Agent": user_agent},
        )
    if response.status_code != 200:
        raise ValidationFailed(f"Reddit API returned HTTP {response.status_code} for {thread_id}")
    listing = response.json()
    meta = {
        "source_type": "reddit",
        "license": "Reddit User Content (Reddit Data API Terms)",
        "legal_basis": LEGAL_BASIS,
        "access_terms_checked": "Reddit Data API Terms and Responsible Builder Policy; "
        "benchmark use only",
        "permitted_uses": "benchmark_only",
        "retention_until": retention_until,
    }
    raw = json.dumps(listing, ensure_ascii=False).encode("utf-8")
    return create_snapshot(settings, raw, "json", url, meta, update=update, reason=reason,
                           text=flatten_thread(listing))
