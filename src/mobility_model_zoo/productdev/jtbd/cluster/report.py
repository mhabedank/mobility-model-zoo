"""Views of a `jtbd-cluster-v1` result (research R16, task T042), rendered from `result.json` only.

- `tree.md`: top-level nodes by descending independent sources, each line with id, kind or kinds,
  mentions, independent sources and the representative quote; children indented (clusters, then
  groups, then more specific groups). Read as an Opportunity Solution Tree.
- `needs.csv`: one row per group, for an outcome-driven list filtered by kind.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

CSV_COLUMNS = ("group_id", "kind", "mentions", "independent_sources", "first_date", "last_date",
               "parent", "top_cluster", "representative_quote")


def _nodes(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = {g["group_id"]: g for g in result["groups"]}
    nodes.update({c["cluster_id"]: c for c in result["clusters"]})
    return nodes


def _order(ids: list[str], nodes: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(ids, key=lambda n: (-nodes[n]["counts"]["independent_sources"], n))


def _kinds(node: dict[str, Any]) -> str:
    if "kind" in node:
        return node["kind"]
    return ", ".join(k for k, v in sorted(node.get("kinds", {}).items()) if v)


def tree_md(result: dict[str, Any]) -> str:
    nodes = _nodes(result)
    quote = {i["item_id"]: i["quote"] for i in result["items"]}
    settings = result["settings"]
    lines = [
        "# Opportunity tree",
        "",
        f"Settings `{settings.get('name')}` ({settings['settings_sha256'][:12]}), "
        f"{len(result['items'])} items, {len(result['groups'])} duplicate groups, "
        f"{len(result['clusters'])} clusters. Specificity relation: "
        f"{'produced' if settings.get('specificity_produced') else 'not produced'}.",
        "",
    ]

    def render(nid: str, depth: int) -> None:
        node = nodes[nid]
        counts = node["counts"]
        text = " ".join(quote[node["representative"]].split())
        lines.append(f"{'  ' * depth}- **{nid}** ({_kinds(node)}; {counts['mentions']} mentions, "
                     f"{counts['independent_sources']} independent sources): \"{text}\"")
        statement = node.get("statement")
        if statement:
            lines.append(f"{'  ' * (depth + 1)}> {statement['text']} ({statement['by']}, "
                         f"{statement['at']})")
        children = node.get("children", [])
        for child in _order([c for c in children if c.startswith("cl-")], nodes) + \
                _order([c for c in children if c.startswith("dg-")], nodes):
            render(child, depth + 1)

    for nid in _order([n for n, node in nodes.items() if not node.get("parent")], nodes):
        render(nid, 0)
    return "\n".join(lines) + "\n"


def top_cluster(gid: str, nodes: dict[str, dict[str, Any]]) -> str | None:
    """The topmost cluster above a group, through `dg-` parents."""
    current, top = nodes[gid].get("parent"), None
    while current:
        if current.startswith("cl-"):
            top = current
        current = nodes[current].get("parent")
    return top


def needs_csv(result: dict[str, Any]) -> str:
    nodes = _nodes(result)
    quote = {i["item_id"]: i["quote"] for i in result["items"]}
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for g in sorted(result["groups"], key=lambda g: (g["kind"], -g["counts"]["independent_sources"],
                                                     g["group_id"])):
        writer.writerow([g["group_id"], g["kind"], g["counts"]["mentions"],
                         g["counts"]["independent_sources"], g["dates"]["first"] or "",
                         g["dates"]["last"] or "", g.get("parent") or "",
                         top_cluster(g["group_id"], nodes) or "",
                         " ".join(quote[g["representative"]].split())])
    return out.getvalue()


def write_report(map_dir: Path | str, out: Path | str | None = None) -> dict[str, str]:
    """`jtbd cluster report --map … [--out …]`: both views next to `result.json` or in `out`."""
    map_dir = Path(map_dir)
    result = json.loads((map_dir / "result.json").read_text(encoding="utf-8"))
    target = Path(out) if out else map_dir
    target.mkdir(parents=True, exist_ok=True)
    (target / "tree.md").write_text(tree_md(result), encoding="utf-8")
    (target / "needs.csv").write_text(needs_csv(result), encoding="utf-8")
    return {"tree": str(target / "tree.md"), "needs": str(target / "needs.csv")}
