"""Collectors of the data overview on the fixture repository (feature 017 T010-T015, T019)."""

from inventory_helpers import fixture_repo

from mobility_model_zoo.datasets.inventory import collect, find


def rows_by_name(inv):
    return {r.name: r for r in inv.rows}


def test_every_kind_is_collected(tmp_path):
    root, data = fixture_repo(tmp_path)
    inv = collect(root, data)
    names = set(rows_by_name(inv))
    assert names == {
        "ds-a@2026-10-01",
        "ds-b@register",
        "beta-sources@current",
        "train@train-v1",
        "cap@cap-v1",
        "cap@cap-v2",
        "pilot@pilot-v1",
        "cluster@cluster-v1",
    }
    assert inv.hidden == 1  # ds-gone is rejected
    assert "alpha: no benchmarks frozen yet" not in inv.notes


def test_downloaded_dataset_is_measured_without_reading_data(tmp_path):
    root, data = fixture_repo(tmp_path)
    r = rows_by_name(collect(root, data))["ds-a@2026-10-01"]
    assert r.availability == "measured"
    assert r.files == 3 and r.size_mb is not None
    assert r.sha256 is not None and r.licence == "CC-BY-4.0"
    assert r.used_by == ["demo-model@0.1.0"]  # from the release record's provenance


def test_dataset_not_downloaded_is_register_only(tmp_path):
    root, _data = fixture_repo(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    r = rows_by_name(collect(root, empty))["ds-a@register"]
    assert r.availability == "register-only"
    assert r.sha256 is None and r.approx_size_mb == 12
    assert "not downloaded here" in r.notes


def test_rejected_datasets_on_request(tmp_path):
    root, data = fixture_repo(tmp_path)
    inv = collect(root, data, include_rejected=True)
    assert "ds-gone@register" in rows_by_name(inv)
    assert inv.hidden == 0


def test_can_benchmark_counts_lineage_and_use(tmp_path):
    root, data = fixture_repo(tmp_path)
    rows = rows_by_name(collect(root, data))
    v2 = rows["cap@cap-v2"]
    assert v2.counts["captures"] == 4 and v2.counts["frames"] == 400
    assert v2.distribution["role"] == {"excluded": 1, "test": 2, "train": 1}
    assert v2.distribution["attack_family"] == {"DoS": 2, "fuzzing": 1, "none": 1}
    assert {
        "relation": "based_on",
        "target": "cap@cap-v1",
        "sha256": rows["cap@cap-v1"].sha256,
    } in v2.lineage
    assert v2.permitted_use == "training_allowed" and v2.licence == "CC-BY-4.0"
    assert v2.used_by == ["demo-model@0.1.0"]
    assert v2.integrity == "ok"  # based_on hash matches


def test_jtbd_manifests_and_strictest_use(tmp_path):
    root, data = fixture_repo(tmp_path)
    rows = rows_by_name(collect(root, data))
    pilot = rows["pilot@pilot-v1"]
    assert pilot.counts == {"chunks": 3, "holdout_chunks": 1, "train_chunks": 0}
    assert pilot.permitted_use == "benchmark_only"  # one source is benchmark_only
    assert "current benchmark of the task" in pilot.notes
    cluster = rows["cluster@cluster-v1"]
    assert cluster.counts["items"] == 12 and cluster.counts["pairs"] == 8
    assert cluster.distribution["pairs_by_level"] == {"high": 5, "random": 3}
    assert cluster.counts["excluded_items"] == 2


def test_source_collection_and_training_set(tmp_path):
    root, data = fixture_repo(tmp_path)
    rows = rows_by_name(collect(root, data))
    src = rows["beta-sources@current"]
    assert src.counts == {"sources": 3, "snapshot_files": 1}
    assert src.availability == "measured"
    assert src.distribution["source_class"] == {"forum-review": 1, "paper": 2}
    train = rows["train@train-v1"]
    assert train.sha256 == "f00d" and train.frozen_at == "2026-10-02"
    assert train.counts["chunks"] == 4 and train.counts["rows_train"] == 8
    assert train.distribution["language"] == {"de": 6, "en": 4}
    assert train.used_by == ["demo-model@0.1.0"]  # recipe config names train-v1


def test_filters(tmp_path):
    root, data = fixture_repo(tmp_path)
    assert {r.kind for r in collect(root, data, kinds=["benchmark"]).rows} == {"benchmark"}
    assert {r.topic for r in collect(root, data, topics=["alpha"]).rows} == {"alpha"}
    only = collect(root, data, use="benchmark_only").rows
    assert only and all(r.permitted_use == "benchmark_only" for r in only)


def test_malformed_manifest_is_an_error_row(tmp_path):
    root, data = fixture_repo(tmp_path)
    (root / "topics/alpha/benchmarks/cap-v1/manifest.json").write_text("{not json")
    rows = rows_by_name(collect(root, data))
    assert rows["cap@cap-v1"].availability == "error"
    assert rows["pilot@pilot-v1"].availability == "measured"  # the rest still prints


def test_dataset_declared_in_two_topics_is_one_error_row(tmp_path):
    root, data = fixture_repo(tmp_path)
    (root / "topics/beta/compliance/datasets.yaml").write_text(
        (root / "topics/alpha/compliance/datasets.yaml").read_text()
    )
    inv = collect(root, data, include_rejected=True)
    ds_a = [r for r in inv.rows if r.id == "ds-a"]
    assert len(ds_a) == 1 and ds_a[0].availability == "error"


def test_find(tmp_path):
    root, data = fixture_repo(tmp_path)
    inv = collect(root, data)
    assert [r.version for r in find(inv, "cap")] == ["cap-v1", "cap-v2"]
    assert [r.version for r in find(inv, "cap-v2")] == ["cap-v2"]
    assert [r.name for r in find(inv, "ds-a@2026-10-01")] == ["ds-a@2026-10-01"]
