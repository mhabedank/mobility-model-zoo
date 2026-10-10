"""Fixtures of the cluster tests (feature 009)."""

from __future__ import annotations

import pytest
from cluster_helpers import BUNDLES, SETTINGS


@pytest.fixture
def basic_result(tmp_path):
    from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundle
    from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

    bundle = BUNDLES / "basic.jsonl"
    stage = ClusterStage.from_settings(SETTINGS)
    return stage.run(read_bundle(bundle), map_dir=tmp_path / "map", bundle_paths=[bundle])
