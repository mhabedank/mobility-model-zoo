"""Propose source records from local metadata (`zoo compliance bootstrap-sources`, research R13).

Inputs (all local or public metadata, never source text): `data/snapshots/*/source.yaml`, the source
plan `data/sources/source-plan.yaml`, the release record's provenance, chunk files of a benchmark
config (snapshot ids only), the Zenodo and Crossref APIs for titles, creators and licences, and a
retrospective opt-out signal check of each origin. Nothing is invented: values that cannot be found
are written as `unknown` with the date of the attempt.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

from mobility_model_zoo.compliance import signals
from mobility_model_zoo.compliance.findings import UNKNOWN

MODIFICATIONS = (
    "Text extracted from the source document, split into chunks, personal identifiers "
    "redacted and labeled by language models; the text itself is not redistributed."
)

# free-text licence in source.yaml -> (SPDX id or LicenseRef, licence URL or None)
LICENCES: list[tuple[str, str, str | None]] = [
    (
        r"^CC-BY(-4\.0)?$|PSI Licence \(CC BY 4\.0\)",
        "CC-BY-4.0",
        "https://creativecommons.org/licenses/by/4.0/",
    ),
    (r"^CC-BY-NC-ND-4\.0$", "CC-BY-NC-ND-4.0", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
    (r"^CC-BY-NC-4\.0$", "CC-BY-NC-4.0", "https://creativecommons.org/licenses/by-nc/4.0/"),
    (
        r"Open Parliament Licence",
        "LicenseRef-Open-Parliament-Licence",
        "https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/",
    ),
    (r"public domain.*17 U\.S\.C", "LicenseRef-US-PD", "https://www.law.cornell.edu/uscode/text/17/105"),
    (
        r"amtliches Werk § 5 UrhG$",
        "LicenseRef-official-work-UrhG-5",
        "https://www.gesetze-im-internet.de/urhg/__5.html",
    ),
    (
        r"amtliches Werk \((assumed|by analogy)\)|§ 5 UrhG status not confirmed",
        "LicenseRef-official-work-UrhG-5-unconfirmed",
        "https://www.gesetze-im-internet.de/urhg/__5.html",
    ),
    (
        r"öUrhG",
        "LicenseRef-official-work-AT-7",
        "https://www.ris.bka.gv.at/eli/bgbl/1936/111/P7/NOR12082917",
    ),
    (
        r"URG",
        "LicenseRef-official-work-CH-5",
        "https://www.fedlex.admin.ch/eli/cc/1993/1798_1798_1798/de#art_5",
    ),
    (
        r"Senedd Commission copyright",
        "LicenseRef-Senedd-Commission-Copyright",
        "https://research.senedd.wales/commission/access-to-information/copyright/",
    ),
    (
        r"Scottish Parliament copyright",
        "LicenseRef-Scottish-Parliament-Licence",
        "https://www.parliament.scot/about/copyright",
    ),
    (
        r"© European Union, reuse with attribution",
        "LicenseRef-EU-Reuse-Decision-2011-833",
        "https://eur-lex.europa.eu/eli/dec/2011/833/oj",
    ),
    (r"non-commercial|House of Commons Canada", "LicenseRef-noncommercial-reproduction", None),
    (r"none stated|unclear|^©|authors keep copyright", "LicenseRef-all-rights-reserved", None),
]

PUBLISHERS = {
    "bundestag.de": "Deutscher Bundestag",
    "dserver.bundestag.de": "Deutscher Bundestag",
    "parliament.uk": "UK Parliament",
    "committees-api.parliament.uk": "UK Parliament",
    "hansard-api.parliament.uk": "UK Parliament",
    "oireachtas.ie": "Houses of the Oireachtas",
    "govinfo.gov": "U.S. Government Publishing Office",
    "senedd.wales": "Senedd Cymru",
    "parliament.scot": "The Scottish Parliament",
    "europarl.europa.eu": "European Parliament",
    "parlament.gv.at": "Österreichisches Parlament",
    "parlament.ch": "Schweizer Parlament",
    "ourcommons.ca": "House of Commons of Canada",
    "parlament-berlin.de": "Abgeordnetenhaus Berlin",
    "bayern.landtag.de": "Bayerischer Landtag",
    "landtag-bw.de": "Landtag von Baden-Württemberg",
    "landtag-niedersachsen.de": "Niedersächsischer Landtag",
    "bpb.de": "Bundeszentrale für politische Bildung",
    "oeko.de": "Öko-Institut",
    "zenodo.org": "Zenodo (CERN)",
    "boeckler.de": "Hans-Böckler-Stiftung",
    "agora-verkehrswende.de": "Agora Verkehrswende",
    "stiftung-mercator.de": "Stiftung Mercator",
    "mobilitaet-in-deutschland.de": "infas / BMDV (Mobilität in Deutschland)",
    "econstor.eu": "ZBW econstor",
    "elib.dlr.de": "Deutsches Zentrum für Luft- und Raumfahrt (DLR)",
    "ebi.ac.uk": "Europe PMC (EMBL-EBI)",
    "pmc.ncbi.nlm.nih.gov": "PubMed Central (NLM)",
    "beteiligungsportal.baden-wuerttemberg.de": "Beteiligungsportal Baden-Württemberg",
}
PARLIAMENT_HOSTS = (
    "bundestag",
    "parliament",
    "oireachtas",
    "govinfo",
    "senedd",
    "europarl",
    "parlament",
    "ourcommons",
    "landtag",
)
CONSENT = re.compile(
    r"(?i)(informed consent|consent|einwilligung|einverständnis|ethics (committee|approval|board)|"
    r"ethikkommission|ethikvotum|institutional review board|\bIRB\b)"
)
ANONYMISED = re.compile(r"(?i)(anonymi[sz]|pseudonymi[sz])")


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def licence_of(text: str) -> tuple[str, str | None]:
    for pattern, spdx, url in LICENCES:
        if re.search(pattern, text or ""):
            return spdx, url
    return UNKNOWN, None


def publisher_of(url: str) -> str | None:
    host = _host(url)
    for key in sorted(PUBLISHERS, key=len, reverse=True):
        if host == key or host.endswith("." + key):
            return PUBLISHERS[key]
    return None


def class_of(source_type: str, url: str, permitted: str, spdx: str) -> str:
    host = _host(url)
    if source_type == "forum_review":
        return "forum-review"
    if "zenodo.org" in host:
        return "research-interviews"
    if source_type == "transcript" and any(k in host for k in PARLIAMENT_HOSTS):
        return "parliamentary-records"
    if spdx.startswith("CC-BY") and "-N" not in spdx and permitted == "training_allowed":
        return "open-papers"
    return "tdm-documents"


def slug(url: str, used: set[str]) -> str:
    p = urlparse(url)
    base = re.sub(r"[^a-z0-9]+", "-", f"{_host(url)}{p.path}".lower()).strip("-")[:60].strip("-")
    candidate, n = base, 2
    while candidate in used:
        candidate, n = f"{base}-{n}", n + 1
    used.add(candidate)
    return candidate


class Metadata:
    """Zenodo and Crossref lookups (titles, creators, licences, descriptions)."""

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=30, headers={"User-Agent": signals.USER_AGENT})

    def zenodo(self, url: str) -> dict[str, Any] | None:
        m = re.search(r"zenodo\.org/(?:records?|api/records)/(\d+)", url)
        if not m:
            return None
        try:
            r = self.client.get(f"https://zenodo.org/api/records/{m.group(1)}")
            r.raise_for_status()
        except httpx.HTTPError:
            return None
        meta = r.json().get("metadata", {})
        return {
            "title": meta.get("title"),
            "creators": [c.get("name") for c in meta.get("creators", []) if c.get("name")],
            "licence": (meta.get("license") or {}).get("id"),
            "description": re.sub(r"<[^>]+>", " ", meta.get("description") or ""),
        }

    def crossref(self, url: str) -> dict[str, Any] | None:
        m = re.search(r"doi\.org/(10\.[^\s?#]+)", url)
        if not m:
            return None
        try:
            r = self.client.get(f"https://api.crossref.org/works/{m.group(1)}")
            r.raise_for_status()
        except httpx.HTTPError:
            return None
        msg = r.json().get("message", {})
        creators = [
            " ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name", "")
            for a in msg.get("author", [])
        ]
        return {
            "title": (msg.get("title") or [None])[0],
            "creators": [c for c in creators if c],
            "publisher": msg.get("publisher"),
        }


def load_snapshots(root: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for path in sorted((root / "data" / "snapshots").glob("*/source.yaml")):
        meta = yaml.safe_load(path.read_text(encoding="utf-8"))
        out[meta["snapshot_id"]] = meta
    return out


def plan_titles(root: Path) -> dict[str, str]:
    path = root / "data" / "sources" / "source-plan.yaml"
    if not path.exists():
        return {}
    plan = yaml.safe_load(path.read_text(encoding="utf-8"))
    titles = {}
    for section in ("papers", "transcripts", "forum_review"):
        for item in plan.get(section) or []:
            if item.get("url") and (item.get("title") or item.get("name")):
                titles[signals.canonical(item["url"])] = item.get("title") or item.get("name")
    return titles


def benchmark_snapshot_ids(root: Path, config: Path) -> set[str]:
    from mobility_model_zoo.productdev.jtbd.config import load_settings

    settings = load_settings(config)
    ids = set()
    for path in sorted(settings.chunks_dir.glob("*.json")):
        chunk = json.loads(path.read_text(encoding="utf-8"))
        if chunk.get("split") in ("main", "holdout"):
            ids.add(chunk["snapshot_id"])
    return ids


def build(
    root: Path,
    *,
    model: str,
    version: str,
    release_record: dict[str, Any],
    benchmark: str | None,
    benchmark_ids: set[str],
    meta: Metadata,
    check: Callable[[str], signals.Verdict] | None,
    today: dt.date,
    used_by_versions: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (source records, owner decision items)."""
    snapshots = load_snapshots(root)
    titles = plan_titles(root)
    training = {s["origin"] for s in release_record["provenance"]["sources"]}
    by_origin: dict[str, list[dict[str, Any]]] = {}
    for snap in snapshots.values():
        if snap["origin_url"] in training or snap["snapshot_id"] in benchmark_ids:
            by_origin.setdefault(snap["origin_url"], []).append(snap)
    missing = sorted(training - set(by_origin))
    items: list[str] = [f"training origin without a local snapshot: {u}" for u in missing]
    records, used = [], set()
    stamp = today.isoformat()
    for origin in sorted(by_origin):
        snaps = by_origin[origin]
        first = snaps[0]
        spdx, licence_url = licence_of(first["license"])
        permitted = "training_allowed" if origin in training else "benchmark_only"
        cls = class_of(first["source_type"], origin, permitted, spdx)
        z = meta.zenodo(origin) if "zenodo.org" in origin else None
        c = meta.crossref(origin) if "doi.org" in origin else None
        title = (z or c or {}).get("title") or titles.get(signals.canonical(origin))
        creators: Any = (z or c or {}).get("creators") or None
        publisher = (c or {}).get("publisher") or publisher_of(origin)
        if cls == "parliamentary-records" and not creators and publisher:
            creators = [publisher]
        if cls == "forum-review":
            creators = [f"contributors of {_host(origin)} (not named; usernames redacted)"]
        rec: dict[str, Any] = {
            "id": slug(origin, used),
            "class": cls,
            "origin_url": origin,
            "title": title or f"{publisher or _host(origin)}: {urlparse(origin).path}",
            "creators": creators or UNKNOWN,
            "publisher": publisher or _host(origin),
            "licence": spdx,
            "licence_url": licence_url
            or (None if spdx.startswith("LicenseRef-all-rights") else UNKNOWN),
            "attribution_text": "",
            "modifications": MODIFICATIONS,
            "permitted_use": permitted,
            "redistribution": "not_allowed",
            "redistribution_basis": "Training and benchmark texts are never redistributed "
            "(constitution VI).",
            "quote_allowed": cls == "parliamentary-records"
            and spdx.startswith("LicenseRef-official-work-UrhG-5")
            and "unconfirmed" not in spdx
            or spdx == "CC-BY-4.0",
            "personal_data": {
                "present": cls in ("parliamentary-records", "research-interviews", "forum-review"),
                "categories": {
                    "parliamentary-records": ["names of office holders and witnesses"],
                    "research-interviews": ["interview statements (pseudonymised by the dataset)"],
                    "forum-review": ["forum posts (usernames redacted)"],
                }.get(cls, []),
                "special_categories": [],
                "human_subjects": cls == "research-interviews",
            },
            "storage": "data/snapshots (outside git)",
            "retention_until": max((str(s.get("retention_until") or "")) for s in snaps) or UNKNOWN,
            "used_by": ([f"{model}@{v}" for v in used_by_versions] if origin in training else [])
            + (
                [f"benchmark:{benchmark}"]
                if benchmark and any(s["snapshot_id"] in benchmark_ids for s in snaps)
                else []
            ),
            "owner": "Martin Habedank",
            "last_reviewed": stamp,
            "next_review": (today + dt.timedelta(days=182)).isoformat(),
        }
        if (
            spdx == UNKNOWN
            or rec["creators"] == UNKNOWN
            or rec["licence_url"] == UNKNOWN
            or rec["retention_until"] == UNKNOWN
        ):
            rec["unknown_checked_at"] = stamp
        if cls == "research-interviews":
            text = (z or {}).get("description") or ""
            m = CONSENT.search(text)
            a = ANONYMISED.search(text)
            if a:
                rec["personal_data"]["anonymisation"] = _sentence(text, a)
            if m:
                rec["personal_data"]["consent_or_ethics"] = _sentence(text, m)
            else:
                rec["personal_data"]["consent_or_ethics"] = UNKNOWN
                rec["unknown_checked_at"] = stamp
                items.append(f"{rec['id']}: no consent or ethics statement found in the Zenodo record")
        rec["attribution_text"] = attribution(rec)
        rec["signals"] = retro_signals(origin, check, stamp)
        if rec["signals"].get("error"):
            items.append(f"{rec['id']}: retrospective signal check failed ({rec['signals']['error']})")
        elif any(
            rec["signals"][k] == "deny" for k in ("robots", "tdmrep", "x_robots", "meta_noai", "ai_txt")
        ):
            items.append(
                f"{rec['id']}: an opt-out signal is present today (used_by: {', '.join(rec['used_by'])})"
            )
        records.append(rec)
    return records, items


def _sentence(text: str, m: re.Match) -> str:
    start = text.rfind(".", 0, m.start()) + 1
    end = text.find(".", m.end())
    return " ".join(text[start : (end + 1) if end >= 0 else len(text)].split())[:400]


def attribution(rec: dict[str, Any]) -> str:
    creators = rec["creators"]
    by = ", ".join(creators) if isinstance(creators, list) else "creators unknown"
    licence = rec["licence"].removeprefix("LicenseRef-").replace("-", " ")
    return f'"{rec["title"]}" by {by} ({rec["publisher"]}), {rec["origin_url"]}, {licence}.'


def retro_signals(
    origin: str, check: Callable[[str], signals.Verdict] | None, stamp: str
) -> dict[str, Any]:
    base = {
        "robots": "absent",
        "tdmrep": "absent",
        "x_robots": "absent",
        "meta_noai": "absent",
        "ai_txt": "absent",
        "checked_at": stamp,
        "retrospective": True,
    }
    if check is None:
        return {**base, "error": "not checked"}
    v = check(origin)
    out = {
        **base,
        "robots": v.robots,
        "tdmrep": v.tdmrep,
        "x_robots": v.x_robots,
        "meta_noai": v.meta_noai,
        "ai_txt": v.ai_txt,
    }
    unreachable = [r for c, r in v.reasons if "unreachable" in r]
    if unreachable:
        out["error"] = "; ".join(unreachable)
    return out
