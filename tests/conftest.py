import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CONTRACTS = REPO / "specs" / "001-jtbd-extraction-pilot" / "contracts"
FIXTURE = REPO / "tests" / "fixtures" / "mini-corpus"


@pytest.fixture
def contracts_dir() -> Path:
    return CONTRACTS


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURE

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session")
def tiny_span_model(tmp_path_factory):
    """Factory: a tiny random span model directory per tuple of produced dimensions (cached)."""
    from span_helpers import build_tiny_model

    cache: dict = {}

    def make(dimensions=("actor_type", "evidence_type", "evidence_scope")) -> Path:
        key = tuple(dimensions)
        if key not in cache:
            name = "tiny-" + ("-".join(key) or "none")
            cache[key] = build_tiny_model(tmp_path_factory.mktemp(name), key)
        return cache[key]

    return make


@pytest.fixture
def register_tree(tmp_path):
    """A repository layout with a minimal valid compliance register (feature 006)."""
    from compliance_helpers import make_register_tree

    return make_register_tree(tmp_path)


# ---- feature 009: synthetic fixture catalogs (copies, so tests may write) ----------------------

CATALOG_FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def catalog_dir(tmp_path: Path, monkeypatch) -> Path:
    """A writable copy of tests/fixtures/catalog."""
    import shutil

    monkeypatch.delenv("MMZ_CATALOG", raising=False)
    target = tmp_path / "catalog"
    shutil.copytree(CATALOG_FIXTURES / "catalog", target)
    return target


@pytest.fixture
def invalid_dir(tmp_path: Path, monkeypatch) -> Path:
    """A writable copy of tests/fixtures/catalog-invalid."""
    import shutil

    monkeypatch.delenv("MMZ_CATALOG", raising=False)
    target = tmp_path / "catalog-invalid"
    shutil.copytree(CATALOG_FIXTURES / "catalog-invalid", target)
    return target


@pytest.fixture(autouse=True)
def _numpy_error_state():
    """Some libraries (emlearn) change numpy's global error state at import; isolate tests."""
    import numpy as np

    state = np.geterr()
    yield
    np.seterr(**state)


@pytest.fixture(autouse=True)
def _no_tracking_from_the_developer(monkeypatch):
    """Tests never log to a developer's tracking server or write offline logs, whatever the shell
    or a `.env` says (feature 017); subprocesses inherit the switch. Tests that track set it up."""
    for key in ("MLFLOW_TRACKING_URI", "MMZ_TRACKING_OFFLINE"):
        monkeypatch.setenv(key, "")  # registers the original value, so teardown restores it
        monkeypatch.delenv(key)
    monkeypatch.setenv("MMZ_TRACKING_IGNORE_DOTENV", "1")
