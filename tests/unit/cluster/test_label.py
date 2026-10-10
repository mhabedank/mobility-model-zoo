"""Reference labeling of pairs and sets with the mock backend (feature 009, T024)."""

from __future__ import annotations

import json

import pytest
from bench_helpers import answer_units, make_env

from mobility_model_zoo.productdev.jtbd.cluster import bench, label
from mobility_model_zoo.productdev.jtbd.errors import (
    BudgetRefused,
    FrozenHashMismatch,
    UsageError,
    ValidationFailed,
)


@pytest.fixture
def frozen(tmp_path):
    env = make_env(tmp_path / "env")
    env.build()
    bench.freeze(env.settings())
    return env


def run_dir(env, model="mock-a", split="test"):
    s = env.settings()
    return s.runs_dir / label.run_id_for(model, split, bench.load_manifest(s)["hashes"]["guideline"])


def test_pair_batches_of_twenty_and_one_unit_per_set(frozen):
    units = label.units_for(frozen.settings(), "test")
    pair_units = [u for u in units if u["type"] == "pairs"]
    assert [len(u["pairs"]) for u in pair_units] == [20, 10]
    assert [u["unit"] for u in units if u["type"] == "sets"] == ["set-test-01", "set-test-02"]


def test_complete_run_writes_pairs_and_sets(frozen):
    answer_units(frozen, "mock-a", "test", pair_label=lambda p: "same")
    out = label.label(frozen.settings(), "mock-a", "test")
    assert out["status"] == "complete" and out["excluded"] == 0
    rows = [json.loads(x) for x in (run_dir(frozen) / "pairs.jsonl").read_text().splitlines()]
    assert len(rows) == 30 and {r["label"] for r in rows} == {"same"}
    sets = (run_dir(frozen) / "sets.jsonl").read_text().splitlines()
    assert len(sets) == 2
    manifest = json.loads((run_dir(frozen) / "manifest.json").read_text())
    assert manifest["role"] == "reference" and manifest["model_version"] == "mock-mock-a"


def test_invalid_pair_label_is_retried_then_excluded_and_counted(frozen):
    answer_units(frozen, "mock-a", "test", pair_label=lambda p: "similar")
    out = label.label(frozen.settings(), "mock-a", "test")
    assert out["excluded"] == 2  # both pair batches; max_retries 1 -> two attempts each
    raw = sorted(p.name for p in (run_dir(frozen) / "raw").glob("pairs-*"))
    assert raw == ["pairs-test-001.a1.json", "pairs-test-001.a2.json",
                   "pairs-test-002.a1.json", "pairs-test-002.a2.json"]


def test_set_answer_that_misses_an_item_is_invalid(frozen):
    answer_units(frozen, "mock-a", "test",
                 set_answer=lambda ids: {"clusters": [{"cluster_id": "c1", "members": ids[:-1]}],
                                         "coarse": None})
    out = label.label(frozen.settings(), "mock-a", "test")
    manifest = json.loads((run_dir(frozen) / "manifest.json").read_text())
    assert out["excluded"] == 2
    assert all("missing items" in e["reason"] for e in manifest["excluded_units"])


def test_set_answer_that_repeats_an_item_is_invalid():
    from mobility_model_zoo.productdev.jtbd.cluster.prompt import set_answer_errors

    answer = {"clusters": [{"cluster_id": "c1", "members": ["a", "b"]},
                           {"cluster_id": "c2", "members": ["b"]}], "coarse": None}
    assert any("repeated" in e for e in set_answer_errors(answer, ["a", "b"]))
    answer = {"clusters": [{"cluster_id": "c1", "members": ["a"]},
                           {"cluster_id": "c2", "members": ["b"]}],
              "coarse": [{"group_id": "g1", "clusters": ["c1"]}]}
    assert set_answer_errors(answer, ["a", "b"]) == [
        "coarse groups do not cover every cluster exactly once"]


def test_raw_responses_are_written_once_and_runs_resume(frozen):
    answer_units(frozen, "mock-a", "test")
    label.label(frozen.settings(), "mock-a", "test", limit=1)
    first = (run_dir(frozen) / "raw" / "pairs-test-001.a1.json").read_bytes()
    out = label.label(frozen.settings(), "mock-a", "test")
    assert out["processed_now"] == 3 and out["status"] == "complete"
    assert (run_dir(frozen) / "raw" / "pairs-test-001.a1.json").read_bytes() == first
    assert not (run_dir(frozen) / "raw" / "pairs-test-001.a2.json").exists()


def test_changed_frozen_file_exits_3(frozen):
    (frozen.root / "criteria.yaml").write_text("duplicate_kappa_min: 0.1\n")
    with pytest.raises(FrozenHashMismatch) as exc:
        label.label(frozen.settings(), "mock-a", "test")
    assert exc.value.exit_code == 3


def test_budget_guard_exits_4(frozen):
    ledger = frozen.settings().ledger_path
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"item": "x", "backend": "openrouter", "estimated_eur": 25,
                                  "actual_eur": 25, "budget": "cluster-test"}) + "\n")
    answer_units(frozen, "mock-a", "test")
    with pytest.raises(BudgetRefused) as exc:
        label.label(frozen.settings(), "mock-a", "test")
    assert exc.value.exit_code == 4


def test_only_configured_benchmark_labelers(frozen):
    with pytest.raises(UsageError):
        label.label(frozen.settings(), "mock-small", "test")  # not a reference of the benchmark
    env = make_env(frozen.root.parent / "other", reference_models=["mock-a", "mock-small"])
    env.build()
    bench.freeze(env.settings())
    with pytest.raises(ValidationFailed, match="role baseline"):
        label.label(env.settings(), "mock-small", "test")


def test_holdout_is_locked_until_revise(frozen):
    with pytest.raises(ValidationFailed, match="locked"):
        label.label(frozen.settings(), "mock-a", "holdout")


def test_pre_send_check_runs_on_every_batch(frozen, monkeypatch):
    from mobility_model_zoo.compliance import presend

    seen = []
    original = presend.check_batch

    def spy(reg, **kw):
        items = list(kw["items"])
        seen.extend(i for i, _, _ in items)
        return original(reg, **{**kw, "items": items})

    monkeypatch.setattr(presend, "check_batch", spy)
    answer_units(frozen, "mock-a", "test")
    label.label(frozen.settings(), "mock-a", "test")
    units = label.units_for(frozen.settings(), "test")
    assert set(seen) == {i for u in units for i in label.unit_items(u)}


def test_identifier_in_a_quote_stops_the_run(frozen):
    pool_path = bench.bench_dir(frozen.settings()) / "pool.jsonl"
    rows = [json.loads(x) for x in pool_path.read_text().splitlines()]
    target = next(p["a"] for p in bench.load_pairs(frozen.settings(), "test"))
    for r in rows:
        if r["item_id"] == target:
            r["quote"] += " Mail me at lena.beispiel@gmx.de"
    pool_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(FrozenHashMismatch):  # the pool is frozen: a changed quote is caught first
        label.label(frozen.settings(), "mock-a", "test")


def test_pre_send_refuses_an_identifier(frozen):
    s = frozen.settings()
    pool = bench.load_pool(s)
    units = label.units_for(s, "test")[:1]
    first = label.unit_items(units[0])[0]
    pool[first] = {**pool[first], "quote": pool[first]["quote"] + " Mail lena.beispiel@gmx.de"}
    with pytest.raises(ValidationFailed, match="C-P2"):
        label._presend(s, s.model("mock-a"), units, pool)
