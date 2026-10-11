"""Harvester for the Zenodo records API (research R6): open datasets and publications.

Each subdomain term is searched as a phrase, restricted to the target language with
`metadata.languages.id` (ISO 639-3) and to one resource type per request (`type=dataset`,
`type=publication`). A record becomes a standalone `item` without parent. Records that are not
openly accessible (`access_right` other than `open`) are skipped: they have no free access route.

Heuristics (documented for the owner):
- publisher: the first creator affiliation (an organisation; creator names are never stored);
  without one, `Zenodo` as `community`. Kind from the affiliation name: city councils, ministries
  and agencies → `government`; company suffixes → `company`; associations and foundations →
  `association`; otherwise `research` (universities and institutes deposit most records).
- origin area: Zenodo metadata has no country field, so `001`.
- genre: datasets by their file types (`gtfs`, `geodata`, `spreadsheet`, `json_xml_dump`, else
  `table`); publications by subtype (articles, preprints, theses → `paper`; books → `book`;
  standards → `standard`; everything else → `report`).
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from typing import Any

import httpx

from mobility_model_zoo.catalog.harvest import base
from mobility_model_zoo.catalog.harvest.iso639 import THREE_TO_TWO

API = "https://zenodo.org/api/records"
LANDING = "https://zenodo.org/records/{id}"
PAGE_SIZE = 25  # the maximum for anonymous requests
MAX_ROUTES = 3
TYPES = {"structured_data": "dataset", "text": "publication"}
DOI = re.compile(r"^10\.\d{4,9}/\S+$")
MEDIA_TYPES = {
    "csv": "text/csv", "tsv": "text/tab-separated-values", "txt": "text/plain",
    "json": "application/json",
    "geojson": "application/geo+json", "xml": "application/xml", "zip": "application/zip",
    "gz": "application/gzip", "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet", "pdf": "application/pdf",
    "kml": "application/vnd.google-earth.kml+xml", "kmz": "application/vnd.google-earth.kmz",
    "gml": "application/gml+xml", "shp": "application/vnd.shp", "gpkg": "application/geopackage+sqlite3",
    "parquet": "application/vnd.apache.parquet", "nc": "application/netcdf", "h5": "application/x-hdf5",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "md": "text/markdown", "html": "text/html", "png": "image/png", "jpg": "image/jpeg",
    "jpeg": "image/jpeg", "glb": "model/gltf-binary",
}
GEO = {"geojson", "kml", "kmz", "gml", "shp", "gpkg"}
SPREADSHEETS = {"xls", "xlsx", "ods"}
DUMPS = {"json", "xml"}
PAPERS = {"article", "preprint", "conferencepaper", "thesis", "workingpaper", "proposal"}
BOOKS = {"book", "section"}
GOVERNMENT = re.compile(r"ayuntamiento|ministr|minister|gobierno|government|council|municipal|agencia|"
                        r"agency|ministerium|stadt |urz[aą]d|city of|generalitat|junta de|diputaci",
                        re.IGNORECASE)
COMPANY = re.compile(r"\b(s\.?a\.?u?|s\.?l\.?|gmbh|ag|ltd|plc|inc|b\.?v\.?|s\.?p\.?a\.?|sp\. z o\.o\.)$",
                     re.IGNORECASE)
ASSOCIATION = re.compile(r"asociaci|association|verein|fundaci|foundation|stiftung|stowarzysz",
                         re.IGNORECASE)
NO_AFFILIATION = {"", "none", "n/a", "na", "-", "independent", "independent researcher"}


def iso639_3(code: str) -> list[str]:
    """Three-letter codes Zenodo may use for a BCP 47 code of the vocabulary."""
    primary = code.split("-")[0].lower()
    if len(primary) == 3:
        return [primary]
    return sorted(three for three, two in THREE_TO_TWO.items() if two == primary)


def _publisher(metadata: dict[str, Any]) -> tuple[str, str]:
    for creator in metadata.get("creators") or []:
        aff = str(creator.get("affiliation") or "").strip()
        if aff.lower() in NO_AFFILIATION:
            continue
        if GOVERNMENT.search(aff):
            return aff, "government"
        if COMPANY.search(aff):
            return aff, "company"
        if ASSOCIATION.search(aff):
            return aff, "association"
        return aff, "research"
    return "Zenodo", "community"


def _ext(key: str) -> str:
    return key.rsplit(".", 1)[-1].lower() if "." in key else ""


def _genre(record: dict[str, Any], title: str) -> tuple[str, str]:
    """(modality, genre) of a record."""
    rtype = (record.get("metadata") or {}).get("resource_type") or {}
    if rtype.get("type") == "publication":
        sub = rtype.get("subtype") or ""
        if sub in PAPERS:
            return "text", "paper"
        if sub in BOOKS:
            return "text", "book"
        if sub == "standard":
            return "text", "standard"
        return "text", "report"
    keys = [str(f.get("key") or "").lower() for f in record.get("files") or []]
    if "gtfs" in title.lower() or any("gtfs" in key for key in keys):
        return "structured_data", "gtfs"
    exts = [_ext(key) for key in keys]
    if any(e in GEO for e in exts):
        return "structured_data", "geodata"
    data = [e for e in exts if e in MEDIA_TYPES]
    if data and all(e in SPREADSHEETS for e in data):
        return "structured_data", "spreadsheet"
    if data and all(e in DUMPS for e in data):
        return "structured_data", "json_xml_dump"
    return "structured_data", "table"


def _access(record: dict[str, Any], landing: str) -> list[dict[str, Any]]:
    routes = []
    for f in (record.get("files") or [])[:MAX_ROUTES]:
        link = (f.get("links") or {}).get("self")
        if not isinstance(link, str) or not link.startswith("http"):
            continue
        route: dict[str, Any] = {"method": "direct_download", "url": landing, "download_url": link,
                                 "auth": "none", "cost": "free", "provider_hint": "zenodo"}
        media = MEDIA_TYPES.get(_ext(f.get("key") or ""))
        if media:
            route["formats"] = [media]
        if isinstance(f.get("size"), int) and f["size"] >= 0:
            route["size_bytes_est"] = f["size"]
        routes.append(route)
    return routes or [{"method": "api", "url": f"{API}/{record['id']}", "download_url": None,
                       "auth": "none", "cost": "free", "provider_hint": "zenodo"}]


def _topics(subdomains: list[str]) -> list[str]:
    topics = ["productdev"]
    if "condition_monitoring" in subdomains:
        topics.append("condition-monitoring")
    if "vehicle_security" in subdomains:
        topics.append("security")
    return topics


class Zenodo:
    name = "zenodo"
    catalogue = "Zenodo"
    env_keys: tuple[str, ...] = ()
    modalities = ("structured_data", "text")
    method = ("Zenodo records API (/api/records), phrase search per subdomain term, filtered by "
              "metadata.languages.id and type dataset/publication; open records only; metadata only")

    def iterate(self, scope: base.Scope, ctx: base.Context) -> Iterator[dict[str, Any]]:
        types = [TYPES[m] for m in (scope.modalities or self.modalities) if m in TYPES]
        seen: dict[str, dict[str, Any]] = {}
        pages = max(1, math.ceil(ctx.limit / PAGE_SIZE))
        for subdomain in base.subdomains_for(scope):
            for language in scope.languages or [None]:
                for term in base.search_terms(subdomain, language):
                    for rtype in types:
                        for record in self._search(term, language, rtype, ctx, pages):
                            cand = self._candidate(record, rtype, subdomain, seen)
                            if cand is not None:
                                yield cand

    def _search(self, term: str, language: str | None, rtype: str, ctx: base.Context,
                pages: int) -> Iterator[dict[str, Any]]:
        query = '"{}"'.format(term.replace('"', ""))
        if language:
            codes = iso639_3(language)
            if codes:
                query += f" AND metadata.languages.id:({' OR '.join(codes)})"
        for page in range(1, pages + 1):
            params = {"q": query, "type": rtype, "size": PAGE_SIZE, "page": page, "sort": "bestmatch"}
            try:
                resp = ctx.client.get(API, params=params)
                resp.raise_for_status()
                hits = (resp.json().get("hits") or {}).get("hits") or []
            except (httpx.HTTPError, ValueError) as e:
                ctx.say(f"zenodo: {term!r} ({rtype}) page {page}: {type(e).__name__}: {e}")
                return
            yield from hits
            if len(hits) < PAGE_SIZE:
                return

    def _candidate(self, record: dict[str, Any], wanted: str, subdomain: str,
                   seen: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        metadata = record.get("metadata") or {}
        rid = record.get("id")
        title = str(metadata.get("title") or record.get("title") or "").strip()
        if not rid or not title:
            return None
        rtype = (metadata.get("resource_type") or {}).get("type")
        if rtype != wanted or (metadata.get("access_right") or "open") != "open":
            return None
        landing = (record.get("links") or {}).get("self_html") or LANDING.format(id=rid)
        if landing in seen:
            known = seen[landing]
            if subdomain not in known["subdomains"]:
                known["subdomains"].append(subdomain)
                known["topics"] = _topics(known["subdomains"])
            return None
        lic = metadata.get("license") or {}
        lid = base.spdx(lic.get("id") if isinstance(lic, dict) else lic)
        licence = base.licence_block(lid, None, landing)
        modality, genre = _genre(record, title)
        publisher, kind = _publisher(metadata)
        doi = str(record.get("doi") or metadata.get("doi") or "").strip()
        subdomains = [subdomain]
        cand = base.candidate(
            self,
            title=title,
            title_en=None,
            languages=[metadata["language"]] if metadata.get("language") else [],
            area="001",
            publisher=publisher,
            kind=kind,
            landing_url=landing,
            modality=modality,
            genre=genre,
            subdomains=subdomains,
            licence=licence,
            access=_access(record, landing),
            evidence=[landing],
            topics=_topics(subdomains),
            level="item",
            identifiers={"doi": doi} if DOI.match(doi) else None,
        )
        seen[landing] = cand
        return cand
