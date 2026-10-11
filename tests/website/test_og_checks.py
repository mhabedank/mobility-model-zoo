"""Checks O1, O2, O4, O5 and the P1/P3 cover of card pages, with injected faults (feature 012).

The site is built without a browser; images are written as minimal PNGs of the right header."""

from __future__ import annotations

import json
import struct
import zlib

import pytest
from site_fixture import MODEL

from mobility_model_zoo.site import check, context, og


def png(width: int, height: int, pad: int = 0) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    body = chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\0")) + chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + body + b"\0" * pad


@pytest.fixture
def site(built):
    """A built site whose cards have files and a clean layout, so every O check passes."""
    data = json.loads((built.out / og.MANIFEST).read_text(encoding="utf-8"))
    for card in data["cards"]:
        (built.out / card["file"]).parent.mkdir(parents=True, exist_ok=True)
        (built.out / card["file"]).write_bytes(png(og.WIDTH, og.HEIGHT))
        card["layout"] = {
            "title_px": 76,
            "line_lines": 1,
            "overflow": [],
            "boxes": {
                "mark": [572, 100, 56, 56],
                "title": [285, 250, 630, 84],
                "line": [200, 360, 800, 44],
            },
        }
    (built.out / og.MANIFEST).write_text(json.dumps(data), encoding="utf-8")
    return built


def run(env) -> list[tuple[str, str, str]]:
    site_cfg = context.load_site_config(env.reg)
    found = []
    found += check.check_og_files(site_cfg, env.out)
    found += check.check_og_layout(env.out)
    found += check.check_og_parity(env.reg, env.out)
    found += check.check_og_hash(env.reg, env.out)
    return [tuple(f) for f in found]


def manifest_edit(env, fn) -> None:
    path = env.out / og.MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def model_card(env) -> dict:
    data = json.loads((env.out / og.MANIFEST).read_text(encoding="utf-8"))
    return next(c for c in data["cards"] if c["kind"] == "model")


def ids(found, page=None) -> set[str]:
    return {f[0] for f in found if page is None or f[1] == page}


def test_clean_site_passes(site):
    assert run(site) == []


def test_build_without_images_fails_o1(built):
    assert "O1" in ids(run(built))


def test_missing_twitter_card(site):
    page = site.out / "models" / MODEL / "index.html"
    html = page.read_text(encoding="utf-8")
    page.write_text(
        html.replace('<meta name="twitter:card" content="summary_large_image">', ""), encoding="utf-8"
    )
    assert ("O1", f"models/{MODEL}/", "no twitter:card tag") in run(site)


@pytest.mark.parametrize(
    ("data", "detail"),
    [
        (png(1200, 600), "is 1200 x 600, not 1200 x 630"),
        (png(1200, 630, pad=og.MAX_BYTES), "bytes, more than"),
        (b"GIF89a" + b"\0" * 30, "is not a PNG"),
    ],
    ids=["size", "bytes", "format"],
)
def test_wrong_image_file(site, data, detail):
    (site.out / model_card(site)["file"]).write_bytes(data)
    assert any(f[0] == "O1" and detail in f[2] for f in run(site))


def test_relative_og_image(site):
    page = site.out / "models" / MODEL / "index.html"
    card = model_card(site)
    html = page.read_text(encoding="utf-8").replace(
        f'property="og:image" content="https://mhabedank.github.io/mobility-model-zoo/{card["file"]}"',
        f'property="og:image" content="{card["file"]}"',
    )
    page.write_text(html, encoding="utf-8")
    assert any(f[0] == "O1" and "og:image is" in f[2] for f in run(site))


def test_layout_overflow_and_safe_square(site):
    def fault(data):
        card = next(c for c in data["cards"] if c["kind"] == "model")
        card["layout"]["overflow"] = ["line"]
        card["layout"]["boxes"]["title"] = [200, 250, 630, 84]

    manifest_edit(site, fault)
    found = [f for f in run(site) if f[0] == "O2"]
    assert any("line overflows" in f[2] for f in found)
    assert any("title lies outside the centre square" in f[2] for f in found)


def test_parity_line_alt_and_labels(site):
    def fault(data):
        card = next(c for c in data["cards"] if c["kind"] == "model")
        card["line"] = "Something else."
        card["labels"] = []

    manifest_edit(site, fault)
    details = [f[2] for f in run(site) if f[0] == "O4"]
    assert any(d.startswith("line is 'Something else.'") for d in details)
    assert any(d.startswith("labels is []") for d in details)

    page = site.out / "models" / MODEL / "index.html"
    html = page.read_text(encoding="utf-8")
    page.write_text(
        html.replace('property="og:image:alt" content="', 'property="og:image:alt" content="X '),
        encoding="utf-8",
    )
    assert any("og:image:alt differs" in f[2] for f in run(site))


def test_missing_non_commercial_label(site):
    site.edit_yaml(f"zoo/models/{MODEL}/model.yaml", lambda m: m.update(usage_class="non-commercial"))
    assert any(f[0] == "O4" and "non-commercial" in f[2] for f in run(site))


def test_stale_hash_and_orphan(site):
    card = model_card(site)
    html = site.out / card["html"]
    html.write_text(
        html.read_text(encoding="utf-8").replace("scout-large", "scout-other"), encoding="utf-8"
    )
    (site.out / og.OG_DIR / "orphan.png").write_bytes(png(1200, 630))
    found = run(site)
    assert any(f[0] == "O5" and "does not carry the hash" in f[2] for f in found)
    assert ("O5", f"{og.OG_DIR}/orphan.png", "no page uses this image") in found


def test_p1_and_p3_cover_card_pages(site):
    page = site.out / og.CARD_DIR / f"{MODEL}.html"
    html = page.read_text(encoding="utf-8")
    html = html.replace(
        "</head>", '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter"></head>'
    )
    html = html.replace("</main>", "<p>Sponsor this zoo</p></main>")
    page.write_text(html, encoding="utf-8")
    where = f"{og.CARD_DIR}/{MODEL}.html"
    assert any(f[1] == where for f in check.check_resources(site.out))
    site_cfg = context.load_site_config(site.reg)
    assert any(f[1] == where and "Sponsor" in f[2] for f in check.check_branding(site_cfg, site.out))
