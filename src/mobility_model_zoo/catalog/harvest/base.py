"""Common parts of the harvesters (research R6, contracts/cli.md `zoo catalog harvest`).

A harvester queries one catalogue API and yields candidates (candidate.schema.json). It never
downloads resource content and never stores abstracts or descriptions from the catalogue (FR-032):
candidates carry no `description`. Judgment fields come from defaults.yaml.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any, Protocol

import httpx
import yaml

from mobility_model_zoo.catalog.checks import Throttle, make_client
from mobility_model_zoo.catalog.model import dump_yaml, vocab
from mobility_model_zoo.release.errors import CredentialError, UsageError

HERE = Path(__file__).resolve().parent


class BudgetExhausted(Exception):
    """The harvester reached its share of a free daily allowance and stops early."""


@dataclass
class Budget:
    """Counts billable requests; stops at `stop_share` of `allowance` (OpenAlex free tier, R6)."""

    allowance: float
    stop_share: float = 0.8
    spent: float = 0.0

    def spend(self, cost: float = 1.0) -> None:
        if self.spent + cost > self.allowance * self.stop_share:
            raise BudgetExhausted(
                f"spent {self.spent:g} of {self.allowance:g}; stopping at {self.stop_share:.0%}"
            )
        self.spent += cost


@dataclass
class Scope:
    languages: list[str] = field(default_factory=list)
    areas: list[str] = field(default_factory=list)
    subdomains: list[str] = field(default_factory=list)
    modalities: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "languages": self.languages,
            "areas": self.areas,
            "subdomains": self.subdomains,
            "modalities": self.modalities,
        }


@dataclass
class Context:
    client: httpx.Client
    env: dict[str, str]
    limit: int
    say: Callable[[str], None]
    budget: Budget | None = None


class Harvester(Protocol):
    name: str  # e.g. "openalex"
    catalogue: str  # human name for quality rationales, e.g. "OpenAlex"
    env_keys: tuple[str, ...]
    modalities: tuple[str, ...]  # modalities it can yield (run scope)
    method: str  # one line for the run header

    def iterate(self, scope: Scope, ctx: Context) -> Iterator[dict[str, Any]]: ...


# ---- defaults, terms and licences ---------------------------------------------------------------


@cache
def defaults() -> dict[str, Any]:
    return yaml.safe_load((HERE / "defaults.yaml").read_text(encoding="utf-8"))


@cache
def terms() -> dict[str, dict[str, list[str]]]:
    return yaml.safe_load((HERE / "terms.yaml").read_text(encoding="utf-8"))["subdomains"]


def search_terms(subdomain: str, language: str | None) -> list[str]:
    by_lang = terms().get(subdomain) or {}
    return list(by_lang.get(language or "en") or by_lang.get("en") or [])


def subdomains_for(scope: Scope) -> list[str]:
    return scope.subdomains or list(terms())


def personal_data(genre: str) -> dict[str, Any]:
    pd = defaults()["personal_data"].get(genre) or {"expectation": "possible", "categories": []}
    return {"expectation": pd["expectation"], "categories": list(pd["categories"])}


def quality(catalogue: str, kind: str) -> dict[str, Any]:
    q = defaults()["quality"]
    return {"score": int(q["score"]), "rationale": q["rationale"].format(catalogue=catalogue, kind=kind)}


CC = re.compile(r"creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/(\d\.\d)", re.IGNORECASE)
SPDX_ALIASES = {
    "cc-by": "CC-BY-4.0",
    "cc-by-4.0": "CC-BY-4.0",
    "cc by 4.0": "CC-BY-4.0",
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc0": "CC0-1.0",
    "cc0-1.0": "CC0-1.0",
    "cc-zero": "CC0-1.0",
    "public-domain": "LicenseRef-public-domain",
    # versionless Creative Commons ids (OpenAlex): read as 4.0, the version base assumes for cc-by
    "cc-by-sa": "CC-BY-SA-4.0",
    "cc-by-nd": "CC-BY-ND-4.0",
    "cc-by-nc": "CC-BY-NC-4.0",
    "cc-by-nc-sa": "CC-BY-NC-SA-4.0",
    "cc-by-nc-nd": "CC-BY-NC-ND-4.0",
    "cc-by-nc-4.0": "CC-BY-NC-4.0",
    "cc-by-nc-sa-4.0": "CC-BY-NC-SA-4.0",
    "cc-by-nd-4.0": "CC-BY-ND-4.0",
    "cc-by-nc-nd-4.0": "CC-BY-NC-ND-4.0",
    "cc-by-3.0": "CC-BY-3.0",
    "cc-by-sa-3.0": "CC-BY-SA-3.0",
    "odc-by": "ODC-By-1.0",
    "odc-by-1.0": "ODC-By-1.0",
    "pddl": "PDDL-1.0",
    "odbl": "ODbL-1.0",
    "odbl-1.0": "ODbL-1.0",
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "etalab-2.0": "etalab-2.0",
    "ogl-uk-3.0": "LicenseRef-OGL-UK-3.0",
    "dl-de-by-2.0": "DL-DE-BY-2.0",
    "dl-de-zero-2.0": "DL-DE-ZERO-2.0",
}


def spdx(value: str | None) -> str:
    """Best-effort SPDX id from a licence name, id or URL; `unknown` when nothing matches."""
    if not value:
        return "unknown"
    text = str(value).strip()
    m = CC.search(text)
    if m:
        kind, code, version = m.group(1).lower(), m.group(2).lower(), m.group(3)
        if kind == "publicdomain":
            return "CC0-1.0" if code == "zero" else "unknown"
        return f"CC-{code.upper()}-{version}"
    key = text.lower().replace("_", "-").rstrip("/")
    return SPDX_ALIASES.get(key, SPDX_ALIASES.get(key.replace(" ", "-"), "unknown"))


def licence_block(licence_id: str, url: str | None, evidence: str | None) -> dict[str, Any]:
    cc = licence_id.startswith(("CC-BY", "CC0"))
    return {
        "id": licence_id,
        "url": url,
        "evidence_url": evidence if licence_id != "unknown" else None,
        "attribution_required": "yes"
        if licence_id.startswith("CC-BY") or licence_id == "ODC-By-1.0"
        else ("no" if licence_id in ("CC0-1.0", "PDDL-1.0") else "unknown"),
        "attribution_text": None,
        "commercial_use": "no" if "-NC" in licence_id else ("yes" if cc else "unknown"),
        "share_alike": True if "-SA" in licence_id else (False if cc else None),
        "derivatives": "no" if "-ND" in licence_id else ("yes" if cc else "unknown"),
    }


def language_code(code: str | None) -> str:
    """BCP 47 code of the vocabulary from ISO 639-1/-3 or a locale; `und` if unknown."""
    if not code:
        return "und"
    raw = str(code).strip().replace("_", "-")
    v = vocab().languages
    if raw in v:
        return raw
    primary = raw.split("-")[0].lower()
    if primary in v:
        return primary
    from mobility_model_zoo.catalog.harvest.iso639 import THREE_TO_TWO

    return THREE_TO_TWO.get(primary, "und")


SECRET_PARAMS = re.compile(
    r"(?i)^(token|access_?token|api_?key|apikey|key|secret|signature|sig|auth|password)$"
)


def strip_secrets(url: str | None) -> str | None:
    """Drop credential-like query parameters (`?token=…`) so no secret enters the catalog."""
    if not url or "?" not in url:
        return url
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    kept = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not SECRET_PARAMS.match(k)
    ]
    return urlunsplit(parts._replace(query=urlencode(kept)))


def candidate(
    harvester: Harvester,
    *,
    title: str,
    title_en: str | None,
    languages: list[str],
    area: str,
    publisher: str,
    kind: str,
    landing_url: str,
    modality: str,
    genre: str,
    subdomains: list[str],
    licence: dict[str, Any],
    access: list[dict[str, Any]],
    evidence: list[str],
    topics: list[str] | None = None,
    level: str = "collection",
    content: dict[str, Any] | None = None,
    identifiers: dict[str, Any] | None = None,
    method: str = "harvest",
) -> dict[str, Any]:
    langs = [language_code(code) for code in languages] or ["und"]
    langs = list(dict.fromkeys(langs))
    if len(langs) > 1 and ("und" in langs or "zxx" in langs):
        langs = [code for code in langs if code not in ("und", "zxx")] or ["und"]
    access = [
        {
            **route,
            "url": strip_secrets(route["url"]),
            **(
                {"download_url": strip_secrets(route["download_url"])}
                if route.get("download_url")
                else {}
            ),
        }
        for route in access
    ]
    landing_url = strip_secrets(landing_url) or landing_url
    out: dict[str, Any] = {
        "level": level,
        "title": {"original": title.strip()[:300], "en": (title_en or title).strip()[:300]},
        "languages": [
            {"code": code, "origin": "original" if code not in ("und", "zxx") else "unknown"}
            for code in langs
        ],
        "origin_area": area,
        "publisher": {"name": publisher.strip()[:200] or "unknown publisher", "kind": kind},
        "landing_url": landing_url,
        "resource_type": {"modality": modality, "genre": genre},
        "topics": topics or ["productdev"],
        "subdomains": subdomains,
        "licence": licence,
        "personal_data": personal_data(genre),
        "access": access,
        "quality": quality(harvester.catalogue, kind),
        "provenance": {"method": method, "evidence": evidence},
    }
    if langs == ["zxx"]:
        out["languages"] = [{"code": "zxx", "origin": "original"}]
    if content:
        out["content"] = content
    if modality in ("audio", "video", "image", "graphic"):
        out.setdefault("content", {}).setdefault("transcripts", {"available": "unknown"})
    if identifiers:
        out["identifiers"] = identifiers
    return out


# ---- running --------------------------------------------------------------------------------------


def load_env(keys: tuple[str, ...]) -> dict[str, str]:
    try:
        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv(usecwd=True), override=False)
        load_dotenv(override=False)
    except ImportError:
        pass
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise CredentialError(f"missing {', '.join(missing)} (set it in .env; see docs/credentials.md)")
    return {k: os.environ[k] for k in keys}


def run_slug(name: str, scope: Scope) -> str:
    parts = [name, *scope.languages[:4], *[a.lower() for a in scope.areas[:4]]]
    return re.sub(r"[^a-z0-9]+", "-", "-".join(parts).lower()).strip("-")[:60]


def write_run(
    root: Path,
    harvester: Harvester,
    scope: Scope,
    candidates: list[dict[str, Any]],
    run_id: str | None,
    notes: str = "",
) -> tuple[Path, Path]:
    day = dt.date.today().isoformat()
    rid = run_id or f"{day}-{run_slug(harvester.name, scope)}"
    runs = root / "runs"
    runs.mkdir(exist_ok=True)
    n = 2
    base = rid
    while (runs / f"{rid}.yaml").exists():
        rid = f"{base}-{n}"
        n += 1
    jsonl = runs / f"{rid}.jsonl"
    jsonl.write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in candidates), encoding="utf-8"
    )
    header = {
        "id": rid,
        "date": day,
        "kind": f"harvester:{harvester.name}",
        "scope": scope.as_dict(),
        "method": harvester.method,
        "agent": None,
        "cost": {"cash_eur": 0, "notes": notes or "free API tier"},
        "outcome": {},
    }
    path = runs / f"{rid}.yaml"
    path.write_text(dump_yaml(header), encoding="utf-8")
    return jsonl, path


def harvest(
    harvester: Harvester,
    root: Path,
    scope: Scope,
    *,
    limit: int,
    run_id: str | None,
    say: Callable[[str], None],
    transport: httpx.BaseTransport | None = None,
    throttle: Throttle | None = None,
    budget: Budget | None = None,
) -> tuple[Path, Path]:
    for code in scope.languages:
        if code not in vocab().languages:
            raise UsageError(f"--lang {code} is not in vocab languages")
    for area in scope.areas:
        if area not in vocab().areas:
            raise UsageError(f"--area {area} is not in vocab areas")
    for sub in scope.subdomains:
        if sub not in vocab().subdomains:
            raise UsageError(f"--subdomain {sub} is not in vocab subdomains")
    env = load_env(harvester.env_keys)
    scope.modalities = scope.modalities or list(harvester.modalities)
    client = make_client(transport, throttle)
    ctx = Context(client=client, env=env, limit=limit, say=say, budget=budget)
    found: list[dict[str, Any]] = []
    notes = ""
    try:
        for cand in harvester.iterate(scope, ctx):
            cand.pop("description", None)  # never store catalogue descriptions (FR-032)
            found.append(cand)
            if len(found) >= limit:
                break
    except BudgetExhausted as e:
        notes = f"stopped early: {e}"
        say(f"{harvester.name}: {notes}")
    finally:
        client.close()
    return write_run(root, harvester, scope, found, run_id, notes)
