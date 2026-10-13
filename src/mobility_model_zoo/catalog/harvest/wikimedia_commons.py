"""Wikimedia Commons harvester: photos, maps, charts and diagrams (research R6, scale-up set).

Searches the File namespace of the MediaWiki API (no key) with the subdomain terms of each scope
language and reads the licence per file from `extmetadata`. One file is one `item`. Metadata only:
the file itself is never downloaded. The uploader or author (`Artist`) is never requested or stored;
attribution is resolved at fetch time. `ImageDescription` is read only to recognise the language of
a map or graphic and is never stored (FR-032).

The API asks bots for `maxlag` and a descriptive User-Agent (Wikimedia User-Agent policy); the
client of `base.harvest` sends the project crawler agent and throttles to one request per second.
"""

from __future__ import annotations

import math
import re
import time
import unicodedata
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from mobility_model_zoo.catalog.harvest import base
from mobility_model_zoo.catalog.model import vocab

API = "https://commons.wikimedia.org/w/api.php"
FILE_PAGE = "https://commons.wikimedia.org/wiki/"
BATCH = 20  # files per request: small batches (Wikimedia API etiquette)
MAX_LAG_RETRIES = 3
MAX_WAIT_SECONDS = 10.0
sleep = time.sleep  # replaced in tests

# Commons licence short names that base.spdx() does not resolve (LicenseShortName, lower case).
# Public-domain marks on Commons are jurisdiction specific (PD-old, PD-user, PD-AR-Photo, …), so
# they are not mapped to CC0; US federal works get the allowlisted LicenseRef-US-PD.
COMMONS_LICENCES = {
    "public domain": "LicenseRef-public-domain",
    "public domain mark": "LicenseRef-public-domain",
    "pdm": "LicenseRef-public-domain",
    "cc0": "CC0-1.0",
    "gfdl": "GFDL-1.2-or-later",
    "gfdl 1.2": "GFDL-1.2-or-later",
    "gfdl 1.3": "GFDL-1.3-or-later",
    "attribution": "LicenseRef-Commons-Attribution",
    "copyrighted free use": "LicenseRef-Commons-copyrighted-free-use",
    "ogl 3": "LicenseRef-OGL-UK-3.0",
    "ogl v3.0": "LicenseRef-OGL-UK-3.0",
}
CC_NAME = re.compile(r"^cc[ -](by(?:-(?:sa|nc|nd))*)[ -](\d\.\d)\b", re.IGNORECASE)
US_GOV = re.compile(r"\bPD[- ]?US[- ]?Gov", re.IGNORECASE)
PUBLICDOMAIN_MARK = re.compile(r"creativecommons\.org/publicdomain/mark/", re.IGNORECASE)

# CirrusSearch file types per modality; charts and maps are bitmaps or drawings alike.
FILETYPES = {"image": "bitmap|drawing", "graphic": "bitmap|drawing", "video": "video", "audio": "audio"}

# Genre cues in titles and categories, checked in this order (first match wins).
GENRE_CUES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "graphic",
        "infographic",
        re.compile(r"\binfogr(?:aphics?|af[ií]as?|afika)\b|インフォグラフィック", re.I),
    ),
    (
        "graphic",
        "chart",
        re.compile(
            r"\b(?:charts?|graphs?|plots?|histograms?|gr[aá]fic[oa]s?|wykres[yu]?|diagrama de barras)\b"
            r"|グラフ|統計図",
            re.I,
        ),
    ),
    (
        "graphic",
        "diagram",
        re.compile(
            r"\b(?:diagrams?|diagramas?|schemat[yu]?|esquemas?|schematics?|flowcharts?)\b|ダイアグラム|図解",
            re.I,
        ),
    ),
    ("image", "map", re.compile(r"\b(?:maps?|mapas?|mapy?|plano de)\b|地図|路線図", re.I)),
]
# Category phrases that contain a cue word but describe photographs ("Patrimonio gráfico de …").
FALSE_CUES = re.compile(
    r"patrimonio gr[aá]fico|material gr[aá]fico|dise[nñ]o gr[aá]fico|photograph", re.I
)

STOPWORDS = {
    "es": {"el", "los", "las", "del", "y", "con", "para", "por", "una", "calle", "ciudad"},
    "pl": {"i", "w", "na", "oraz", "dla", "ze", "się", "ulica", "miasto"},
    "en": {"the", "and", "of", "with", "for", "street", "city"},
}
KANA = re.compile(r"[぀-ヿ]")
LANG_SUFFIX = re.compile(r"[-_(.]([a-z]{2,3}(?:-[a-z]{2,4})?)\)?$")  # "Diagram-es", "Map (es)" -> es
TAGS = re.compile(r"<[^>]+>")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def fold(text: str) -> str:
    """Lower case without accents, for matching only."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def file_title(page_title: str) -> tuple[str, str]:
    """(title without `File:` and extension, extension)."""
    name = page_title.split(":", 1)[1] if ":" in page_title else page_title
    stem, dot, ext = name.rpartition(".")
    return (stem if dot else name).replace("_", " ").strip(), (ext.lower() if dot else "")


def meta(info: dict[str, Any], key: str) -> str:
    value = ((info.get("extmetadata") or {}).get(key) or {}).get("value")
    return str(value) if value is not None else ""


def licence_id(short_name: str, url: str, categories: str) -> str:
    name = short_name.strip().lower()
    if name in ("public domain", "pdm", "public domain mark") or PUBLICDOMAIN_MARK.search(url):
        return "LicenseRef-US-PD" if US_GOV.search(categories) else "LicenseRef-public-domain"
    if name in COMMONS_LICENCES:
        return COMMONS_LICENCES[name]
    found = base.spdx(url) if url else "unknown"
    if found != "unknown":
        return found
    m = CC_NAME.match(name)
    if m:
        return f"CC-{m.group(1).upper()}-{m.group(2)}"
    return base.spdx(short_name)


def licence(short_name: str, url: str, categories: str, evidence: str) -> dict[str, Any]:
    lid = licence_id(short_name, url, categories)
    block = base.licence_block(lid, url or None, evidence)
    if lid.startswith("GFDL"):
        block |= {
            "attribution_required": "yes",
            "commercial_use": "yes",
            "share_alike": True,
            "derivatives": "yes",
        }
    elif lid == "LicenseRef-Commons-Attribution":
        block |= {"attribution_required": "yes"}
    return block


def classify(title: str, categories: str, mime: str) -> tuple[str, str]:
    """(modality, genre) from title, categories and MIME type; photo when nothing points elsewhere."""
    if mime.startswith("video/"):
        return "video", "footage"
    if mime.startswith("audio/"):
        return "audio", "field_recording"
    for text in (title, FALSE_CUES.sub(" ", categories)):
        for modality, genre, cue in GENRE_CUES:
            if cue.search(text):
                return modality, genre
    if mime == "image/svg+xml":
        return "graphic", "diagram"  # drawings without a cue: schematic graphics, not photographs
    return "image", "photo"


def detect_language(title: str, text: str, language: str | None, subdomain: str) -> str:
    """The search language when the title or description evidently uses it, else `und`."""
    suffix = LANG_SUFFIX.search(title.lower())
    if suffix and suffix.group(1) in vocab().languages:
        return suffix.group(1)
    if not language:
        return "und"
    if language == "ja":
        return "ja" if KANA.search(f"{title} {text}") else "und"
    folded = fold(f"{title} {text}")
    english = {fold(t) for t in base.search_terms(subdomain, "en")}
    for term in base.search_terms(subdomain, language):
        if fold(term) not in english and fold(term) in folded:
            return language
    words = set(WORD.findall(folded))
    if len(words & {fold(w) for w in STOPWORDS.get(language, set())}) >= 2:
        return language
    return "und"


def clean_url(url: str) -> str:
    """The file address without the tracking parameters the API appends (utm_*)."""
    parts = urlsplit(url)
    query = "&".join(p for p in parts.query.split("&") if p and not p.startswith("utm_"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


class WikimediaCommons:
    name = "wikimedia-commons"
    catalogue = "Wikimedia Commons"
    env_keys: tuple[str, ...] = ()
    modalities = ("image", "graphic", "video", "audio")
    method = (
        "MediaWiki API search in the File namespace (bitmap, drawing, video, audio) with the subdomain "
        "terms per language; licence from extmetadata LicenseShortName/LicenseUrl; metadata only, no "
        "uploaders"
    )

    def query(
        self, ctx: base.Context, term: str, offset: int, size: int, filetypes: str = "bitmap|drawing"
    ) -> dict[str, Any]:
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "maxlag": "5",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": f"{term} filetype:{filetypes}",
            "gsrlimit": str(size),
            "gsroffset": str(offset),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Categories|ImageDescription",
        }
        for attempt in range(MAX_LAG_RETRIES + 1):
            response = ctx.client.get(API, params=params)
            response.raise_for_status()
            data = response.json()
            error = data.get("error") or {}
            if error.get("code") != "maxlag":
                if error:
                    raise RuntimeError(
                        f"Commons API error {error.get('code')}: {error.get('info', '')[:200]}"
                    )
                return data
            wait = min(float(response.headers.get("Retry-After") or 5), MAX_WAIT_SECONDS)
            ctx.say(f"{self.name}: servers lagged, waiting {wait:g}s (attempt {attempt + 1})")
            sleep(wait)
        raise RuntimeError("Commons API: replication lag persisted, try later")

    def to_candidate(
        self, page: dict[str, Any], language: str | None, subdomain: str, allowed: list[str]
    ) -> dict[str, Any] | None:
        info = (page.get("imageinfo") or [{}])[0]
        page_url = info.get("descriptionurl") or FILE_PAGE + page["title"].replace(" ", "_")
        mime = str(info.get("mime") or "")
        title, ext = file_title(page["title"])
        if mime == "application/ogg":  # Ogg holds video (.ogv) or sound (.oga, .ogg, .opus)
            mime = "video/ogg" if ext == "ogv" else "audio/ogg"
        categories = meta(info, "Categories")
        modality, genre = classify(title, categories, mime)
        if allowed and modality not in allowed:
            return None
        if genre == "photo":
            languages = ["zxx"]
        else:
            described = TAGS.sub(" ", meta(info, "ImageDescription"))[:2000]
            languages = [detect_language(title, described, language, subdomain)]
        route: dict[str, Any] = {
            "method": "direct_download",
            "url": page_url,
            "download_url": clean_url(info["url"]) if info.get("url") else None,
            "auth": "none",
            "cost": "free",
            "provider_hint": "url",
        }
        if re.fullmatch(r"[a-z]+/[A-Za-z0-9.+-]+", mime):
            route["formats"] = [mime]
        if isinstance(info.get("size"), int):
            route["size_bytes_est"] = info["size"]
        cand = base.candidate(
            self,
            title=title or page["title"],
            title_en=None,
            languages=languages,
            area="001",
            publisher="Wikimedia Commons contributors",
            kind="community",
            landing_url=page_url,
            modality=modality,
            genre=genre,
            subdomains=[subdomain],
            licence=licence(
                meta(info, "LicenseShortName"), meta(info, "LicenseUrl"), categories, page_url
            ),
            access=[route],
            evidence=[page_url],
            level="item",
            content={"transcripts": {"available": "no"}} if genre == "photo" else None,
            identifiers={"other": [f"wikimedia-commons:M{page['pageid']}"]}
            if page.get("pageid")
            else None,
        )
        return cand

    def iterate(self, scope: base.Scope, ctx: base.Context) -> Iterator[dict[str, Any]]:
        languages: list[str | None] = list(scope.languages) or [None]
        plan = [
            (lang, sub, term)
            for lang in languages
            for sub in base.subdomains_for(scope)
            for term in base.search_terms(sub, lang)
        ]
        quota = max(1, math.ceil(ctx.limit / max(1, len(plan))))
        wanted = scope.modalities or list(self.modalities)
        filetypes = "|".join(dict.fromkeys(FILETYPES[m] for m in self.modalities if m in wanted))
        seen: dict[int, dict[str, Any]] = {}
        for lang, sub, term in plan:
            taken, offset = 0, 0
            while taken < quota:
                data = self.query(ctx, term, offset, min(BATCH, max(quota - taken, 5)), filetypes)
                pages = sorted(
                    (data.get("query") or {}).get("pages") or [], key=lambda p: p.get("index", 0)
                )
                for page in pages:
                    if taken >= quota:
                        break
                    pid = page.get("pageid")
                    if pid in seen:  # found again with another subdomain's terms (FR-003)
                        if sub not in seen[pid]["subdomains"]:
                            seen[pid]["subdomains"].append(sub)
                        continue
                    cand = self.to_candidate(page, lang, sub, scope.modalities)
                    if cand is None:
                        continue
                    seen[pid] = cand
                    taken += 1
                    yield cand
                cont = (data.get("continue") or {}).get("gsroffset")
                if cont is None or not pages:
                    break
                offset = int(cont)
            ctx.say(f"{self.name}: {lang or 'en'} {sub} {term!r}: {taken}")
