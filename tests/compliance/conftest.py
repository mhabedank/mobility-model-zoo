from pathlib import Path

import pytest
from compliance_helpers import make_register_tree


@pytest.fixture
def register_tree(tmp_path: Path) -> Path:
    """A repository layout with a minimal valid compliance register."""
    return make_register_tree(tmp_path)
