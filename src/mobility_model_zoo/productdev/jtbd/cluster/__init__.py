"""Deduplication and clustering of JTBD items (feature 009, task `jtbd-cluster`).

    from mobility_model_zoo.productdev.jtbd.cluster import ClusterStage, read_bundle

    stage = ClusterStage.from_settings("configs/productdev/jtbd/cluster-baseline.yaml")
    result = stage.run(read_bundle("bundle.jsonl"), map_dir="my-map")

The runtime modules need the base install plus numpy, scipy, scikit-learn, pyyaml and jsonschema;
the benchmark and measurement modules need the `[jtbd]` extra and are never imported here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundle
    from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

__all__ = ["ClusterStage", "read_bundle"]


def __getattr__(name: str):
    # Lazy, so `jtbd cluster check` never imports torch or scikit-learn.
    if name == "ClusterStage":
        from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

        return ClusterStage
    if name == "read_bundle":
        from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundle

        return read_bundle
    raise AttributeError(name)
