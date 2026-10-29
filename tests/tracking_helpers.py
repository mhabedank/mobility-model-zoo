"""A real tracking store in a temporary directory for the tracking tests (feature 017).

MLflow's file store runs in-process with the skinny client, so the tests exercise the real client
API (runs, batches, dataset inputs, search filters) without a server.
"""

from __future__ import annotations

import pytest

from mobility_model_zoo.tracking import client as tc


@pytest.fixture
def store(tmp_path, monkeypatch):
    pytest.importorskip("mlflow")
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file://{tmp_path / 'store'}")
    monkeypatch.setattr(tc, "STRICT", False)
    return tc.new_client()


def runs_of(client, experiment: str, flt: str = ""):
    exp = client.get_experiment_by_name(experiment)
    return [] if exp is None else list(client.search_runs([exp.experiment_id], filter_string=flt))
