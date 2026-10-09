"""Model facts on the website and where they come from (FR-004, checks B2 and F1).

Every number on a page comes from a results file of a release. `metric()` loads it, refuses a
metric that does not say what it is measured against, and formats it with `card.num`, the same
function the model card uses, so the site and the card print identical strings. `Facts` records
each rendered fact with its source; `zoo site check` reloads the sources and compares (F1).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.card import num
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry

PLACEHOLDER = re.compile(r"\{metric:(quality|performance)\.([a-z0-9_]+)\}")
UNITS = {"chunks/min": "texts/min"}


@dataclass
class Facts:
    """Rendered facts: (page, key, value as printed, source file, metric name)."""

    rows: list[dict[str, str]] = field(default_factory=list)

    def add(self, page: str, key: str, value: str, source: str, metric: str) -> None:
        self.rows.append({"page": page, "key": key, "value": value, "source": source, "metric": metric})

    def write(self, out: Path) -> None:
        path = out / "_build" / "facts.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def unit_label(unit: str | None) -> str:
    return UNITS.get(unit or "", unit or "")


def metric(reg: Registry, name: str, version: str, kind: str, metric_name: str) -> dict[str, Any]:
    """One metric of a release, ready to print: value, unit, what it is measured against."""
    path = reg.results_path(name, version, kind)
    source = str(path.relative_to(reg.root))
    if not path.exists():
        raise GateFailed([f"B2 {name}: {source} is missing"])
    found = next(
        (m for m in reg.results(name, version, kind)["metrics"] if m["name"] == metric_name), None
    )
    if found is None:
        raise GateFailed([f"B2 {name}: metric {kind}.{metric_name} is not in {source}"])
    if kind == "quality" and not (found.get("reference") and found.get("benchmark")):
        raise GateFailed([f"B2 {name}: quality metric {metric_name} has no reference or benchmark"])
    if kind == "performance" and not found.get("hardware"):
        raise GateFailed([f"B2 {name}: performance metric {metric_name} has no hardware"])
    if kind == "quality":
        against = f"measured against {found['reference']}, benchmark {found['benchmark']}"
    else:
        against = f"measured on {found['hardware']}"
    return {
        "name": metric_name,
        "kind": kind,
        "value": num(found["value"]),
        "raw": found["value"],
        "unit": unit_label(found.get("unit")),
        "description": found.get("description", ""),
        "against": against,
        "source": source,
    }


def placeholders(text: str) -> list[tuple[str, str]]:
    return PLACEHOLDER.findall(text or "")


@dataclass
class Notes:
    """Footnotes of one page: every resolved number links to what it is measured against."""

    items: list[dict[str, str]] = field(default_factory=list)

    def ref(self, m: dict[str, Any]) -> int:
        for i, item in enumerate(self.items, 1):
            if item["metric"] == f"{m['kind']}.{m['name']}":
                return i
        self.items.append(
            {
                "metric": f"{m['kind']}.{m['name']}",
                "text": f"{m['description']}; {m['against']}.",
                "source": m["source"],
            }
        )
        return len(self.items)


def resolve(
    text: str,
    reg: Registry,
    name: str,
    version: str,
    facts: Facts,
    notes: Notes,
    page: str,
    key: str,
) -> str:
    """HTML for prose with `{metric:…}` placeholders: escaped text, each number linked to a note."""
    out, pos = [], 0
    for match in PLACEHOLDER.finditer(text):
        out.append(escape(text[pos : match.start()]))
        m = metric(reg, name, version, match[1], match[2])
        n = notes.ref(m)
        facts.add(page, f"{key}:{match[1]}.{match[2]}", m["value"], m["source"], m["name"])
        unit = f" {m['unit']}" if m["unit"] else ""
        out.append(
            f'<span class="fact">{escape(m["value"])}{escape(unit)}</span>'
            f'<sup><a href="#fn-{n}" id="fnref-{n}-{len(out)}" aria-label="Note {n}">{n}</a></sup>'
        )
        pos = match.end()
    out.append(escape(text[pos:]))
    return "".join(out)
