"""Processing and content checks of the import (feature 016, FR-006, FR-009, FR-013; I4, I5).
Needs the `images` extra; the OCR and face models load on first use, so these are slow."""

from __future__ import annotations

import io

import pytest

pytest.importorskip("PIL")
pytestmark = pytest.mark.slow

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from mobility_model_zoo.site import images  # noqa: E402
from mobility_model_zoo.site import images_process as proc  # noqa: E402


def flat_scene(path, text: str | None = None, size=(1200, 800)):
    """A poster-like scene: navy sky band, cream ground, one orange rectangle; optional big text."""
    img = Image.new("RGB", size, (236, 240, 230))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0], size[1] // 2], fill=(17, 24, 70))
    d.rectangle([300, 350, 900, 600], fill=(240, 160, 40))
    if text:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 140)
        except OSError:
            font = ImageFont.load_default(size=140)
        d.text((120, 120), text, fill=(255, 255, 255), font=font)
    img.save(path)
    return path


def test_crop_box_keeps_the_focal_point_and_the_aspect():
    box = proc.crop_box(1344, 768, "16:9", (0.5, 0.5))
    assert box == (0, 6, 1344, 762)  # 1344 px is not exactly 16:9; the crop is centred
    left, top, right, bottom = proc.crop_box(1344, 768, "3:2", (0.9, 0.5))
    assert (bottom - top) == 768 and round((right - left) / (bottom - top), 2) == 1.5
    assert right == 1344  # clamped to the right edge, the focal point stays inside
    left, top, right, bottom = proc.crop_box(1200, 800, "16:9", (0.5, 0.1))
    assert top == 0 and (right - left) == 1200 and round((right - left) / (bottom - top), 2) == 1.78


def test_derivatives_carry_the_marker_and_stay_under_the_caps(tmp_path):
    png = flat_scene(tmp_path / "scene.png")
    ders = proc.derivatives(png, "3:2", (0.5, 0.5), "Qwen/Qwen-Image-2512", "siebdruck")
    assert set(ders) == set(images.WIDTHS)
    for w, data in ders.items():
        assert len(data) <= images.BYTE_CAPS[w]
        assert images.IPTC_MARKER.encode() in data
        with Image.open(io.BytesIO(data)) as im:
            assert im.width == w and im.format == "WEBP"
            assert images.IPTC_MARKER.encode() in (im.info.get("xmp") or b"")


def test_readable_text_is_rejected_and_a_plain_scene_passes(tmp_path):
    clean = proc.text(flat_scene(tmp_path / "clean.png"))
    assert clean["pass"] and clean["tokens"] == []
    lettered = proc.text(flat_scene(tmp_path / "text.png", "ROUTE 400"))
    assert not lettered["pass"]
    assert any("400" in t["text"] or "ROUTE" in t["text"].upper() for t in lettered["tokens"])


def test_face_detector_runs_and_passes_a_scene_without_faces(tmp_path):
    out = proc.faces(flat_scene(tmp_path / "clean.png"))
    assert out["pass"] and out["hits"] == []
    assert proc.tool_versions()["yunet_sha256"] == proc.YUNET_SHA256


def test_detectors_accept_a_webp_and_the_deep_check_falls_back_to_the_derivative(
    site_env, tmp_path, monkeypatch
):
    """Feature 019 (research R1): without a source PNG the deep check runs on the 1600 px file."""
    from test_images_record import make_record
    from test_images_series import write_series

    from mobility_model_zoo.site import images_cli

    png = flat_scene(tmp_path / "scene.png")
    ders = proc.derivatives(png, "3:2", (0.5, 0.5), "Qwen/Qwen-Image-2512", "siebdruck")
    webp = tmp_path / "scene-1600.webp"
    webp.write_bytes(ders[1600])
    assert proc.faces(webp)["pass"] and proc.text(webp)["pass"]
    write_series(site_env.root)
    d = make_record(site_env.root, "pool-a", (), "3:2", "rail", "tram", source_file=False)
    (d / "pool-a-1600.webp").write_bytes(ders[1600])  # a real derivative for the detectors
    rec = {
        "_dir": d,
        "id": "pool-a",
        "source": {},
        "derivatives": {"1600": {"file": "pool-a-1600.webp"}},
    }
    rec["source"] = {"width": 1200, "height": 800}
    src, kind = images_cli._source_for(site_env.reg, rec)
    assert kind == "1600 px derivative at source scale" and src.suffix == ".png"
    with Image.open(src) as scaled:
        assert scaled.width == 1200  # the detectors see the source's pixel size
    cached = site_env.root / images.SOURCES_CACHE / "pool-a.png"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(png.read_bytes())
    assert images_cli._source_for(site_env.reg, rec) == (cached, "cached source")


def test_phash_is_stable_and_separates_scenes(tmp_path):
    a = proc.phash(flat_scene(tmp_path / "a.png"))
    b = proc.phash(flat_scene(tmp_path / "b.png"))
    assert a == b  # the same scene hashes the same
    c = proc.phash(flat_scene(tmp_path / "c.png", "ROUTE 400"))
    assert proc.phash_distance(a, c) > proc.PHASH_MAX_BITS
