"""Rendering of the public compliance documents (contracts/documents.md)."""

from compliance_helpers import load, write

from mobility_model_zoo.compliance import render


def _tree(root):
    write(
        root,
        "compliance/recipients.yaml",
        {
            "generated_at": "2026-10-08",
            "sources": [],
            "recipients": [
                {
                    "route_id": "local-model",
                    "model_id": "local-model",
                    "backend": "ollama",
                    "hosting_provider": "local:box",
                    "roles": ["teacher"],
                    "first_call": "2026-10-01T00:00:00Z",
                    "last_call": "2026-10-02T00:00:00Z",
                    "calls_ok": 3,
                    "calls_error": 1,
                    "runs": ["r1"],
                }
            ],
        },
    )
    write(
        root,
        "compliance/decisions.yaml",
        {
            "decisions": [
                {
                    "id": d,
                    "date": "2026-10-08",
                    "decision": f"decision {d}",
                    "rationale": "r",
                    "scope": ["*"],
                    "review_by": "2027-04-08",
                    "decided_by": "owner",
                }
                for d in ("D6", "D10", "D11", "D12", "D-parl-art9")
            ]
        },
    )
    write(
        root,
        "zoo/models/model-x/model.yaml",
        {"topic": "t", "base_model": "FacebookAI/xlm-roberta-large"},
    )
    write(root, "zoo/models/model-x/releases/0.1.0.yaml", {"version": "0.1.0"})
    return root


def test_render_contains_required_elements(register_tree):
    reg = load(_tree(register_tree))
    out = render.render_all(reg)
    assert set(render.OUTPUTS) <= set(out)
    privacy = out["PRIVACY.md"]
    for needle in (
        "privacy@example.org",
        "https://example.org/imprint.html",
        "Art. 14 GDPR",
        "Art. 6(1)(f)",
        "## Your right to object (Art. 21 GDPR)",
        "`local-model`",
        "review 24 months after freeze",
        "Test Authority",
        "Papers under Creative Commons",
    ):
        assert needle in privacy, needle
    copyright_policy = out["COPYRIGHT_POLICY.md"]
    for needle in (
        "§44b",
        "robots.txt",
        "TDMRep",
        "noai",
        "ai.txt",
        "decision D6",
        "14 days",
        "30 consecutive words",
    ):
        assert needle in copyright_policy, needle
    assert "Copyright (c) Facebook, Inc. and its affiliates." in out["NOTICE"]
    tpn = out["THIRD_PARTY_NOTICES.md"]
    assert "| Paper One | Erika Mustermann | https://example.org/paper-one |" in tpn  # licence credit
    assert "privacy@example.org" in out[".github/ISSUE_TEMPLATE/rights-request.yml"]
    assert "Do not post personal data" in out[".github/ISSUE_TEMPLATE/rights-request.yml"]
    assert "Art. 30" in out["docs/compliance/record-of-processing.md"]
    assert "Short impact assessment" in out["docs/compliance/lia-dpia.md"]
    assert out == render.render_all(reg)  # deterministic


def test_attribution_only_for_training_sources(register_tree):
    from compliance_helpers import seed

    root = _tree(register_tree)
    seed(
        root,
        "topics/t/compliance/sources.yaml",
        lambda d: d["sources"][0].update(used_by=["benchmark:b"]),
    )
    assert "Paper One" not in render.render_all(load(root))["THIRD_PARTY_NOTICES.md"]


def test_no_branding_in_generated_text(register_tree):
    out = render.render_all(load(_tree(register_tree)))
    assert not any("Miskatonic" in text for text in out.values())
