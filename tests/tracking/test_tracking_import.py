"""`zoo tracking import`: past results as `imported` runs, once (feature 017 T050, T052; FR-028)."""

import json

from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture
from typer.testing import CliRunner

from mobility_model_zoo.edge.paths import repo_root
from mobility_model_zoo.release.cli import app
from mobility_model_zoo.tracking.importer import import_all, sources

runner = CliRunner()


def test_sources_of_the_repository():
    keys = {s.key for s in sources(repo_root())}
    assert {"scout-large@0.1.0", "scout-large@0.1.3", "picket-forest@0.2.1"} <= keys
    assert "cluster-v1/decision" in keys and "hum-fan/research-report" in keys
    assert not any(k.startswith("sandbox-pipeline-tiny") for k in keys)


def test_import_is_exact_dated_and_idempotent(store):  # noqa: F811
    first = dict(import_all(models=["scout-large"]))
    assert set(first.values()) == {"created"} and "scout-large@0.1.3" in first
    again = dict(import_all(models=["scout-large"]))
    assert set(again.values()) == {"exists"}

    [run] = runs_of(store, "productdev/jtbd-span", "tags.`mmz.import_key` = 'scout-large@0.1.3'")
    tags = run.data.tags
    assert tags["mmz.imported"] == "true" and tags["mmz.benchmark"] == "pilot-v2"
    assert tags["mmz.model_version"] == "0.1.3"
    quality = json.loads((repo_root() / "zoo/models/scout-large/results/0.1.3/quality.json").read_text())
    for m in quality["metrics"]:
        if isinstance(m["value"], int | float):
            assert run.data.metrics[m["name"]] == m["value"]  # exactly the repository's numbers
    assert run.info.start_time == run.info.end_time  # dated, not timed: no curves were recorded
    assert sorted(a.path for a in store.list_artifacts(run.info.run_id)) == [
        "performance.json",
        "quality.json",
    ]


def test_import_command(store):  # noqa: F811
    r = runner.invoke(app, ["tracking", "import", "--model", "picket-forest", "--dry-run"])
    assert r.exit_code == 0, r.output
    assert "would create" in r.stdout and "picket-forest@0.2.1" in r.stdout
    r = runner.invoke(app, ["tracking", "import", "--model", "picket-forest"])
    assert r.exit_code == 0 and "created" in r.stdout
