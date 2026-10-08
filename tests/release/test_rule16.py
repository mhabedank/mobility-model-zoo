"""Release-level compliance stages (gate rule 16) and route-based teacher rights (rule 6)."""

import copy

from compliance_helpers import load, route, write

from mobility_model_zoo.compliance.checks import Context
from mobility_model_zoo.compliance.release_checks import stage_model, stage_signoff

RC = {
    "model": "m",
    "version": "0.1.0",
    "state": "draft",
    "ai_system": {"is_system": True, "rationale": "r"},
    "gpai": {
        "is_gpai": False,
        "generative": False,
        "params": 5.6e8,
        "training_compute_flop": 1e17,
        "base_model_compute_flop": "unknown",
        "method": "6ND",
        "rationale": "encoder classifier",
    },
    "exclusion_basis": "art2_12",
    "monetisation": "none",
    "intended_purpose": "p",
    "out_of_scope": ["x"],
    "annex_iii_match": "none",
    "annex_i": {"legislation": "none", "safety_component": False, "rationale": "r"},
    "art50_trigger": "none",
    "legal_references": {"ai_act": "2024/1689", "guidelines": [], "checked_at": "2026-10-08"},
    "export": {"self_classification": "not listed", "rationale": "r"},
    "licences": {
        "weights": "Apache-2.0",
        "code": "Apache-2.0",
        "base_model": "MIT",
        "notices": [],
        "share_alike_inputs": False,
        "gated": False,
    },
    "provenance": {"sources": [], "datasets": [], "routes": [], "recipients_sha256": "0"},
    "scans": {
        "redaction_recall": 0.97,
        "art9_counts": {},
        "publication_scan": None,
        "memorisation": {"status": "not_applicable", "rationale": "extractive"},
    },
    "signed_off_by": None,
    "signed_off_at": None,
}


def ctx_with(root, rc):
    write(root, "zoo/models/m/releases/0.1.0.compliance.yaml", rc)
    return Context(load(root), model="m", version="0.1.0")


def ids(fn, ctx):
    return {f.check_id for f in fn(ctx)}


def test_clean_model_stage(register_tree):
    assert ids(stage_model, ctx_with(register_tree, RC)) == set()


def test_missing_compliance_record(register_tree):
    assert ids(stage_signoff, Context(load(register_tree), model="m", version="0.1.0")) == {"C-S1"}


def test_memorisation_missing(register_tree):
    rc = copy.deepcopy(RC)
    del rc["scans"]["memorisation"]
    write(register_tree, "zoo/models/m/releases/0.1.0.compliance.yaml", rc)
    ctx = Context(load(register_tree), model="m", version="0.1.0")
    assert ids(stage_model, ctx) == {"C-D1"}


def test_generative_needs_probe(register_tree):
    rc = copy.deepcopy(RC)
    rc["gpai"]["generative"] = True
    assert "C-D1" in ids(stage_model, ctx_with(register_tree, rc))


def test_compute_above_threshold(register_tree):
    rc = copy.deepcopy(RC)
    rc["gpai"]["training_compute_flop"] = 2e23
    assert ids(stage_model, ctx_with(register_tree, rc)) == {"C-D2"}


def test_signoff(register_tree):
    assert ids(stage_signoff, ctx_with(register_tree, RC)) == {"C-S1"}
    signed = {**RC, "state": "signed_off", "signed_off_by": "owner", "signed_off_at": "2026-10-08"}
    assert ids(stage_signoff, ctx_with(register_tree, signed)) == set()


def test_teacher_route_rights(register_tree):
    write(
        register_tree,
        "compliance/providers.yaml",
        {
            "routes": [
                route(
                    id="t-good", log_matches=["teacher-a|openrouter|P"], output_training_permitted="yes"
                ),
                route(
                    id="t-unclear",
                    log_matches=["teacher-b|openrouter|Q"],
                    output_training_permitted="unclear",
                ),
            ]
        },
    )
    reg = load(register_tree)
    assert reg.output_training_permitted("teacher-a")
    assert not reg.output_training_permitted("teacher-b")
    assert not reg.output_training_permitted("teacher-unknown")  # no route: not permitted
