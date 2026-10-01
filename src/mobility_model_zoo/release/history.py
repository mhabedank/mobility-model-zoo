"""`zoo history-check`: the whole git history holds no data files, model files or secrets (FR-003c).

Run once before the repository becomes public (feature 004). Path rules find data and model files;
`gitleaks` finds secrets. Synthetic test fixtures under `tests/fixtures/` are allowed.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from mobility_model_zoo.release.errors import GateFailed, UsageError

ALLOWED_PREFIXES = ("tests/fixtures/",)
FORBIDDEN_SUFFIXES = {".jsonl", ".safetensors", ".pt", ".pth", ".bin", ".gguf", ".onnx", ".parquet"}
FORBIDDEN_DIRS = {"data", "snapshots", "raw_responses"}


def forbidden(path: str) -> str | None:
    if path.startswith(ALLOWED_PREFIXES):
        return None
    p = PurePosixPath(path)
    if p.parts and p.parts[0] in FORBIDDEN_DIRS or any(part in FORBIDDEN_DIRS for part in p.parts[:-1]):
        return "data directory"
    if p.name == ".env" or p.name.startswith(".env.") and p.name != ".env.example":
        return "environment file"
    if p.suffix in FORBIDDEN_SUFFIXES:
        return f"{p.suffix} file"
    return None


def path_findings(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "log", "--all", "--format=@%H", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    findings, commit, seen = [], "", set()
    for line in out.splitlines():
        if line.startswith("@"):
            commit = line[1:]
        elif line and line not in seen and (why := forbidden(line)):
            seen.add(line)
            findings.append(f"{line} ({why}), first seen in commit {commit[:12]}")
    return findings


def secret_findings(root: Path) -> list[str]:
    if shutil.which("gitleaks") is None:
        raise UsageError("gitleaks is not installed; the secret scan cannot run")
    done = subprocess.run(
        ["gitleaks", "git", "--no-banner", "--redact", "--log-opts=--all", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode == 0:
        return []
    lines = [
        ln for ln in (done.stdout + done.stderr).splitlines() if "leaks found" in ln or "Commit:" in ln
    ]
    return ["gitleaks: " + (" | ".join(lines) or f"exit {done.returncode}")]


def run(root: Path, say: Callable[[str], None]) -> None:
    findings = path_findings(root)
    say(f"paths: {len(findings)} finding(s)")
    findings += secret_findings(root)
    if findings:
        raise GateFailed(findings)
    say("history-check: no data files, model files or secrets in any commit")
