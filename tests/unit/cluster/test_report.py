"""tree.md and needs.csv from result.json only (feature 009, T042)."""

from __future__ import annotations

import csv
import io
import json

from test_hierarchy import JOB, LATE, LATE_MONDAY, by_quote, run

from mobility_model_zoo.productdev.jtbd.cluster.report import CSV_COLUMNS, needs_csv, write_report
from mobility_model_zoo.productdev.jtbd.cluster.stage import write_result


def test_views_are_rendered_from_the_result_file(tmp_path):
    result = run()
    write_result(tmp_path / "map", result)
    paths = write_report(tmp_path / "map", tmp_path / "views")
    tree = (tmp_path / "views" / "tree.md").read_text()
    lines = tree.splitlines()
    top = [line for line in lines if line.startswith("- **")]
    assert len(top) == sum(1 for c in result["clusters"] + result["groups"] if not c["parent"])
    groups = by_quote(result)
    late = next(n for n, line in enumerate(lines) if f"**{groups[LATE]['group_id']}**" in line)
    monday = next(n for n, line in enumerate(lines)
                  if f"**{groups[LATE_MONDAY]['group_id']}**" in line)
    indent = lambda line: len(line) - len(line.lstrip())  # noqa: E731
    assert monday == late + 1 and indent(lines[monday]) == indent(lines[late]) + 2
    assert json.loads((tmp_path / "map" / "result.json").read_text()) == result  # unchanged
    assert set(paths) == {"tree", "needs"}


def test_needs_csv_has_one_row_per_group_with_its_top_cluster():
    result = run()
    rows = list(csv.DictReader(io.StringIO(needs_csv(result))))
    assert tuple(rows[0]) == CSV_COLUMNS
    assert sorted(r["group_id"] for r in rows) == sorted(g["group_id"] for g in result["groups"])
    by_quote = {r["representative_quote"]: r for r in rows}
    assert by_quote[LATE_MONDAY]["top_cluster"] == by_quote[JOB]["top_cluster"] != ""
    assert by_quote[LATE_MONDAY]["parent"] == by_quote[LATE]["group_id"]


def test_statements_are_shown_in_the_tree():
    from mobility_model_zoo.productdev.jtbd.cluster.report import tree_md

    result = run()
    result["clusters"][0]["statement"] = {"text": "Commuters need reliable trains", "by": "person",
                                          "at": "2026-10-11"}
    assert "> Commuters need reliable trains (person, 2026-10-11)" in tree_md(result)
