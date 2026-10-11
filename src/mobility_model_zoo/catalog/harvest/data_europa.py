"""Harvester for the data.europa.eu search API (research R6): open datasets of EU institutions and
member states.

The search API has no language facet, so the harvester searches with the terms of the target
language and keeps a dataset only if its `language` lists that language, or (when the dataset gives
no language) its title was written in it (`translation_meta`); such a dataset gets `und`. The
licence is read from the distributions; distributions with different known licences make `mixed`.
data.europa.eu drops the reuse conditions of the Polish portal dane.gov.pl, so for its datasets the
harvester reads the licence from the dane.gov.pl API (`dane_gov_pl_licence`) and keeps `unknown`
when the publisher adds its own conditions. The same holds for the CKAN portals in `CKAN_PORTALS`,
whose `package_show` the harvester asks (`ckan_licence`).

Heuristics (documented for the owner):
- origin area: EU institutions and agencies → `EU`; else the dataset `country`; `EUROPE` → `150`;
  otherwise `001`.
- publisher kind: EU bodies → `government`; no publisher → the source catalogue as
  `open_data_portal`; names of universities and research institutes → `research`; company suffixes
  → `company`; associations and foundations → `association`; everything else → `government`
  (data.europa.eu harvests public-sector portals).
- genre: `gtfs` if a distribution or the title says GTFS; `geodata` for geographical formats and
  OGC services; `spreadsheet` if every file is a spreadsheet; otherwise `table`.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator
from typing import Any

import httpx

from mobility_model_zoo.catalog.harvest import base
from mobility_model_zoo.catalog.model import vocab

API = "https://data.europa.eu/api/hub/search/search"
LANDING = "https://data.europa.eu/data/datasets/{id}"
PAGE_SIZE = 50
MAX_ROUTES = 3
EU_BODY = "http://publications.europa.eu/resource/authority/corporate-body/"
SPDX_URL = re.compile(r"spdx\.org/licenses/([A-Za-z0-9.+-]+)")
EU_CC = re.compile(r"^CC_BY(?:_?(SA|NC|ND|NCSA|NCND|NC_SA|NC_ND))?_(\d)_(\d)$", re.IGNORECASE)
CC_PARTS = {"": "", "SA": "-SA", "NC": "-NC", "ND": "-ND", "NCSA": "-NC-SA", "NCND": "-NC-ND"}
EU_LICENCES = {
    "CC0": "CC0-1.0",
    "ODC_BY": "ODC-By-1.0",
    "ODC_ODBL": "ODbL-1.0",
    "ODC_PDDL": "PDDL-1.0",
    "OGL_3_0": "LicenseRef-OGL-UK-3.0",
    "DL_DE_BY_2_0": "DL-DE-BY-2.0",
    "DL_DE_ZERO_2_0": "DL-DE-ZERO-2.0",
    "ETALAB_2_0": "etalab-2.0",
}
URL_LICENCES = {
    "nationalarchives.gov.uk/doc/open-government-licence/version/3": "LicenseRef-OGL-UK-3.0",
    "dcat-ap.de/def/licenses/dl-by-de/2.0": "DL-DE-BY-2.0",
    "dcat-ap.de/def/licenses/dl-zero-de/2.0": "DL-DE-ZERO-2.0",
    "etalab.gouv.fr/licence-ouverte-open-licence": "etalab-2.0",
}
# EU file-type authority ids → IANA media types (used when a distribution gives no media_type)
MEDIA_TYPES = {
    "CSV": "text/csv",
    "TSV": "text/tab-separated-values",
    "JSON": "application/json",
    "GEOJSON": "application/geo+json",
    "XML": "application/xml",
    "ZIP": "application/zip",
    "XLS": "application/vnd.ms-excel",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ODS": "application/vnd.oasis.opendocument.spreadsheet",
    "PDF": "application/pdf",
    "HTML": "text/html",
    "TXT": "text/plain",
    "RDF_XML": "application/rdf+xml",
    "KML": "application/vnd.google-earth.kml+xml",
    "KMZ": "application/vnd.google-earth.kmz",
    "GML": "application/gml+xml",
    "SHP": "application/vnd.shp",
    "GPKG": "application/geopackage+sqlite3",
    "PARQUET": "application/vnd.apache.parquet",
}
SPREADSHEETS = {"XLS", "XLSX", "ODS"}
SERVICES = {"WMS_SRVC", "WFS_SRVC", "WCS_SRVC", "WMTS_SRVC", "API", "REST", "SPARQLQ", "OAPIF"}
GEO_FORMATS = {"GEOJSON", "KML", "KMZ", "GML", "SHP", "GPKG"}
MEDIA_TYPE = re.compile(r"^[a-z]+/[A-Za-z0-9.+-]+$")
IANA_URL = re.compile(r"iana\.org/assignments/media-types/([a-z]+/[A-Za-z0-9.+-]+)")
DOI = re.compile(r"(10\.\d{4,9}/\S+)$")
DANE_GOV_PL = re.compile(r"^https-dane-gov-pl-(?:[a-z]{2}-)?dataset-(\d+)(?:-|$)")
DANE_API = "https://api.dane.gov.pl/1.4/datasets/{n}"
DANE_PAGE = "https://dane.gov.pl/pl/dataset/{n}"
# National CKAN portals whose licences data.europa.eu drops: data.europa.eu catalog id ->
# (package_show endpoint, dataset page). Probed 2026-10-11; si and hu publish no licence, hr and ro
# did not answer, cy and bg have no usable API.
CKAN_PORTALS = {
    "data-gov-lv": (
        "https://data.gov.lv/dati/api/3/action/package_show",
        "https://data.gov.lv/dati/lv/dataset/{name}",
    ),
}
CKAN_SUFFIX = re.compile(r"~~\d+$")
# conditions a publisher may add on dane.gov.pl; any of them makes the licence alone insufficient
DANE_CONDITIONS = (
    "license_condition_custom_description",
    "license_condition_db_or_copyrighted",
    "license_condition_personal_data",
)
RESEARCH = re.compile(
    r"univers|research|investigaci|forschung|recherche|ricerca|badawcz|csic|cnrs|"
    r"fraunhofer|helmholtz|academ",
    re.IGNORECASE,
)
COMPANY = re.compile(
    r"\b(s\.?a\.?u?|s\.?l\.?|gmbh|ag|ltd|plc|inc|b\.?v\.?|s\.?p\.?a\.?|sp\. z o\.o\.)$", re.IGNORECASE
)
ASSOCIATION = re.compile(
    r"asociaci|association|verein|fundaci|foundation|stiftung|stowarzysz", re.IGNORECASE
)


def _licence_id(lic: Any) -> str:
    """SPDX id of one distribution licence (EU authority id, SPDX URL or licence URL)."""
    if not lic:
        return "unknown"
    values = [lic] if isinstance(lic, str) else [lic.get("resource"), lic.get("id"), lic.get("label")]
    for value in (str(v) for v in values if v):
        m = SPDX_URL.search(value)
        if m:
            return m.group(1)
        code = value.rstrip("/").rsplit("/", 1)[-1].strip().upper().replace("-", "_")
        m = EU_CC.match(code)
        if m:
            mid = CC_PARTS[(m.group(1) or "").replace("_", "")]
            return f"CC-BY{mid}-{m.group(2)}.{m.group(3)}"
        if code in EU_LICENCES:
            return EU_LICENCES[code]
        for fragment, spdx_id in URL_LICENCES.items():
            if fragment in value:
                return spdx_id
        if "opendefinition.org/licenses/" in value:
            value = value.rstrip("/").rsplit("/", 1)[-1]
        found = base.spdx(re.sub(r"_(\d)_(\d)$", r"-\1.\2", value))
        if found != "unknown":
            return found
    return "unknown"


def _licence(dataset: dict[str, Any], landing: str) -> dict[str, Any]:
    ids: dict[str, str | None] = {}
    for dist in dataset.get("distributions") or []:
        lic = dist.get("license")
        lid = _licence_id(lic)
        if lid != "unknown" and lid not in ids:
            url = lic.get("resource") if isinstance(lic, dict) else lic
            ids[lid] = url if isinstance(url, str) and url.startswith("http") else None
    if not ids:
        return base.licence_block("unknown", None, None)
    if len(ids) > 1:
        return base.licence_block("mixed", None, landing)
    lid, url = next(iter(ids.items()))
    return base.licence_block(lid, url, landing)


def dane_gov_pl_licence(
    dataset_id: str, client: httpx.Client, say: Any = print
) -> dict[str, Any] | None:
    """Licence block from the dane.gov.pl API for a dataset that data.europa.eu harvested from it.

    None when the id is not a dane.gov.pl dataset or the API fails; `unknown` when the dataset has
    no licence or its publisher added conditions of its own.
    """
    m = DANE_GOV_PL.match(dataset_id)
    if not m:
        return None
    n = m.group(1)
    try:
        resp = client.get(DANE_API.format(n=n), headers={"Accept": "application/json"})
        resp.raise_for_status()
        attrs = ((resp.json().get("data") or {}).get("attributes")) or {}
    except (httpx.HTTPError, ValueError, AttributeError) as e:
        say(f"data-europa: dane.gov.pl dataset {n}: {type(e).__name__}: {e}")
        return None
    if any(attrs.get(k) for k in DANE_CONDITIONS):
        return base.licence_block("unknown", None, None)
    lid = base.spdx(str(attrs.get("license_name") or ""))
    if lid == "unknown":
        return base.licence_block("unknown", None, None)
    return base.licence_block(lid, None, DANE_PAGE.format(n=n))


def ckan_licence(
    catalog_id: str | None, dataset_id: str, client: httpx.Client, say: Any = print
) -> dict[str, Any] | None:
    """Licence block from a national CKAN portal of `CKAN_PORTALS`; None if not one or it fails."""
    portal = CKAN_PORTALS.get(catalog_id or "")
    if portal is None:
        return None
    api, page = portal
    ref = CKAN_SUFFIX.sub("", dataset_id)
    try:
        resp = client.get(api, params={"id": ref})
        resp.raise_for_status()
        result = resp.json().get("result") or {}
    except (httpx.HTTPError, ValueError, AttributeError) as e:
        say(f"data-europa: {catalog_id} dataset {ref}: {type(e).__name__}: {e}")
        return None
    lid = base.spdx(str(result.get("license_id") or ""))
    if lid == "unknown":
        lid = base.spdx(str(result.get("license_title") or ""))
    if lid == "unknown" or not result.get("name"):
        return base.licence_block("unknown", None, None)
    url = result.get("license_url")
    return base.licence_block(
        lid,
        url if isinstance(url, str) and url.startswith("http") else None,
        page.format(name=result["name"]),
    )


def _first(value: Any) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    return value if isinstance(value, str) and value.startswith("http") else None


def _format(dist: dict[str, Any]) -> tuple[str | None, str | None]:
    """(EU file-type id, IANA media type) of a distribution."""
    fmt = dist.get("format") or {}
    code = str(fmt.get("id") or "").upper() or None
    media = str(dist.get("media_type") or "")
    m = IANA_URL.search(media)
    if m:
        media = m.group(1)
    if code is None and media.split("/")[-1].upper() in ("WMS", "WFS", "WCS", "WMTS"):
        code = f"{media.split('/')[-1].upper()}_SRVC"
    if not MEDIA_TYPE.match(media):
        media = MEDIA_TYPES.get(code or "") or ""
    return code, media or None


def _route(dist: dict[str, Any]) -> dict[str, Any] | None:
    code, media = _format(dist)
    download = _first(dist.get("download_url"))
    access = _first(dist.get("access_url")) or download
    if access is None:
        return None
    if code in SERVICES or dist.get("access_service"):
        method = "api"
        download = None
    elif media == "text/html" and not download:
        method = "page_by_page"
    elif download or media:
        method = "direct_download"
    else:
        method = "page_by_page"
    route: dict[str, Any] = {
        "method": method,
        "url": access,
        "download_url": download,
        "auth": "none",
        "cost": "free",
        "provider_hint": "url",
    }
    if media and method == "direct_download":
        route["formats"] = [media]
    size = dist.get("byte_size")
    if isinstance(size, int) and size >= 0 and method == "direct_download":
        route["size_bytes_est"] = size
    return route


def _access(dataset: dict[str, Any], landing: str) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    seen: set[str] = set()
    order = {"direct_download": 0, "api": 1, "page_by_page": 2}
    for dist in dataset.get("distributions") or []:
        route = _route(dist)
        if route and route["url"] not in seen:
            seen.add(route["url"])
            routes.append(route)
    routes.sort(key=lambda r: order[r["method"]])
    return routes[:MAX_ROUTES] or [
        {
            "method": "page_by_page",
            "url": landing,
            "download_url": None,
            "auth": "none",
            "cost": "free",
            "provider_hint": "url",
        }
    ]


def _genre(dataset: dict[str, Any], title: str) -> str:
    codes = [_format(d)[0] or "" for d in dataset.get("distributions") or []]
    if "GTFS" in title.upper() or any("GTFS" in c for c in codes):
        return "gtfs"
    geo = any(c in GEO_FORMATS or c in SERVICES - {"API", "REST", "SPARQLQ"} for c in codes) or any(
        t.get("id") == "geographical"
        for d in dataset.get("distributions") or []
        for t in ((d.get("format") or {}).get("format_types") or [])
    )
    if geo:
        return "geodata"
    files = [c for c in codes if c]
    if files and all(c in SPREADSHEETS for c in files):
        return "spreadsheet"
    return "table"


def _eu_body(dataset: dict[str, Any]) -> bool:
    pub = dataset.get("publisher") or {}
    cls = (dataset.get("corporate-body-classification") or {}).get("id")
    return str(pub.get("resource") or "").startswith(EU_BODY) or (cls not in (None, "_NATIONAL"))


def _area(dataset: dict[str, Any]) -> str:
    if _eu_body(dataset):
        return "EU"
    country = str((dataset.get("country") or {}).get("id") or "")
    if len(country) == 2 and country.upper() in vocab().areas:
        return country.upper()
    if country.upper() == "EUROPE":
        return "150"
    return "001"


def _publisher(dataset: dict[str, Any]) -> tuple[str, str]:
    name = str((dataset.get("publisher") or {}).get("name") or "").strip()
    if _eu_body(dataset):
        return name or "European Union", "government"
    if not name:
        cat = dataset.get("catalog") or {}
        title = cat.get("title") or {}
        label = title
        if isinstance(title, dict):
            label = title.get("en") or next(iter(title.values()), None)
        return str(label or cat.get("id") or "data.europa.eu"), "open_data_portal"
    if RESEARCH.search(name):
        return name, "research"
    if COMPANY.search(name):
        return name, "company"
    if ASSOCIATION.search(name):
        return name, "association"
    return name, "government"


def _original_language(dataset: dict[str, Any]) -> str | None:
    details = (dataset.get("translation_meta") or {}).get("details") or {}
    for info in details.values():
        if isinstance(info, dict) and info.get("original_language"):
            return str(info["original_language"])
    return None


def _languages(dataset: dict[str, Any]) -> list[str]:
    out = []
    for lang in dataset.get("language") or []:
        raw = lang
        if isinstance(lang, dict):
            raw = lang.get("id") or str(lang.get("resource") or "").rsplit("/", 1)[-1]
        code = base.language_code(raw)
        if code != "und":
            out.append(code)
    return out


def _doi(dataset: dict[str, Any]) -> str | None:
    raw = dataset.get("doi_identifiers") or []
    for value in [raw] if isinstance(raw, str) else raw:
        m = DOI.search(str(value).strip())
        if m:
            return m.group(1)
    return None


def _topics(subdomains: list[str]) -> list[str]:
    topics = ["productdev"]
    if "condition_monitoring" in subdomains:
        topics.append("condition-monitoring")
    if "vehicle_security" in subdomains:
        topics.append("security")
    return topics


class DataEuropa:
    name = "data-europa"
    catalogue = "data.europa.eu"
    env_keys: tuple[str, ...] = ()
    modalities = ("structured_data",)
    method = (
        "data.europa.eu search API (/api/hub/search/search, filters=dataset), subdomain terms per "
        "language, language checked on the dataset; metadata only"
    )

    def iterate(self, scope: base.Scope, ctx: base.Context) -> Iterator[dict[str, Any]]:
        if scope.modalities and "structured_data" not in scope.modalities:
            return
        seen: dict[str, dict[str, Any]] = {}
        languages = scope.languages or [None]
        pages = max(1, math.ceil(ctx.limit / PAGE_SIZE))
        for subdomain in base.subdomains_for(scope):
            for language in languages:
                for term in base.search_terms(subdomain, language):
                    for dataset in self._search(term, scope, ctx, pages):
                        cand = self._candidate(dataset, subdomain, language, scope, seen, ctx)
                        if cand is not None:
                            yield cand

    def _search(
        self, term: str, scope: base.Scope, ctx: base.Context, pages: int
    ) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"q": term, "filters": "dataset", "limit": PAGE_SIZE}
        countries = [a.lower() for a in scope.areas if len(a) == 2 and a.isalpha() and a != "EU"]
        if countries:
            params["facets"] = json.dumps({"country": countries})
        for page in range(pages):
            try:
                resp = ctx.client.get(API, params={**params, "page": page})
                resp.raise_for_status()
                results = (resp.json().get("result") or {}).get("results") or []
            except (httpx.HTTPError, ValueError) as e:
                ctx.say(f"data-europa: {term!r} page {page}: {type(e).__name__}: {e}")
                return
            yield from results
            if len(results) < PAGE_SIZE:
                return

    def _candidate(
        self,
        dataset: dict[str, Any],
        subdomain: str,
        language: str | None,
        scope: base.Scope,
        seen: dict[str, dict[str, Any]],
        ctx: base.Context,
    ) -> dict[str, Any] | None:
        did = dataset.get("id")
        titles = dataset.get("title") or {}
        if not did or not isinstance(titles, dict) or not titles:
            return None
        landing = LANDING.format(id=did)
        if landing in seen:
            known = seen[landing]
            if subdomain not in known["subdomains"]:
                known["subdomains"].append(subdomain)
                known["topics"] = _topics(known["subdomains"])
            return None
        langs = _languages(dataset)
        original = _original_language(dataset)
        if language and language not in langs and (langs or base.language_code(original) != language):
            return None
        area = _area(dataset)
        if scope.areas and area not in scope.areas:
            return None
        title_lang = next((code for code in (original, *langs) if code in titles), None)
        title = titles[title_lang] if title_lang else next(iter(titles.values()))
        if not title:
            return None
        publisher, kind = _publisher(dataset)
        subdomains = [subdomain]
        licence = _licence(dataset, landing)
        if licence["id"] == "unknown":
            catalog = (dataset.get("catalog") or {}).get("id")
            licence = (
                dane_gov_pl_licence(str(did), ctx.client, ctx.say)
                or ckan_licence(catalog, str(did), ctx.client, ctx.say)
                or licence
            )
        cand = base.candidate(
            self,
            title=str(title),
            title_en=titles.get("en"),
            languages=langs,
            area=area,
            publisher=publisher,
            kind=kind,
            landing_url=landing,
            modality="structured_data",
            genre=_genre(dataset, str(title)),
            subdomains=subdomains,
            licence=licence,
            access=_access(dataset, landing),
            evidence=[landing, licence["evidence_url"]]
            if licence["evidence_url"] not in (None, landing)
            else [landing],
            topics=_topics(subdomains),
            level="collection",
            identifiers={"doi": doi} if (doi := _doi(dataset)) else None,
        )
        seen[landing] = cand
        return cand
