"""Gate check: the runs behind a release used the frozen benchmark and the pre-registered criteria
(feature 021, research R22; spec US1 scenario 4).

For a release whose benchmark has a frozen manifest (`topics/<topic>/benchmarks/<benchmark>/
manifest.json`) and an evaluation report with a run list (`topics/<topic>/reports/<model>/<version>/
evaluation.json`, written by the task tool), every run must name the SHA-256 of that manifest, and
every criteria commit must be in the repository history and older than the earliest run. Releases
from before feature 021 (no manifest, no report or no run list) skip the check with a note.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path


def _iso(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def trace_findings(
    root: Path, topic: str, model: str, version: str, benchmark: str
) -> tuple[list[str], str]:
    """(failures, note) of the benchmark trace."""
    manifest = root / "topics" / topic / "benchmarks" / benchmark / "manifest.json"
    report = root / "topics" / topic / "reports" / model / version / "evaluation.json"
    if not manifest.exists():
        return [], f"benchmark trace skipped: no frozen manifest for {benchmark}"
    if not report.exists():
        return [], "benchmark trace skipped: no evaluation report with runs"
    runs = json.loads(report.read_text(encoding="utf-8")).get("runs") or []
    if not runs:
        return [], "benchmark trace skipped: the evaluation report has no run list"
    sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    failures = [
        f"run of seed {r.get('seed')} names manifest {str(r.get('manifest_sha256'))[:12]}…, "
        f"not the frozen {benchmark} ({sha[:12]}…)"
        for r in runs
        if r.get("manifest_sha256") != sha
    ]
    earliest = min(_iso(r["trained_at"]) for r in runs)
    for commit in sorted({r.get("criteria_commit", "") for r in runs}):
        if not commit or _git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode != 0:
            failures.append(f"criteria commit {commit[:12] or '(none)'} is not in the history")
            continue
        committed = _iso(_git(root, "show", "-s", "--format=%cI", commit).stdout.strip())
        if committed >= earliest:
            failures.append(
                f"criteria commit {commit[:12]} ({committed:%Y-%m-%d %H:%M}) is not older than the "
                f"first run ({earliest:%Y-%m-%d %H:%M}); pre-registration must come first"
            )
    if failures:
        return failures, ""
    return [], (
        f"benchmark trace: {len(runs)} runs on frozen {benchmark}, criteria committed before the "
        "first run"
    )
