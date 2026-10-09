"""Deterministic checks of a `jtbd-cluster-v1` result (spec FR-026).

They never call a model and are reported on their own (constitution III). Each check returns its
name, whether it passed and the ids that broke it.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from mobility_model_zoo.productdev.jtbd.cluster.bundle import ATTRIBUTES

OUTPUT_SCHEMA = Path(__file__).resolve().parent / "jtbd-cluster-v1.schema.json"
MAX_OFFENDERS = 20


@cache
def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(OUTPUT_SCHEMA.read_text(encoding="utf-8")),
                                format_checker=FormatChecker())


def _check(name: str, offenders: list[str]) -> dict[str, Any]:
    return {"name": name, "passed": not offenders, "offending": sorted(offenders)[:MAX_OFFENDERS],
            "count": len(offenders)}


def schema_errors(result: dict[str, Any]) -> list[str]:
    errors = sorted(_validator().iter_errors(result), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in errors]


def independence_rule(origin_based: list[bool]) -> str:
    """`origin` if every independence key comes from an origin, `source_id` if none does."""
    kinds = set(origin_based)
    return "origin" if kinds == {True} else "source_id" if kinds == {False} else "mixed"


def aggregate(items: list[dict[str, Any]], rule: str) -> dict[str, Any]:
    """Counts, attribute distributions and dates over serialised items. The independence rule is
    passed in, because serialised items do not say whether their key came from an origin."""
    keys = {i["independence_key"] for i in items}
    dated = sorted(i["date"] for i in items if i["date"])
    distributions = {}
    for attr in ATTRIBUTES:
        values = Counter(i[attr] for i in items if attr in i)
        if values:
            distributions[attr] = dict(sorted(values.items()))
    return {
        "counts": {"mentions": len(items), "independent_sources": len(keys), "independence_rule": rule},
        "distributions": distributions,
        "dates": {"first": dated[0] if dated else None, "last": dated[-1] if dated else None,
                  "undated": sum(1 for i in items if not i["date"])},
    }


def check_result(result: dict[str, Any], bundle_quotes: dict[str, str] | None = None
                 ) -> list[dict[str, Any]]:
    """All checks that apply to the result. `bundle_quotes` maps item id to the quote in the
    input bundles; without it, the byte-identity check is skipped and reported as such."""
    checks = [_check("schema", schema_errors(result))]
    items = {i["item_id"]: i for i in result.get("items", [])}
    groups = {g["group_id"]: g for g in result.get("groups", [])}

    membership: Counter[str] = Counter()
    wrong_group = []
    for gid, group in groups.items():
        for iid in group["members"]:
            membership[iid] += 1
            if iid in items and items[iid]["group_id"] != gid:
                wrong_group.append(iid)
    unplaced = [iid for iid in items if membership[iid] != 1]
    unknown = [iid for iid in membership if iid not in items]
    checks.append(_check("every_item_in_exactly_one_group", unplaced + unknown + wrong_group))

    if bundle_quotes is None:
        checks.append({"name": "quotes_identical_to_input", "passed": True, "offending": [],
                       "count": 0, "skipped": "no input bundles given"})
    else:
        changed = [iid for iid, item in items.items() if bundle_quotes.get(iid) != item["quote"]]
        missing = [iid for iid in bundle_quotes if iid not in items]
        checks.append(_check("quotes_identical_to_input", changed + missing))

    mixed = [gid for gid, g in groups.items()
             if any(items[i]["kind"] != g["kind"] for i in g["members"] if i in items)]
    checks.append(_check("group_single_kind", mixed))

    bad_rep = [gid for gid, g in groups.items() if g["representative"] not in g["members"]]
    checks.append(_check("representative_is_member", bad_rep))

    wrong_counts = []
    for gid, group in groups.items():
        rule = (group.get("counts") or {}).get("independence_rule", "mixed")
        expected = aggregate([items[i] for i in group["members"] if i in items], rule)
        got = {k: group.get(k) for k in ("counts", "distributions", "dates")}
        if got != expected:
            wrong_counts.append(gid)
    checks.append(_check("group_aggregates", wrong_counts))
    return checks


def passed(checks: list[dict[str, Any]]) -> bool:
    return all(c["passed"] for c in checks)
