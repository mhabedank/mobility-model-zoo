import pytest

from jtbd_pilot.decision import evaluate, finetuning
from jtbd_pilot.schema import DecisionCriteria

CRITERIA = DecisionCriteria.model_validate({
    "version": "t", "max_reruns": 1, "underpowered_min_units": 30,
    "thresholds": {"relevance_kappa": 0.8, "evidence_type_weighted_kappa": 0.6, "kind_kappa": 0.6,
                   "actor_type_kappa": 0.6, "evidence_scope_kappa": 0.6, "item_matching_f1": 0.7},
    "rethink_below": {"evidence_type_weighted_kappa": 0.4},
    "revise_band": {"evidence_type_weighted_kappa": [0.4, 0.6]},
    "finetuning_optional": {"min_quality_ratio": 0.85, "min_throughput_ratio": 10,
                            "quality_reference": "frontier_vs_frontier_composite",
                            "throughput_reference": "frontier_reference_chunks_per_min"},
})
GOOD = {"relevance": 0.9, "item_matching": 0.8, "kind": 0.7, "actor_type": 0.7,
        "evidence_type": 0.7, "evidence_scope": 0.7}


def dims(**overrides):
    return {k: {"score": overrides.get(k, v)} for k, v in GOOD.items()}


@pytest.mark.parametrize("overrides,reruns,expected", [
    ({}, 0, "go"),
    ({"evidence_type": 0.5}, 0, "revise"),
    ({"evidence_type": 0.39}, 0, "rethink"),
    ({"evidence_type": 0.3, "relevance": 0.5}, 0, "rethink"),
    ({"relevance": 0.79}, 0, "revise"),
    ({"item_matching": 0.69}, 0, "revise"),
    ({"kind": 0.5}, 1, "rethink"),
    ({}, 1, "go"),
])
def test_decision_table(overrides, reruns, expected):
    assert evaluate(CRITERIA, dims(**overrides), reruns)["decision"] == expected


def test_band_path_and_precedence():
    result = evaluate(CRITERIA, dims(evidence_type=0.5), 0)
    assert "in [0.4, 0.6)" in result["path"][0]
    result = evaluate(CRITERIA, dims(evidence_type=0.3, relevance=0.5), 0)
    assert "precedence" in result["path"][0]
    assert result["per_dimension"]["evidence_type"]["decision"] == "rethink"


def test_second_rerun_refused():
    result = evaluate(CRITERIA, dims(kind=0.5), 1)
    assert result["per_dimension"]["kind"]["decision"] == "rethink"
    assert "no further rerun" in result["path"][0]


def test_finetuning_rule():
    scores = [{"role": "baseline", "model_id": "m1", "quality_ratio_a": 0.86,
               "quality_ratio_b": 0.7},
              {"role": "baseline", "model_id": "m2", "quality_ratio_a": 0.9,
               "quality_ratio_b": 0.8}]
    perf = {"m1": {"chunks_per_min": 30}, "m2": {"chunks_per_min": 20}}
    frontier = {"chunks_per_min": 2.5}
    result = finetuning(CRITERIA, scores, perf, frontier)
    assert result["status"] == "optional"
    assert [r["meets_rule"] for r in result["models"]] == [True, False]
    assert finetuning(CRITERIA, scores, {}, frontier)["status"] == "undetermined"
    low = [{**s, "quality_ratio_a": 0.84} for s in scores]
    assert finetuning(CRITERIA, low, perf, frontier)["status"] == "required"
