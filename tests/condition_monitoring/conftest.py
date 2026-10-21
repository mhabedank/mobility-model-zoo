"""Fixtures of the condition-monitoring tests (helpers in condmon_helpers.py)."""

from __future__ import annotations

import pytest
from condmon_helpers import CRITERIA_YAML, HarTree, write_har


@pytest.fixture
def har_tree(tmp_path, monkeypatch) -> HarTree:
    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    return write_har(tmp_path)


@pytest.fixture
def frozen(har_tree, tmp_path, monkeypatch):
    """A temporary repository with the frozen manifest and the committed criteria record."""
    from mobility_model_zoo.condition_monitoring import benchmark as bm
    from mobility_model_zoo.condition_monitoring.activity import train as pace

    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(bm, "repo", lambda: root)
    manifest = pace.build_manifest()
    path = bm.manifest_path("uci-har-v1")
    bm.freeze(path, manifest)
    criteria = root / "configs/condition-monitoring/activity/pace-cnn-criteria.yaml"
    criteria.parent.mkdir(parents=True)
    criteria.write_text(CRITERIA_YAML)
    return root
