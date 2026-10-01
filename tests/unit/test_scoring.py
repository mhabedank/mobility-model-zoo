import json

import pytest
from helpers import FIXTURE, copy_fixture, pilot, reference_chain, run_ids

from mobility_model_zoo.productdev.jtbd.scoring import Target, score_units

EXPECTED = json.loads((FIXTURE / "expected.json").read_text())["baseline_mock_small"]


def test_mock_small_against_consensus(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    pilot(config, "agreement")
    pilot(config, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    run = run_ids(config)["mock-small"]
    pilot(config, "check", "--run", run)
    score = pilot(config, "score", "--run", run)
    d = score["dimensions"]
    assert d["relevance"]["score"] == pytest.approx(EXPECTED["relevance_kappa"])
    assert d["item_matching"]["score"] == pytest.approx(EXPECTED["item_matching_f1"])
    assert d["kind"]["score"] == pytest.approx(EXPECTED["kind_kappa"])
    assert d["actor_type"]["score"] == pytest.approx(EXPECTED["actor_type_kappa"])
    assert d["evidence_type"]["score"] == pytest.approx(EXPECTED["evidence_type_quadratic_kappa"])
    assert d["evidence_scope"]["score"] == pytest.approx(EXPECTED["evidence_scope_kappa"])
    assert score["composite"] == pytest.approx(EXPECTED["composite"])
    assert score["neutral_contested_hits"] == EXPECTED["neutral_contested_hits"]
    assert score["check_pass_rates"]["schema_valid"]["rate"] == pytest.approx(
        EXPECTED["schema_valid_pass_rate"])
    assert score["frontier_composite_consensus_units"] == pytest.approx(
        EXPECTED["frontier_composite_consensus_units"])
    assert score["quality_ratio_a"] == pytest.approx(EXPECTED["quality_ratio_a"])
    assert score["quality_ratio_b"] == pytest.approx(EXPECTED["quality_ratio_b"], rel=1e-5)


def test_score_requires_frozen_benchmark(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    pilot(config, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    pilot(config, "score", "--run", run_ids(config)["mock-small"], expect=1)


class Out:
    def __init__(self, relevant, items):
        self.relevant, self.items = relevant, items

    @property
    def valid_items(self):
        return [i for i in self.items if i.span]


def test_empty_output_on_empty_consensus_counts_as_correct():
    consensus = [{"chunk_id": "c1", "level": "relevance", "value": False}]
    units, neutral = score_units(consensus, [], ["c1"], {"c1": Out(False, [])}, 0.3)
    assert units["relevance"] == [("c1", ("false", "false"))]
    assert units["item_matching"] == [("c1", (0, 0, 0))]
    assert not neutral


def test_target_dataclass_defaults():
    t = Target((0, 5), "pain")
    assert t.values == {} and t.contested_existence is False


def test_teacher_scored_raw_and_after_quote_repair(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    pilot(config, "agreement")
    pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock",
          "--model", "mock-teacher-y")
    run = run_ids(config)["mock-teacher-y"]
    manifest_path = config.parent / "store" / "runs" / run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["cost_eur"] = 0.5
    manifest_path.write_text(json.dumps(manifest))
    checks = pilot(config, "check", "--run", run)
    score = pilot(config, "score", "--run", run)
    repaired = score["repaired"]
    # mock-teacher-y has one near-miss quote ("pendel" for "pendle") in ch-001.
    assert repaired["repair_stats"] == {"invalid_quotes": 1, "repaired": 1, "dropped": 0}
    assert (repaired["dimensions"]["item_matching"]["score"]
            > score["dimensions"]["item_matching"]["score"])
    assert repaired["composite"] > score["composite"]
    assert repaired["quality_ratio_a"] == pytest.approx(
        repaired["composite"] / score["frontier_composite_consensus_units"], abs=1e-6)
    # Check pass rates stay on the raw output.
    assert score["check_pass_rates"]["quote_verbatim"] == checks["pass_rates"]["quote_verbatim"]
    assert score["check_pass_rates"]["quote_verbatim"]["rate"] < 1
    assert score["cost_per_chunk_eur"] == pytest.approx(0.5 / 5)


def test_baseline_has_no_repaired_view(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    pilot(config, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    run = run_ids(config)["mock-small"]
    score = pilot(config, "score", "--run", run)
    assert "repaired" not in score
    assert score["cost_per_chunk_eur"] == 0
