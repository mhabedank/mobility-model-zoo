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
