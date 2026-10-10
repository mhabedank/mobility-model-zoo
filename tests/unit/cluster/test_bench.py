"""Benchmark cluster-v1: pool, split, pairs, sets and freezing (feature 009, T022)."""

from __future__ import annotations

import pytest
import yaml
from bench_helpers import make_env

from mobility_model_zoo.productdev.jtbd.cluster import bench
from mobility_model_zoo.productdev.jtbd.errors import FrozenHashMismatch, UsageError


@pytest.fixture
def built(tmp_path):
    env = make_env(tmp_path / "a")
    env.build()
    return env


def test_split_is_by_snapshot(built):
    s = built.settings()
    pool = list(bench.load_pool(s).values())
    split_of = {}
    for row in pool:
        assert split_of.setdefault(row["snapshot_id"], row["split"]) == row["split"]
    counts = {sp: sum(1 for v in split_of.values() if v == sp) for sp in bench.SPLITS}
    assert counts == {"holdout": 4, "dev": 7, "test": 13}  # 24 snapshots, 15% / 30% / rest


def test_pairs_are_same_kind_and_within_one_split(built):
    s = built.settings()
    pool = bench.load_pool(s)
    for p in bench.load_pairs(s):
        assert pool[p["a"]]["kind"] == pool[p["b"]]["kind"]
        assert pool[p["a"]]["split"] == pool[p["b"]]["split"] == p["split"]
        assert p["a"] != p["b"] and set(p) == {"pair_id", "a", "b", "split", "stratum"}
    assert len({p["pair_id"] for p in bench.load_pairs(s)}) == len(bench.load_pairs(s))


def test_strata_shares_match_the_config(built):
    s = built.settings()
    cfg = bench.cfg(s)["pairs"]
    for split in bench.SPLITS:
        pairs = bench.load_pairs(s, split)
        assert abs(len(pairs) - cfg[split]) <= 1
        for stratum, share in cfg["strata"].items():
            got = sum(1 for p in pairs if p["stratum"] == stratum)
            assert abs(got - round(cfg[split] * share)) <= 1, (split, stratum)


def test_sets_hold_ids_of_one_split(built):
    s = built.settings()
    pool = bench.load_pool(s)
    for st in bench.load_sets(s):
        assert len(st["items"]) == 8 and len(set(st["items"])) == 8
        assert {pool[i]["split"] for i in st["items"]} == {st["split"]}
    assert [st["set_id"] for st in bench.load_sets(s, "test")] == ["set-test-01", "set-test-02"]


def test_lists_hold_no_text(built):
    text = (bench.bench_dir(built.settings()) / "pairs.jsonl").read_text()
    text += (bench.bench_dir(built.settings()) / "sets.jsonl").read_text()
    assert "every" not in text and "quote" not in text


def test_samplers_are_labse_and_lexical_only(tmp_path):
    env = make_env(tmp_path / "x")
    s = env.settings()
    bench.check_samplers(bench.cfg(s), env.root)
    bad = dict(bench.cfg(s)["pairs"], samplers=[{"name": "e5", "model_id": "intfloat/x"}])
    with pytest.raises(UsageError, match="samplers"):
        bench.check_samplers(dict(bench.cfg(s), pairs=bad), env.root)
    (env.root / "cluster-baseline.yaml").write_text(yaml.safe_dump(
        {"encoder": {"model_id": "sentence-transformers/LaBSE"}}))
    with pytest.raises(UsageError, match="candidate encoder"):
        bench.check_samplers(bench.cfg(s), env.root)


def test_pilot_holdout_chunks_never_enter_the_pool():
    lines = [{"source_id": "pilot-v2:ch-1"}, {"source_id": "pilot-v2:ch-2"}]
    assert bench.without_holdout(lines, {"ch-2"}) == [{"source_id": "pilot-v2:ch-1"}]


def test_same_seed_gives_the_same_lists(tmp_path):
    a, b = make_env(tmp_path / "a"), make_env(tmp_path / "b")
    a.build(), b.build()
    for name in ("pool.jsonl", "pairs.jsonl", "sets.jsonl"):
        assert (bench.bench_dir(a.settings()) / name).read_bytes() == \
            (bench.bench_dir(b.settings()) / name).read_bytes()


def test_freeze_hashes_and_verify(built):
    s = built.settings()
    result = bench.freeze(s)
    assert result["state"] == "frozen"
    assert set(result["hashes"]) == {"guideline", "examples", "prompt", "wire_schema", "criteria",
                                     "budget", "pairs", "sets", "pool"}
    assert bench.freeze(s)["verified"] is True
    with pytest.raises(FrozenHashMismatch):
        built.build()  # a frozen benchmark is never rebuilt
    (built.root / "criteria.yaml").write_text("duplicate_kappa_min: 0.1\n")
    with pytest.raises(FrozenHashMismatch, match="criteria"):
        bench.verify(s)


def test_revised_guideline_may_be_frozen_once_for_the_re_pilot(built, tmp_path):
    s = built.settings()
    bench.freeze(s)
    guideline = tmp_path / "guideline.md"
    guideline.write_text("# revised guideline\n")
    cfg = yaml.safe_load(built.config.read_text())
    cfg["cluster"]["guideline"] = str(guideline)
    built.config.write_text(yaml.safe_dump(cfg))
    with pytest.raises(FrozenHashMismatch):
        bench.verify(built.settings())
    bench.set_state(built.settings(), "revise", "test")
    assert bench.freeze(built.settings())["revised"] is True
    assert bench.verify(built.settings())["state"] == "frozen"
