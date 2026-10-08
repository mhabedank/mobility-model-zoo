"""Helpers for compliance tests: a minimal valid register (synthetic data only)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml

TODAY = dt.date(2026, 10, 8)
REVIEW = {"owner": "owner", "last_reviewed": "2026-10-08", "next_review": "2027-04-08"}


def controller() -> dict[str, Any]:
    return {
        "name": "Test Controller (private person)",
        "privacy_contact": "privacy@example.org",
        "general_contact": "contact@example.org",
        "imprint_url": "https://example.org/imprint.html",
        "website_privacy_url": "https://example.org/privacy.html",
        "supervisory_authority": "Test Authority",
        "commercial_activity": "none",
        **REVIEW,
    }


def source_class() -> dict[str, Any]:
    return {
        "id": "cc-papers",
        "description": "Papers under Creative Commons licences",
        "copyright_basis": "licence",
        "gdpr_legal_basis": "art6_1_f",
        "lia": {
            "purpose": "p",
            "necessity": "n",
            "balancing": "b",
            "safeguards": "s",
            "decided_at": "2026-10-08",
        },
        "art9_handling": "quarantine",
        "retention_purpose": "reproduce the benchmark",
        "retention_rule": "review 24 months after freeze",
        **REVIEW,
    }


def source(**over: Any) -> dict[str, Any]:
    rec = {
        "id": "paper-one",
        "class": "cc-papers",
        "origin_url": "https://example.org/paper-one",
        "title": "Paper One",
        "creators": ["Erika Mustermann"],
        "publisher": "Example Press",
        "licence": "CC-BY-4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution_text": '"Paper One" by Erika Mustermann, CC BY 4.0',
        "modifications": "extracted text, chunked, redacted, labeled",
        "permitted_use": "training_allowed",
        "redistribution": "not_allowed",
        "redistribution_basis": "training texts are not redistributed",
        "quote_allowed": True,
        "signals": {
            "robots": "allow",
            "tdmrep": "absent",
            "x_robots": "absent",
            "meta_noai": "absent",
            "ai_txt": "absent",
            "checked_at": "2026-10-08",
            "retrospective": True,
        },
        "personal_data": {
            "present": False,
            "categories": [],
            "special_categories": [],
            "human_subjects": False,
        },
        "storage": "data/snapshots",
        "retention_until": "2028-10-01",
        "used_by": ["model-x@0.1.0"],
        **REVIEW,
    }
    rec.update(over)
    return rec


def route(**over: Any) -> dict[str, Any]:
    rec = {
        "id": "local-model",
        "model_id": "local-model",
        "access_path": "local",
        "hosting_provider": "self",
        "region": "DE",
        "dpf_listed": False,
        "zero_data_retention": True,
        "training_on_inputs": False,
        "dpa": False,
        "terms_url": "https://example.org/model-licence",
        "terms_checked_at": "2026-10-08",
        "output_training_permitted": "yes",
        "allowed_for": ["teacher"],
        **REVIEW,
    }
    rec.update(over)
    return rec


def decision(**over: Any) -> dict[str, Any]:
    rec = {
        "id": "D-test",
        "date": "2026-10-08",
        "decision": "d",
        "rationale": "r",
        "scope": ["*"],
        "review_by": "2027-04-08",
        "decided_by": "owner",
    }
    rec.update(over)
    return rec


def write(root: Path, rel: str, data: Any) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def load(root: Path, today: dt.date = TODAY):
    from mobility_model_zoo.compliance.register import Register

    return Register.load(root, today=today)


def seed(root: Path, rel: str, mutate) -> None:
    """Load a register file, apply `mutate(data)`, write it back."""
    path = root / rel
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def make_register_tree(root: Path) -> Path:
    """A repository layout with a minimal valid register."""
    write(root, "zoo/topics.yaml", {"topics": []})
    write(root, "compliance/controller.yaml", controller())
    write(root, "compliance/decisions.yaml", {"decisions": [decision()]})
    write(root, "compliance/providers.yaml", {"routes": [route()]})
    write(root, "compliance/waivers.yaml", {"waivers": []})
    write(root, "compliance/requests.yaml", {"requests": []})
    write(root, "compliance/legal-watch.yaml", {"items": []})
    write(root, "topics/t/compliance/source-classes.yaml", {"classes": [source_class()]})
    write(root, "topics/t/compliance/sources.yaml", {"sources": [source()]})
    return root
