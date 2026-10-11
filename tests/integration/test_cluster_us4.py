"""User story 4 end to end: corrections and stable ids across an extended run (feature 009, T047).

Stub vectors from tests/fixtures/cluster/vectors.json; nothing is downloaded.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from mobility_model_zoo.productdev.jtbd.cli import app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cluster"
BASIC = FIXTURE / "bundles" / "basic.jsonl"
MORE = FIXTURE / "bundles" / "more.jsonl"
SETTINGS = FIXTURE / "settings.yaml"


def jtbd(*args, expect=0):
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == expect, (result.exit_code, result.output)
    return result


def run(out, *bundles):
    args = ["cluster", "run", "--map", str(out), "--settings", str(SETTINGS)]
    for b in bundles:
        args += ["--input", str(b)]
    jtbd(*args)
    return json.loads((out / "result.json").read_text())


def test_corrections_survive_and_ids_stay_stable(tmp_path):
    out = tmp_path / "map"
    first = run(out, BASIC)
    items = {i["item_id"]: i for i in first["items"]}
    by_kind: dict[str, list[dict]] = {}
    for g in first["groups"]:
        by_kind.setdefault(g["kind"], []).append(g)
    pains = [g for g in by_kind["pain"] if len(g["members"]) == 1][:3]
    split_group = next(g for g in first["groups"] if len(g["members"]) >= 2)
    a, b, c = (g["members"][0] for g in pains)
    jtbd("cluster", "correct", "merge", a, b, "--map", str(out), "--note", "same need")
    jtbd("cluster", "correct", "split", "--set", split_group["members"][0],
         "--set", split_group["members"][1], "--map", str(out))
    jtbd("cluster", "correct", "representative", c, "--map", str(out))

    second = run(out, BASIC, MORE)
    statuses = [s["status"] for s in second["checks"]["corrections"]]
    assert statuses == ["applied", "applied", "applied"]          # 100% in effect (SC-004)
    group_of = {i["item_id"]: i["group_id"] for i in second["items"]}
    assert group_of[a] == group_of[b]
    assert group_of[split_group["members"][0]] != group_of[split_group["members"][1]]
    groups = {g["group_id"]: g for g in second["groups"]}
    assert groups[group_of[c]]["representative"] == c and groups[group_of[a]]["corrected"]

    # Groups the corrections did not touch and the new input did not join keep their id.
    touched = {a, b, c, *split_group["members"]}
    new_items = {i["item_id"] for i in second["items"]} - set(items)
    unchanged = [g for g in first["groups"]
                 if not touched & set(g["members"])
                 and {i for i, gid in group_of.items() if gid == group_of[g["members"][0]]}
                 == set(g["members"])]
    kept = sum(group_of[g["members"][0]] == g["group_id"] for g in unchanged)
    assert unchanged and kept / len(unchanged) >= 0.95
    changes = json.loads((out / "changes.json").read_text())
    assert set(changes) >= {"new", "grown", "merged", "split", "removed", "stale_corrections",
                            "refused_corrections", "orphaned_annotations"}
    assert new_items and changes["stale_corrections"] == [] == changes["refused_corrections"]


def test_same_command_twice_gives_identical_bytes(tmp_path):
    out = tmp_path / "map"
    run(out, BASIC, MORE)
    jtbd("cluster", "correct", "move", next(iter(json.loads(
        (out / "result.json").read_text())["items"]))["item_id"], "--top", "--map", str(out))
    run(out, BASIC, MORE)
    first = (out / "result.json").read_bytes()
    run(out, BASIC, MORE)
    assert (out / "result.json").read_bytes() == first


def test_annotation_survives_a_rerun(tmp_path):
    out = tmp_path / "map"
    result = run(out, BASIC)
    node = result["groups"][0]["group_id"]
    jtbd("cluster", "annotate", "--map", str(out), "--node", node, "--statement",
         "Parking in town is hard", "--assign", "persona=commuter", "--by", "person")
    again = run(out, BASIC, MORE)
    group = next(g for g in again["groups"] if g["group_id"] == node)
    assert group["statement"]["text"] == "Parking in town is hard"
    assert group["assignments"] == [{"scheme": "persona", "value": "commuter", "origin": "person"}]
    jtbd("cluster", "annotate", "--map", str(out), "--node", "dg-999999", "--assign", "x=y",
         "--by", "person")
    run(out, BASIC, MORE)
    changes = json.loads((out / "changes.json").read_text())
    assert changes["orphaned_annotations"] == ["dg-999999"]
