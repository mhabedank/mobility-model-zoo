"""Fetch lists: the hand-off from the index to a later download feature (FR-028, FR-029, research R10).

Each item carries a `proposed_record` in the shape of the topic register it will land in:
`sources.yaml` for texts, audio, video and images, `datasets.yaml` for structured data. The
fetch-time fields (storage, retention_until, crawl_manifest_sha256, pii_scan) are left to the
download feature, which also confirms the source class.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from mobility_model_zoo.catalog import rules, states
from mobility_model_zoo.catalog.model import Catalog, dump_yaml, read_yaml, schema
from mobility_model_zoo.datasets import UsageRefused
from mobility_model_zoo.release.errors import UsageError

OWNER = "Martin Habedank"
# Proposed source class per kind of source; confirmed against the topic's source classes at fetch.
CLASS_BY_KIND = {
    "parliament": "parliamentary-records",
    "research": "open-papers",
    "education": "open-papers",
    "community": "forum-review",
}
DEFAULT_CLASS = "tdm-documents"
REGISTER_SIGNALS = (
    "robots",
    "tdmrep",
    "x_robots",
    "meta_noai",
    "ai_txt",
    "content_signal",
    "content_usage",
)


def _attribution(entry: dict[str, Any]) -> str:
    lic = entry["licence"]
    if lic.get("attribution_text"):
        return lic["attribution_text"]
    title = entry["title"]["original"]
    url = lic.get("url") or lic["id"]
    publisher = entry["publisher"]["name"]
    return f'"{title}" by {publisher}, {entry["landing_url"]}, licensed under {lic["id"]} ({url}).'


def _personal_data(entry: dict[str, Any]) -> dict[str, Any]:
    pd = entry["personal_data"]
    return {
        "present": pd["expectation"] != "none",
        "categories": list(pd["categories"]),
        "special_categories": [],
        "human_subjects": False,
    }


def proposed_record(
    entry: dict[str, Any], route: dict[str, Any], today: str
) -> tuple[str, dict[str, Any]]:
    """(target register, record) for a cleared entry."""
    usage = entry["usage"]
    signals = {k: v for k, v in (entry.get("signals") or {}).items() if k in REGISTER_SIGNALS}
    signals["checked_at"] = (entry.get("signals") or {}).get("checked_at", today)
    signals["retrospective"] = False
    review = dt.date.fromisoformat(today)
    rec: dict[str, Any] = {
        "id": entry["id"],
        "class": CLASS_BY_KIND.get(entry["publisher"]["kind"], DEFAULT_CLASS),
        "origin_url": entry["landing_url"],
        "title": entry["title"]["original"],
        "creators": [entry["publisher"]["name"]],
        "publisher": entry["publisher"]["name"],
        "licence": entry["licence"]["id"],
        "licence_url": entry["licence"].get("url"),
        "attribution_text": _attribution(entry),
        "modifications": f"Not yet fetched; proposed from catalog entry {entry['id']}.",
        "permitted_use": usage["permitted_use"],
        "redistribution": usage["redistribution"],
        "redistribution_basis": f"Catalog rule {usage['rule']}: {usage['rationale']}",
        "quote_allowed": False,
        "signals": signals,
        "personal_data": _personal_data(entry),
        "used_by": [],
        "owner": OWNER,
        "last_reviewed": today,
        "next_review": (review + dt.timedelta(days=182)).isoformat(),
        "notes": "Proposed by the resource index (feature 009); confirm the source class at fetch time.",
    }
    if entry.get("platform_terms"):
        terms = entry["platform_terms"]
        rec["platform_terms"] = {
            "url": terms["url"],
            "checked_at": terms["checked_at"],
            "ml_use": terms["ml_use"],
            "hosted_processing": "unclear",
        }
    if entry["resource_type"]["modality"] != "structured_data":
        return "sources", rec
    hint = route.get("provider_hint")
    url = route.get("download_url") or route["url"]
    zenodo = re.search(r"zenodo\.org/records?/(\d+)", url) if hint == "zenodo" else None
    rec.update(
        {
            "provider": "zenodo" if zenodo else "url",
            "locator": {"zenodo_record": zenodo.group(1)} if zenodo else {"urls": [url]},
            "license_check": "manual",
            "license_checked": today,
            "status": "active",
            "commercial_use": entry["licence"].get("commercial_use") == "yes",
            "approx_size_mb": round((route.get("size_bytes_est") or 0) / 1e6, 3),
            "use_case": ", ".join(entry.get("subdomains") or []),
        }
    )
    if (entry.get("identifiers") or {}).get("doi"):
        rec["doi"] = entry["identifiers"]["doi"]
    return "datasets", rec


def build(
    cat: Catalog, selected: list[dict[str, Any]], name: str, selection: str, today: str | None = None
) -> dict[str, Any]:
    today = today or dt.date.today().isoformat()
    items, refused = [], []
    for e in selected:
        status = (e.get("status") or {}).get("value")
        route = states.clearable_route(e)
        if status != "cleared":
            reason = (e.get("status") or {}).get("reason") or "; ".join(states.clear_blockers(e)) or "-"
            refused.append({"entry_id": e["id"], "reason": f"status {status}: {reason}"})
        elif route is None:
            refused.append({"entry_id": e["id"], "reason": "no usable access route"})
        else:
            register, record = proposed_record(e, route, today)
            items.append(
                {
                    "entry_id": e["id"],
                    "access_route": route,
                    "target_register": register,
                    "target_topic": (e.get("topics") or ["productdev"])[0],
                    "proposed_record": record,
                }
            )
    v = cat.version()
    doc = {
        "id": f"{today}-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}",
        "created_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "selection": selection,
        "catalog_commit": v["catalog_commit"] or "0" * 40,
        "catalog_sha256": v["catalog_sha256"],
        "vocab_version": v["vocab_version"],
        "rules_version": int(rules.table()["version"]),
        "items": items,
        "refused": refused,
    }
    jsonschema.validate(doc, schema("fetch-list"))
    return doc


def write(
    cat: Catalog, name: str, selected: list[dict[str, Any]], selection: str
) -> tuple[Path, dict[str, Any]]:
    doc = build(cat, selected, name, selection)
    if not doc["items"]:
        raise UsageRefused(f"no cleared entry in the selection ({len(doc['refused'])} refused)")
    folder = cat.root / "fetch-lists"
    folder.mkdir(exist_ok=True)
    path = folder / f"{doc['id']}.yaml"
    path.write_text(dump_yaml(doc), encoding="utf-8")
    return path, doc


def read(path: Path) -> dict[str, Any]:
    doc = read_yaml(path)
    jsonschema.validate(doc, schema("fetch-list"))
    return doc


def link(cat: Catalog, entry_id: str, target: str, zoo_root: Path, today: str) -> None:
    """Set an entry to fetched after its record exists in topics/<topic>/compliance/<register>.yaml."""
    parts = target.split(":")
    if len(parts) != 3 or parts[0] not in ("sources", "datasets"):
        raise UsageError("target must be REGISTER:TOPIC:RECORD with REGISTER sources or datasets")
    register, topic, record_id = parts
    if entry_id not in cat.entries:
        raise UsageError(f"unknown entry {entry_id}")
    path = zoo_root / "topics" / topic / "compliance" / f"{register}.yaml"
    records = (
        (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get(register, [])
        if path.exists()
        else []
    )
    if not any(r.get("id") == record_id for r in records):
        raise UsageRefused(f"{record_id} is not in topics/{topic}/compliance/{register}.yaml")
    e = cat.entries[entry_id]
    e["fetched"] = {"register": register, "topic": topic, "record_id": record_id, "linked_at": today}
    states.set_status(e, "fetched", today)
    cat.write_entry(e)
