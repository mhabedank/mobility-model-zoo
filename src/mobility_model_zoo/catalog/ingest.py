"""Discovery runs → entries: validate, deduplicate (R7), assign ids, write (FR-019, FR-022).

A line that fails never becomes an entry; it is listed in the run header with its reason.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import jsonschema

from mobility_model_zoo.catalog import states
from mobility_model_zoo.catalog.model import Catalog, dump_yaml, read_yaml, schema
from mobility_model_zoo.catalog.validate import DedupeIndex, Finding, k1, k9
from mobility_model_zoo.compliance.signals import canonical

MAX_REJECTED_SHARE = 0.20
ID_MAX = 80


def slug(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def make_id(candidate: dict[str, Any], taken: set[str]) -> str:
    area = slug(str(candidate.get("origin_area", "xx")))
    publisher = slug((candidate.get("publisher") or {}).get("name", ""))[:30].strip("-")
    title = slug((candidate.get("title") or {}).get("en", ""))
    base = "-".join(p for p in (area, publisher, title) if p)[:ID_MAX].strip("-")
    if len(base) < 3:
        digest = hashlib.sha256(json.dumps(candidate, sort_keys=True, default=str).encode()).hexdigest()
        base = f"{area}-{digest[:10]}"
    new, n = base, 2
    while new in taken:
        suffix = f"-{n}"
        new = base[: ID_MAX - len(suffix)].rstrip("-") + suffix
        n += 1
    return new


def candidate_errors(candidate: dict[str, Any]) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema("candidate"))
    return [
        f"{'.'.join(map(str, e.absolute_path)) or '(line)'}: {e.message}"
        for e in sorted(validator.iter_errors(candidate), key=lambda e: list(e.absolute_path))
    ]


def to_entry(candidate: dict[str, Any], entry_id: str, added_by: str, today: str) -> dict[str, Any]:
    entry = copy.deepcopy(candidate)
    entry["id"] = entry_id
    entry["schema_version"] = 1
    entry.setdefault("parent", None)
    prov = entry["provenance"]
    entry["provenance"] = {
        "added_by": added_by,
        "added_at": today,
        "method": prov["method"],
        "evidence": list(prov.get("evidence") or []),
        "last_verified": None,
    }
    entry["status"] = {"value": "candidate", "since": today}
    return entry


def merge(existing: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """Add the candidate's access routes, evidence and identifiers to an existing entry."""
    changed = False
    have = {canonical(a["url"]) for a in existing.get("access") or []}
    for route in candidate.get("access") or []:
        if canonical(route["url"]) not in have:
            existing.setdefault("access", []).append(route)
            have.add(canonical(route["url"]))
            changed = True
    prov = existing.setdefault("provenance", {})
    for url in (candidate.get("provenance") or {}).get("evidence") or []:
        if url not in prov.setdefault("evidence", []):
            prov["evidence"].append(url)
            changed = True
    ident = candidate.get("identifiers") or {}
    if ident:
        mine = existing.setdefault("identifiers", {})
        if ident.get("doi") and not mine.get("doi"):
            mine["doi"] = ident["doi"]
            changed = True
        for other in ident.get("other") or []:
            if other not in mine.setdefault("other", []):
                mine["other"].append(other)
                changed = True
        if not mine.get("other"):
            mine.pop("other", None)
    return changed


def add_one(
    cat: Catalog,
    candidate: dict[str, Any],
    *,
    added_by: str,
    today: str,
    index: DedupeIndex | None = None,
) -> tuple[str | None, list[Finding]]:
    """Add one candidate. Returns (entry id or None, findings). Merges count as the existing id."""
    errors = candidate_errors(candidate)
    if errors:
        return None, [
            Finding(str(candidate.get("id", "(new)")), "K1", "fail", "(candidate)", e) for e in errors
        ]
    index = index or DedupeIndex.build(cat.entries.values())
    match = index.exact(candidate)
    if match:
        existing = cat.entries[match[0]]
        if merge(existing, candidate):
            cat.write_entry(existing)
        return match[0], [Finding(match[0], "K3", "warn", "(entry)", f"merged: {match[1]}")]
    entry_id = candidate.get("id") or make_id(candidate, set(cat.entries))
    if entry_id in cat.entries:
        return None, [Finding(entry_id, "K2", "fail", "id", "id already exists")]
    entry = to_entry(candidate, entry_id, added_by, today)
    findings = k1(entry) + k9(entry)
    if any(f.severity == "fail" for f in findings):
        return None, findings
    for f in findings:
        if f.flag:
            states.set_flag(entry, f.flag)
    similar = index.similar(entry)
    if similar:
        entry.setdefault("relations", {})["possible_duplicates"] = similar
        states.set_flag(entry, "possible_duplicate")
    cat.write_entry(entry)
    index.add(entry)
    return entry_id, findings


def ingest(cat: Catalog, jsonl: Path, run_file: Path, today: str) -> dict[str, Any]:
    """Add every line of a run; write the outcome into the run header and return it."""
    header = read_yaml(run_file)
    run_id = header["id"]
    index = DedupeIndex.build(cat.entries.values())
    scope = header.get("scope") or {}
    cells: dict[tuple[str, str], dict[str, int]] = {
        (lang, mod): {"proposed": 0, "accepted": 0}
        for lang in scope.get("languages") or []
        for mod in scope.get("modalities") or []
    }
    outcome = {"proposed": 0, "accepted": 0, "merged": 0, "rejected": 0, "rejected_lines": []}
    known = set(cat.entries)
    for number, raw in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        outcome["proposed"] += 1
        try:
            candidate = json.loads(raw)
        except json.JSONDecodeError as e:
            outcome["rejected"] += 1
            outcome["rejected_lines"].append({"line": number, "reason": f"invalid JSON: {e.msg}"})
            continue
        keys = [
            (lang.get("code"), (candidate.get("resource_type") or {}).get("modality"))
            for lang in candidate.get("languages") or []
            if isinstance(lang, dict)
        ]
        keys = [k for k in keys if isinstance(k[0], str) and isinstance(k[1], str)]
        for key in keys:
            cells.setdefault(key, {"proposed": 0, "accepted": 0})["proposed"] += 1
        entry_id, findings = add_one(cat, candidate, added_by=f"run:{run_id}", today=today, index=index)
        if entry_id is None:
            outcome["rejected"] += 1
            reason = "; ".join(f"{f.field}: {f.message}" for f in findings if f.severity == "fail")
            outcome["rejected_lines"].append({"line": number, "reason": reason[:500]})
            continue
        if entry_id in known:
            outcome["merged"] += 1
            continue
        known.add(entry_id)
        outcome["accepted"] += 1
        for key in keys:
            cells[key]["accepted"] += 1
    outcome["by_cell"] = [
        {"language": lang, "modality": mod, **counts} for (lang, mod), counts in sorted(cells.items())
    ]
    header["outcome"] = outcome
    jsonschema.validate(header, schema("run"))
    run_file.write_text(dump_yaml(header), encoding="utf-8")
    return outcome
