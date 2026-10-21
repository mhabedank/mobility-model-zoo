"""Gate rule 9: benchmark trace of the runs (feature 021, T056; research R22, spec US1 scenario 4)."""

import hashlib
import json
import subprocess

from mobility_model_zoo.release.benchmark_trace import trace_findings

BENCH = "b-v1"


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()


def _setup(root, runs=None, manifest_text='{"benchmark": "b-v1"}'):
    m = root / "topics" / "t" / "benchmarks" / BENCH / "manifest.json"
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(manifest_text)
    sha = hashlib.sha256(m.read_bytes()).hexdigest()
    r = root / "topics" / "t" / "reports" / "m" / "0.1.0" / "evaluation.json"
    r.parent.mkdir(parents=True, exist_ok=True)
    r.write_text(json.dumps({"runs": runs if runs is not None else []}))
    return sha


def _run(sha, commit, trained_at="2999-01-01T00:00:00Z", seed=0):
    return {"seed": seed, "manifest_sha256": sha, "criteria_commit": commit, "trained_at": trained_at}


def test_matching_runs_after_the_criteria_commit_pass(zoo_env):
    head = _git(zoo_env.root, "rev-parse", "HEAD")
    sha = _setup(zoo_env.root)
    _setup(zoo_env.root, [_run(sha, head), _run(sha, head, seed=1)])
    failures, note = trace_findings(zoo_env.root, "t", "m", "0.1.0", BENCH)
    assert failures == []
    assert note.startswith("benchmark trace: 2 runs on frozen b-v1")


def test_a_run_on_another_manifest_fails(zoo_env):
    head = _git(zoo_env.root, "rev-parse", "HEAD")
    sha = _setup(zoo_env.root)
    _setup(zoo_env.root, [_run(sha, head), _run("0" * 64, head, seed=1)])
    failures, _ = trace_findings(zoo_env.root, "t", "m", "0.1.0", BENCH)
    assert failures and "seed 1" in failures[0]


def test_criteria_committed_after_the_first_run_fail(zoo_env):
    head = _git(zoo_env.root, "rev-parse", "HEAD")
    sha = _setup(zoo_env.root)
    _setup(zoo_env.root, [_run(sha, head, trained_at="2000-01-01T00:00:00Z")])
    failures, _ = trace_findings(zoo_env.root, "t", "m", "0.1.0", BENCH)
    assert failures and "not older than the first run" in failures[0]


def test_unknown_criteria_commit_fails(zoo_env):
    sha = _setup(zoo_env.root)
    _setup(zoo_env.root, [_run(sha, "f" * 40)])
    failures, _ = trace_findings(zoo_env.root, "t", "m", "0.1.0", BENCH)
    assert failures and "not in the history" in failures[0]


def test_releases_without_manifest_or_run_list_skip_with_a_note(zoo_env):
    failures, note = trace_findings(zoo_env.root, "t", "m", "0.1.0", BENCH)
    assert failures == [] and "no frozen manifest" in note
    _setup(zoo_env.root)  # manifest and a report without runs
    failures, note = trace_findings(zoo_env.root, "t", "m", "0.1.0", BENCH)
    assert failures == [] and "no run list" in note
