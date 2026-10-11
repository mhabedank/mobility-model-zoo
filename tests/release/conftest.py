"""Fixtures for the release tool: a temporary repository with a valid sandbox registry, a git
history that contains the recipe, and a FakeHub whose staging repo holds the staged files."""

from __future__ import annotations

import hashlib
import re
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


def make_mcu_env(root: Path) -> ZooEnv:
    """The sandbox registry with the mcu fixture `edge-fixture-tiny` staged (feature 005 T055)."""
    from edge_fixture import NAME, npz_bytes, tiny_model, write_examples

    env = make_env(root)
    model = tiny_model()
    write_examples(env.reg.model_dir(NAME), model)
    staged = {"model.npz": npz_bytes(model)}
    revision = env.hub.seed(env.reg.model_raw(NAME)["repos"]["staging"], staged, private=True)
    record = env.reg.record_raw(NAME, VERSION)
    record["files"] = [
        {"path": p, "sha256": hashlib.sha256(b).hexdigest(), "size_bytes": len(b)}
        for p, b in sorted(staged.items())
    ]
    record["staging"]["revision"] = revision
    record["recipe"]["git_commit"] = git(root, "rev-parse", "HEAD")
    env.reg.write_record(NAME, VERSION, record)
    env.model = NAME
    env.qmodel = model
    return env


@pytest.fixture
def mcu_env(tmp_path: Path) -> ZooEnv:
    return make_mcu_env(tmp_path)


class FakeRunner:
    """Stands in for the clean-environment runner: returns a deterministic output per code."""

    def __init__(self, returncode: int = 0):
        self.returncode = returncode
        self.calls: list[str] = []

    def run(self, code: str) -> tuple[int, str, str]:
        self.calls.append(code)
        if self.returncode:
            return self.returncode, "", "Traceback: boom"
        stable = re.sub(r"[0-9a-f]{40}", "<sha>", code)  # independent of fake commit ids
        digest = hashlib.sha256(stable.encode()).hexdigest()[:8]
        return 0, f'{{"items": [], "run": "{digest}"}}\n', ""


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()


def lines() -> tuple[list[str], callable]:
    out: list[str] = []
    return out, out.append


def make_mcu_forest_env(root: Path) -> ZooEnv:
    """The sandbox registry with the emlearn fixture `edge-fixture-forest` staged (feature 007)."""
    import shutil

    from edge_fixture_forest import NAME, staged_files, write_examples

    from mobility_model_zoo.edge.paths import REPO_ROOT
    from mobility_model_zoo.security.can_ids.scorer import SOURCES

    env = make_env(root)
    for path in SOURCES.values():  # the gate compares staged sources with the recipe commit
        dest = root / path.relative_to(REPO_ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, dest)
    files = staged_files()
    write_examples(env.reg.model_dir(NAME), files)
    git(root, "-c", "user.email=t@example.org", "-c", "user.name=t", "add", "-A")
    git(root, "-c", "user.email=t@example.org", "-c", "user.name=t", "commit", "-qm", "forest sources")
    revision = env.hub.seed(env.reg.model_raw(NAME)["repos"]["staging"], files, private=True)
    record = env.reg.record_raw(NAME, VERSION)
    record["files"] = [
        {"path": p, "sha256": hashlib.sha256(b).hexdigest(), "size_bytes": len(b)}
        for p, b in sorted(files.items())
    ]
    record["staging"]["revision"] = revision
    record["recipe"]["git_commit"] = git(root, "rev-parse", "HEAD")
    env.reg.write_record(NAME, VERSION, record)
    env.model = NAME
    env.files = files
    return env


@pytest.fixture
def mcu_forest_env(tmp_path: Path) -> ZooEnv:
    import shutil

    pytest.importorskip("emlearn")
    pytest.importorskip("sklearn")
    if not (shutil.which("cc") or shutil.which("gcc")):
        pytest.skip("needs a C compiler")
    return make_mcu_forest_env(tmp_path)
