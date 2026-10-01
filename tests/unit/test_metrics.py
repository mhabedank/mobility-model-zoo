import json
import math

import pytest
from helpers import FIXTURE, copy_fixture, pilot, reference_chain

from mobility_model_zoo.productdev.jtbd.metrics import bootstrap_ci, f1_stat, kappa

EXPECTED = json.loads((FIXTURE / "expected.json").read_text())["reference"]


def test_kappa_basics():
    assert kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert math.isnan(kappa([], []))
    a = ["pain", "job", "pain", "gain", "pain", "job"]
    b = ["pain", "pain", "pain", "gain", "pain", "job"]
    assert kappa(a, b, ["job", "pain", "gain"]) == pytest.approx(15 / 21)


def test_weighted_kappa_hand_computed():
    a, b = [1, 2, 1, 1, 4, 3], [1, 2, 3, 1, 4, 3]
    labels = [0, 1, 2, 3, 4]
    assert kappa(a, b, labels, "quadratic") == pytest.approx(0.75)
    assert kappa(a, b, labels, "linear") == pytest.approx(1 - 2 / (46 / 6))


def test_bootstrap_is_deterministic():
    units = [(f"c{i}", (1, 0, i % 2)) for i in range(20)]
    assert bootstrap_ci(units, f1_stat, 100, 3) == bootstrap_ci(units, f1_stat, 100, 3)


def test_agreement_on_mini_corpus(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    result = pilot(config, "agreement")
    d = result["dimensions"]
    assert d["relevance"]["score"] == pytest.approx(EXPECTED["relevance_kappa"])
    assert d["item_matching"]["score"] == pytest.approx(EXPECTED["item_matching_f1"])
    assert d["kind"]["score"] == pytest.approx(EXPECTED["kind_kappa"])
    assert d["actor_type"]["score"] == pytest.approx(EXPECTED["actor_type_kappa"])
    assert d["evidence_type"]["score"] == pytest.approx(EXPECTED["evidence_type_quadratic_kappa"])
    assert d["evidence_type"]["linear"]["score"] == pytest.approx(
        EXPECTED["evidence_type_linear_kappa"])
    assert d["evidence_scope"]["score"] == pytest.approx(EXPECTED["evidence_scope_kappa"])
    assert result["composite_all_units"] == pytest.approx(EXPECTED["composite_all_units"])
    assert all(v["underpowered"] for v in d.values())
    assert result["evidence_levels"]["counts"] == EXPECTED["evidence_level_counts"]
    assert result["evidence_levels"]["underpowered_levels"] == ["observation", "measurement"]
    assert set(result["breakdowns"]["language"]) == {"de", "en"}
