"""`zoo data stats|history|diff` (feature 017 T017, T020, T024; contracts/cli.md)."""

import json
import time

import pytest
from inventory_helpers import fixture_repo
from typer.testing import CliRunner

from mobility_model_zoo.release.cli import app

runner = CliRunner()


@pytest.fixture
def fixture_env(tmp_path, monkeypatch):
    """The CLI on the fixture repository: repo_root and MMZ_DATA point at the copies."""
    root, data = fixture_repo(tmp_path)
    monkeypatch.setenv("MMZ_DATA", str(data))
    import mobility_model_zoo.edge.paths as paths

    monkeypatch.setattr(paths, "repo_root", lambda: root)
    return root, data


def test_stats_table_and_footer(fixture_env):
    r = runner.invoke(app, ["data", "stats"])
    assert r.exit_code == 0, r.output
    assert "cap-v2" in r.stdout and "4 captures" in r.stdout
    assert "hidden: 1 rejected or broken dataset(s)" in r.stdout
    assert "ds-gone" not in r.stdout


def test_stats_json_and_filters(fixture_env):
    r = runner.invoke(app, ["data", "stats", "--json", "--kind", "benchmark", "--topic", "alpha"])
    assert r.exit_code == 0, r.output
    rows = json.loads(r.stdout)
    assert [x["version"] for x in rows] == ["cap-v1", "cap-v2"]
    r = runner.invoke(app, ["data", "stats", "--json", "--use", "benchmark_only"])
    assert {x["permitted_use"] for x in json.loads(r.stdout)} == {"benchmark_only"}
    r = runner.invoke(app, ["data", "stats", "--json", "--include-rejected"])
    assert "ds-gone" in {x["id"] for x in json.loads(r.stdout)}


def test_stats_without_downloaded_data(fixture_env, tmp_path, monkeypatch):
    empty = tmp_path / "nothing"
    empty.mkdir()
    monkeypatch.setenv("MMZ_DATA", str(empty))
    r = runner.invoke(app, ["data", "stats", "--wide"])
    assert r.exit_code == 0, r.output
    assert "~12 MB" in r.stdout  # register size of ds-a


def test_stats_exits_7_on_a_changed_parent_manifest(fixture_env):
    root, _ = fixture_env
    path = root / "topics/alpha/benchmarks/cap-v1/manifest.json"
    m = json.loads(path.read_text())
    m["protocol"]["seed"] = 2
    path.write_text(json.dumps(m))
    r = runner.invoke(app, ["data", "stats"])
    assert r.exit_code == 7
    assert "cap@cap-v2" in r.stdout and "based_on hash differs" in r.stdout


def test_diff_and_kind_mismatch(fixture_env):
    r = runner.invoke(app, ["data", "diff", "cap-v1", "cap-v2", "--members", "--json"])
    assert r.exit_code == 0, r.output
    d = json.loads(r.stdout)
    assert d["distribution"]["role"]["excluded"] == {"a": 0, "b": 1, "delta": 1}
    assert d["members"]["changed"] == ["ds-a/set_01/2"]
    assert d["protocol"]["protocol.grace_s"] == {"a": 1.0, "b": 2.0}
    assert runner.invoke(app, ["data", "diff", "cap-v1", "pilot-v1"]).exit_code == 2


def test_history_outside_git_says_so(fixture_env):
    r = runner.invoke(app, ["data", "history", "cap"])
    assert r.exit_code == 0, r.output
    assert "frozen" in r.stdout and "lineage: cap@cap-v1 -> cap@cap-v2" in r.stdout
    assert "history incomplete" in r.stdout
    assert runner.invoke(app, ["data", "history", "nope"]).exit_code == 2


def test_real_repository_counts_and_speed():
    """The committed benchmarks, counted as in the quickstart (SC-001, SC-002)."""
    start = time.monotonic()
    r = runner.invoke(app, ["data", "stats", "--json", "--kind", "benchmark"])
    assert time.monotonic() - start < 30
    assert r.exit_code in (0, 7), r.output
    rows = {x["version"]: x for x in json.loads(r.stdout)}
    v3 = rows["can-ids-v3"]
    assert v3["counts"]["captures"] == 281
    assert v3["distribution"]["role"] == {
        "excluded": 6,
        "out_of_scope": 17,
        "test": 183,
        "train": 47,
        "validation": 28,
    }
    assert rows["cluster-v1"]["distribution"]["items_by_split"] == {
        "dev": 3395,
        "test": 6967,
        "holdout": 2133,
    }
