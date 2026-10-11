"""Podcast Index harvester: podcast feeds (research R6, scale-up set).

Searches https://api.podcastindex.org/api/1.0/search/byterm with the subdomain terms of each scope
language (free key and secret: PODCASTINDEX_API_KEY, PODCASTINDEX_API_SECRET). One feed is one
`collection`. Metadata only: no episode audio is fetched. Authentication follows the official
docs (https://podcastindex-org.github.io/docs-api/): `X-Auth-Key`, `X-Auth-Date` (UTC unix time,
whole seconds), `Authorization` = lower-case hex SHA-1 of key + secret + date, and a User-Agent
naming the product (the project crawler agent of `base.harvest`).

Podcasters are often private persons: the publisher keeps only the name needed for attribution
(kind `individual` unless the name reads as an organisation); e-mail addresses and links are
removed from it. Feed descriptions are never stored (FR-032).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlencode

from mobility_model_zoo.catalog.harvest import base
from mobility_model_zoo.catalog.model import vocab
from mobility_model_zoo.release.errors import CredentialError

API = "https://api.podcastindex.org/api/1.0"
PAGE = "https://podcastindex.org/podcast/"
MAX_RESULTS = 100  # per search request (the API allows 1-1000)
now = time.time  # replaced in tests

PODCAST_MEDIA = {"", "podcast"}  # podcast:medium values kept; music, video, film, audiobook, … are not
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
LINK = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
# Name cues for a kind of source other than `individual` (first match wins).
KIND_CUES: list[tuple[str, re.Pattern[str]]] = [
    (
        "government",
        re.compile(
            r"\b(?:ayuntamiento|ministerio|gobierno|government|ministry|city of|municipality|"
            r"consejer[ií]a|generalitat|junta de|diputaci[oó]n|urz[aą]d|ministerstwo|gmina|"
            r"agency|agencia)\b",
            re.I,
        ),
    ),
    (
        "research",
        re.compile(
            r"\b(?:universi(?:ty|dad|dade|tat|t[aä]t)|uniwersytet|institut[eo]?|instytut|csic|research|"
            r"politécnica|polit[eé]cnica|college|laborator(?:y|io))\b",
            re.I,
        ),
    ),
    (
        "media",
        re.compile(
            r"\b(?:radio|tv|fm|media|news|noticias|peri[oó]dico|diario|magazine|revista|network|studios?|"
            r"producciones|productions|broadcast(?:ing)?|channel|canal|podcasts?|ivoox|onda)\b",
            re.I,
        ),
    ),
    (
        "association",
        re.compile(
            r"\b(?:asociaci[oó]n|association|fundaci[oó]n|foundation|stowarzyszenie|fundacja|club|"
            r"colectivo|federaci[oó]n|federation|ngo|coalition|plataforma)\b",
            re.I,
        ),
    ),
    (
        "company",
        re.compile(
            r"\bS\.\s?[AL]\.|\bS\.L\.U\.|\bsp\. z o\.o|"
            r"\b(?:inc|ltd|llc|gmbh|corp(?:oration)?|company|empresa|group|grupo|consulting)\b",
            re.I,
        ),
    ),
]


def auth_headers(key: str, secret: str, at: float | None = None) -> dict[str, str]:
    stamp = str(int(now() if at is None else at))
    digest = hashlib.sha1((key + secret + stamp).encode("utf-8")).hexdigest()  # noqa: S324 (API contract)
    return {"X-Auth-Key": key, "X-Auth-Date": stamp, "Authorization": digest}


def publisher(feed: dict[str, Any]) -> tuple[str, str]:
    """(name for attribution, kind of source); never an e-mail address or a link."""
    for raw in (feed.get("author"), feed.get("ownerName")):
        name = LINK.sub(" ", EMAIL.sub(" ", str(raw or "")))
        name = re.sub(r"[()<>\[\]]", " ", name)
        name = re.sub(r"\s+", " ", name).strip(" ,;:-|")
        if len(name) >= 2:
            for kind, cue in KIND_CUES:
                if cue.search(name):
                    return name, kind
            return name, "individual"
    return "unknown publisher", "individual"


def area(language_tag: str | None) -> str:
    """Country of a language tag such as es-ES or pt-br when it is a known area, else `001`."""
    parts = re.split(r"[-_]", str(language_tag or "").strip())
    if len(parts) >= 2 and len(parts[-1]) == 2 and parts[-1].upper() in vocab().areas:
        return parts[-1].upper()
    return "001"


def http_url(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if re.match(r"^https?://\S+$", text) else None


def iso_day(stamp: Any) -> str | None:
    if not isinstance(stamp, int | float) or stamp <= 0:
        return None
    return dt.datetime.fromtimestamp(stamp, dt.UTC).date().isoformat()


class PodcastIndex:
    name = "podcast-index"
    catalogue = "Podcast Index"
    env_keys = ("PODCASTINDEX_API_KEY", "PODCASTINDEX_API_SECRET")
    modalities = ("audio",)
    method = (
        "Podcast Index API search/byterm (clean) with the subdomain terms per language; one feed per "
        "entry, kept when the feed language matches the scope; metadata only, no episodes"
    )

    def search(self, ctx: base.Context, term: str) -> list[dict[str, Any]]:
        # `clean` is a flag without a value (docs: "Parameter shall not have a value").
        url = f"{API}/search/byterm?{urlencode({'q': term, 'max': MAX_RESULTS})}&clean"
        headers = auth_headers(ctx.env["PODCASTINDEX_API_KEY"], ctx.env["PODCASTINDEX_API_SECRET"])
        response = ctx.client.get(url, headers=headers)
        if response.status_code in (401, 403):
            raise CredentialError(
                "Podcast Index rejected PODCASTINDEX_API_KEY/PODCASTINDEX_API_SECRET "
                f"(HTTP {response.status_code})"
            )
        response.raise_for_status()
        data = response.json()
        if str(data.get("status", "true")).lower() != "true":
            raise RuntimeError(f"Podcast Index error: {str(data.get('description', ''))[:200]}")
        return list(data.get("feeds") or [])

    def to_candidate(self, feed: dict[str, Any], subdomain: str) -> dict[str, Any] | None:
        feed_url = http_url(feed.get("url"))
        title = str(feed.get("title") or "").strip()
        if not feed_url or not title or feed.get("id") is None:
            return None
        page = f"{PAGE}{feed['id']}"
        name, kind = publisher(feed)
        # The documented API exposes no podcast:license field; take one if a future version adds it.
        lic = base.spdx(feed.get("license")) if feed.get("license") else "unknown"
        content: dict[str, Any] = {"transcripts": {"available": "unknown"}, "frequency": "IRREG"}
        if isinstance(feed.get("episodeCount"), int) and feed["episodeCount"] >= 0:
            content["volume"] = {"items": feed["episodeCount"]}
        newest = iso_day(feed.get("newestItemPubdate"))
        if newest:
            content["updated"] = newest
        other = [f"podcastindex:{feed['id']}"]
        if feed.get("podcastGuid"):
            other.append(f"podcast-guid:{str(feed['podcastGuid']).lower()}")
        if feed.get("itunesId"):
            other.append(f"itunes:{feed['itunesId']}")
        return base.candidate(
            self,
            title=title,
            title_en=None,
            languages=[str(feed.get("language") or "")],
            area=area(feed.get("language")),
            publisher=name,
            kind=kind,
            landing_url=http_url(feed.get("link")) or page,
            modality="audio",
            genre="podcast",
            subdomains=[subdomain],
            licence=base.licence_block(lic, None, page),
            access=[
                {
                    "method": "feed",
                    "url": feed_url,
                    "download_url": None,
                    "auth": "none",
                    "cost": "free",
                    "formats": [
                        "application/atom+xml" if feed.get("type") == 1 else "application/rss+xml"
                    ],
                    "provider_hint": "url",
                }
            ],
            evidence=[page],
            content=content,
            identifiers={"other": other},
        )

    def iterate(self, scope: base.Scope, ctx: base.Context) -> Iterator[dict[str, Any]]:
        if scope.modalities and "audio" not in scope.modalities:
            return
        languages: list[str | None] = list(scope.languages) or [None]
        plan = [
            (lang, sub, term)
            for lang in languages
            for sub in base.subdomains_for(scope)
            for term in base.search_terms(sub, lang)
        ]
        quota = max(1, math.ceil(ctx.limit / max(1, len(plan))))
        seen: dict[Any, dict[str, Any]] = {}
        for lang, sub, term in plan:
            taken = 0
            for feed in self.search(ctx, term):
                if taken >= quota:
                    break
                if feed.get("id") in seen:  # found again with another subdomain's terms (FR-003)
                    if sub not in seen[feed["id"]]["subdomains"]:
                        seen[feed["id"]]["subdomains"].append(sub)
                    continue
                if feed.get("dead") or str(feed.get("medium") or "").lower() not in PODCAST_MEDIA:
                    continue
                if lang and base.language_code(feed.get("language")) != lang:
                    continue  # the search is not language-bound; keep the scope's cells clean
                cand = self.to_candidate(feed, sub)
                if cand is None:
                    continue
                seen[feed["id"]] = cand
                taken += 1
                yield cand
            ctx.say(f"{self.name}: {lang or 'any'} {sub} {term!r}: {taken}")
