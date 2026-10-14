"""Reading a licence from the text of an evidence page (audit research R8, check K5).

The deterministic matcher looks for licence URLs, names and badges; it knows no stored decision.
Some evidence pages are single-page applications whose HTML carries no licence (data.europa.eu,
Zenodo); for them `readable_url` names the portal's own machine-readable record of the same
resource, which states the licence the page shows. Page text is held in memory only.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx

CC_URL = re.compile(r"creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/(\d\.\d)", re.I)
CC_TEXT = re.compile(r"\bCC[\s_-]?(BY(?:[\s_-](?:NC|SA|ND)){0,2})[\s_-]?(\d)[._](\d)\b", re.I)
PATTERNS = [
    (re.compile(r"\bCC0\b|creativecommons\.org/publicdomain/zero", re.I), "CC0-1.0"),
    # before the UK licence: French pages name it "Licence Ouverte / Open Licence"
    (re.compile(r"licence ouverte|etalab", re.I), "etalab-2.0"),
    (re.compile(r"open government licence", re.I), "LicenseRef-OGL-UK-3.0"),
    (re.compile(r"datenlizenz deutschland.{0,20}namensnennung", re.I), "DL-DE-BY-2.0"),
    # ODbL pages also name Open Data Commons; read ODbL first
    (re.compile(r"\bODbL\b|open database license", re.I), "ODbL-1.0"),
    (re.compile(r"open data commons attribution|\bodc-by\b", re.I), "ODC-By-1.0"),
    (re.compile(r"\bMIT License\b|\blicen[cs]e:\s*mit\b", re.I), "MIT"),
    (
        re.compile(r"Apache License,? (?:Version )?2\.0|\blicen[cs]e:\s*apache-2\.0\b", re.I),
        "Apache-2.0",
    ),
    (re.compile(r"公共データ利用規約|public data license", re.I), "LicenseRef-Japan-PDL-1.0"),
    (
        re.compile(r"政府標準利用規約|government standard terms of use", re.I),
        "LicenseRef-Japan-Gov-Standard-Terms-2.0",
    ),
    (
        re.compile(
            r"all rights reserved|todos los derechos reservados|wszelkie prawa zastrzeżone|無断転載"
            r"|tous droits réservés|alle rechte vorbehalten|tutti i diritti riservati",
            re.I,
        ),
        "LicenseRef-proprietary",
    ),
]
# Creative Commons licences written out, in the languages of the target set that name them most
ATTRIB = [
    "attribution",
    "namensnennung",
    "atribuci[oó]n",
    "reconocimiento",
    "atribui[cç][aã]o",
    "uznanie autorstwa",
    "attribuzione",
    "naamsvermelding",
    "erk[äa]nnande",
    "nimeäminen",
]
NC = [
    "non[- ]?commercial",
    "nicht[- ]?kommerziell",
    "no ?comercial",
    "n[aã]o ?comercial",
    "pas d.utilisation commerciale",
    "u[żz]ycie niekomercyjne",
    "non commerciale",
    "niet[- ]commercieel",
    "ickekommersiell",
    "ei kaupallinen",
]
SA = [
    "share ?alike",
    "weitergabe unter gleichen bedingungen",
    "compartir ?igual",
    "compartilha ?igual",
    "partage dans les m[êe]mes conditions",
    "na tych samych warunkach",
    "condividi allo stesso modo",
    "gelijk delen",
    "dela lika",
    "j[aä]rjest[aä]",
]
ND = [
    "no ?derivatives",
    "no ?derivs",
    "keine bearbeitungen?",
    "sin ?(?:obra ?)?derivadas?",
    "sem ?deriva[cç][oõ]es",
    "pas de modification",
    "bez utwor[oó]w zale[żz]nych",
    "non opere derivate",
    "geen afgeleide werken",
    "inga bearbetningar",
]
SEP = r"\W{1,4}"


def _any(words: list[str]) -> str:
    return "(?:" + "|".join(words) + ")"


CC_LONG = re.compile(
    rf"creative ?commons{SEP}{_any(ATTRIB)}"
    rf"(?P<nc>{SEP}{_any(NC)})?(?P<sa>{SEP}{_any(SA)})?(?P<nd>{SEP}{_any(ND)})?"
    rf"{SEP}(?:\w+\W{{1,3}}){{0,2}}?(?P<v>\d\.\d)",
    re.I,
)
OPEN_IDS = ("unknown", "mixed", "LicenseRef-proprietary", "LicenseRef-all-rights-reserved")

DATA_EUROPA = re.compile(r"^/data/datasets/([^/?#]+)")
ZENODO = re.compile(r"^/records?/(\d+)")
DANE = re.compile(r"^/(?:[a-z]{2}/)?dataset/(\d+)")


def match_licence(text: str, url: str | None = None) -> str:
    """Deterministic reading: an SPDX id or LicenseRef, LicenseRef-proprietary, or unknown."""
    # lazy: checks imports this module, and harvest.base imports checks
    from mobility_model_zoo.catalog.harvest import base

    if url:
        for page, lid in base.LICENCE_PAGES.items():
            if page in url.lower():
                return lid
    m = CC_URL.search(text)
    if m and m.group(1).lower() == "licenses":
        return f"CC-{m.group(2).upper()}-{m.group(3)}"
    m = CC_TEXT.search(text)
    if m:
        parts = re.split(r"[\s_-]+", m.group(1).upper())
        return f"CC-{'-'.join(parts)}-{m.group(2)}.{m.group(3)}"
    m = CC_LONG.search(text)
    if m:
        parts = ["BY"] + [k.upper() for k in ("nc", "sa", "nd") if m.group(k)]
        return f"CC-{'-'.join(parts)}-{m.group('v')}"
    for pattern, lid in PATTERNS:
        if pattern.search(text):
            return lid
    return "unknown"


def visible_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    # keep link targets: licence badges are often only an <a href> to creativecommons.org
    html = re.sub(r'(?i)href=["\']([^"\']+)["\']', r" \1 ", html)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def readable_url(url: str) -> str:
    """The address whose text states the licence: the portal API for single-page applications."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host == "data.europa.eu" and (m := DATA_EUROPA.match(parts.path)):
        return f"https://data.europa.eu/api/hub/search/datasets/{m.group(1)}"
    if host == "zenodo.org" and (m := ZENODO.match(parts.path)):
        return f"https://zenodo.org/api/records/{m.group(1)}"
    if host == "dane.gov.pl" and (m := DANE.match(parts.path)):
        return f"https://api.dane.gov.pl/1.4/datasets/{m.group(1)}"
    return url


def normalise(licence: str, known: set[str]) -> str:
    """A reader's answer as a catalog licence id: listed ids and the fixed answers stay as they are."""
    from mobility_model_zoo.catalog.harvest import base  # see match_licence

    text = str(licence or "").strip()
    if text in known or text in OPEN_IDS:
        return text
    found = base.spdx(text)
    return found if found != "unknown" else text or "unknown"


def conflicts(stored: str, read: str) -> bool:
    """The page reserves all rights although the entry carries an open licence."""
    return read == "LicenseRef-proprietary" and stored not in OPEN_IDS


DOI_HOSTS = ("doi.org", "dx.doi.org")
CROSSREF = "https://api.crossref.org/works/{doi}"
DATACITE = "https://api.datacite.org/dois/{doi}"
KEYWORDS = re.compile(
    r"licen[cs]|lizenz|licencia|licença|creative ?commons|\bcc[ -]?by|\bcc0\b|public domain|rights|©"
    r"|ライセンス|利用規約|许可|授权|라이선스|저작권",
    re.I,
)


def doi_of(url: str) -> str | None:
    parts = urlsplit(url)
    if (parts.hostname or "").lower() in DOI_HOSTS and parts.path.startswith("/10."):
        return unquote(parts.path[1:])
    return None


def registry_statement(doi: str, client: httpx.Client) -> str:
    """The licence a DOI registry records for the work (Crossref, else DataCite); '' if none."""
    try:
        resp = client.get(CROSSREF.format(doi=doi))
        if resp.status_code < 400:
            urls = [x.get("URL", "") for x in (resp.json().get("message") or {}).get("license") or []]
            if urls:
                return "Crossref licence: " + " ".join(urls)
        resp = client.get(DATACITE.format(doi=doi))
        if resp.status_code < 400:
            rights = ((resp.json().get("data") or {}).get("attributes") or {}).get("rightsList") or []
            parts = [f"{r.get('rights', '')} {r.get('rightsUri', '')}" for r in rights]
            if parts:
                return "DataCite rights: " + " ".join(parts)
    except (httpx.HTTPError, ValueError, AttributeError):
        pass
    return ""


def _api_excerpt(host: str, data: dict[str, Any]) -> str:
    """Title and licence fields of a portal API record, as compact text."""
    if host == "zenodo.org":
        meta = data.get("metadata") or {}
        keep = {"title": meta.get("title"), "license": meta.get("license"), "rights": meta.get("rights")}
    elif host == "dane.gov.pl":
        attrs = (data.get("data") or {}).get("attributes") or {}
        fields = ("title", "license_name", "license_condition_custom_description")
        keep = {k: attrs.get(k) for k in fields}
    else:  # data.europa.eu
        result = data.get("result") or {}
        keep = {
            "title": result.get("title"),
            "licences": [d.get("license") for d in result.get("distributions") or []],
            "rights": [d.get("rights") for d in result.get("distributions") or []],
        }
    return json.dumps(keep, ensure_ascii=False)


def evidence_text(url: str, client: httpx.Client) -> str:
    """The text a reader judges for an evidence address ('' if it cannot be read)."""
    readable = readable_url(url)
    try:
        resp = client.get(readable)
    except httpx.HTTPError:
        resp = None
    text = ""
    if resp is not None and resp.status_code < 400:
        if readable != url:
            try:
                text = _api_excerpt((urlsplit(url).hostname or "").lower(), resp.json())
            except ValueError:
                text = ""
        else:
            text = visible_text(resp.text)
    doi = doi_of(url)
    if doi:
        text = " ".join(t for t in (registry_statement(doi, client), text) if t)
    return text


def excerpt(text: str, limit: int) -> str:
    """At most `limit` characters: the start plus the passages around licence words."""
    if len(text) <= limit:
        return text
    head = text[: limit // 4]
    spans: list[tuple[int, int]] = []
    for m in KEYWORDS.finditer(text, limit // 4):
        start, end = max(m.start() - 200, limit // 4), m.end() + 200
        if spans and start <= spans[-1][1]:
            spans[-1] = (spans[-1][0], end)
        else:
            spans.append((start, end))
    out = head
    for start, end in spans:
        piece = " … " + text[start:end]
        if len(out) + len(piece) > limit:
            break
        out += piece
    return out
