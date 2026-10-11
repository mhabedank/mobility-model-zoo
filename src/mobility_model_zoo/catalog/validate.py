"""Offline checks of catalog entries: K1 schema and vocabulary, K2 integrity, K3 duplicates (R7),
K9 personal data in metadata (FR-031). K8 (usage rules) lives in rules.py. No network.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import jsonschema
from rapidfuzz import fuzz

from mobility_model_zoo.catalog.model import Catalog, entry_path, schema, vocab
from mobility_model_zoo.compliance.scan import pii
from mobility_model_zoo.compliance.signals import canonical

FUZZY_THRESHOLD = 92
LICENCE_ID = re.compile(r"^([A-Za-z0-9.+-]+|LicenseRef-[A-Za-z0-9.-]+|unknown|mixed)$")
# K9: in addresses, a handle or a user path warns (FR-031)
HANDLE_URL = re.compile(r"@[A-Za-z0-9_]{2,}|/user/|/u/|[?&]user=", re.IGNORECASE)
CONTACT_KINDS = {
    "email",
    "phone_labeled",
    "phone_international",
    "phone_de",
    "iban",
    "postal_address_de",
    "tax_id_de",
    "date_of_birth",
}


@dataclass(frozen=True)
class Finding:
    entry_id: str
    check: str
    severity: str  # fail | warn
    field: str
    message: str
    flag: str | None = None

    def line(self) -> str:
        return f"{self.severity.upper()} {self.entry_id} {self.check} {self.field}: {self.message}"


def _path(error: jsonschema.ValidationError) -> str:
    out = ""
    for part in error.absolute_path:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "(entry)"


# ---- K1 ----------------------------------------------------------------------------------------


def k1(entry: dict[str, Any]) -> list[Finding]:
    eid = str(entry.get("id", "?"))
    v = vocab()
    out: list[Finding] = []
    validator = jsonschema.Draft202012Validator(schema("entry"))
    for err in sorted(validator.iter_errors(entry), key=lambda e: list(e.absolute_path)):
        if _path(err) == "subdomains" and err.validator == "minItems":
            continue  # reported below with the scope reason
        out.append(Finding(eid, "K1", "fail", _path(err), err.message))

    def bad(field: str, value: Any, allowed: Iterable[str], name: str) -> None:
        allowed = list(allowed)
        hint = ", ".join(allowed) if len(allowed) <= 25 else f"see vocab {name} v{v.version}"
        out.append(Finding(eid, "K1", "fail", field, f"{value!r} is not in vocab {name} ({hint})"))

    codes = [lang.get("code") for lang in entry.get("languages") or [] if isinstance(lang, dict)]
    for i, code in enumerate(codes):
        if code not in v.languages:
            bad(f"languages[{i}].code", code, v.languages, "languages")
    if len(codes) > 1 and ({"zxx", "und"} & set(codes)):
        out.append(
            Finding(eid, "K1", "fail", "languages", "zxx and und cannot be combined with other codes")
        )
    transcripts = ((entry.get("content") or {}).get("transcripts") or {}).get("languages") or []
    for i, code in enumerate(transcripts):
        if code not in v.languages:
            bad(f"content.transcripts.languages[{i}]", code, v.languages, "languages")
    area = entry.get("origin_area")
    if area is not None and str(area) not in v.areas:
        bad("origin_area", area, sorted(v.areas), "areas")
    kind = (entry.get("publisher") or {}).get("kind")
    if kind is not None and kind not in v.kinds:
        bad("publisher.kind", kind, v.kinds, "source-kinds")
    rtype = entry.get("resource_type") or {}
    modality, genre = rtype.get("modality"), rtype.get("genre")
    if modality in v.modalities and genre not in v.genres(modality):
        bad("resource_type.genre", genre, v.genres(modality), f"resource-types ({modality})")
    for i, topic in enumerate(entry.get("topics") or []):
        if topic not in v.topics:
            bad(f"topics[{i}]", topic, v.topics, "topics")
    subdomains = entry.get("subdomains")
    if isinstance(subdomains, list) and not subdomains:
        out.append(
            Finding(eid, "K1", "fail", "subdomains", "no mobility subdomain: out of scope (FR-003)")
        )
    for i, sub in enumerate(subdomains or []):
        if sub not in v.subdomains:
            bad(f"subdomains[{i}]", sub, v.subdomains, "subdomains")
    freq = (entry.get("content") or {}).get("frequency")
    if freq is not None and freq not in v.frequencies:
        bad("content.frequency", freq, v.frequencies, "frequencies")
    return _dedupe(out)


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen, out = set(), []
    for f in findings:
        if (f.field, f.message) not in seen:
            seen.add((f.field, f.message))
            out.append(f)
    return out


# ---- K2 ----------------------------------------------------------------------------------------


def k2(cat: Catalog) -> list[Finding]:
    out: list[Finding] = []
    for file, reason in cat.load_errors:
        out.append(Finding(file, "K2", "fail", "(file)", reason))
    for eid, e in cat.entries.items():
        parent = e.get("parent")
        if parent is not None:
            p = cat.entries.get(parent)
            if p is None:
                out.append(Finding(eid, "K2", "fail", "parent", f"parent {parent} does not exist"))
            elif p.get("level") != "collection":
                out.append(Finding(eid, "K2", "fail", "parent", f"parent {parent} is not a collection"))
        rel = e.get("relations") or {}
        for target in (rel.get("translation_of") or []) + [rel.get("duplicate_of")]:
            if target and target not in cat.entries:
                out.append(Finding(eid, "K2", "fail", "relations", f"{target} does not exist"))
        if "origin_area" in e and "id" in e:
            expected = entry_path(cat.root, e)
            if cat.paths.get(eid) and cat.paths[eid].resolve() != expected.resolve():
                rel_expected = expected.relative_to(cat.root).as_posix()
                out.append(Finding(eid, "K2", "fail", "(file)", f"file must be {rel_expected}"))
    return out


# ---- K3 (R7) -----------------------------------------------------------------------------------


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", text.lower()).split())


# An access address identifies a resource only if it is a feed or a file. Service endpoints, catalogue
# search pages and publisher home pages are shared by many datasets (batch 1, 2026-10-11).
IDENTITY_METHODS = {"direct_download", "bulk_dump"}
FILE_PATH = re.compile(
    r"\.(zip|csv|tsv|json|geojson|jsonl|xml|xlsx?|ods|parquet|gpkg|kmz|kml|gtfs|txt|pdf|gz|7z|shp|"
    r"mp3|mp4|wav|ogg|webm|png|jpe?g|svg|tiff?)$",
    re.IGNORECASE,
)


def identifies(route: dict[str, Any]) -> bool:
    """True if the access route's address names this one resource (a feed or a file)."""
    url = str(route.get("url") or "")
    if not url:
        return False
    if route.get("method") == "feed":
        return True
    return route.get("method") in IDENTITY_METHODS and bool(FILE_PATH.search(urlparse(url).path))


def keys(entry: dict[str, Any]) -> dict[str, set[str]]:
    urls = {canonical(entry["landing_url"])} if entry.get("landing_url") else set()
    urls |= {canonical(a["url"]) for a in entry.get("access") or [] if identifies(a)}
    ids = set()
    ident = entry.get("identifiers") or {}
    if ident.get("doi"):
        ids.add("doi:" + ident["doi"].lower())
    ids |= {str(x).lower() for x in ident.get("other") or []}
    return {"url": urls, "id": ids}


def fuzzy_key(entry: dict[str, Any]) -> str:
    title = (entry.get("title") or {}).get("original", "")
    return _norm(f"{title} {(entry.get('publisher') or {}).get('name', '')}")


@dataclass
class DedupeIndex:
    """Exact keys (canonical URLs, persistent ids) and fuzzy keys of known entries (R7)."""

    url: dict[str, str]
    pid: dict[str, str]
    fuzzy: dict[str, str]

    @classmethod
    def build(cls, entries: Iterable[dict[str, Any]]) -> DedupeIndex:
        idx = cls({}, {}, {})
        for e in entries:
            idx.add(e)
        return idx

    def add(self, e: dict[str, Any]) -> None:
        k = keys(e)
        for u in k["url"]:
            self.url.setdefault(u, e["id"])
        for i in k["id"]:
            self.pid.setdefault(i, e["id"])
        self.fuzzy.setdefault(fuzzy_key(e), e["id"])

    def exact(self, e: dict[str, Any]) -> tuple[str, str] | None:
        """(existing id, reason) for a match on a canonical URL or a persistent identifier."""
        k = keys(e)
        for i in sorted(k["id"]):
            if i in self.pid and self.pid[i] != e.get("id"):
                return self.pid[i], f"same identifier {i}"
        for u in sorted(k["url"]):
            if u in self.url and self.url[u] != e.get("id"):
                return self.url[u], f"same address {u}"
        return None

    def similar(self, e: dict[str, Any]) -> list[str]:
        key = fuzzy_key(e)
        if not key:
            return []
        return sorted(
            other
            for k, other in self.fuzzy.items()
            if other != e.get("id") and fuzz.token_sort_ratio(key, k) >= FUZZY_THRESHOLD
        )


def k3(cat: Catalog) -> list[Finding]:
    out: list[Finding] = []
    idx = DedupeIndex({}, {}, {})
    for eid in sorted(cat.entries):
        e = cat.entries[eid]
        if e.get("status", {}).get("value") in ("rejected",):
            continue
        dup_of = (e.get("relations") or {}).get("duplicate_of")
        match = idx.exact(e)
        if (
            match
            and dup_of != match[0]
            and (cat.entries[match[0]].get("relations") or {}).get("duplicate_of") != eid
        ):
            out.append(Finding(eid, "K3", "fail", "(entry)", f"duplicate of {match[0]}: {match[1]}"))
        for other in idx.similar(e):
            if other != dup_of:
                out.append(
                    Finding(
                        eid,
                        "K3",
                        "warn",
                        "title",
                        f"possibly the same resource as {other}",
                        flag="possible_duplicate",
                    )
                )
        idx.add(e)
    return out


# ---- K9 (FR-031) -------------------------------------------------------------------------------


def k9(entry: dict[str, Any]) -> list[Finding]:
    eid = str(entry.get("id", "?"))
    out: list[Finding] = []
    title = entry.get("title") or {}
    texts = {
        "title.original": title.get("original") or "",
        "title.en": title.get("en") or "",
        "description": entry.get("description") or "",
        "publisher.name": (entry.get("publisher") or {}).get("name") or "",
    }
    for field_name, text in texts.items():
        for hit in pii(text):
            if hit.kind in CONTACT_KINDS:
                out.append(Finding(eid, "K9", "fail", field_name, f"contact data ({hit.kind})"))
            else:
                out.append(
                    Finding(
                        eid,
                        "K9",
                        "warn",
                        field_name,
                        f"possible personal data ({hit.kind})",
                        flag="personal_data_in_metadata",
                    )
                )
    urls = {"landing_url": entry.get("landing_url") or ""}
    urls |= {f"access[{i}].url": a.get("url") or "" for i, a in enumerate(entry.get("access") or [])}
    for field_name, url in urls.items():
        if HANDLE_URL.search(url):
            out.append(
                Finding(
                    eid,
                    "K9",
                    "warn",
                    field_name,
                    "user handle or user path in address",
                    flag="personal_data_in_metadata",
                )
            )
    return _dedupe(out)


# ---- all offline checks ------------------------------------------------------------------------


def offline(cat: Catalog, *, allowlist: list[dict[str, Any]] | None = None) -> list[Finding]:
    """K1, K2, K3, K9 and, with an allow-list, K8 (stored usage matches the rules)."""
    from mobility_model_zoo.catalog import rules

    out: list[Finding] = []
    for eid in sorted(cat.entries):
        e = cat.entries[eid]
        out += k1(e)
        out += k9(e)
        if allowlist is not None:
            out += rules.k8(e, allowlist)
    out += k2(cat)
    out += k3(cat)
    return out
