"""History of registers and benchmarks from git, and version diffs (feature 017 T021, T023, T025)."""

import json

import yaml
from inventory_helpers import commit, fixture_repo, git, init_git

from mobility_model_zoo.datasets.inventory import collect, find, history
from mobility_model_zoo.datasets.inventory.diff import diff


def _repo_with_history(tmp_path):
    root, data = fixture_repo(tmp_path)
    cap_v2 = root / "topics/alpha/benchmarks/cap-v2"
    held = tmp_path / "cap-v2"
    cap_v2.rename(held)
    init_git(root)
    first = commit(root, "datasets, pilot, cap-v1", "2026-10-03")
    reg = root / "topics/alpha/compliance/datasets.yaml"
    data_yaml = yaml.safe_load(reg.read_text())
    data_yaml["datasets"][0]["permitted_use"] = "benchmark_only"
    reg.write_text(yaml.safe_dump(data_yaml, sort_keys=False))
    second = commit(root, "ds-a becomes benchmark_only", "2026-10-04")
    held.rename(cap_v2)
    third = commit(root, "cap-v2", "2026-10-05")
    return root, data, (first, second, third)


def test_register_events_with_old_and_new_values(tmp_path):
    root, _data, (first, second, _third) = _repo_with_history(tmp_path)
    rel = "topics/alpha/compliance/datasets.yaml"
    events = history.register_events(root, rel, "datasets", "dataset:ds-a@register", "ds-a")
    assert [(e.event, e.commit) for e in events] == [("registered", first), ("field-changed", second)]
    change = events[1]
    assert (change.field, change.old, change.new) == (
        "permitted_use",
        "training_allowed",
        "benchmark_only",
    )
    assert history.record_last_change(root, rel, "datasets", "ds-a") == "2026-10-04"
    assert history.record_last_change(root, rel, "datasets", "ds-b") == "2026-10-03"


def test_benchmark_freeze_and_lineage_events(tmp_path):
    root, data, (_first, _second, third) = _repo_with_history(tmp_path)
    inv = collect(root, data)
    v2 = find(inv, "cap-v2")[0]
    events = history.manifest_events(root, v2)
    assert ("frozen", third) in [(e.event, e.commit) for e in events]
    superseded = [e for e in events if e.event == "superseded"]
    assert superseded and superseded[0].old == "cap@cap-v1"
    assert any(e.event == "excluded" and e.new == "ds-a/set_01/2" for e in events)
    assert v2.last_change == "2026-10-05"


def test_shallow_clone_is_flagged(tmp_path):
    root, _data, _ = _repo_with_history(tmp_path)
    clone = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth", "1", f"file://{root}", str(clone))
    assert history.is_shallow(clone)
    assert not history.is_shallow(root)


def test_diff_counts_members_and_settings(tmp_path):
    root, data = fixture_repo(tmp_path)
    inv = collect(root, data)
    a, b = find(inv, "cap-v1")[0], find(inv, "cap-v2")[0]
    d = diff(root, a, b, members=True)
    assert d.counts["captures"] == {"a": 4, "b": 4, "delta": 0}
    assert d.distribution["role"]["train"] == {"a": 2, "b": 1, "delta": -1}
    assert d.members == {"added": [], "removed": [], "changed": ["ds-a/set_01/2"]}
    assert d.protocol["protocol.grace_s"] == {"a": 1.0, "b": 2.0}
    assert diff(root, a, b).members["changed"] == ["1 member(s)"]
    assert json.dumps(d.to_dict())  # serialisable for --json
