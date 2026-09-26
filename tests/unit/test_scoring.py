import json

import pytest
from helpers import FIXTURE, copy_fixture, pilot, reference_chain, run_ids

from jtbd_pilot.scoring import Target, score_units

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
