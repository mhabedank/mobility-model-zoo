import pytest

from mobility_model_zoo.productdev.jtbd.decision import evaluate, finetuning
from mobility_model_zoo.productdev.jtbd.schema import DecisionCriteria

CRITERIA = DecisionCriteria.model_validate({
    "version": "t", "max_reruns": 1, "underpowered_min_units": 30,
    "thresholds": {"relevance_kappa": 0.8, "evidence_type_weighted_kappa": 0.6, "kind_kappa": 0.6,
                   "actor_type_kappa": 0.6, "evidence_scope_kappa": 0.6, "item_matching_f1": 0.7},
    "rethink_below": {"evidence_type_weighted_kappa": 0.4},
    "revise_band": {"evidence_type_weighted_kappa": [0.4, 0.6]},
    "finetuning_optional": {"min_quality_ratio": 0.85, "min_throughput_ratio": 10,
                            "quality_reference": "frontier_vs_frontier_composite",
                            "throughput_reference": "frontier_reference_chunks_per_min"},
    "teacher_fitness": {"min_quality_ratio": 0.9, "min_schema_valid": 0.98, "tie_margin": 0.02,
                        "score_view": "repaired"},
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


def teacher(model_id, ratio, schema_valid=0.99, cost=0.01, raw_ratio=None, role="teacher_candidate",
            dims=None):
    return {"model_id": model_id, "role": role, "quality_ratio_a": raw_ratio or ratio,
            "cost_per_chunk_eur": cost,
            "check_pass_rates": {"schema_valid": {"rate": schema_valid}},
            "repaired": {"quality_ratio_a": ratio, "composite": ratio,
                         "dimensions": {d: {"score": v} for d, v in (dims or {}).items()}}}


@pytest.mark.parametrize("ratio,schema_valid,fit,reason", [
    (0.90, 0.98, True, None),
    (0.899, 0.98, False, "repaired quality_ratio_a 0.899 < 0.9"),
    (0.90, 0.979, False, "schema_valid 0.979 < 0.98"),
])
def test_teacher_fitness_thresholds(ratio, schema_valid, fit, reason):
    from mobility_model_zoo.productdev.jtbd.decision import teacher_fitness

    [row] = teacher_fitness(CRITERIA, [teacher("t", ratio, schema_valid)])["candidates"]
    assert row["fit"] is fit
    assert row["reasons"] == ([reason] if reason else [])


def test_teacher_fitness_uses_the_repaired_view_only():
    from mobility_model_zoo.productdev.jtbd.decision import teacher_fitness

    result = teacher_fitness(CRITERIA, [teacher("t", 0.92, raw_ratio=0.85)])
    assert result["candidates"][0]["fit"] and result["recommended"] == "t"


@pytest.mark.parametrize("gap,expected", [(0.015, "cheap"), (0.03, "best")])
def test_teacher_recommendation_tie_margin(gap, expected):
    from mobility_model_zoo.productdev.jtbd.decision import teacher_fitness

    scores = [teacher("best", 0.95, cost=0.02), teacher("cheap", 0.95 - gap, cost=0.001)]
    assert teacher_fitness(CRITERIA, scores)["recommended"] == expected


def test_no_fit_teacher_names_missing_dimensions_and_skips_baselines():
    from mobility_model_zoo.productdev.jtbd.decision import teacher_fitness

    scores = [teacher("t", 0.8, dims={"kind": 0.5, "relevance": 0.95}),
              teacher("small", 0.5, role="baseline")]
    result = teacher_fitness(CRITERIA, scores, {"kind": 0.8, "relevance": 1.0})
    assert result["recommended"] is None
    [row] = result["candidates"]
    assert row["model_id"] == "t" and not row["fit"]
    assert "kind 0.500 < 0.9 x frontier 0.800" in row["reasons"]
    assert not any(r.startswith("relevance") for r in row["reasons"])
