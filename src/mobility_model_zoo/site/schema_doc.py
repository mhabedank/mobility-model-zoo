"""Documentation of an output format, generated from its JSON schema (research R7, check B5).

Types, required fields and allowed values come from the schema the model validates against; the
meaning of each field comes from `zoo/formats/<id>.yaml`. The two must name the same fields.
"""

from __future__ import annotations

import json
from typing import Any

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry, load_yaml, parse_version


def _type(prop: dict[str, Any]) -> tuple[str, list[Any]]:
    if "const" in prop:
        return "string (constant)", [prop["const"]]
    if "enum" in prop:
        return "string", list(prop["enum"])
    kind = prop.get("type", "any")
    if isinstance(kind, list):
        kind = " or ".join(kind)
    if kind == "array":
        inner, enum = _type(prop.get("items", {}))
        return f"array of {inner if inner != 'object' else 'objects'}", enum
    bounds = []
    if "minimum" in prop:
        bounds.append(f"≥ {prop['minimum']}")
    if "maximum" in prop:
        bounds.append(f"≤ {prop['maximum']}")
    return kind + (f" ({', '.join(bounds)})" if bounds else ""), []


def flatten(schema: dict[str, Any], prefix: str = "") -> list[dict[str, Any]]:
    """One row per field: arrays of objects are expanded as `name[].field`."""
    rows = []
    required = set(schema.get("required", []))
    for key, prop in schema.get("properties", {}).items():
        path = f"{prefix}{key}"
        kind, enum = _type(prop)
        rows.append({"path": path, "type": kind, "enum": enum, "required": key in required})
        items = prop.get("items", {})
        if prop.get("type") == "array" and items.get("type") == "object":
            rows += flatten(items, f"{path}[].")
    return rows


def _public_models(reg: Registry) -> list[str]:
    from mobility_model_zoo.site.context import is_sandbox

    return [name for name in reg.model_names() if not is_sandbox(reg, name)]


def format_ids(reg: Registry) -> list[str]:
    """Every output format of a published, non-sandbox release; format pages are never removed."""
    ids = set()
    for name in _public_models(reg):
        for version in reg.published_versions(name):
            fmt = reg.record_raw(name, version).get("output_format_version")
            if fmt:
                ids.add(fmt)
    return sorted(ids)


def output_format(reg: Registry, format_id: str) -> dict[str, Any] | None:
    """The documented format, or None if `zoo/formats/<id>.yaml` does not exist."""
    path = reg.zoo / "formats" / f"{format_id}.yaml"
    if not path.exists():
        return None
    doc = load_yaml(path) or {}
    schema_path = reg.root / doc["schema"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    rows = flatten(schema)
    meanings = doc.get("fields", {})
    paths = {r["path"] for r in rows}
    failures = [
        f"B5 {format_id}: schema field {p} has no meaning in {path.name}"
        for p in sorted(paths - set(meanings))
    ]
    failures += [
        f"B5 {format_id}: {path.name} describes {p}, which is not in the schema"
        for p in sorted(set(meanings) - paths)
    ]
    if failures:
        raise GateFailed(failures)
    for row in rows:
        row.update({k: meanings[row["path"]].get(k, "") for k in ("meaning", "empty_case", "notes")})
    produced_by = []
    for name in _public_models(reg):
        for version in sorted(reg.published_versions(name), key=parse_version):
            if reg.record_raw(name, version).get("output_format_version") == format_id:
                produced_by.append({"name": name, "version": version})
    dims = next((r for r in rows if r["path"] == "dimensions"), None)
    return {
        "id": format_id,
        "title": doc.get("title", format_id),
        "schema_path": doc["schema"],
        "schema": schema,
        "input": doc.get("input", []),
        "rules": doc.get("rules", []),
        "edge_cases": doc.get("edge_cases", []),
        "versioning": doc.get("versioning", ""),
        "rows": rows,
        "dimensions": [r for r in rows if dims and r["path"].split(".")[-1] in dims["enum"]],
        "produced_by": produced_by,
    }
