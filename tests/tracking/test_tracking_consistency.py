"""Tags that make runs comparable, across the integrations (feature 017 T054; constitution VIII).

Every run names its task and topic; an evaluation names its frozen benchmark (spikes excepted, they
are never benchmark results); a training names its training data; a measurement names its hardware.
"""

import json

from tracking_helpers import store  # noqa: F401 - pytest fixture

from mobility_model_zoo import tracking
from mobility_model_zoo.edge.bench.results import Recorder, write_summary
from mobility_model_zoo.security.can_ids import track
from mobility_model_zoo.tracking.importer import import_results


def _all_runs(client):
    return [r for e in client.search_experiments() for r in client.search_runs([e.experiment_id])]


def test_every_integration_tags_its_runs_for_comparison(store, tmp_path):  # noqa: F811
    track.evaluation({"detectors": {"picket-forest": {"recall": 0.9}}}, "can-ids-v3", "picket-forest")
    track.protocol_evaluation({"set_01": {"all": {"f1": 0.8}}}, "can-train-and-test")
    export = tmp_path / "export"
    export.mkdir()
    (export / "config.json").write_text(json.dumps({"benchmark": "can-ids-v3"}))
    track.training({"tree_nodes": 10}, "can-ids-v3", export, None)
    track.measurement([{"name": "latency_ms", "value": 1.0}], "host", None, "0.2.1")
    rec = Recorder(tmp_path / "hil")
    rec.record("bench", "sim", model="hum-fan", us_avg=10.0, n=1)
    write_summary(tmp_path / "hil")
    with tracking.run(
        "productdev/jtbd-span",
        "train",
        "jtbd-span",
        tags={"mmz.kind": "train", "mmz.training_set": "span-train-v1"},
    ) as r:
        r.log_step(1, {"loss": 1.0})
    import_results(models=["picket-forest"])

    runs = _all_runs(store)
    assert len(runs) >= 7
    for run in runs:
        tags, where = run.data.tags, f"{run.info.run_name}: {run.data.tags}"
        assert tags.get("mmz.task") and tags.get("mmz.topic"), where
        kind = tags.get("mmz.kind")
        if kind == "evaluate" and tags.get("mmz.spike") != "true":
            assert tags.get("mmz.benchmark"), where
        if kind == "train":
            assert tags.get("mmz.training_set"), where
        if kind == "measure":
            assert tags.get("mmz.hardware"), where
        if kind == "import":
            assert tags.get("mmz.imported") == "true" and tags.get("mmz.import_key"), where


def test_metric_names_are_stable_across_runs(store):  # noqa: F811
    result = {"detectors": {"picket-forest": {"recall": 0.9, "false_alarms_per_hour": 0.4}}}
    track.evaluation(result, "can-ids-v3", "picket-forest")
    track.evaluation(result, "can-ids-v3", "picket-forest")
    a, b = _all_runs(store)
    assert set(a.data.metrics) == set(b.data.metrics)
