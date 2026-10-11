"""The clean-environment runner installs what the card's install line installs (feature 013, R4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mobility_model_zoo.release.usage import VenvRunner, install_spec

ROOT = Path(__file__).resolve().parents[2]
EDGE_LINE = 'pip install "mobility-model-zoo[edge] @ git+https://github.com/x/y@picket-forest/v0.2.1"'
TEXT_LINE = 'pip install "mobility-model-zoo[text] @ git+https://github.com/x/y@scout-large/v0.1.3"'


def test_install_spec_keeps_the_extras_of_the_install_line(tmp_path):
    assert install_spec(tmp_path, EDGE_LINE) == f"{tmp_path}[edge]"
    assert install_spec(tmp_path, TEXT_LINE) == f"{tmp_path}[text]"
    assert install_spec(tmp_path, "pip install mobility-model-zoo[edge, release]") == (
        f"{tmp_path}[edge,release]"
    )


def test_install_spec_without_extras_is_the_bare_checkout(tmp_path):
    assert install_spec(tmp_path, 'pip install "mobility-model-zoo @ git+https://x/y@t"') == str(
        tmp_path
    )
    assert install_spec(tmp_path, "") == str(tmp_path)


@pytest.mark.slow
def test_fresh_env_rejects_an_import_outside_the_extra():
    """Needs uv and network: a real environment built from the edge install line has no torch."""
    runner = VenvRunner(ROOT, None, EDGE_LINE)
    rc, _, err = runner.run("import torch")
    assert rc != 0 and "torch" in err
    rc, out, err = runner.run(
        "from mobility_model_zoo.security.can_ids import picket_forest as pf\nprint(pf.FORMAT)"
    )
    assert rc == 0, err
    assert out.strip() == "picket-forest-v2"
