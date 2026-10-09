"""History import with git filter-repo (feature 005, scripts/import/import_branch.py)."""

import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    shutil.which("git-filter-repo") is None, reason="git-filter-repo missing"
)


def sh(*args, cwd):
    subprocess.run(
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "Ada",
            "GIT_AUTHOR_EMAIL": "ada@example.org",
            "GIT_COMMITTER_NAME": "Ada",
            "GIT_COMMITTER_EMAIL": "ada@example.org",
            "GIT_AUTHOR_DATE": "2026-10-01T10:00:00",
            "GIT_COMMITTER_DATE": "2026-10-01T10:00:00",
            "HOME": str(cwd),
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        },
    )


def source_repo(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    sh("git", "init", "-q", "-b", "feature", cwd=src)
    (src / "docs").mkdir()
    (src / "docs" / "a.md").write_text("doc\n")
    sh("git", "add", "-A", cwd=src)
    sh("git", "commit", "-q", "-m", "add doc", cwd=src)
    (src / "secret.bin").write_text("raw frames\n")
    sh("git", "add", "-A", cwd=src)
    sh("git", "commit", "-q", "-m", "add binary", cwd=src)
    (src / "extra.txt").write_text("x\n")
    sh("git", "add", "-A", cwd=src)
    sh("git", "commit", "-q", "-m", "add extra", cwd=src)
    return src


def run(tmp_path, mapping):
    m = tmp_path / "map.yaml"
    m.write_text(yaml.safe_dump(mapping))
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/import/import_branch.py"),
            "--source",
            str(tmp_path / "src"),
            "--branch",
            "feature",
            "--map",
            str(m),
            "--out",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )


MAP = {
    "renames": [{"from": "docs/", "to": "topics/t/research/"}],
    "strip": [{"glob": "*.bin", "reason": "raw data"}],
}


def test_unmapped_path_fails(tmp_path):
    source_repo(tmp_path)
    res = run(tmp_path, MAP)
    assert res.returncode == 2 and "extra.txt" in res.stderr


def test_import_rewrites_and_strips(tmp_path):
    source_repo(tmp_path)
    res = run(tmp_path, {**MAP, "drop": [{"glob": "extra.txt", "reason": "not needed"}]})
    assert res.returncode == 0, res.stderr
    out = tmp_path / "out"
    names = subprocess.run(
        ["git", "log", "--all", "--format=", "--name-only"], cwd=out, capture_output=True, text=True
    ).stdout.split()
    assert "secret.bin" not in names and "topics/t/research/a.md" in names
    first = subprocess.run(
        ["git", "log", "--reverse", "--format=%an %ad", "--date=short"],
        cwd=out,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]
    assert first == "Ada 2026-10-01"
    rows = list(csv.DictReader((tmp_path / "out.merge-log.csv").open()))
    assert {r["old_path"]: r["status"] for r in rows} == {
        "docs/a.md": "renamed",
        "secret.bin": "strip",
        "extra.txt": "drop",
    }
