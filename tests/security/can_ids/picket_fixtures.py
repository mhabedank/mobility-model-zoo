"""Shared helpers of the picket-forest reference tests (feature 013).

Unique module name on purpose: pytest imports sibling helpers by bare name, and two `conftest`
or `helpers` modules in one session would shadow each other.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPO_ROOT / "zoo" / "models" / "picket-forest" / "examples"
RELEASE_REPO = "mobility-model-zoo/picket-forest"
RELEASE_REVISION = "v0.2.0"  # the weights are identical in every later patch release

_ENTRY = re.compile(r"\{0x([0-9A-Fa-f]+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u\}")
_BUS_RATE = re.compile(r"PICKET_FOREST_BUS_RATE\s*\(([^)]+)\)")


def example_paths() -> list[Path]:
    """The example captures of the registry, in card order."""
    return sorted(EXAMPLES_DIR.glob("*.json"))


def load_release_model() -> dict:
    """`model.joblib` of the published release, from the Hub cache; skips without network."""
    import joblib

    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(RELEASE_REPO, "model.joblib", revision=RELEASE_REVISION)
    except Exception as e:  # noqa: BLE001 - any Hub or network failure means "cannot test here"
        pytest.skip(f"released model not available: {type(e).__name__}: {e}")
    return joblib.load(path)


def header_table(path: Path) -> list[tuple[int, int, int, int, int]]:
    """Rows (id, period_us, window_us, max_count, dlc) of a `picket_forest_table.h`."""
    text = Path(path).read_text(encoding="utf-8")
    return [
        (int(m.group(1), 16), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))
        for m in _ENTRY.finditer(text)
    ]


def header_bus_rate(path: Path) -> float:
    """`PICKET_FOREST_BUS_RATE` of a table header as the float32 value it encodes."""
    import numpy as np

    m = _BUS_RATE.search(Path(path).read_text(encoding="utf-8"))
    if m is None:
        raise ValueError(f"{path}: no PICKET_FOREST_BUS_RATE")
    return float(np.float32(m.group(1).rstrip("fF")))
