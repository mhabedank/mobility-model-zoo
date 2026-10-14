"""Reading a licence from the text of an evidence page (audit research R8, check K5).

The deterministic matcher looks for licence URLs, names and badges; it knows no stored decision.
Some evidence pages are single-page applications whose HTML carries no licence (data.europa.eu,
Zenodo); for them `readable_url` names the portal's own machine-readable record of the same
resource, which states the licence the page shows. Page text is held in memory only.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

CC_URL = re.compile(r"creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/(\d\.\d)", re.I)
CC_TEXT = re.compile(r"\bCC[\s_-]?(BY(?:[\s_-](?:NC|SA|ND)){0,2})[\s_-]?(\d)[._](\d)\b", re.I)
PATTERNS = [
    (re.compile(r"\bCC0\b|creativecommons\.org/publicdomain/zero", re.I), "CC0-1.0"),
    # before the UK licence: French pages name it "Licence Ouverte / Open Licence"
    (re.compile(r"licence ouverte|etalab", re.I), "etalab-2.0"),
    (re.compile(r"open government licence", re.I), "LicenseRef-OGL-UK-3.0"),
    (re.compile(r"datenlizenz deutschland.{0,20}namensnennung", re.I), "DL-DE-BY-2.0"),
    (re.compile(r"open data commons attribution|odc-by", re.I), "ODC-By-1.0"),
    (re.compile(r"\bODbL\b|open database license", re.I), "ODbL-1.0"),
    (re.compile(r"公共データ利用規約|public data license", re.I), "LicenseRef-Japan-PDL-1.0"),
    (re.compile(r"政府標準利用規約|government standard terms of use", re.I),
     "LicenseRef-Japan-Gov-Standard-Terms-2.0"),
    (
        re.compile(
            r"all rights reserved|todos los derechos reservados|wszelkie prawa zastrzeżone|無断転載"
            r"|tous droits réservés|alle rechte vorbehalten|tutti i diritti riservati",
            re.I,
        ),
        "LicenseRef-proprietary",
    ),
]
OPEN_IDS = ("unknown", "mixed", "LicenseRef-proprietary", "LicenseRef-all-rights-reserved")

DATA_EUROPA = re.compile(r"^/data/datasets/([^/?#]+)")
ZENODO = re.compile(r"^/records?/(\d+)")


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
