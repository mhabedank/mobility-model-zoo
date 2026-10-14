"""Image records (feature 016, FR-012; check I1): schema, hashes, byte caps, placements."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from site_fixture import MODEL

from mobility_model_zoo.release.registry import dump_yaml, load_yaml
from mobility_model_zoo.site import images

MARKER = images.IPTC_MARKER.encode()


def make_record(root: Path, rid: str = "hero-test", placements=("start-hero",), aspect="16:9") -> Path:
    """A minimal valid record with fake files; the WebPs are tiny bytes that carry the marker."""
    d = root / images.IMAGES_DIR / rid
    d.mkdir(parents=True)
    src = d / f"{rid}.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    ders = {}
    for w in images.WIDTHS:
        f = d / f"{rid}-{w}.webp"
        data = b"RIFF" + b"\0" * 8 + b"WEBPVP8X" + MARKER + bytes([w % 251])
        f.write_bytes(data)
        ders[str(w)] = {"file": f.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    rec = {
        "id": rid,
        "series": "siebdruck",
        "generation": {
            "model": "Qwen/Qwen-Image-2512",
            "revision": "a" * 40,
            "model_licence": "Apache-2.0",
            "model_card": "https://huggingface.co/Qwen/Qwen-Image-2512",
            "pipeline": "QwenImagePipeline",
            "prompt": "an orange-yellow tram, style text",
            "negative_prompt": "text",
            "seed": 1021,
            "steps": 50,
            "guidance": 4.0,
            "width": 1344,
            "height": 768,
            "generated": "2026-10-14",
            "hardware": "dgx-spark",
            "generator": {"commit": "unversioned", "image_digest": "sha256:" + "b" * 64},
        },
        "licence": "CC0-1.0",
        "placements": list(placements),
        "scene": "A tram leaving a stop at sunrise on a wide boulevard",
        "alt": "An orange tram glides out of a stop on a wide boulevard at sunrise (AI-generated image)",
        "focal_point": [0.5, 0.55],
        "aspect": aspect,
        "source": {"file": src.name, "width": 1344, "height": 768, "sha256": images.sha256(src)},
        "derivatives": ders,
        "checks": {
            "tools": {},
            "ran": "2026-10-14T10:00:00+00:00",
            "faces": "pass",
            "text": "pass",
            "bytes": "pass",
        },
    }
    (d / "image.yaml").write_text(dump_yaml(rec), encoding="utf-8")
    return d


def test_no_records_is_fine(site_env):
    assert images.load_records(site_env.reg) == ([], [])


def test_a_valid_record_loads(site_env):
    make_record(site_env.root)
    records, findings = images.load_records(site_env.reg)
    assert findings == [] and [r["id"] for r in records] == ["hero-test"]


@pytest.mark.parametrize(
    ("edit", "word"),
    [
        (lambda r: r.pop("scene"), "scene"),
        (lambda r: r["generation"].pop("seed"), "seed"),
        (lambda r: r.update(alt="no suffix here at all, forty characters long yes"), "alt"),
        (lambda r: r.update(licence="MIT"), "licence"),
        (lambda r: r["generation"].update(model_licence="CC-BY-NC-4.0"), "model_licence"),
        (lambda r: r["source"].update(sha256="0" * 64), "sha256"),
        (lambda r: r["derivatives"]["960"].update(bytes=1), "960"),
    ],
)
def test_broken_records_are_i1(site_env, edit, word):
    d = make_record(site_env.root)
    rec = load_yaml(d / "image.yaml")
    edit(rec)
    (d / "image.yaml").write_text(dump_yaml(rec), encoding="utf-8")
    _, findings = images.load_records(site_env.reg)
    assert findings and all(f.startswith("I1 hero-test") for f in findings)
    assert any(word in f for f in findings), findings


def test_byte_cap_is_i1(site_env):
    d = make_record(site_env.root)
    big = d / "hero-test-480.webp"
    data = b"RIFF" + MARKER + b"\0" * 70_000
    big.write_bytes(data)
    rec = load_yaml(d / "image.yaml")
    rec["derivatives"]["480"].update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (d / "image.yaml").write_text(dump_yaml(rec), encoding="utf-8")
    _, findings = images.load_records(site_env.reg)
    assert any("more than 60000" in f for f in findings), findings


def test_duplicate_and_unknown_placements_are_i1(site_env):
    make_record(site_env.root, "a", ("topic:productdev",), "3:2")
    make_record(site_env.root, "b", ("topic:productdev", "topic:nowhere", "model:ghost"), "3:2")
    _, findings = images.load_records(site_env.reg)
    assert any("also used by a" in f for f in findings)
    assert any("unknown topic nowhere" in f for f in findings)
    assert any("model ghost is not shown" in f for f in findings)
    assert not any("I1 a:" in f for f in findings)


def test_set_digest_and_placement_resolution(site_env):
    make_record(site_env.root, "hero", ("start-hero",))
    make_record(site_env.root, "pd", ("topic:productdev",), "3:2")
    records, _ = images.load_records(site_env.reg)
    digest = images.set_digest(records)
    assert [i["id"] for i in digest["images"]] == ["hero", "pd"] and len(digest["digest"]) == 64
    placed = images.by_placement(records)
    assert images.resolve(placed, "start-hero")[0]["id"] == "hero"
    rec, warning = images.resolve(placed, f"model:{MODEL}", "productdev")
    assert rec["id"] == "pd" and "using topic:productdev" in warning
    rec, warning = images.resolve(placed, "model:other", "security")
    assert rec is None and warning == "no image for model:other, motif only"
    assert images.resolve(placed, "topic:security") == (None, "no image for topic:security")
