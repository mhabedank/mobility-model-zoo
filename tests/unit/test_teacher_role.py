"""Only the pilot's recommended teacher labels the training split (T021, research R5)."""

import pytest
from helpers import pilot, reference_chain, run_ids
from span_helpers import span_train_env, write_train_chunks

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import write_json

DIMS = ("relevance", "item_matching", "kind", "actor_type", "evidence_type", "evidence_scope")


def decision(recommended, failed=()):
    return {"decision": "go",
            "per_dimension": {d: {"passed": d not in failed} for d in DIMS},
            "teacher_fitness": {"recommended": recommended}}


@pytest.fixture
def env(tmp_path):
    bench, train = span_train_env(tmp_path)
    reference_chain(bench)
    settings = load_settings(train)
    write_train_chunks(settings, [("snap-000000000001", "de", "paper"),
                                  ("snap-000000000002", "en", "paper")])
    pilot(train, "corpus", "review-sample", "--seed", "1")
    pilot(train, "corpus", "mark-reviewed", "--all")
    pilot(train, "corpus", "redact-check")
    pilot(train, "freeze")
    return bench, train


def write_decision(bench, doc):
    write_json(load_settings(bench).analysis_dir / "decision.json", doc)


def label(train, model, split="train", expect=0):
    return pilot(train, "label", "--role", "teacher", "--backend", "mock", "--model", model,
                 "--split", split, expect=expect)


def test_refused_before_the_pilot_decides(env):
    _, train = env
    label(train, "mock-teacher-x", expect=1)


def test_only_the_recommended_teacher_on_the_train_split(env):
    bench, train = env
    write_decision(bench, decision("mock-teacher-x"))
    label(train, "mock-teacher-y", expect=1)
    label(train, "mock-teacher-x", split="main", expect=1)
    out = label(train, "mock-teacher-x")
    assert out["status"] == "complete"
    assert out["run_id"].startswith("run-teacher-mock-teacher-x-train-")


def test_benchmark_reference_can_never_teach(env):
    bench, train = env
    write_decision(bench, decision("mock-a"))
    pilot(train, "label", "--role", "teacher", "--backend", "mock", "--model", "mock-a",
          "--split", "train", expect=1)


def test_no_fit_teacher_refuses(env):
    bench, train = env
    write_decision(bench, decision(None))
    label(train, "mock-teacher-x", expect=1)


def test_guideline_must_be_the_decisions(env, tmp_path):
    bench, train = env
    write_decision(bench, decision("mock-teacher-x"))
    guideline = load_settings(bench).paths["guideline"]
    assert load_settings(train).paths["guideline"] == guideline
    # The training dataset freezes a changed guideline; it differs from the pilot's decision.
    guideline.write_text(guideline.read_text() + "\nChanged after the decision.\n")
    pilot(train, "freeze", "--new-version", "train-test-v2", "--rationale", "test")
    label(train, "mock-teacher-x", expect=1)


def test_recommended_ensemble_labels_with_members_then_combines(env):
    bench, train = env
    write_decision(bench, decision("mock-ensemble"))
    label(train, "mock-teacher-x")
    label(train, "mock-teacher-y")
    out = pilot(train, "ensemble", "--split", "train")
    assert out["run_id"].startswith("run-teacher-mock-ensemble-train-")
    assert set(run_ids(train)) == {"mock-teacher-x", "mock-teacher-y", "mock-ensemble"}
