"""Fixtures for the release tool: a temporary repository with a valid sandbox registry, a git
history that contains the recipe, and a FakeHub whose staging repo holds the staged files."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakehub import FakeHub, copy_tree  # noqa: E402

from mobility_model_zoo.release.registry import Registry  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MODEL = "sandbox-pipeline-tiny"
VERSION = "0.1.0"
STAGED = {"config.json": b'{"seed": 0}\n', "model.safetensors": b"fake-weights-v1\n"}


@dataclass
class ZooEnv:
    root: Path
    reg: Registry
    hub: FakeHub
    model: str = MODEL
    version: str = VERSION

    def record(self, version: str = VERSION) -> dict:
        return self.reg.record_raw(self.model, version)

    def set_record(self, data: dict, version: str = VERSION) -> None:
        self.reg.write_record(self.model, version, data)


def git(root: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    return out.stdout.strip()


def make_env(root: Path) -> ZooEnv:
    copy_tree(FIXTURES / "registry", root)
    for rel in ("src/mobility_model_zoo/sandbox/build_test_model.py", "docs/adding-a-model.md"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("# recipe\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "-c", "user.email=t@example.org", "-c", "user.name=t", "add", "-A")
    git(root, "-c", "user.email=t@example.org", "-c", "user.name=t", "commit", "-qm", "recipe")
    head = git(root, "rev-parse", "HEAD")

    hub = FakeHub()
    reg = Registry(root)
    model = reg.model_raw(MODEL)
    revision = hub.seed(model["repos"]["staging"], STAGED, private=True)
    record = reg.record_raw(MODEL, VERSION)
    record["files"] = [
        {"path": p, "sha256": hashlib.sha256(b).hexdigest(), "size_bytes": len(b)}
        for p, b in sorted(STAGED.items())
    ]
    record["staging"]["revision"] = revision
    record["recipe"]["git_commit"] = head
    reg.write_record(MODEL, VERSION, record)
    return ZooEnv(root=root, reg=reg, hub=hub)


@pytest.fixture
def zoo_env(tmp_path: Path) -> ZooEnv:
    return make_env(tmp_path)


class FakeRunner:
    """Stands in for the clean-environment runner: returns a deterministic output per code."""

    def __init__(self, returncode: int = 0):
        self.returncode = returncode
        self.calls: list[str] = []

    def run(self, code: str) -> tuple[int, str, str]:
        self.calls.append(code)
        if self.returncode:
            return self.returncode, "", "Traceback: boom"
        digest = hashlib.sha256(code.encode()).hexdigest()[:8]
        return 0, f'{{"items": [], "run": "{digest}"}}\n', ""


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()


def lines() -> tuple[list[str], callable]:
    out: list[str] = []
    return out, out.append
