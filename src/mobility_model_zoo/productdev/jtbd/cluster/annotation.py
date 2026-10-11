"""Statements and assignments that later methods attach to nodes (research R15, task T054).

Named `annotation`, not `annotations`: the package's `from __future__ import annotations` would
shadow a submodule of that name in `from ...cluster import annotations`.

`annotations.jsonl` in the map directory holds one line per annotation, keyed by node id:
`{"node": "cl-000012", "statement": {"text", "by", "at"}, "assignments": [{"scheme", "value",
"origin"}]}`. They are merged into the result on every run: the latest statement of a node wins;
assignments are kept per (scheme, origin), the latest value winning, so several schemes coexist.
Annotations on an id that no longer exists are reported as orphaned. The stage never writes a
statement itself.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd.errors import UsageError

FILE = "annotations.jsonl"
NODE = re.compile(r"^(dg|cl)-[0-9]{6}$")
AUTHOR = re.compile(r"^(person|model:.+)$")


def _is_date(value: Any) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def validate(line: Any) -> str | None:
    if not isinstance(line, dict) or not NODE.match(str(line.get("node", ""))):
        return "`node` must be a dg- or cl- id"
    extra = set(line) - {"node", "statement", "assignments"}
    if extra:
        return f"unknown keys: {sorted(extra)}"
    if "statement" not in line and not line.get("assignments"):
        return "a statement or at least one assignment is needed"
    statement = line.get("statement")
    if statement is not None:
        if (not isinstance(statement, dict) or set(statement) != {"text", "by", "at"}
                or not str(statement["text"]).strip() or not AUTHOR.match(str(statement["by"]))
                or not _is_date(statement["at"])):
            return "statement needs `text`, `by` (person or model:<id>) and `at` (ISO date)"
    for a in line.get("assignments") or []:
        if (not isinstance(a, dict) or set(a) != {"scheme", "value", "origin"}
                or not str(a["scheme"]).strip() or not str(a["value"]).strip()
                or not AUTHOR.match(str(a["origin"]))):
            return "assignment needs `scheme`, `value` and `origin` (person or model:<id>)"
    return None


def load(map_dir: Path | str | None) -> list[dict[str, Any]]:
    if map_dir is None:
        return []
    path = Path(map_dir) / FILE
    if not path.exists():
        return []
    lines = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        line = json.loads(raw)
        error = validate(line)
        if error:
            raise UsageError(f"{path}:{n}: {error}")
        lines.append(line)
    return lines


def append(map_dir: Path | str, line: dict[str, Any]) -> None:
    """`jtbd cluster annotate`: validate and append one line."""
    error = validate(line)
    if error:
        raise UsageError(error)
    path = Path(map_dir) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")


def merge(result: dict[str, Any], lines: list[dict[str, Any]]) -> list[str]:
    """Merges annotations into the result's nodes in place; returns orphaned node ids."""
    nodes = {g["group_id"]: g for g in result["groups"]}
    nodes.update({c["cluster_id"]: c for c in result["clusters"]})
    assignments: dict[str, dict[tuple[str, str], dict]] = {}
    orphaned = set()
    for line in lines:
        node = nodes.get(line["node"])
        if node is None:
            orphaned.add(line["node"])
            continue
        if line.get("statement") is not None:
            node["statement"] = line["statement"]
        for a in line.get("assignments") or []:
            assignments.setdefault(line["node"], {})[(a["scheme"], a["origin"])] = a
    for nid, by_key in assignments.items():
        nodes[nid]["assignments"] = [by_key[k] for k in sorted(by_key)]
    return sorted(orphaned)
