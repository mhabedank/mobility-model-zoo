"""The generator's series loading, job plan and manifest shape (features 016 and 019);
rendering needs a GPU."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "scripts" / "imagery" / "gen.py"
SERIES = ROOT / "zoo" / "site" / "images" / "series" / "siebdruck.yaml"


def load_gen():
    spec = importlib.util.spec_from_file_location("gen", GEN)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gen"] = mod
    spec.loader.exec_module(mod)
    return mod


def args(out: Path, **kw) -> argparse.Namespace:
    base = dict(seeds=1, seed_base=0, only="", reserve=False, out=out)
    base.update(kw)
    return argparse.Namespace(**base)


def test_series_file_of_the_repository_loads_and_is_complete():
    gen = load_gen()
    series = gen.load_series(SERIES)
    assert series["name"] == "siebdruck" and "\n" not in series["style"]
    for key in ("draft", "final"):
        m = series["models"][key]
        assert {"id", "pipeline", "licence", "card", "steps"} <= set(m)
        assert m["licence"] in ("Apache-2.0", "MIT")
    subs = gen.subjects(series)
    assert len(subs) >= 100 and len({s["key"] for s in subs}) == len(subs)
    for s in subs:
        assert "orange-yellow" in s["prompt"]  # the accent sits on the vehicle or machine (R13)
        assert s["aspect"] in gen.SIZES


def test_sizes():
    gen = load_gen()
    assert gen.SIZES["16:9"] == (1344, 768) and gen.SIZES["3:2"] == (1200, 800)


def test_seeds_are_stable_and_distinct_between_subjects():
    gen = load_gen()
    a = gen.seed_for("rail/high-speed-viaduct", 0, 0)
    assert a == gen.seed_for("rail/high-speed-viaduct", 0, 0)
    assert gen.seed_for("rail/high-speed-viaduct", 0, 1) == a + 1
    assert gen.seed_for("rail/high-speed-viaduct", 1000, 0) == a + 1000
    series = gen.load_series(SERIES)
    seeds = {gen.seed_for(s["key"], 0, 0) for s in gen.subjects(series)}
    assert len(seeds) == len(gen.subjects(series))


def test_plan_selects_by_theme_subject_reserve_and_next_file(tmp_path):
    gen = load_gen()
    series = {
        "name": "s",
        "style": "style",
        "themes": {
            "rail": [
                {"id": "a", "prompt": "an orange-yellow a", "aspect": "16:9"},
                {"id": "r", "prompt": "an orange-yellow r", "reserve": True},
            ],
            "water": [{"id": "b", "prompt": "an orange-yellow b"}],
        },
    }
    files = [j["file"] for j in gen.plan(series, args(tmp_path, seeds=2))]
    assert len(files) == 4 and all("--r--" not in f for f in files)
    assert files[0].startswith("rail--a--") and files[0].endswith(".png")
    assert [j["key"] for j in gen.plan(series, args(tmp_path, only="water"))] == ["water/b"]
    assert [j["key"] for j in gen.plan(series, args(tmp_path, only="rail/r"))] == ["rail/r"]
    assert len(gen.plan(series, args(tmp_path, reserve=True))) == 3
    (tmp_path / "next.txt").write_text("rail/a\n\nwater/b\n", encoding="utf-8")
    assert [j["key"] for j in gen.plan(series, args(tmp_path))] == ["rail/a", "water/b"]
    assert gen.plan(series, args(tmp_path))[0]["aspect"] == "16:9"


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
