"""`zoo data publish`: one run per data version, idempotent (feature 017 T034, T035; FR-014-FR-016)."""

from inventory_helpers import fixture_repo
from tracking_helpers import runs_of, store  # noqa: F401 - pytest fixture

from mobility_model_zoo.datasets.inventory import collect
from mobility_model_zoo.tracking.publish import publish


def test_create_update_supersede(store, tmp_path):  # noqa: F811
    root, data = fixture_repo(tmp_path)
    rows = collect(root, data).rows
    first = {a.row: a.action for a in publish(rows, profile=True)}
    assert set(first.values()) == {"create"}
    again = {a.row: a.action for a in publish(collect(root, data).rows)}
    assert set(again.values()) == {"update"}
    runs = runs_of(store, "datasets", "tags.`mmz.id` = 'cap' and tags.`mmz.version` = 'cap-v2'")
    [run] = runs
    assert run.data.metrics["count.captures"] == 4
    assert run.data.metrics["dist.role.excluded"] == 1
    assert run.data.tags["mmz.permitted_use"] == "training_allowed"
    assert [a.path for a in store.list_artifacts(run.info.run_id)] == ["profile.json"]
    # a changed version (new hash) is a new run; the old one is marked superseded
    path = root / "topics/alpha/benchmarks/cap-v2/manifest.json"
    path.write_text(path.read_text().replace('"grace_s": 2.0', '"grace_s": 3.0'))
    changed = {a.row: a.action for a in publish(collect(root, data).rows)}
    assert changed["cap@cap-v2"] == "supersede"
    both = runs_of(store, "datasets", "tags.`mmz.id` = 'cap' and tags.`mmz.version` = 'cap-v2'")
    assert len(both) == 2
    assert sum("mmz.superseded_by" in r.data.tags for r in both) == 1


def test_register_row_is_superseded_by_a_downloaded_version(store, tmp_path):  # noqa: F811
    root, data = fixture_repo(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    publish(collect(root, empty, kinds=["dataset"]).rows)  # a machine without the data
    publish(collect(root, data, kinds=["dataset"]).rows)  # the machine with it
    runs = runs_of(store, "datasets", "tags.`mmz.id` = 'ds-a'")
    by_version = {r.data.tags["mmz.version"]: r for r in runs}
    assert set(by_version) == {"register", "2026-10-01"}
    assert by_version["register"].data.tags["mmz.superseded_by"] == by_version["2026-10-01"].info.run_id
    actions = {a.row: a.action for a in publish(collect(root, empty, kinds=["dataset"]).rows)}
    assert actions["ds-a@register"] == "skip"  # no resurrection from a machine without the data


def test_dry_run_without_uri(tmp_path, monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    from mobility_model_zoo.tracking import config

    monkeypatch.setattr(config, "_dotenv_keys", lambda: {})
    root, data = fixture_repo(tmp_path)
    actions = publish(collect(root, data).rows, dry_run=True)
    assert {a.action for a in actions} == {"create"}
    assert all("no server asked" in a.note for a in actions)


def test_dry_run_writes_nothing(store, tmp_path):  # noqa: F811
    root, data = fixture_repo(tmp_path)
    publish(collect(root, data).rows, dry_run=True)
    assert runs_of(store, "datasets") == []
