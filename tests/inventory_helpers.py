"""Copies of the inventory fixtures (tests/fixtures/inventory) for the overview tests (feature 017)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "inventory"


def fixture_repo(tmp_path: Path) -> tuple[Path, Path]:
    """(repository root, data root) outside any git repository."""
    root = tmp_path / "repo"
    data = tmp_path / "data"
    shutil.copytree(FIXTURE / "repo", root)
    shutil.copytree(FIXTURE / "data", data)
    return root, data


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout


def init_git(root: Path) -> None:
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.org")
    git(root, "config", "user.name", "test")
    git(root, "config", "commit.gpgsign", "false")


def commit(root: Path, message: str, date: str) -> str:
    git(root, "add", "-A")
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", message],
        check=True,
        env={
            "GIT_AUTHOR_DATE": f"{date}T12:00:00",
            "GIT_COMMITTER_DATE": f"{date}T12:00:00",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(root),
        },
    )
    return git(root, "rev-parse", "HEAD").strip()
