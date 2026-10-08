"""Repository layout by topic (feature 005, FR-001, FR-003)."""

from pathlib import Path

import yaml

from mobility_model_zoo.release.cli import topic_folder_failures
from mobility_model_zoo.release.registry import Registry

ROOT = Path(__file__).resolve().parents[2]


def test_every_public_topic_has_its_folder():
    assert topic_folder_failures(Registry(ROOT)) == []


def test_no_jtbd_folder_at_top_level():
    for name in ("guideline", "reports", "benchmarks", "spike", "deploy", "docs/recipes"):
        assert not (ROOT / name).exists(), name


def test_missing_topic_folder_is_reported(tmp_path):
    (tmp_path / "zoo").mkdir()
    (tmp_path / "zoo/topics.yaml").write_text(yaml.safe_dump({"topics": [
        {"id": "security", "title": "S", "description": "d", "hf_collection": None},
        {"id": "sandbox", "title": "P", "description": "d", "hf_collection": None}]}))
    failures = topic_folder_failures(Registry(tmp_path))
    assert failures == ["topic security: topics/security/README.md is missing",
                        "topic security: topics/security/compliance/datasets.yaml is missing"]
