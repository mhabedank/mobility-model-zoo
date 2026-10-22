"""Integrity of frozen benchmarks (feature 017 T022, T026; FR-007, constitution IX)."""

import json

from inventory_helpers import commit, fixture_repo, init_git

from mobility_model_zoo.datasets.inventory import collect, find, integrity


def _write(path, manifest):
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def _committed(tmp_path):
    root, data = fixture_repo(tmp_path)
    init_git(root)
    commit(root, "frozen benchmarks", "2026-10-05")
    return root, data


def test_based_on_mismatch_after_parent_edit(tmp_path):
    root, data = fixture_repo(tmp_path)
    path = root / "topics/alpha/benchmarks/cap-v1/manifest.json"
    m = json.loads(path.read_text())
    m["captures"][0]["frames"] = 999
    _write(path, m)
    v2 = find(collect(root, data), "cap-v2")[0]
    assert v2.integrity == "mismatch"


def test_content_change_after_freeze_is_flagged(tmp_path):
    root, data = _committed(tmp_path)
    path = root / "topics/beta/benchmarks/pilot-v1/manifest.json"
    m = json.loads(path.read_text())
    m["chunks"]["ch-4"] = "h4"
    _write(path, m)
    sha = commit(root, "edit a frozen pilot", "2026-10-06")
    pilot = find(collect(root, data), "pilot-v1")[0]
    assert pilot.integrity == "changed-after-freeze"
    assert any(sha[:12] in n and "chunks" in n for n in pilot.notes)


def test_lifecycle_refreeze_and_recorded_revision_are_allowed(tmp_path):
    root, data = _committed(tmp_path)
    path = root / "topics/beta/benchmarks/cluster-v1/manifest.json"
    m = json.loads(path.read_text())
    m["state"] = "decided"
    m["events"].append({"at": "2026-10-06", "state": "decided", "event": "decision go"})
    _write(path, m)
    commit(root, "lifecycle only", "2026-10-06")
    m["hashes"]["pairs"] = "p2"
    m["revisions"].append({"at": "2026-10-07", "previous": {"pairs": "p1"}})
    _write(path, m)
    commit(root, "recorded revision", "2026-10-07")
    m["hashes"]["budget"] = "b2"
    m["events"].append({"at": "2026-10-08", "state": "frozen", "event": "re-frozen before any labeling"})
    _write(path, m)
    commit(root, "re-frozen before labeling", "2026-10-08")
    assert integrity.frozen_violation(root, "topics/beta/benchmarks/cluster-v1/manifest.json") is None
    assert find(collect(root, data), "cluster-v1")[0].integrity == "ok"


def test_unrecorded_hash_change_is_flagged(tmp_path):
    root, _data = _committed(tmp_path)
    path = root / "topics/beta/benchmarks/cluster-v1/manifest.json"
    m = json.loads(path.read_text())
    m["hashes"]["pairs"] = "p2"
    _write(path, m)
    commit(root, "silent hash change", "2026-10-06")
    sha, _date, keys = integrity.frozen_violation(
        root, "topics/beta/benchmarks/cluster-v1/manifest.json"
    )
    assert keys == ["hashes"]


def test_verify_without_data_leaves_rows_unchecked(tmp_path):
    root, data = fixture_repo(tmp_path)
    inv = collect(root, data, verify=True)
    pilot = find(inv, "pilot-v1")[0]
    assert pilot.integrity == "unchecked"
    assert any("content check" in n for n in pilot.notes)
