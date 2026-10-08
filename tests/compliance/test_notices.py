"""Notices and drift checks (C-N1, C-N2, C-N3)."""

from compliance_helpers import load, write
from test_render import _tree  # noqa: E402

from mobility_model_zoo.compliance import render
from mobility_model_zoo.compliance.checks import Context, stage_drift, stage_notices


def _rendered(root):
    render.write_all(load(root))
    return root


def ids(fn, root):
    return {f.check_id for f in fn(Context(load(root)))}


def test_clean_render_passes(register_tree):
    root = _rendered(_tree(register_tree))
    assert ids(stage_notices, root) == set()
    assert ids(stage_drift, root) == set()


def test_route_missing_from_privacy_notice(register_tree):
    root = _rendered(_tree(register_tree))
    privacy = root / "PRIVACY.md"
    privacy.write_text(privacy.read_text().replace("`local-model`", "`something-else`"))
    assert "C-N1" in ids(stage_notices, root)


def test_unregistered_recipient(register_tree):
    root = _rendered(_tree(register_tree))
    write(
        root,
        "compliance/recipients.yaml",
        {
            "generated_at": "2026-10-08",
            "sources": [],
            "recipients": [
                {
                    "route_id": "unregistered",
                    "model_id": "m",
                    "backend": "openrouter",
                    "hosting_provider": "X",
                    "roles": ["teacher"],
                    "first_call": None,
                    "last_call": None,
                    "calls_ok": 1,
                    "calls_error": 0,
                    "runs": ["r"],
                }
            ],
        },
    )
    assert "C-N1" in ids(stage_notices, root)


def test_retention_differs(register_tree):
    root = _rendered(_tree(register_tree))
    privacy = root / "PRIVACY.md"
    privacy.write_text(privacy.read_text().replace("review 24 months after freeze", "kept forever"))
    assert "C-N2" in ids(stage_notices, root)


def test_hand_edited_notice_is_drift(register_tree):
    root = _rendered(_tree(register_tree))
    notice = root / "NOTICE"
    notice.write_text(notice.read_text() + "\nedited by hand\n")
    assert ids(stage_drift, root) == {"C-N3"}
