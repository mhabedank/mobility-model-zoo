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
