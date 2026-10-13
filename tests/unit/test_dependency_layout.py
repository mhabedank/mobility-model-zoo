"""Dependency layout and install lines (feature 013, contracts/dependency-layout.md).

The base install is what every model shares; a model's card names the extra its kind needs, and that
extra must hold what the card's snippet imports. Checked here without installing anything.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
BASE = PYPROJECT["project"]["dependencies"]
EXTRAS = PYPROJECT["project"]["optional-dependencies"]
TEXT_STACK = {"torch", "transformers", "safetensors", "sentencepiece"}
MODELS = sorted((ROOT / "zoo" / "models").glob("*/model.yaml"))


def names(requirements: list[str]) -> set[str]:
    return {re.split(r"[\s\[<>=!~;@]", r, maxsplit=1)[0].lower().replace("_", "-") for r in requirements}


def test_base_install_is_small():
    assert names(BASE) == {"huggingface-hub", "numpy"}


def test_text_extra_holds_the_text_stack():
    assert names(EXTRAS["text"]) == TEXT_STACK


def test_edge_extra_holds_what_the_forest_snippet_imports():
    assert {"numpy", "scikit-learn", "joblib"} <= names(EXTRAS["edge"])
    assert not names(EXTRAS["edge"]) & TEXT_STACK, "an edge install must not pull the text stack"
    assert "pandas" not in names(EXTRAS["edge"]), "pandas is not on the inference path"


def test_jtbd_extra_includes_the_text_extra():
    assert "mobility-model-zoo[text]" in EXTRAS["jtbd"]


def test_cluster_extra_includes_the_text_extra():
    assert "mobility-model-zoo[text]" in EXTRAS["cluster"]


@pytest.mark.parametrize("path", MODELS, ids=lambda p: p.parent.name)
def test_install_line_names_the_extra_of_the_runtime(path):
    """mcu models name `edge`; python models name `text` or one extra that includes it (a task
    stage such as `cluster` needs more than the text stack)."""
    model = yaml.safe_load(path.read_text(encoding="utf-8"))
    extras = re.search(r"mobility-model-zoo\[([^\]]+)\]", model["card"]["install"])
    assert extras is not None, model["card"]["install"]
    named = extras.group(1)
    if model.get("runtime") == "mcu":
        assert named == "edge", model["card"]["install"]
    else:
        assert named == "text" or "mobility-model-zoo[text]" in EXTRAS.get(named, []), named
