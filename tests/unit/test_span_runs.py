"""Span runs in the shared harness: loading, checks and scoring of produced dimensions (T018)."""

import json

import pytest
from helpers import FIXTURE, copy_fixture, pilot, reference_chain
from span_helpers import span_outputs_from_mock, write_span_run

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.scoring import comparison_composite

EXPECTED = json.loads((FIXTURE / "expected.json").read_text())["baseline_mock_small"]


@pytest.fixture
def bench(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    pilot(config, "agreement")
    return config


def span_run(config, dims, mutate=None, run_id="run-student-span-main-test"):
    settings = load_settings(config)
    chunks = chunk_map(settings, "main")
    outputs = span_outputs_from_mock(FIXTURE / "mock" / "mock-small", chunks, dims)
    if mutate:
        mutate(outputs)
    excluded = sorted(set(chunks) - set(outputs))
    return write_span_run(settings, run_id, outputs, dims, excluded)


def test_span_run_scores_only_produced_dimensions(bench):
    run = span_run(bench, ("actor_type",))
    checks = pilot(bench, "check", "--run", run)["pass_rates"]
    assert all(v["rate"] == 1.0 for v in checks.values()), checks
    score = pilot(bench, "score", "--run", run)
    d = score["dimensions"]
    # Same spans and labels as mock-small, so the produced dimensions score the same.
    assert d["relevance"]["score"] == pytest.approx(EXPECTED["relevance_kappa"])
    assert d["item_matching"]["score"] == pytest.approx(EXPECTED["item_matching_f1"])
    assert d["kind"]["score"] == pytest.approx(EXPECTED["kind_kappa"])
    assert d["actor_type"]["score"] == pytest.approx(EXPECTED["actor_type_kappa"])
    for dim in ("evidence_type", "evidence_scope"):
        assert d[dim] == {"status": "not_produced", "score": None, "n": 0}
    names = ["relevance", "item_matching", "kind", "actor_type"]
    manual = sum(EXPECTED[k] for k in ("relevance_kappa", "item_matching_f1", "kind_kappa",
                                       "actor_type_kappa")) / 4
    assert score["comparison_composite"]["dimensions"] == names
    assert score["comparison_composite"]["value"] == pytest.approx(manual)
    assert score["composite"] == pytest.approx(manual)
    assert score["produced_dimensions"] == ["actor_type"]


def test_comparison_composite_is_undefined_for_a_missing_dimension():
    dims = {"relevance": {"score": 0.5}, "kind": {"score": 1.0},
            "actor_type": {"status": "not_produced", "score": None, "n": 0}}
    assert comparison_composite(dims, ["relevance", "kind"]) == pytest.approx(0.75)
    assert comparison_composite(dims, ["relevance", "actor_type"]) is None
    assert comparison_composite(dims, ["relevance", "item_matching"]) is None


def test_wrong_offset_fails_the_verbatim_check(bench):
    def shift(outputs):
        item = outputs["ch-001"]["items"][0]
        item["start"] += 1
        item["end"] += 1

    run = span_run(bench, ("actor_type",), shift)
    rates = pilot(bench, "check", "--run", run)["pass_rates"]
    assert rates["quote_verbatim"]["rate"] < 1.0


def test_extra_attribute_fails_consistency(bench):
    def extra(outputs):
        outputs["ch-001"]["items"][0]["evidence_scope"] = "single"

    run = span_run(bench, ("actor_type",), extra)
    rates = pilot(bench, "check", "--run", run)["pass_rates"]
    assert rates["consistency.span_dimensions"]["rate"] < 1.0
    assert rates["schema_valid"]["rate"] == 1.0


def test_span_backend_requires_the_student_role(bench):
    settings = load_settings(bench)
    run = span_run(bench, ("actor_type",))
    manifest = json.loads((settings.runs_dir / run / "manifest.json").read_text())
    with pytest.raises(ValueError, match="student runs"):
        from mobility_model_zoo.productdev.jtbd.schema import LabelRunManifest

        LabelRunManifest.model_validate({**manifest, "role": "baseline"})
