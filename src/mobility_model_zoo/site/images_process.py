"""Processing and content checks of website images (feature 016, research R3 to R5).

Crop around the focal point, encode WebP derivatives that carry the IPTC "trained algorithmic
media" marker, enforce the byte caps, detect faces (YuNet) and readable text (RapidOCR), and
compare regenerated images by perceptual hash (I5). Everything here needs the `images` extra and is
imported lazily by `zoo site images`; `zoo site build` never touches it.
"""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.errors import UsageError
from mobility_model_zoo.site.images import BYTE_CAPS, IPTC_MARKER, WIDTHS

INSTALL = "the images extra is missing: uv sync --extra release --extra images"
QUALITY, MIN_QUALITY = 72, 60
FACE_SCORE, FACE_MIN_HEIGHT = 0.5, 16
TEXT_CONFIDENCE, TEXT_MIN_CHARS = 0.7, 2
PHASH_MAX_BITS = 4
# opencv_zoo's YuNet face detector (MIT), pinned by content hash; fetched once into the cache.
YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
    "face_detection_yunet_2023mar.onnx"
)
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
CACHE = Path.home() / ".cache" / "mobility-model-zoo" / "yunet"


class MissingExtra(UsageError):
    pass


def _pil():
    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise MissingExtra(INSTALL) from e
    return Image


# ---- crop and encode ---------------------------------------------------------------------------
def crop_box(
    width: int, height: int, aspect: str, focal: tuple[float, float]
) -> tuple[int, int, int, int]:
    """The largest box of the aspect ratio inside the image, centred on the focal point and clamped
    to the edges, so the focal point stays visible at every width (FR-006)."""
    aw, ah = (16, 9) if aspect == "16:9" else (3, 2)
    if width * ah > height * aw:  # too wide: full height
        cw, ch = round(height * aw / ah), height
    else:
        cw, ch = width, round(width * ah / aw)
    cx, cy = focal[0] * width, focal[1] * height
    left = min(max(round(cx - cw / 2), 0), width - cw)
    top = min(max(round(cy - ch / 2), 0), height - ch)
    return left, top, left + cw, top + ch


def xmp_packet(model: str, series: str) -> bytes:
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
        'xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
        f"<Iptc4xmpExt:DigitalSourceType>{IPTC_MARKER}</Iptc4xmpExt:DigitalSourceType>"
        f"<xmp:CreatorTool>mobility-model-zoo imagery, series {series}, model {model}</xmp:CreatorTool>"
        '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
    ).encode()


def encode(img: Any, width: int, xmp: bytes) -> bytes:
    """One WebP derivative within its byte cap; quality drops from 72 to 60 if needed."""
    scaled = img.resize((width, round(width * img.height / img.width)), _pil().Resampling.LANCZOS)
    for quality in range(QUALITY, MIN_QUALITY - 1, -4):
        buf = io.BytesIO()
        scaled.save(buf, "WEBP", quality=quality, method=6, xmp=xmp)
        data = buf.getvalue()
        if len(data) <= BYTE_CAPS[width]:
            return data
    raise UsageError(
        f"the {width} px derivative stays above {BYTE_CAPS[width]} bytes even at quality {MIN_QUALITY}"
    )


def derivatives(
    png: Path, aspect: str, focal: tuple[float, float], model: str, series: str
) -> dict[int, bytes]:
    Image = _pil()
    with Image.open(png) as img:
        img = img.convert("RGB")
        cropped = img.crop(crop_box(img.width, img.height, aspect, focal))
        xmp = xmp_packet(model, series)
        return {w: encode(cropped, w, xmp) for w in WIDTHS}


def has_marker(path: Path) -> bool:
    """Whether a derivative carries the IPTC marker (check I3); reads the XMP chunk of the WebP."""
    Image = _pil()
    with Image.open(path) as img:
        xmp = img.info.get("xmp") or b""
    return IPTC_MARKER.encode() in xmp


# ---- content checks (I4) -----------------------------------------------------------------------
def _yunet_model() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "face_detection_yunet_2023mar.onnx"
    if not path.exists():
        with urllib.request.urlopen(YUNET_URL, timeout=60) as r:  # noqa: S310 - pinned by hash below
            path.write_bytes(r.read())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not YUNET_SHA256:
        print(f"warning: YuNet model is not pinned yet; downloaded sha256 {digest}", file=sys.stderr)
    elif digest != YUNET_SHA256:
        path.unlink()
        raise UsageError(f"YuNet model hash {digest} differs from the pinned {YUNET_SHA256}")
    return path


def faces(png: Path) -> dict[str, Any]:
    """Detections of identifiable size; `pass` is False if any (FR-009)."""
    try:
        import cv2
    except ImportError as e:  # pragma: no cover
        raise MissingExtra(INSTALL) from e
    import numpy as np

    img = cv2.imread(str(png))
    if img is None:
        raise UsageError(f"{png} is not an image")
    det = cv2.FaceDetectorYN.create(str(_yunet_model()), "", (320, 320), FACE_SCORE, 0.3, 5000)
    hits: list[dict[str, float]] = []
    below = 0
    views = [img]
    h, w = img.shape[:2]
    for half in (img[:, : w // 2], img[:, w // 2 :]):  # 2x upscaled halves catch small faces
        views.append(cv2.resize(half, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    for scale, view in zip((1, 2, 2), views, strict=True):
        det.setInputSize((view.shape[1], view.shape[0]))
        _, found = det.detect(view)
        for row in np.asarray(found if found is not None else []).reshape(-1, 15):
            height = float(row[3]) / scale
            score = float(row[14])
            if score >= FACE_SCORE and height >= FACE_MIN_HEIGHT:
                hits.append({"score": round(score, 3), "height_px": round(height, 1)})
            else:
                below += 1
    return {"pass": not hits, "hits": hits, "below_threshold": below}


def text(png: Path) -> dict[str, Any]:
    """OCR tokens with confidence ≥ 0.7 and at least two alphanumerics; any means fail (FR-009)."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as e:  # pragma: no cover
        raise MissingExtra(INSTALL) from e
    result, _ = RapidOCR()(str(png))
    tokens = []
    for _box, word, score in result or []:
        alnum = sum(ch.isalnum() for ch in word)
        if float(score) >= TEXT_CONFIDENCE and alnum >= TEXT_MIN_CHARS:
            tokens.append({"text": word, "score": round(float(score), 3)})
    return {"pass": not tokens, "tokens": tokens}


def tool_versions() -> dict[str, str]:
    from importlib import metadata

    out = {}
    for pkg in ("pillow", "opencv-python-headless", "rapidocr-onnxruntime", "onnxruntime"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pass
    out["yunet_sha256"] = YUNET_SHA256
    return out


# ---- perceptual hash (I5) ----------------------------------------------------------------------
def phash(path: Path) -> int:
    """64-bit pHash: 32x32 grey, DCT, top-left 8x8 against the median."""
    import numpy as np

    Image = _pil()
    with Image.open(path) as img:
        grey = np.asarray(img.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    n = 32
    k = np.arange(n)
    dct = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    coeffs = dct @ grey @ dct.T
    low = coeffs[:8, :8].flatten()
    median = np.median(low[1:])
    bits = 0
    for i, v in enumerate(low):
        if v > median:
            bits |= 1 << i
    return bits


def phash_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def phash_hex(path: Path) -> str:
    """The pHash as 16 hex characters, the form stored in `checks.measures.phash` (feature 019)."""
    return f"{phash(path):016x}"


def duplicate_of(h: str, others: dict[str, str], max_bits: int) -> tuple[str, int] | None:
    """The closest of `others` (id → hex pHash) within `max_bits`, as (id, bits); else None (I7)."""
    best: tuple[str, int] | None = None
    for other_id, oh in others.items():
        bits = bin(int(h, 16) ^ int(oh, 16)).count("1")
        if bits <= max_bits and (best is None or bits < best[1]):
            best = (other_id, bits)
    return best


# ---- style check (I6, feature 019, research R4) ------------------------------------------------
STYLE_LONG_SIDE = 240
ACCENT = "accent"  # the one anchor that must sit on the vehicle or machine
PALETTE_K = 6  # clusters measured on the approved images: the accent and five palette tones


def _lab_pixels(path: Path, long_side: int = STYLE_LONG_SIDE):
    """The image as float CIELAB (L 0-100, a and b centred) at `long_side` px, plus its shape."""
    import cv2
    import numpy as np

    Image = _pil()
    with Image.open(path) as img:
        img = img.convert("RGB")
        scale = long_side / max(img.width, img.height)
        small = img.resize(
            (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
            Image.Resampling.LANCZOS,
        )
        rgb = np.asarray(small, dtype=np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float64)
    lab[..., 0] *= 100.0 / 255.0
    lab[..., 1:] -= 128.0
    return lab


def style(path: Path, palette: dict[str, Any]) -> dict[str, Any]:
    """Palette and accent-location measurement against the series' anchors. Every pixel goes to
    its nearest anchor within `tolerance_de` (CIE76), else to `other`. Rules: `other` share ≤
    other_max; accent share within [accent_min, accent_max]; the largest 8-connected accent
    region holds ≥ largest_min of accent pixels; accent in the top fifth ≤ top_max of accent
    pixels unless the largest region reaches into the top fifth. Returns pass, reasons, measures;
    the measures include the accent centroid (clamped to 0.2–0.8) as the default focal point."""
    import cv2
    import numpy as np

    lab = _lab_pixels(path)
    h, w = lab.shape[:2]
    names = list(palette["anchors"])
    accent_i, other_i = names.index(ACCENT), len(names)
    anchors = np.array([palette["anchors"][n] for n in names], dtype=np.float64)
    flat = lab.reshape(-1, 3)
    d = np.sqrt(((flat[:, None, :] - anchors[None, :, :]) ** 2).sum(axis=2))
    nearest = d.argmin(axis=1)
    within = d[np.arange(len(flat)), nearest] <= float(palette["tolerance_de"])
    labels = np.where(within, nearest, other_i)
    n = len(flat)
    other_share = float((labels == other_i).sum() / n)
    accent_mask = (labels == accent_i).reshape(h, w).astype(np.uint8)
    accent_px = int(accent_mask.sum())
    accent_share = accent_px / n
    largest_share, top_share, centroid, reaches_top = 0.0, 0.0, [0.5, 0.5], False
    if accent_px:
        count, comp, stats, cents = cv2.connectedComponentsWithStats(accent_mask, connectivity=8)
        if count > 1:
            areas = stats[1:, cv2.CC_STAT_AREA]
            k = int(areas.argmax()) + 1
            largest_share = float(areas.max() / accent_px)
            cx, cy = cents[k]
            centroid = [
                round(min(0.8, max(0.2, float(cx) / w)), 3),
                round(min(0.8, max(0.2, float(cy) / h)), 3),
            ]
            top_k = int(stats[k, cv2.CC_STAT_TOP])
            bottom_k = top_k + int(stats[k, cv2.CC_STAT_HEIGHT])
            # a tall machine may reach into the sky band; a region lying inside it is a sky
            reaches_top = top_k < h / 5 < bottom_k
        top_share = float(accent_mask[: max(1, h // 5), :].sum() / accent_px)
    reasons = []
    if other_share > palette["other_max"]:
        reasons.append(f"other {other_share:.1%} > {palette['other_max']:.0%}")
    if accent_share < palette["accent_min"]:
        reasons.append(f"accent_min {accent_share:.1%} < {palette['accent_min']:.1%}")
    if accent_share > palette["accent_max"]:
        reasons.append(f"accent_max {accent_share:.1%} > {palette['accent_max']:.0%}")
    if accent_px and largest_share < palette["largest_min"]:
        reasons.append(f"largest {largest_share:.0%} < {palette['largest_min']:.0%}")
    if accent_px and top_share > palette["top_max"] and not reaches_top:
        reasons.append(f"top {top_share:.0%} > {palette['top_max']:.0%}")
    return {
        "pass": not reasons,
        "reasons": reasons,
        "measures": {
            "other_share": round(other_share, 4),
            "accent_share": round(accent_share, 4),
            "accent_largest_share": round(largest_share, 4),
            "accent_top_share": round(top_share, 4),
            "accent_centroid": centroid,
        },
    }


def measure_anchors(paths: list[Path], k: int = PALETTE_K) -> dict[str, list[float]]:
    """k-means over the Lab pixels of approved images. The centre with the strongest yellow-red
    (a + b) is the accent; the others are palette tones named by lightness, darkest first
    (`tone1` …). Printed once into the series file (research R4, task T025)."""
    import cv2
    import numpy as np

    pixels = np.concatenate([_lab_pixels(p, 160).reshape(-1, 3) for p in paths]).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 60, 0.5)
    _, _, centres = cv2.kmeans(pixels, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    centres = [[round(float(v), 1) for v in c] for c in centres]
    accent = max(centres, key=lambda c: c[1] + c[2])
    tones = sorted((c for c in centres if c is not accent), key=lambda c: c[0])
    out = {ACCENT: accent}
    for i, c in enumerate(tones, 1):
        out[f"tone{i}"] = c
    return out
