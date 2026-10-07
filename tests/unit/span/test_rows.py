"""Training rows: repair, alignment, dimension filter, validation by snapshot (T025)."""

import pytest
from helpers import pilot
from span_helpers import teacher_env, write_recipe

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.span.rows import align_units, load_rows, validation_snapshots


@pytest.fixture
def env(tmp_path):
    bench, train, run = teacher_env(tmp_path)
    return train, run, tmp_path


def build(train, run, recipe, expect=0):
    return pilot(train, "span", "build-rows", "--run", run, "--recipe", str(recipe),
                 expect=expect)


def test_rows_repair_quotes_and_keep_only_produced_dimensions(env):
    train, run, tmp = env
    stats = build(train, run, write_recipe(tmp / "r.yaml", ["actor_type"]))
    assert stats["dimensions"] == ["actor_type"]
    # mock-teacher-y has one near-miss quote ("pendel" for "pendle") in ch-001: repaired.
    assert stats["items_repaired"] == 1 and stats["items_dropped"] == 0
    assert stats["excluded"] == {}  # every mock-teacher-y answer is valid JSON
    rows = load_rows(load_settings(train))
    assert len(rows) == 5
    for row in rows:
        for item in row["items"]:
            assert set(item) == {"span", "kind", "actor_type"}
            s, e = item["span"]
            assert row["text"][s:e].strip()
        if not row["relevant"]:
            assert row["items"] == []
    assert any("pendle" in r["text"][i["span"][0]:i["span"][1]]
               for r in rows for i in r["items"])


def test_validation_split_never_shares_a_snapshot(env):
    train, run, tmp = env
    stats = build(train, run, write_recipe(tmp / "r.yaml", ["actor_type"]))
    rows = load_rows(load_settings(train))
    val = {r["snapshot_id"] for r in rows if r["split"] == "val"}
    trn = {r["snapshot_id"] for r in rows if r["split"] == "train"}
    assert val and trn and not val & trn
    assert stats["rows_per_split"]["val"] == len([r for r in rows if r["split"] == "val"])


def test_refuses_without_dimensions_and_for_non_teacher_runs(env):
    train, run, tmp = env
    build(train, run, write_recipe(tmp / "r.yaml", None), expect=1)
    pilot(train, "span", "build-rows", "--run", "run-unknown", "--recipe",
          str(write_recipe(tmp / "r2.yaml", [])), expect=2)


def test_align_units_takes_the_item_covering_half():
    text = "First unit here. Second unit is long enough. Third."
    items = [{"span": [0, 16], "kind": "pain"}, {"span": [17, 30], "kind": "job"}]
    aligned = align_units(text, items)
    assert [(text[a:b], i and i["kind"]) for (a, b), i in aligned] == [
        ("First unit here.", "pain"), ("Second unit is long enough.", "job"), ("Third.", None)]


def test_validation_snapshots_are_seeded_and_bounded():
    ids = [f"s{n}" for n in range(20)]
    assert validation_snapshots(ids, 0.1, 1) == validation_snapshots(ids, 0.1, 1)
    assert len(validation_snapshots(ids, 0.1, 1)) == 2
    assert validation_snapshots(["only"], 0.1, 1) == set()
