"""The generator's series loading and manifest shape (feature 016); rendering needs a GPU."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "scripts" / "imagery" / "gen.py"


def load_gen():
    spec = importlib.util.spec_from_file_location("gen", GEN)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gen"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_series_file_of_the_repository_loads_and_is_complete():
    gen = load_gen()
    series = gen.load_series(ROOT / "zoo" / "site" / "images" / "series" / "siebdruck.yaml")
    assert series["name"] == "siebdruck" and "\n" not in series["style"]
    for key in ("draft", "final"):
        m = series["models"][key]
        assert {"id", "pipeline", "licence", "card", "steps"} <= set(m)
        assert m["licence"] in ("Apache-2.0", "MIT")
    assert "start-hero" in series["subjects"] and all(series["subjects"].values())
    for subjects in series["subjects"].values():
        for s in subjects:
            assert "orange-yellow" in s  # the accent sits on the vehicle or machine (research R13)


def test_aspect_and_sizes():
    gen = load_gen()
    assert gen.aspect_of("start-hero") == "16:9" and gen.aspect_of("topic-security") == "3:2"
    assert gen.SIZES["16:9"] == (1344, 768) and gen.SIZES["3:2"] == (1200, 800)


def test_generator_identity_comes_from_the_environment(monkeypatch):
    gen = load_gen()
    monkeypatch.setenv("ZOO_GEN_COMMIT", "abc1234")
    monkeypatch.setenv("ZOO_GEN_IMAGE", "sha256:" + "0" * 64)
    ident = gen.generator_identity()
    assert ident["commit"] == "abc1234" and ident["image_digest"].startswith("sha256:")
    assert len(ident["script_sha256"]) == 64


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="rendering needs torch and a GPU")
def test_render_smoke():  # pragma: no cover - only on the GPU machine
    pytest.skip("rendering is exercised manually on the Spark (scripts/imagery/README.md)")
