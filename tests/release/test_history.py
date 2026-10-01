"""`zoo history-check` finds data files anywhere in the history, also after deletion (T061)."""

from __future__ import annotations

import pytest
from conftest import git

from mobility_model_zoo.release.history import forbidden, path_findings


@pytest.mark.parametrize(
    "path",
    [
        "data/chunks/a.json",
        "spike/data/x.txt",
        ".env",
        "out/labels.jsonl",
        "m/model.safetensors",
        "a.pt",
    ],
)
def test_forbidden_paths(path):
    assert forbidden(path)


@pytest.mark.parametrize(
    "path",
    ["src/x.py", ".env.example", "tests/fixtures/mini-corpus/store/snapshots/index.jsonl", "README.md"],
)
def test_allowed_paths(path):
    assert forbidden(path) is None


def test_deleted_data_file_is_still_found(tmp_path):
    def commit(message):
        git(tmp_path, "-c", "user.email=t@example.org", "-c", "user.name=t", "add", "-A")
        git(tmp_path, "-c", "user.email=t@example.org", "-c", "user.name=t", "commit", "-qm", message)

    git(tmp_path, "init", "-q")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "raw.txt").write_text("scraped text")
    commit("oops")
    (tmp_path / "data" / "raw.txt").unlink()
    (tmp_path / "ok.txt").write_text("fine")
    commit("remove")
    findings = path_findings(tmp_path)
    assert len(findings) == 1 and findings[0].startswith("data/raw.txt")
