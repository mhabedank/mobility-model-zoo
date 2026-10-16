"""The style check I6 and the duplicate helpers of I7 (feature 019, FR-005, FR-006).
Needs the `images` extra."""

from __future__ import annotations

import pytest

pytest.importorskip("cv2")
pytestmark = pytest.mark.slow

from PIL import Image, ImageDraw  # noqa: E402

from mobility_model_zoo.site import images_process as proc  # noqa: E402

NAVY, MINT, CREAM, ACCENT = (17, 24, 70), (207, 245, 232), (243, 235, 216), (240, 160, 40)
PALETTE = {
    "anchors": {
        "navy": [12, 12, -32],
        "mint": [94, -14, 2],
        "cream": [93, 1, 11],
        "accent": [72, 22, 68],
    },
    "tolerance_de": 18,
    "other_max": 0.12,
    "accent_min": 0.015,
    "accent_max": 0.30,
    "largest_min": 0.50,
    "top_max": 0.15,
}


def scene(path, accent_boxes=((300, 350, 900, 600),), sky=MINT, ground=CREAM, size=(1200, 800)):
    img = Image.new("RGB", size, ground)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0], size[1] // 2], fill=sky)
    d.rectangle([0, size[1] - 120, size[0], size[1]], fill=NAVY)
    for box in accent_boxes:
        d.rectangle(list(box), fill=ACCENT)
    img.save(path)
    return path


def test_anchors_are_close_to_the_palette_colours(tmp_path):
    """The placeholder anchors in the series file sit near the sRGB colours used here."""
    anchors = proc.measure_anchors([scene(tmp_path / "a.png", ((200, 300, 1000, 650),))])
    assert "accent" in anchors and len(anchors) == proc.PALETTE_K
    assert anchors["tone1"][0] < 30 and anchors["accent"][2] > 40
    assert anchors["tone1"][0] < anchors["tone2"][0]


def test_in_palette_scene_passes_and_reports_the_centroid(tmp_path):
    out = proc.style(scene(tmp_path / "ok.png"), PALETTE)
    assert out["pass"], out["reasons"]
    m = out["measures"]
    assert m["other_share"] < 0.05 and 0.1 < m["accent_share"] < 0.2
    assert m["accent_largest_share"] > 0.95
    cx, cy = m["accent_centroid"]
    assert 0.45 < cx < 0.55 and 0.55 < cy < 0.65  # inside the orange rectangle


def test_orange_sky_fails_top(tmp_path):
    out = proc.style(scene(tmp_path / "sky.png", accent_boxes=(), sky=ACCENT), PALETTE)
    assert not out["pass"] and any(
        r.startswith("accent_max") or r.startswith("top") for r in out["reasons"]
    )
    # a thin accent band only in the sky, with the machine below: top rule
    out = proc.style(scene(tmp_path / "band.png", ((0, 0, 1200, 60), (500, 500, 600, 560))), PALETTE)
    assert not out["pass"] and any(
        r.startswith("top") or r.startswith("largest") for r in out["reasons"]
    )


def test_scattered_accent_fails_largest(tmp_path):
    boxes = ((100, 450, 300, 600), (500, 450, 700, 600), (900, 450, 1100, 600))
    out = proc.style(scene(tmp_path / "scatter.png", boxes), PALETTE)
    assert not out["pass"] and any(r.startswith("largest") for r in out["reasons"])


def test_off_palette_scene_fails_other(tmp_path):
    out = proc.style(scene(tmp_path / "grey.png", sky=(120, 140, 120), ground=(90, 110, 90)), PALETTE)
    assert not out["pass"] and any(r.startswith("other") for r in out["reasons"])


def test_no_accent_fails_accent_min(tmp_path):
    out = proc.style(scene(tmp_path / "none.png", accent_boxes=()), PALETTE)
    assert not out["pass"] and any(r.startswith("accent_min") for r in out["reasons"])


def test_phash_hex_and_duplicates(tmp_path):
    a = proc.phash_hex(scene(tmp_path / "a.png"))
    assert len(a) == 16 and int(a, 16) >= 0
    assert proc.duplicate_of(a, {"x": a}, 10) == ("x", 0)
    far = f"{int(a, 16) ^ ((1 << 20) - 1):016x}"  # 20 bits flipped
    assert proc.duplicate_of(a, {"x": far}, 10) is None
    b = proc.phash_hex(scene(tmp_path / "b.png", ((100, 100, 400, 300),)))
    assert proc.duplicate_of(a, {"b": b}, 4) is None
