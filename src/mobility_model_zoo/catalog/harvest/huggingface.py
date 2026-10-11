"""Hugging Face Hub harvester: datasets by search term and language tag (research R6).

`/api/datasets?search=` matches a substring of the dataset id, so the harvester keeps only ids that
contain the search term as whole words (`bus` must not find `business`). Licence and languages come
from the `license:` and `language:` tags; the dataset card text is never stored (FR-032) and no
dataset file is fetched (FR-001). Search terms are the English ones of terms.yaml (ids are mostly
English) plus the ASCII-folded terms of the target language.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from typing import Any

from mobility_model_zoo.catalog.harvest.base import (
    Context,
    Scope,
    candidate,
    language_code,
    licence_block,
    search_terms,
    spdx,
    subdomains_for,
)

API = "https://huggingface.co/api/datasets"
PAGE_URL = "https://huggingface.co/datasets/{id}"
PAGE = 50
MAX_LANGUAGES = 10
CC_TAG = re.compile(r"^cc-by(-(nc|sa|nd))*-\d\.\d$")
FORMATS = {
    "csv": "text/csv", "json": "application/json", "parquet": "application/vnd.apache.parquet",
    "arrow": "application/vnd.apache.arrow.file", "text": "text/plain", "xml": "application/xml",
    "webdataset": "application/x-tar",
}
FALSE_FRIENDS = ("puerto rico",)  # search terms that are part of a name (es `puerto` = port)
TOPICS = {"vehicle_security": ["security"], "condition_monitoring": ["condition-monitoring"]}
ACADEMIC = re.compile(
    r"univ|institut|college|academ|research|\blabs?\b|cnrs|inria|fraunhofer|csic|\bupm\b|\btum\b|"
    r"\beth\b|epfl|\bmit\b|大学|研究",
    re.IGNORECASE,
)


def words(text: str) -> list[str]:
    """Lower-case ASCII words of an id or term; splits camelCase, `_`, `-`, `.` and spaces."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    folded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", folded)
    return [w for w in re.split(r"[^A-Za-z0-9]+", folded.lower()) if w]


def matches(term: str, dataset_id: str) -> bool:
    """True if the term's words occur in a row in the dataset name (plural `s`/`es` allowed)."""
    want = words(term)
    have = words(dataset_id.split("/")[-1])
    if not want:
        return False
    joined = "".join(want)
    if len(want) > 1 and any(w in (joined, joined + "s") for w in have):
        return True
    for start in range(len(have) - len(want) + 1):
        if all(have[start + i] in (w, w + "s", w + "es") for i, w in enumerate(want)):
            return True
    return False


def tag_values(tags: list[str], prefix: str) -> list[str]:
    return [t.split(":", 1)[1] for t in tags if isinstance(t, str) and t.startswith(prefix + ":")]


def licence_id(raw: str) -> str:
    found = spdx(raw)
    if found == "unknown" and CC_TAG.match(raw.lower()):
        return raw.upper()
    return found


class HuggingFace:
    name = "huggingface"
    catalogue = "Hugging Face Hub"
    env_keys: tuple[str, ...] = ()
    modalities = ("structured_data", "text", "image")
    method = ("Hugging Face Hub dataset search (/api/datasets, search term x language tag, full=true); "
              "whole-word match on the dataset id; metadata only")

    def iterate(self, scope: Scope, ctx: Context) -> Iterator[dict[str, Any]]:
        seen: set[str] = set()
        for lang in scope.languages or [None]:
            for sub in subdomains_for(scope):
                terms = search_terms(sub, "en")
                if lang and lang != "en":
                    terms += [" ".join(words(t)) for t in search_terms(sub, lang)]
                for term in dict.fromkeys(t for t in terms if t.strip()):
                    for item in self.search(term, lang, ctx):
                        dataset_id = str(item.get("id") or "")
                        if not dataset_id or dataset_id in seen or not matches(term, dataset_id):
                            continue
                        name = " ".join(words(dataset_id.split("/")[-1]))
                        if any(f in name for f in FALSE_FRIENDS):
                            continue
                        if item.get("private") or item.get("disabled"):
                            continue
                        cand = self.candidate(item, sub, lang)
                        if cand is None or cand["resource_type"]["modality"] not in scope.modalities:
                            continue
                        seen.add(dataset_id)
                        yield cand

    def search(self, term: str, lang: str | None, ctx: Context) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"search": term, "limit": PAGE, "full": "true"}
        if lang:
            params["filter"] = f"language:{lang.split('-')[0].lower()}"
        r = ctx.client.get(API, params=params)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []

    def candidate(self, item: dict[str, Any], subdomain: str, lang: str | None) -> dict[str, Any] | None:
        dataset_id = str(item["id"])
        tags = [t for t in item.get("tags") or [] if isinstance(t, str)]
        card = item.get("cardData") if isinstance(item.get("cardData"), dict) else {}
        page = PAGE_URL.format(id=dataset_id)
        author = str(item.get("author") or dataset_id.split("/")[0])
        rtype = resource_type(tags)
        if rtype is None:
            return None
        modality, genre = rtype
        title = str(card.get("pretty_name") or "").strip() or " ".join(
            re.split(r"[_-]+", dataset_id.split("/")[-1])).strip() or dataset_id
        languages = [language_code(code) for code in tag_values(tags, "language")]
        languages = [code for code in dict.fromkeys(languages) if code != "und"][:MAX_LANGUAGES]
        if not languages and lang:
            languages = [lang]
        licence = self.licence(tags, card, page)
        dates = (("published", "createdAt"), ("updated", "lastModified"))
        content = {k: str(item[f])[:10] for k, f in dates if item.get(f)}
        return candidate(
            self,
            title=title,
            title_en=None,
            languages=languages,
            area="001",
            publisher=author,
            kind="research" if ACADEMIC.search(author) else "community",
            landing_url=page,
            modality=modality,
            genre=genre,
            subdomains=[subdomain],
            topics=TOPICS.get(subdomain),
            licence=licence,
            access=[{
                "method": "api",
                "url": page,
                "download_url": None,
                "auth": "account" if item.get("gated") else "none",
                "cost": "free",
                "formats": [FORMATS[f] for f in dict.fromkeys(tag_values(tags, "format"))
                            if f in FORMATS],
                "provider_hint": "huggingface",
                "notes": "gated: accept the conditions on the dataset page" if item.get("gated")
                else "Hugging Face datasets API",
            }],
            evidence=[page],
            content=content or None,
            identifiers={"other": [f"huggingface:datasets/{dataset_id}"]},
        )

    @staticmethod
    def licence(tags: list[str], card: dict[str, Any], page: str) -> dict[str, Any]:
        raw = card.get("license")
        values = [str(v) for v in (raw if isinstance(raw, list) else [raw]) if v]
        values = values or tag_values(tags, "license")
        ids = {licence_id(v) for v in values}
        link = str(card.get("license_link") or "")
        url = link if link.startswith(("http://", "https://")) else None
        if not ids or ids == {"unknown"}:
            return licence_block("unknown", url, None)
        known = ids - {"unknown"}
        if len(known) == 1 and len(ids) == 1:
            return licence_block(known.pop(), url, page)
        return licence_block("mixed", url, page)


def resource_type(tags: list[str]) -> tuple[str, str] | None:
    """(modality, genre) from task, modality and format tags; `table` by default; None for audio or
    video only datasets (not covered by this harvester)."""
    tasks = tag_values(tags, "task_categories")
    kinds = set(tag_values(tags, "modality"))
    formats = set(tag_values(tags, "format"))
    if kinds and not kinds & {"tabular", "text", "timeseries", "geospatial", "image", "3d"}:
        return None
    if "3d" in kinds and "tabular" not in kinds:
        return "structured_data", "sensor_data"
    if "image" in kinds and not kinds & {"tabular", "text"}:
        return "image", "photo"
    if any(t.startswith("text-") for t in tasks) and "tabular" not in kinds:
        return "text", "article"
    if "time-series-forecasting" in tasks or "timeseries" in kinds:
        return "structured_data", "time_series"
    if formats == {"json"} and "tabular" not in kinds:
        return "structured_data", "json_xml_dump"
    return "structured_data", "table"
